"""
core/sociable_essence_v2.py

Sociable Numbers エッセンス v2 — 数理的深化.

Per Zarameさん 指示: 案 Q + 案 S

3 新 mechanisms:

A. ThreadConstraintPropagator (kappa-divisor 風 cascade)
   数論: D = B²(d+e)² - 2ABde, kappa | D
         → kappa 選択で g, L が自動決定
   NRMO: Thread budget K で primary thread 選択
         → remaining budget で secondary/suppressed thread を cascade 配分

B. EqualSigmaVerifier (Equal-Sigma aliquot 風厳密検証)
   数論: σ(N) を proper divisor 和で厳密計算 → P0 verification
   NRMO: action 後の projected state aliquot 和を計算
         → ruin boundary との距離を厳密測定
         Revalidation Gate の強化

C. SuccessfulPatternBooster (p3-residue 逆応用)
   数論: Failed primes q を pre-reject
   NRMO: Successful (thread, state-sig) を bonus boost
         学習的 thread weight reinforcement
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import deque, Counter
from enum import Enum

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action


# ============================================================
# A. ThreadConstraintPropagator (kappa-divisor cascade)
# ============================================================

@dataclass
class PropagatedWeights:
    """Cascade 配分結果"""
    primary_thread: str
    primary_weight: float
    secondary_threads: Dict[str, float]
    suppressed_threads: Dict[str, float]
    total_budget_used: float
    kappa_value: float           # kappa (cascade parameter)
    D_value: float               # D = B²(d+e)² - 2ABde 風
    reason: str = ""


class ThreadConstraintPropagator:
    """Per sociable numbers v6.9: kappa-divisor cascade.
    
    数理:
      D = B²(d+e)² - 2ABde
      kappa | D
      g = (B(d+e) + kappa) / (Ade)
      L = (B(d+e) + D/kappa) / (Ade)
    
    NRMO mapping:
      A, B = scaling constants (set per world type)
      d, e = primary characteristics (state R, X)
      D = "thread budget"
      kappa = primary thread weight (chosen from divisors of D)
      g, L = secondary thread weights (cascade determined)
    """
    
    # Budget constants (normalized 0-1)
    TOTAL_BUDGET_K = 1.5         # sum of all thread weights ≤ K
    PRIMARY_MIN_SHARE = 0.40     # primary が最低この share
    PRIMARY_MAX_SHARE = 0.85     # primary がこの share 以下
    SECONDARY_MAX_COUNT = 3      # secondary thread 数
    
    def propagate(self, primary_thread_name: str,
                    primary_initial_weight: float,
                    candidate_thread_names: List[str],
                    state: WorldState,
                    world_type: str = "unknown"
                    ) -> PropagatedWeights:
        """Primary thread weight から残り thread の weight を cascade 決定.
        
        数論の divisor 構造を Thread budget に応用.
        """
        # Compute D (state-dependent budget)
        # D = B²(d+e)² - 2ABde
        #   d, e ← (R, X) を normalize
        #   A, B ← world-dependent scaling
        A, B = self._get_AB(world_type)
        d = state.R / 100.0       # 0-1
        e = state.X / 100.0       # 0-1
        D_raw = (B**2) * ((d + e)**2) - 2 * A * B * d * e
        D = max(0.1, abs(D_raw))   # avoid degenerate
        
        # Kappa: primary weight, must be ≤ D in "divisor space"
        kappa = min(primary_initial_weight, D)
        kappa = max(kappa, self.PRIMARY_MIN_SHARE * self.TOTAL_BUDGET_K)
        kappa = min(kappa, self.PRIMARY_MAX_SHARE * self.TOTAL_BUDGET_K)
        
        # Primary weight
        primary_w = kappa
        
        # Remaining budget for secondary
        remaining = self.TOTAL_BUDGET_K - primary_w
        
        # Secondary cascade: D/kappa style
        secondary_candidates = [t for t in candidate_thread_names if t != primary_thread_name]
        
        # Cascade weight = remaining * (D/kappa) / sum_normalization
        # Simulate divisor structure: each secondary gets D/kappa * (1/(rank+1))
        secondary_weights: Dict[str, float] = {}
        suppressed_weights: Dict[str, float] = {}
        
        if remaining > 0 and secondary_candidates:
            # D/kappa = "complementary divisor"
            complement = D / max(0.01, kappa)
            
            # Rank-based allocation (sociable chain order)
            n_secondary = min(self.SECONDARY_MAX_COUNT, len(secondary_candidates))
            
            # Decreasing weights: 1/(1+rank) normalized
            ranks = list(range(n_secondary))
            decay = [1.0 / (1.0 + r * 0.5) for r in ranks]
            decay_sum = sum(decay)
            
            for i, thread_name in enumerate(secondary_candidates[:n_secondary]):
                w = remaining * (decay[i] / decay_sum) * (complement / max(complement + 0.1, 1.0))
                w = min(w, 0.4)  # cap
                secondary_weights[thread_name] = float(w)
            
            # Remaining threads (beyond secondary) = suppressed
            for thread_name in secondary_candidates[n_secondary:]:
                # Suppression strength based on D - kappa "deficit"
                supp_w = 0.50 + 0.30 * (1.0 - complement / (complement + 1.0))
                suppressed_weights[thread_name] = float(min(supp_w, 0.95))
        else:
            # No room for secondary → all others suppressed
            for thread_name in secondary_candidates:
                suppressed_weights[thread_name] = 0.80
        
        total_used = primary_w + sum(secondary_weights.values())
        
        return PropagatedWeights(
            primary_thread=primary_thread_name,
            primary_weight=primary_w,
            secondary_threads=secondary_weights,
            suppressed_threads=suppressed_weights,
            total_budget_used=total_used,
            kappa_value=float(kappa),
            D_value=float(D),
            reason=f"kappa={kappa:.3f}, D={D:.3f}, complement={D/max(0.01,kappa):.2f}",
        )
    
    def _get_AB(self, world_type: str) -> Tuple[float, float]:
        """A, B scaling constants per world type"""
        if world_type == "drifting":
            return (1.0, 1.5)   # B 大 = D 大 = synthesis 寄り
        elif world_type == "chaotic":
            return (1.2, 1.0)   # A 大 = D 小 = recovery 寄り
        elif world_type == "noisy":
            return (1.0, 1.0)   # neutral
        return (1.0, 1.0)


# ============================================================
# B. EqualSigmaVerifier (P0 strict aliquot check)
# ============================================================

@dataclass
class SigmaVerification:
    """Equal-Sigma 検証結果"""
    passed: bool
    sigma_before: float          # σ(state_before)
    sigma_projected: float       # σ(predicted state_after)
    delta_sigma: float           # 変化
    distance_to_ruin: float      # ruin boundary との距離 (0-1)
    risk_assessment: str         # "safe" | "marginal" | "danger"
    reason: str = ""


class EqualSigmaVerifier:
    """Per sociable numbers v6.9: Equal-Sigma aliquot verification (P0 必須).
    
    数論:
      σ(N) = Σ_{d|N, d<N} d   (proper divisor sum)
      Equal-Sigma: σ(N₁) - N₁ = N₂, σ(N₂) - N₂ = N₁
      → 厳密 P0 verification で full vs near3 を判別
    
    NRMO 応用:
      "aliquot sum" 風 = 「state の生存余裕の合計」
      σ(R, E, G, O, K, X) = weighted sum of available resources
      
      Action 後の projected σ() が:
        - 増加 = 状態改善
        - 減少 = 状態悪化
        - 急激な減少 = ruin proximity
    """
    
    # Resource weights for sigma computation
    RESOURCE_WEIGHTS = {
        "R": 1.5,    # critical resource
        "E": 1.2,
        "G": 1.0,
        "O": 0.8,
        "K": 0.5,
        "X": -1.0,   # X は cost (negative weight)
    }
    
    # Risk thresholds
    SAFE_SIGMA = 200
    MARGINAL_SIGMA = 100
    DANGER_SIGMA = 50
    
    def compute_sigma(self, state: WorldState) -> float:
        """σ(state) = aliquot-sum 風 weighted resource total"""
        return (
            self.RESOURCE_WEIGHTS["R"] * state.R +
            self.RESOURCE_WEIGHTS["E"] * state.E +
            self.RESOURCE_WEIGHTS["G"] * state.G +
            self.RESOURCE_WEIGHTS["O"] * state.O +
            self.RESOURCE_WEIGHTS["K"] * state.K +
            self.RESOURCE_WEIGHTS["X"] * state.X
        )
    
    def verify(self, state_before: WorldState, action: Action,
                projected_delta: Optional[Dict] = None) -> SigmaVerification:
        """Action による state 変化を厳密検証"""
        sigma_before = self.compute_sigma(state_before)
        
        # Projected state
        if projected_delta is None:
            projected_delta = self._estimate_delta(action)
        
        projected = WorldState(
            t=state_before.t,
            R=max(0, min(100, state_before.R + projected_delta.get("R", 0))),
            E=max(0, min(100, state_before.E + projected_delta.get("E", 0))),
            G=max(0, min(100, state_before.G + projected_delta.get("G", 0))),
            O=max(0, min(100, state_before.O + projected_delta.get("O", 0))),
            K=max(0, min(100, state_before.K + projected_delta.get("K", 0))),
            X=max(0, min(100, state_before.X + projected_delta.get("X", 0))),
            cumulative_score=state_before.cumulative_score,
            is_ruined=False,
        )
        
        sigma_projected = self.compute_sigma(projected)
        delta = sigma_projected - sigma_before
        
        # Distance to ruin
        # ruin: R ≤ 0, X ≥ 100
        r_distance = projected.R / 100.0
        x_distance = (100 - projected.X) / 100.0
        distance_to_ruin = min(r_distance, x_distance)
        
        # Risk assessment
        if sigma_projected >= self.SAFE_SIGMA:
            risk = "safe"
        elif sigma_projected >= self.MARGINAL_SIGMA:
            risk = "marginal"
        elif sigma_projected >= self.DANGER_SIGMA:
            risk = "danger"
        else:
            risk = "critical"
        
        # Per P0 Equal-Sigma strict rule: pass only if sigma not severely degraded
        # AND distance to ruin > 0.10
        passed = (sigma_projected >= self.DANGER_SIGMA and 
                    distance_to_ruin >= 0.10 and
                    delta >= -50.0)  # sigma 急減を禁止
        
        return SigmaVerification(
            passed=passed,
            sigma_before=float(sigma_before),
            sigma_projected=float(sigma_projected),
            delta_sigma=float(delta),
            distance_to_ruin=float(distance_to_ruin),
            risk_assessment=risk,
            reason=f"σ:{sigma_before:.1f}→{sigma_projected:.1f}(Δ{delta:+.1f}), "
                    f"d2ruin={distance_to_ruin:.2f}, risk={risk}",
        )
    
    def _estimate_delta(self, action: Action) -> Dict:
        intent_delta = {
            "invest":  {"R": -8, "O": 6, "X": 3},
            "defend":  {"R": -2, "X": -5, "O": -1},
            "explore": {"R": -3, "K": 5, "O": 4},
            "recover": {"R": -1, "E": 8, "G": 6, "O": -2},
            "hold":    {"R": -1, "X": 1, "O": -1},
        }
        strength_mult = {"A": 0.6, "B": 1.0, "C": 1.6}
        base = intent_delta.get(action.intent, {})
        mult = strength_mult.get(action.strength, 1.0)
        return {k: v * mult for k, v in base.items()}


# ============================================================
# C. SuccessfulPatternBooster (p3-residue 逆応用)
# ============================================================

@dataclass
class SuccessRecord:
    """成功 pattern 記録"""
    thread_name: str
    state_signature: str
    reward: float
    step: int


class SuccessfulPatternBooster:
    """Per sociable numbers v6.9: p3-residue avoidance 逆応用.
    
    数論 (元):
      "Failed primes q" → pre-reject `d*L ≡ 1 mod q`
    
    NRMO (逆応用):
      "Successful (thread, state-signature)" → boost
      過去成功した combination を学習的に強化
    
    p3-residue が "failed q → reject" なら、その逆は "success q → boost".
    """
    
    SUCCESS_REWARD_THRESHOLD = 0.5      # この値以上 = success
    BOOST_THRESHOLD = 3                  # success N 回 → boost rule 化
    MAX_BOOST_VALUE = 0.30               # max boost weight
    
    def __init__(self):
        self.success_counts: Counter = Counter()
        self.records: deque = deque(maxlen=200)
        # state_signature -> { thread_name -> boost_weight }
        self.boost_rules: Dict[str, Dict[str, float]] = {}
    
    def _state_signature(self, state: WorldState) -> str:
        def bucket(v):
            if v < 25: return 0
            if v < 50: return 1
            if v < 75: return 2
            return 3
        return (f"R{bucket(state.R)}_E{bucket(state.E)}_"
                f"O{bucket(state.O)}_X{bucket(state.X)}")
    
    def record_success(self, thread_name: str, state: WorldState,
                         reward: float, step: int):
        """成功 pattern を記録"""
        if reward < self.SUCCESS_REWARD_THRESHOLD:
            return
        
        sig = self._state_signature(state)
        key = (thread_name, sig)
        self.success_counts[key] += 1
        
        self.records.append(SuccessRecord(
            thread_name=thread_name, state_signature=sig,
            reward=reward, step=step
        ))
        
        # Boost rule learning
        if self.success_counts[key] >= self.BOOST_THRESHOLD:
            if sig not in self.boost_rules:
                self.boost_rules[sig] = {}
            count = self.success_counts[key]
            boost = min(self.MAX_BOOST_VALUE,
                          0.05 * (count - self.BOOST_THRESHOLD + 1))
            self.boost_rules[sig][thread_name] = boost
    
    def get_boost(self, thread_name: str, state: WorldState) -> float:
        """Thread × state-signature に対する boost weight"""
        sig = self._state_signature(state)
        if sig in self.boost_rules:
            return self.boost_rules[sig].get(thread_name, 0.0)
        return 0.0
    
    def get_summary(self) -> Dict:
        return {
            "total_success_records": len(self.records),
            "unique_thread_sig_combinations": len(self.success_counts),
            "boost_rules_count": sum(len(d) for d in self.boost_rules.values()),
            "max_boost_value": (max(
                [b for d in self.boost_rules.values() for b in d.values()],
                default=0.0
            )),
        }


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Sociable Essence v2 (Q + S) Test")
    print("=" * 70)
    
    # Test A: ThreadConstraintPropagator
    print("\n--- A. ThreadConstraintPropagator (kappa-divisor cascade) ---")
    propagator = ThreadConstraintPropagator()
    
    test_state = WorldState(t=0, R=50, E=50, G=50, O=50, K=50, X=40,
                              cumulative_score=0, is_ruined=False)
    
    candidates = ["RecoveryThread", "DefensiveThread", "SynthesisThread",
                    "AggressiveThread", "MutationThread", "ExplorationThread"]
    
    # drifting: SynthesisThread primary
    for world in ["drifting", "chaotic", "noisy"]:
        print(f"\n  World: {world}")
        result = propagator.propagate("SynthesisThread", 0.75,
                                          candidates, test_state, world)
        print(f"    Primary: {result.primary_thread} = {result.primary_weight:.3f}")
        print(f"    Secondary: {result.secondary_threads}")
        print(f"    Suppressed: {result.suppressed_threads}")
        print(f"    kappa={result.kappa_value:.3f}, D={result.D_value:.3f}, "
              f"total_used={result.total_budget_used:.3f}")
    
    # Test B: EqualSigmaVerifier
    print("\n--- B. EqualSigmaVerifier (P0 strict aliquot) ---")
    verifier = EqualSigmaVerifier()
    
    # Safe state + safe action
    state_safe = WorldState(t=0, R=60, E=60, G=60, O=50, K=50, X=30,
                              cumulative_score=0, is_ruined=False)
    for action in [Action("recover", "A"), Action("invest", "C"), Action("explore", "B")]:
        result = verifier.verify(state_safe, action)
        print(f"  state_safe + {action.intent}/{action.strength}: "
              f"passed={result.passed}, {result.reason}")
    
    # Dangerous state
    state_danger = WorldState(t=0, R=15, E=15, G=20, O=30, K=30, X=85,
                                cumulative_score=0, is_ruined=False)
    for action in [Action("recover", "A"), Action("invest", "C")]:
        result = verifier.verify(state_danger, action)
        print(f"  state_danger + {action.intent}/{action.strength}: "
              f"passed={result.passed}, {result.reason}")
    
    # Test C: SuccessfulPatternBooster
    print("\n--- C. SuccessfulPatternBooster (p3-residue 逆応用) ---")
    booster = SuccessfulPatternBooster()
    
    state_test = WorldState(t=0, R=55, E=55, G=55, O=60, K=50, X=40,
                              cumulative_score=0, is_ruined=False)
    
    # Synthesis が R=55 E=55 で 4 回成功
    for step in range(4):
        booster.record_success("SynthesisThread", state_test, 
                                 reward=0.8, step=step)
    
    boost = booster.get_boost("SynthesisThread", state_test)
    print(f"  SynthesisThread @ state_test: boost = {boost:.3f}")
    
    boost_other = booster.get_boost("AggressiveThread", state_test)
    print(f"  AggressiveThread @ state_test: boost = {boost_other:.3f}")
    
    print(f"  Summary: {booster.get_summary()}")
    
    print("\n[Sociable Essence v2 動作確認 ✅]")
