"""
core/sociable_detection_layer.py

Sociable Essence 4-Layer Detection System.

Per Zarameさん 設計指示書 v3.2:
  Sociable Essence は score 改善装置ではなく、
  LoomEngine の探索能力と検出能力を上げる中核観測層.

4 layers (all default ON for observation):
  1. SociableObservationLayer       - 全 state/action/module を記録
  2. SociableCanonicalizationLayer  - 見かけが違う同型状態を canonical 化
  3. SociableCycleOrbitDetector     - cycle / drift / no-improvement loop 検出
  4. SociableFailureFaceDetector    - near-success failure-face 検出

社交数理論からの transfer:
  - orbit canonicalization (同じ orbit state を canonical 化)
  - failure-face detection (near3 が p3 で落ちる構造)
  - residue avoidance (同じ failure-face へ落ちる候補回避)
  - divisor channel (成功 corridor から候補生成)
  - effective range guard (nominal vs effective 探索範囲分離)
"""
from __future__ import annotations
import os, sys, hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import deque, Counter
from enum import Enum
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action


# ============================================================
# Common types
# ============================================================

class FailureFace(Enum):
    """Per Zarameさん 仕様 § 5: failure-face 分類"""
    STABILIZATION_OVERUSE = "stabilization_overuse"
    GUARD_FORCED = "guard_forced"
    DRIFT_MISS = "drift_miss"
    RECOVERY_DOMINANCE = "recovery_dominance"
    AGGRESSIVE_DRAWDOWN = "aggressive_drawdown"
    THROTTLE_FORCED = "throttle_forced"
    REVALIDATION_REJECTED = "revalidation_rejected"
    NO_IMPROVEMENT_CYCLE = "no_improvement_cycle"
    R_CRITICAL = "r_critical"
    X_HIGH = "x_high"
    OVER_DEFENSE = "over_defense"
    UNKNOWN = "unknown"


# ============================================================
# Layer 1: SociableObservationLayer (常時 ON)
# ============================================================

@dataclass
class ObservationRecord:
    """1 step の observation"""
    step: int
    state_signature: str
    action_signature: str
    module_signature: str
    context_signature: str
    world_signature: str
    reward_delta: float
    r_delta: float
    e_delta: float
    x_delta: float
    o_delta: float
    guard_intervention: bool
    throttle_intervention: bool
    revalidation_rejected: bool
    oracle_gap_estimate: float = 0.0


class SociableObservationLayer:
    """全 state/action/module を記録. 行動変更なし.
    
    Default: ON
    """
    
    HISTORY_SIZE = 100
    
    def __init__(self):
        self.records: deque = deque(maxlen=self.HISTORY_SIZE)
        self.prev_state: Optional[WorldState] = None
        self.prev_reward: float = 0.0
    
    @staticmethod
    def state_signature(state: WorldState) -> str:
        """Bucketed state signature (1 step 単位)"""
        def b(v):
            if v < 20: return 0
            if v < 40: return 1
            if v < 60: return 2
            if v < 80: return 3
            return 4
        return f"R{b(state.R)}E{b(state.E)}G{b(state.G)}O{b(state.O)}K{b(state.K)}X{b(state.X)}"
    
    @staticmethod
    def action_signature(action: Action) -> str:
        return f"{action.intent}_{action.strength}"
    
    @staticmethod
    def context_signature(context_name: str) -> str:
        return context_name
    
    def record(self, step: int, state: WorldState, action: Action,
                 module: str, context_name: str, world_type: str,
                 reward: float, guard_intervention: bool = False,
                 throttle_intervention: bool = False,
                 revalidation_rejected: bool = False,
                 oracle_gap: float = 0.0):
        """1 step を記録"""
        if self.prev_state is not None:
            r_delta = state.R - self.prev_state.R
            e_delta = state.E - self.prev_state.E
            x_delta = state.X - self.prev_state.X
            o_delta = state.O - self.prev_state.O
            reward_delta = reward - self.prev_reward
        else:
            r_delta = e_delta = x_delta = o_delta = 0
            reward_delta = 0
        
        rec = ObservationRecord(
            step=step,
            state_signature=self.state_signature(state),
            action_signature=self.action_signature(action),
            module_signature=module,
            context_signature=self.context_signature(context_name),
            world_signature=world_type,
            reward_delta=reward_delta,
            r_delta=float(r_delta),
            e_delta=float(e_delta),
            x_delta=float(x_delta),
            o_delta=float(o_delta),
            guard_intervention=guard_intervention,
            throttle_intervention=throttle_intervention,
            revalidation_rejected=revalidation_rejected,
            oracle_gap_estimate=float(oracle_gap),
        )
        self.records.append(rec)
        self.prev_state = state
        self.prev_reward = reward
    
    def get_recent(self, n: int = 10) -> List[ObservationRecord]:
        return list(self.records)[-n:]


# ============================================================
# Layer 2: SociableCanonicalizationLayer (常時 ON)
# ============================================================

class SociableCanonicalizationLayer:
    """見かけが違う同型状態を canonical 化.
    
    Per 社交数: orbit canonicalization
    
    canonical_state_id, canonical_failure_id, canonical_context_id, orbit_id
    
    Default: ON
    """
    
    def __init__(self):
        # state_sig → canonical_state_id
        self.state_canonical_map: Dict[str, str] = {}
        # (state_sig, action_sig, failure_face) → canonical_failure_id
        self.failure_canonical_map: Dict[Tuple, str] = {}
        # context_sig → canonical_context_id
        self.context_canonical_map: Dict[str, str] = {}
        # state_sig sequence → orbit_id
        self.orbit_map: Dict[str, str] = {}
        
        self.next_state_id = 0
        self.next_failure_id = 0
        self.next_context_id = 0
        self.next_orbit_id = 0
    
    def canonicalize_state(self, state_sig: str) -> str:
        if state_sig not in self.state_canonical_map:
            self.state_canonical_map[state_sig] = f"S{self.next_state_id:04d}"
            self.next_state_id += 1
        return self.state_canonical_map[state_sig]
    
    def canonicalize_failure(self, state_sig: str, action_sig: str,
                                 face: FailureFace) -> str:
        key = (state_sig, action_sig, face.value)
        if key not in self.failure_canonical_map:
            self.failure_canonical_map[key] = f"F{self.next_failure_id:04d}"
            self.next_failure_id += 1
        return self.failure_canonical_map[key]
    
    def canonicalize_orbit(self, state_sigs: Tuple[str, ...]) -> str:
        """連続 state_sig sequence を orbit として canonical 化"""
        # Rotation invariance: orbit は周期的 → 最小回転を canonical key に
        n = len(state_sigs)
        if n == 0:
            return "ORB_EMPTY"
        rotations = [tuple(state_sigs[i:] + state_sigs[:i]) for i in range(n)]
        canonical = min(rotations)
        key = str(canonical)
        if key not in self.orbit_map:
            self.orbit_map[key] = f"O{self.next_orbit_id:04d}"
            self.next_orbit_id += 1
        return self.orbit_map[key]
    
    def get_stats(self) -> Dict:
        return {
            "canonical_states": len(self.state_canonical_map),
            "canonical_failures": len(self.failure_canonical_map),
            "canonical_orbits": len(self.orbit_map),
        }


# ============================================================
# Layer 3: SociableCycleOrbitDetector (常時 ON)
# ============================================================

@dataclass
class OrbitMetrics:
    """Per 仕様 § 2.3: Cycle/Orbit detection metrics"""
    orbit_recurrence_score: float       # 同 state に戻る頻度 (0-1)
    cycle_closure_score: float           # 完全 cycle が閉じる頻度 (0-1)
    drift_escape_score: float            # 戻らない方向への流れ (0-1)
    directional_persistence: float       # 方向性持続 (0-1)
    reversal_rate: float                 # 反転頻度 (0-1)
    state_delta_autocorrelation: float  # delta の自己相関
    no_improvement_cycle_score: float   # 同じパターンで improvement なし (0-1)
    random_volatility_score: float      # 局所 jitter
    
    # Likelihood scores per Zarameさん 仕様 § 3
    drift_likelihood: float = 0.0
    chaotic_likelihood: float = 0.0
    noisy_likelihood: float = 0.0


class SociableCycleOrbitDetector:
    """Per 仕様 § 2.3 & § 3: 
    Drift/Chaotic/Noisy を構造的に判別する detector.
    
    Default: ON
    """
    
    HISTORY_NEEDED = 5    # min steps for compute
    WINDOW_SIZE = 15      # rolling window
    
    def __init__(self):
        self.state_history: deque = deque(maxlen=self.WINDOW_SIZE)
        self.r_history: deque = deque(maxlen=self.WINDOW_SIZE)
        self.x_history: deque = deque(maxlen=self.WINDOW_SIZE)
        self.reward_history: deque = deque(maxlen=self.WINDOW_SIZE)
        self.state_sig_history: deque = deque(maxlen=self.WINDOW_SIZE)
    
    def update(self, state: WorldState, reward: float, state_sig: str):
        self.state_history.append(state)
        self.r_history.append(state.R)
        self.x_history.append(state.X)
        self.reward_history.append(reward)
        self.state_sig_history.append(state_sig)
    
    def compute_metrics(self) -> OrbitMetrics:
        n = len(self.state_history)
        if n < self.HISTORY_NEEDED:
            return OrbitMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        r_arr = np.array(self.r_history)
        x_arr = np.array(self.x_history)
        rew_arr = np.array(self.reward_history)
        
        # === Orbit recurrence: 同 state_sig がどれくらい繰り返すか ===
        sig_counts = Counter(self.state_sig_history)
        max_count = max(sig_counts.values())
        orbit_recurrence = min(1.0, max_count / n)
        
        # === Cycle closure: 全体が周期で閉じるか ===
        # 簡易判定: 直近 k step と前 k step が同じ pattern か
        cycle_closure = 0.0
        sig_list = list(self.state_sig_history)
        for k in range(2, min(n // 2 + 1, 5)):
            if sig_list[-2*k:-k] == sig_list[-k:]:
                cycle_closure = max(cycle_closure, 0.5 + 0.1 * k)
        cycle_closure = min(1.0, cycle_closure)
        
        # === Directional persistence ===
        # R: 全体が一貫して上下しているか
        x_diffs = np.diff(x_arr)
        r_diffs = np.diff(r_arr)
        
        x_dir_persist = 0.0
        if len(x_diffs) > 0:
            pos_count = np.sum(x_diffs > 0)
            neg_count = np.sum(x_diffs < 0)
            x_dir_persist = abs(pos_count - neg_count) / max(1, len(x_diffs))
        
        r_dir_persist = 0.0
        if len(r_diffs) > 0:
            pos_count = np.sum(r_diffs > 0)
            neg_count = np.sum(r_diffs < 0)
            r_dir_persist = abs(pos_count - neg_count) / max(1, len(r_diffs))
        
        directional_persistence = max(x_dir_persist, r_dir_persist)
        
        # === Drift escape score: X 上昇 OR R 下降 が持続 ===
        x_slope = float(np.polyfit(range(n), x_arr, 1)[0]) if n >= 3 else 0
        r_slope = float(np.polyfit(range(n), r_arr, 1)[0]) if n >= 3 else 0
        
        # x_slope > 0 (X 上昇) or r_slope < 0 (R 下降) が drift
        drift_escape_x = max(0, min(1.0, x_slope / 3.0))
        drift_escape_r = max(0, min(1.0, -r_slope / 3.0))
        drift_escape = max(drift_escape_x, drift_escape_r)
        
        # === Reversal rate: diff の符号がどれくらい反転するか ===
        reversal_rate = 0.0
        if len(x_diffs) >= 2:
            sign_changes = np.sum(np.diff(np.sign(x_diffs)) != 0)
            reversal_rate = float(sign_changes / max(1, len(x_diffs) - 1))
        
        # === State delta autocorrelation ===
        if len(x_diffs) >= 3:
            try:
                autocorr = float(np.corrcoef(x_diffs[:-1], x_diffs[1:])[0, 1])
                if np.isnan(autocorr):
                    autocorr = 0.0
            except Exception:
                autocorr = 0.0
        else:
            autocorr = 0.0
        autocorr = max(-1.0, min(1.0, autocorr))
        
        # === No improvement cycle ===
        # 直近 k step で reward が improving していない
        no_improve = 0.0
        if len(rew_arr) >= 5:
            recent_mean = np.mean(rew_arr[-5:])
            if recent_mean < 0.15:
                no_improve = min(1.0, (0.15 - recent_mean) * 3 + 0.3)
        
        # === Random volatility (Noisy 特徴) ===
        # local jitter: 各 step の delta variance が大きい
        if len(x_diffs) >= 3:
            volatility = float(np.std(x_diffs))
            random_vol = min(1.0, volatility / 5.0)
        else:
            random_vol = 0.0
        
        # === Likelihood scores ===
        # Drift likelihood (per 仕様 § 3.1)
        drift_likelihood = (
            directional_persistence * 0.30
            + drift_escape * 0.35
            + abs(autocorr) * 0.15  # 正の autocorr = drift trend
            + (1.0 - cycle_closure) * 0.15  # low cycle closure
            - reversal_rate * 0.15
            - random_vol * 0.10
        )
        drift_likelihood = max(0.0, min(1.0, drift_likelihood))
        
        # Chaotic likelihood (per 仕様 § 3.2)
        chaotic_likelihood = (
            random_vol * 0.30
            + reversal_rate * 0.30
            + orbit_recurrence * 0.20  # moderate orbit
            + (1.0 - directional_persistence) * 0.20
        )
        chaotic_likelihood = max(0.0, min(1.0, chaotic_likelihood))
        
        # Noisy likelihood (per 仕様 § 3.3)
        noisy_likelihood = (
            random_vol * 0.40
            + (1.0 - directional_persistence) * 0.30  # low signal persistence
            + (1.0 - cycle_closure) * 0.15  # weak cycle
            + (1.0 - drift_escape) * 0.15   # weak drift
        )
        noisy_likelihood = max(0.0, min(1.0, noisy_likelihood))
        
        return OrbitMetrics(
            orbit_recurrence_score=float(orbit_recurrence),
            cycle_closure_score=float(cycle_closure),
            drift_escape_score=float(drift_escape),
            directional_persistence=float(directional_persistence),
            reversal_rate=float(reversal_rate),
            state_delta_autocorrelation=float(autocorr),
            no_improvement_cycle_score=float(no_improve),
            random_volatility_score=float(random_vol),
            drift_likelihood=float(drift_likelihood),
            chaotic_likelihood=float(chaotic_likelihood),
            noisy_likelihood=float(noisy_likelihood),
        )


# ============================================================
# Layer 4: SociableFailureFaceDetector (常時 ON)
# ============================================================

@dataclass
class FailureFaceDistribution:
    """近 N step の failure-face 分布"""
    distribution: Dict[str, int]
    dominant_face: Optional[FailureFace]
    dominant_ratio: float
    near_success_count: int
    failure_face_entropy: float


class SociableFailureFaceDetector:
    """Per 仕様 § 2.4: near-success failure-face 検出.
    
    Default: ON
    """
    
    HISTORY_NEEDED = 5
    WINDOW_SIZE = 30
    NEAR_SUCCESS_REWARD_RANGE = (-0.2, 0.3)  # near-success の reward range
    
    def __init__(self):
        # 各 face の発生回数 (rolling)
        self.face_history: deque = deque(maxlen=self.WINDOW_SIZE)
        self.near_success_history: deque = deque(maxlen=self.WINDOW_SIZE)
        # (state_sig, action_sig) → most common failure_face
        self.failure_pattern_map: Dict[Tuple[str, str], Counter] = {}
    
    def record(self, state: WorldState, action: Action, reward: float,
                 module: str, guard_intervention: bool = False,
                 throttle_intervention: bool = False,
                 revalidation_rejected: bool = False,
                 stabilization_overuse: bool = False,
                 drift_miss: bool = False):
        """1 step の (state, action, outcome) を失敗面分類"""
        face = self._infer_failure_face(
            state, action, reward, module,
            guard_intervention, throttle_intervention,
            revalidation_rejected,
            stabilization_overuse, drift_miss
        )
        if face is not None:
            self.face_history.append(face)
            state_sig = SociableObservationLayer.state_signature(state)
            action_sig = SociableObservationLayer.action_signature(action)
            key = (state_sig, action_sig)
            if key not in self.failure_pattern_map:
                self.failure_pattern_map[key] = Counter()
            self.failure_pattern_map[key][face.value] += 1
        
        # near success?
        if self.NEAR_SUCCESS_REWARD_RANGE[0] <= reward <= self.NEAR_SUCCESS_REWARD_RANGE[1]:
            self.near_success_history.append(reward)
    
    def _infer_failure_face(self, state: WorldState, action: Action, reward: float,
                                module: str, guard_int: bool, throttle_int: bool,
                                reval_rej: bool, stab_overuse: bool, drift_miss: bool
                                ) -> Optional[FailureFace]:
        # 優先順位ベースで face を分類
        if guard_int:
            return FailureFace.GUARD_FORCED
        if throttle_int:
            return FailureFace.THROTTLE_FORCED
        if reval_rej:
            return FailureFace.REVALIDATION_REJECTED
        if state.R <= 18:
            return FailureFace.R_CRITICAL
        if state.X >= 80:
            return FailureFace.X_HIGH
        if drift_miss:
            return FailureFace.DRIFT_MISS
        if stab_overuse:
            return FailureFace.STABILIZATION_OVERUSE
        if module == "RecoveryCandidate" and reward < 0.1:
            return FailureFace.RECOVERY_DOMINANCE
        if module == "AggressiveEngine" and reward < -0.1:
            return FailureFace.AGGRESSIVE_DRAWDOWN
        if action.intent == "defend" and reward < -0.05:
            return FailureFace.OVER_DEFENSE
        if reward < 0:
            return FailureFace.UNKNOWN
        return None  # success
    
    def get_distribution(self) -> FailureFaceDistribution:
        if not self.face_history:
            return FailureFaceDistribution(
                distribution={}, dominant_face=None,
                dominant_ratio=0.0, near_success_count=0,
                failure_face_entropy=0.0
            )
        counter = Counter(f.value for f in self.face_history)
        total = sum(counter.values())
        most = counter.most_common(1)[0]
        dominant_name = most[0]
        dominant_face = FailureFace(dominant_name)
        dominant_ratio = most[1] / total
        
        # Entropy
        probs = [c / total for c in counter.values()]
        entropy = -sum(p * np.log2(p) for p in probs if p > 0)
        
        return FailureFaceDistribution(
            distribution=dict(counter),
            dominant_face=dominant_face,
            dominant_ratio=float(dominant_ratio),
            near_success_count=len(self.near_success_history),
            failure_face_entropy=float(entropy),
        )


# ============================================================
# Integrated Sociable Detection System
# ============================================================

@dataclass
class SociableDetectionReport:
    """全 4 層の結合 report"""
    orbit_metrics: OrbitMetrics
    failure_distribution: FailureFaceDistribution
    canonical_stats: Dict
    n_observation_records: int
    
    def to_dict(self) -> Dict:
        return {
            "orbit": {
                "drift_likelihood": self.orbit_metrics.drift_likelihood,
                "chaotic_likelihood": self.orbit_metrics.chaotic_likelihood,
                "noisy_likelihood": self.orbit_metrics.noisy_likelihood,
                "drift_escape": self.orbit_metrics.drift_escape_score,
                "directional_persistence": self.orbit_metrics.directional_persistence,
                "reversal_rate": self.orbit_metrics.reversal_rate,
                "no_improvement": self.orbit_metrics.no_improvement_cycle_score,
            },
            "failure": {
                "dominant_face": (self.failure_distribution.dominant_face.value 
                                    if self.failure_distribution.dominant_face else None),
                "dominant_ratio": self.failure_distribution.dominant_ratio,
                "near_success_count": self.failure_distribution.near_success_count,
                "entropy": self.failure_distribution.failure_face_entropy,
            },
            "canonical": self.canonical_stats,
            "observations": self.n_observation_records,
        }


class SociableDetectionSystem:
    """4 層を統合した sociable detection system.
    
    All layers default ON for observation.
    Per Zarameさん 仕様: 行動介入は別途 ablation 対象.
    """
    
    def __init__(self):
        self.observation = SociableObservationLayer()
        self.canonicalization = SociableCanonicalizationLayer()
        self.cycle_detector = SociableCycleOrbitDetector()
        self.failure_detector = SociableFailureFaceDetector()
    
    def update(self, step: int, state: WorldState, action: Action,
                 module: str, context_name: str, world_type: str,
                 reward: float, guard_intervention: bool = False,
                 throttle_intervention: bool = False,
                 revalidation_rejected: bool = False,
                 stabilization_overuse: bool = False,
                 drift_miss: bool = False, oracle_gap: float = 0.0):
        """1 step の updates を全 layer に分配"""
        # Layer 1: Observation
        self.observation.record(
            step, state, action, module, context_name, world_type,
            reward, guard_intervention, throttle_intervention,
            revalidation_rejected, oracle_gap
        )
        
        # Layer 2: Canonicalization
        state_sig = SociableObservationLayer.state_signature(state)
        self.canonicalization.canonicalize_state(state_sig)
        
        # Layer 3: Cycle/Orbit Detection
        self.cycle_detector.update(state, reward, state_sig)
        
        # Layer 4: Failure-Face Detection
        self.failure_detector.record(
            state, action, reward, module,
            guard_intervention, throttle_intervention, revalidation_rejected,
            stabilization_overuse, drift_miss
        )
    
    def get_report(self) -> SociableDetectionReport:
        return SociableDetectionReport(
            orbit_metrics=self.cycle_detector.compute_metrics(),
            failure_distribution=self.failure_detector.get_distribution(),
            canonical_stats=self.canonicalization.get_stats(),
            n_observation_records=len(self.observation.records),
        )


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Sociable Detection System Test (4 Layers)")
    print("=" * 70)
    
    # Test 1: Drifting world (X 上昇 R 減少)
    print("\n--- DRIFTING simulation ---")
    sds = SociableDetectionSystem()
    for t in range(20):
        state = WorldState(t=t, R=70 - t*2, E=50, G=50, O=50, K=50,
                            X=20 + t*3,
                            cumulative_score=0, is_ruined=False)
        sds.update(t, state, Action("invest", "A"), "Module", "Normal",
                     "unknown", reward=0.2)
    rep = sds.get_report()
    print(f"  orbit: drift_lik={rep.orbit_metrics.drift_likelihood:.3f}, "
          f"chaotic_lik={rep.orbit_metrics.chaotic_likelihood:.3f}, "
          f"noisy_lik={rep.orbit_metrics.noisy_likelihood:.3f}")
    print(f"  drift_escape={rep.orbit_metrics.drift_escape_score:.3f}, "
          f"dir_persist={rep.orbit_metrics.directional_persistence:.3f}, "
          f"reversal={rep.orbit_metrics.reversal_rate:.3f}")
    print(f"  canonical: {rep.canonical_stats}")
    
    # Test 2: Chaotic world (high variance, no direction)
    print("\n--- CHAOTIC simulation ---")
    sds = SociableDetectionSystem()
    rng = np.random.default_rng(42)
    for t in range(20):
        state = WorldState(t=t, R=50 + rng.normal(0, 15), E=50, G=50, O=50, K=50,
                            X=40 + rng.normal(0, 10),
                            cumulative_score=0, is_ruined=False)
        sds.update(t, state, Action("recover", "A"), "RecoveryCandidate", "Normal",
                     "unknown", reward=0.1)
    rep = sds.get_report()
    print(f"  orbit: drift_lik={rep.orbit_metrics.drift_likelihood:.3f}, "
          f"chaotic_lik={rep.orbit_metrics.chaotic_likelihood:.3f}, "
          f"noisy_lik={rep.orbit_metrics.noisy_likelihood:.3f}")
    print(f"  reversal={rep.orbit_metrics.reversal_rate:.3f}, "
          f"random_vol={rep.orbit_metrics.random_volatility_score:.3f}")
    
    # Test 3: Failure-face distribution
    print("\n--- FAILURE-FACE detection ---")
    sds = SociableDetectionSystem()
    for t in range(10):
        state = WorldState(t=t, R=15 - t, E=20, G=20, O=30, K=30, X=70,
                            cumulative_score=0, is_ruined=False)
        # Guard 介入の reward < 0 シナリオ
        sds.update(t, state, Action("invest", "B"), "AggressiveEngine", "Normal",
                     "unknown", reward=-0.3, guard_intervention=True)
    rep = sds.get_report()
    print(f"  dominant_face: {rep.failure_distribution.dominant_face}")
    print(f"  distribution: {rep.failure_distribution.distribution}")
    print(f"  entropy: {rep.failure_distribution.failure_face_entropy:.3f}")
    
    print("\n[Sociable Detection System 動作確認 ✅]")
