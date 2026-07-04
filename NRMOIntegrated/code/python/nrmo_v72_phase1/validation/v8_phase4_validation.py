"""
validation/v8_phase4_validation.py

監査指摘 2 (Phase 6 PARTIAL_PASS) と指摘 3 (all 8 criteria 0/15) への対応。
V8Engine 対象に Phase 4 を再実行し、新指標も含めて評価。
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
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "benchmark"))

from config import NRMOConfig
from world_models import World, WorldType
from engines import V71Engine
from statistical_tests import run_all_tests


WORLD_TYPE_MAP = {
    "Normal": WorldType.NORMAL,
    "FastExpansion": WorldType.FAST_EXPANSION,
    "Vulnerable": WorldType.VULNERABLE,
    "Stagnation": WorldType.STAGNATION,
    "Race": WorldType.RACE,
}


def _run_v71(args):
    world_name, horizon, world_seed, engine_seed = args
    engine = V71Engine()
    world = World(WORLD_TYPE_MAP[world_name], seed=world_seed)
    ruined = False
    ruin_step = None
    for t in range(horizon):
        action = engine.select_action(world.state)
        _, reward, done, _ = world.step(action)
        if hasattr(engine, 'update_reward'):
            engine.update_reward(action, reward)
        if done:
            ruined = True
            ruin_step = t + 1
            break
    return {
        "final_score": float(world.state.cumulative_score),
        "is_ruined": ruined,
        "ruin_step": ruin_step,
        "completed_steps": world.state.t,
        "world_seed": world_seed,
    }


def _run_v8(args):
    world_name, horizon, world_seed, engine_seed = args
    # 各 run で独立な rng_manager (engine_seed)
    from v8_engine import V8Engine
    from rng_manager import RNGManager
    rng_mgr = RNGManager(master_seed=engine_seed)
    engine = V8Engine(rng_manager=rng_mgr, enable_meta_log=False)
    world = World(WORLD_TYPE_MAP[world_name], seed=world_seed)
    ruined = False
    ruin_step = None
    for t in range(horizon):
        decision = engine.decide(world.state)
        action = decision.action
        if action is None:
            from world_models import Action
            action = Action(intent="hold", strength="A")
        _, reward, done, _ = world.step(action)
        engine.update_reward(action, reward)
        if done:
            ruined = True
            ruin_step = t + 1
            break
    return {
        "final_score": float(world.state.cumulative_score),
        "is_ruined": ruined,
        "ruin_step": ruin_step,
        "completed_steps": world.state.t,
        "world_seed": world_seed,
    }


def run_v8_phase4(config: NRMOConfig,
                    worlds: List[str] = None,
                    horizons: List[int] = None,
                    n_runs: int = 100) -> Dict:
    """V8 対象 Phase 4 (re-design)"""
    worlds = worlds or ["Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"]
    horizons = horizons or [200, 500, 1000]
    
    print("=" * 70)
    print("V8 Phase 4 Validation (re-run, with new metrics)")
    print("=" * 70)
    print(f"Worlds: {worlds}")
    print(f"Horizons: {horizons}")
    print(f"Runs/cell: {n_runs}")
    
    all_cell_results = []
    start = time.time()
    
    for world in worlds:
        for horizon in horizons:
            cell_id = f"{world}_H{horizon}"
            print(f"\n[{cell_id}]")
            cell_start = time.time()
            
            # P0-2 fix: paired design — 同じ world_seed で v7.1 と v8 を実行
            # world_seed と engine_seed を分離
            args = [
                (world, horizon, world_seed, world_seed + 200000)
                for world_seed in range(n_runs)
            ]
            
            with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
                v71_results = list(ex.map(_run_v71, args))
            with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
                v8_results = list(ex.map(_run_v8, args))
            
            v71_scores = np.array([r["final_score"] for r in v71_results])
            v71_ruin_rate = np.mean([r["is_ruined"] for r in v71_results])
            v71_ruined_steps = [r["ruin_step"] for r in v71_results 
                                  if r["ruin_step"] is not None]
            v8_scores = np.array([r["final_score"] for r in v8_results])
            v8_ruin_rate = np.mean([r["is_ruined"] for r in v8_results])
            v8_ruined_steps = [r["ruin_step"] for r in v8_results
                                if r["ruin_step"] is not None]
            
            # paired test (Wilcoxon signed-rank)
            from scipy.stats import wilcoxon
            score_diffs = v8_scores - v71_scores
            try:
                stat, p_value = wilcoxon(score_diffs, alternative="greater")
                paired_test = {"stat": float(stat), "p_value": float(p_value)}
            except Exception as e:
                paired_test = {"error": str(e)}
            
            # 統計検定 (legacy report)
            report = run_all_tests(
                v71_scores, v8_scores,
                cell_id=cell_id,
                baseline_name="v7.1",
                candidate_name="v8",
            )
            
            cell_summary = {
                "cell": cell_id,
                "world": world,
                "horizon": horizon,
                "n_runs": n_runs,
                "v71": {
                    "median": float(np.median(v71_scores)),
                    "mean": float(np.mean(v71_scores)),
                    "std": float(np.std(v71_scores)),
                    "ruin_rate": float(v71_ruin_rate),
                    "median_time_to_ruin": (
                        float(np.median(v71_ruined_steps)) if v71_ruined_steps else None
                    ),
                },
                "v8": {
                    "median": float(np.median(v8_scores)),
                    "mean": float(np.mean(v8_scores)),
                    "std": float(np.std(v8_scores)),
                    "ruin_rate": float(v8_ruin_rate),
                    "median_time_to_ruin": (
                        float(np.median(v8_ruined_steps)) if v8_ruined_steps else None
                    ),
                },
                "diff": {
                    "median": float(np.median(v8_scores) - np.median(v71_scores)),
                    "mean": float(np.mean(v8_scores) - np.mean(v71_scores)),
                    "paired_median_diff": float(np.median(v8_scores - v71_scores)),
                    "paired_mean_diff": float(np.mean(v8_scores - v71_scores)),
                    "n_v8_better": int(np.sum(v8_scores > v71_scores)),
                    "n_v71_better": int(np.sum(v71_scores > v8_scores)),
                    "n_tied": int(np.sum(v8_scores == v71_scores)),
                    "ruin_rate": float(v8_ruin_rate - v71_ruin_rate),
                    "time_to_ruin": (
                        float(np.median(v8_ruined_steps) - np.median(v71_ruined_steps))
                        if v71_ruined_steps and v8_ruined_steps else None
                    ),
                    "paired_wilcoxon": paired_test,
                },
                "convergence_report": report.summarize(),
            }
            
            elapsed = time.time() - cell_start
            cell_summary["elapsed_sec"] = elapsed
            
            sign = "+" if cell_summary["diff"]["median"] >= 0 else ""
            ruin_sign = "+" if cell_summary["diff"]["ruin_rate"] >= 0 else ""
            
            print(f"  v7.1: median={cell_summary['v71']['median']:.3f} "
                   f"ruin={cell_summary['v71']['ruin_rate']:.1%}")
            print(f"  v8:   median={cell_summary['v8']['median']:.3f} "
                   f"ruin={cell_summary['v8']['ruin_rate']:.1%}")
            print(f"  diff: median={sign}{cell_summary['diff']['median']:.3f}, "
                   f"ruin={ruin_sign}{cell_summary['diff']['ruin_rate']*100:.1f}%")
            print(f"  ({elapsed:.1f}s)")
            
            all_cell_results.append(cell_summary)
    
    # サマリー
    total_elapsed = time.time() - start
    
    pareto_passing = sum(1 for r in all_cell_results 
                          if r["diff"]["median"] >= -0.005)
    strict_improvements = sum(1 for r in all_cell_results
                                if r["diff"]["median"] > 0.01)
    ruin_improvements = sum(1 for r in all_cell_results
                              if r["diff"]["ruin_rate"] < -0.005)
    ruin_violations = sum(1 for r in all_cell_results
                            if r["diff"]["ruin_rate"] > 0.005)
    
    summary = {
        "phase": "4_v8",
        "n_cells": len(all_cell_results),
        "n_runs_per_cell": n_runs,
        "worlds": worlds,
        "horizons": horizons,
        "pareto_passing": pareto_passing,
        "pareto_pass_rate": pareto_passing / len(all_cell_results),
        "strict_improvements": strict_improvements,
        "ruin_improvements": ruin_improvements,
        "ruin_violations": ruin_violations,
        "total_elapsed_sec": total_elapsed,
        "cell_results": all_cell_results,
    }
    
    print(f"\n{'='*70}")
    print(f"V8 Phase 4 Summary")
    print(f"{'='*70}")
    print(f"Total cells: {len(all_cell_results)}")
    print(f"Pareto passing: {pareto_passing}/{len(all_cell_results)} "
           f"({pareto_passing/len(all_cell_results)*100:.1f}%)")
    print(f"Strict improvements: {strict_improvements}/{len(all_cell_results)}")
    print(f"Ruin rate improvements (v8 better): {ruin_improvements}/{len(all_cell_results)}")
    print(f"Ruin rate violations (v8 worse): {ruin_violations}/{len(all_cell_results)}")
    
    return summary


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
    
    # 軽量設定で実行 (n=100, 3 worlds x 2 horizons = 6 cells)
    summary = run_v8_phase4(
        cfg,
        worlds=["Normal", "Vulnerable", "Stagnation"],
        horizons=[200, 500],
        n_runs=100,
    )
    
    output_path = cfg.results_dir / "v8_phase4_validation.json"
    with open(output_path, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved: {output_path}")
