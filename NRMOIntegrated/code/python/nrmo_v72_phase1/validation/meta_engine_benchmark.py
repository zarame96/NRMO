"""
validation/meta_engine_benchmark.py

MetaEngine の完全検証.

Engines compared:
  v71_pure, v8.4.1, v8.5.1, v9_minimal, ActiveCycleEngine, 
  MetaEngine (mode=hybrid), MetaEngine (mode=rule_based),
  MetaEngine (mode=performance), recover_fixed

3 worlds × 3 levels × 9 engines = 81 cells
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


def _run_meta(args):
    """Generic Meta runner with mode"""
    world_type, chaos, horizon, seed, mode = args
    from meta_engine import MetaEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    meta = MetaEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                        mode=mode, min_streak=5)
    
    engine_usage = {}
    world_type_counts = {}
    
    ruined = False
    for t in range(horizon):
        d = meta.decide(world.observe())
        engine_usage[d.active_engine] = engine_usage.get(d.active_engine, 0) + 1
        world_type_counts[d.world_type] = world_type_counts.get(d.world_type, 0) + 1
        r, done, _ = world.step(d.action)
        meta.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "engine_usage": engine_usage,
             "world_type_counts": world_type_counts,
             "switch_count": meta.engine_selector.switch_count}


def _run_meta_hybrid(args):
    world_type, chaos, horizon, seed = args
    return _run_meta((world_type, chaos, horizon, seed, "hybrid"))


def _run_meta_rule(args):
    world_type, chaos, horizon, seed = args
    return _run_meta((world_type, chaos, horizon, seed, "rule_based"))


def _run_meta_perf(args):
    world_type, chaos, horizon, seed = args
    return _run_meta((world_type, chaos, horizon, seed, "performance"))


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


def run_benchmark(cfg, n_runs=120, horizon=200, seed_offset=8000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "moderate", "severe"]
    
    print("=" * 80)
    print("MetaEngine Comprehensive Benchmark")
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
                "v9_minimal": _run_v9,
                "ActiveCycle": _run_active_cycle,
                "Meta_hybrid": _run_meta_hybrid,
                "Meta_rule": _run_meta_rule,
                "Meta_perf": _run_meta_perf,
                "recover_fixed": _run_recover_fixed,
            }
            
            results = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results[name] = {"metrics": compute_metrics(rs, n_runs),
                                  "scores": [r["final_score"] for r in rs]}
                if name.startswith("Meta_"):
                    # Engine usage aggregate
                    agg_usage = {}
                    agg_world = {}
                    total_switches = 0
                    for r in rs:
                        for e, c in r.get("engine_usage", {}).items():
                            agg_usage[e] = agg_usage.get(e, 0) + c
                        for w, c in r.get("world_type_counts", {}).items():
                            agg_world[w] = agg_world.get(w, 0) + c
                        total_switches += r.get("switch_count", 0)
                    results[name]["engine_usage"] = agg_usage
                    results[name]["world_type_counts"] = agg_world
                    results[name]["total_switches"] = total_switches
            
            elapsed = time.time() - t0
            
            # Ranking
            ranking = [(name, data["metrics"]["median"]) for name, data in results.items()]
            ranking.sort(key=lambda x: -x[1])
            print(f"  Ranking (median):")
            for i, (name, med) in enumerate(ranking):
                marker = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "  "))
                m = results[name]["metrics"]
                print(f"    {marker} {name:<16}: med={med:6.2f} std={m['std']:5.2f} "
                      f"p5={m['p5']:6.2f} ruin={m['ruin_rate']:.0%}")
            
            # Meta details
            for meta_name in ["Meta_hybrid", "Meta_rule", "Meta_perf"]:
                if meta_name in results and "engine_usage" in results[meta_name]:
                    print(f"  {meta_name} stats:")
                    print(f"    Engine usage: {results[meta_name]['engine_usage']}")
                    print(f"    World types: {results[meta_name]['world_type_counts']}")
                    print(f"    Total switches: {results[meta_name]['total_switches']}")
            
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "n_runs": n_runs,
                "engines": {k: {"metrics": v["metrics"]} for k, v in results.items()},
                "meta_extras": {
                    name: {
                        "engine_usage": results[name].get("engine_usage", {}),
                        "world_type_counts": results[name].get("world_type_counts", {}),
                        "total_switches": results[name].get("total_switches", 0),
                    } for name in ["Meta_hybrid", "Meta_rule", "Meta_perf"]
                    if name in results
                },
                "elapsed_sec": elapsed,
            }
    
    return all_results


def analyze(results):
    print("\n" + "=" * 80)
    print("MetaEngine Cross-World Analysis")
    print("=" * 80)
    
    # Top 3 per cell
    print("\n[Top 3 per cell]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = [(name, data["metrics"]["median"])
                        for name, data in cell["engines"].items()]
            entries.sort(key=lambda x: -x[1])
            print(f"  [{world}/{level}] " +
                  " | ".join(f"{i+1}.{name}({m:.1f})" for i, (name, m) in enumerate(entries[:3])))
    
    # Meta vs individual best per world
    print("\n[Meta_hybrid vs best individual engine per cell]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            meta_score = cell["engines"]["Meta_hybrid"]["metrics"]["median"]
            individuals = [(name, data["metrics"]["median"])
                            for name, data in cell["engines"].items()
                            if not name.startswith("Meta_")]
            individuals.sort(key=lambda x: -x[1])
            best_name, best_score = individuals[0]
            diff = meta_score - best_score
            print(f"  [{world}/{level}] Meta={meta_score:.2f} vs best_indiv {best_name}({best_score:.2f}): "
                  f"{diff:+.2f}")
    
    # Universal "best" engine count
    print("\n[Universal performance: 各 engine が何 cell で top 3 入りか]")
    top_counts = {}
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = [(name, data["metrics"]["median"])
                        for name, data in cell["engines"].items()]
            entries.sort(key=lambda x: -x[1])
            for name, _ in entries[:3]:
                top_counts[name] = top_counts.get(name, 0) + 1
    sorted_top = sorted(top_counts.items(), key=lambda x: -x[1])
    print(f"  Top 3 counts (9 cells max): {sorted_top}")


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
    results = run_benchmark(cfg, n_runs=120, horizon=200, seed_offset=8000)
    analyze(results)
    
    summary = {
        "version": "meta_engine_final",
        "description": "MetaEngine (全 engine 統合) vs individual engines, 3 worlds",
        "main_results": results,
    }
    
    out = cfg.results_dir / "meta_engine_final_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
