"""
validation/loom_v2_benchmark.py

LoomEngineV2 (with sociable essence) benchmark.

Engines:
  - v8.4.1 / v8.5.1 / v9_minimal / UnifiedEngine (references)
  - LoomEngine_v1 (no sociable)
  - LoomEngineV2_full (sociable: tracker + dedup + cycle)
  - LoomV2_no_tracker (ablation)
  - LoomV2_no_dedup (ablation)
  - LoomV2_no_cycle (ablation)
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


def _run_unified(args):
    world_type, chaos, horizon, seed = args
    from unified_engine import UnifiedEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = UnifiedEngine(rng_manager=RNGManager(master_seed=seed + 200000))
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_loom_v1(args):
    world_type, chaos, horizon, seed = args
    from loom_engine import LoomEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomEngine(rng_manager=RNGManager(master_seed=seed + 200000))
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_loom_v2_full(args):
    world_type, chaos, horizon, seed = args
    from loom_engine_v2 import LoomEngineV2
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomEngineV2(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_failure_tracker=True, use_canonical_dedup=True,
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
             "is_ruined": ruined, "completed_steps": world.state.t,
             "sociable_summary": eng.get_sociable_summary(),
             "thread_selected_counts": dict(eng.stats["thread_selected_counts"])}


def _run_loom_v2_no_tracker(args):
    world_type, chaos, horizon, seed = args
    from loom_engine_v2 import LoomEngineV2
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomEngineV2(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_failure_tracker=False, use_canonical_dedup=True,
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


def _run_loom_v2_no_dedup(args):
    world_type, chaos, horizon, seed = args
    from loom_engine_v2 import LoomEngineV2
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomEngineV2(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_failure_tracker=True, use_canonical_dedup=False,
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


def _run_loom_v2_no_cycle(args):
    world_type, chaos, horizon, seed = args
    from loom_engine_v2 import LoomEngineV2
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomEngineV2(rng_manager=RNGManager(master_seed=seed + 200000),
                          use_failure_tracker=True, use_canonical_dedup=True,
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


def run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=11000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "severe"]
    
    print("=" * 80)
    print("LoomEngineV2 Benchmark (with Sociable Essence)")
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
                "v8.4.1": _run_v841,
                "v8.5.1": _run_v851,
                "v9_minimal": _run_v9,
                "UnifiedEngine": _run_unified,
                "LoomEngine_v1": _run_loom_v1,
                "LoomV2_full": _run_loom_v2_full,
                "LoomV2_no_tracker": _run_loom_v2_no_tracker,
                "LoomV2_no_dedup": _run_loom_v2_no_dedup,
                "LoomV2_no_cycle": _run_loom_v2_no_cycle,
                "recover_fixed": _run_recover_fixed,
            }
            
            results = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results[name] = {"metrics": compute_metrics(rs, n_runs),
                                  "scores": [r["final_score"] for r in rs]}
                if name.startswith("LoomV2_"):
                    agg_soc = {"canonical_dedup": 0, "pre_rejected": 0,
                                "cycles_detected": 0, "stagnation_breaks": 0,
                                "failure_records": 0}
                    agg_thread = {}
                    for r in rs:
                        s = r.get("sociable_summary", {})
                        agg_soc["canonical_dedup"] += s.get("canonical_duplicates_removed", 0)
                        agg_soc["pre_rejected"] += s.get("pre_rejected_count", 0)
                        agg_soc["cycles_detected"] += s.get("cycles_detected", 0)
                        agg_soc["stagnation_breaks"] += s.get("stagnation_breaks", 0)
                        agg_soc["failure_records"] += s.get("failure_records", 0)
                        for t, c in r.get("thread_selected_counts", {}).items():
                            agg_thread[t] = agg_thread.get(t, 0) + c
                    results[name]["sociable_summary"] = agg_soc
                    results[name]["thread_histogram"] = agg_thread
            
            elapsed = time.time() - t0
            
            # Ranking
            ranking = [(name, data["metrics"]["median"]) for name, data in results.items()]
            ranking.sort(key=lambda x: -x[1])
            print(f"  Ranking (median):")
            for i, (name, med) in enumerate(ranking):
                marker = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "  "))
                m = results[name]["metrics"]
                print(f"    {marker} {name:<22}: med={med:6.2f} std={m['std']:5.2f} "
                      f"p5={m['p5']:6.2f} ruin={m['ruin_rate']:.0%}")
            
            # LoomV2 sociable stats
            if "LoomV2_full" in results:
                s = results["LoomV2_full"].get("sociable_summary", {})
                print(f"  LoomV2_full sociable: dedup={s['canonical_dedup']}, "
                      f"pre_rej={s['pre_rejected']}, cycles={s['cycles_detected']}, "
                      f"breaks={s['stagnation_breaks']}, fail_rec={s['failure_records']}")
                print(f"  LoomV2_full threads: {results['LoomV2_full'].get('thread_histogram', {})}")
            
            # LoomV2 vs LoomV1 paired diff
            v2_scores = np.array(results["LoomV2_full"]["scores"])
            v1_scores = np.array(results["LoomEngine_v1"]["scores"])
            v9_scores = np.array(results["v9_minimal"]["scores"])
            v851_scores = np.array(results["v8.5.1"]["scores"])
            
            from scipy.stats import wilcoxon
            try:
                _, p_v2_v1 = wilcoxon(v2_scores - v1_scores, alternative="two-sided")
                _, p_v2_v9 = wilcoxon(v2_scores - v9_scores, alternative="two-sided")
                _, p_v2_v851 = wilcoxon(v2_scores - v851_scores, alternative="two-sided")
            except Exception:
                p_v2_v1 = p_v2_v9 = p_v2_v851 = None
            
            print(f"  LoomV2 vs:")
            print(f"    LoomEngine_v1: {float(np.median(v2_scores - v1_scores)):+.2f}, "
                  f"p={p_v2_v1:.4f}" if p_v2_v1 else "")
            print(f"    v9_minimal:    {float(np.median(v2_scores - v9_scores)):+.2f}, "
                  f"p={p_v2_v9:.4f}" if p_v2_v9 else "")
            print(f"    v8.5.1:        {float(np.median(v2_scores - v851_scores)):+.2f}, "
                  f"p={p_v2_v851:.4f}" if p_v2_v851 else "")
            
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "n_runs": n_runs,
                "engines": {k: {"metrics": v["metrics"]} for k, v in results.items()},
                "loom_v2_sociable": results["LoomV2_full"].get("sociable_summary", {}),
                "loom_v2_threads": results["LoomV2_full"].get("thread_histogram", {}),
                "elapsed_sec": elapsed,
            }
    
    return all_results


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
    results = run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=11000)
    
    summary = {
        "version": "loom_v2_sociable",
        "description": "LoomEngineV2 with sociable essence vs others, 3 worlds × 2 levels",
        "main_results": results,
    }
    
    out = cfg.results_dir / "loom_v2_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
