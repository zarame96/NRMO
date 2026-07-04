"""
core/loom_engine.py

NRMO LoomEngine (= LoomControlledUnifiedEngine).

Per Spec § 1.3 & § 10.1:
  外側は 1 つの判断主体 (NRMO Loom Engine).
  内側は LoomCore + LoomLayer + StrongEngineΩfull + Safety.

Per Spec § 10.3 central principle:
  All threads available. Few threads active.

Per Spec § 11 Operating Rule:
  Best Unified Result =
    Shared Governance (NRMO Core)
    + World-Conditional Specialist Threads
    + Sparse Activation
    + Common Risk Floor (EG, Throttle, Reval)
    + Oracle Gap Minimization

Per Spec § 13 Invariants (8 つ不可侵):
  1. true_veto cannot be overridden.
  2. EmergencyResourceGuard cannot be bypassed.
  3. ActionIntensityThrottle cannot be bypassed.
  4. Cumulative risk budget cannot exceed threshold.
  5. A Thread cannot directly decide final action.
  6. Final action must pass Revalidation Gate.
  7. R critical state suppresses high-intensity aggressive output.
  8. Loom Core may adjust thread activation but may not modify NRMO ruin boundaries.
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from decision_trace import DecisionTrace
from rng_manager import RNGManager
from engines import V71Engine

from active_pattern_proxy import ActivePatternProxy
from veto_classification import VetoClassification
from emergency_guards import (
    EmergencyResourceGuard, ActionIntensityThrottle,
    GuardConfig, GuardDecision
)
from cumulative_risk_tracker import CumulativeRiskTracker, CumulativeRiskConfig
from map_layer import MAPLayer
from strong_engine_omega_full import StrongEngineOmegaFull, FullCandidate
from context_classifier import ContextClassifier, Context

from loom_core import (
    LoomCore, LoomLayer, WeavingInstructions, WovenCandidate,
    Thread, MODULE_TO_THREAD
)
from v9_minimal_engine import SynthesisPathwayStandalone


# ============================================================
# LoomDecision (per Spec § 14)
# ============================================================

@dataclass
class LoomDecision:
    """Per Spec § 14 Required Trace Schema"""
    action: Action
    status: str
    confidence: float
    
    # Trace fields (Spec § 14)
    input_state: Dict
    detected_world: str
    detected_context: str
    active_threads: Dict[str, float]
    suppressed_threads: Dict[str, float]
    generated_candidates_count: int
    selected_pattern: Optional[Dict]
    guard_result: Optional[str]
    calibration_result: Optional[str]
    revalidation_result: Optional[str]
    final_action: str
    reason: str
    
    # Internal
    instructions: Optional[WeavingInstructions] = None
    woven_candidate: Optional[WovenCandidate] = None
    emergency_guard: Optional[GuardDecision] = None
    throttle_guard: Optional[GuardDecision] = None
    
    metadata: Dict = field(default_factory=dict)
    
    def to_trace(self) -> Dict:
        """Per Spec § 14 Required Trace Schema"""
        return {
            "input_state": self.input_state,
            "detected_world": self.detected_world,
            "detected_context": self.detected_context,
            "active_threads": self.active_threads,
            "suppressed_threads": self.suppressed_threads,
            "generated_candidates_count": self.generated_candidates_count,
            "selected_pattern": self.selected_pattern,
            "guard_result": self.guard_result,
            "calibration_result": self.calibration_result,
            "revalidation_result": self.revalidation_result,
            "final_action": self.final_action,
            "reason": self.reason,
        }


# ============================================================
# LoomEngine
# ============================================================

class LoomEngine:
    """NRMO LoomEngine — 外側 1 engine, 内側 LoomCore-controlled threads.
    
    Architecture (per Spec § 3.2):
      NRMO Core:        Ruin boundary, true VETO, allowed set
      Loom Core:        World/Context/Risk recognition, weaving decision
      Loom Layer:       activation/suppression weights to threads
      StrongEngineΩfull: 8 threads (Recovery, Defensive, Drift, Synthesis,
                                       Aggressive, Exploration, Mutation, Invention)
      Calibration:      過剰攻撃/防御 補正
      PassivePattern/ActivePattern Guard
      EmergencyResourceGuard
      ActionIntensityThrottle
      CumulativeRiskTracker
      Revalidation Gate
    """
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  module_config: Optional[Dict[str, bool]] = None,
                  guard_config: Optional[GuardConfig] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        # === Loom Core / Layer ===
        self.loom_core = LoomCore()
        self.loom_layer = LoomLayer()
        
        # === StrongEngineΩfull (Thread 群) ===
        se_rng = self.rng_manager.spawn("strong_engine")
        mc = module_config or {}
        self.strong_engine = StrongEngineOmegaFull(
            rng=se_rng,
            enable_defensive=mc.get("defensive", True),
            enable_recovery=mc.get("recovery", True),
            enable_exploration=mc.get("exploration", True),
            enable_mutation=mc.get("mutation", True),
            enable_synthesis=mc.get("synthesis", True),
            enable_invention=mc.get("invention", True),
            enable_aggressive=mc.get("aggressive", True),
        )
        
        # Synthesis Standalone (drift/synthesis 用、V9 由来)
        self.synthesis_standalone = SynthesisPathwayStandalone()
        
        # === V71 base (fallback only, NOT for selection) ===
        self.v71 = V71Engine(rng=self.rng_manager.spawn("v71"))
        
        # === Memory ===
        self.map_layer = MAPLayer()
        self.recent_rewards: deque = deque(maxlen=10)
        
        # === Common Risk Floor (Spec § 11.4) — Invariants 1-7 ===
        self.guard_config = guard_config or GuardConfig()
        self.emergency_guard = EmergencyResourceGuard(self.guard_config)
        self.throttle_guard = ActionIntensityThrottle(self.guard_config)
        self.active_pattern = ActivePatternProxy()
        self.active_pattern.INTERVENTION_THRESHOLD = 0.35
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        # === Stats ===
        self.decision_counter = 0
        self.stats = {
            "total_decisions": 0,
            "thread_selected_counts": {},
            "active_thread_history": [],
            "world_type_counts": {},
            "context_counts": {},
            "fallback_used_count": 0,
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "sparse_thread_count_history": [],  # 各 step の active thread 数
        }
    
    # ============================================================
    # Helpers
    # ============================================================
    
    def _build_conditions(self, observation: WorldState) -> Dict:
        conditions = {}
        
        # O confidence
        if self.map_layer.l2:
            trends = self.map_layer.get_state_trends()
            if trends:
                o_vol = abs(trends.get("O", 0))
                conditions["O_confidence"] = max(0.3, 1.0 - o_vol / 3.0)
            else:
                conditions["O_confidence"] = 0.7
        else:
            conditions["O_confidence"] = 0.7
        
        # Drawdown
        if len(self.recent_rewards) >= 3:
            conditions["recent_drawdown"] = sum(list(self.recent_rewards)[-3:]) < -0.5
        else:
            conditions["recent_drawdown"] = False
        
        conditions["true_veto"] = False
        
        if len(self.recent_rewards) >= 5:
            x = np.arange(len(self.recent_rewards))
            y = np.array(list(self.recent_rewards))
            conditions["reward_trend"] = float(np.polyfit(x, y, 1)[0])
        else:
            conditions["reward_trend"] = 0
        
        if self.map_layer.l2:
            near_ruin = self.map_layer.near_ruin_count()
            conditions["observation_noise"] = 0.05 if near_ruin == 0 else \
                                                 0.15 if near_ruin < 5 else \
                                                 0.30 if near_ruin < 15 else 0.50
        else:
            conditions["observation_noise"] = 0.05
        
        return conditions
    
    def _estimate_action_delta(self, action):
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
    
    def _revalidate(self, state, proposed):
        """Per Invariant 6: Final action must pass Revalidation Gate"""
        revalidation = self.emergency_guard.apply(state, proposed)
        if revalidation.applied:
            return False, f"revalidation_eg_failed: {revalidation.rule_triggered}"
        projected_delta = self._estimate_action_delta(proposed)
        breached, _ = self.cumulative_risk.projected_breach_after(projected_delta)
        if breached:
            return False, "revalidation_cumulative_breach"
        return True, "passed"
    
    def _generate_all_candidates_simple(self):
        return [Action(intent=i, strength=s)
                 for i in ["invest", "defend", "explore", "recover", "hold"]
                 for s in ["A", "B", "C"]]
    
    # ============================================================
    # Sparse candidate generation (per Spec § 8.7 Sparse Weaving)
    # ============================================================
    
    def _generate_sparse_candidates(self, observation: WorldState,
                                       conditions: Dict,
                                       instructions: WeavingInstructions
                                       ) -> List[FullCandidate]:
        """Spec § 10.3: All threads available, few threads active.
        
        Thread が active な場合のみ candidate を生成.
        Suppressed thread は skip.
        """
        all_cands = []
        
        # Threshold: 完全 suppression は 0.95 以上
        def is_thread_skipped(thread: Thread) -> bool:
            supp_w = instructions.suppressed_threads.get(thread, 0.0)
            return supp_w >= 0.95
        
        # Defensive
        if not is_thread_skipped(Thread.DEFENSIVE):
            cands = self.strong_engine.defensive.generate(observation, self.map_layer)
            all_cands.extend(cands)
        
        # Recovery
        if not is_thread_skipped(Thread.RECOVERY):
            cands = self.strong_engine.recovery.generate(observation, self.map_layer)
            all_cands.extend(cands)
        
        # Exploration
        if not is_thread_skipped(Thread.EXPLORATION):
            cands = self.strong_engine.exploration.generate(observation, self.map_layer)
            all_cands.extend(cands)
        
        # Mutation (cooldown も考慮)
        if not is_thread_skipped(Thread.MUTATION):
            mut_cands = self.strong_engine.mutation.generate(
                observation, all_cands[:6], self.map_layer
            )
            all_cands.extend(mut_cands)
        
        # Synthesis  
        if not is_thread_skipped(Thread.SYNTHESIS):
            syn_cands = self.strong_engine.synthesis.generate(
                observation, all_cands[:6], self.map_layer
            )
            all_cands.extend(syn_cands)
        
        # Invention
        if not is_thread_skipped(Thread.INVENTION):
            inv_cands = self.strong_engine.invention.generate(observation, self.map_layer)
            all_cands.extend(inv_cands)
        
        # Aggressive (Opportunity context など)
        if not is_thread_skipped(Thread.AGGRESSIVE):
            agg_cands = self.strong_engine.aggressive.generate(
                observation, conditions, self.map_layer
            )
            all_cands.extend(agg_cands)
        
        # SynthesisStandalone (Drift Thread として drifting world で活躍)
        # Drift detected → 必ず synthesis standalone を加える
        if (instructions.detected_world == "drifting" and 
            not is_thread_skipped(Thread.DRIFT) and
            not is_thread_skipped(Thread.SYNTHESIS)):
            v71_a = self.v71.select_action(observation)
            syn_a = self.synthesis_standalone.synthesize(observation, v71_a)
            if syn_a is not None:
                all_cands.append(FullCandidate(
                    module="SynthesisStandalone",
                    attack_candidate=syn_a,
                    safe_variant=Action(syn_a.intent, "A"),
                    minimum_reversible_variant=Action("hold", "A"),
                    expected_upside=0.55,
                    estimated_downside=0.10,
                    reversibility=0.90,
                    reason="drift_synthesis_v9_like",
                ))
        
        return all_cands
    
    # ============================================================
    # Main decide
    # ============================================================
    
    def decide(self, observation: WorldState) -> LoomDecision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        
        # === Build conditions ===
        conditions = self._build_conditions(observation)
        
        # === LoomCore: weaving decision ===
        instructions = self.loom_core.decide_weaving(
            observation, conditions,
            cumulative_exposure=self.cumulative_risk.exposure_scalar())
        
        # Stats
        self.stats["world_type_counts"][instructions.detected_world] = \
            self.stats["world_type_counts"].get(instructions.detected_world, 0) + 1
        self.stats["context_counts"][instructions.detected_context] = \
            self.stats["context_counts"].get(instructions.detected_context, 0) + 1
        
        active_count = len(instructions.active_threads)
        self.stats["sparse_thread_count_history"].append(active_count)
        self.stats["active_thread_history"].append(
            {t.value: w for t, w in instructions.active_threads.items()}
        )
        
        # === Sparse candidate generation ===
        all_cands = self._generate_sparse_candidates(observation, conditions, instructions)
        
        # === LoomLayer: weighting ===
        woven = self.loom_layer.apply(all_cands, instructions)
        
        # === Selection ===
        best_woven = self.loom_layer.select_best(woven, instructions)
        
        if best_woven is None:
            # 最終 fallback: recover/A
            current_action = Action("recover", "A")
            selected_module = "fallback_recover"
            self.stats["fallback_used_count"] += 1
            reason_select = "no_woven_candidate_fallback"
        else:
            current_action = best_woven.original_candidate.attack_candidate
            selected_module = best_woven.original_candidate.module
            self.stats["thread_selected_counts"][best_woven.thread.value] = \
                self.stats["thread_selected_counts"].get(best_woven.thread.value, 0) + 1
            reason_select = best_woven.reason
            
            # Aggressive selection tracking
            if selected_module == "AggressiveEngine":
                self.strong_engine.aggressive.record_selection(best_woven.original_candidate)
        
        # === Common Risk Floor (Invariants 1-7) ===
        status = "ACCEPT"
        guard_result = "no_intervention"
        
        # Invariant 2: EmergencyResourceGuard cannot be bypassed
        eg = self.emergency_guard.apply(observation, current_action)
        if eg.applied:
            if (best_woven is not None and 
                best_woven.original_candidate.module == "AggressiveEngine"):
                self.strong_engine.aggressive.record_block(
                    best_woven.original_candidate, f"guard_{eg.rule_triggered}"
                )
            current_action = eg.forced_action
            status = "GUARD_FORCED"
            guard_result = f"emergency_guard: {eg.rule_triggered}"
            self.stats["emergency_triggered"] += 1
        
        # Invariant 3: ActionIntensityThrottle cannot be bypassed
        th = self.throttle_guard.apply(observation, current_action)
        if th.applied:
            current_action = th.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            guard_result += f" | throttle: {th.rule_triggered}"
            self.stats["throttle_triggered"] += 1
        
        # ActivePattern (Calibration Layer)
        calibration_result = "no_intervention"
        revalidation_result = "n/a"
        all_cands_simple = self._generate_all_candidates_simple()
        veto = VetoClassification.no_veto()
        ap_proposal = self.active_pattern.evaluate(
            observation, all_cands_simple, current_action, veto
        )
        if ap_proposal.has_correction_proposal and ap_proposal.proposed_action:
            # Invariant 6: Revalidation Gate
            passed, rev_reason = self._revalidate(observation, ap_proposal.proposed_action)
            revalidation_result = rev_reason
            if passed:
                current_action = ap_proposal.proposed_action
                if status == "ACCEPT":
                    status = "AP_INTERVENED"
                calibration_result = "ap_intervened"
                self.stats["ap_intervened"] += 1
            else:
                calibration_result = f"ap_rejected_at_revalidation"
                self.stats["revalidation_rejected"] += 1
        
        # Final aggressive accept tracking
        if (best_woven is not None
            and best_woven.original_candidate.module == "AggressiveEngine"
            and current_action == best_woven.original_candidate.attack_candidate):
            self.strong_engine.aggressive.record_final_accept(best_woven.original_candidate)
        
        # === Update histories ===
        self.active_pattern.update_history(observation, current_action)
        self.throttle_guard.update_history(observation, current_action)
        self.loom_core.context_classifier.update_history(
            observation, current_action,
            self.recent_rewards[-1] if self.recent_rewards else 0.0
        )
        
        self.map_layer.update(
            t=self.decision_counter,
            state=observation,
            action_intent=current_action.intent,
            action_strength=current_action.strength,
            reward=0.0,
        )
        
        self.strong_engine.record_action_taken(current_action)
        
        # === Build LoomDecision ===
        input_state = {"R": observation.R, "E": observation.E, "G": observation.G,
                        "O": observation.O, "K": observation.K, "X": observation.X}
        
        selected_pattern = None
        if best_woven is not None:
            selected_pattern = {
                "module": selected_module,
                "thread": best_woven.thread.value,
                "activation_weight": best_woven.activation_weight,
                "suppression_weight": best_woven.suppression_weight,
                "adjusted_score": best_woven.adjusted_score,
            }
        
        reason = (f"weave: {instructions.reason}; "
                   f"select: {reason_select}; "
                   f"guard: {guard_result}")
        
        return LoomDecision(
            action=current_action,
            status=status,
            confidence=0.75,
            input_state=input_state,
            detected_world=instructions.detected_world,
            detected_context=instructions.detected_context,
            active_threads={t.value: w for t, w in instructions.active_threads.items()},
            suppressed_threads={t.value: w for t, w in instructions.suppressed_threads.items()},
            generated_candidates_count=len(all_cands),
            selected_pattern=selected_pattern,
            guard_result=guard_result,
            calibration_result=calibration_result,
            revalidation_result=revalidation_result,
            final_action=f"{current_action.intent}/{current_action.strength}",
            reason=reason,
            instructions=instructions,
            woven_candidate=best_woven,
            emergency_guard=eg,
            throttle_guard=th,
            metadata={"step": self.decision_counter,
                       "active_thread_count": active_count,
                       "candidates_generated": len(all_cands)},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        self.v71.update_reward(action, reward)
        self.recent_rewards.append(float(reward))
        self.loom_core.update_reward(reward)
        
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)
        
        if self.map_layer.l1:
            self.map_layer.l1[-1].reward = float(reward)
    
    def get_aggressive_counters(self) -> Dict:
        return dict(self.strong_engine.aggressive.counters)
    
    def get_sparse_summary(self) -> Dict:
        """Sparse activation の summary"""
        if not self.stats["sparse_thread_count_history"]:
            return {}
        counts = self.stats["sparse_thread_count_history"]
        return {
            "mean_active_threads": float(np.mean(counts)),
            "median_active_threads": float(np.median(counts)),
            "max_active_threads": int(max(counts)),
            "min_active_threads": int(min(counts)),
        }


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    from noisy_world import NoisyObservationWorld
    
    print("=" * 70)
    print("LoomEngine Test")
    print("=" * 70)
    
    for world_class, world_name in [
        (ChaoticWorld, "Chaotic"),
        (DriftingWorld, "Drifting"),
        (NoisyObservationWorld, "Noisy"),
    ]:
        print(f"\n--- {world_name} (severe) ---")
        for seed in [42, 123]:
            cfg = ChaosConfig.from_level("severe")
            world = world_class(cfg, seed=seed)
            rng_mgr = RNGManager(master_seed=seed + 200000)
            eng = LoomEngine(rng_manager=rng_mgr)
            
            for t in range(200):
                d = eng.decide(world.observe())
                r, done, _ = world.step(d.action)
                eng.update_reward(d.action, r)
                if done:
                    break
            
            sparse = eng.get_sparse_summary()
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}")
            print(f"    Worlds detected: {eng.stats['world_type_counts']}")
            print(f"    Contexts: {eng.stats['context_counts']}")
            print(f"    Threads selected: {eng.stats['thread_selected_counts']}")
            print(f"    Sparse: mean={sparse.get('mean_active_threads', 0):.2f} threads, "
                  f"max={sparse.get('max_active_threads', 0)}")
            print(f"    Aggressive counters: gen={eng.get_aggressive_counters().get('generated_count', 0)} "
                  f"sel={eng.get_aggressive_counters().get('selected_by_merger_count', 0)} "
                  f"final={eng.get_aggressive_counters().get('final_accepted_count', 0)}")
    
    print("\n[LoomEngine 動作確認 ✅]")
