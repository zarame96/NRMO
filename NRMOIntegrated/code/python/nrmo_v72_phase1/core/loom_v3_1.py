"""
core/loom_v3_1.py

Loom v3.1 — 全強化累積版.

Per Zarameさん 指示: 「全て試してみろ」

統合内容:
  案 1: EnhancedWorldDetector (drift sensitive)
  案 2: Drift Override (早期 hint で Drift mode 固定)
  案 3: DriftThreadInternal を v9_minimal 寄りに強化
  案 4: Oracle Gap Feedback を active learning に
  案 5: 上記累積

Loom v3 を継承 + 主要 component を差し替え.
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
from context_classifier import Context, ContextClassification

from loom_v3 import (
    Loom, LoomDecision, LoomMode, SparseDecision,
    SparseActivationController,
    DriftThreadInternal, StabilizationThreadInternal,
    SevereCycleThreadInternal, SafetyThreadInternal,
    OracleGapFeedback,
)
from enhanced_world_detector import EnhancedWorldDetector
from v9_minimal_engine import SynthesisPathwayStandalone


# ============================================================
# 案 2: Drift-Override SparseActivationController
# ============================================================

class DriftOverrideController(SparseActivationController):
    """SparseActivationController + early drift hint override.
    
    Per spec 案 2: 早期 5 step で drifting hint があれば DRIFT mode 固定.
    """
    
    def decide(self, state, world_type, world_conf, context,
                 risk_proximity=0.0, recent_rewards=None,
                 early_drift_hint: bool = False,
                 drift_oracle_gap_positive: bool = False
                 ) -> SparseDecision:
        recent_rewards = recent_rewards or []
        
        # === 案 2: Early drift hint override ===
        # X 連続上昇 or R 連続減少 hint があれば、emergency 以外で Drift mode 強制
        if (early_drift_hint and 
            not (state.R <= 18 or state.X >= 85 or risk_proximity >= 0.70 or
                  context.primary_context == Context.EMERGENCY)):
            return SparseDecision(
                primary_mode=LoomMode.DRIFT,
                primary_thread="DriftThread",
                secondary_threads=["SynthesisLite", "MinimalIntervention"],
                suppressed_threads={
                    "AggressiveThread": 0.85,
                    "RecoveryDominance": 0.65,
                    "HeavyWorldAdaptive": 0.75,
                    "OverCalibration": 0.60,
                    "MutationThread": 0.65,
                    "InventionThread": 0.70,
                    "StabilizationCorrection": 0.50,
                },
                action_size_cap="A",
                reason="early_drift_hint_override_v9_like",
                oracle_reference="v9_minimal",
            )
        
        # === 案 4: Oracle gap positive (drifting gap detected) → boost ===
        # Recent 状況で drifting world と判明し gap 大きい → Drift mode 強制
        if (drift_oracle_gap_positive and 
            not (state.R <= 18 or state.X >= 85 or risk_proximity >= 0.70 or
                  context.primary_context == Context.EMERGENCY)):
            return SparseDecision(
                primary_mode=LoomMode.DRIFT,
                primary_thread="DriftThread",
                secondary_threads=["SynthesisLite", "MinimalIntervention"],
                suppressed_threads={
                    "AggressiveThread": 0.80,
                    "RecoveryDominance": 0.60,
                    "HeavyWorldAdaptive": 0.75,
                    "StabilizationCorrection": 0.55,
                },
                action_size_cap="A",
                reason="drift_oracle_gap_boost",
                oracle_reference="v9_minimal",
            )
        
        # それ以外は親 controller の logic に委ねる
        return super().decide(state, world_type, world_conf, context,
                                  risk_proximity, recent_rewards)


# ============================================================
# 案 3: Enhanced DriftThread (v9_minimal 寄り)
# ============================================================

class EnhancedDriftThread(DriftThreadInternal):
    """DriftThreadInternal を v9_minimal 寄りに強化.
    
    v9_minimal の正の挙動:
      1. V71 base + EmergencyGuard のみ
      2. SynthesisStandalone を 候補に
      3. recover を fallback (minimal intervention)
      4. ContextualMerger を bypass (heavy correction を避ける)
    """
    
    def generate(self, state: WorldState, v71_action: Action,
                   map_layer=None) -> List[FullCandidate]:
        """v9_minimal 風 minimal candidate set"""
        cands = []
        
        # ★ V71 action は最優先 candidate (v9_minimal の primary)
        cands.append(FullCandidate(
            module="DriftBaseV71",
            attack_candidate=v71_action,
            safe_variant=Action(v71_action.intent, "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.60,  # v9 寄りに boost
            estimated_downside=0.08,
            reversibility=0.92,
            reason="drift_v71_primary",
        ))
        
        # SynthesisStandalone (v9_minimal の synthesis-lite)
        syn = self.synthesis.synthesize(state, v71_action)
        if syn is not None:
            cands.append(FullCandidate(
                module="SynthesisStandalone",
                attack_candidate=syn,
                safe_variant=Action(syn.intent, "A"),
                minimum_reversible_variant=Action("hold", "A"),
                expected_upside=0.55,
                estimated_downside=0.10,
                reversibility=0.90,
                reason="drift_synthesis_lite",
            ))
        
        # Recovery は fallback のみ (low priority)
        cands.append(FullCandidate(
            module="RecoveryCandidate",
            attack_candidate=Action("recover", "A"),
            safe_variant=Action("recover", "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.30,  # 下げる (v9-like: dont over-recover)
            estimated_downside=0.05,
            reversibility=0.95,
            reason="drift_recovery_fallback",
        ))
        
        return cands


# ============================================================
# 案 4: Active Oracle Gap Feedback
# ============================================================

class ActiveOracleGapFeedback(OracleGapFeedback):
    """Oracle Gap Feedback + active mode switching.
    
    Per spec 案 4: gap が大きい時に自動で Drift mode boost.
    
    Mechanism:
      - 直近 N step の reward avg を track
      - 同 (world, context) で連続 K step 不振 → drift_boost フラグ ON
      - drift_boost ON → DriftOverrideController で Drift mode 固定
    """
    
    POOR_PERFORMANCE_THRESHOLD = 0.20   # avg reward これ以下
    POOR_STREAK_NEEDED = 3                # 連続不振 step 数
    
    def __init__(self):
        super().__init__()
        self.poor_performance_streak: int = 0
        self.drift_boost_active: bool = False
        self.recent_rewards_for_decision: deque = deque(maxlen=5)
    
    def update_step(self, reward: float, world_type: str):
        """毎 step で呼ばれる: reward に基づく drift boost 判定"""
        self.recent_rewards_for_decision.append(reward)
        
        # Poor performance streak
        if reward < self.POOR_PERFORMANCE_THRESHOLD:
            self.poor_performance_streak += 1
        else:
            self.poor_performance_streak = 0
        
        # 案 4: 連続不振 + drifting world ≥ moderate signal → drift boost
        if (self.poor_performance_streak >= self.POOR_STREAK_NEEDED and
            world_type in ("drifting", "unknown")):
            self.drift_boost_active = True
        else:
            self.drift_boost_active = False
    
    def should_boost_drift(self) -> bool:
        return self.drift_boost_active


# ============================================================
# Loom v3.1 (Enhanced)
# ============================================================

class LoomV31(Loom):
    """Loom v3.1 — 案 1-4 累積版.
    
    Components 差し替え:
      - WorldDetector → EnhancedWorldDetector
      - SparseController → DriftOverrideController
      - DriftThread → EnhancedDriftThread
      - OracleGap → ActiveOracleGapFeedback
    """
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  guard_config: Optional[GuardConfig] = None,
                  use_qs_essence: bool = True):
        super().__init__(rng_manager=rng_manager,
                          guard_config=guard_config,
                          use_qs_essence=use_qs_essence)
        
        # === 案 1: EnhancedWorldDetector ===
        self.world_detector = EnhancedWorldDetector()
        
        # === 案 2: DriftOverrideController ===
        self.sparse_controller = DriftOverrideController()
        
        # === 案 3: EnhancedDriftThread ===
        self.drift_thread = EnhancedDriftThread()
        
        # === 案 4: ActiveOracleGapFeedback ===
        self.oracle_gap = ActiveOracleGapFeedback()
        
        # Extra stats
        self.stats["drift_override_count"] = 0
        self.stats["drift_boost_count"] = 0
    
    def decide(self, observation: WorldState) -> LoomDecision:
        """Override decide to use enhanced components"""
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        
        # === Sensing (Enhanced) ===
        conditions = self._build_conditions(observation)
        self.world_detector.update(observation)
        world_type, world_conf = self.world_detector.detect_world_type()
        context = self.context_classifier.classify(observation, conditions=conditions)
        risk_proximity = self._compute_risk_proximity(observation)
        
        # === 案 2 + 4: Drift hints ===
        early_drift_hint = self.world_detector.is_early_drift_hint()
        drift_oracle_gap_positive = self.oracle_gap.should_boost_drift()
        
        if early_drift_hint:
            self.stats["drift_override_count"] += 1
        if drift_oracle_gap_positive:
            self.stats["drift_boost_count"] += 1
        
        # === Sparse Activation Decision (Enhanced) ===
        sparse = self.sparse_controller.decide(
            observation, world_type, world_conf, context, risk_proximity,
            list(self.recent_rewards),
            early_drift_hint=early_drift_hint,
            drift_oracle_gap_positive=drift_oracle_gap_positive,
        )
        
        # Stats
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
        
        # === Candidate generation by mode ===
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
        
        # action_size_cap enforcement
        cap_order = {"A": 1, "B": 2, "C": 3}
        cap_lv = cap_order.get(sparse.action_size_cap, 3)
        cands = [c for c in cands 
                  if c.attack_candidate is None or
                     cap_order.get(c.attack_candidate.strength, 3) <= cap_lv]
        if not cands:
            cands = self.safety_thread.generate(observation, self.map_layer)
        
        # === QS-A: ThreadConstraintPropagator ===
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
        # 案 3: Drift mode は ContextualMerger を bypass し、最優先候補 (V71) を直接選択
        if sparse.primary_mode == LoomMode.DRIFT and cands:
            # V71 primary を直接 select (v9_minimal 風)
            v71_cand = next((c for c in cands if c.module == "DriftBaseV71"), None)
            if v71_cand is not None:
                selected_candidate = v71_cand
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
        else:
            current_action = Action("recover", "A")
        
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
        
        # === Common Risk Floor (Safety Floor) ===
        from emergency_guards import GuardDecision
        from veto_classification import VetoClassification
        
        status = "ACCEPT"
        guard_result = "no_intervention"
        
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
        
        th = self.throttle_guard.apply(observation, current_action)
        if th.applied:
            current_action = th.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            guard_result += f" | throttle: {th.rule_triggered}"
            self.stats["throttle_triggered"] += 1
        
        # ActivePattern + Revalidation
        # ★ Drift mode では AP intervention を抑制 (over-calibration suppress)
        revalidation_result = "n/a"
        if sparse.primary_mode != LoomMode.DRIFT:
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
                    if "sigma" in rev_reason:
                        self.stats["qs_verification_rejected"] += 1
        
        # Final aggressive tracking
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
            metadata={"step": self.decision_counter,
                       "early_drift_hint": early_drift_hint,
                       "drift_boost": drift_oracle_gap_positive},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        # Super
        super().update_reward(action, reward, state_before, state_after)
        
        # 案 4: ActiveOracleGapFeedback update
        last_world = "unknown"
        if self.stats["world_type_counts"]:
            last_world = max(self.stats["world_type_counts"],
                              key=self.stats["world_type_counts"].get)
        self.oracle_gap.update_step(reward, last_world)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    from noisy_world import NoisyObservationWorld
    
    print("=" * 70)
    print("Loom v3.1 (Enhanced) Test")
    print("=" * 70)
    
    for World, world_name in [
        (DriftingWorld, "Drifting"),
        (ChaoticWorld, "Chaotic"),
        (NoisyObservationWorld, "Noisy"),
    ]:
        print(f"\n--- {world_name} mild ---")
        for seed in [42, 123, 999]:
            cfg = ChaosConfig.from_level("mild")
            world = World(cfg, seed=seed)
            eng = LoomV31(rng_manager=RNGManager(master_seed=seed + 200000))
            
            for t in range(200):
                d = eng.decide(world.observe())
                r, done, _ = world.step(d.action)
                eng.update_reward(d.action, r)
                if done:
                    break
            
            sparse = eng.get_sparse_summary()
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}")
            print(f"    Modes: {eng.stats['mode_counts']}")
            print(f"    Worlds: {eng.stats['world_type_counts']}")
            print(f"    drift_override: {eng.stats['drift_override_count']}, "
                  f"drift_boost: {eng.stats['drift_boost_count']}")
            print(f"    Sparse: mean={sparse.get('mean_active', 0):.2f} "
                  f"max={sparse.get('max_active', 0)}")
    
    print("\n[Loom v3.1 動作確認 ✅]")
