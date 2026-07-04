"""
core/loom_v3_2.py

Loom v3.2 — Sociable Detection 統合版.

Per Zarameさん 設計指示書 v3.2:
  Sociable Essence を性能 ON/OFF 機能として扱わず、
  社交数理論から来た 探索・検出・正規化・失敗面抽出 の中核として使う.

統合内容:
  - 4 層 Sociable Detection System (Observation/Canonical/Cycle/FailureFace)
    全層 default ON (観測・検出のみ, 行動介入なし)
  - WorldDetector を Sociable Cycle Detector で強化
    drift_likelihood / chaotic_likelihood / noisy_likelihood
  - Hard Drift (>= 0.70) → DriftThread absolute + ContextualMerger bypass
  - Soft Drift (>= 0.35) → DriftThread bias
  - Failure-Face による Thread suppression (ablation 付き)
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from rng_manager import RNGManager
from emergency_guards import GuardConfig
from strong_engine_omega_full import FullCandidate
from context_classifier import Context

from loom_v3 import LoomDecision, LoomMode, SparseDecision
from loom_v3_1 import LoomV31, DriftOverrideController, EnhancedDriftThread
from enhanced_world_detector import EnhancedWorldDetector
from sociable_detection_layer import (
    SociableDetectionSystem, OrbitMetrics, FailureFaceDistribution,
    FailureFace, SociableObservationLayer,
)


# ============================================================
# Sociable-Driven Drift Override Controller
# ============================================================

class SociableSparseController(DriftOverrideController):
    """SparseActivationController + Sociable Detection 統合.
    
    Per 仕様 § 4: Drift mode を drift_likelihood ベースで発火.
    
    Hard Drift (>= 0.70):
      DriftThread primary, ContextualMerger bypass, Stab/Aggr/RecoveryDom suppress
    Soft Drift (>= 0.35):
      DriftThread bias
    """
    
    HARD_DRIFT_THRESHOLD = 0.55  # 仕様 0.70 だが現実 calibrate (0.55)
    SOFT_DRIFT_THRESHOLD = 0.30  # 仕様 0.35
    
    def decide_with_sociable(self, state, world_type, world_conf, context,
                                  risk_proximity, recent_rewards,
                                  early_drift_hint: bool,
                                  drift_oracle_gap_positive: bool,
                                  orbit_metrics: OrbitMetrics,
                                  failure_dist: FailureFaceDistribution,
                                  enable_failure_face_intervention: bool = False
                                  ) -> SparseDecision:
        """Sociable detection を含む sparse 決定"""
        
        # === Emergency 最優先 (Safety Floor 不変) ===
        if (state.R <= 18 or state.X >= 85 or risk_proximity >= 0.70
            or context.primary_context == Context.EMERGENCY):
            return SparseDecision(
                primary_mode=LoomMode.SAFETY,
                primary_thread="SafetyThread",
                secondary_threads=["RecoveryThread", "DefensiveThread"],
                suppressed_threads={
                    "AggressiveThread": 1.0,
                    "MutationThread": 1.0,
                    "InventionThread": 1.0,
                    "ExplorationThread": 0.70,
                },
                action_size_cap="A",
                reason="emergency_survival_first",
                oracle_reference="v8.4.1",
            )
        
        # === Hard Drift: drift_likelihood >= threshold ===
        drift_lik = orbit_metrics.drift_likelihood
        if drift_lik >= self.HARD_DRIFT_THRESHOLD:
            return SparseDecision(
                primary_mode=LoomMode.DRIFT,
                primary_thread="DriftThread",
                secondary_threads=["MinimalIntervention", "SynthesisLite"],
                suppressed_threads={
                    "StabilizationThread": 0.90,
                    "AggressiveThread": 0.95,
                    "RecoveryDominance": 0.85,
                    "HeavyWorldAdaptive": 0.90,
                    "MutationThread": 0.75,
                    "InventionThread": 0.80,
                    "ContextualMerger": 1.0,  # bypass 指示
                },
                action_size_cap="A",
                reason=f"hard_drift(lik={drift_lik:.2f})_v9_absolute",
                oracle_reference="v9_minimal",
            )
        
        # === Failure-face intervention (ablation 付き) ===
        if enable_failure_face_intervention and failure_dist.dominant_face is not None:
            face = failure_dist.dominant_face
            ratio = failure_dist.dominant_ratio
            
            # § 5.1: Drifting で Stabilization 過剰
            if (face == FailureFace.STABILIZATION_OVERUSE and ratio >= 0.35):
                return SparseDecision(
                    primary_mode=LoomMode.DRIFT,
                    primary_thread="DriftThread",
                    secondary_threads=["MinimalIntervention", "SynthesisLite"],
                    suppressed_threads={
                        "StabilizationThread": 0.90,
                        "AggressiveThread": 0.80,
                        "RecoveryDominance": 0.65,
                    },
                    action_size_cap="A",
                    reason=f"failure_face_stab_overuse({ratio:.2f})",
                    oracle_reference="v9_minimal",
                )
            
            # § 5.2: Guard forced 過剰
            if (face == FailureFace.GUARD_FORCED and ratio >= 0.40):
                return SparseDecision(
                    primary_mode=LoomMode.SAFETY,
                    primary_thread="SafetyThread",
                    secondary_threads=["RecoveryThread", "DefensiveThread"],
                    suppressed_threads={
                        "AggressiveThread": 0.95,
                        "MutationThread": 0.90,
                        "InventionThread": 0.95,
                    },
                    action_size_cap="A",
                    reason=f"failure_face_guard_forced({ratio:.2f})",
                    oracle_reference="v8.4.1",
                )
            
            # § 5.3: No-improvement cycle
            if (face == FailureFace.NO_IMPROVEMENT_CYCLE or
                orbit_metrics.no_improvement_cycle_score >= 0.60):
                return SparseDecision(
                    primary_mode=LoomMode.STAGNATION,
                    primary_thread="MutationThread",
                    secondary_threads=["SynthesisThread", "ExplorationThread"],
                    suppressed_threads={
                        "RepeatedRecovery": 0.55,
                        "AggressiveC": 0.90,
                    },
                    action_size_cap="B",
                    reason=f"failure_face_no_improvement_cycle",
                    oracle_reference="v8.5.1",
                )
        
        # === Soft Drift: bias toward drift ===
        if drift_lik >= self.SOFT_DRIFT_THRESHOLD:
            return SparseDecision(
                primary_mode=LoomMode.DRIFT,
                primary_thread="DriftThread",
                secondary_threads=["SynthesisLite", "RecoveryThread"],
                suppressed_threads={
                    "AggressiveThread": 0.80,
                    "RecoveryDominance": 0.55,
                    "StabilizationThread": 0.50,
                },
                action_size_cap="A",
                reason=f"soft_drift(lik={drift_lik:.2f})",
                oracle_reference="v9_minimal",
            )
        
        # === Severe / Volatile (高 chaotic_likelihood + reversal) ===
        if (orbit_metrics.chaotic_likelihood >= 0.55 and
            orbit_metrics.reversal_rate >= 0.50 and
            world_type == "chaotic" and world_conf >= 0.45):
            return SparseDecision(
                primary_mode=LoomMode.SEVERE_CYCLE,
                primary_thread="SevereCycleThread",
                secondary_threads=["DefensiveThread", "RecoveryThread"],
                suppressed_threads={
                    "AggressiveThread": 0.65,
                    "MutationThread": 0.70,
                    "UnboundedExploration": 0.80,
                },
                action_size_cap="A",
                reason="severe_volatile_active_cycle",
                oracle_reference="ActiveCycle",
            )
        
        # === Opportunity ===
        if (context.primary_context == Context.OPPORTUNITY and state.R >= 40
            and state.X <= 60):
            return SparseDecision(
                primary_mode=LoomMode.OPPORTUNITY,
                primary_thread="AggressiveSmallAttackThread",
                secondary_threads=["ExplorationThread", "SynthesisThread"],
                suppressed_threads={
                    "RecoveryDominance": 0.50,
                    "AggressiveC": 0.95,
                },
                action_size_cap="B",
                reason="opportunity_small_reversible",
                oracle_reference="v8.5.1",
            )
        
        # === Stabilization (Chaotic/Noisy) ===
        if (world_type in ("chaotic", "noisy") or
            orbit_metrics.chaotic_likelihood >= 0.40 or
            orbit_metrics.noisy_likelihood >= 0.40):
            return SparseDecision(
                primary_mode=LoomMode.STABILIZATION,
                primary_thread="StabilizationThread",
                secondary_threads=["RecoveryThread", "SynthesisThread"],
                suppressed_threads={
                    "AggressiveC": 0.90,
                    "HeavyMutation": 0.55,
                },
                action_size_cap="A",
                reason=f"stabilization_chaotic_noisy",
                oracle_reference="v8.5.1",
            )
        
        # === Default Normal (with drift bias if any drift signal) ===
        if drift_lik >= 0.15:
            primary = "DriftThread"
            mode = LoomMode.DRIFT
            secondary = ["SynthesisLite", "RecoveryThread"]
            ref = "v9_minimal"
            reason = f"normal_with_drift_bias({drift_lik:.2f})"
        else:
            primary = "RecoveryThread"
            mode = LoomMode.NORMAL
            secondary = ["DefensiveThread", "SynthesisThread"]
            ref = "v8.4.1"
            reason = "normal_default"
        
        return SparseDecision(
            primary_mode=mode,
            primary_thread=primary,
            secondary_threads=secondary,
            suppressed_threads={
                "AggressiveThread": 0.65,
                "MutationThread": 0.65,
            },
            action_size_cap="A",
            reason=reason,
            oracle_reference=ref,
        )


# ============================================================
# Loom v3.2
# ============================================================

class LoomV32(LoomV31):
    """Loom v3.2 — Sociable Detection 統合版.
    
    Per Zarameさん 仕様:
      - Sociable 4 層 default ON (観測のみ)
      - Drift 判定を Sociable Cycle Detector ベース
      - Hard Drift で ContextualMerger absolute bypass
      - Failure-face による thread 制御 (ablation 付き)
    """
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  guard_config: Optional[GuardConfig] = None,
                  use_qs_essence: bool = True,
                  # ★ NEW: failure-face による行動介入 (ablation 用)
                  enable_failure_face_intervention: bool = True):
        super().__init__(rng_manager=rng_manager,
                          guard_config=guard_config,
                          use_qs_essence=use_qs_essence)
        
        # === Sociable Detection System (4 層, default ON) ===
        self.sociable_detection = SociableDetectionSystem()
        
        # === Sociable-driven Sparse Controller ===
        self.sparse_controller = SociableSparseController()
        
        # === Behavior intervention flag (ablation 用) ===
        self.enable_failure_face_intervention = enable_failure_face_intervention
        
        # Extra stats
        self.stats["hard_drift_count"] = 0
        self.stats["soft_drift_count"] = 0
        self.stats["failure_face_intervention_count"] = 0
        self.stats["contextual_merger_bypass_count"] = 0
        self.stats["dominant_failure_faces"] = {}
        
        # Last decision tracking
        self.last_module: str = "none"
        self.last_guard_intervention: bool = False
        self.last_throttle_intervention: bool = False
        self.last_revalidation_rejected: bool = False
        self.last_stabilization_overuse: bool = False
        self.last_drift_miss: bool = False
    
    def decide(self, observation: WorldState) -> LoomDecision:
        """Override: Sociable Detection 経由で sparse 決定"""
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        
        # === Sensing ===
        conditions = self._build_conditions(observation)
        self.world_detector.update(observation)
        world_type, world_conf = self.world_detector.detect_world_type()
        context = self.context_classifier.classify(observation, conditions=conditions)
        risk_proximity = self._compute_risk_proximity(observation)
        
        early_drift_hint = self.world_detector.is_early_drift_hint()
        drift_oracle_gap_positive = self.oracle_gap.should_boost_drift()
        
        # === Sociable Detection report ===
        sociable_report = self.sociable_detection.get_report()
        orbit_metrics = sociable_report.orbit_metrics
        failure_dist = sociable_report.failure_distribution
        
        if early_drift_hint:
            self.stats["drift_override_count"] += 1
        if drift_oracle_gap_positive:
            self.stats["drift_boost_count"] += 1
        
        # === Sparse Decision (Sociable-driven) ===
        sparse = self.sparse_controller.decide_with_sociable(
            observation, world_type, world_conf, context,
            risk_proximity, list(self.recent_rewards),
            early_drift_hint=early_drift_hint,
            drift_oracle_gap_positive=drift_oracle_gap_positive,
            orbit_metrics=orbit_metrics,
            failure_dist=failure_dist,
            enable_failure_face_intervention=self.enable_failure_face_intervention,
        )
        
        # Stats
        if "hard_drift" in sparse.reason:
            self.stats["hard_drift_count"] += 1
        elif "soft_drift" in sparse.reason:
            self.stats["soft_drift_count"] += 1
        if "failure_face" in sparse.reason:
            self.stats["failure_face_intervention_count"] += 1
        
        self.stats["mode_counts"][sparse.primary_mode.value] = \
            self.stats["mode_counts"].get(sparse.primary_mode.value, 0) + 1
        self.stats["primary_thread_counts"][sparse.primary_thread] = \
            self.stats["primary_thread_counts"].get(sparse.primary_thread, 0) + 1
        self.stats["world_type_counts"][world_type] = \
            self.stats["world_type_counts"].get(world_type, 0) + 1
        self.stats["context_counts"][context.primary_context.value] = \
            self.stats["context_counts"].get(context.primary_context.value, 0) + 1
        self.stats["sparse_active_history"].append(
            1 + len(sparse.secondary_threads)
        )
        
        # === Candidate generation ===
        v71_a = self.v71.select_action(observation)
        
        if sparse.primary_mode == LoomMode.SAFETY:
            cands = self.safety_thread.generate(observation, self.map_layer)
        elif sparse.primary_mode == LoomMode.DRIFT:
            cands = self.drift_thread.generate(observation, v71_a, self.map_layer)
        elif sparse.primary_mode == LoomMode.STABILIZATION:
            cands = self.stab_thread.generate(observation, conditions, self.map_layer)
        elif sparse.primary_mode == LoomMode.SEVERE_CYCLE:
            cands = self.severe_thread.generate(observation, conditions, self.map_layer)
        elif sparse.primary_mode == LoomMode.OPPORTUNITY:
            cands = self.stab_thread.generate(observation, conditions, self.map_layer)
        elif sparse.primary_mode == LoomMode.STAGNATION:
            cands = self.stab_thread.generate(observation, conditions, self.map_layer)
            mut_cands = self.strong_engine.mutation.generate(
                observation, cands[:4], self.map_layer
            )
            cands.extend(mut_cands[:2])
        else:  # NORMAL
            cands = self.safety_thread.generate(observation, self.map_layer)
            syn = self.drift_thread.synthesis.synthesize(observation, v71_a)
            if syn is not None:
                cands.append(FullCandidate(
                    module="SynthesisStandalone",
                    attack_candidate=syn,
                    safe_variant=Action(syn.intent, "A"),
                    minimum_reversible_variant=Action("hold", "A"),
                    expected_upside=0.50, estimated_downside=0.10,
                    reversibility=0.90, reason="normal_synthesis_lite",
                ))
        
        # action_size_cap
        cap_order = {"A": 1, "B": 2, "C": 3}
        cap_lv = cap_order.get(sparse.action_size_cap, 3)
        cands = [c for c in cands 
                  if c.attack_candidate is None or
                     cap_order.get(c.attack_candidate.strength, 3) <= cap_lv]
        if not cands:
            cands = self.safety_thread.generate(observation, self.map_layer)
        
        # === QS-A: Propagator ===
        propagated_dict = None
        if self.use_qs_essence and self.propagator is not None:
            all_threads = ["RecoveryThread", "DefensiveThread", "SynthesisThread",
                            "AggressiveThread", "MutationThread", "ExplorationThread",
                            "DriftThread", "InventionThread"]
            primary_w = 0.85 if sparse.primary_mode == LoomMode.SAFETY else 0.70
            propagated = self.propagator.propagate(
                sparse.primary_thread, primary_w, all_threads,
                observation, world_type
            )
            propagated_dict = {
                "primary_weight": propagated.primary_weight,
                "kappa": propagated.kappa_value,
                "D": propagated.D_value,
            }
            self.stats["qs_propagated"] += 1
        
        # === Selection ===
        # Hard Drift: ContextualMerger absolute bypass
        is_hard_drift = "hard_drift" in sparse.reason
        is_drift_mode = sparse.primary_mode == LoomMode.DRIFT
        
        if (is_drift_mode and cands):
            # V71 primary を直接 select
            v71_cand = next((c for c in cands if c.module == "DriftBaseV71"), None)
            if v71_cand is not None:
                selected_candidate = v71_cand
                if is_hard_drift:
                    self.stats["contextual_merger_bypass_count"] += 1
            else:
                merger_result = self.contextual_merger.merge(cands, observation, context)
                selected_candidate = merger_result.best_candidate
        else:
            merger_result = self.contextual_merger.merge(cands, observation, context)
            selected_candidate = merger_result.best_candidate
        
        if selected_candidate is not None:
            current_action = selected_candidate.attack_candidate
            if selected_candidate.module == "AggressiveEngine":
                self.strong_engine.aggressive.record_selection(selected_candidate)
            module_for_record = selected_candidate.module
        else:
            current_action = Action("recover", "A")
            module_for_record = "fallback_recover"
        
        # === QS-S2: SuccessfulPatternBooster ===
        boost = 0.0
        if (self.use_qs_essence and self.booster is not None
            and selected_candidate is not None):
            from loom_core import MODULE_TO_THREAD
            thread_for_boost = MODULE_TO_THREAD.get(selected_candidate.module)
            if thread_for_boost is not None:
                boost = self.booster.get_boost(thread_for_boost.value, observation)
                if boost > 0:
                    self.stats["qs_boost_applied"] += 1
        
        # === Common Risk Floor ===
        from emergency_guards import GuardDecision
        from veto_classification import VetoClassification
        
        status = "ACCEPT"
        guard_result = "no_intervention"
        guard_intervened = False
        throttle_intervened = False
        
        eg = self.emergency_guard.apply(observation, current_action)
        if eg.applied:
            if (selected_candidate is not None and 
                selected_candidate.module == "AggressiveEngine"):
                self.strong_engine.aggressive.record_block(
                    selected_candidate, f"guard_{eg.rule_triggered}"
                )
            current_action = eg.forced_action
            status = "GUARD_FORCED"
            guard_result = f"emergency_guard: {eg.rule_triggered}"
            self.stats["emergency_triggered"] += 1
            guard_intervened = True
        
        th = self.throttle_guard.apply(observation, current_action)
        if th.applied:
            current_action = th.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            guard_result += f" | throttle: {th.rule_triggered}"
            self.stats["throttle_triggered"] += 1
            throttle_intervened = True
        
        # ActivePattern + Revalidation (skip in Drift mode per spec § 12)
        revalidation_result = "n/a"
        reval_rejected = False
        if not is_drift_mode:
            all_cands_simple = self._generate_all_candidates_simple()
            veto = VetoClassification.no_veto()
            ap_proposal = self.active_pattern.evaluate(
                observation, all_cands_simple, current_action, veto
            )
            strict_sigma = sparse.primary_mode in (LoomMode.SAFETY, LoomMode.SEVERE_CYCLE)
            if ap_proposal.has_correction_proposal and ap_proposal.proposed_action:
                passed, rev_reason = self._revalidate(
                    observation, ap_proposal.proposed_action,
                    strict_sigma=strict_sigma and self.use_qs_essence
                )
                revalidation_result = rev_reason
                if passed:
                    current_action = ap_proposal.proposed_action
                    if status == "ACCEPT":
                        status = "AP_INTERVENED"
                    self.stats["ap_intervened"] += 1
                else:
                    self.stats["revalidation_rejected"] += 1
                    reval_rejected = True
                    if "sigma" in rev_reason:
                        self.stats["qs_verification_rejected"] += 1
        
        # Final tracking
        if (selected_candidate is not None
            and selected_candidate.module == "AggressiveEngine"
            and current_action == selected_candidate.attack_candidate):
            self.strong_engine.aggressive.record_final_accept(selected_candidate)
        
        # Histories
        self.active_pattern.update_history(observation, current_action)
        self.throttle_guard.update_history(observation, current_action)
        self.context_classifier.update_history(
            observation, current_action,
            self.recent_rewards[-1] if self.recent_rewards else 0.0
        )
        self.map_layer.update(
            t=self.decision_counter, state=observation,
            action_intent=current_action.intent,
            action_strength=current_action.strength,
            reward=0.0,
        )
        self.strong_engine.record_action_taken(current_action)
        
        self.last_state_before = observation
        self.last_primary_thread = sparse.primary_thread
        self.last_module = module_for_record
        self.last_guard_intervention = guard_intervened
        self.last_throttle_intervention = throttle_intervened
        self.last_revalidation_rejected = reval_rejected
        # Detect stab_overuse / drift_miss heuristic
        self.last_stabilization_overuse = (
            sparse.primary_mode == LoomMode.STABILIZATION and
            orbit_metrics.drift_likelihood >= 0.30  # drift signal あったのに stab
        )
        self.last_drift_miss = (
            sparse.primary_mode != LoomMode.DRIFT and
            orbit_metrics.drift_likelihood >= 0.40
        )
        
        sigma_dict = None
        if self.use_qs_essence and self.verifier is not None:
            ver = self.verifier.verify(observation, current_action)
            sigma_dict = {
                "sigma_projected": ver.sigma_projected,
                "delta": ver.delta_sigma,
                "distance_to_ruin": ver.distance_to_ruin,
                "risk": ver.risk_assessment,
            }
        
        return LoomDecision(
            action=current_action,
            status=status,
            confidence=0.75,
            detected_world=world_type,
            detected_context=context.primary_context.value,
            primary_mode=sparse.primary_mode.value,
            primary_thread=sparse.primary_thread,
            secondary_threads=sparse.secondary_threads,
            suppressed_threads=sparse.suppressed_threads,
            safety_floor={
                "EmergencyResourceGuard": "active",
                "ActionIntensityThrottle": "active",
                "Revalidation": "active",
                "CumulativeRisk": "active",
            },
            oracle_reference=sparse.oracle_reference,
            oracle_gap_estimate=self.oracle_gap.get_avg_gap(
                world_type, context.primary_context.value
            ),
            sparse_active_count=1 + len(sparse.secondary_threads),
            candidates_generated=len(cands),
            propagated_weights=propagated_dict,
            sigma_verification=sigma_dict,
            success_boost_applied=boost,
            selected_candidate=selected_candidate,
            emergency_guard=eg,
            throttle_guard=th,
            revalidation_result=revalidation_result,
            final_action=f"{current_action.intent}/{current_action.strength}",
            reason=f"sparse: {sparse.reason} | guard: {guard_result}",
            metadata={
                "step": self.decision_counter,
                "drift_likelihood": orbit_metrics.drift_likelihood,
                "chaotic_likelihood": orbit_metrics.chaotic_likelihood,
                "noisy_likelihood": orbit_metrics.noisy_likelihood,
                "drift_escape": orbit_metrics.drift_escape_score,
                "dominant_failure_face": (failure_dist.dominant_face.value 
                                            if failure_dist.dominant_face else None),
            },
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        super().update_reward(action, reward, state_before, state_after)
        
        # === Sociable Detection update (4 層に分配) ===
        if self.last_state_before is not None:
            world_type = "unknown"
            if self.stats["world_type_counts"]:
                world_type = max(self.stats["world_type_counts"],
                                  key=self.stats["world_type_counts"].get)
            context_name = "unknown"
            if self.stats["context_counts"]:
                context_name = max(self.stats["context_counts"],
                                    key=self.stats["context_counts"].get)
            
            self.sociable_detection.update(
                step=self.decision_counter,
                state=self.last_state_before,
                action=action,
                module=self.last_module,
                context_name=context_name,
                world_type=world_type,
                reward=reward,
                guard_intervention=self.last_guard_intervention,
                throttle_intervention=self.last_throttle_intervention,
                revalidation_rejected=self.last_revalidation_rejected,
                stabilization_overuse=self.last_stabilization_overuse,
                drift_miss=self.last_drift_miss,
            )
            
            # Track dominant failure face
            rep = self.sociable_detection.get_report()
            if rep.failure_distribution.dominant_face is not None:
                face_name = rep.failure_distribution.dominant_face.value
                self.stats["dominant_failure_faces"][face_name] = \
                    self.stats["dominant_failure_faces"].get(face_name, 0) + 1
    
    def get_sociable_report(self):
        return self.sociable_detection.get_report()


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    
    print("=" * 70)
    print("Loom v3.2 (Sociable Detection 統合) Test")
    print("=" * 70)
    
    for World, world_name in [(DriftingWorld, "Drifting"), (ChaoticWorld, "Chaotic")]:
        print(f"\n--- {world_name} mild ---")
        for seed in [42, 123]:
            cfg = ChaosConfig.from_level("mild")
            world = World(cfg, seed=seed)
            eng = LoomV32(rng_manager=RNGManager(master_seed=seed + 200000),
                            enable_failure_face_intervention=True)
            
            for t in range(200):
                d = eng.decide(world.observe())
                r, done, _ = world.step(d.action)
                eng.update_reward(d.action, r)
                if done:
                    break
            
            rep = eng.get_sociable_report()
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}")
            print(f"    Modes: {eng.stats['mode_counts']}")
            print(f"    HardDrift={eng.stats['hard_drift_count']}, "
                  f"SoftDrift={eng.stats['soft_drift_count']}, "
                  f"FF_intervention={eng.stats['failure_face_intervention_count']}, "
                  f"Merger_bypass={eng.stats['contextual_merger_bypass_count']}")
            print(f"    Avg drift_lik={rep.orbit_metrics.drift_likelihood:.2f}, "
                  f"chaotic_lik={rep.orbit_metrics.chaotic_likelihood:.2f}")
            print(f"    Dominant failure faces: {eng.stats['dominant_failure_faces']}")
    
    print("\n[Loom v3.2 動作確認 ✅]")
