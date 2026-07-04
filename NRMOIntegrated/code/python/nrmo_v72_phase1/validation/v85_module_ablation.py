"""
validation/v85_module_ablation.py

Module ablation: StrongEngineΩfull の各 module を個別 OFF にして寄与度を測る.

Modules:
  1. DefensiveCandidate
  2. RecoveryCandidate
  3. ExplorationCandidate
  4. MutationPathway
  5. SynthesisPathway
  6. InventionPathway
  7. AggressiveEngineSubmodule

Configurations:
  baseline_v841: v8.4.1 (StrongEngine OFF) — reference
  full:          v8.5 all ON
  minus_X:       v8.5 with module X OFF (7 variants)

Honest goal:
  Identify which module(s) actually drive the improvement
  observed in v8.5 over v8.4.1.
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


def _run_v85_config(args):
    chaos, horizon, seed, module_config = args
    from v85_engine import V85Engine
    from rng_manager import RNGManager
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
    eng = V85Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                      use_active_pattern=True,
                      use_strong_engine_full=True,
                      module_config=module_config)
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


def run_ablation(cfg, n_runs=150, horizon=200, seed_offset=1500):
    """各 module 個別 OFF で測定 (mild/moderate/severe に絞る)"""
    
    # 改善が大きい chaos level で測定
    levels = ["mild", "moderate", "severe"]
    
    MODULES = ["defensive", "recovery", "exploration", 
                 "mutation", "synthesis", "invention", "aggressive"]
    
    ALL_ON = {m: True for m in MODULES}
    ALL_OFF = {m: False for m in MODULES}
    
    print("=" * 80)
    print("V8.5 Module Ablation — 真の改善 source を特定")
    print("=" * 80)
    print(f"  n_runs={n_runs}, seed range {seed_offset}-{seed_offset+n_runs-1}")
    print(f"  chaos levels: {levels}")
    print(f"  Modules to test: {MODULES}")
    
    all_results = {}
    
    for level in levels:
        print(f"\n[{level.upper()}]")
        args_base = [(level, horizon, seed_offset + s) for s in range(n_runs)]
        
        # baseline: v8.4.1
        print("  Running v8.4.1...")
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
            v841_r = list(ex.map(_run_v841, args_base))
        v841_med = float(np.median([r["final_score"] for r in v841_r]))
        v841_std = float(np.std([r["final_score"] for r in v841_r]))
        print(f"    v8.4.1: median={v841_med:.2f}, std={v841_std:.2f}")
        
        # full: v8.5 all ON
        print("  Running v8.5 (all ON)...")
        args_full = [(level, horizon, seed_offset + s, ALL_ON) for s in range(n_runs)]
        with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
            v85_full_r = list(ex.map(_run_v85_config, args_full))
        v85_full_med = float(np.median([r["final_score"] for r in v85_full_r]))
        v85_full_std = float(np.std([r["final_score"] for r in v85_full_r]))
        print(f"    v8.5 full: median={v85_full_med:.2f}, std={v85_full_std:.2f} "
              f"(full vs v8.4.1: +{v85_full_med - v841_med:.2f})")
        
        # Each module OFF
        per_module = {}
        for mod in MODULES:
            module_config = dict(ALL_ON)
            module_config[mod] = False  # turn this one OFF
            
            args_mod = [(level, horizon, seed_offset + s, module_config) for s in range(n_runs)]
            with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                results = list(ex.map(_run_v85_config, args_mod))
            
            scores = [r["final_score"] for r in results]
            med = float(np.median(scores))
            std = float(np.std(scores))
            
            # Contribution = full - (minus_this) = この module の寄与
            contribution = v85_full_med - med
            
            per_module[mod] = {
                "median_when_off": med,
                "std_when_off": std,
                "contribution_to_full": contribution,
                "vs_v841": med - v841_med,
            }
            sign = "+" if contribution >= 0 else ""
            print(f"    -{mod:<12}: med={med:6.2f} std={std:5.2f}  "
                  f"contribution: {sign}{contribution:.2f}  "
                  f"vs v841: {med - v841_med:+.2f}")
        
        elapsed = time.time() - t0
        
        cell = {
            "n_runs": n_runs,
            "horizon": horizon,
            "v841_median": v841_med,
            "v841_std": v841_std,
            "v85_full_median": v85_full_med,
            "v85_full_std": v85_full_std,
            "v85_full_vs_v841": v85_full_med - v841_med,
            "per_module": per_module,
            "elapsed_sec": elapsed,
        }
        all_results[level] = cell
    
    return all_results


def print_contribution_summary(results):
    """Module 寄与度 ranking"""
    print("\n" + "=" * 80)
    print("Module Contribution Summary (Higher = More Important)")
    print("=" * 80)
    
    MODULES = ["defensive", "recovery", "exploration",
                 "mutation", "synthesis", "invention", "aggressive"]
    
    for level, cell in results.items():
        print(f"\n[{level.upper()}] v8.4.1: {cell['v841_median']:.2f}, "
              f"v8.5 full: {cell['v85_full_median']:.2f} "
              f"(improvement: {cell['v85_full_vs_v841']:+.2f})")
        
        contributions = [(mod, cell["per_module"][mod]["contribution_to_full"])
                          for mod in MODULES]
        contributions.sort(key=lambda x: -x[1])
        
        print(f"  Module contributions (full - minus_X):")
        for mod, contrib in contributions:
            bar = "█" * max(0, int(contrib * 2))
            sign = "+" if contrib >= 0 else ""
            print(f"    {mod:<12}: {sign}{contrib:6.2f}  {bar}")


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
    results = run_ablation(cfg, n_runs=150, horizon=200, seed_offset=1500)
    print_contribution_summary(results)
    
    out = cfg.results_dir / "v85_ablation_results.json"
    with open(out, "w") as f:
        json.dump(_convert(results), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
