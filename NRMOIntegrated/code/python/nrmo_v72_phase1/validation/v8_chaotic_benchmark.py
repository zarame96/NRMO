"""
validation/v8_chaotic_benchmark.py

ChaoticWorld での v7.1 vs v8 の真の比較.

これが「v8 が存在意義を持つかどうか」を測る最初の場.
整然 worlds (Phase 1-6) では v7.1 が勝つのは当然.
混沌世界で v8 が勝てるかが本当の検証.
"""
from __future__ import annotations
import os
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple
import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "core"))
sys.path.insert(0, str(_ROOT / "phase8"))
sys.path.insert(0, str(_ROOT / "phase9"))
sys.path.insert(0, str(_ROOT / "phase10"))
sys.path.insert(0, str(_ROOT / "phase11"))

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
    ruin_step = None
    for t in range(horizon):
        observed = world.observe()  # ← engine は filtered state を見る
        action = engine.select_action(observed)
        reward, done, info = world.step(action)
        engine.update_reward(action, reward)
        if done:
            ruined = True
            ruin_step = t + 1
            break
    
    return {
        "engine": "v7.1",
        "chaos_level": chaos_level,
        "seed": seed,
        "final_score": float(world.state.cumulative_score),
        "is_ruined": ruined,
        "ruin_step": ruin_step,
        "completed_steps": world.state.t,
        "regime_shifts": world.regime_shift_count,
        "black_swans": world.black_swan_count,
    }


def _run_v8(args):
    chaos_level, horizon, seed = args
    config = ChaosConfig.from_level(chaos_level)
    world = ChaoticWorld(config, seed=seed)
    
    from v8_engine import V8Engine
    from rng_manager import RNGManager
    rng_mgr = RNGManager(master_seed=seed + 300000)
    engine = V8Engine(rng_manager=rng_mgr, enable_meta_log=False)
    
    ruined = False
    ruin_step = None
    for t in range(horizon):
        observed = world.observe()  # ← engine は filtered state を見る
        decision = engine.decide(observed)
        action = decision.action
        if action is None:
            action = Action(intent="hold", strength="A")
        reward, done, info = world.step(action)
        engine.update_reward(action, reward)
        if done:
            ruined = True
            ruin_step = t + 1
            break
    
    return {
        "engine": "v8",
        "chaos_level": chaos_level,
        "seed": seed,
        "final_score": float(world.state.cumulative_score),
        "is_ruined": ruined,
        "ruin_step": ruin_step,
        "completed_steps": world.state.t,
        "regime_shifts": world.regime_shift_count,
        "black_swans": world.black_swan_count,
    }


def run_chaotic_benchmark(config: NRMOConfig,
                            chaos_levels: List[str] = None,
                            horizon: int = 500,
                            n_runs: int = 100) -> Dict:
    """5 chaos levels で v7.1 vs v8 を paired 比較"""
    chaos_levels = chaos_levels or ["mild", "moderate", "severe", "extreme", "total"]
    
    print("=" * 70)
    print("V7.1 vs V8 in CHAOTIC WORLD")
    print("=" * 70)
    print(f"Chaos levels: {chaos_levels}")
    print(f"Horizon: {horizon}")
    print(f"Paired runs per level: {n_runs}")
    
    all_results = {}
    start = time.time()
    
    for level in chaos_levels:
        print(f"\n[{level.upper()}]")
        cell_start = time.time()
        
        # paired: 同じ seed で v7.1 と v8 を実行 (chaos の出現は同じになる)
        args = [(level, horizon, seed) for seed in range(n_runs)]
        
        with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
            v71_results = list(ex.map(_run_v71, args))
        with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
            v8_results = list(ex.map(_run_v8, args))
        
        v71_scores = np.array([r["final_score"] for r in v71_results])
        v8_scores = np.array([r["final_score"] for r in v8_results])
        v71_ruin = np.mean([r["is_ruined"] for r in v71_results])
        v8_ruin = np.mean([r["is_ruined"] for r in v8_results])
        
        v71_steps = np.array([r["completed_steps"] for r in v71_results])
        v8_steps = np.array([r["completed_steps"] for r in v8_results])
        
        # paired stats
        score_diffs = v8_scores - v71_scores
        n_v8_better = int(np.sum(score_diffs > 0))
        n_v71_better = int(np.sum(score_diffs < 0))
        n_tied = int(np.sum(score_diffs == 0))
        
        try:
            from scipy.stats import wilcoxon
            stat, p_value = wilcoxon(score_diffs, alternative="greater")
            wilcoxon_p = float(p_value)
        except Exception:
            wilcoxon_p = None
        
        elapsed = time.time() - cell_start
        
        cell = {
            "chaos_level": level,
            "n_runs": n_runs,
            "v71": {
                "median_score": float(np.median(v71_scores)),
                "mean_score": float(np.mean(v71_scores)),
                "ruin_rate": float(v71_ruin),
                "median_steps": float(np.median(v71_steps)),
            },
            "v8": {
                "median_score": float(np.median(v8_scores)),
                "mean_score": float(np.mean(v8_scores)),
                "ruin_rate": float(v8_ruin),
                "median_steps": float(np.median(v8_steps)),
            },
            "paired": {
                "median_diff": float(np.median(score_diffs)),
                "mean_diff": float(np.mean(score_diffs)),
                "n_v8_better": n_v8_better,
                "n_v71_better": n_v71_better,
                "n_tied": n_tied,
                "wilcoxon_p_v8_greater": wilcoxon_p,
                "steps_diff_median": float(np.median(v8_steps - v71_steps)),
            },
            "elapsed_sec": elapsed,
        }
        
        print(f"  v7.1: median_score={cell['v71']['median_score']:.2f} "
                f"ruin={cell['v71']['ruin_rate']:.1%} "
                f"median_steps={cell['v71']['median_steps']:.0f}")
        print(f"  v8:   median_score={cell['v8']['median_score']:.2f} "
                f"ruin={cell['v8']['ruin_rate']:.1%} "
                f"median_steps={cell['v8']['median_steps']:.0f}")
        sign = "+" if cell["paired"]["median_diff"] >= 0 else ""
        print(f"  paired diff median: {sign}{cell['paired']['median_diff']:.2f}")
        print(f"  v8 better: {n_v8_better}/{n_runs}, v7.1 better: {n_v71_better}/{n_runs}")
        if wilcoxon_p is not None:
            sig = "✓ p<0.05" if wilcoxon_p < 0.05 else "ns"
            print(f"  Wilcoxon (v8 > v7.1): p={wilcoxon_p:.4f} ({sig})")
        print(f"  ({elapsed:.1f}s)")
        
        all_results[level] = cell
    
    total_elapsed = time.time() - start
    
    # サマリー
    print(f"\n{'='*70}")
    print(f"CHAOTIC BENCHMARK SUMMARY")
    print(f"{'='*70}")
    print(f"{'Level':<10} {'v7.1 med':>10} {'v8 med':>10} {'diff':>10} {'v8 wins':>10}")
    print("-" * 70)
    for level in chaos_levels:
        c = all_results[level]
        diff = c["paired"]["median_diff"]
        sign = "+" if diff >= 0 else ""
        wins = f"{c['paired']['n_v8_better']}/{n_runs}"
        diff_str = f"{sign}{diff:.2f}"
        print(f"{level:<10} {c['v71']['median_score']:>10.2f} "
                f"{c['v8']['median_score']:>10.2f} "
                f"{diff_str:>10} "
                f"{wins:>10}")
    
    return {
        "phase": "chaotic_benchmark",
        "chaos_levels": chaos_levels,
        "horizon": horizon,
        "n_runs": n_runs,
        "results": all_results,
        "total_elapsed_sec": total_elapsed,
    }


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
    
    summary = run_chaotic_benchmark(
        cfg,
        chaos_levels=["mild", "moderate", "severe", "extreme", "total"],
        horizon=300,
        n_runs=80,
    )
    
    output_path = cfg.results_dir / "chaotic_benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {output_path}")
