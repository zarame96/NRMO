"""
NRMO v7.2 Phase 4 — Final Validation

Phase 3 で発見した最適サブセット (10 機能) を:
  全 5 worlds × 全 horizons で完全検証
  8 つの収束基準すべてをチェック
"""
import os
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'benchmark'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ablation'))

from world_models import World, WorldType
from engines import V71Engine
from ablation_engine import AblatableV72Engine, FeatureFlags, ALL_FEATURES
from statistical_tests import run_all_tests


WORLD_TYPE_MAP = {
    "Normal": WorldType.NORMAL,
    "FastExpansion": WorldType.FAST_EXPANSION,
    "Vulnerable": WorldType.VULNERABLE,
    "Stagnation": WorldType.STAGNATION,
    "Race": WorldType.RACE,
}


# Phase 3 で発見された最適サブセット
OPTIMAL_FEATURES = ["I8", "H2", "H5", "G1", "G2", "G3", "G6", "G7", "G8", "G9"]


def _run_v71(args):
    world_name, horizon, seed = args
    engine = V71Engine()
    world = World(WORLD_TYPE_MAP[world_name], seed=seed)
    for _ in range(horizon):
        action = engine.select_action(world.state)
        _, reward, done, _ = world.step(action)
        if hasattr(engine, 'update_reward'):
            engine.update_reward(action, reward)
        if done:
            break
    return world.state.cumulative_score


def _run_v72_optimal(args):
    flags_tuple, world_name, horizon, seed = args
    flags = FeatureFlags(**dict(flags_tuple))
    engine = AblatableV72Engine(flags=flags)
    world = World(WORLD_TYPE_MAP[world_name], seed=seed)
    for _ in range(horizon):
        action = engine.select_action(world.state)
        _, reward, done, _ = world.step(action)
        if hasattr(engine, 'update_reward'):
            engine.update_reward(action, reward)
        if done:
            break
    return world.state.cumulative_score


def run_cell_validation(world: str, horizon: int, n_runs: int,
                          optimal_flags: FeatureFlags,
                          n_workers: int = 4) -> Dict:
    """1 cell の完全検証"""
    # v7.1 baseline
    v71_args = [(world, horizon, i) for i in range(n_runs)]
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        v71_scores = list(executor.map(_run_v71, v71_args))
    v71_scores = np.array(v71_scores)
    
    # v7.2 optimal
    flags_tuple = tuple((f, getattr(optimal_flags, f)) for f in ALL_FEATURES)
    v72_args = [(flags_tuple, world, horizon, i + 100000) for i in range(n_runs)]
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        v72_scores = list(executor.map(_run_v72_optimal, v72_args))
    v72_scores = np.array(v72_scores)
    
    # 統計検定
    report = run_all_tests(
        v71_scores, v72_scores,
        cell_id=f"{world}_H{horizon}",
        baseline_name="v7.1",
        candidate_name="v7.2_optimal",
    )
    
    return {
        "cell": f"{world}_H{horizon}",
        "world": world,
        "horizon": horizon,
        "n_runs": n_runs,
        "v71_stats": {
            "mean": float(np.mean(v71_scores)),
            "median": float(np.median(v71_scores)),
            "std": float(np.std(v71_scores)),
            "p25": float(np.percentile(v71_scores, 25)),
            "p75": float(np.percentile(v71_scores, 75)),
        },
        "v72_stats": {
            "mean": float(np.mean(v72_scores)),
            "median": float(np.median(v72_scores)),
            "std": float(np.std(v72_scores)),
            "p25": float(np.percentile(v72_scores, 25)),
            "p75": float(np.percentile(v72_scores, 75)),
        },
        "diff_median": float(np.median(v72_scores) - np.median(v71_scores)),
        "diff_mean": float(np.mean(v72_scores) - np.mean(v71_scores)),
        "convergence_report": report.summarize(),
        "all_8_passed": report.all_passed,
    }


def run_phase4_validation(worlds: List[str], horizons: List[int],
                            n_runs: int = 500,
                            n_workers: int = 4,
                            output_path: str = None) -> Dict:
    """Phase 4 全 cells 統合検証"""
    print("=" * 70)
    print("Phase 4 — Final Validation")
    print("=" * 70)
    
    # 最適サブセット構築
    optimal_flags = FeatureFlags.all_off()
    for f in OPTIMAL_FEATURES:
        setattr(optimal_flags, f, True)
    
    print(f"Optimal features ({len(OPTIMAL_FEATURES)}/22):")
    for f in OPTIMAL_FEATURES:
        print(f"  ✓ {f}")
    print(f"\nValidation grid:")
    print(f"  Worlds: {worlds}")
    print(f"  Horizons: {horizons}")
    print(f"  Runs/cell: {n_runs}")
    print(f"  Total cells: {len(worlds) * len(horizons)}")
    
    all_results = []
    start = time.time()
    
    for i, world in enumerate(worlds):
        for j, horizon in enumerate(horizons):
            cell_idx = i * len(horizons) + j + 1
            total = len(worlds) * len(horizons)
            
            print(f"\n[{cell_idx}/{total}] {world}_H{horizon}: ", end="", flush=True)
            cell_start = time.time()
            
            result = run_cell_validation(
                world=world,
                horizon=horizon,
                n_runs=n_runs,
                optimal_flags=optimal_flags,
                n_workers=n_workers,
            )
            
            elapsed = time.time() - cell_start
            
            diff_med = result["diff_median"]
            sign = "+" if diff_med >= 0 else ""
            passed = "✓" if result["all_8_passed"] else "✗"
            
            print(f"v7.1={result['v71_stats']['median']:.3f}, "
                    f"v7.2={result['v72_stats']['median']:.3f} "
                    f"(diff={sign}{diff_med:.3f}) [{passed}] {elapsed:.1f}s",
                    flush=True)
            
            all_results.append(result)
    
    total_elapsed = time.time() - start
    
    # サマリー
    pareto_passing = sum(1 for r in all_results
                          if r["diff_median"] >= -0.005)
    strict_improvements = sum(1 for r in all_results
                                if r["diff_median"] > 0.01)
    all_criteria_passing = sum(1 for r in all_results if r["all_8_passed"])
    
    summary = {
        "phase": 4,
        "optimal_features": OPTIMAL_FEATURES,
        "n_features": len(OPTIMAL_FEATURES),
        "n_runs_per_cell": n_runs,
        "total_cells": len(all_results),
        "pareto_passing": pareto_passing,
        "strict_improvements": strict_improvements,
        "all_criteria_passing": all_criteria_passing,
        "total_elapsed_sec": total_elapsed,
        "cell_results": all_results,
    }
    
    print(f"\n{'='*70}")
    print(f"PHASE 4 SUMMARY")
    print(f"{'='*70}")
    print(f"Total cells: {summary['total_cells']}")
    print(f"Pareto passing (diff >= -0.005): {pareto_passing}/{summary['total_cells']}")
    print(f"Strict improvements (diff > 0.01): {strict_improvements}/{summary['total_cells']}")
    print(f"All 8 criteria passing: {all_criteria_passing}/{summary['total_cells']}")
    print(f"Total elapsed: {total_elapsed:.1f}s")
    
    if output_path:
        # Convert numpy types to Python native types for JSON serialization
        def _convert(obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, dict):
                return {k: _convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_convert(v) for v in obj]
            return obj
        
        with open(output_path, "w") as f:
            json.dump(_convert(summary), f, indent=2)
        print(f"\nSaved: {output_path}")
    
    return summary


if __name__ == "__main__":
    summary = run_phase4_validation(
        worlds=["Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"],
        horizons=[200, 500, 1000],
        n_runs=400,
        n_workers=4,
        output_path="./phase4_validation_results.json",
    )
