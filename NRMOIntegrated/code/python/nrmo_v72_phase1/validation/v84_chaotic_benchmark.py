"""
validation/v84_chaotic_benchmark.py

引き算 step 1: v7.1 vs (v7.1 + ActivePattern) を ChaoticWorld で比較.
"""
from __future__ import annotations
import os
import sys
import json
import time
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
from engines import V71Engine


def _run_v71(args):
    chaos_level, horizon, seed = args
    config = ChaosConfig.from_level(chaos_level)
    world = ChaoticWorld(config, seed=seed)
    engine = V71Engine()
    
    ruined = False
    for t in range(horizon):
        obs = world.observe()
        action = engine.select_action(obs)
        reward, done, _ = world.step(action)
        engine.update_reward(action, reward)
        if done:
            ruined = True
            break
    
    return {
        "final_score": float(world.state.cumulative_score),
        "is_ruined": ruined,
        "completed_steps": world.state.t,
    }


def _run_v84(args):
    chaos_level, horizon, seed = args
    config = ChaosConfig.from_level(chaos_level)
    world = ChaoticWorld(config, seed=seed)
    
    from v84_minimal_engine import V84MinimalEngine
    from rng_manager import RNGManager
    rng_mgr = RNGManager(master_seed=seed + 600000)
    engine = V84MinimalEngine(rng_manager=rng_mgr)
    
    ruined = False
    intervention_count = 0
    ap_scores = []
    
    for t in range(horizon):
        obs = world.observe()
        decision = engine.decide(obs)
        action = decision.action if decision.action else Action(intent="hold", strength="A")
        
        if decision.status == "INTERVENED":
            intervention_count += 1
        if decision.active_pattern_proposal:
            ap_scores.append(decision.active_pattern_proposal.score)
        
        reward, done, _ = world.step(action)
        engine.update_reward(action, reward)
        if done:
            ruined = True
            break
    
    return {
        "final_score": float(world.state.cumulative_score),
        "is_ruined": ruined,
        "completed_steps": world.state.t,
        "intervention_count": intervention_count,
        "ap_score_mean": float(np.mean(ap_scores)) if ap_scores else 0.0,
        "ap_score_max": float(np.max(ap_scores)) if ap_scores else 0.0,
    }


def run_v84_chaotic(config: NRMOConfig, n_runs: int = 30):
    chaos_levels = ["mild", "moderate", "severe", "extreme", "total"]
    horizon = 200
    
    print("=" * 70)
    print("V7.1 vs V8.4 Minimal (v7.1 + ActivePattern) in ChaoticWorld")
    print("=" * 70)
    
    all_results = {}
    
    for level in chaos_levels:
        print(f"\n[{level.upper()}]")
        args = [(level, horizon, seed) for seed in range(n_runs)]
        
        with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
            v71_results = list(ex.map(_run_v71, args))
        with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
            v84_results = list(ex.map(_run_v84, args))
        
        v71_scores = np.array([r["final_score"] for r in v71_results])
        v84_scores = np.array([r["final_score"] for r in v84_results])
        v71_steps = np.array([r["completed_steps"] for r in v71_results])
        v84_steps = np.array([r["completed_steps"] for r in v84_results])
        
        diffs = v84_scores - v71_scores
        n_v84_better = int(np.sum(diffs > 0))
        n_v71_better = int(np.sum(diffs < 0))
        
        avg_intv = float(np.mean([r["intervention_count"] for r in v84_results]))
        avg_ap_score = float(np.mean([r["ap_score_mean"] for r in v84_results]))
        max_ap = float(np.max([r["ap_score_max"] for r in v84_results]))
        
        cell = {
            "v71_median": float(np.median(v71_scores)),
            "v84_median": float(np.median(v84_scores)),
            "v71_steps_median": float(np.median(v71_steps)),
            "v84_steps_median": float(np.median(v84_steps)),
            "diff_median": float(np.median(diffs)),
            "diff_mean": float(np.mean(diffs)),
            "n_v84_better": n_v84_better,
            "n_v71_better": n_v71_better,
            "avg_interventions_per_run": avg_intv,
            "avg_ap_score": avg_ap_score,
            "max_ap_score": max_ap,
        }
        
        print(f"  v7.1:        median={cell['v71_median']:7.2f}  steps={cell['v71_steps_median']:.0f}")
        print(f"  v8.4 min:    median={cell['v84_median']:7.2f}  steps={cell['v84_steps_median']:.0f}")
        sign = "+" if cell['diff_median'] >= 0 else ""
        print(f"  diff median: {sign}{cell['diff_median']:.2f}  (v8.4 wins {n_v84_better}/{n_runs})")
        print(f"  AP score avg: {avg_ap_score:.3f}, max: {max_ap:.3f}")
        print(f"  AP interventions/run: {avg_intv:.2f}")
        
        all_results[level] = cell
    
    # Summary
    print(f"\n{'='*70}")
    print(f"V8.4 Minimal Summary")
    print(f"{'='*70}")
    print(f"{'Level':<10} {'v7.1':>8} {'v8.4':>8} {'diff':>8} {'wins':>8} {'intv':>6}")
    print("-" * 70)
    for level in chaos_levels:
        c = all_results[level]
        d = c["diff_median"]
        sign = "+" if d >= 0 else ""
        ds = f"{sign}{d:.2f}"
        wins = f"{c['n_v84_better']}/{n_runs}"
        print(f"{level:<10} {c['v71_median']:>8.2f} {c['v84_median']:>8.2f} "
                f"{ds:>8} {wins:>8} {c['avg_interventions_per_run']:>6.1f}")
    
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
    results = run_v84_chaotic(cfg, n_runs=30)
    
    out = cfg.results_dir / "v84_chaotic_results.json"
    with open(out, "w") as f:
        json.dump(_convert(results), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
