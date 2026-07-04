"""
validation/v851_full_benchmark.py

V8.5.1 = v8.5 + ContextualCandidateMerger.

Required (handoff doc § 14):
  Baselines: v7.1, v8.4.1, v8.5 full, v8.5.1
  
  Required outputs (§ 14.3):
    median, paired median diff, mean, std,
    lower quartile (25%), 5th percentile, CVaR (lower tail mean),
    time_to_ruin (median + lower tail), ruin_rate, Wilcoxon p,
    module selection histogram, action histogram,
    context histogram, context × module table

Success criteria (§ 16):
  1. Does not degrade v8.4.1 in mild/moderate/severe
  2. Does not worsen lower tail in extreme/total
  3. RecoveryCandidate not always-on winner
  4. Module selection diversity in appropriate contexts
  5. AggressiveEngine has nonzero generated + eligible counts
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
from world_models import Action


def _run_v71(args):
    chaos, horizon, seed = args
    from engines import V71Engine
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
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
    chaos, horizon, seed = args
    from v841_engine import V841Engine
    from rng_manager import RNGManager
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
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


def _run_v85_full(args):
    """v8.5 with original CandidateMerger (handoff doc baseline)"""
    chaos, horizon, seed = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
    eng = V851Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True,
                       use_strong_engine_full=True,
                       use_contextual_merger=False)  # ★ original merger
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


def _run_v851(args):
    """v8.5.1 with ContextualCandidateMerger"""
    chaos, horizon, seed = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
    eng = V851Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True,
                       use_strong_engine_full=True,
                       use_contextual_merger=True)  # ★ contextual merger
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
             "context_module_table": dict(eng.stats["context_module_table"]),
             "aggressive_counters": eng.get_aggressive_counters()}


# ============================================================
# Required outputs (handoff doc § 14.3)
# ============================================================

def compute_full_metrics(rs: List[Dict], n_runs: int) -> Dict:
    scores = np.array([r["final_score"] for r in rs])
    steps = np.array([r["completed_steps"] for r in rs])
    ruined = np.array([r["is_ruined"] for r in rs])
    
    # Lower tail: 5th percentile, CVaR (mean of bottom 10%)
    p5 = float(np.percentile(scores, 5))
    p25 = float(np.percentile(scores, 25))
    
    sorted_scores = np.sort(scores)
    n_bottom = max(1, n_runs // 10)
    cvar_lower = float(np.mean(sorted_scores[:n_bottom]))
    
    steps_p5 = float(np.percentile(steps, 5))
    
    return {
        "median": float(np.median(scores)),
        "mean": float(np.mean(scores)),
        "std": float(np.std(scores)),
        "p25_lower_quartile": p25,
        "p5_lower": p5,
        "cvar_lower_10pct": cvar_lower,
        "ruin_rate": float(np.mean(ruined)),
        "median_steps": float(np.median(steps)),
        "p5_steps_lower_tail": steps_p5,
    }


def run_v851_benchmark(cfg, n_runs=200, horizon=200, seed_offset=2000):
    levels = ["mild", "moderate", "severe", "extreme", "total"]
    
    print("=" * 80)
    print("V8.5.1 Full Benchmark (handoff doc § 14)")
    print("=" * 80)
    print(f"  n_runs={n_runs}, seeds {seed_offset}-{seed_offset+n_runs-1}")
    
    all_results = {}
    
    for level in levels:
        print(f"\n[{level.upper()}]")
        args = [(level, horizon, seed_offset + s) for s in range(n_runs)]
        
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
            v71_r = list(ex.map(_run_v71, args))
        with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
            v841_r = list(ex.map(_run_v841, args))
        with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
            v85_r = list(ex.map(_run_v85_full, args))
        with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
            v851_r = list(ex.map(_run_v851, args))
        elapsed = time.time() - t0
        
        v71_m = compute_full_metrics(v71_r, n_runs)
        v841_m = compute_full_metrics(v841_r, n_runs)
        v85_m = compute_full_metrics(v85_r, n_runs)
        v851_m = compute_full_metrics(v851_r, n_runs)
        
        # Paired comparisons
        diffs_851_vs_841 = np.array([v851_r[i]["final_score"] - v841_r[i]["final_score"]
                                       for i in range(n_runs)])
        diffs_851_vs_85 = np.array([v851_r[i]["final_score"] - v85_r[i]["final_score"]
                                      for i in range(n_runs)])
        
        from scipy.stats import wilcoxon
        try:
            _, p_vs_841 = wilcoxon(diffs_851_vs_841, alternative="two-sided")
        except Exception:
            p_vs_841 = None
        try:
            _, p_vs_85 = wilcoxon(diffs_851_vs_85, alternative="two-sided")
        except Exception:
            p_vs_85 = None
        
        # Aggregate module selection across runs (V851)
        agg_module_counts = {}
        agg_context_counts = {}
        agg_context_module = {}
        for r in v851_r:
            for m, c in r.get("module_counts", {}).items():
                agg_module_counts[m] = agg_module_counts.get(m, 0) + c
            for ctx, c in r.get("context_counts", {}).items():
                agg_context_counts[ctx] = agg_context_counts.get(ctx, 0) + c
            for ctx, mod_dict in r.get("context_module_table", {}).items():
                if ctx not in agg_context_module:
                    agg_context_module[ctx] = {}
                for m, c in mod_dict.items():
                    agg_context_module[ctx][m] = agg_context_module[ctx].get(m, 0) + c
        
        # AggressiveEngine aggregate counters
        agg_aggressive = {
            "generated_count": 0, "eligible_count": 0,
            "selected_by_merger_count": 0, "final_accepted_count": 0,
            "blocked_by_guard_count": 0, "blocked_by_revalidation_count": 0,
        }
        for r in v851_r:
            for k in agg_aggressive.keys():
                agg_aggressive[k] += r.get("aggressive_counters", {}).get(k, 0)
        
        cell = {
            "n_runs": n_runs,
            "v71_metrics": v71_m,
            "v841_metrics": v841_m,
            "v85_metrics": v85_m,
            "v851_metrics": v851_m,
            "paired_v851_vs_v841": {
                "median_diff": float(np.median(diffs_851_vs_841)),
                "mean_diff": float(np.mean(diffs_851_vs_841)),
                "n_851_better": int(np.sum(diffs_851_vs_841 > 0)),
                "wilcoxon_p": p_vs_841,
            },
            "paired_v851_vs_v85": {
                "median_diff": float(np.median(diffs_851_vs_85)),
                "mean_diff": float(np.mean(diffs_851_vs_85)),
                "n_851_better": int(np.sum(diffs_851_vs_85 > 0)),
                "wilcoxon_p": p_vs_85,
            },
            "v851_module_selection_histogram": agg_module_counts,
            "v851_context_histogram": agg_context_counts,
            "v851_context_module_table": agg_context_module,
            "v851_aggressive_counters_total": agg_aggressive,
            "elapsed_sec": elapsed,
        }
        
        # Print summary
        print(f"  v7.1:    med={v71_m['median']:6.2f} std={v71_m['std']:5.2f} "
              f"p5={v71_m['p5_lower']:6.2f} CVaR={v71_m['cvar_lower_10pct']:6.2f}")
        print(f"  v8.4.1:  med={v841_m['median']:6.2f} std={v841_m['std']:5.2f} "
              f"p5={v841_m['p5_lower']:6.2f} CVaR={v841_m['cvar_lower_10pct']:6.2f}")
        print(f"  v8.5:    med={v85_m['median']:6.2f} std={v85_m['std']:5.2f} "
              f"p5={v85_m['p5_lower']:6.2f} CVaR={v85_m['cvar_lower_10pct']:6.2f}")
        print(f"  v8.5.1:  med={v851_m['median']:6.2f} std={v851_m['std']:5.2f} "
              f"p5={v851_m['p5_lower']:6.2f} CVaR={v851_m['cvar_lower_10pct']:6.2f}")
        
        d = cell["paired_v851_vs_v841"]["median_diff"]
        sign = "+" if d >= 0 else ""
        w = cell["paired_v851_vs_v841"]["n_851_better"]
        p_str = f"{p_vs_841:.4f}" if p_vs_841 else "n/a"
        print(f"  v851 vs v841: med diff={sign}{d:.2f}, 851 wins {w}/{n_runs}, p={p_str}")
        
        d2 = cell["paired_v851_vs_v85"]["median_diff"]
        sign2 = "+" if d2 >= 0 else ""
        w2 = cell["paired_v851_vs_v85"]["n_851_better"]
        p2_str = f"{p_vs_85:.4f}" if p_vs_85 else "n/a"
        print(f"  v851 vs v85:  med diff={sign2}{d2:.2f}, 851 wins {w2}/{n_runs}, p={p2_str}")
        
        print(f"  Module selection (v8.5.1):  {agg_module_counts}")
        print(f"  Context histogram (v8.5.1): {agg_context_counts}")
        print(f"  Aggressive: gen={agg_aggressive['generated_count']} "
              f"eligible={agg_aggressive['eligible_count']} "
              f"selected={agg_aggressive['selected_by_merger_count']} "
              f"final={agg_aggressive['final_accepted_count']}")
        print(f"  ({elapsed:.0f}s)")
        
        all_results[level] = cell
    
    return all_results


def check_success_criteria(results: Dict) -> Dict:
    """Handoff doc § 16 success criteria"""
    print("\n" + "=" * 80)
    print("V8.5.1 Success Criteria (handoff doc § 16)")
    print("=" * 80)
    
    criteria = {}
    
    # 1. Does not degrade v8.4.1 in mild/moderate/severe
    deg = []
    for level in ["mild", "moderate", "severe"]:
        d = results[level]["paired_v851_vs_v841"]["median_diff"]
        p = results[level]["paired_v851_vs_v841"]["wilcoxon_p"]
        ok = (d >= -1.0) or (p is not None and p > 0.05)
        deg.append((level, d, p, ok))
    criteria["1_no_degrade_mild_moderate_severe"] = {
        "passed": all(d[3] for d in deg),
        "evidence": [{"level": d[0], "diff": d[1], "p": d[2]} for d in deg],
    }
    
    # 2. Does not worsen lower tail in extreme/total
    lower_check = []
    for level in ["extreme", "total"]:
        v841_p5 = results[level]["v841_metrics"]["p5_lower"]
        v851_p5 = results[level]["v851_metrics"]["p5_lower"]
        v841_cvar = results[level]["v841_metrics"]["cvar_lower_10pct"]
        v851_cvar = results[level]["v851_metrics"]["cvar_lower_10pct"]
        ok = (v851_p5 >= v841_p5 - 1.0) and (v851_cvar >= v841_cvar - 1.0)
        lower_check.append((level, v841_p5, v851_p5, v841_cvar, v851_cvar, ok))
    criteria["2_no_worsen_lower_tail_extreme_total"] = {
        "passed": all(c[5] for c in lower_check),
        "evidence": [{"level": c[0], "v841_p5": c[1], "v851_p5": c[2],
                       "v841_cvar": c[3], "v851_cvar": c[4]} for c in lower_check],
    }
    
    # 3. RecoveryCandidate not always-on
    rec_ratios = []
    for level, cell in results.items():
        hist = cell["v851_module_selection_histogram"]
        total = sum(hist.values())
        rec_count = hist.get("RecoveryCandidate", 0)
        rec_ratio = rec_count / total if total > 0 else 0
        rec_ratios.append((level, rec_ratio))
    # 50% 未満なら "not always-on"
    avg_rec_ratio = np.mean([r[1] for r in rec_ratios])
    criteria["3_recovery_not_always_on"] = {
        "passed": avg_rec_ratio < 0.50,
        "evidence": [{"level": r[0], "recovery_ratio": r[1]} for r in rec_ratios],
        "avg_recovery_ratio": float(avg_rec_ratio),
    }
    
    # 4. Module diversity
    diversities = []
    for level, cell in results.items():
        hist = cell["v851_module_selection_histogram"]
        active_modules = sum(1 for c in hist.values() if c > 0)
        diversities.append((level, active_modules))
    avg_active = np.mean([d[1] for d in diversities])
    criteria["4_module_diversity"] = {
        "passed": avg_active >= 3,  # at least 3 distinct modules selected
        "evidence": [{"level": d[0], "active_modules": d[1]} for d in diversities],
        "avg_active_modules": float(avg_active),
    }
    
    # 5. AggressiveEngine nonzero generated + eligible
    agg_check = []
    for level, cell in results.items():
        agg = cell["v851_aggressive_counters_total"]
        ok = agg["generated_count"] > 0 and agg["eligible_count"] > 0
        agg_check.append((level, agg["generated_count"], agg["eligible_count"], ok))
    criteria["5_aggressive_nonzero_generated_eligible"] = {
        "passed": all(c[3] for c in agg_check),
        "evidence": [{"level": c[0], "gen": c[1], "elig": c[2]} for c in agg_check],
    }
    
    n_passed = sum(1 for c in criteria.values() if c["passed"])
    print(f"\n{n_passed}/5 criteria PASSED:")
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
    results = run_v851_benchmark(cfg, n_runs=200, horizon=200, seed_offset=2000)
    criteria = check_success_criteria(results)
    
    summary = {
        "version": "v8.5.1",
        "description": "v8.5 + ContextualCandidateMerger",
        "main_results": results,
        "success_criteria_check": criteria,
    }
    
    out = cfg.results_dir / "v851_full_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
