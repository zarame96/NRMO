"""
NRMO v7.2 Phase 5 — Long Run Convergence Validation

H=2000 まで延長して plateau 値を確認:
  - v7.1 と v7.2 の plateau が同等以上か
  - 軌跡 attractor の同一性
  - 破滅率の非発散
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ablation'))

from world_models import World, WorldType
from engines import V71Engine
from ablation_engine import AblatableV72Engine, FeatureFlags, ALL_FEATURES


WORLD_TYPE_MAP = {
    "Normal": WorldType.NORMAL,
    "FastExpansion": WorldType.FAST_EXPANSION,
    "Vulnerable": WorldType.VULNERABLE,
    "Stagnation": WorldType.STAGNATION,
    "Race": WorldType.RACE,
}

OPTIMAL_FEATURES = ["I8", "H2", "H5", "G1", "G2", "G3", "G6", "G7", "G8", "G9"]


def _run_long(args):
    """Long run の実行 (途中状態も記録)"""
    engine_type, flags_tuple, world_name, horizon, seed, checkpoints = args
    
    if engine_type == "v7.1":
        engine = V71Engine()
    else:
        flags = FeatureFlags(**dict(flags_tuple))
        engine = AblatableV72Engine(flags=flags)
    
    world = World(WORLD_TYPE_MAP[world_name], seed=seed)
    
    # チェックポイントごとの score を記録
    checkpoint_scores = {}
    for t in range(horizon):
        action = engine.select_action(world.state)
        _, reward, done, _ = world.step(action)
        if hasattr(engine, 'update_reward'):
            engine.update_reward(action, reward)
        
        if (t + 1) in checkpoints:
            checkpoint_scores[t + 1] = world.state.cumulative_score
        
        if done:
            # 残り checkpoint は最終 score で埋める
            for cp in checkpoints:
                if cp > t + 1 and cp not in checkpoint_scores:
                    checkpoint_scores[cp] = world.state.cumulative_score
            break
    
    return {
        "engine": engine_type,
        "world": world_name,
        "seed": seed,
        "checkpoint_scores": checkpoint_scores,
        "final_score": world.state.cumulative_score,
        "is_ruined": world.state.is_ruined,
    }


def run_phase5_long_run(worlds: List[str],
                          max_horizon: int = 2000,
                          checkpoints: List[int] = None,
                          n_runs: int = 200,
                          n_workers: int = 4,
                          output_path: str = None) -> Dict:
    """Phase 5 Long Run 検証"""
    print("=" * 70)
    print("Phase 5 — Long Run Convergence Validation")
    print("=" * 70)
    
    if checkpoints is None:
        checkpoints = [200, 500, 1000, 1500, 2000]
    checkpoints = [c for c in checkpoints if c <= max_horizon]
    
    optimal_flags = FeatureFlags.all_off()
    for f in OPTIMAL_FEATURES:
        setattr(optimal_flags, f, True)
    flags_tuple = tuple((f, getattr(optimal_flags, f)) for f in ALL_FEATURES)
    
    print(f"Worlds: {worlds}")
    print(f"Max horizon: {max_horizon}")
    print(f"Checkpoints: {checkpoints}")
    print(f"Runs/condition/world: {n_runs}")
    
    all_results = {}
    start = time.time()
    
    for world in worlds:
        print(f"\n[{world}]")
        all_results[world] = {}
        
        for engine_type in ["v7.1", "v7.2_optimal"]:
            print(f"  {engine_type}: ", end="", flush=True)
            cell_start = time.time()
            
            args_list = [
                (engine_type, flags_tuple, world, max_horizon, i, checkpoints)
                for i in range(n_runs)
            ]
            
            with ProcessPoolExecutor(max_workers=n_workers) as executor:
                results = list(executor.map(_run_long, args_list))
            
            elapsed = time.time() - cell_start
            
            # 各チェックポイントの統計
            ckpt_stats = {}
            for cp in checkpoints:
                scores = [r["checkpoint_scores"].get(cp, r["final_score"])
                            for r in results]
                ckpt_stats[cp] = {
                    "median": float(np.median(scores)),
                    "mean": float(np.mean(scores)),
                    "std": float(np.std(scores)),
                }
            
            # plateau 検出: 最後 25% の安定性
            last_ckpt_idx = int(len(checkpoints) * 0.75)
            plateau_ckpts = checkpoints[last_ckpt_idx:]
            plateau_medians = [ckpt_stats[c]["median"] for c in plateau_ckpts]
            plateau_value = float(np.mean(plateau_medians))
            plateau_std = float(np.std(plateau_medians))
            
            ruin_rate = float(np.mean([r["is_ruined"] for r in results]))
            
            all_results[world][engine_type] = {
                "checkpoint_stats": ckpt_stats,
                "plateau_value": plateau_value,
                "plateau_std": plateau_std,
                "ruin_rate": ruin_rate,
                "elapsed_sec": elapsed,
            }
            
            print(f"plateau={plateau_value:.3f}±{plateau_std:.3f}, "
                    f"ruin_rate={ruin_rate:.1%} [{elapsed:.1f}s]", flush=True)
    
    total_elapsed = time.time() - start
    
    # 比較サマリー
    print(f"\n{'='*70}")
    print(f"PHASE 5 — Long Run Comparison")
    print(f"{'='*70}")
    print(f"{'World':<15} {'v7.1 plateau':<15} {'v7.2 plateau':<15} "
            f"{'Diff':<10} {'Ruin v7.1':<10} {'Ruin v7.2':<10}")
    print("-" * 80)
    
    plateau_violations = 0
    ruin_violations = 0
    
    for world in worlds:
        v71 = all_results[world]["v7.1"]
        v72 = all_results[world]["v7.2_optimal"]
        
        diff = v72["plateau_value"] - v71["plateau_value"]
        ruin_diff = v72["ruin_rate"] - v71["ruin_rate"]
        
        if diff < -0.005:
            plateau_violations += 1
        if ruin_diff > 0.005:
            ruin_violations += 1
        
        sign = "+" if diff >= 0 else ""
        print(f"{world:<15} {v71['plateau_value']:<15.3f} "
                f"{v72['plateau_value']:<15.3f} "
                f"{sign}{diff:<9.3f} "
                f"{v71['ruin_rate']:<10.1%} {v72['ruin_rate']:<10.1%}")
    
    print(f"\nPlateau violations: {plateau_violations}/{len(worlds)}")
    print(f"Ruin rate violations: {ruin_violations}/{len(worlds)}")
    print(f"Total elapsed: {total_elapsed:.1f}s")
    
    summary = {
        "phase": 5,
        "optimal_features": OPTIMAL_FEATURES,
        "max_horizon": max_horizon,
        "checkpoints": checkpoints,
        "n_runs": n_runs,
        "world_results": all_results,
        "plateau_violations": plateau_violations,
        "ruin_violations": ruin_violations,
        "total_elapsed_sec": total_elapsed,
    }
    
    if output_path:
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nSaved: {output_path}")
    
    return summary


if __name__ == "__main__":
    summary = run_phase5_long_run(
        worlds=["Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"],
        max_horizon=2000,
        checkpoints=[200, 500, 1000, 1500, 2000],
        n_runs=150,
        n_workers=4,
        output_path="./phase5_long_run_results.json",
    )
