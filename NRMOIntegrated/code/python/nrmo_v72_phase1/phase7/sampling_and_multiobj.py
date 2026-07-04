"""
NRMO Phase 7 — Step 7.2 + 7.3 + 7.4

Step 7.2: Latin Hypercube Sampling (流木 8: curse of dimensionality)
Step 7.3: Multi-objective Optimization (流木 9: Goodhart's Law 準備)
Step 7.4: Stress Test Infrastructure (流木 25: Black Swan 準備)

11 次元の World Parameter 空間を効率的にカバーする基盤。
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Callable, Optional
import numpy as np


# ============================================================
# Step 7.2: Latin Hypercube Sampling
# ============================================================

class LatinHypercubeSampler:
    """11 次元 World Parameter 空間の効率的サンプリング
    
    Random Sampling との違い:
      - Random: 偶発的な集中、未探索領域あり
      - LHS: 各次元を等分割し、coverage を保証
    
    Curse of dimensionality 対策:
      11 次元では完全グリッドは指数的に困難 (例: 10^11 cells)
      LHS は N サンプルで各次元 N 分割を保証
    """
    
    # World Parameter の各次元の range
    PARAM_RANGES = {
        "opportunity_arrival_rate": (0.01, 0.55),
        "opportunity_window_duration": (1.0, 30.0),
        "ruin_probability_base": (0.001, 0.15),
        "resource_decay_rate": (0.01, 0.06),
        "physical_decay_rate": (0.01, 0.06),
        "emotional_volatility": (0.05, 0.55),
        "irreversibility_propensity": (0.05, 0.75),
        "recovery_rate": (0.005, 0.10),
        "competitive_pressure": (0.05, 0.95),
        "information_uncertainty": (0.05, 0.70),
        "noise_amplitude": (0.05, 0.40),
    }
    
    DIM_NAMES = list(PARAM_RANGES.keys())
    DIM = len(DIM_NAMES)  # 11
    
    def __init__(self, n_samples: int, seed: int = 0):
        self.n_samples = n_samples
        self.rng = np.random.RandomState(seed)
    
    def sample(self) -> List[Dict[str, float]]:
        """LHS で n_samples 個の世界パラメータを生成"""
        # 各次元を n_samples 分割し、permutation
        latin_square = np.zeros((self.n_samples, self.DIM))
        
        for d in range(self.DIM):
            # 各次元の n_samples 個の interval の中央点
            intervals = np.linspace(0, 1, self.n_samples + 1)
            midpoints = (intervals[:-1] + intervals[1:]) / 2
            # Random permutation で次元間のランダム性
            shuffled = self.rng.permutation(midpoints)
            # 少しランダムノイズを加える
            jitter = self.rng.uniform(-0.5 / self.n_samples,
                                      0.5 / self.n_samples,
                                      self.n_samples)
            latin_square[:, d] = shuffled + jitter
            latin_square[:, d] = np.clip(latin_square[:, d], 0, 1)
        
        # 各 row を WorldParameters にマッピング
        samples = []
        for row in latin_square:
            params = {}
            for d, name in enumerate(self.DIM_NAMES):
                low, high = self.PARAM_RANGES[name]
                params[name] = low + row[d] * (high - low)
            samples.append(params)
        
        return samples
    
    def diversity_metric(self, samples: List[Dict]) -> float:
        """サンプルの多様性 (最近隣距離の平均)"""
        if len(samples) < 2:
            return 0.0
        
        # 正規化された数値配列に変換
        matrix = []
        for s in samples:
            row = []
            for name in self.DIM_NAMES:
                low, high = self.PARAM_RANGES[name]
                normalized = (s[name] - low) / (high - low)
                row.append(normalized)
            matrix.append(row)
        matrix = np.array(matrix)
        
        # ペア距離の最小値の平均
        from scipy.spatial.distance import pdist, squareform
        distances = squareform(pdist(matrix))
        np.fill_diagonal(distances, np.inf)
        nearest_distances = distances.min(axis=1)
        return float(nearest_distances.mean())


# ============================================================
# Step 7.3: Multi-objective Optimization (NSGA-II 簡易版)
# ============================================================

@dataclass
class MultiObjectiveSolution:
    """多目的最適化の解候補"""
    parameters: np.ndarray             # 機能フラグ (22D binary)
    objectives: Dict[str, float]       # 複数の目的値
    rank: int = 0                      # Pareto rank
    crowding_distance: float = 0.0
    
    def dominates(self, other: "MultiObjectiveSolution") -> bool:
        """この解が other を Pareto 支配するか"""
        at_least_one_better = False
        for key in self.objectives:
            if self.objectives[key] < other.objectives[key]:
                return False
            if self.objectives[key] > other.objectives[key]:
                at_least_one_better = True
        return at_least_one_better


class MultiObjectiveOptimizer:
    """多目的最適化 (NSGA-II 簡易版)
    
    Goodhart's Law 対策:
      単一スコアの最大化ではなく、複数目的の Pareto front 探索
      
    例: 4 つの目的
      objective_1: 訓練分布内の平均改善 (Score 高い)
      objective_2: 訓練分布外の worst case (Robust)
      objective_3: シンプル性 (機能数少)
      objective_4: 計算速度 (実行時間短)
      
    Pareto front 上のすべての解は「ある意味で最良」
    どれを採用するかは Vision 次第
    """
    
    def __init__(self, n_objectives: int, evaluator: Callable,
                 population_size: int = 30, max_generations: int = 20):
        self.n_objectives = n_objectives
        self.evaluator = evaluator
        self.population_size = population_size
        self.max_generations = max_generations
        self.dim = 22
    
    def evaluate(self, individuals: List[np.ndarray]) -> List[MultiObjectiveSolution]:
        """個体を評価"""
        solutions = []
        for ind in individuals:
            objectives = self.evaluator(ind)
            solutions.append(MultiObjectiveSolution(
                parameters=ind.copy(),
                objectives=objectives,
            ))
        return solutions
    
    def non_dominated_sort(self, solutions: List[MultiObjectiveSolution]
                            ) -> List[List[int]]:
        """非支配ソート (Pareto fronts に分割)"""
        fronts = [[]]
        n_dominated = [0] * len(solutions)
        dominates_list = [[] for _ in solutions]
        
        for i, p in enumerate(solutions):
            for j, q in enumerate(solutions):
                if i == j:
                    continue
                if p.dominates(q):
                    dominates_list[i].append(j)
                elif q.dominates(p):
                    n_dominated[i] += 1
            
            if n_dominated[i] == 0:
                p.rank = 0
                fronts[0].append(i)
        
        front_idx = 0
        while fronts[front_idx]:
            next_front = []
            for i in fronts[front_idx]:
                for j in dominates_list[i]:
                    n_dominated[j] -= 1
                    if n_dominated[j] == 0:
                        solutions[j].rank = front_idx + 1
                        next_front.append(j)
            front_idx += 1
            fronts.append(next_front)
        
        return [f for f in fronts if f]
    
    def crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
        """Uniform crossover"""
        mask = np.random.rand(self.dim) < 0.5
        child = np.where(mask, parent1, parent2)
        return child
    
    def mutate(self, individual: np.ndarray, mutation_rate: float = 0.1) -> np.ndarray:
        """Bit-flip mutation"""
        mask = np.random.rand(self.dim) < mutation_rate
        child = individual.copy()
        child[mask] = 1 - child[mask]
        return child
    
    def optimize(self) -> List[MultiObjectiveSolution]:
        """NSGA-II 簡易版"""
        # 初期 population (random)
        population = [
            np.random.randint(0, 2, self.dim) for _ in range(self.population_size)
        ]
        solutions = self.evaluate(population)
        fronts = self.non_dominated_sort(solutions)
        
        for gen in range(self.max_generations):
            # Tournament selection + crossover + mutation
            offspring = []
            while len(offspring) < self.population_size:
                # Tournament
                i, j = np.random.choice(len(solutions), 2, replace=False)
                parent1 = solutions[i] if solutions[i].rank < solutions[j].rank \
                          else solutions[j]
                k, l = np.random.choice(len(solutions), 2, replace=False)
                parent2 = solutions[k] if solutions[k].rank < solutions[l].rank \
                          else solutions[l]
                
                child = self.crossover(parent1.parameters, parent2.parameters)
                child = self.mutate(child, mutation_rate=0.1)
                offspring.append(child)
            
            # Combine and select best
            offspring_solutions = self.evaluate(offspring)
            combined = solutions + offspring_solutions
            fronts = self.non_dominated_sort(combined)
            
            # Elitist selection (top fronts)
            new_population = []
            for front in fronts:
                if len(new_population) + len(front) <= self.population_size:
                    new_population.extend([combined[i] for i in front])
                else:
                    # 残り枠を crowding distance で選択 (簡略化: random)
                    remaining = self.population_size - len(new_population)
                    selected = np.random.choice(front, remaining, replace=False)
                    new_population.extend([combined[i] for i in selected])
                    break
            
            solutions = new_population
        
        # Pareto front を返す
        fronts = self.non_dominated_sort(solutions)
        if fronts:
            pareto_front = [solutions[i] for i in fronts[0]]
        else:
            pareto_front = []
        return pareto_front


# ============================================================
# Step 7.4: Stress Test Infrastructure (Heavy-tailed)
# ============================================================

class HeavyTailedSampler:
    """Heavy-tailed 分布からの World Parameter サンプリング
    
    Black Swan 対策:
      通常分布 (Normal/Uniform) では極端事象が表現できない
      Heavy-tailed (Cauchy, Pareto) で極稀の極端値も含めてサンプル
    """
    
    def __init__(self, base_sampler: LatinHypercubeSampler, 
                 tail_probability: float = 0.05,
                 seed: int = 0):
        """
        tail_probability: 各サンプルが extreme 化される確率
        """
        self.base_sampler = base_sampler
        self.tail_probability = tail_probability
        self.rng = np.random.RandomState(seed)
    
    def sample_extreme_value(self, low: float, high: float) -> float:
        """Range 外の extreme 値を生成"""
        # Pareto 分布で tail 値を生成 (parameter alpha=1.5 で heavy tail)
        pareto_val = self.rng.pareto(1.5) * (high - low) * 0.5
        # Range の境界付近、または外側の値
        if self.rng.random() < 0.5:
            return min(high * 1.5, high + pareto_val)
        else:
            return max(low * 0.3, low - pareto_val) if low > 0 else low - pareto_val
    
    def sample_with_extremes(self, n_normal: int, n_extreme: int) -> List[Dict]:
        """通常 + extreme の混合サンプリング"""
        # 通常 LHS サンプル
        normal_samples = LatinHypercubeSampler(
            n_normal, seed=int(self.rng.randint(10000))
        ).sample()
        
        # Extreme サンプル: 1 次元だけ extreme 値、他は LHS
        extreme_samples = []
        for _ in range(n_extreme):
            params = LatinHypercubeSampler(
                1, seed=int(self.rng.randint(10000))
            ).sample()[0]
            
            # ランダムに 1 次元を選んで extreme 化
            extreme_dim = self.rng.choice(LatinHypercubeSampler.DIM_NAMES)
            low, high = LatinHypercubeSampler.PARAM_RANGES[extreme_dim]
            params[extreme_dim] = self.sample_extreme_value(low, high)
            
            extreme_samples.append(params)
        
        return normal_samples + extreme_samples
    
    def black_swan_scenarios(self, n: int = 5) -> List[Dict]:
        """Black Swan シナリオ生成: 複数次元同時 extreme"""
        scenarios = []
        for i in range(n):
            params = LatinHypercubeSampler(
                1, seed=int(self.rng.randint(10000))
            ).sample()[0]
            
            # 3-5 次元を同時に extreme 化
            n_extreme_dims = self.rng.randint(3, 6)
            extreme_dims = self.rng.choice(
                LatinHypercubeSampler.DIM_NAMES, n_extreme_dims, replace=False
            )
            
            for dim in extreme_dims:
                low, high = LatinHypercubeSampler.PARAM_RANGES[dim]
                params[dim] = self.sample_extreme_value(low, high)
            
            params["_black_swan"] = True
            params["_extreme_dims"] = list(extreme_dims)
            scenarios.append(params)
        
        return scenarios


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Phase 7 Step 7.2 + 7.3 + 7.4 動作確認")
    print("=" * 70)
    
    # Step 7.2: LHS
    print("\n--- Step 7.2: Latin Hypercube Sampling ---")
    lhs = LatinHypercubeSampler(n_samples=20, seed=42)
    samples = lhs.sample()
    diversity = lhs.diversity_metric(samples)
    
    print(f"Generated {len(samples)} samples (11D)")
    print(f"Diversity metric: {diversity:.4f}")
    print(f"Sample 1: {dict(list(samples[0].items())[:4])}...")
    print(f"Sample 10: {dict(list(samples[10].items())[:4])}...")
    
    # Step 7.3: Multi-objective
    print("\n--- Step 7.3: Multi-objective Optimization ---")
    
    def mock_multi_eval(features: np.ndarray) -> Dict[str, float]:
        """4 目的の mock 評価"""
        n_active = int(features.sum())
        
        # 目的 1: 訓練分布内の平均改善 (機能多いほど良い)
        score = n_active * 0.5 + np.random.normal(0, 0.2)
        
        # 目的 2: Robust (機能少なめが良い)
        robust = -abs(n_active - 8) * 0.3 + np.random.normal(0, 0.2)
        
        # 目的 3: シンプル性 (機能少ない方が良い)
        simplicity = -n_active * 0.1
        
        # 目的 4: 計算速度 (機能少ない方が速い)
        speed = -n_active * 0.05
        
        return {
            "score": score,
            "robustness": robust,
            "simplicity": simplicity,
            "speed": speed,
        }
    
    optimizer = MultiObjectiveOptimizer(
        n_objectives=4,
        evaluator=mock_multi_eval,
        population_size=30,
        max_generations=15,
    )
    
    np.random.seed(42)
    pareto = optimizer.optimize()
    
    print(f"Pareto front size: {len(pareto)}")
    print(f"Top 3 solutions:")
    sorted_pareto = sorted(pareto, key=lambda s: -s.objectives["score"])
    for i, sol in enumerate(sorted_pareto[:3]):
        active = [
            "I8 I9 I10 I11 I12 H1 H2 H3 H4 H5 H6 H7 G1 G2 G3 G4 G5 G6 G7 G8 G9 G10".split()[j]
            for j, v in enumerate(sol.parameters) if v
        ]
        print(f"  Solution {i+1}: {len(active)} features")
        print(f"    objectives: {sol.objectives}")
    
    # Step 7.4: Heavy-tailed Sampling
    print("\n--- Step 7.4: Stress Test Infrastructure ---")
    heavy = HeavyTailedSampler(lhs, tail_probability=0.05, seed=42)
    
    mixed_samples = heavy.sample_with_extremes(n_normal=10, n_extreme=5)
    black_swans = heavy.black_swan_scenarios(n=3)
    
    print(f"Mixed samples (normal + extreme): {len(mixed_samples)}")
    print(f"Black Swan scenarios: {len(black_swans)}")
    
    print(f"\nBlack Swan example:")
    bs = black_swans[0]
    print(f"  Extreme dims: {bs.get('_extreme_dims', [])}")
    for dim in bs.get('_extreme_dims', [])[:3]:
        original_low, original_high = lhs.PARAM_RANGES[dim]
        print(f"  {dim}: {bs[dim]:.3f} (normal range: [{original_low}, {original_high}])")
    
    print(f"\n[Step 7.2 + 7.3 + 7.4 完了 ✅]")
