"""
validation/unified_engine_benchmark.py

UnifiedEngine final benchmark.

Compared engines:
  - v8.4.1 (frozen baseline)
  - v8.5.1 (ContextualMerger)
  - v9_minimal (引き算)
  - ActiveCycleEngine
  - Meta_hybrid (前の試み)
  - UnifiedEngine (全 system 内包)
  - UnifiedEngine_no_world_adaptive (ablation)
  - recover_fixed

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


def _make_world(world_type, chaos, seed):
    cfg = ChaosConfig.from_level(chaos)
    if world_type == "chaotic":
        return ChaoticWorld(cfg, seed=seed)
    elif world_type == "drifting":
        return DriftingWorld(cfg, seed=seed)
    elif world_type == "noisy":
        return NoisyObservationWorld(cfg, seed=seed)


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
        d = eng.decide(observed)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
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
        d = eng.decide(world.observe())
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v9(args):
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
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_active_cycle(args):
    world_type, chaos, horizon, seed = args
    from active_cycle_engine import ActiveCycleEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = ActiveCycleEngine(rng_manager=RNGManager(master_seed=seed + 200000))
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_meta_hybrid(args):
    world_type, chaos, horizon, seed = args
    from meta_engine import MetaEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = MetaEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                       mode="hybrid", min_streak=5)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_unified(args):
    world_type, chaos, horizon, seed = args
    from unified_engine import UnifiedEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = UnifiedEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_active_bias=True,
                          use_cyclic_feedback=True,
                          use_opportunity_expansion=True,
                          use_synthesis_default=True,
                          use_world_adaptive_weights=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "module_counts": dict(eng.stats["module_selection_counts"]),
             "world_type_counts": dict(eng.stats["world_type_counts"]),
             "world_adaptive_applied": eng.stats["world_adaptive_applied"],
             "active_bias_applied": eng.stats["active_bias_applied"],
             "opportunity_expanded": eng.stats["opportunity_expanded"],
             "aggressive_counters": eng.get_aggressive_counters()}


def _run_unified_no_world(args):
    """Ablation: UnifiedEngine without WorldAdaptiveWeighting"""
    world_type, chaos, horizon, seed = args
    from unified_engine import UnifiedEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = UnifiedEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_active_bias=True,
                          use_cyclic_feedback=True,
                          use_opportunity_expansion=True,
                          use_synthesis_default=True,
                          use_world_adaptive_weights=False)  # OFF
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


def run_benchmark(cfg, n_runs=120, horizon=200, seed_offset=9000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "moderate", "severe"]
    
    print("=" * 80)
    print("UnifiedEngine Final Benchmark")
    print("=" * 80)
    print(f"  n_runs={n_runs}, seeds {seed_offset}-{seed_offset+n_runs-1}")
    print(f"  Mission: 1 engine 内に全 system, 内部協調で最良結果")
    
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
                "v8.4.1": _run_v841,
                "v8.5.1": _run_v851,
                "v9_minimal": _run_v9,
                "ActiveCycle": _run_active_cycle,
                "Meta_hybrid": _run_meta_hybrid,
                "UnifiedEngine": _run_unified,
                "Unified_no_world": _run_unified_no_world,
                "recover_fixed": _run_recover_fixed,
            }
            
            results = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results[name] = {"metrics": compute_metrics(rs, n_runs),
                                  "scores": [r["final_score"] for r in rs]}
                if name == "UnifiedEngine":
                    agg_mod = {}
                    agg_world = {}
                    agg_wa = 0
                    agg_ab = 0
                    agg_oe = 0
                    agg_aggr = {"generated": 0, "selected": 0, "final": 0}
                    for r in rs:
                        for m, c in r.get("module_counts", {}).items():
                            agg_mod[m] = agg_mod.get(m, 0) + c
                        for w, c in r.get("world_type_counts", {}).items():
                            agg_world[w] = agg_world.get(w, 0) + c
                        agg_wa += r.get("world_adaptive_applied", 0)
                        agg_ab += r.get("active_bias_applied", 0)
                        agg_oe += r.get("opportunity_expanded", 0)
                        ac = r.get("aggressive_counters", {})
                        agg_aggr["generated"] += ac.get("generated_count", 0)
                        agg_aggr["selected"] += ac.get("selected_by_merger_count", 0)
                        agg_aggr["final"] += ac.get("final_accepted_count", 0)
                    results[name]["module_histogram"] = agg_mod
                    results[name]["world_type_histogram"] = agg_world
                    results[name]["world_adaptive_total"] = agg_wa
                    results[name]["active_bias_total"] = agg_ab
                    results[name]["opportunity_expanded_total"] = agg_oe
                    results[name]["aggressive_summary"] = agg_aggr
            
            elapsed = time.time() - t0
            
            # Ranking
            ranking = [(name, data["metrics"]["median"]) for name, data in results.items()]
            ranking.sort(key=lambda x: -x[1])
            print(f"  Ranking (median):")
            for i, (name, med) in enumerate(ranking):
                marker = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "  "))
                m = results[name]["metrics"]
                print(f"    {marker} {name:<18}: med={med:6.2f} std={m['std']:5.2f} "
                      f"p5={m['p5']:6.2f} ruin={m['ruin_rate']:.0%}")
            
            # UnifiedEngine details
            if "UnifiedEngine" in results:
                u = results["UnifiedEngine"]
                print(f"  UnifiedEngine stats:")
                print(f"    world_adaptive: {u['world_adaptive_total']}, "
                      f"active_bias: {u['active_bias_total']}, "
                      f"opp_exp: {u['opportunity_expanded_total']}")
                print(f"    World histogram: {u['world_type_histogram']}")
                print(f"    Module histogram: {u['module_histogram']}")
                print(f"    Aggressive: {u['aggressive_summary']}")
            
            # Pairwise diffs
            u_scores = np.array(results["UnifiedEngine"]["scores"])
            v841 = np.array(results["v8.4.1"]["scores"])
            v851 = np.array(results["v8.5.1"]["scores"])
            v9 = np.array(results["v9_minimal"]["scores"])
            ac = np.array(results["ActiveCycle"]["scores"])
            
            from scipy.stats import wilcoxon
            try:
                _, p_u_v841 = wilcoxon(u_scores - v841, alternative="two-sided")
                _, p_u_v851 = wilcoxon(u_scores - v851, alternative="two-sided")
                _, p_u_v9 = wilcoxon(u_scores - v9, alternative="two-sided")
                _, p_u_ac = wilcoxon(u_scores - ac, alternative="two-sided")
            except Exception:
                p_u_v841 = p_u_v851 = p_u_v9 = p_u_ac = None
            
            print(f"  Unified vs:")
            print(f"    v8.4.1:      {float(np.median(u_scores - v841)):+.2f}, p={p_u_v841:.4f}" if p_u_v841 else "")
            print(f"    v8.5.1:      {float(np.median(u_scores - v851)):+.2f}, p={p_u_v851:.4f}" if p_u_v851 else "")
            print(f"    v9_minimal:  {float(np.median(u_scores - v9)):+.2f}, p={p_u_v9:.4f}" if p_u_v9 else "")
            print(f"    ActiveCycle: {float(np.median(u_scores - ac)):+.2f}, p={p_u_ac:.4f}" if p_u_ac else "")
            
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "n_runs": n_runs,
                "engines": {k: {"metrics": v["metrics"]} for k, v in results.items()},
                "unified_extras": {
                    "module_histogram": results["UnifiedEngine"].get("module_histogram", {}),
                    "world_type_histogram": results["UnifiedEngine"].get("world_type_histogram", {}),
                    "world_adaptive_total": results["UnifiedEngine"].get("world_adaptive_total", 0),
                    "active_bias_total": results["UnifiedEngine"].get("active_bias_total", 0),
                    "opportunity_expanded_total": results["UnifiedEngine"].get("opportunity_expanded_total", 0),
                    "aggressive_summary": results["UnifiedEngine"].get("aggressive_summary", {}),
                },
                "elapsed_sec": elapsed,
            }
    
    return all_results


def analyze(results):
    print("\n" + "=" * 80)
    print("UnifiedEngine Cross-World Final Analysis")
    print("=" * 80)
    
    # Top 3 per cell
    print("\n[Top 3 per cell]")
    top_counts = {}
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = [(name, data["metrics"]["median"])
                        for name, data in cell["engines"].items()]
            entries.sort(key=lambda x: -x[1])
            print(f"  [{world}/{level}] " +
                  " | ".join(f"{i+1}.{name}({m:.1f})" for i, (name, m) in enumerate(entries[:3])))
            for name, _ in entries[:3]:
                top_counts[name] = top_counts.get(name, 0) + 1
    
    print(f"\n[Top 3 入りカウント (9 cells max)]")
    sorted_top = sorted(top_counts.items(), key=lambda x: -x[1])
    for name, count in sorted_top:
        print(f"  {name:<22}: {count}/9 cells")
    
    # UnifiedEngine vs individual best
    print("\n[UnifiedEngine vs best individual engine per cell]")
    u_total_loss = 0.0
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            u_score = cell["engines"]["UnifiedEngine"]["metrics"]["median"]
            individuals = [(name, data["metrics"]["median"])
                            for name, data in cell["engines"].items()
                            if name != "UnifiedEngine"]
            individuals.sort(key=lambda x: -x[1])
            best_name, best_score = individuals[0]
            diff = u_score - best_score
            u_total_loss += min(0, diff)
            print(f"  [{world}/{level}] U={u_score:.2f} vs best_indiv {best_name}({best_score:.2f}): {diff:+.2f}")
    print(f"\n  Total Unified loss vs best per cell: {u_total_loss:.2f}")
    
    # World adaptive ablation
    print("\n[World Adaptive Weights Contribution (Unified vs Unified_no_world)]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            u_with = cell["engines"]["UnifiedEngine"]["metrics"]["median"]
            u_without = cell["engines"]["Unified_no_world"]["metrics"]["median"]
            print(f"  [{world}/{level}] with={u_with:.2f}, without={u_without:.2f}, contribution={u_with - u_without:+.2f}")


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
    results = run_benchmark(cfg, n_runs=120, horizon=200, seed_offset=9000)
    analyze(results)
    
    summary = {
        "version": "unified_engine_final",
        "description": "UnifiedEngine vs all engines, 3 worlds",
        "main_results": results,
    }
    
    out = cfg.results_dir / "unified_engine_final_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
