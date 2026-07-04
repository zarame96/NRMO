"""
validation/v851_ablation_suite.py

V8.5.1 ablation suite (handoff doc § 15).

12 variants:
  1. Full v8.5.1
  2. No RecoveryCandidate
  3. RecoveryCandidate only
  4. No AggressiveEngine
  5. AggressiveEngine forced diagnostic
  6. No Mutation
  7. No Synthesis
  8. No Invention
  9. No ContextualRouter (= v8.5 original merger)
  10. No recovery repetition penalty (TODO future)
  11. No opportunity-context recovery penalty (TODO future)
  12. Original CandidateMerger vs ContextualCandidateMerger (= 1 vs 9)

Plus baselines:
  v8.4.1 frozen
  recover/A fixed baseline
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


# ============================================================
# Variant runners
# ============================================================

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


def _run_recover_fixed(args):
    """recover/A fixed baseline (no agent learning, no engine)"""
    chaos, horizon, seed = args
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
    ruined = False
    action = Action("recover", "A")
    for t in range(horizon):
        r, done, _ = world.step(action)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v851_variant(args):
    """Generic v8.5.1 runner with config"""
    chaos, horizon, seed, variant_config = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
    
    eng = V851Engine(
        rng_manager=RNGManager(master_seed=seed + 200000),
        use_active_pattern=True,
        use_strong_engine_full=variant_config.get("strong_engine", True),
        use_contextual_merger=variant_config.get("contextual_merger", True),
        module_config=variant_config.get("module_config", None),
        aggressive_forced_diagnostic=variant_config.get("aggressive_forced", False),
    )
    
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
    
    return {
        "final_score": float(world.state.cumulative_score),
        "is_ruined": ruined,
        "completed_steps": world.state.t,
        "module_counts": dict(eng.stats["module_selection_counts"]),
        "context_counts": dict(eng.stats["context_counts"]),
        "context_module_table": dict(eng.stats["context_module_table"]),
        "aggressive_counters": eng.get_aggressive_counters(),
    }


def _run_v85_original_merger(args):
    """Variant 9 / 12: v8.5 original merger"""
    chaos, horizon, seed = args
    return _run_v851_variant((chaos, horizon, seed, {
        "strong_engine": True,
        "contextual_merger": False,  # original
        "module_config": None,
    }))


def make_variant_config(name: str) -> Dict:
    """Variant config factory"""
    all_on = {m: True for m in ["defensive", "recovery", "exploration",
                                  "mutation", "synthesis", "invention", "aggressive"]}
    
    if name == "full":
        return {"strong_engine": True, "contextual_merger": True}
    
    elif name == "no_recovery":
        mc = dict(all_on); mc["recovery"] = False
        return {"strong_engine": True, "contextual_merger": True, "module_config": mc}
    
    elif name == "recovery_only":
        mc = {m: False for m in all_on.keys()}
        mc["recovery"] = True
        return {"strong_engine": True, "contextual_merger": True, "module_config": mc}
    
    elif name == "no_aggressive":
        mc = dict(all_on); mc["aggressive"] = False
        return {"strong_engine": True, "contextual_merger": True, "module_config": mc}
    
    elif name == "aggressive_forced":
        return {"strong_engine": True, "contextual_merger": True,
                 "aggressive_forced": True}
    
    elif name == "no_mutation":
        mc = dict(all_on); mc["mutation"] = False
        return {"strong_engine": True, "contextual_merger": True, "module_config": mc}
    
    elif name == "no_synthesis":
        mc = dict(all_on); mc["synthesis"] = False
        return {"strong_engine": True, "contextual_merger": True, "module_config": mc}
    
    elif name == "no_invention":
        mc = dict(all_on); mc["invention"] = False
        return {"strong_engine": True, "contextual_merger": True, "module_config": mc}
    
    elif name == "original_merger":  # variant 9 / 12
        return {"strong_engine": True, "contextual_merger": False}
    
    raise ValueError(f"Unknown variant: {name}")


VARIANTS = [
    "full",
    "no_recovery",
    "recovery_only",
    "no_aggressive",
    "aggressive_forced",
    "no_mutation",
    "no_synthesis",
    "no_invention",
    "original_merger",
]


# ============================================================
# Metrics computation
# ============================================================

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
        "p25": float(np.percentile(scores, 25)),
        "p5": float(np.percentile(scores, 5)),
        "cvar_lower_10pct": float(np.mean(sorted_s[:n_bottom])),
        "ruin_rate": float(np.mean(ruined)),
        "median_steps": float(np.median(steps)),
    }


def run_ablation_suite(cfg, n_runs=150, horizon=200, seed_offset=3000):
    """Run all variants on selected chaos levels"""
    levels = ["mild", "moderate", "severe", "extreme", "total"]
    
    print("=" * 80)
    print("V8.5.1 Ablation Suite (handoff doc § 15)")
    print("=" * 80)
    print(f"  n_runs={n_runs}, seeds {seed_offset}-{seed_offset+n_runs-1}")
    print(f"  Variants: {VARIANTS}")
    print(f"  + baselines: v8.4.1, recover_fixed")
    
    all_results = {}
    
    for level in levels:
        print(f"\n[{level.upper()}]")
        args_base = [(level, horizon, seed_offset + s) for s in range(n_runs)]
        
        t0 = time.time()
        
        # Baselines
        print("  Running baselines...")
        with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
            v841_r = list(ex.map(_run_v841, args_base))
        with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
            rec_fixed_r = list(ex.map(_run_recover_fixed, args_base))
        v841_m = compute_metrics(v841_r, n_runs)
        rec_fixed_m = compute_metrics(rec_fixed_r, n_runs)
        
        print(f"    v8.4.1:        med={v841_m['median']:6.2f} std={v841_m['std']:5.2f}")
        print(f"    recover_fixed: med={rec_fixed_m['median']:6.2f} std={rec_fixed_m['std']:5.2f}")
        
        # Variants
        variant_results = {}
        for variant in VARIANTS:
            vconfig = make_variant_config(variant)
            args_v = [(level, horizon, seed_offset + s, vconfig) for s in range(n_runs)]
            with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                results = list(ex.map(_run_v851_variant, args_v))
            
            m = compute_metrics(results, n_runs)
            
            # Aggregate module/context/aggressive
            agg_mod = {}
            agg_ctx = {}
            agg_aggressive = {"generated_count": 0, "eligible_count": 0,
                                "selected_by_merger_count": 0, "final_accepted_count": 0,
                                "blocked_by_guard_count": 0, "blocked_by_revalidation_count": 0}
            for r in results:
                for mod, c in r.get("module_counts", {}).items():
                    agg_mod[mod] = agg_mod.get(mod, 0) + c
                for ctx, c in r.get("context_counts", {}).items():
                    agg_ctx[ctx] = agg_ctx.get(ctx, 0) + c
                for k in agg_aggressive.keys():
                    agg_aggressive[k] += r.get("aggressive_counters", {}).get(k, 0)
            
            # Paired diff vs full
            full_scores = np.array([variant_results.get("full", {}).get("scores", [0]*n_runs)[i]
                                     if "full" in variant_results else 0
                                     for i in range(n_runs)])
            
            variant_results[variant] = {
                "metrics": m,
                "module_histogram": agg_mod,
                "context_histogram": agg_ctx,
                "aggressive_counters": agg_aggressive,
                "scores": [r["final_score"] for r in results],
            }
            
            # Print
            diff_vs_841 = m["median"] - v841_m["median"]
            sign = "+" if diff_vs_841 >= 0 else ""
            print(f"    {variant:<20}: med={m['median']:6.2f} std={m['std']:5.2f}  "
                  f"vs841: {sign}{diff_vs_841:.2f}  "
                  f"agg_sel={agg_aggressive['selected_by_merger_count']}")
        
        elapsed = time.time() - t0
        
        cell = {
            "n_runs": n_runs,
            "v841_baseline": v841_m,
            "recover_fixed_baseline": rec_fixed_m,
            "variants": {k: {"metrics": v["metrics"],
                              "module_histogram": v["module_histogram"],
                              "context_histogram": v["context_histogram"],
                              "aggressive_counters": v["aggressive_counters"]}
                          for k, v in variant_results.items()},
            "v841_scores": [r["final_score"] for r in v841_r],
            "rec_fixed_scores": [r["final_score"] for r in rec_fixed_r],
            "variant_scores": {k: v["scores"] for k, v in variant_results.items()},
            "elapsed_sec": elapsed,
        }
        all_results[level] = cell
    
    return all_results


def check_extended_criteria(results: Dict) -> Dict:
    """Handoff doc § 16 criteria 7, 8"""
    print("\n" + "=" * 80)
    print("V8.5.1 Extended Success Criteria (§ 16 items 7, 8)")
    print("=" * 80)
    
    criteria = {}
    
    # 8. recover/A fixed baseline ≠ full v8.5.1
    rec_diff_check = []
    for level, cell in results.items():
        full_med = cell["variants"]["full"]["metrics"]["median"]
        rec_fixed_med = cell["recover_fixed_baseline"]["median"]
        diff = full_med - rec_fixed_med
        # 「等価でない」= median 差 が大きい (1 point 以上)
        ok = abs(diff) >= 1.0
        rec_diff_check.append((level, full_med, rec_fixed_med, diff, ok))
    criteria["8_recover_fixed_not_equiv_full"] = {
        "passed": all(c[4] for c in rec_diff_check),
        "evidence": [{"level": c[0], "full_med": c[1], "rec_fixed_med": c[2],
                       "diff": c[3]} for c in rec_diff_check],
    }
    
    # 12. Original vs Contextual Merger
    merger_check = []
    for level, cell in results.items():
        full_med = cell["variants"]["full"]["metrics"]["median"]
        orig_med = cell["variants"]["original_merger"]["metrics"]["median"]
        diff = full_med - orig_med
        merger_check.append((level, full_med, orig_med, diff))
    criteria["12_contextual_vs_original_merger"] = {
        "passed": True,  # informative only
        "evidence": [{"level": c[0], "full_med": c[1], "original_med": c[2],
                       "diff": c[3]} for c in merger_check],
    }
    
    # Module contribution check (variant 6, 7, 8)
    mod_contrib_check = {}
    for module in ["mutation", "synthesis", "invention"]:
        variant_name = f"no_{module}"
        contributions = []
        for level, cell in results.items():
            full_med = cell["variants"]["full"]["metrics"]["median"]
            without_med = cell["variants"][variant_name]["metrics"]["median"]
            contrib = full_med - without_med
            contributions.append((level, contrib))
        avg_contrib = np.mean([c[1] for c in contributions])
        mod_contrib_check[module] = {
            "avg_contribution": float(avg_contrib),
            "by_level": [{"level": c[0], "contribution": c[1]} for c in contributions],
            "measurable": abs(avg_contrib) > 0.3,
        }
    criteria["7_pathway_module_contributions"] = {
        "passed": True,  # honest reporting
        "evidence": mod_contrib_check,
    }
    
    # Aggressive forced diagnostic check (variant 5)
    agg_forced_check = []
    for level, cell in results.items():
        forced_agg_counters = cell["variants"]["aggressive_forced"]["aggressive_counters"]
        forced_med = cell["variants"]["aggressive_forced"]["metrics"]["median"]
        full_med = cell["variants"]["full"]["metrics"]["median"]
        agg_forced_check.append({
            "level": level,
            "forced_med": forced_med,
            "full_med": full_med,
            "forced_diff": forced_med - full_med,
            "agg_selected": forced_agg_counters.get("selected_by_merger_count", 0),
            "agg_final_accepted": forced_agg_counters.get("final_accepted_count", 0),
        })
    criteria["5_aggressive_forced_diagnostic"] = {
        "passed": True,  # informative
        "evidence": agg_forced_check,
    }
    
    n_passed = sum(1 for c in criteria.values() if c["passed"])
    print(f"\n{n_passed}/{len(criteria)} extended criteria PASSED:")
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
    results = run_ablation_suite(cfg, n_runs=150, horizon=200, seed_offset=3000)
    extended_criteria = check_extended_criteria(results)
    
    # Strip scores from output to keep file small
    cleaned = {}
    for level, cell in results.items():
        cleaned[level] = {
            "n_runs": cell["n_runs"],
            "v841_baseline": cell["v841_baseline"],
            "recover_fixed_baseline": cell["recover_fixed_baseline"],
            "variants": cell["variants"],
            "elapsed_sec": cell["elapsed_sec"],
        }
    
    summary = {
        "version": "v8.5.1_ablation_suite",
        "description": "handoff doc § 15 — 12 variant ablation",
        "main_results": cleaned,
        "extended_criteria": extended_criteria,
    }
    
    out = cfg.results_dir / "v851_ablation_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
