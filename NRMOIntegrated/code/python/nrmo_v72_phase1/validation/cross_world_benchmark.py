"""
validation/cross_world_benchmark.py

Cross-world generality validation.

Hypothesis (handoff doc § 18 implicit):
  v8.5.1 ContextualCandidateMerger が ChaoticWorld 以外の chaotic world でも
  v8.4.1 を上回るなら、それは真の generality.

Comparison:
  WorldType:        ChaoticWorld  /  DriftingWorld
  Engine x level:   v7.1, v8.4.1, v8.5(original merger), v8.5.1(contextual)
                     x chaos levels mild, moderate, severe
  
  Plus recover_fixed baseline (sanity check)
"""
from __future__ import annotations
import os, sys, json, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List
import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "core"))

from config import NRMOConfig
from chaotic_world import ChaoticWorld, ChaosConfig
from drifting_world import DriftingWorld
from world_models import Action


# ============================================================
# Runners (world type に応じて切替)
# ============================================================

def _make_world(world_type: str, chaos_level: str, seed: int):
    cfg = ChaosConfig.from_level(chaos_level)
    if world_type == "chaotic":
        return ChaoticWorld(cfg, seed=seed)
    elif world_type == "drifting":
        return DriftingWorld(cfg, seed=seed)
    raise ValueError(f"Unknown world_type: {world_type}")


def _run_v71(args):
    world_type, chaos, horizon, seed = args
    from engines import V71Engine
    world = _make_world(world_type, chaos, seed)
    eng = V71Engine(rng=np.random.default_rng(seed + 100000))
    ruined = False
    for t in range(horizon):
        a = eng.select_action(world.observe())
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v841(args):
    world_type, chaos, horizon, seed = args
    from v841_engine import V841Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V841Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True)
    ruined = False
    for t in range(horizon):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(world.state)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v85(args):
    world_type, chaos, horizon, seed = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V851Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True,
                       use_strong_engine_full=True,
                       use_contextual_merger=False)  # original merger
    ruined = False
    for t in range(horizon):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(world.state)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v851(args):
    world_type, chaos, horizon, seed = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V851Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True,
                       use_strong_engine_full=True,
                       use_contextual_merger=True)  # contextual
    ruined = False
    for t in range(horizon):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(world.state)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "module_counts": dict(eng.stats["module_selection_counts"]),
             "context_counts": dict(eng.stats["context_counts"]),
             "aggressive_counters": eng.get_aggressive_counters()}


def _run_recover_fixed(args):
    world_type, chaos, horizon, seed = args
    world = _make_world(world_type, chaos, seed)
    ruined = False
    a = Action("recover", "A")
    for t in range(horizon):
        r, done, _ = world.step(a)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def compute_metrics(rs: List[Dict], n_runs: int) -> Dict:
    scores = np.array([r["final_score"] for r in rs])
    steps = np.array([r["completed_steps"] for r in rs])
    ruined = np.array([r["is_ruined"] for r in rs])
    sorted_s = np.sort(scores)
    n_bottom = max(1, n_runs // 10)
    return {
        "median": float(np.median(scores)),
        "mean": float(np.mean(scores)),
        "std": float(np.std(scores)),
        "p5": float(np.percentile(scores, 5)),
        "cvar_lower_10pct": float(np.mean(sorted_s[:n_bottom])),
        "ruin_rate": float(np.mean(ruined)),
        "median_steps": float(np.median(steps)),
    }


def run_cross_world(cfg, n_runs=150, horizon=200, seed_offset=4000):
    world_types = ["chaotic", "drifting"]
    chaos_levels = ["mild", "moderate", "severe"]
    
    print("=" * 80)
    print("Cross-World Generality Test")
    print("=" * 80)
    print(f"  n_runs={n_runs}, horizon={horizon}, seeds {seed_offset}-{seed_offset+n_runs-1}")
    print(f"  World types: {world_types}")
    print(f"  Chaos levels: {chaos_levels}")
    
    all_results = {}
    
    for world_type in world_types:
        print(f"\n{'='*60}")
        print(f"  WORLD: {world_type.upper()}")
        print(f"{'='*60}")
        all_results[world_type] = {}
        
        for level in chaos_levels:
            print(f"\n[{world_type}/{level}]")
            args_base = [(world_type, level, horizon, seed_offset + s) for s in range(n_runs)]
            
            t0 = time.time()
            with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                v71_r = list(ex.map(_run_v71, args_base))
            with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                v841_r = list(ex.map(_run_v841, args_base))
            with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                v85_r = list(ex.map(_run_v85, args_base))
            with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                v851_r = list(ex.map(_run_v851, args_base))
            with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                rec_fixed_r = list(ex.map(_run_recover_fixed, args_base))
            elapsed = time.time() - t0
            
            v71_m = compute_metrics(v71_r, n_runs)
            v841_m = compute_metrics(v841_r, n_runs)
            v85_m = compute_metrics(v85_r, n_runs)
            v851_m = compute_metrics(v851_r, n_runs)
            rec_fixed_m = compute_metrics(rec_fixed_r, n_runs)
            
            # Paired
            diffs_851_vs_841 = np.array([v851_r[i]["final_score"] - v841_r[i]["final_score"]
                                          for i in range(n_runs)])
            diffs_851_vs_rec = np.array([v851_r[i]["final_score"] - rec_fixed_r[i]["final_score"]
                                          for i in range(n_runs)])
            
            from scipy.stats import wilcoxon
            try:
                _, p_vs_841 = wilcoxon(diffs_851_vs_841, alternative="two-sided")
            except Exception:
                p_vs_841 = None
            try:
                _, p_vs_rec = wilcoxon(diffs_851_vs_rec, alternative="two-sided")
            except Exception:
                p_vs_rec = None
            
            # Aggregate v851 stats
            agg_mod = {}
            agg_ctx = {}
            agg_aggressive = {"generated_count": 0, "eligible_count": 0,
                                "selected_by_merger_count": 0, "final_accepted_count": 0}
            for r in v851_r:
                for m, c in r.get("module_counts", {}).items():
                    agg_mod[m] = agg_mod.get(m, 0) + c
                for ctx, c in r.get("context_counts", {}).items():
                    agg_ctx[ctx] = agg_ctx.get(ctx, 0) + c
                for k in agg_aggressive.keys():
                    agg_aggressive[k] += r.get("aggressive_counters", {}).get(k, 0)
            
            cell = {
                "n_runs": n_runs,
                "v71": v71_m,
                "v841": v841_m,
                "v85": v85_m,
                "v851": v851_m,
                "recover_fixed": rec_fixed_m,
                "paired_v851_vs_v841": {
                    "median_diff": float(np.median(diffs_851_vs_841)),
                    "wilcoxon_p": p_vs_841,
                    "n_851_better": int(np.sum(diffs_851_vs_841 > 0)),
                },
                "paired_v851_vs_recover_fixed": {
                    "median_diff": float(np.median(diffs_851_vs_rec)),
                    "wilcoxon_p": p_vs_rec,
                    "n_851_better": int(np.sum(diffs_851_vs_rec > 0)),
                },
                "v851_module_histogram": agg_mod,
                "v851_context_histogram": agg_ctx,
                "v851_aggressive_counters": agg_aggressive,
                "elapsed_sec": elapsed,
            }
            
            # Print
            print(f"  v7.1:           med={v71_m['median']:6.2f} std={v71_m['std']:5.2f} ruin={v71_m['ruin_rate']:.0%}")
            print(f"  v8.4.1:         med={v841_m['median']:6.2f} std={v841_m['std']:5.2f} ruin={v841_m['ruin_rate']:.0%}")
            print(f"  v8.5 (orig):    med={v85_m['median']:6.2f} std={v85_m['std']:5.2f} ruin={v85_m['ruin_rate']:.0%}")
            print(f"  v8.5.1 (ctx):   med={v851_m['median']:6.2f} std={v851_m['std']:5.2f} ruin={v851_m['ruin_rate']:.0%}")
            print(f"  recover_fixed:  med={rec_fixed_m['median']:6.2f} std={rec_fixed_m['std']:5.2f} ruin={rec_fixed_m['ruin_rate']:.0%}")
            
            d = cell["paired_v851_vs_v841"]["median_diff"]
            sign = "+" if d >= 0 else ""
            w = cell["paired_v851_vs_v841"]["n_851_better"]
            p_str = f"{p_vs_841:.4f}" if p_vs_841 else "n/a"
            print(f"  v851 vs v841:    diff={sign}{d:.2f}, 851 wins {w}/{n_runs}, p={p_str}")
            
            d_r = cell["paired_v851_vs_recover_fixed"]["median_diff"]
            sign_r = "+" if d_r >= 0 else ""
            w_r = cell["paired_v851_vs_recover_fixed"]["n_851_better"]
            p_r_str = f"{p_vs_rec:.4f}" if p_vs_rec else "n/a"
            print(f"  v851 vs rec_fxd: diff={sign_r}{d_r:.2f}, 851 wins {w_r}/{n_runs}, p={p_r_str}")
            
            print(f"  Modules: {agg_mod}")
            print(f"  Aggressive: gen={agg_aggressive['generated_count']} "
                  f"sel={agg_aggressive['selected_by_merger_count']}")
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = cell
    
    return all_results


def check_generality(results: Dict) -> Dict:
    """Generality criteria"""
    print("\n" + "=" * 80)
    print("Cross-World Generality Check")
    print("=" * 80)
    
    criteria = {}
    
    # 1. v851 vs v841 in DriftingWorld (新 world で機能するか)
    drifting_diffs = []
    for level in ["mild", "moderate", "severe"]:
        cell = results.get("drifting", {}).get(level, {})
        if cell:
            d = cell["paired_v851_vs_v841"]["median_diff"]
            p = cell["paired_v851_vs_v841"]["wilcoxon_p"]
            drifting_diffs.append((level, d, p))
    
    # 全 level で improvement
    all_improved = all(d > 0 for _, d, _ in drifting_diffs)
    criteria["1_v851_beats_v841_in_drifting"] = {
        "passed": all_improved,
        "evidence": [{"level": l, "diff": d, "p": p} for l, d, p in drifting_diffs],
    }
    
    # 2. v851 vs recover_fixed in DriftingWorld (NRMO 戦略が機械的戦略より良いか)
    rec_diffs = []
    for level in ["mild", "moderate", "severe"]:
        cell = results.get("drifting", {}).get(level, {})
        if cell:
            d = cell["paired_v851_vs_recover_fixed"]["median_diff"]
            rec_diffs.append((level, d))
    all_beat_rec = all(d > 0 for _, d in rec_diffs)
    criteria["2_v851_beats_recover_fixed_in_drifting"] = {
        "passed": all_beat_rec,
        "evidence": [{"level": l, "diff": d} for l, d in rec_diffs],
    }
    
    # 3. AggressiveEngine activates in DriftingWorld
    agg_active = []
    for level in ["mild", "moderate", "severe"]:
        cell = results.get("drifting", {}).get(level, {})
        if cell:
            sel = cell["v851_aggressive_counters"]["selected_by_merger_count"]
            agg_active.append((level, sel))
    total_sel = sum(s for _, s in agg_active)
    criteria["3_aggressive_selected_in_drifting"] = {
        "passed": total_sel > 0,
        "evidence": [{"level": l, "selected": s} for l, s in agg_active],
        "total_selected": total_sel,
    }
    
    # 4. Module diversity (not recovery-only)
    diversity_check = []
    for level in ["mild", "moderate", "severe"]:
        cell = results.get("drifting", {}).get(level, {})
        if cell:
            hist = cell["v851_module_histogram"]
            total = sum(hist.values())
            rec = hist.get("RecoveryCandidate", 0)
            rec_ratio = rec / total if total > 0 else 0
            diversity_check.append((level, rec_ratio))
    avg_rec = np.mean([r for _, r in diversity_check]) if diversity_check else 1.0
    criteria["4_module_diversity_in_drifting"] = {
        "passed": avg_rec < 0.50,
        "evidence": [{"level": l, "recovery_ratio": r} for l, r in diversity_check],
        "avg_recovery_ratio": float(avg_rec),
    }
    
    n_passed = sum(1 for c in criteria.values() if c["passed"])
    print(f"\n{n_passed}/{len(criteria)} generality criteria PASSED:")
    for key, status in criteria.items():
        mark = "✅" if status["passed"] else "❌"
        print(f"  {mark} {key}")
    
    return criteria


def _convert(obj):
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert(v) for v in obj]
    return obj


if __name__ == "__main__":
    cfg = NRMOConfig.from_env(n_workers=4)
    results = run_cross_world(cfg, n_runs=150, horizon=200, seed_offset=4000)
    criteria = check_generality(results)
    
    summary = {
        "version": "cross_world_v851",
        "description": "v8.5.1 generality test on DriftingWorld",
        "main_results": results,
        "generality_criteria": criteria,
    }
    
    out = cfg.results_dir / "cross_world_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
