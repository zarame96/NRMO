"""
NRMO v7.2 Phase 2 — Ablation Runner

22 機能 × 5 worlds × 3 horizons の体系的 ablation:
  - LOI (Leave-One-In): その機能のみ ON
  - LOO (Leave-One-Out): その機能のみ OFF
  - Baseline: All OFF (= v7.1)
  - Full: All ON (= v7.2)
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from world_models import World, WorldType, WorldState, Action
from engines import V71Engine
from ablation_engine import AblatableV72Engine, FeatureFlags, ALL_FEATURES


def _world_name_to_type(world_name: str) -> WorldType:
    mapping = {
        "Normal": WorldType.NORMAL,
        "FastExpansion": WorldType.FAST_EXPANSION,
        "Vulnerable": WorldType.VULNERABLE,
        "Stagnation": WorldType.STAGNATION,
        "Race": WorldType.RACE,
    }
    return mapping[world_name]


def run_single_ablation(args: Tuple) -> Dict:
    """1 run の ablation 実行"""
    condition_id, flags_dict, world_name, horizon, seed = args
    
    flags = FeatureFlags(**flags_dict)
    engine = AblatableV72Engine(flags=flags)
    world_type = _world_name_to_type(world_name)
    world = World(world_type, seed=seed)
    
    for t in range(horizon):
        action = engine.select_action(world.state)
        _, reward, done, _ = world.step(action)
        if hasattr(engine, 'update_reward'):
            engine.update_reward(action, reward)
        if done:
            break
    
    return {
        "condition_id": condition_id,
        "world": world_name,
        "horizon": horizon,
        "seed": seed,
        "final_score": world.state.cumulative_score,
        "final_t": world.state.t,
    }


def run_ablation_cell(condition_id: str, flags: FeatureFlags,
                       world_name: str, horizon: int,
                       n_runs: int, n_workers: int = 4,
                       seed_base: int = 0) -> Dict:
    """1 ablation condition × cell の全 runs 実行"""
    flags_dict = {f: getattr(flags, f) for f in ALL_FEATURES}
    
    args_list = [
        (condition_id, flags_dict, world_name, horizon, seed_base + i)
        for i in range(n_runs)
    ]
    
    start = time.time()
    scores = []
    
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        for result in executor.map(run_single_ablation, args_list):
            scores.append(result["final_score"])
    
    elapsed = time.time() - start
    scores = np.array(scores)
    
    return {
        "condition_id": condition_id,
        "world": world_name,
        "horizon": horizon,
        "n_runs": n_runs,
        "elapsed_sec": elapsed,
        "stats": {
            "mean": float(np.mean(scores)),
            "median": float(np.median(scores)),
            "std": float(np.std(scores)),
            "p25": float(np.percentile(scores, 25)),
            "p75": float(np.percentile(scores, 75)),
        },
        "raw_scores": scores.tolist(),
    }


def build_ablation_conditions() -> List[Tuple[str, FeatureFlags]]:
    """ablation の全 conditions を構築"""
    conditions = []
    
    # Baseline (v7.1 相当)
    conditions.append(("BASELINE_v71", FeatureFlags.all_off()))
    
    # Full (v7.2 全機能 ON)
    conditions.append(("FULL_v72", FeatureFlags.all_on()))
    
    # LOI: 各機能単独 ON
    for feature in ALL_FEATURES:
        conditions.append((f"LOI_{feature}", FeatureFlags.loi(feature)))
    
    # LOO: 各機能のみ OFF
    for feature in ALL_FEATURES:
        conditions.append((f"LOO_{feature}", FeatureFlags.loo(feature)))
    
    return conditions


def run_full_ablation(worlds: List[str], horizons: List[int],
                      n_runs: int = 1000, n_workers: int = 4,
                      checkpoint_dir: str = "./ablation_results"):
    """全 ablation 実行"""
    Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
    
    conditions = build_ablation_conditions()
    total_cells = len(conditions) * len(worlds) * len(horizons)
    
    print(f"Total cells: {total_cells}")
    print(f"  Conditions: {len(conditions)} (= 2 base + {len(ALL_FEATURES)} LOI + {len(ALL_FEATURES)} LOO)")
    print(f"  Worlds: {len(worlds)}")
    print(f"  Horizons: {len(horizons)}")
    print(f"  Runs/cell: {n_runs}")
    print(f"  Total runs: {total_cells * n_runs:,}")
    
    cell_count = 0
    start = time.time()
    
    for condition_id, flags in conditions:
        for world in worlds:
            for horizon in horizons:
                cell_count += 1
                cell_id = f"{condition_id}_{world}_H{horizon}"
                
                # Skip if already completed
                cache_path = Path(checkpoint_dir) / f"{cell_id}.json"
                if cache_path.exists():
                    continue
                
                cell_start = time.time()
                result = run_ablation_cell(
                    condition_id=condition_id,
                    flags=flags,
                    world_name=world,
                    horizon=horizon,
                    n_runs=n_runs,
                    n_workers=n_workers,
                )
                
                with open(cache_path, "w") as f:
                    json.dump(result, f)
                
                elapsed = time.time() - cell_start
                total_elapsed = time.time() - start
                eta = total_elapsed / cell_count * (total_cells - cell_count)
                
                print(f"[{cell_count}/{total_cells}] {cell_id}: "
                      f"median={result['stats']['median']:6.2f} "
                      f"({elapsed:.1f}s, ETA {eta/60:.1f}min)", flush=True)
    
    print(f"\nAblation complete in {time.time() - start:.1f}s")
    print(f"Results saved to: {checkpoint_dir}")


if __name__ == "__main__":
    # クイックテスト
    print("=" * 60)
    print("Phase 2 Ablation Quick Test")
    print("=" * 60)
    
    # 小規模設定で動作確認
    run_full_ablation(
        worlds=["Normal", "Vulnerable"],
        horizons=[200],
        n_runs=100,
        n_workers=4,
        checkpoint_dir="./ablation_results_quick",
    )
