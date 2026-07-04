"""
NRMO Phase 8 — 構造的再設計

対処する流木:
  流木 1: 最適化 vs 制約満足 (CMDP 化)
  流木 2: MDP vs POMDP (Belief state 導入)
  流木 3: Belief 更新欠落 (Bayesian online inference)
  流木 13: Multiple comparisons
  流木 14: Distribution shift

設計思想:
  「世界は隠れた変数を持つ」を明示的にモデル化
  「破滅を避ける」をハード制約として実装
  Belief 状態を online update し、不確実性を保持
  
Phase 11 統合:
  Knightian (11.6) との連携: belief が確率分布で表現できない場合
  Skin in the Game (11.4): belief の不確実性に応じた stake
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
import numpy as np
from scipy import stats


# ============================================================
# Step 8.1: POMDP Framework
# ============================================================

@dataclass
class Observation:
    """エージェントが観測する情報"""
    state_vector: np.ndarray  # 6D state (R, E, G, O, K, X)
    timestamp: int
    metadata: Dict = field(default_factory=dict)


@dataclass
class HiddenWorldState:
    """エージェントには直接見えない隠れた世界状態"""
    # World parameters (11D)
    world_params: Dict[str, float] = field(default_factory=dict)
    # その他の隠れた変数
    hidden_state: Dict = field(default_factory=dict)


class POMDPFormulation:
    """POMDP の形式的定義
    
    Tuple <S, A, T, R, Ω, O, γ>:
      S: 隠れ状態空間 (HiddenWorldState)
      A: 行動空間 (Action)
      T: 状態遷移 P(s'|s,a)
      R: 報酬関数 (制約付き)
      Ω: 観測空間 (Observation)
      O: 観測モデル P(o|s', a)
      γ: 割引率
    """
    
    def __init__(self, 
                 state_dim: int = 11,    # 世界パラメータの次元
                 obs_dim: int = 6,        # 観測の次元
                 action_dim: int = 15):   # 5 intent × 3 strength
        self.state_dim = state_dim
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.gamma = 0.95  # 割引率
    
    def transition_model(self, hidden_state: HiddenWorldState, 
                          action) -> HiddenWorldState:
        """状態遷移 (概念実装)"""
        # World parameters は通常変化しないが、若干のドリフトを許容
        new_params = {
            k: v + np.random.normal(0, v * 0.01)  # 1% drift
            for k, v in hidden_state.world_params.items()
        }
        return HiddenWorldState(world_params=new_params)
    
    def observation_model(self, hidden_state: HiddenWorldState,
                           obs_state: np.ndarray) -> float:
        """観測モデル P(o|s) の対数尤度"""
        # World params に応じた observation の尤度
        # 簡略化: noise_amplitude が高いほど obs が noisy
        noise = hidden_state.world_params.get("noise_amplitude", 0.1)
        log_likelihood = -np.sum((obs_state - 50) ** 2) / (2 * (noise * 100) ** 2)
        return log_likelihood


# ============================================================
# Step 8.2: Belief State + Bayesian Online Update
# ============================================================

@dataclass
class BeliefState:
    """エージェントの信念状態 (隠れ世界に関する確率分布)
    
    実装: Particle Filter (N 個の粒子で分布を近似)
    """
    particles: List[Dict[str, float]]  # 各粒子は world_params の dict
    weights: np.ndarray                 # 各粒子の重み
    
    @classmethod
    def initialize_uniform(cls, n_particles: int = 100,
                            param_ranges: Optional[Dict] = None,
                            rng: Optional[np.random.Generator] = None) -> "BeliefState":
        """均一事前分布で初期化 (rng で再現性確保)"""
        if rng is None:
            rng = np.random.default_rng()
        if param_ranges is None:
            # 標準的な範囲
            param_ranges = {
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
        
        particles = []
        for _ in range(n_particles):
            p = {}
            for name, (low, high) in param_ranges.items():
                p[name] = float(rng.uniform(low, high))
            particles.append(p)
        
        weights = np.ones(n_particles) / n_particles
        return cls(particles=particles, weights=weights)
    
    def mean_estimate(self) -> Dict[str, float]:
        """重み付き平均推定"""
        if not self.particles:
            return {}
        keys = list(self.particles[0].keys())
        result = {}
        for k in keys:
            values = np.array([p[k] for p in self.particles])
            result[k] = float(np.sum(values * self.weights))
        return result
    
    def variance_estimate(self) -> Dict[str, float]:
        """不確実性 (分散) の推定"""
        means = self.mean_estimate()
        result = {}
        for k in means:
            values = np.array([p[k] for p in self.particles])
            var = np.sum(self.weights * (values - means[k]) ** 2)
            result[k] = float(var)
        return result
    
    def entropy(self) -> float:
        """信念のエントロピー (不確実性指標)"""
        return -np.sum(self.weights * np.log(self.weights + 1e-10))


class BayesianUpdater:
    """Particle Filter による信念の online update"""
    
    def __init__(self, pomdp: POMDPFormulation, n_particles: int = 100,
                  rng: Optional[np.random.Generator] = None):
        self.pomdp = pomdp
        self.n_particles = n_particles
        self.rng = rng if rng is not None else np.random.default_rng()
        self.belief: Optional[BeliefState] = None
        self.update_history = []
    
    def initialize(self, param_ranges: Optional[Dict] = None):
        """信念を初期化 (uniform prior)"""
        self.belief = BeliefState.initialize_uniform(
            self.n_particles, param_ranges, rng=self.rng
        )
    
    def update(self, observation: Observation, action=None):
        """新観測で信念を update"""
        if self.belief is None:
            self.initialize()
        
        # 各粒子の尤度を計算
        log_weights = []
        for particle in self.belief.particles:
            hidden = HiddenWorldState(world_params=particle)
            log_lik = self.pomdp.observation_model(hidden, observation.state_vector)
            log_weights.append(log_lik)
        
        # log-sum-exp トリックで正規化
        log_weights = np.array(log_weights)
        log_weights -= log_weights.max()  # 数値安定性
        new_weights = np.exp(log_weights) * self.belief.weights
        new_weights /= new_weights.sum() + 1e-10
        
        self.belief.weights = new_weights
        
        # Resampling (effective sample size が小さくなったら)
        ess = 1.0 / np.sum(new_weights ** 2)
        if ess < self.n_particles * 0.5:
            self._resample()
        
        # 更新履歴
        self.update_history.append({
            "timestamp": observation.timestamp,
            "ess": float(ess),
            "entropy": self.belief.entropy(),
            "mean_estimate": self.belief.mean_estimate(),
        })
    
    def _resample(self):
        """重みに従って particle を resample (self.rng 使用で再現性)"""
        indices = self.rng.choice(
            len(self.belief.particles),
            size=self.n_particles,
            replace=True,
            p=self.belief.weights
        )
        new_particles = [
            dict(self.belief.particles[i]) for i in indices
        ]
        # 少しのジッタを加えて多様性維持
        for p in new_particles:
            for k, v in p.items():
                p[k] = v + float(self.rng.normal(0, abs(v) * 0.01))
        
        self.belief.particles = new_particles
        self.belief.weights = np.ones(self.n_particles) / self.n_particles
    
    def get_belief_summary(self) -> Dict:
        """現在の信念のサマリー"""
        if self.belief is None:
            return {}
        return {
            "mean": self.belief.mean_estimate(),
            "variance": self.belief.variance_estimate(),
            "entropy": self.belief.entropy(),
            "n_updates": len(self.update_history),
        }


# ============================================================
# Step 8.3: CMDP (Constrained MDP)
# ============================================================

@dataclass
class Constraint:
    """ハード制約"""
    name: str
    threshold: float
    operator: str  # "<", ">", "<=", ">="
    description: str
    
    def is_violated(self, value: float) -> bool:
        if self.operator == "<":
            return value >= self.threshold
        elif self.operator == ">":
            return value <= self.threshold
        elif self.operator == "<=":
            return value > self.threshold
        elif self.operator == ">=":
            return value < self.threshold
        return False


class CMDPFormulation:
    """Constrained MDP
    
    通常 MDP:
      max E[Σ γ^t r_t]
    
    CMDP:
      max E[Σ γ^t r_t]
      s.t. E[Σ γ^t c_i_t] ≤ d_i for all constraints i
    
    NRMO 本旨:
      不可逆破滅 = ハード制約
      これは「ペナルティ」ではなく「禁止」
    """
    
    def __init__(self):
        # NRMO の標準制約
        self.constraints = [
            Constraint(
                name="ruin_probability",
                threshold=0.01,  # 1% 以下
                operator="<=",
                description="不可逆破滅率は 1% を超えてはならない",
            ),
            Constraint(
                name="optionality_min",
                threshold=10.0,  # 最低 10 unit
                operator=">=",
                description="選択肢の総量は閾値以上を保つ",
            ),
            Constraint(
                name="vision_drift",
                threshold=0.3,  # 30% 以下
                operator="<=",
                description="Vision からの累積ドリフトは 30% 以下",
            ),
        ]
    
    def add_constraint(self, constraint: Constraint):
        self.constraints.append(constraint)
    
    def check_action(self, action, predicted_outcome: Dict) -> Tuple[bool, List[str]]:
        """行動が制約を満たすかチェック"""
        violations = []
        for c in self.constraints:
            value = predicted_outcome.get(c.name, 0.0)
            if c.is_violated(value):
                violations.append(f"{c.name}: {value} violates {c.operator}{c.threshold}")
        
        is_feasible = len(violations) == 0
        return is_feasible, violations
    
    def feasibility_filter(self, candidates: List, 
                            predicted_outcomes: List[Dict]) -> List:
        """制約を満たす候補だけを返す"""
        feasible = []
        for cand, outcome in zip(candidates, predicted_outcomes):
            is_feasible, _ = self.check_action(cand, outcome)
            if is_feasible:
                feasible.append(cand)
        return feasible


# ============================================================
# Step 8.4: Distribution Shift Handling
# ============================================================

class DistributionShiftMonitor:
    """訓練分布と現在の観測分布の乖離を検出"""
    
    def __init__(self, n_reference_samples: int = 100):
        self.reference_samples = []
        self.recent_samples = []
        self.n_reference = n_reference_samples
    
    def add_reference(self, obs: Observation):
        """訓練/参照分布のサンプル"""
        self.reference_samples.append(obs.state_vector.copy())
        if len(self.reference_samples) > self.n_reference:
            self.reference_samples.pop(0)
    
    def add_recent(self, obs: Observation):
        """最近の観測"""
        self.recent_samples.append(obs.state_vector.copy())
        # 直近 30 個のみ保持
        if len(self.recent_samples) > 30:
            self.recent_samples.pop(0)
    
    def detect_shift(self) -> Tuple[bool, float, str]:
        """分布シフトを検出
        
        Returns: (is_shifted, severity, reason)
        """
        if len(self.reference_samples) < 20 or len(self.recent_samples) < 10:
            return False, 0.0, "Insufficient data"
        
        ref = np.array(self.reference_samples)
        recent = np.array(self.recent_samples)
        
        # 各次元で KS test
        severities = []
        for d in range(ref.shape[1]):
            stat, p_value = stats.ks_2samp(ref[:, d], recent[:, d])
            severities.append(stat)
        
        max_severity = max(severities)
        
        if max_severity > 0.4:
            return True, max_severity, f"Strong shift detected (KS={max_severity:.3f})"
        elif max_severity > 0.2:
            return True, max_severity, f"Mild shift detected (KS={max_severity:.3f})"
        return False, max_severity, "No significant shift"


# ============================================================
# Step 8.5: Multiple Comparisons Correction
# ============================================================

class MultipleComparisonsCorrector:
    """複数比較の補正
    
    22 機能 × 25 cells × 8 基準 = 4,400 検定
    α=0.05 だと Type I error が大量発生
    
    Bonferroni: 厳しいが安全
    Holm-Bonferroni: より powerful
    Benjamini-Hochberg: FDR control
    """
    
    @staticmethod
    def bonferroni(p_values: List[float], alpha: float = 0.05) -> List[bool]:
        """Bonferroni 補正
        
        Returns: 各 test が有意か (True/False)
        """
        adjusted_alpha = alpha / len(p_values)
        return [p < adjusted_alpha for p in p_values]
    
    @staticmethod
    def holm_bonferroni(p_values: List[float], alpha: float = 0.05) -> List[bool]:
        """Holm-Bonferroni 補正"""
        n = len(p_values)
        sorted_indices = np.argsort(p_values)
        sorted_p = np.array(p_values)[sorted_indices]
        
        # 各 sorted p に対し alpha/(n-i) を閾値
        results_sorted = []
        for i in range(n):
            threshold = alpha / (n - i)
            if sorted_p[i] < threshold:
                results_sorted.append(True)
            else:
                # ここから先は全て False (sequential)
                results_sorted.extend([False] * (n - i))
                break
        
        # 元の順序に戻す
        results = [False] * n
        for i, idx in enumerate(sorted_indices):
            results[idx] = results_sorted[i] if i < len(results_sorted) else False
        
        return results
    
    @staticmethod
    def benjamini_hochberg(p_values: List[float], 
                            fdr: float = 0.10) -> List[bool]:
        """Benjamini-Hochberg FDR control"""
        n = len(p_values)
        sorted_indices = np.argsort(p_values)
        sorted_p = np.array(p_values)[sorted_indices]
        
        # 各 sorted p に対し (i/n)*fdr を閾値
        results_sorted = [False] * n
        max_significant_i = -1
        for i in range(n):
            threshold = (i + 1) / n * fdr
            if sorted_p[i] < threshold:
                max_significant_i = i
        
        for i in range(max_significant_i + 1):
            results_sorted[i] = True
        
        results = [False] * n
        for i, idx in enumerate(sorted_indices):
            results[idx] = results_sorted[i]
        
        return results


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Phase 8 — 構造的再設計 動作確認")
    print("=" * 70)
    
    np.random.seed(42)
    
    # === Step 8.1 + 8.2: POMDP + Bayesian Update ===
    print("\n--- Step 8.1 + 8.2: POMDP Belief Update ---")
    
    pomdp = POMDPFormulation()
    updater = BayesianUpdater(pomdp, n_particles=100)
    updater.initialize()
    
    initial_summary = updater.get_belief_summary()
    print(f"Initial belief entropy: {initial_summary['entropy']:.3f}")
    print(f"Initial belief variance (noise_amp): "
          f"{initial_summary['variance'].get('noise_amplitude', 0):.4f}")
    
    # 観測を 10 回与えて update
    true_noise = 0.2
    for t in range(10):
        # シミュレートされた観測 (true noise 0.2 で生成)
        obs_state = np.array([
            50 + np.random.normal(0, true_noise * 30),
            70 + np.random.normal(0, true_noise * 30),
            65 + np.random.normal(0, true_noise * 30),
            45 + np.random.normal(0, true_noise * 30),
            55 + np.random.normal(0, true_noise * 30),
            25 + np.random.normal(0, true_noise * 30),
        ])
        obs = Observation(state_vector=obs_state, timestamp=t)
        updater.update(obs)
    
    final_summary = updater.get_belief_summary()
    print(f"After 10 obs: entropy={final_summary['entropy']:.3f}")
    print(f"Belief about noise_amplitude: "
          f"mean={final_summary['mean'].get('noise_amplitude', 0):.4f}, "
          f"var={final_summary['variance'].get('noise_amplitude', 0):.4f}")
    print(f"  (true value was {true_noise})")
    
    # === Step 8.3: CMDP ===
    print("\n--- Step 8.3: CMDP (Constrained MDP) ---")
    
    cmdp = CMDPFormulation()
    print(f"Constraints: {len(cmdp.constraints)}")
    for c in cmdp.constraints:
        print(f"  {c.name}: {c.operator} {c.threshold}")
    
    # ある候補行動について制約チェック
    candidate_outcome_safe = {
        "ruin_probability": 0.005,
        "optionality_min": 25.0,
        "vision_drift": 0.15,
    }
    is_feasible, viol = cmdp.check_action(None, candidate_outcome_safe)
    print(f"\nSafe candidate: feasible={is_feasible}")
    
    candidate_outcome_risky = {
        "ruin_probability": 0.05,  # 違反
        "optionality_min": 5.0,    # 違反
        "vision_drift": 0.20,
    }
    is_feasible, viol = cmdp.check_action(None, candidate_outcome_risky)
    print(f"Risky candidate: feasible={is_feasible}")
    print(f"  Violations: {viol}")
    
    # === Step 8.4: Distribution Shift ===
    print("\n--- Step 8.4: Distribution Shift Monitor ---")
    
    monitor = DistributionShiftMonitor(n_reference_samples=50)
    
    # Reference (training 分布)
    for _ in range(50):
        ref_obs = Observation(
            state_vector=np.random.normal(50, 10, 6),
            timestamp=0,
        )
        monitor.add_reference(ref_obs)
    
    # 最近の観測 (同分布)
    for _ in range(20):
        recent_obs = Observation(
            state_vector=np.random.normal(50, 10, 6),
            timestamp=0,
        )
        monitor.add_recent(recent_obs)
    
    is_shifted, sev, reason = monitor.detect_shift()
    print(f"Same distribution: shifted={is_shifted}, severity={sev:.3f}")
    
    # Shift simulation
    monitor.recent_samples = []
    for _ in range(20):
        shifted_obs = Observation(
            state_vector=np.random.normal(70, 15, 6),  # 異なる分布
            timestamp=0,
        )
        monitor.add_recent(shifted_obs)
    
    is_shifted, sev, reason = monitor.detect_shift()
    print(f"Different distribution: shifted={is_shifted}, severity={sev:.3f}")
    print(f"  {reason}")
    
    # === Step 8.5: Multiple Comparisons ===
    print("\n--- Step 8.5: Multiple Comparisons Correction ---")
    
    # 100 個の p_value (10 個は真に有意、90 個は null)
    np.random.seed(0)
    p_values_significant = np.random.uniform(0, 0.01, 10)
    p_values_null = np.random.uniform(0, 1, 90)
    all_p = np.concatenate([p_values_significant, p_values_null])
    
    bonf = MultipleComparisonsCorrector.bonferroni(list(all_p), alpha=0.05)
    holm = MultipleComparisonsCorrector.holm_bonferroni(list(all_p), alpha=0.05)
    bh = MultipleComparisonsCorrector.benjamini_hochberg(list(all_p), fdr=0.10)
    
    print(f"Significant (Bonferroni): {sum(bonf)}/{len(all_p)}")
    print(f"Significant (Holm):       {sum(holm)}/{len(all_p)}")
    print(f"Significant (BH FDR=10%): {sum(bh)}/{len(all_p)}")
    print(f"  (10 個が真に有意のはず)")
    
    print(f"\n[Phase 8 完了 ✅]")
