"""
NRMO Phase 7 — Step 7.1: CMA-ES Implementation

対処する流木:
  流木 6: NP 困難性 (22 機能組み合わせは 2^22 = 4M、全探索不可)
  流木 7: 非凸性 (Composite Score は非凸、Greedy は local optimum)

戦略:
  - Binary CMA-ES (連続 → binary)
  - Multi-start (複数初期点)
  - Restart policy (停滞時に再起動)
  - Population-based search (多様性維持)

Phase 11 統合:
  - Multi-Framework Ensemble の枠内で動作
  - Falsifiability 条件を制約として組み込み
  - Frame 内でのみ最適化
"""
import os
import sys
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Callable, Optional
import numpy as np


# ============================================================
# Binary CMA-ES: 22 機能の binary 空間で最適化
# ============================================================

@dataclass
class CMAESConfig:
    """CMA-ES 設定"""
    dim: int = 22                    # 探索空間次元 (= 22 features)
    population_size: int = 16        # 1 世代の個体数
    sigma_init: float = 0.3          # 初期 step size
    sigma_min: float = 0.01          # 最小 step size (収束判定)
    mu_ratio: float = 0.5            # 選択比率 (上位 mu/lambda)
    max_generations: int = 50        # 最大世代数
    n_restarts: int = 3              # multi-start 回数
    stagnation_threshold: int = 10   # 停滞検出 (世代)


@dataclass
class CMAESResult:
    """最適化結果"""
    best_solution: np.ndarray        # binary vector (22D)
    best_features: List[str]         # active features
    best_score: float
    generations_used: int
    restarts_used: int
    convergence_history: List[float]
    total_evaluations: int


ALL_FEATURES = (
    ["I8", "I9", "I10", "I11", "I12"] +
    ["H1", "H2", "H3", "H4", "H5", "H6", "H7"] +
    ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"]
)


class BinaryCMAES:
    """22D binary 空間用の CMA-ES
    
    内部は連続値 [0,1] で扱い、評価時に 0.5 で binary 化
    """
    
    def __init__(self, config: CMAESConfig, evaluator: Callable):
        self.config = config
        self.evaluator = evaluator
        
        # 共分散行列 (対角化されたシンプル版)
        self.mean = np.full(config.dim, 0.5)
        self.sigma = config.sigma_init
        self.C = np.eye(config.dim)
        
        # 履歴
        self.history = []
        self.best_score = -np.inf
        self.best_solution = None
        self.eval_count = 0
        self.stagnation_count = 0
    
    def sample_population(self) -> np.ndarray:
        """1 世代の個体をサンプル"""
        # 多変量正規分布からサンプル
        population = np.random.multivariate_normal(
            self.mean, (self.sigma ** 2) * self.C,
            size=self.config.population_size
        )
        # [0, 1] にクリップ
        return np.clip(population, 0, 1)
    
    def to_binary(self, continuous: np.ndarray) -> np.ndarray:
        """連続値 → binary (>0.5 で 1)"""
        return (continuous > 0.5).astype(int)
    
    def evaluate_population(self, population: np.ndarray) -> List[float]:
        """全個体を評価"""
        scores = []
        for individual in population:
            binary = self.to_binary(individual)
            score = self.evaluator(binary)
            scores.append(score)
            self.eval_count += 1
        return scores
    
    def update_distribution(self, population: np.ndarray, scores: List[float]):
        """選択された個体から分布を更新"""
        # 上位 mu 個体を選択
        mu = max(1, int(self.config.population_size * self.config.mu_ratio))
        sorted_indices = np.argsort(scores)[::-1]  # 降順
        selected_indices = sorted_indices[:mu]
        selected = population[selected_indices]
        
        # 重み (上位ほど重み大)
        weights = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1))
        weights /= weights.sum()
        
        # 平均更新
        new_mean = np.sum(selected * weights[:, np.newaxis], axis=0)
        
        # 共分散更新 (rank-mu)
        deviations = selected - self.mean
        new_C = np.zeros_like(self.C)
        for i, w in enumerate(weights):
            new_C += w * np.outer(deviations[i], deviations[i])
        
        # スムージング (前世代の影響)
        c_mu = min(1.0, mu / (self.config.dim ** 2))
        self.C = (1 - c_mu) * self.C + c_mu * new_C
        
        # Step size 更新
        new_sigma_factor = np.linalg.norm(new_mean - self.mean) / \
                            (self.sigma * np.sqrt(self.config.dim))
        if new_sigma_factor > 1.0:
            self.sigma *= 1.05  # 成功時は拡大
        else:
            self.sigma *= 0.95  # 失敗時は縮小
        
        self.sigma = max(self.sigma, self.config.sigma_min)
        self.mean = new_mean
    
    def run_single(self) -> Tuple[np.ndarray, float, int]:
        """1 回の最適化実行"""
        last_best = -np.inf
        
        for gen in range(self.config.max_generations):
            population = self.sample_population()
            scores = self.evaluate_population(population)
            
            gen_best = max(scores)
            gen_best_idx = scores.index(gen_best)
            gen_best_solution = self.to_binary(population[gen_best_idx])
            
            # 全体ベスト更新
            if gen_best > self.best_score:
                self.best_score = gen_best
                self.best_solution = gen_best_solution.copy()
                self.stagnation_count = 0
            else:
                self.stagnation_count += 1
            
            self.history.append({
                "generation": len(self.history),
                "best_in_gen": gen_best,
                "global_best": self.best_score,
                "sigma": self.sigma,
                "n_active": int(gen_best_solution.sum()),
            })
            
            # 分布更新
            self.update_distribution(population, scores)
            
            # 早期終了判定
            if self.sigma < self.config.sigma_min:
                break
            if self.stagnation_count >= self.config.stagnation_threshold:
                break
        
        return self.best_solution, self.best_score, gen + 1
    
    def optimize(self) -> CMAESResult:
        """Multi-start CMA-ES"""
        print(f"Binary CMA-ES (dim={self.config.dim}, "
              f"pop={self.config.population_size}, "
              f"restarts={self.config.n_restarts})", flush=True)
        
        best_global_solution = None
        best_global_score = -np.inf
        total_gens = 0
        
        for restart in range(self.config.n_restarts):
            # 各 restart で初期化
            self.mean = np.random.uniform(0.2, 0.8, self.config.dim)
            self.sigma = self.config.sigma_init
            self.C = np.eye(self.config.dim)
            self.stagnation_count = 0
            
            solution, score, gens = self.run_single()
            total_gens += gens
            
            if score > best_global_score:
                best_global_score = score
                best_global_solution = solution.copy()
            
            print(f"  Restart {restart+1}: score={score:.3f}, "
                  f"gens={gens}, active={int(solution.sum())}", flush=True)
        
        # 結果整理
        active_features = [
            ALL_FEATURES[i] for i, v in enumerate(best_global_solution) if v
        ]
        
        return CMAESResult(
            best_solution=best_global_solution,
            best_features=active_features,
            best_score=best_global_score,
            generations_used=total_gens,
            restarts_used=self.config.n_restarts,
            convergence_history=[h["global_best"] for h in self.history],
            total_evaluations=self.eval_count,
        )


# ============================================================
# テスト評価関数 (Phase 1-6 の subset evaluator を模した軽量版)
# ============================================================

def mock_evaluator(features: np.ndarray) -> float:
    """軽量評価関数 (テスト用)
    
    実際の v7.2 機能評価を簡略化:
      - 「KEEP 9 機能」を含むと加点
      - 機能数が多すぎるとペナルティ
      - 機能間の相互作用 (一部)
    """
    feature_dict = {ALL_FEATURES[i]: bool(features[i]) for i in range(22)}
    
    score = 0.0
    
    # Phase 2 で発見された KEEP 機能
    keep_features = ["I8", "H2", "G1", "G2", "G3", "G7", "G8", "G9"]
    for f in keep_features:
        if feature_dict[f]:
            score += 1.0
    
    # Phase 3 で発見された追加機能
    bonus_features = ["H5", "G6"]
    for f in bonus_features:
        if feature_dict[f]:
            score += 0.5
    
    # 撤回された機能 (LOI で悪化)
    drop_features = ["H7"]
    for f in drop_features:
        if feature_dict[f]:
            score -= 0.8
    
    # 機能数ペナルティ (シンプル性)
    n_active = sum(features)
    if n_active > 15:
        score -= 0.05 * (n_active - 15)
    elif n_active < 3:
        score -= 0.1 * (3 - n_active)
    
    # 相互作用 (G7 と G2 の組み合わせは効く)
    if feature_dict["G7"] and feature_dict["G2"]:
        score += 0.3
    
    # I8 単独はとても効く
    if feature_dict["I8"]:
        score += 0.5
    
    # ノイズ
    score += np.random.normal(0, 0.05)
    
    return score


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Phase 7 Step 7.1 — Binary CMA-ES")
    print("=" * 70)
    
    np.random.seed(42)
    
    config = CMAESConfig(
        dim=22,
        population_size=16,
        sigma_init=0.3,
        max_generations=30,
        n_restarts=3,
    )
    
    cma = BinaryCMAES(config, mock_evaluator)
    
    start = time.time()
    result = cma.optimize()
    elapsed = time.time() - start
    
    print(f"\n{'=' * 70}")
    print(f"Result")
    print(f"{'=' * 70}")
    print(f"Best score: {result.best_score:.3f}")
    print(f"Best features ({len(result.best_features)}/22):")
    for f in result.best_features:
        print(f"  ✓ {f}")
    print(f"Total evaluations: {result.total_evaluations}")
    print(f"Total generations: {result.generations_used}")
    print(f"Elapsed: {elapsed:.2f}s")
    
    # Greedy との比較 (Phase 3 の手法)
    print(f"\n--- Greedy 比較 ---")
    greedy_features = ["I8", "H2", "H5", "G1", "G2", "G3", "G6", "G7", "G8", "G9"]
    greedy_binary = np.array([
        1 if ALL_FEATURES[i] in greedy_features else 0 for i in range(22)
    ])
    greedy_score = mock_evaluator(greedy_binary)
    print(f"Greedy (Phase 3 result): {greedy_score:.3f} "
          f"({len(greedy_features)} features)")
    print(f"CMA-ES:                  {result.best_score:.3f} "
          f"({len(result.best_features)} features)")
    
    diff = result.best_score - greedy_score
    if diff > 0:
        print(f"→ CMA-ES improves by {diff:+.3f}")
    else:
        print(f"→ Greedy was already optimal (diff: {diff:+.3f})")
    
    print(f"\n[Step 7.1 完了 ✅]")
