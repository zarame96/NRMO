"""
validation/sociable_ablation_benchmark.py

Sociable Essence ablation benchmark.

Per Zarameさん 指示:
  案 C: default off, on/off 対決 (ablation 目的)

Engines × sociable on/off:
  - V851Engine
  - ActiveCycleEngine
  - UnifiedEngine
  - LoomEngineV2 (常に sociable 含む, 但し flag で disable)
  - V9_minimal (no sociable, reference)
  - recover_fixed (reference)

3 worlds × 2 levels × ~10 engines
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


# === V851 ===
def _run_v851_off(args):
    world_type, chaos, horizon, seed = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V851Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True,
                       use_strong_engine_full=True,
                       use_contextual_merger=True,
                       enable_sociable_essence=False)
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


def _run_v851_on(args):
    world_type, chaos, horizon, seed = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V851Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True,
                       use_strong_engine_full=True,
                       use_contextual_merger=True,
                       enable_sociable_essence=True)
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
    n_records = len(eng.failure_tracker.records) if eng.failure_tracker else 0
    n_rules = (sum(len(s) for s in eng.failure_tracker.residue_rules.values())
                if eng.failure_tracker else 0)
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "n_failure_records": n_records, "n_residue_rules": n_rules}


# === ActiveCycle ===
def _run_ac_off(args):
    world_type, chaos, horizon, seed = args
    from active_cycle_engine import ActiveCycleEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = ActiveCycleEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                              enable_sociable_essence=False)
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(observed)
        r, done, _ = world.step(d.action)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(d.action, r, sb, sa)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_ac_on(args):
    world_type, chaos, horizon, seed = args
    from active_cycle_engine import ActiveCycleEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = ActiveCycleEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                              enable_sociable_essence=True)
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(observed)
        r, done, _ = world.step(d.action)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(d.action, r, sb, sa)
        if done:
            ruined = True; break
    n_records = len(eng.failure_tracker.records) if eng.failure_tracker else 0
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "n_failure_records": n_records}


# === UnifiedEngine ===
def _run_u_off(args):
    world_type, chaos, horizon, seed = args
    from unified_engine import UnifiedEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = UnifiedEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                          enable_sociable_essence=False)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_u_on(args):
    world_type, chaos, horizon, seed = args
    from unified_engine import UnifiedEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = UnifiedEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                          enable_sociable_essence=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    n_records = len(eng.failure_tracker.records) if eng.failure_tracker else 0
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "n_failure_records": n_records}


# === LoomEngineV2 ===
def _run_loom_v2_off(args):
    world_type, chaos, horizon, seed = args
    from loom_engine_v2 import LoomEngineV2
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomEngineV2(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_failure_tracker=False,
                          use_canonical_dedup=False,
                          use_cycle_detector=False)
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(observed)
        r, done, _ = world.step(d.action)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(d.action, r, sb, sa)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_loom_v2_on(args):
    world_type, chaos, horizon, seed = args
    from loom_engine_v2 import LoomEngineV2
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomEngineV2(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_failure_tracker=True,
                          use_canonical_dedup=True,
                          use_cycle_detector=True)
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(observed)
        r, done, _ = world.step(d.action)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(d.action, r, sb, sa)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


# === V9 + recover_fixed (references) ===
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
    }


def run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=12000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "severe"]
    
    print("=" * 80)
    print("Sociable Essence Ablation Benchmark")
    print("=" * 80)
    print(f"  n_runs={n_runs}, seeds {seed_offset}-{seed_offset+n_runs-1}")
    print(f"  各 engine × sociable on/off の改善検証 (default off, ablation 目的)")
    
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
                "V851_off": _run_v851_off,
                "V851_on":  _run_v851_on,
                "AC_off":   _run_ac_off,
                "AC_on":    _run_ac_on,
                "U_off":    _run_u_off,
                "U_on":     _run_u_on,
                "Loom2_off":  _run_loom_v2_off,
                "Loom2_on":   _run_loom_v2_on,
                "V9_minimal": _run_v9,
                "recover":    _run_recover_fixed,
            }
            
            results = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results[name] = {"metrics": compute_metrics(rs, n_runs),
                                  "scores": [r["final_score"] for r in rs]}
                if name.endswith("_on"):
                    avg_records = float(np.mean([r.get("n_failure_records", 0) for r in rs]))
                    results[name]["avg_failure_records"] = avg_records
            
            elapsed = time.time() - t0
            
            # Print: paired comparison
            print(f"  {'Engine':<16} {'OFF':>8} {'ON':>8} {'diff':>8} {'p_value':>10}")
            print(f"  " + "-" * 60)
            from scipy.stats import wilcoxon
            
            for base in ["V851", "AC", "U", "Loom2"]:
                off_key = f"{base}_off"
                on_key = f"{base}_on"
                off_scores = np.array(results[off_key]["scores"])
                on_scores = np.array(results[on_key]["scores"])
                off_med = results[off_key]["metrics"]["median"]
                on_med = results[on_key]["metrics"]["median"]
                diff = float(np.median(on_scores - off_scores))
                try:
                    if not all(d == 0 for d in (on_scores - off_scores)):
                        _, p = wilcoxon(on_scores - off_scores, alternative="two-sided")
                    else:
                        p = 1.0
                except Exception:
                    p = float("nan")
                marker = "✓" if abs(diff) > 0.5 else ("~" if abs(diff) > 0.1 else " ")
                print(f"  {base:<16} {off_med:8.2f} {on_med:8.2f} {diff:+8.2f}{marker} {p:10.4f}")
            
            # References
            print(f"  {'V9_minimal':<16} {results['V9_minimal']['metrics']['median']:>8.2f}")
            print(f"  {'recover':<16} {results['recover']['metrics']['median']:>8.2f}")
            
            # Sociable mechanism activity
            print(f"  Sociable activity (failure records avg per run):")
            for on_key in ["V851_on", "AC_on", "U_on"]:
                avg = results[on_key].get("avg_failure_records", 0)
                print(f"    {on_key:<16}: {avg:.1f}")
            
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "n_runs": n_runs,
                "engines": {k: {"metrics": v["metrics"],
                                 "avg_failure_records": v.get("avg_failure_records", 0)}
                             for k, v in results.items()},
                "elapsed_sec": elapsed,
            }
    
    return all_results


def analyze(results):
    print("\n" + "=" * 80)
    print("Sociable Essence Ablation Analysis")
    print("=" * 80)
    
    # Across cells: sociable on - off diff per engine
    print("\n[Sociable Essence net effect across 6 cells]")
    for base in ["V851", "AC", "U", "Loom2"]:
        diffs = []
        for world in results.keys():
            for level in results[world].keys():
                off_m = results[world][level]["engines"][f"{base}_off"]["metrics"]["median"]
                on_m = results[world][level]["engines"][f"{base}_on"]["metrics"]["median"]
                diffs.append((f"{world}/{level}", on_m - off_m))
        avg_diff = float(np.mean([d[1] for d in diffs]))
        wins = sum(1 for d in diffs if d[1] > 0.1)
        losses = sum(1 for d in diffs if d[1] < -0.1)
        print(f"\n  {base}: avg diff = {avg_diff:+.2f}  wins={wins}/6, losses={losses}/6")
        for cell, diff in diffs:
            sign = "+" if diff >= 0 else ""
            print(f"    [{cell}] {sign}{diff:.2f}")


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
    results = run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=12000)
    analyze(results)
    
    summary = {
        "version": "sociable_ablation_v1",
        "description": "全 engine × sociable on/off ablation",
        "main_results": results,
    }
    
    out = cfg.results_dir / "sociable_ablation_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
