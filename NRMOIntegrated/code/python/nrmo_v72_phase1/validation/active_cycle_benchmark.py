"""
validation/active_cycle_benchmark.py

ActiveCycleEngine final benchmark.

Engines compared:
  - v71_pure (control)
  - v8.4.1 (frozen baseline)
  - v8.5.1 (ContextualMerger)
  - v9_minimal (引き算)
  - ActiveCycleEngine (Maximum + Active + Cyclic, 新)
  - ActiveCycle_no_active_bias (ablation)
  - ActiveCycle_no_synthesis_default (ablation)
  - recover_fixed (sanity)

3 worlds × 3 levels × 8 engines
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
from noisy_world import NoisyObservationWorld
from world_models import Action


def _make_world(world_type: str, chaos_level: str, seed: int):
    cfg = ChaosConfig.from_level(chaos_level)
    if world_type == "chaotic":
        return ChaoticWorld(cfg, seed=seed)
    elif world_type == "drifting":
        return DriftingWorld(cfg, seed=seed)
    elif world_type == "noisy":
        return NoisyObservationWorld(cfg, seed=seed)
    raise ValueError(f"Unknown world: {world_type}")


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
            ruined = True; break
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
        observed = world.observe()
        sb = {"R": observed.R, "E": observed.E, "G": observed.G,
              "O": observed.O, "K": observed.K, "X": observed.X}
        d = eng.decide(observed)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        obs2 = world.observe()
        sa = {"R": obs2.R, "E": obs2.E, "G": obs2.G,
              "O": obs2.O, "K": obs2.K, "X": obs2.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True; break
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
                       use_contextual_merger=True)
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        d = eng.decide(observed)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "module_counts": dict(eng.stats["module_selection_counts"])}


def _run_v9_minimal(args):
    world_type, chaos, horizon, seed = args
    from v9_minimal_engine import V9MinimalEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V9MinimalEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                            use_synthesis=True, use_emergency_guard=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "synthesis_selected": eng.stats["synthesis_selected"]}


def _run_active_cycle(args):
    world_type, chaos, horizon, seed = args
    from active_cycle_engine import ActiveCycleEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = ActiveCycleEngine(
        rng_manager=RNGManager(master_seed=seed + 200000),
        use_active_bias=True,
        use_cyclic_feedback=True,
        use_opportunity_expansion=True,
        use_synthesis_default=True,
    )
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "active_bias_applied": eng.stats["active_bias_applied"],
             "opportunity_expanded": eng.stats["opportunity_expanded"],
             "synthesis_default_used": eng.stats["synthesis_default_used"],
             "active_action_count": eng.stats["active_action_count"],
             "passive_action_count": eng.stats["passive_action_count"],
             "module_counts": dict(eng.stats["module_selection_counts"]),
             "context_counts": dict(eng.stats["context_counts"]),
             "aggressive_counters": eng.get_aggressive_counters()}


def _run_active_cycle_no_bias(args):
    world_type, chaos, horizon, seed = args
    from active_cycle_engine import ActiveCycleEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = ActiveCycleEngine(
        rng_manager=RNGManager(master_seed=seed + 200000),
        use_active_bias=False,  # ablation
        use_cyclic_feedback=True,
        use_opportunity_expansion=True,
        use_synthesis_default=True,
    )
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_active_cycle_no_synthesis_default(args):
    world_type, chaos, horizon, seed = args
    from active_cycle_engine import ActiveCycleEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = ActiveCycleEngine(
        rng_manager=RNGManager(master_seed=seed + 200000),
        use_active_bias=True,
        use_cyclic_feedback=True,
        use_opportunity_expansion=True,
        use_synthesis_default=False,  # ablation
    )
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_recover_fixed(args):
    world_type, chaos, horizon, seed = args
    world = _make_world(world_type, chaos, seed)
    ruined = False
    a = Action("recover", "A")
    for t in range(horizon):
        r, done, _ = world.step(a)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def compute_metrics(rs, n_runs):
    scores = np.array([r["final_score"] for r in rs])
    sorted_s = np.sort(scores)
    n_bot = max(1, n_runs // 10)
    return {
        "median": float(np.median(scores)),
        "mean": float(np.mean(scores)),
        "std": float(np.std(scores)),
        "p5": float(np.percentile(scores, 5)),
        "cvar": float(np.mean(sorted_s[:n_bot])),
        "ruin_rate": float(np.mean([r["is_ruined"] for r in rs])),
        "median_steps": float(np.median([r["completed_steps"] for r in rs])),
    }


def run_benchmark(cfg, n_runs=150, horizon=200, seed_offset=7000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "moderate", "severe"]
    
    print("=" * 80)
    print("ActiveCycleEngine — 3 World Final Benchmark")
    print("=" * 80)
    print(f"  n_runs={n_runs}, seeds {seed_offset}-{seed_offset+n_runs-1}")
    
    all_results = {}
    
    for world_type in worlds:
        print(f"\n{'='*60}")
        print(f"  WORLD: {world_type.upper()}")
        print(f"{'='*60}")
        all_results[world_type] = {}
        
        for level in levels:
            print(f"\n[{world_type}/{level}]")
            args = [(world_type, level, horizon, seed_offset + s) for s in range(n_runs)]
            
            t0 = time.time()
            engines = {
                "v71_pure": _run_v71,
                "v8.4.1": _run_v841,
                "v8.5.1": _run_v851,
                "v9_minimal": _run_v9_minimal,
                "ActiveCycle_full": _run_active_cycle,
                "AC_no_active_bias": _run_active_cycle_no_bias,
                "AC_no_syn_default": _run_active_cycle_no_synthesis_default,
                "recover_fixed": _run_recover_fixed,
            }
            
            results = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results[name] = {"metrics": compute_metrics(rs, n_runs),
                                  "scores": [r["final_score"] for r in rs]}
                if name == "ActiveCycle_full":
                    bias_total = sum(r.get("active_bias_applied", 0) for r in rs)
                    opp_total = sum(r.get("opportunity_expanded", 0) for r in rs)
                    syn_total = sum(r.get("synthesis_default_used", 0) for r in rs)
                    active_total = sum(r.get("active_action_count", 0) for r in rs)
                    passive_total = sum(r.get("passive_action_count", 0) for r in rs)
                    agg_mod = {}
                    agg_ctx = {}
                    agg_aggr = {"generated": 0, "selected": 0, "final": 0}
                    for r in rs:
                        for m, c in r.get("module_counts", {}).items():
                            agg_mod[m] = agg_mod.get(m, 0) + c
                        for ctx, c in r.get("context_counts", {}).items():
                            agg_ctx[ctx] = agg_ctx.get(ctx, 0) + c
                        ac = r.get("aggressive_counters", {})
                        agg_aggr["generated"] += ac.get("generated_count", 0)
                        agg_aggr["selected"] += ac.get("selected_by_merger_count", 0)
                        agg_aggr["final"] += ac.get("final_accepted_count", 0)
                    results[name]["active_bias_total"] = bias_total
                    results[name]["opportunity_expanded_total"] = opp_total
                    results[name]["synthesis_default_total"] = syn_total
                    results[name]["active_action_total"] = active_total
                    results[name]["passive_action_total"] = passive_total
                    results[name]["module_histogram"] = agg_mod
                    results[name]["context_histogram"] = agg_ctx
                    results[name]["aggressive_summary"] = agg_aggr
            
            elapsed = time.time() - t0
            
            # Print
            ranking = [(name, data["metrics"]["median"]) for name, data in results.items()]
            ranking.sort(key=lambda x: -x[1])
            print(f"  Ranking (median score):")
            for i, (name, med) in enumerate(ranking):
                marker = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "  "))
                m = results[name]["metrics"]
                print(f"    {marker} {name:<22}: med={med:6.2f} std={m['std']:5.2f} "
                      f"p5={m['p5']:6.2f} ruin={m['ruin_rate']:.0%}")
            
            if "ActiveCycle_full" in results:
                ac = results["ActiveCycle_full"]
                print(f"  ActiveCycle stats:")
                print(f"    active_bias_applied: {ac['active_bias_total']}")
                print(f"    opportunity_expanded: {ac['opportunity_expanded_total']}")
                print(f"    synthesis_default_used: {ac['synthesis_default_total']}")
                print(f"    active/passive actions: {ac['active_action_total']}/{ac['passive_action_total']}")
                print(f"    module histogram: {ac['module_histogram']}")
                print(f"    context histogram: {ac['context_histogram']}")
                print(f"    aggressive: {ac['aggressive_summary']}")
            
            # Paired vs key competitors
            ac_scores = np.array(results["ActiveCycle_full"]["scores"])
            v841_scores = np.array(results["v8.4.1"]["scores"])
            v851_scores = np.array(results["v8.5.1"]["scores"])
            v9_scores = np.array(results["v9_minimal"]["scores"])
            
            from scipy.stats import wilcoxon
            try:
                _, p_ac_vs_841 = wilcoxon(ac_scores - v841_scores, alternative="two-sided")
                _, p_ac_vs_851 = wilcoxon(ac_scores - v851_scores, alternative="two-sided")
                _, p_ac_vs_v9 = wilcoxon(ac_scores - v9_scores, alternative="two-sided")
            except Exception:
                p_ac_vs_841 = p_ac_vs_851 = p_ac_vs_v9 = None
            
            print(f"  AC vs v8.4.1: diff={np.median(ac_scores - v841_scores):+.2f}, "
                  f"p={p_ac_vs_841:.4f}" if p_ac_vs_841 else "n/a")
            print(f"  AC vs v8.5.1: diff={np.median(ac_scores - v851_scores):+.2f}, "
                  f"p={p_ac_vs_851:.4f}" if p_ac_vs_851 else "n/a")
            print(f"  AC vs v9_minimal: diff={np.median(ac_scores - v9_scores):+.2f}, "
                  f"p={p_ac_vs_v9:.4f}" if p_ac_vs_v9 else "n/a")
            print(f"  ({elapsed:.0f}s)")
            
            cell_save = {
                "n_runs": n_runs,
                "engines": {k: {"metrics": v["metrics"]} for k, v in results.items()},
                "ac_extras": {
                    k: results["ActiveCycle_full"].get(k)
                    for k in ["active_bias_total", "opportunity_expanded_total",
                              "synthesis_default_total", "active_action_total",
                              "passive_action_total", "module_histogram",
                              "context_histogram", "aggressive_summary"]
                },
                "paired_ac_vs_841": {
                    "median_diff": float(np.median(ac_scores - v841_scores)),
                    "p": float(p_ac_vs_841) if p_ac_vs_841 else None,
                },
                "paired_ac_vs_851": {
                    "median_diff": float(np.median(ac_scores - v851_scores)),
                    "p": float(p_ac_vs_851) if p_ac_vs_851 else None,
                },
                "paired_ac_vs_v9": {
                    "median_diff": float(np.median(ac_scores - v9_scores)),
                    "p": float(p_ac_vs_v9) if p_ac_vs_v9 else None,
                },
                "elapsed_sec": elapsed,
            }
            all_results[world_type][level] = cell_save
    
    return all_results


def analyze(results):
    print("\n" + "=" * 80)
    print("ActiveCycleEngine Cross-World Final Analysis")
    print("=" * 80)
    
    # Engine ranking per world/level
    print("\n[Top 3 Engine per Cell]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = [(name, data["metrics"]["median"])
                        for name, data in cell["engines"].items()]
            entries.sort(key=lambda x: -x[1])
            print(f"  [{world}/{level}] " + 
                  " | ".join(f"{i+1}.{name}({m:.1f})" for i, (name, m) in enumerate(entries[:3])))
    
    # ActiveCycle vs main competitors
    print("\n[ActiveCycle vs v8.4.1 / v8.5.1 / v9_minimal]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            ac = cell["engines"]["ActiveCycle_full"]["metrics"]["median"]
            v841 = cell["engines"]["v8.4.1"]["metrics"]["median"]
            v851 = cell["engines"]["v8.5.1"]["metrics"]["median"]
            v9 = cell["engines"]["v9_minimal"]["metrics"]["median"]
            print(f"  [{world}/{level}] AC={ac:.2f}  vs841={ac-v841:+.2f}  "
                  f"vs851={ac-v851:+.2f}  vs9={ac-v9:+.2f}")
    
    # ActiveCycle ablation
    print("\n[ActiveCycle ablation (full vs -active_bias vs -synthesis_default)]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            full = cell["engines"]["ActiveCycle_full"]["metrics"]["median"]
            no_bias = cell["engines"]["AC_no_active_bias"]["metrics"]["median"]
            no_syn = cell["engines"]["AC_no_syn_default"]["metrics"]["median"]
            print(f"  [{world}/{level}] full={full:.2f}  "
                  f"-active_bias={no_bias:.2f}({full-no_bias:+.2f})  "
                  f"-syn_default={no_syn:.2f}({full-no_syn:+.2f})")


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
    results = run_benchmark(cfg, n_runs=150, horizon=200, seed_offset=7000)
    analyze(results)
    
    summary = {
        "version": "active_cycle_final",
        "description": "ActiveCycleEngine vs all engines in 3 worlds",
        "main_results": results,
    }
    
    out = cfg.results_dir / "active_cycle_final_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
