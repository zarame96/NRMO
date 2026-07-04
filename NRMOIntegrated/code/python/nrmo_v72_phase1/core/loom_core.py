"""
core/loom_core.py

NRMO Loom Core / Loom Layer.

Per spec NRMO_Loom_Core_Loom_Layer_Spec.md:

  LoomCore は上位制御核.
    - World/Context/Risk recognition
    - Thread Activation/Suppression decision
    - Sparse Weaving (全 thread を同時に動かさない)
    - Oracle Gap Minimization
    - Over-Generalization Prevention
  
  LoomLayer は LoomCore の判断を制御値へ変換.
    - activation_weight, suppression_weight
    - action_size_cap, cooldown_steps
    - risk_budget_limit, thread_priority, fallback_thread

Central principle:
  "All threads available. Few threads active."
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import deque
from enum import Enum

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from context_classifier import Context, ContextClassification, ContextClassifier
from meta_engine import WorldTypeDetector


# ============================================================
# Thread names (per Spec § 4.1)
# ============================================================

class Thread(Enum):
    RECOVERY = "RecoveryThread"        # 回復・資源維持
    DEFENSIVE = "DefensiveThread"      # 下方リスク抑制
    DRIFT = "DriftThread"               # regime shift, drifting world
    SYNTHESIS = "SynthesisThread"      # 複数候補統合
    AGGRESSIVE = "AggressiveThread"    # 機会獲得・突破
    EXPLORATION = "ExplorationThread"  # 情報収集・probe
    MUTATION = "MutationThread"        # 変異探索
    INVENTION = "InventionThread"      # 新規発明


# Module name (FullCandidate.module) → Thread mapping
MODULE_TO_THREAD: Dict[str, Thread] = {
    "RecoveryCandidate": Thread.RECOVERY,
    "DefensiveCandidate": Thread.DEFENSIVE,
    "ExplorationCandidate": Thread.EXPLORATION,
    "SynthesisPathway": Thread.SYNTHESIS,
    "SynthesisStandalone": Thread.SYNTHESIS,  # V9 由来も Synthesis 扱い
    "MutationPathway": Thread.MUTATION,
    "InventionPathway": Thread.INVENTION,
    "AggressiveEngine": Thread.AGGRESSIVE,
    # DriftThread は drifting world で SynthesisStandalone を担当する形で実現
}


# ============================================================
# LoomLayer instructions (per Spec § 9)
# ============================================================

@dataclass
class WeavingInstructions:
    """LoomCore → LoomLayer に渡る weaving 指示"""
    # Thread weights (0.0 - 1.0)
    active_threads: Dict[Thread, float] = field(default_factory=dict)
    # Suppression weights (0.0 = no suppression, 1.0 = complete suppression)
    suppressed_threads: Dict[Thread, float] = field(default_factory=dict)
    
    # Output controls
    action_size_cap: str = "C"  # "A", "B", "C" — 最大許容 strength
    cooldown_threads: Dict[Thread, int] = field(default_factory=dict)
    risk_budget_limit: float = 1.0
    thread_priority: List[Thread] = field(default_factory=list)
    fallback_thread: Optional[Thread] = None
    revalidation_strict: bool = False
    
    # Trace
    reason: str = ""
    detected_world: str = "unknown"
    detected_context: str = "Normal"
    
    def is_active(self, thread: Thread) -> bool:
        return thread in self.active_threads
    
    def is_suppressed(self, thread: Thread, threshold: float = 0.5) -> bool:
        return self.suppressed_threads.get(thread, 0.0) >= threshold
    
    def to_dict(self) -> Dict:
        return {
            "active_threads": {t.value: w for t, w in self.active_threads.items()},
            "suppressed_threads": {t.value: w for t, w in self.suppressed_threads.items()},
            "action_size_cap": self.action_size_cap,
            "cooldown_threads": {t.value: c for t, c in self.cooldown_threads.items()},
            "risk_budget_limit": self.risk_budget_limit,
            "thread_priority": [t.value for t in self.thread_priority],
            "fallback_thread": self.fallback_thread.value if self.fallback_thread else None,
            "reason": self.reason,
            "detected_world": self.detected_world,
            "detected_context": self.detected_context,
        }


# ============================================================
# Risk State Evaluation
# ============================================================

@dataclass
class RiskState:
    """Risk assessment per Spec § 8.3"""
    r_critical: bool          # R 危険水準
    r_low: bool                # R 低位
    x_high: bool               # X 高位
    drawdown_recent: bool      # 最近の drawdown
    ruin_proximity: float      # 0-1, 1 = imminent ruin
    cumulative_exposure: float # 累積 risk exposure
    
    @classmethod
    def evaluate(cls, state: WorldState, recent_rewards: List[float],
                 cumulative_exposure: float = 0.0) -> "RiskState":
        r_critical = state.R <= 15
        r_low = state.R <= 35
        x_high = state.X >= 70
        drawdown_recent = (len(recent_rewards) >= 3 and 
                            sum(recent_rewards[-3:]) < -1.0)
        
        # Ruin proximity: R 低い + X 高い
        ruin_proximity = min(1.0, max(0, (20 - state.R) / 20) * 0.5 +
                                max(0, (state.X - 60) / 40) * 0.5)
        
        # 累積 risk exposure (CumulativeRiskTracker.exposure_scalar() から注入)
        cumulative = float(max(0.0, min(1.0, cumulative_exposure)))
        
        return cls(r_critical, r_low, x_high, drawdown_recent,
                    ruin_proximity, cumulative)


# ============================================================
# LoomCore (per Spec § 8)
# ============================================================

class LoomCore:
    """上位制御核 — どの thread を、いつ、どの強度で発火させるか決める.
    
    Per Spec § 10.3 central principle:
      "All threads available. Few threads active."
    
    Per Spec § 11 Operating Rule:
      Best Unified Result =
        Shared Governance
        + World-Conditional Specialist Threads
        + Sparse Activation
        + Common Risk Floor
        + Oracle Gap Minimization
    """
    
    # Cooldown
    AGGRESSIVE_COOLDOWN_STEPS = 3
    MUTATION_COOLDOWN_STEPS = 5
    
    def __init__(self, world_detector: Optional[WorldTypeDetector] = None,
                  context_classifier: Optional[ContextClassifier] = None):
        self.world_detector = world_detector or WorldTypeDetector(history_size=15)
        self.context_classifier = context_classifier or ContextClassifier()
        
        # Cooldown tracking
        self.thread_cooldowns: Dict[Thread, int] = {}
        self.recent_rewards: deque = deque(maxlen=10)
        
        self.decision_count = 0
        self.stats = {
            "weaving_decisions": 0,
            "thread_activation_count": {t: 0 for t in Thread},
            "thread_suppression_count": {t: 0 for t in Thread},
            "world_type_counts": {},
            "context_counts": {},
        }
    
    def decide_weaving(self, observation: WorldState,
                         conditions: Optional[Dict] = None,
                         cumulative_exposure: float = 0.0) -> WeavingInstructions:
        """Per Spec § 8: Loom Core responsibilities"""
        self.decision_count += 1
        self.stats["weaving_decisions"] += 1
        
        # 1. World recognition
        self.world_detector.update(observation)
        world_type, world_conf = self.world_detector.detect_world_type()
        self.stats["world_type_counts"][world_type] = \
            self.stats["world_type_counts"].get(world_type, 0) + 1
        
        # 2. Context recognition
        context = self.context_classifier.classify(observation, conditions=conditions)
        ctx_name = context.primary_context.value
        self.stats["context_counts"][ctx_name] = \
            self.stats["context_counts"].get(ctx_name, 0) + 1
        
        # 3. Risk evaluation
        risk = RiskState.evaluate(observation, list(self.recent_rewards),
                                   cumulative_exposure=cumulative_exposure)
        
        # 4. Decide weaving (sparse, world-conditional)
        instructions = self._compose_weaving(observation, world_type, world_conf,
                                                context, risk)
        
        # 4b. 累積 risk exposure による caution escalation (hard clamp)。
        #     ★context 分岐が cap="B" 等に設定した後に適用するので必ず勝つ
        #     (OPPORTUNITY/STAGNATION の B-cap にも上書きされない)。
        #     瞬時状態が無事でも累積暴露が閾値超なら強度を A に抑える (passive ruin 防止)。
        if risk.cumulative_exposure >= 0.7:
            instructions.action_size_cap = "A"
            instructions.suppressed_threads[Thread.AGGRESSIVE] = max(
                0.7, instructions.suppressed_threads.get(Thread.AGGRESSIVE, 0.0))
            self.stats["cumulative_exposure_escalations"] = \
                self.stats.get("cumulative_exposure_escalations", 0) + 1
        
        # 5. Update cooldowns
        self._decrement_cooldowns()
        for thread in instructions.active_threads:
            if thread == Thread.AGGRESSIVE:
                self.thread_cooldowns[thread] = self.AGGRESSIVE_COOLDOWN_STEPS
            elif thread == Thread.MUTATION:
                self.thread_cooldowns[thread] = self.MUTATION_COOLDOWN_STEPS
        
        # Stats
        for t in instructions.active_threads:
            self.stats["thread_activation_count"][t] = \
                self.stats["thread_activation_count"].get(t, 0) + 1
        for t in instructions.suppressed_threads:
            if instructions.suppressed_threads[t] >= 0.5:
                self.stats["thread_suppression_count"][t] = \
                    self.stats["thread_suppression_count"].get(t, 0) + 1
        
        return instructions
    
    def _decrement_cooldowns(self):
        expired = []
        for t in self.thread_cooldowns:
            self.thread_cooldowns[t] -= 1
            if self.thread_cooldowns[t] <= 0:
                expired.append(t)
        for t in expired:
            del self.thread_cooldowns[t]
    
    def _compose_weaving(self, state: WorldState, world_type: str,
                            world_conf: float, context: ContextClassification,
                            risk: RiskState) -> WeavingInstructions:
        """Per Spec § 12: Context-to-Thread Policy
        
        Sparse activation 原則: 2-4 thread のみ active.
        """
        instr = WeavingInstructions(
            detected_world=world_type,
            detected_context=context.primary_context.value,
        )
        
        # === Invariant 7: R critical → high-intensity aggressive 抑制 ===
        if risk.r_critical:
            instr.action_size_cap = "A"
        
        # === Context-to-Thread Policy (Spec § 12) ===
        ctx = context.primary_context
        
        # PRIORITY: world hint (drifting world detected → drift behavior)
        # World-conditional override
        if world_type == "drifting" and world_conf > 0.55 and not risk.r_critical:
            # Spec § 12.3 Drifting:
            #   Primary: Drift, Synthesis-lite, Minimal Intervention
            #   Suppressed: Aggressive C, heavy generalized controls
            #   Rule: Prefer v9-like lean behavior
            instr.active_threads = {
                Thread.DRIFT: 0.75,
                Thread.SYNTHESIS: 0.55,
                Thread.RECOVERY: 0.30,
            }
            instr.suppressed_threads = {
                Thread.AGGRESSIVE: 0.85,
                Thread.MUTATION: 0.65,
                Thread.INVENTION: 0.70,
                Thread.EXPLORATION: 0.30,
            }
            instr.action_size_cap = "A"  # v9-like: A strength only
            instr.thread_priority = [Thread.SYNTHESIS, Thread.RECOVERY, Thread.DRIFT]
            instr.fallback_thread = Thread.RECOVERY
            instr.reason = "drift_detected_v9_like"
            return instr
        
        if ctx == Context.EMERGENCY:
            # Spec § 12.1
            instr.active_threads = {
                Thread.RECOVERY: 0.90,
                Thread.DEFENSIVE: 0.80,
            }
            instr.suppressed_threads = {
                Thread.AGGRESSIVE: 1.0,    # complete
                Thread.MUTATION: 1.0,
                Thread.INVENTION: 1.0,
                Thread.EXPLORATION: 0.50,
            }
            instr.action_size_cap = "A"
            instr.thread_priority = [Thread.RECOVERY, Thread.DEFENSIVE]
            instr.fallback_thread = Thread.RECOVERY
            instr.reason = "emergency_survival_first"
            return instr
        
        elif ctx == Context.RECOVERY:
            # Spec § 12.2
            instr.active_threads = {
                Thread.RECOVERY: 0.80,
                Thread.DEFENSIVE: 0.60,
            }
            secondary = {}
            # Information value if O reasonable
            if state.O > 50 and not risk.x_high:
                secondary[Thread.EXPLORATION] = 0.25  # secondary, A only
            instr.active_threads.update(secondary)
            instr.suppressed_threads = {
                Thread.AGGRESSIVE: 0.75,
                Thread.MUTATION: 0.60,
                Thread.INVENTION: 0.70,
            }
            instr.action_size_cap = "A"
            instr.fallback_thread = Thread.RECOVERY
            instr.reason = "recovery_with_limited_exploration"
            return instr
        
        elif ctx == Context.OPPORTUNITY:
            # Spec § 12.5
            instr.active_threads = {
                Thread.AGGRESSIVE: 0.60,  # small reversible attack
                Thread.EXPLORATION: 0.45,
                Thread.SYNTHESIS: 0.40,
            }
            # Recovery suppressed if R sufficient and no drawdown
            if state.R >= 50 and not risk.drawdown_recent:
                instr.suppressed_threads = {
                    Thread.RECOVERY: 0.40,
                }
            # Drift secondary if trend present
            if world_type == "drifting":
                instr.active_threads[Thread.DRIFT] = 0.30
            instr.action_size_cap = "B"  # B strength allowed for opportunity
            if Thread.AGGRESSIVE in self.thread_cooldowns:
                instr.action_size_cap = "A"  # cooldown 中は A only
            else:
                # ★最大前進解禁 (Wolf Pursuit C / 全力非連続ジャンプ):
                #   verified-safe かつ 強い opportunity のときだけ C を許可。
                #   それ以外は B 上限のまま (過剰前進を出さない)。
                #   累積暴露 hard clamp (decide_weaving) と NRMO veto / safety が backstop。
                verified_safe = (
                    state.R >= 70 and state.X <= 40
                    and not risk.r_low and not risk.r_critical
                    and not risk.drawdown_recent
                    and risk.cumulative_exposure < 0.30
                    and world_type not in ("drifting", "chaotic")
                )
                strong_opportunity = (state.O >= 60 and risk.ruin_proximity <= 0.05)
                if verified_safe and strong_opportunity:
                    instr.action_size_cap = "C"            # 全力非連続ジャンプ解禁
                    instr.active_threads[Thread.AGGRESSIVE] = 0.80   # Wolf Pursuit 寄り
                    instr.active_threads[Thread.MUTATION] = 0.40     # 探索も広げる
                    instr.reason = "opportunity_verified_safe_full_forward_C"
                    self.stats["forward_C_unlocks"] = \
                        self.stats.get("forward_C_unlocks", 0) + 1
            instr.thread_priority = [Thread.AGGRESSIVE, Thread.SYNTHESIS, Thread.EXPLORATION]
            instr.fallback_thread = Thread.SYNTHESIS
            if instr.action_size_cap != "C":      # C 解禁時は full-forward reason を保持
                instr.reason = "opportunity_small_reversible"
            return instr
        
        elif ctx == Context.STAGNATION:
            # Spec § 12.6
            instr.active_threads = {
                Thread.MUTATION: 0.55,
                Thread.SYNTHESIS: 0.50,
                Thread.AGGRESSIVE: 0.35,  # small reversible
                Thread.EXPLORATION: 0.40,
            }
            instr.suppressed_threads = {
                Thread.RECOVERY: 0.40,  # if not improving
            }
            instr.action_size_cap = "B"
            if Thread.MUTATION in self.thread_cooldowns:
                instr.active_threads[Thread.MUTATION] = 0.20
            instr.thread_priority = [Thread.SYNTHESIS, Thread.EXPLORATION, Thread.MUTATION]
            instr.fallback_thread = Thread.SYNTHESIS
            instr.reason = "stagnation_explore_mutate"
            return instr
        
        elif ctx == Context.UNCERTAINTY:
            # Spec § 12.7
            instr.active_threads = {
                Thread.EXPLORATION: 0.60,  # probe/A
                Thread.SYNTHESIS: 0.30,    # synthesis-lite
                Thread.DEFENSIVE: 0.30,
            }
            instr.suppressed_threads = {
                Thread.AGGRESSIVE: 0.75,
                Thread.MUTATION: 0.50,
            }
            instr.action_size_cap = "A"
            instr.reason = "uncertainty_probe_only"
            return instr
        
        elif ctx == Context.DEFENSE:
            instr.active_threads = {
                Thread.DEFENSIVE: 0.80,
                Thread.RECOVERY: 0.40,
            }
            instr.suppressed_threads = {
                Thread.AGGRESSIVE: 0.65,
                Thread.MUTATION: 0.55,
            }
            instr.action_size_cap = "A"
            instr.fallback_thread = Thread.DEFENSIVE
            instr.reason = "defense_x_high"
            return instr
        
        else:  # NORMAL
            # World-conditional Chaotic / Noisy (Spec § 12.4)
            if world_type in ("chaotic", "noisy"):
                instr.active_threads = {
                    Thread.RECOVERY: 0.55,
                    Thread.DEFENSIVE: 0.45,
                    Thread.SYNTHESIS: 0.40,
                }
                # Exploration secondary
                if not risk.x_high:
                    instr.active_threads[Thread.EXPLORATION] = 0.25
                instr.suppressed_threads = {
                    Thread.AGGRESSIVE: 0.55,
                    Thread.MUTATION: 0.55,
                    Thread.INVENTION: 0.65,
                }
                instr.action_size_cap = "A"
                instr.thread_priority = [Thread.SYNTHESIS, Thread.RECOVERY, Thread.DEFENSIVE]
                instr.reason = f"normal_in_{world_type}_smoothing"
                return instr
            
            # Unknown world / Normal: default safety bias
            instr.active_threads = {
                Thread.RECOVERY: 0.50,
                Thread.DEFENSIVE: 0.40,
                Thread.SYNTHESIS: 0.40,
            }
            instr.suppressed_threads = {
                Thread.AGGRESSIVE: 0.60,
                Thread.MUTATION: 0.60,
                Thread.INVENTION: 0.65,
            }
            instr.action_size_cap = "A"
            instr.reason = "normal_default_safety"
            return instr
    
    def update_reward(self, reward: float):
        self.recent_rewards.append(float(reward))


# ============================================================
# LoomLayer (per Spec § 9)
# ============================================================

@dataclass
class WovenCandidate:
    """LoomLayer 適用後の candidate"""
    original_candidate: object  # FullCandidate
    thread: Thread
    activation_weight: float    # boost
    suppression_weight: float   # penalty
    adjusted_score: float        # score for selection
    allowed: bool                # action_size_cap pass
    reason: str = ""


class LoomLayer:
    """LoomCore の判断を candidate に適用する制御層"""
    
    # Strength order
    STRENGTH_ORDER = {"A": 1, "B": 2, "C": 3}
    
    # Activation boost scale
    ACTIVATION_BOOST_SCALE = 0.30
    SUPPRESSION_PENALTY_SCALE = 0.80
    
    def apply(self, candidates: List[object],
                instructions: WeavingInstructions,
                # ★ sociable essence hooks (optional)
                failure_tracker=None,
                apply_canonical_dedup: bool = False,
                state=None,
                ) -> List[WovenCandidate]:
        """各 candidate に thread の activation/suppression を適用.
        
        Per sociable numbers エッセンス:
          - failure_tracker: pre-rejection based on past failures
          - apply_canonical_dedup: canonical key dedup
        """
        # === Pre-processing: sociable essence ===
        n_pre_rejected_sociable = 0
        n_dedup_removed = 0
        
        if failure_tracker is not None and state is not None:
            filtered_cands = []
            for cand in candidates:
                thread = MODULE_TO_THREAD.get(cand.module)
                if thread is None:
                    filtered_cands.append(cand)
                    continue
                should_reject, _ = failure_tracker.should_pre_reject(
                    thread.value, state
                )
                if should_reject:
                    n_pre_rejected_sociable += 1
                    continue
                filtered_cands.append(cand)
            if not filtered_cands:
                # safety
                rec_keep = [c for c in candidates if c.module == "RecoveryCandidate"]
                filtered_cands = rec_keep[:1] if rec_keep else list(candidates[:1])
            candidates = filtered_cands
        
        if apply_canonical_dedup:
            try:
                from sociable_essence import CandidateCanonicalizer
                candidates, n_dedup_removed = CandidateCanonicalizer.deduplicate(candidates)
            except ImportError:
                pass
        
        woven = []
        cap_level = self.STRENGTH_ORDER.get(instructions.action_size_cap, 3)
        
        for cand in candidates:
            module_name = cand.module
            thread = MODULE_TO_THREAD.get(module_name)
            if thread is None:
                # Unknown module → default neutral
                woven.append(WovenCandidate(
                    original_candidate=cand,
                    thread=Thread.SYNTHESIS,  # arbitrary
                    activation_weight=0.0,
                    suppression_weight=0.0,
                    adjusted_score=self._base_score(cand),
                    allowed=True,
                    reason="unknown_thread",
                ))
                continue
            
            # Drift override: SynthesisStandalone in drifting context → DriftThread
            if (module_name == "SynthesisStandalone" 
                and instructions.detected_world == "drifting"):
                thread = Thread.DRIFT
            
            # Activation weight
            act_w = instructions.active_threads.get(thread, 0.0)
            
            # Suppression weight
            supp_w = instructions.suppressed_threads.get(thread, 0.0)
            
            # action_size_cap check
            allowed = True
            if cand.attack_candidate and cand.attack_candidate.strength:
                cand_level = self.STRENGTH_ORDER.get(cand.attack_candidate.strength, 3)
                if cand_level > cap_level:
                    allowed = False  # ruled out by cap
            
            # Suppression による完全除外
            if supp_w >= 0.95:
                allowed = False
            
            # Score adjustment
            base = self._base_score(cand)
            adjusted = (base 
                         + act_w * self.ACTIVATION_BOOST_SCALE
                         - supp_w * self.SUPPRESSION_PENALTY_SCALE)
            
            # Priority bonus
            if thread in instructions.thread_priority:
                priority_idx = instructions.thread_priority.index(thread)
                adjusted += (len(instructions.thread_priority) - priority_idx) * 0.05
            
            reason_parts = []
            if act_w > 0:
                reason_parts.append(f"act:{thread.value}:{act_w:.2f}")
            if supp_w > 0:
                reason_parts.append(f"supp:{thread.value}:{supp_w:.2f}")
            if not allowed:
                reason_parts.append("ruled_out")
            
            woven.append(WovenCandidate(
                original_candidate=cand,
                thread=thread,
                activation_weight=act_w,
                suppression_weight=supp_w,
                adjusted_score=adjusted,
                allowed=allowed,
                reason="|".join(reason_parts),
            ))
        
        return woven
    
    def _base_score(self, cand) -> float:
        """FullCandidate の基礎 score"""
        return (1.0 * cand.expected_upside
                 - 1.5 * cand.estimated_downside
                 + 0.5 * cand.reversibility)
    
    def select_best(self, woven: List[WovenCandidate],
                      instructions: WeavingInstructions) -> Optional[WovenCandidate]:
        """Selection: 最良 candidate を選ぶ.
        
        Sparse 原則:
          - allowed only
          - score 最大
          - fallback_thread を用意
        """
        # Step 1: allowed のみ
        eligible = [w for w in woven if w.allowed]
        
        if not eligible:
            # 全 candidate が ruled out → fallback
            if instructions.fallback_thread:
                fallback = [w for w in woven 
                            if w.thread == instructions.fallback_thread]
                if fallback:
                    fallback.sort(key=lambda x: -x.adjusted_score)
                    return fallback[0]
            return None
        
        # Step 2: score 最大
        eligible.sort(key=lambda x: -x.adjusted_score)
        return eligible[0]


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    
    print("=" * 70)
    print("LoomCore / LoomLayer Test")
    print("=" * 70)
    
    loom_core = LoomCore()
    loom_layer = LoomLayer()
    
    # 異なる context での weaving 判断
    test_states = [
        ("Emergency", WorldState(t=0, R=12, E=20, G=30, O=50, K=50, X=85,
                                   cumulative_score=0, is_ruined=False)),
        ("Recovery", WorldState(t=0, R=25, E=20, G=50, O=40, K=50, X=40,
                                  cumulative_score=0, is_ruined=False)),
        ("Opportunity", WorldState(t=0, R=60, E=70, G=60, O=80, K=50, X=30,
                                     cumulative_score=0, is_ruined=False)),
        ("Normal", WorldState(t=0, R=55, E=55, G=55, O=50, K=50, X=40,
                                cumulative_score=0, is_ruined=False)),
    ]
    
    for label, state in test_states:
        # Build dummy conditions
        conds = {"O_confidence": 0.8 if label == "Opportunity" else 0.6,
                  "observation_noise": 0.05}
        
        instr = loom_core.decide_weaving(state, conds)
        
        print(f"\n[{label}] state R={state.R} X={state.X} O={state.O}")
        print(f"  Detected: world={instr.detected_world}, context={instr.detected_context}")
        print(f"  Active threads: {[(t.value, f'{w:.2f}') for t, w in instr.active_threads.items()]}")
        print(f"  Suppressed: {[(t.value, f'{w:.2f}') for t, w in instr.suppressed_threads.items()]}")
        print(f"  Action cap: {instr.action_size_cap}, fallback: {instr.fallback_thread}")
        print(f"  Reason: {instr.reason}")
    
    print("\n[LoomCore / LoomLayer 動作確認 ✅]")
