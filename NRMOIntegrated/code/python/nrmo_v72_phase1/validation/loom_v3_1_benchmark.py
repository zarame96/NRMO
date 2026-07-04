"""
validation/loom_v3_1_benchmark.py

Loom v3.1 完全 benchmark.

LoomV31 (案 1-4 累積) vs LoomV3 (前) vs reference specialists.

9 cells (3 worlds × 3 levels) で:
  - v8.4.1, v8.5.1, v9_minimal, ActiveCycle, Meta_hybrid, UnifiedEngine
  - Loom (v3), Loom v3.1 (Enhanced)
  - recover_fixed
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
        d = eng.decide(world.observe())
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v851(args):
    world_type, chaos, horizon, seed = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V851Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True, use_strong_engine_full=True,
                       use_contextual_merger=True, enable_sociable_essence=False)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
        if done: ruined = True; break
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
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_ac(args):
    world_type, chaos, horizon, seed = args
    from active_cycle_engine import ActiveCycleEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = ActiveCycleEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                              enable_sociable_essence=False)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_loom_v3(args):
    world_type, chaos, horizon, seed = args
    from loom_v3 import Loom
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = Loom(rng_manager=RNGManager(master_seed=seed + 200000),
                 use_qs_essence=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "mode_counts": dict(eng.stats["mode_counts"])}


def _run_loom_v3_1(args):
    world_type, chaos, horizon, seed = args
    from loom_v3_1 import LoomV31
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomV31(rng_manager=RNGManager(master_seed=seed + 200000),
                     use_qs_essence=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done: ruined = True; break
    sparse = eng.get_sparse_summary()
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "mode_counts": dict(eng.stats["mode_counts"]),
             "world_type_counts": dict(eng.stats["world_type_counts"]),
             "drift_override_count": eng.stats["drift_override_count"],
             "drift_boost_count": eng.stats["drift_boost_count"],
             "mean_active": sparse.get("mean_active", 0),
             "emergency_triggered": eng.stats["emergency_triggered"]}


def _run_recover_fixed(args):
    world_type, chaos, horizon, seed = args
    world = _make_world(world_type, chaos, seed)
    ruined = False
    a = Action("recover", "A")
    for t in range(horizon):
        r, done, _ = world.step(a)
        if done: ruined = True; break
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
    }


def run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=14000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "moderate", "severe"]
    
    print("=" * 80)
    print("Loom v3.1 Benchmark (案 1-4 累積)")
    print("=" * 80)
    
    all_results = {}
    
    for world_type in worlds:
        print(f"\n{'='*60}\n  WORLD: {world_type.upper()}\n{'='*60}")
        all_results[world_type] = {}
        
        for level in levels:
            print(f"\n[{world_type}/{level}]")
            args = [(world_type, level, horizon, seed_offset + s) for s in range(n_runs)]
            
            t0 = time.time()
            engines = {
                "v8.4.1": _run_v841,
                "v8.5.1": _run_v851,
                "v9_minimal": _run_v9,
                "ActiveCycle": _run_ac,
                "Loom_v3": _run_loom_v3,
                "Loom_v3.1": _run_loom_v3_1,
                "recover": _run_recover_fixed,
            }
            
            results = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results[name] = {"metrics": compute_metrics(rs, n_runs),
                                  "scores": [r["final_score"] for r in rs]}
                if name == "Loom_v3.1":
                    agg = {"mode_counts": {}, "world_type_counts": {},
                            "drift_override_total": 0, "drift_boost_total": 0,
                            "mean_active_list": [], "emergency_total": 0}
                    for r in rs:
                        for k in ["mode_counts", "world_type_counts"]:
                            for kk, vv in r.get(k, {}).items():
                                agg[k][kk] = agg[k].get(kk, 0) + vv
                        agg["drift_override_total"] += r.get("drift_override_count", 0)
                        agg["drift_boost_total"] += r.get("drift_boost_count", 0)
                        agg["mean_active_list"].append(r.get("mean_active", 0))
                        agg["emergency_total"] += r.get("emergency_triggered", 0)
                    results[name]["loom_extras"] = agg
                    results[name]["loom_extras"]["mean_active"] = (
                        float(np.mean(agg["mean_active_list"])) if agg["mean_active_list"] else 0)
            
            elapsed = time.time() - t0
            
            # Ranking
            ranking = [(name, data["metrics"]["median"]) for name, data in results.items()]
            ranking.sort(key=lambda x: -x[1])
            print(f"  Ranking (median):")
            for i, (name, med) in enumerate(ranking):
                marker = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "  "))
                m = results[name]["metrics"]
                print(f"    {marker} {name:<14}: med={med:6.2f} std={m['std']:5.2f} "
                      f"p5={m['p5']:6.2f}")
            
            le = results["Loom_v3.1"].get("loom_extras", {})
            print(f"  Loom_v3.1: modes={le.get('mode_counts', {})}")
            print(f"    drift_override={le.get('drift_override_total', 0)}, "
                  f"drift_boost={le.get('drift_boost_total', 0)}, "
                  f"emergency={le.get('emergency_total', 0)}")
            print(f"    worlds={le.get('world_type_counts', {})}")
            
            # v3 vs v3.1 paired
            v3_scores = np.array(results["Loom_v3"]["scores"])
            v31_scores = np.array(results["Loom_v3.1"]["scores"])
            diff = float(np.median(v31_scores - v3_scores))
            print(f"  Loom_v3.1 vs Loom_v3: diff = {diff:+.2f}")
            
            # vs v9_minimal (key reference)
            v9_scores = np.array(results["v9_minimal"]["scores"])
            v31_vs_v9 = float(np.median(v31_scores - v9_scores))
            print(f"  Loom_v3.1 vs v9_minimal: {v31_vs_v9:+.2f}")
            
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "engines": {k: {"metrics": v["metrics"]} for k, v in results.items()},
                "loom_v31_extras": le,
                "v31_vs_v3": diff,
                "v31_vs_v9": v31_vs_v9,
                "elapsed_sec": elapsed,
            }
    
    return all_results


def analyze(results):
    print("\n" + "=" * 80)
    print("Loom v3.1 Analysis")
    print("=" * 80)
    
    # Top 3 per cell + count
    top3_counts = {}
    v31_top3_cells = []
    v3_top3_cells = []
    
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = [(name, data["metrics"]["median"])
                        for name, data in cell["engines"].items()]
            entries.sort(key=lambda x: -x[1])
            for i, (name, _) in enumerate(entries[:3]):
                top3_counts[name] = top3_counts.get(name, 0) + 1
                if name == "Loom_v3.1":
                    v31_top3_cells.append(f"{world}/{level}({i+1}位)")
                if name == "Loom_v3":
                    v3_top3_cells.append(f"{world}/{level}({i+1}位)")
    
    print("\n[Top 3 入りカウント]")
    for name, count in sorted(top3_counts.items(), key=lambda x: -x[1]):
        marker = "★" if name in ("Loom_v3", "Loom_v3.1") else " "
        print(f"  {marker} {name:<14}: {count}/9 cells")
    
    print(f"\n[Loom_v3.1 Top3 cells]: {v31_top3_cells}")
    print(f"[Loom_v3 Top3 cells]: {v3_top3_cells}")
    
    # Drifting specific check
    print("\n[Drifting performance]")
    for level in ["mild", "moderate", "severe"]:
        cell = results.get("drifting", {}).get(level)
        if cell:
            v31 = cell["engines"]["Loom_v3.1"]["metrics"]["median"]
            v3 = cell["engines"]["Loom_v3"]["metrics"]["median"]
            v9 = cell["engines"]["v9_minimal"]["metrics"]["median"]
            print(f"  drifting/{level}: v3.1={v31:.2f}, v3={v3:.2f}, v9={v9:.2f}, "
                  f"v3.1 vs v9 gap={v31-v9:+.2f}")
    
    # Best-per-cell loss
    v31_loss = 0.0
    v3_loss = 0.0
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            v31_med = cell["engines"]["Loom_v3.1"]["metrics"]["median"]
            v3_med = cell["engines"]["Loom_v3"]["metrics"]["median"]
            others = [(n, d["metrics"]["median"]) for n, d in cell["engines"].items()
                       if n not in ("Loom_v3", "Loom_v3.1")]
            best = max(others, key=lambda x: x[1])
            v31_loss += min(0, v31_med - best[1])
            v3_loss += min(0, v3_med - best[1])
    
    print(f"\n[Best-per-cell loss]")
    print(f"  Loom_v3:   {v3_loss:.2f}")
    print(f"  Loom_v3.1: {v31_loss:.2f}")
    print(f"  Target: better than -20 (UnifiedEngine -52.65)")


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
    results = run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=14000)
    analyze(results)
    
    summary = {
        "version": "loom_v3_1",
        "description": "Loom v3.1 全強化累積 (案 1-4)",
        "main_results": results,
    }
    out = cfg.results_dir / "loom_v3_1_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
