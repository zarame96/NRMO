"""
validation/loom_v3_2_tuned_benchmark.py

Loom v3.2.1 (tuned) 完全 benchmark.

3 修正 (threshold + SevereCycle 厳格化 + FF intervention 優先順序) の効果検証.
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
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_loom_v3_2(args):
    world_type, chaos, horizon, seed = args
    from loom_v3_2 import LoomV32
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomV32(rng_manager=RNGManager(master_seed=seed + 200000),
                     use_qs_essence=True,
                     enable_failure_face_intervention=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_loom_v3_2_1(args):
    """Loom v3.2.1 (tuned)"""
    world_type, chaos, horizon, seed = args
    from loom_v3_2_tuned import LoomV32Tuned
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomV32Tuned(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_qs_essence=True,
                          enable_failure_face_intervention=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "mode_counts": dict(eng.stats["mode_counts"]),
             "hard_drift_count": eng.stats["hard_drift_count"],
             "soft_drift_count": eng.stats["soft_drift_count"],
             "ff_intervention_count": eng.stats["failure_face_intervention_count"],
             "merger_bypass_count": eng.stats["contextual_merger_bypass_count"]}


def _run_loom_v3_2_1_ff_off(args):
    """Loom v3.2.1 with FF intervention OFF"""
    world_type, chaos, horizon, seed = args
    from loom_v3_2_tuned import LoomV32Tuned
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomV32Tuned(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_qs_essence=True,
                          enable_failure_face_intervention=False)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_recover(args):
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
        "ruin_rate": float(np.mean([r["is_ruined"] for r in rs])),
    }


def run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=16000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "moderate", "severe"]
    
    print("=" * 80)
    print("Loom v3.2.1 (Tuned) Benchmark")
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
                "Loom_v3.1": _run_loom_v3_1,
                "Loom_v3.2": _run_loom_v3_2,
                "Loom_v3.2.1": _run_loom_v3_2_1,
                "Loom_v3.2.1_ffoff": _run_loom_v3_2_1_ff_off,
                "recover": _run_recover,
            }
            
            results = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results[name] = {"metrics": compute_metrics(rs, n_runs),
                                  "scores": [r["final_score"] for r in rs]}
                if name == "Loom_v3.2.1":
                    agg = {"mode_counts": {}, "hard_drift_total": 0,
                            "soft_drift_total": 0, "ff_intervention_total": 0,
                            "merger_bypass_total": 0}
                    for r in rs:
                        for k, v in r.get("mode_counts", {}).items():
                            agg["mode_counts"][k] = agg["mode_counts"].get(k, 0) + v
                        agg["hard_drift_total"] += r.get("hard_drift_count", 0)
                        agg["soft_drift_total"] += r.get("soft_drift_count", 0)
                        agg["ff_intervention_total"] += r.get("ff_intervention_count", 0)
                        agg["merger_bypass_total"] += r.get("merger_bypass_count", 0)
                    results[name]["v321_extras"] = agg
            
            elapsed = time.time() - t0
            
            # Ranking
            ranking = [(name, data["metrics"]["median"]) for name, data in results.items()]
            ranking.sort(key=lambda x: -x[1])
            print(f"  Ranking (median):")
            for i, (name, med) in enumerate(ranking):
                marker = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "  "))
                m = results[name]["metrics"]
                print(f"    {marker} {name:<18}: med={med:6.2f} std={m['std']:5.2f} "
                      f"p5={m['p5']:6.2f}")
            
            # v3.2.1 details
            le = results["Loom_v3.2.1"].get("v321_extras", {})
            print(f"  Loom_v3.2.1:")
            print(f"    Modes: {le.get('mode_counts', {})}")
            print(f"    HardDrift={le.get('hard_drift_total', 0)}, "
                  f"SoftDrift={le.get('soft_drift_total', 0)}, "
                  f"FF_int={le.get('ff_intervention_total', 0)}, "
                  f"Bypass={le.get('merger_bypass_total', 0)}")
            
            # Paired
            v321 = np.array(results["Loom_v3.2.1"]["scores"])
            v32 = np.array(results["Loom_v3.2"]["scores"])
            v31 = np.array(results["Loom_v3.1"]["scores"])
            v9 = np.array(results["v9_minimal"]["scores"])
            
            print(f"  v3.2.1 vs v3.2: {float(np.median(v321 - v32)):+.2f}")
            print(f"  v3.2.1 vs v3.1: {float(np.median(v321 - v31)):+.2f}")
            print(f"  v3.2.1 vs v9_minimal: {float(np.median(v321 - v9)):+.2f}")
            
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "engines": {k: {"metrics": v["metrics"]} for k, v in results.items()},
                "v321_extras": le,
                "elapsed_sec": elapsed,
            }
    
    return all_results


def analyze(results):
    print("\n" + "=" * 80)
    print("Loom v3.2.1 Analysis")
    print("=" * 80)
    
    top3_counts = {}
    v321_top3 = []
    v31_top3 = []
    
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = [(name, data["metrics"]["median"])
                        for name, data in cell["engines"].items()]
            entries.sort(key=lambda x: -x[1])
            for i, (name, _) in enumerate(entries[:3]):
                top3_counts[name] = top3_counts.get(name, 0) + 1
                if name == "Loom_v3.2.1":
                    v321_top3.append(f"{world}/{level}({i+1}位)")
                if name == "Loom_v3.1":
                    v31_top3.append(f"{world}/{level}({i+1}位)")
    
    print("\n[Top 3 入りカウント]")
    for name, count in sorted(top3_counts.items(), key=lambda x: -x[1]):
        marker = "★" if name.startswith("Loom") else " "
        print(f"  {marker} {name:<22}: {count}/9 cells")
    
    print(f"\n[Loom_v3.2.1 Top3]: {v321_top3}")
    print(f"[Loom_v3.1 Top3]: {v31_top3}")
    
    # 成功条件
    v321_count = top3_counts.get("Loom_v3.2.1", 0)
    
    # Best-per-cell loss
    v321_loss = 0.0
    v31_loss = 0.0
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            v321_med = cell["engines"]["Loom_v3.2.1"]["metrics"]["median"]
            v31_med = cell["engines"]["Loom_v3.1"]["metrics"]["median"]
            others = [(n, d["metrics"]["median"]) for n, d in cell["engines"].items()
                       if not n.startswith("Loom")]
            best = max(others, key=lambda x: x[1])
            v321_loss += min(0, v321_med - best[1])
            v31_loss += min(0, v31_med - best[1])
    
    print(f"\n[成功条件 (仕様 § 9)]")
    print(f"  {'✅' if v321_count >= 7 else '❌'} 1. Top3 ≥ 7/9: 実績 {v321_count}/9")
    
    dm = results.get("drifting", {}).get("mild")
    if dm:
        dm_v321 = dm["engines"]["Loom_v3.2.1"]["metrics"]["median"]
        dm_v31 = dm["engines"]["Loom_v3.1"]["metrics"]["median"]
        mark = "✅" if dm_v321 >= 25 else "❌"
        print(f"  {mark} 2. Drifting/mild ≥ 25: 実績 {dm_v321:.2f} (v3.1: {dm_v31:.2f})")
    
    dmod = results.get("drifting", {}).get("moderate")
    if dmod:
        dmod_v321 = dmod["engines"]["Loom_v3.2.1"]["metrics"]["median"]
        dmod_v31 = dmod["engines"]["Loom_v3.1"]["metrics"]["median"]
        mark = "✅" if dmod_v321 >= 13 else "❌"
        print(f"  {mark} 3. Drifting/moderate ≥ 13: 実績 {dmod_v321:.2f} (v3.1: {dmod_v31:.2f})")
    
    mark = "✅" if v321_loss > -30 else "❌"
    print(f"  {mark} 4. Best-per-cell loss > -30: 実績 {v321_loss:.2f} (v3.1: {v31_loss:.2f})")
    
    # Drifting trajectory
    print("\n[Drifting Performance]")
    for level in ["mild", "moderate", "severe"]:
        cell = results.get("drifting", {}).get(level)
        if cell:
            v321 = cell["engines"]["Loom_v3.2.1"]["metrics"]["median"]
            v32 = cell["engines"]["Loom_v3.2"]["metrics"]["median"]
            v31 = cell["engines"]["Loom_v3.1"]["metrics"]["median"]
            v9 = cell["engines"]["v9_minimal"]["metrics"]["median"]
            print(f"  drifting/{level}: v3.1={v31:.2f} → v3.2={v32:.2f} → v3.2.1={v321:.2f}, "
                  f"v9={v9:.2f}")


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
    results = run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=16000)
    analyze(results)
    
    summary = {
        "version": "loom_v3_2_1",
        "description": "Loom v3.2.1 tuned (threshold + SevereCycle 厳格化 + FF priority)",
        "main_results": results,
    }
    out = cfg.results_dir / "loom_v3_2_1_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
