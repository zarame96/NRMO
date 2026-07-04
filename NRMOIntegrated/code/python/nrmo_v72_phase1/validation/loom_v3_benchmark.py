"""
validation/loom_v3_benchmark.py

Loom (LoomEngine v3) 完全 benchmark.

Per Zarameさん 設計指示書 § 11:
  Engines:
    v8.4.1, v8.5.1, v9_minimal, ActiveCycle, UnifiedEngine,
    Meta_hybrid, Loom, recover_fixed
  Worlds: 3 × 3 levels = 9 cells
  Metrics: median, mean, std, p5, cvar, ruin_rate, Top3, oracle_gap, sparse histogram

Success goals:
  Top3 count: at least 5/9
  Best-per-cell loss: better than -20
  Drifting/mild: 14.6 → at least 30
  Chaotic/Noisy: retain v8.5.1-level
  Lower-tail: no degradation vs v8.4.1
  No recover-fixed collapse
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
                       use_contextual_merger=True,
                       enable_sociable_essence=False)  # per spec: default off
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
        if done:
            ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_meta(args):
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


def _run_loom(args):
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
        if done:
            ruined = True; break
    sparse = eng.get_sparse_summary()
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "mode_counts": dict(eng.stats["mode_counts"]),
             "primary_thread_counts": dict(eng.stats["primary_thread_counts"]),
             "world_type_counts": dict(eng.stats["world_type_counts"]),
             "context_counts": dict(eng.stats["context_counts"]),
             "mean_active": sparse.get("mean_active", 0),
             "max_active": sparse.get("max_active", 0),
             "emergency_triggered": eng.stats["emergency_triggered"],
             "throttle_triggered": eng.stats["throttle_triggered"],
             "ap_intervened": eng.stats["ap_intervened"],
             "qs_propagated": eng.stats["qs_propagated"],
             "qs_sigma_rejected": eng.stats["qs_verification_rejected"],
             "qs_boost_applied": eng.stats["qs_boost_applied"]}


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


def run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=13000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "moderate", "severe"]
    
    print("=" * 80)
    print("Loom (LoomEngine v3) Benchmark — per Zarameさん 設計指示書 § 11")
    print("=" * 80)
    print(f"  n_runs={n_runs}, seeds {seed_offset}-{seed_offset+n_runs-1}")
    
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
                "Meta_hybrid": _run_meta,
                "UnifiedEngine": _run_unified,
                "Loom": _run_loom,
                "recover": _run_recover_fixed,
            }
            
            results = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results[name] = {"metrics": compute_metrics(rs, n_runs),
                                  "scores": [r["final_score"] for r in rs]}
                if name == "Loom":
                    agg = {"mode_counts": {}, "primary_thread_counts": {},
                           "world_type_counts": {}, "context_counts": {},
                           "mean_active_list": [], "max_active": 0,
                           "emergency_total": 0, "throttle_total": 0,
                           "ap_total": 0, "qs_propagated_total": 0,
                           "qs_sigma_rejected_total": 0, "qs_boost_total": 0}
                    for r in rs:
                        for k in ["mode_counts", "primary_thread_counts",
                                   "world_type_counts", "context_counts"]:
                            for kk, vv in r.get(k, {}).items():
                                agg[k][kk] = agg[k].get(kk, 0) + vv
                        agg["mean_active_list"].append(r.get("mean_active", 0))
                        agg["max_active"] = max(agg["max_active"], r.get("max_active", 0))
                        agg["emergency_total"] += r.get("emergency_triggered", 0)
                        agg["throttle_total"] += r.get("throttle_triggered", 0)
                        agg["ap_total"] += r.get("ap_intervened", 0)
                        agg["qs_propagated_total"] += r.get("qs_propagated", 0)
                        agg["qs_sigma_rejected_total"] += r.get("qs_sigma_rejected", 0)
                        agg["qs_boost_total"] += r.get("qs_boost_applied", 0)
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
                      f"p5={m['p5']:6.2f} ruin={m['ruin_rate']:.0%}")
            
            # Loom details
            le = results["Loom"]["loom_extras"]
            print(f"  Loom sparse: mean_active={le['mean_active']:.2f}, max={le['max_active']}")
            print(f"  Loom modes: {le['mode_counts']}")
            print(f"  Loom worlds: {le['world_type_counts']}")
            print(f"  Loom safety: EG={le['emergency_total']}, Throttle={le['throttle_total']}, AP={le['ap_total']}")
            print(f"  Loom QS: prop={le['qs_propagated_total']}, "
                  f"sigma_rej={le['qs_sigma_rejected_total']}, "
                  f"boost={le['qs_boost_total']}")
            
            # Oracle gap analysis
            loom_med = results["Loom"]["metrics"]["median"]
            specialist_meds = {name: data["metrics"]["median"]
                                for name, data in results.items() if name != "Loom"}
            best_spec_name = max(specialist_meds, key=specialist_meds.get)
            best_spec_med = specialist_meds[best_spec_name]
            oracle_gap = best_spec_med - loom_med
            print(f"  Oracle gap: Loom {loom_med:.2f} vs best specialist {best_spec_name}({best_spec_med:.2f}) = {oracle_gap:+.2f}")
            
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "n_runs": n_runs,
                "engines": {k: {"metrics": v["metrics"]} for k, v in results.items()},
                "loom_extras": le,
                "oracle_gap": float(oracle_gap),
                "best_specialist": best_spec_name,
                "best_specialist_median": float(best_spec_med),
                "elapsed_sec": elapsed,
            }
    
    return all_results


def analyze(results):
    print("\n" + "=" * 80)
    print("Loom Cross-World Analysis (per spec § 8 Success Goals)")
    print("=" * 80)
    
    # Top 3 count
    top3_counts = {}
    loom_top3_cells = []
    best_per_cell_loss_total = 0.0
    
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = [(name, data["metrics"]["median"])
                        for name, data in cell["engines"].items()]
            entries.sort(key=lambda x: -x[1])
            for i, (name, med) in enumerate(entries[:3]):
                top3_counts[name] = top3_counts.get(name, 0) + 1
                if name == "Loom":
                    loom_top3_cells.append(f"{world}/{level}({i+1}位)")
            # Loom loss vs best per cell
            loom_med = cell["engines"]["Loom"]["metrics"]["median"]
            best_med = entries[0][1] if entries[0][0] != "Loom" else entries[1][1]
            best_per_cell_loss_total += min(0, loom_med - best_med)
    
    print("\n[Top 3 入りカウント (9 cells max)]")
    sorted_top = sorted(top3_counts.items(), key=lambda x: -x[1])
    for name, count in sorted_top:
        marker = "★" if name == "Loom" else " "
        print(f"  {marker} {name:<14}: {count}/9 cells")
    
    print(f"\n[Loom Top3 cells]: {loom_top3_cells}")
    print(f"\n[Loom Best-per-cell loss total]: {best_per_cell_loss_total:.2f}")
    print(f"  Target: better than -20 (UnifiedEngine -52.65)")
    
    # Per-world summary
    print("\n[Per-world Loom vs best specialist]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            gap = cell["oracle_gap"]
            ref = cell["best_specialist"]
            ref_score = cell["best_specialist_median"]
            loom = cell["engines"]["Loom"]["metrics"]["median"]
            sign = "+" if gap <= 0 else "-"
            print(f"  [{world}/{level}] Loom={loom:.2f} vs {ref}({ref_score:.2f}): gap={gap:+.2f}")
    
    # Drifting/mild specific check
    if "mild" in results.get("drifting", {}):
        drift_mild_loom = results["drifting"]["mild"]["engines"]["Loom"]["metrics"]["median"]
        print(f"\n[Drifting/mild Loom]: {drift_mild_loom:.2f} (target: >=30)")
    
    # Lower-tail check vs v8.4.1
    print("\n[Lower-tail safety vs v8.4.1]")
    p5_degraded = []
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            loom_p5 = cell["engines"]["Loom"]["metrics"]["p5"]
            v841_p5 = cell["engines"]["v8.4.1"]["metrics"]["p5"]
            if loom_p5 < v841_p5 - 1.0:
                p5_degraded.append(f"{world}/{level}: Loom={loom_p5:.2f} < v841={v841_p5:.2f}")
    if p5_degraded:
        print(f"  ⚠ degraded cells: {p5_degraded}")
    else:
        print("  ✅ no degradation")


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
    results = run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=13000)
    analyze(results)
    
    summary = {
        "version": "loom_v3_final",
        "description": "Loom (LoomEngine v3) per spec § 11",
        "main_results": results,
    }
    out = cfg.results_dir / "loom_v3_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
