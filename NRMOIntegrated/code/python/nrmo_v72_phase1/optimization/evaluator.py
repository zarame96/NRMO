"""
NRMO v7.2 Phase 3 — Combination Evaluator

機能サブセット (FeatureFlags) を評価:
  - 全 world × horizon でシミュレーション
  - v7.1 ベースラインに対する Pareto 改善を計算
  - 単一スコア (Pareto 改善の総合点) を返す
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ablation'))

from world_models import World, WorldType, Action
from engines import V71Engine
from ablation_engine import AblatableV72Engine, FeatureFlags, ALL_FEATURES


WORLD_LIST = ["Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"]
WORLD_TYPE_MAP = {
    "Normal": WorldType.NORMAL,
    "FastExpansion": WorldType.FAST_EXPANSION,
    "Vulnerable": WorldType.VULNERABLE,
    "Stagnation": WorldType.STAGNATION,
    "Race": WorldType.RACE,
}


def _run_one(args):
    """1 run の実行"""
    flags_tuple, world_name, horizon, seed = args
    flags_dict = dict(flags_tuple)
    flags = FeatureFlags(**flags_dict)
    engine = AblatableV72Engine(flags=flags)
    world = World(WORLD_TYPE_MAP[world_name], seed=seed)
    for t in range(horizon):
        action = engine.select_action(world.state)
        _, reward, done, _ = world.step(action)
        if hasattr(engine, 'update_reward'):
            engine.update_reward(action, reward)
        if done:
            break
    return world.state.cumulative_score


def _run_v71_baseline(args):
    """v7.1 baseline 1 run"""
    world_name, horizon, seed = args
    engine = V71Engine()
    world = World(WORLD_TYPE_MAP[world_name], seed=seed)
    for t in range(horizon):
        action = engine.select_action(world.state)
        _, reward, done, _ = world.step(action)
        if hasattr(engine, 'update_reward'):
            engine.update_reward(action, reward)
        if done:
            break
    return world.state.cumulative_score


@dataclass
class EvaluationResult:
    """評価結果"""
    flags: FeatureFlags
    cell_scores: Dict[str, Dict[str, float]]  # {world: {metric: value}}
    pareto_violations: int
    strict_improvements: int
    total_improvement: float
    composite_score: float
    n_active_features: int
    elapsed_sec: float


class CombinationEvaluator:
    """機能サブセットの評価"""
    
    def __init__(self,
                 worlds: List[str] = None,
                 horizons: List[int] = None,
                 n_runs: int = 200,
                 n_workers: int = 4,
                 tolerance: float = 0.005,
                 baseline_cache: Optional[Dict] = None):
        self.worlds = worlds or WORLD_LIST
        self.horizons = horizons or [200]
        self.n_runs = n_runs
        self.n_workers = n_workers
        self.tolerance = tolerance
        self.baseline_cache = baseline_cache or {}
    
    def precompute_baseline(self):
        """v7.1 baseline を事前計算してキャッシュ"""
        print(f"Precomputing v7.1 baseline ({len(self.worlds)} worlds × "
                f"{len(self.horizons)} horizons × {self.n_runs} runs)...", flush=True)
        start = time.time()
        
        for world in self.worlds:
            for horizon in self.horizons:
                key = f"{world}_H{horizon}"
                if key in self.baseline_cache:
                    continue
                
                args_list = [(world, horizon, i) for i in range(self.n_runs)]
                
                with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
                    scores = list(executor.map(_run_v71_baseline, args_list))
                
                scores = np.array(scores)
                self.baseline_cache[key] = {
                    "mean": float(np.mean(scores)),
                    "median": float(np.median(scores)),
                    "std": float(np.std(scores)),
                    "p25": float(np.percentile(scores, 25)),
                }
        
        elapsed = time.time() - start
        print(f"Baseline ready in {elapsed:.1f}s", flush=True)
    
    def evaluate(self, flags: FeatureFlags, verbose: bool = False) -> EvaluationResult:
        """機能サブセットを評価"""
        if not self.baseline_cache:
            self.precompute_baseline()
        
        start = time.time()
        cell_scores = {}
        pareto_violations = 0
        strict_improvements = 0
        total_improvement = 0.0
        
        # flags を tuple 化 (multiprocessing 用)
        flags_tuple = tuple((f, getattr(flags, f)) for f in ALL_FEATURES)
        
        for world in self.worlds:
            cell_scores[world] = {}
            for horizon in self.horizons:
                args_list = [
                    (flags_tuple, world, horizon, i)
                    for i in range(self.n_runs)
                ]
                
                with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
                    scores = list(executor.map(_run_one, args_list))
                
                scores = np.array(scores)
                median = float(np.median(scores))
                
                cell_key = f"{world}_H{horizon}"
                cell_scores[world][f"H{horizon}_median"] = median
                
                # Pareto check
                baseline_median = self.baseline_cache[cell_key]["median"]
                diff = median - baseline_median
                total_improvement += diff
                
                if diff < -self.tolerance:
                    pareto_violations += 1
                if diff > self.tolerance * 2:
                    strict_improvements += 1
                
                if verbose:
                    sign = "+" if diff >= 0 else ""
                    print(f"    {cell_key}: median={median:.3f} "
                            f"(baseline={baseline_median:.3f}, diff={sign}{diff:.3f})")
        
        n_cells = len(self.worlds) * len(self.horizons)
        
        # Composite score:
        #   - Pareto 違反は厳しいペナルティ
        #   - 厳格改善はボーナス
        #   - 機能数ペナルティ (簡素性)
        composite = (
            total_improvement
            - 5.0 * pareto_violations
            + 0.1 * strict_improvements
            - 0.01 * len([f for f in ALL_FEATURES if getattr(flags, f)])
        )
        
        elapsed = time.time() - start
        
        return EvaluationResult(
            flags=flags,
            cell_scores=cell_scores,
            pareto_violations=pareto_violations,
            strict_improvements=strict_improvements,
            total_improvement=total_improvement,
            composite_score=composite,
            n_active_features=len([f for f in ALL_FEATURES if getattr(flags, f)]),
            elapsed_sec=elapsed,
        )


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3 Evaluator 動作確認")
    print("=" * 60)
    
    evaluator = CombinationEvaluator(
        worlds=["Normal", "Vulnerable"],
        horizons=[200],
        n_runs=100,
        n_workers=4,
    )
    
    evaluator.precompute_baseline()
    print(f"\nBaseline cache: {evaluator.baseline_cache}")
    
    # 候補 1: All ON
    print("\n--- All ON (v7.2 full) ---")
    result_all_on = evaluator.evaluate(FeatureFlags.all_on(), verbose=True)
    print(f"  Composite: {result_all_on.composite_score:.3f}")
    print(f"  Pareto violations: {result_all_on.pareto_violations}")
    print(f"  Total improvement: {result_all_on.total_improvement:+.3f}")
    
    # 候補 2: Phase 2 で発見した KEEP 9 機能のみ
    print("\n--- KEEP 9 機能のみ (Phase 2 推奨) ---")
    keep = FeatureFlags.all_off()
    for f in ["I8", "I11", "H2", "G1", "G2", "G3", "G7", "G8", "G9"]:
        setattr(keep, f, True)
    result_keep = evaluator.evaluate(keep, verbose=True)
    print(f"  Composite: {result_keep.composite_score:.3f}")
    print(f"  Pareto violations: {result_keep.pareto_violations}")
    print(f"  Total improvement: {result_keep.total_improvement:+.3f}")
    
    # 候補 3: All OFF (v7.1 相当)
    print("\n--- All OFF (v7.1) ---")
    result_all_off = evaluator.evaluate(FeatureFlags.all_off(), verbose=True)
    print(f"  Composite: {result_all_off.composite_score:.3f}")
    print(f"  Pareto violations: {result_all_off.pareto_violations}")
    print(f"  Total improvement: {result_all_off.total_improvement:+.3f}")
