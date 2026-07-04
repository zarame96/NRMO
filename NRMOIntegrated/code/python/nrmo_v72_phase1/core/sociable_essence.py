"""
core/sociable_essence.py

Sociable Numbers (v6.9) エッセンスの NRMO 取り込み.

3 つの数理機構を Loom 制御に統合:

  A. FailureFaceTracker (= failure-face profiling)
     各 thread が「どの failure-face で詰まったか」を蓄積.
     p3-dominant / p4-dominant 風の profiling.
     → 過去失敗した thread × face を pre-reject.
  
  B. CanonicalKey + Deduplication
     候補を canonical form で表現し重複排除.
     "16 unique canonical full successes" 風.
     → candidate pool を clean に保つ.
  
  C. SociableCycleDetector
     state-action history で k-cycle を検出.
     σ^k(N)=N の sociable chain 風.
     → cycle 発見 = stagnation orbit = breakthrough 必要.

References:
  sociable_numbers_v6_9_handoff.md
  - failure-face profile (p3/p4 counting)
  - canonical deduplication
  - residue avoidance (failed primes q から pre-rejection)
  - kappa-divisor: D = B²(d+e)² - 2ABde
"""
from __future__ import annotations
import os, sys, hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import deque, Counter
from enum import Enum

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action


# ============================================================
# A. FailureFaceTracker (p3/p4 dominance profile 風)
# ============================================================

class FailureFace(Enum):
    """候補が fail し得る "face" の分類.
    
    Per sociable numbers handoff: "p3 failure 10, p4 failure 2"
    → 4 failure-face system (p1, p2, p3, p4) を NRMO に generalise.
    """
    R_CRITICAL = "r_critical"          # R 危険水準で attack
    X_HIGH = "x_high"                   # X 高位で expansion
    O_LOW = "o_low"                     # O 低位で invest
    E_LOW = "e_low"                     # E 低位で defend
    CUMULATIVE_BREACH = "cumulative"    # cumulative risk 超過
    REVERSIBILITY_LOW = "reversibility" # 不可逆性が高い
    REPETITION = "repetition"           # 同 module 過剰連続
    GUARD_REJECTION = "guard_rejection" # EG/Throttle で reject


@dataclass
class ThreadFailureRecord:
    """1 thread × 1 face の failure 記録"""
    thread_name: str
    face: FailureFace
    state_signature: str  # state の low-rank signature
    step: int
    

class FailureFaceTracker:
    """Thread × failure-face の profile を蓄積し、
    過去多発した combination を pre-reject する.
    
    Per sociable numbers handoff:
      "p3-dominant halo channel" → "Recovery-dominant safe channel"
      "Use failed primes q to pre-reject d*L ≡ 1 mod q"
        → use failed (thread, face, signature) to pre-reject new candidate
    """
    
    MAX_RECORDS = 200       # 蓄積最大
    MAX_FACE_PER_THREAD = 8 # thread あたり face 種類
    PRE_REJECT_THRESHOLD = 3  # 同パターン N 回 fail → pre-reject 候補
    
    def __init__(self):
        # (thread_name, face, state_signature) -> count
        self.failure_counts: Counter = Counter()
        # face per thread profile
        self.thread_face_profile: Dict[str, Counter] = {}
        self.records: deque = deque(maxlen=self.MAX_RECORDS)
        
        # Learned residue rules: state_signature -> set of blocked threads
        self.residue_rules: Dict[str, Set[str]] = {}
    
    def _state_signature(self, state: WorldState) -> str:
        """State の low-rank signature.
        
        Per sociable numbers: signature is canonical small-rank key.
        Bucketing で signature 衝突を許容.
        """
        # 4 buckets per dimension (low/mid-low/mid-high/high)
        def bucket(v):
            if v < 25: return 0
            if v < 50: return 1
            if v < 75: return 2
            return 3
        return (f"R{bucket(state.R)}_E{bucket(state.E)}_"
                f"O{bucket(state.O)}_X{bucket(state.X)}")
    
    def record_failure(self, thread_name: str, face: FailureFace,
                         state: WorldState, step: int):
        """Thread × face × state-signature の failure を記録"""
        sig = self._state_signature(state)
        key = (thread_name, face.value, sig)
        self.failure_counts[key] += 1
        
        if thread_name not in self.thread_face_profile:
            self.thread_face_profile[thread_name] = Counter()
        self.thread_face_profile[thread_name][face.value] += 1
        
        self.records.append(ThreadFailureRecord(
            thread_name=thread_name, face=face,
            state_signature=sig, step=step
        ))
        
        # Residue rule learning: PRE_REJECT_THRESHOLD 回 fail → block
        if self.failure_counts[key] >= self.PRE_REJECT_THRESHOLD:
            if sig not in self.residue_rules:
                self.residue_rules[sig] = set()
            self.residue_rules[sig].add(thread_name)
    
    def should_pre_reject(self, thread_name: str, state: WorldState) -> Tuple[bool, str]:
        """Per sociable numbers residue avoidance:
        過去 N 回 fail した (thread, signature) は pre-reject.
        """
        sig = self._state_signature(state)
        if sig in self.residue_rules and thread_name in self.residue_rules[sig]:
            # Count を取得
            for face in FailureFace:
                count = self.failure_counts.get((thread_name, face.value, sig), 0)
                if count >= self.PRE_REJECT_THRESHOLD:
                    return True, f"residue_rule:{thread_name}@{sig}@{face.value}={count}"
        return False, ""
    
    def get_dominance_profile(self, thread_name: str) -> Tuple[Optional[str], float]:
        """Per sociable numbers: "p3-dominant halo channel" 風.
        Thread の最頻 failure-face を返す.
        """
        if thread_name not in self.thread_face_profile:
            return None, 0.0
        counter = self.thread_face_profile[thread_name]
        if not counter:
            return None, 0.0
        most_common = counter.most_common(1)[0]
        face, count = most_common
        total = sum(counter.values())
        return face, count / total if total > 0 else 0.0
    
    def get_summary(self) -> Dict:
        return {
            "total_records": len(self.records),
            "unique_thread_face_signatures": len(self.failure_counts),
            "residue_rules_count": sum(len(s) for s in self.residue_rules.values()),
            "thread_dominance": {
                t: self.get_dominance_profile(t) 
                for t in self.thread_face_profile.keys()
            },
        }


# ============================================================
# B. Canonical Key + Candidate Deduplication
# ============================================================

@dataclass
class CanonicalCandidate:
    """Candidate の canonical form"""
    canonical_key: str          # hash-based key
    module: str
    intent: str
    strength: str
    expected_upside_bucket: int  # discretized
    estimated_downside_bucket: int
    reversibility_bucket: int


class CandidateCanonicalizer:
    """Per sociable numbers: "canonical4 deduplication".
    
    候補の canonical form を計算し、同じ canonical key の重複を排除.
    """
    
    @staticmethod
    def _bucket_float(v: float, n_buckets: int = 10) -> int:
        return int(max(0, min(n_buckets - 1, v * n_buckets)))
    
    @classmethod
    def compute_canonical(cls, candidate) -> CanonicalCandidate:
        """FullCandidate → CanonicalCandidate"""
        intent = candidate.attack_candidate.intent if candidate.attack_candidate else "none"
        strength = candidate.attack_candidate.strength if candidate.attack_candidate else "A"
        
        u_b = cls._bucket_float(candidate.expected_upside, 10)
        d_b = cls._bucket_float(candidate.estimated_downside, 10)
        r_b = cls._bucket_float(candidate.reversibility, 10)
        
        # Canonical key
        key_str = f"{candidate.module}:{intent}:{strength}:U{u_b}:D{d_b}:R{r_b}"
        canonical_key = hashlib.md5(key_str.encode()).hexdigest()[:12]
        
        return CanonicalCandidate(
            canonical_key=canonical_key,
            module=candidate.module,
            intent=intent,
            strength=strength,
            expected_upside_bucket=u_b,
            estimated_downside_bucket=d_b,
            reversibility_bucket=r_b,
        )
    
    @classmethod
    def deduplicate(cls, candidates: List) -> Tuple[List, int]:
        """Canonical key で deduplicate.
        Returns: (unique candidates, n_duplicates_removed)
        """
        seen_keys: Set[str] = set()
        unique = []
        n_removed = 0
        
        for cand in candidates:
            canonical = cls.compute_canonical(cand)
            if canonical.canonical_key in seen_keys:
                n_removed += 1
                continue
            seen_keys.add(canonical.canonical_key)
            unique.append(cand)
        
        return unique, n_removed


# ============================================================
# C. SociableCycleDetector
# ============================================================

@dataclass
class CycleInfo:
    """検出された cycle 情報"""
    cycle_length: int           # k (cycle 長)
    starts_at_step: int
    pattern: List[Tuple[str, str]]  # (intent, strength) の k 要素
    stagnation: bool            # 進歩なし cycle か


class SociableCycleDetector:
    """Per sociable numbers: σ^k(N) = N の sociable chain detection.
    
    NRMO への応用:
      state-action history で k-cycle を検出
      cycle 発見 = 同じパターンの繰り返し = stagnation orbit
      → breakthrough (mutation, aggressive) が必要
    """
    
    MIN_CYCLE_LENGTH = 2
    MAX_CYCLE_LENGTH = 8
    HISTORY_SIZE = 30
    STAGNATION_REWARD_THRESHOLD = 0.3  # 平均 reward < この値 = stagnation
    
    def __init__(self):
        # (state_signature, action.intent, action.strength) sequence
        self.history: deque = deque(maxlen=self.HISTORY_SIZE)
        self.recent_rewards: deque = deque(maxlen=self.HISTORY_SIZE)
        self.detected_cycles: List[CycleInfo] = []
        self.current_step = 0
    
    def _state_signature(self, state: WorldState) -> str:
        """Coarse signature (cycle detection 用)"""
        def bucket(v):
            if v < 25: return 0
            if v < 50: return 1
            if v < 75: return 2
            return 3
        return f"R{bucket(state.R)}_X{bucket(state.X)}_O{bucket(state.O)}"
    
    def update(self, state: WorldState, action: Action, reward: float):
        self.current_step += 1
        sig = self._state_signature(state)
        self.history.append((sig, action.intent, action.strength))
        self.recent_rewards.append(reward)
    
    def detect_cycle(self) -> Optional[CycleInfo]:
        """直近 history で k-cycle (k=2..8) を検出.
        
        Returns: 最も短い検出された cycle (or None)
        """
        if len(self.history) < self.MIN_CYCLE_LENGTH * 2:
            return None
        
        history_list = list(self.history)
        n = len(history_list)
        
        # k=2 から最大 cycle 長まで試す
        for k in range(self.MIN_CYCLE_LENGTH, min(self.MAX_CYCLE_LENGTH + 1, n // 2 + 1)):
            # 直近 2*k 要素を取り、前半 k と 後半 k が一致するか
            if n < 2 * k:
                continue
            first_half = history_list[-2*k:-k]
            second_half = history_list[-k:]
            
            if first_half == second_half:
                # Cycle 検出!
                pattern = [(h[1], h[2]) for h in second_half]
                
                # Stagnation check
                recent_reward_avg = (sum(list(self.recent_rewards)[-k:]) / k 
                                       if self.recent_rewards else 0)
                stagnation = recent_reward_avg < self.STAGNATION_REWARD_THRESHOLD
                
                cycle = CycleInfo(
                    cycle_length=k,
                    starts_at_step=self.current_step - 2*k + 1,
                    pattern=pattern,
                    stagnation=stagnation,
                )
                self.detected_cycles.append(cycle)
                return cycle
        
        return None
    
    def get_summary(self) -> Dict:
        if not self.detected_cycles:
            return {"cycles_detected": 0}
        return {
            "cycles_detected": len(self.detected_cycles),
            "stagnation_cycles": sum(1 for c in self.detected_cycles if c.stagnation),
            "cycle_length_distribution": Counter(
                c.cycle_length for c in self.detected_cycles
            ),
            "longest_cycle": max(c.cycle_length for c in self.detected_cycles),
        }


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Sociable Essence Test")
    print("=" * 70)
    
    # Test A: FailureFaceTracker
    print("\n--- A. FailureFaceTracker ---")
    tracker = FailureFaceTracker()
    
    test_state = WorldState(t=0, R=15, E=20, G=30, O=50, K=50, X=80,
                              cumulative_score=0, is_ruined=False)
    
    # AggressiveThread が R critical で何度も fail するシナリオ
    for step in range(5):
        tracker.record_failure("AggressiveThread", FailureFace.R_CRITICAL,
                                test_state, step)
    
    should_block, reason = tracker.should_pre_reject("AggressiveThread", test_state)
    print(f"  pre-reject AggressiveThread @ R=15: {should_block} ({reason})")
    
    # 別 thread はまだ block されない
    should_block, reason = tracker.should_pre_reject("RecoveryThread", test_state)
    print(f"  pre-reject RecoveryThread @ R=15: {should_block} ({reason})")
    
    profile = tracker.get_summary()
    print(f"  Summary: {profile}")
    
    # Test B: Canonical Deduplication
    print("\n--- B. CandidateCanonicalizer ---")
    from strong_engine_omega_full import FullCandidate
    
    cand1 = FullCandidate(
        module="RecoveryCandidate",
        attack_candidate=Action("recover", "A"),
        safe_variant=Action("recover", "A"),
        minimum_reversible_variant=Action("hold", "A"),
        expected_upside=0.50, estimated_downside=0.10, reversibility=0.90,
        reason="r1",
    )
    cand2 = FullCandidate(
        module="RecoveryCandidate",
        attack_candidate=Action("recover", "A"),
        safe_variant=Action("recover", "A"),
        minimum_reversible_variant=Action("hold", "A"),
        expected_upside=0.51, estimated_downside=0.10, reversibility=0.90,
        reason="r2",  # 同じ canonical (差は 0.01)
    )
    cand3 = FullCandidate(
        module="DefensiveCandidate",
        attack_candidate=Action("defend", "A"),
        safe_variant=Action("defend", "A"),
        minimum_reversible_variant=Action("hold", "A"),
        expected_upside=0.30, estimated_downside=0.10, reversibility=0.90,
        reason="d1",
    )
    
    unique, n_removed = CandidateCanonicalizer.deduplicate([cand1, cand2, cand3])
    print(f"  Input 3 candidates, unique={len(unique)}, removed={n_removed}")
    for c in unique:
        canonical = CandidateCanonicalizer.compute_canonical(c)
        print(f"    {c.module}: key={canonical.canonical_key} "
              f"(U{canonical.expected_upside_bucket}D{canonical.estimated_downside_bucket}R{canonical.reversibility_bucket})")
    
    # Test C: SociableCycleDetector
    print("\n--- C. SociableCycleDetector ---")
    detector = SociableCycleDetector()
    
    # Cycle pattern: recover/A → hold/A → recover/A → hold/A → ...
    states = []
    actions = [Action("recover", "A"), Action("hold", "A")] * 5
    
    state_a = WorldState(t=0, R=40, E=40, G=40, O=40, K=50, X=40,
                           cumulative_score=0, is_ruined=False)
    state_b = WorldState(t=0, R=42, E=43, G=42, O=38, K=50, X=42,
                           cumulative_score=0, is_ruined=False)
    
    for i, action in enumerate(actions):
        state = state_a if i % 2 == 0 else state_b
        detector.update(state, action, reward=0.1)  # low reward
    
    cycle = detector.detect_cycle()
    if cycle:
        print(f"  Cycle detected! length={cycle.cycle_length}, "
              f"stagnation={cycle.stagnation}, pattern={cycle.pattern}")
    else:
        print("  No cycle detected")
    
    print(f"  Summary: {detector.get_summary()}")
    
    print("\n[Sociable Essence 動作確認 ✅]")
