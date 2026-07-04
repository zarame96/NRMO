"""
core/loom_engine_v2.py

NRMO LoomEngine v2 — sociable numbers エッセンス統合版.

Per spec NRMO_Loom_Core_Loom_Layer_Spec.md + sociable_numbers_v6_9_handoff.md.

Additional mechanisms over v1:
  - FailureFaceTracker: thread × failure-face profile, residue avoidance
  - CandidateCanonicalizer: candidate deduplication (canonical4 風)
  - SociableCycleDetector: k-cycle detection, stagnation breakthrough

Theoretical addition (per sociable numbers handoff):
  - "p3-dominant halo channel" → "Recovery-dominant safe channel"
    → 数理的に同等な構造 (一強 face による degenerate basin)
  - "p3-residue-avoidance" → "Recovery pre-rejection at known fail signatures"
  - "Equal-Sigma verification" → Revalidation Gate (既存)
  - "Sociable chain σ^k(N)=N" → k-cycle = stagnation orbit
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
from rng_manager import RNGManager
from emergency_guards import GuardConfig

from loom_engine import LoomEngine, LoomDecision
from loom_core import (
    LoomCore, LoomLayer, WeavingInstructions, WovenCandidate,
    Thread, MODULE_TO_THREAD
)
from sociable_essence import (
    FailureFaceTracker, FailureFace,
    CandidateCanonicalizer, CanonicalCandidate,
    SociableCycleDetector, CycleInfo,
)


# ============================================================
# LoomEngine v2
# ============================================================

class LoomEngineV2(LoomEngine):
    """LoomEngine + sociable numbers エッセンス統合.
    
    Per sociable numbers theory:
      - failure-face profiling で thread × state-signature 蓄積
      - canonical deduplication で candidate pool clean
      - sociable cycle 検出で stagnation breakthrough
    """
    
    # Cycle breakthrough parameters
    STAGNATION_BREAK_ACTIVATION_BOOST = 0.30
    
    # Reward thresholds for failure record
    FAILURE_REWARD_THRESHOLD = -0.20  # この値以下 = failure
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  module_config: Optional[Dict[str, bool]] = None,
                  guard_config: Optional[GuardConfig] = None,
                  # New ablation switches
                  use_failure_tracker: bool = True,
                  use_canonical_dedup: bool = True,
                  use_cycle_detector: bool = True):
        super().__init__(rng_manager=rng_manager,
                          module_config=module_config,
                          guard_config=guard_config)
        
        # === Sociable essence components ===
        self.use_failure_tracker = use_failure_tracker
        self.use_canonical_dedup = use_canonical_dedup
        self.use_cycle_detector = use_cycle_detector
        
        self.failure_tracker = FailureFaceTracker() if use_failure_tracker else None
        self.cycle_detector = SociableCycleDetector() if use_cycle_detector else None
        
        # Track last selected (state, thread) for reward attribution
        self.last_state_before: Optional[WorldState] = None
        self.last_selected_thread: Optional[Thread] = None
        
        # Stagnation breakthrough state
        self.stagnation_break_active: bool = False
        self.stagnation_break_cooldown: int = 0
        
        # Stats extension
        self.stats.update({
            "canonical_duplicates_removed": 0,
            "pre_rejected_by_failure_tracker": 0,
            "cycles_detected": 0,
            "stagnation_breaks_activated": 0,
            "failure_records_added": 0,
        })
    
    # ============================================================
    # Override: decide
    # ============================================================
    
    def decide(self, observation: WorldState) -> LoomDecision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        
        # === Sensing + LoomCore ===
        conditions = self._build_conditions(observation)
        instructions = self.loom_core.decide_weaving(observation, conditions)
        
        # === Sociable: Cycle detection ===
        cycle_detected = None
        if self.use_cycle_detector and self.cycle_detector is not None:
            cycle_detected = self.cycle_detector.detect_cycle()
            if cycle_detected and cycle_detected.stagnation:
                if self.stagnation_break_cooldown <= 0:
                    self.stagnation_break_active = True
                    self.stagnation_break_cooldown = 5  # 5 step 持続
                    self.stats["stagnation_breaks_activated"] += 1
                    self.stats["cycles_detected"] += 1
                    instructions = self._apply_stagnation_breakthrough(instructions)
                    instructions.reason += f"|stagnation_break(cycle{cycle_detected.cycle_length})"
        
        if self.stagnation_break_cooldown > 0:
            self.stagnation_break_cooldown -= 1
        else:
            self.stagnation_break_active = False
        
        # Stats
        self.stats["world_type_counts"][instructions.detected_world] = \
            self.stats["world_type_counts"].get(instructions.detected_world, 0) + 1
        self.stats["context_counts"][instructions.detected_context] = \
            self.stats["context_counts"].get(instructions.detected_context, 0) + 1
        active_count = len(instructions.active_threads)
        self.stats["sparse_thread_count_history"].append(active_count)
        
        # === Sparse candidate generation ===
        all_cands = self._generate_sparse_candidates(observation, conditions, instructions)
        
        # === Sociable: Canonical Deduplication ===
        if self.use_canonical_dedup:
            all_cands, n_removed = CandidateCanonicalizer.deduplicate(all_cands)
            self.stats["canonical_duplicates_removed"] += n_removed
        
        # === Sociable: Pre-rejection by failure tracker ===
        if self.use_failure_tracker and self.failure_tracker is not None:
            filtered = []
            for cand in all_cands:
                thread = MODULE_TO_THREAD.get(cand.module)
                if thread is None:
                    filtered.append(cand)
                    continue
                # SynthesisStandalone は drifting で必須 → bypass pre-reject
                if (cand.module == "SynthesisStandalone" and
                    instructions.detected_world == "drifting"):
                    filtered.append(cand)
                    continue
                should_reject, _ = self.failure_tracker.should_pre_reject(
                    thread.value, observation
                )
                if should_reject:
                    self.stats["pre_rejected_by_failure_tracker"] += 1
                    continue
                filtered.append(cand)
            
            # Safety: 全部弾かれたら recover/A 残す
            if not filtered:
                from strong_engine_omega_full import FullCandidate
                filtered.append(FullCandidate(
                    module="RecoveryCandidate",
                    attack_candidate=Action("recover", "A"),
                    safe_variant=Action("recover", "A"),
                    minimum_reversible_variant=Action("hold", "A"),
                    expected_upside=0.40, estimated_downside=0.05, reversibility=0.95,
                    reason="forced_recovery_after_all_rejected",
                ))
            all_cands = filtered
        
        # === LoomLayer: weighting ===
        woven = self.loom_layer.apply(all_cands, instructions)
        
        # === Selection ===
        best_woven = self.loom_layer.select_best(woven, instructions)
        
        if best_woven is None:
            current_action = Action("recover", "A")
            selected_module = "fallback_recover"
            self.stats["fallback_used_count"] += 1
            reason_select = "no_woven_fallback"
            selected_thread = Thread.RECOVERY
        else:
            current_action = best_woven.original_candidate.attack_candidate
            selected_module = best_woven.original_candidate.module
            selected_thread = best_woven.thread
            self.stats["thread_selected_counts"][best_woven.thread.value] = \
                self.stats["thread_selected_counts"].get(best_woven.thread.value, 0) + 1
            reason_select = best_woven.reason
            
            if selected_module == "AggressiveEngine":
                self.strong_engine.aggressive.record_selection(best_woven.original_candidate)
        
        # === Common Risk Floor (Invariants) ===
        from emergency_guards import GuardDecision
        from veto_classification import VetoClassification
        
        status = "ACCEPT"
        guard_result = "no_intervention"
        
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
            
            # Sociable: failure record (guard reject = high-severity failure)
            if self.use_failure_tracker and self.failure_tracker is not None:
                self.failure_tracker.record_failure(
                    selected_thread.value, FailureFace.GUARD_REJECTION,
                    observation, self.decision_counter
                )
                self.stats["failure_records_added"] += 1
        
        th = self.throttle_guard.apply(observation, current_action)
        if th.applied:
            current_action = th.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            guard_result += f" | throttle: {th.rule_triggered}"
            self.stats["throttle_triggered"] += 1
        
        # ActivePattern
        calibration_result = "no_intervention"
        revalidation_result = "n/a"
        all_cands_simple = self._generate_all_candidates_simple()
        veto = VetoClassification.no_veto()
        ap_proposal = self.active_pattern.evaluate(
            observation, all_cands_simple, current_action, veto
        )
        if ap_proposal.has_correction_proposal and ap_proposal.proposed_action:
            passed, rev_reason = self._revalidate(observation, ap_proposal.proposed_action)
            revalidation_result = rev_reason
            if passed:
                current_action = ap_proposal.proposed_action
                if status == "ACCEPT":
                    status = "AP_INTERVENED"
                calibration_result = "ap_intervened"
                self.stats["ap_intervened"] += 1
            else:
                calibration_result = "ap_rejected_at_revalidation"
                self.stats["revalidation_rejected"] += 1
        
        # Final aggressive accept tracking
        if (best_woven is not None
            and best_woven.original_candidate.module == "AggressiveEngine"
            and current_action == best_woven.original_candidate.attack_candidate):
            self.strong_engine.aggressive.record_final_accept(best_woven.original_candidate)
        
        # Histories
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
        
        # Remember for update_reward
        self.last_state_before = observation
        self.last_selected_thread = selected_thread
        
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
        if cycle_detected:
            reason += f" | cycle_detected:k={cycle_detected.cycle_length}"
        
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
                       "candidates_generated": len(all_cands),
                       "cycle_detected": cycle_detected.cycle_length if cycle_detected else None,
                       "stagnation_break_active": self.stagnation_break_active},
        )
    
    def _apply_stagnation_breakthrough(self, instructions: WeavingInstructions
                                          ) -> WeavingInstructions:
        """Per sociable numbers: σ^k(N)=N detected → 別 channel に escape.
        
        Sociable chain (stagnation cycle) を抜けるため Aggressive/Mutation を boost.
        """
        # Reduce Recovery suppression (let other threads win)
        if Thread.RECOVERY in instructions.active_threads:
            instructions.active_threads[Thread.RECOVERY] *= 0.4
        
        # Boost breakthrough threads
        boosted_threads = [Thread.AGGRESSIVE, Thread.MUTATION,
                            Thread.SYNTHESIS, Thread.EXPLORATION]
        for t in boosted_threads:
            current = instructions.active_threads.get(t, 0.0)
            instructions.active_threads[t] = max(current, 0.55)
            # Remove from suppressed
            if t in instructions.suppressed_threads:
                instructions.suppressed_threads[t] = 0.0
        
        # Allow B strength
        instructions.action_size_cap = "B"
        
        return instructions
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        # super: V71 + recent_rewards + loom_core + cum_risk + maplayer
        super().update_reward(action, reward, state_before, state_after)
        
        # Sociable: cycle detector update (use last_state_before which is WorldState)
        if (self.use_cycle_detector and self.cycle_detector is not None 
            and self.last_state_before is not None):
            self.cycle_detector.update(self.last_state_before, action, reward)
        
        # Sociable: failure tracking (low reward = failure attribution)
        if (self.use_failure_tracker and self.failure_tracker is not None
            and reward < self.FAILURE_REWARD_THRESHOLD
            and self.last_state_before is not None
            and self.last_selected_thread is not None):
            
            face = self._infer_failure_face(action, reward, self.last_state_before)
            self.failure_tracker.record_failure(
                self.last_selected_thread.value, face,
                self.last_state_before, self.decision_counter
            )
            self.stats["failure_records_added"] += 1
    
    def _infer_failure_face(self, action: Action, reward: float,
                              state: WorldState) -> FailureFace:
        """Reward 低い理由 = どの face かを推定"""
        if state.R <= 20:
            return FailureFace.R_CRITICAL
        if state.X >= 70:
            return FailureFace.X_HIGH
        if state.O <= 30 and action.intent == "invest":
            return FailureFace.O_LOW
        if state.E <= 25 and action.intent == "defend":
            return FailureFace.E_LOW
        if action.strength == "C":
            return FailureFace.REVERSIBILITY_LOW
        return FailureFace.REPETITION
    
    def get_sociable_summary(self) -> Dict:
        return {
            "canonical_duplicates_removed": self.stats["canonical_duplicates_removed"],
            "pre_rejected_count": self.stats["pre_rejected_by_failure_tracker"],
            "cycles_detected": self.stats["cycles_detected"],
            "stagnation_breaks": self.stats["stagnation_breaks_activated"],
            "failure_records": self.stats["failure_records_added"],
            "failure_tracker_summary": (self.failure_tracker.get_summary() 
                                          if self.failure_tracker else None),
            "cycle_detector_summary": (self.cycle_detector.get_summary()
                                         if self.cycle_detector else None),
        }


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    
    print("=" * 70)
    print("LoomEngine v2 (with Sociable Essence) Test")
    print("=" * 70)
    
    for world_class, world_name in [(ChaoticWorld, "Chaotic"),
                                       (DriftingWorld, "Drifting")]:
        print(f"\n--- {world_name} (severe) ---")
        for seed in [42, 123]:
            cfg = ChaosConfig.from_level("severe")
            world = world_class(cfg, seed=seed)
            rng_mgr = RNGManager(master_seed=seed + 200000)
            eng = LoomEngineV2(rng_manager=rng_mgr,
                                  use_failure_tracker=True,
                                  use_canonical_dedup=True,
                                  use_cycle_detector=True)
            
            for t in range(200):
                observed = world.observe()
                d = eng.decide(observed)
                sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                      "O": world.state.O, "K": world.state.K, "X": world.state.X}
                r, done, _ = world.step(d.action)
                sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                      "O": world.state.O, "K": world.state.K, "X": world.state.X}
                eng.update_reward(d.action, r, sb, sa)
                if done:
                    break
            
            socsum = eng.get_sociable_summary()
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}")
            print(f"    canonical_dedup_removed: {socsum['canonical_duplicates_removed']}")
            print(f"    pre_rejected: {socsum['pre_rejected_count']}")
            print(f"    cycles_detected: {socsum['cycles_detected']}, "
                  f"stagnation_breaks: {socsum['stagnation_breaks']}")
            print(f"    failure_records: {socsum['failure_records']}")
            print(f"    Threads selected: {eng.stats['thread_selected_counts']}")
    
    print("\n[LoomEngineV2 動作確認 ✅]")
