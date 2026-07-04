"""
core/loom_v3.py

Loom (= LoomEngine v3).

Per Zarameさん 設計指示書:
  Specialist を外部 engine として扱うのではなく、Loom 内部の
  Specialist Thread として吸収し、必要な時だけ疎に発火する.

Architecture:
  Loom
    ├─ NRMO Core (ruin boundary, true veto)
    ├─ v8.4.1 Safety Floor (EG + Throttle + CumRisk + Revalidation)
    ├─ Loom Core (World/Context classifier, Sparse activation, Oracle gap)
    ├─ Specialist Threads (Drift / Stab / Severe / Safety internal)
    ├─ Base Threads (Recovery / Defensive / Synthesis / Aggr-small / Exploration)
    ├─ QS essence (Propagator + Verifier + Booster)
    └─ Decision Trace Logger

中核原則 (再掲):
  All threads available. Few threads active. (max 3)
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import deque
from enum import Enum
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
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
from context_classifier import Context, ContextClassifier, ContextClassification
from contextual_candidate_merger import ContextualCandidateMerger
from meta_engine import WorldTypeDetector
from v9_minimal_engine import SynthesisPathwayStandalone

# QS essence
from sociable_essence_v2 import (
    ThreadConstraintPropagator, PropagatedWeights,
    EqualSigmaVerifier, SigmaVerification,
    SuccessfulPatternBooster,
)


# ============================================================
# Specialist Mode enum
# ============================================================

class LoomMode(Enum):
    SAFETY = "Safety"            # v8.4.1 風: Emergency / R critical
    DRIFT = "Drift"               # v9_minimal 風: drifting world
    STABILIZATION = "Stabilization"  # v8.5.1 風: chaotic/noisy mild-moderate
    SEVERE_CYCLE = "SevereCycle"  # ActiveCycle 風: chaotic/severe
    OPPORTUNITY = "Opportunity"   # opportunity context
    STAGNATION = "Stagnation"    # stagnation context
    NORMAL = "Normal"             # default


# ============================================================
# SparseActivationController
# ============================================================

@dataclass
class SparseDecision:
    """Sparse activation 決定"""
    primary_mode: LoomMode
    primary_thread: str
    secondary_threads: List[str]
    suppressed_threads: Dict[str, float]
    action_size_cap: str  # "A", "B", "C"
    reason: str = ""
    
    # Oracle reference
    oracle_reference: str = ""


class SparseActivationController:
    """Per spec § 6 Sparse Activation Rule:
    max_active_threads = 3
    primary <= 1, secondary <= 2.
    """
    
    MAX_ACTIVE = 3
    MAX_SECONDARY = 2
    
    def decide(self, state: WorldState,
                 world_type: str, world_conf: float,
                 context: ContextClassification,
                 risk_proximity: float = 0.0,
                 recent_rewards: List[float] = None
                 ) -> SparseDecision:
        """Per spec § 5 Context-to-Thread 発火ルール"""
        ctx = context.primary_context
        recent_rewards = recent_rewards or []
        
        # === 5.1 Emergency (R critical / X critical / proximity high) ===
        if (state.R <= 18 or state.X >= 85 or risk_proximity >= 0.70
            or ctx == Context.EMERGENCY):
            return SparseDecision(
                primary_mode=LoomMode.SAFETY,
                primary_thread="SafetyThread",
                secondary_threads=["RecoveryThread", "DefensiveThread"],
                suppressed_threads={
                    "AggressiveThread": 1.0,
                    "MutationThread": 1.0,
                    "InventionThread": 1.0,
                    "ExplorationThread": 0.70,
                    "DriftScaling": 0.80,
                },
                action_size_cap="A",
                reason="emergency_survival_first",
                oracle_reference="v8.4.1",
            )
        
        # === 5.2 Drifting (per spec: Behave like v9_minimal) ===
        # Drift detection: world_type=drifting と confidence + persistent X 上昇
        is_drift = (world_type == "drifting" and world_conf >= 0.45)
        if is_drift and not ctx == Context.EMERGENCY:
            return SparseDecision(
                primary_mode=LoomMode.DRIFT,
                primary_thread="DriftThread",
                secondary_threads=["SynthesisLite", "MinimalIntervention"],
                suppressed_threads={
                    "AggressiveThread": 0.80,
                    "RecoveryDominance": 0.60,
                    "HeavyWorldAdaptive": 0.70,
                    "OverCalibration": 0.60,
                    "MutationThread": 0.65,
                    "InventionThread": 0.70,
                },
                action_size_cap="A",
                reason="drift_detected_v9_like",
                oracle_reference="v9_minimal",
            )
        
        # === 5.4 Severe / Volatile (per spec: Behave like ActiveCycle) ===
        # Severe: high variance recent rewards + chaotic
        if (recent_rewards and len(recent_rewards) >= 5):
            recent_std = float(np.std(recent_rewards[-5:]))
        else:
            recent_std = 0.0
        is_severe = (recent_std > 0.5 and world_type == "chaotic"
                       and world_conf >= 0.45)
        if is_severe:
            return SparseDecision(
                primary_mode=LoomMode.SEVERE_CYCLE,
                primary_thread="SevereCycleThread",
                secondary_threads=["DefensiveThread", "RecoveryThread"],
                suppressed_threads={
                    "AggressiveThread": 0.65,
                    "MutationThread": 0.70,
                    "InventionThread": 0.75,
                    "UnboundedExploration": 0.80,
                },
                action_size_cap="A",
                reason="severe_volatile_active_cycle_like",
                oracle_reference="ActiveCycle",
            )
        
        # === 5.5 Opportunity ===
        if (ctx == Context.OPPORTUNITY and state.R >= 40
            and state.X <= 60 and recent_std <= 0.3):
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
        
        # === 5.6 Stagnation ===
        if (ctx == Context.STAGNATION and recent_rewards
            and len(recent_rewards) >= 5):
            recent_mean = float(np.mean(recent_rewards[-5:]))
            if recent_mean < 0.15:
                return SparseDecision(
                    primary_mode=LoomMode.STAGNATION,
                    primary_thread="MutationThread",
                    secondary_threads=["SynthesisThread", "ExplorationThread"],
                    suppressed_threads={
                        "RepeatedRecovery": 0.55,
                    },
                    action_size_cap="B",
                    reason="stagnation_disruption",
                    oracle_reference="v8.5.1",
                )
        
        # === 5.3 Chaotic / Noisy (per spec: Behave like v8.5.1) ===
        if world_type in ("chaotic", "noisy"):
            return SparseDecision(
                primary_mode=LoomMode.STABILIZATION,
                primary_thread="StabilizationThread",
                secondary_threads=["RecoveryThread", "SynthesisThread"],
                suppressed_threads={
                    "AggressiveC": 0.90,
                    "HeavyMutation": 0.55,
                    "ExcessiveDrift": 0.60,
                },
                action_size_cap="A",
                reason=f"{world_type}_stabilization_v851_like",
                oracle_reference="v8.5.1" if world_conf >= 0.3 else "recover_fixed",
            )
        
        # === Default Normal ===
        return SparseDecision(
            primary_mode=LoomMode.NORMAL,
            primary_thread="RecoveryThread",
            secondary_threads=["DefensiveThread", "SynthesisThread"],
            suppressed_threads={
                "AggressiveThread": 0.65,
                "MutationThread": 0.65,
            },
            action_size_cap="A",
            reason="normal_default",
            oracle_reference="v8.4.1",
        )


# ============================================================
# Specialist Threads (Internal Logic)
# ============================================================

class DriftThreadInternal:
    """v9_minimal の挙動を内部 thread として実装.
    
    minimal intervention + synthesis-lite + V71 trend follow.
    """
    
    def __init__(self):
        self.synthesis = SynthesisPathwayStandalone()
    
    def generate(self, state: WorldState, v71_action: Action,
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        """Drift Thread: V71 base + SynthesisStandalone (minimal)"""
        cands = []
        
        # V71 base (minimal intervention)
        cands.append(FullCandidate(
            module="DriftBaseV71",
            attack_candidate=v71_action,
            safe_variant=Action(v71_action.intent, "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.45,
            estimated_downside=0.08,
            reversibility=0.92,
            reason="drift_v71_minimal_intervention",
        ))
        
        # Synthesis Standalone (v9-like synthesis-lite)
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
        
        # Recovery weakly (fallback safety)
        cands.append(FullCandidate(
            module="RecoveryCandidate",
            attack_candidate=Action("recover", "A"),
            safe_variant=Action("recover", "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.40,
            estimated_downside=0.05,
            reversibility=0.95,
            reason="drift_recovery_weak",
        ))
        
        return cands


class StabilizationThreadInternal:
    """v8.5.1 の挙動を内部 thread として実装.
    
    StrongEngineΩfull + ContextualMerger (Recovery + Defensive + Synthesis).
    """
    
    def __init__(self, strong_engine: StrongEngineOmegaFull):
        self.strong_engine = strong_engine
    
    def generate(self, state: WorldState, conditions: Dict,
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        """Stabilization Thread: 8 module diversity (v8.5.1 like)"""
        # Defensive + Recovery + Synthesis 中心
        all_cands = []
        all_cands.extend(self.strong_engine.defensive.generate(state, map_layer))
        all_cands.extend(self.strong_engine.recovery.generate(state, map_layer))
        all_cands.extend(self.strong_engine.exploration.generate(state, map_layer))
        all_cands.extend(self.strong_engine.synthesis.generate(state, all_cands[:6], map_layer))
        # Mutation 抑制 (heavy_mutation suppression)
        # Aggressive small only (no C)
        agg_cands = self.strong_engine.aggressive.generate(state, conditions, map_layer)
        agg_filtered = [c for c in agg_cands 
                         if c.attack_candidate and c.attack_candidate.strength != "C"]
        all_cands.extend(agg_filtered)
        return all_cands


class SevereCycleThreadInternal:
    """ActiveCycle の挙動を内部 thread として実装.
    
    Active bias + Cyclic feedback + Opportunity bounded.
    """
    
    def __init__(self, strong_engine: StrongEngineOmegaFull):
        self.strong_engine = strong_engine
        self.last_successful_active: Optional[Action] = None
    
    def generate(self, state: WorldState, conditions: Dict,
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        """Severe Cycle Thread: Active bias + defensive backup"""
        all_cands = []
        all_cands.extend(self.strong_engine.defensive.generate(state, map_layer))
        all_cands.extend(self.strong_engine.recovery.generate(state, map_layer))
        # Synthesis-lite
        syn_cands = self.strong_engine.synthesis.generate(state, all_cands[:4], map_layer)
        all_cands.extend(syn_cands[:2])  # lite = 2 候補のみ
        # Aggressive bounded (no escalation)
        agg_cands = self.strong_engine.aggressive.generate(state, conditions, map_layer)
        agg_bounded = [c for c in agg_cands 
                        if c.attack_candidate and c.attack_candidate.strength == "A"]
        all_cands.extend(agg_bounded[:2])  # max 2 aggressive
        
        # Cyclic feedback: last successful active を boost
        if self.last_successful_active is not None:
            all_cands.append(FullCandidate(
                module="SevereCycleRepeat",
                attack_candidate=self.last_successful_active,
                safe_variant=Action(self.last_successful_active.intent, "A"),
                minimum_reversible_variant=Action("hold", "A"),
                expected_upside=0.50,
                estimated_downside=0.12,
                reversibility=0.85,
                reason="cyclic_feedback_repeat",
            ))
        
        return all_cands
    
    def record_success(self, action: Action, reward: float):
        if reward > 0.35 and action.intent in ("invest", "explore", "defend"):
            self.last_successful_active = action


class SafetyThreadInternal:
    """v8.4.1 の挙動を内部 thread として実装.
    
    Survival first: Recovery + Defensive only.
    """
    
    def generate(self, state: WorldState,
                   map_layer: Optional[MAPLayer] = None) -> List[FullCandidate]:
        """Safety Thread: recover/A only with defensive backup"""
        return [
            FullCandidate(
                module="RecoveryCandidate",
                attack_candidate=Action("recover", "A"),
                safe_variant=Action("recover", "A"),
                minimum_reversible_variant=Action("hold", "A"),
                expected_upside=0.50,
                estimated_downside=0.03,
                reversibility=0.98,
                reason="safety_recover_only",
            ),
            FullCandidate(
                module="DefensiveCandidate",
                attack_candidate=Action("defend", "A"),
                safe_variant=Action("defend", "A"),
                minimum_reversible_variant=Action("hold", "A"),
                expected_upside=0.35,
                estimated_downside=0.05,
                reversibility=0.95,
                reason="safety_defend_backup",
            ),
        ]


# ============================================================
# OracleGapFeedback
# ============================================================

class OracleGapFeedback:
    """Per spec § 7 Oracle Gap Feedback.
    
    world × context 別の reference specialist との比較で
    Loom の挙動を adjust.
    """
    
    def __init__(self):
        # (world_type, context) -> recent_oracle_gap_estimate
        self.gap_estimates: Dict[Tuple[str, str], deque] = {}
        # Per-mode adjustment recommendations
        self.adjustments: Dict[str, float] = {}
    
    def update(self, world_type: str, context: str,
                 reference_engine: str, current_score: float,
                 reference_estimate: float):
        """gap = reference - current"""
        gap = reference_estimate - current_score
        key = (world_type, context)
        if key not in self.gap_estimates:
            self.gap_estimates[key] = deque(maxlen=20)
        self.gap_estimates[key].append(gap)
    
    def get_avg_gap(self, world_type: str, context: str) -> float:
        key = (world_type, context)
        if key not in self.gap_estimates or not self.gap_estimates[key]:
            return 0.0
        return float(np.mean(list(self.gap_estimates[key])))
    
    def get_summary(self) -> Dict:
        return {
            "tracked_cells": len(self.gap_estimates),
            "avg_gaps": {
                f"{w}/{c}": float(np.mean(list(d)))
                for (w, c), d in self.gap_estimates.items() if d
            },
        }


# ============================================================
# Loom Decision
# ============================================================

@dataclass
class LoomDecision:
    """Per spec § 12 Decision Trace Requirement"""
    action: Action
    status: str
    confidence: float
    
    detected_world: str
    detected_context: str
    primary_mode: str
    primary_thread: str
    secondary_threads: List[str]
    suppressed_threads: Dict[str, float]
    safety_floor: Dict[str, str]
    oracle_reference: str
    oracle_gap_estimate: Optional[float]
    
    sparse_active_count: int  # active thread 数 (must be ≤ 3)
    candidates_generated: int
    
    # QS essence
    propagated_weights: Optional[Dict] = None
    sigma_verification: Optional[Dict] = None
    success_boost_applied: float = 0.0
    
    # Internal
    selected_candidate: Optional[FullCandidate] = None
    emergency_guard: Optional[GuardDecision] = None
    throttle_guard: Optional[GuardDecision] = None
    revalidation_result: str = "n/a"
    
    final_action: str = ""
    reason: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def to_trace(self) -> Dict:
        return {
            "detected_world": self.detected_world,
            "detected_context": self.detected_context,
            "primary_mode": self.primary_mode,
            "primary_thread": self.primary_thread,
            "secondary_threads": self.secondary_threads,
            "suppressed_threads": self.suppressed_threads,
            "safety_floor": self.safety_floor,
            "oracle_reference": self.oracle_reference,
            "oracle_gap_estimate": self.oracle_gap_estimate,
            "sparse_active_count": self.sparse_active_count,
            "final_action": self.final_action,
            "reason": self.reason,
        }


# ============================================================
# Loom (LoomEngine v3) main
# ============================================================

class Loom:
    """Loom = LoomEngine v3.
    
    Specialist 内部吸収版:
      v8.4.1 → SafetyThread (Safety Floor)
      v9_minimal → DriftThread
      v8.5.1 → StabilizationThread
      ActiveCycle → SevereCycleThread
    
    Sparse activation (max 3) + Oracle gap feedback + QS essence.
    """
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  guard_config: Optional[GuardConfig] = None,
                  use_qs_essence: bool = True):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        # === NRMO Core: Safety Floor (v8.4.1) ===
        self.guard_config = guard_config or GuardConfig()
        self.emergency_guard = EmergencyResourceGuard(self.guard_config)
        self.throttle_guard = ActionIntensityThrottle(self.guard_config)
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        self.active_pattern = ActivePatternProxy()
        self.active_pattern.INTERVENTION_THRESHOLD = 0.35
        
        # === Loom Core ===
        self.world_detector = WorldTypeDetector(history_size=15)
        self.context_classifier = ContextClassifier()
        self.sparse_controller = SparseActivationController()
        self.oracle_gap = OracleGapFeedback()
        
        # === StrongEngine (base candidate pool) ===
        se_rng = self.rng_manager.spawn("strong_engine")
        self.strong_engine = StrongEngineOmegaFull(rng=se_rng)
        
        # === Specialist Threads (Internal) ===
        self.drift_thread = DriftThreadInternal()
        self.stab_thread = StabilizationThreadInternal(self.strong_engine)
        self.severe_thread = SevereCycleThreadInternal(self.strong_engine)
        self.safety_thread = SafetyThreadInternal()
        
        # === V71 (base for drift) ===
        self.v71 = V71Engine(rng=self.rng_manager.spawn("v71"))
        
        # === ContextualMerger (selection) ===
        self.contextual_merger = ContextualCandidateMerger()
        
        # === MAPLayer ===
        self.map_layer = MAPLayer()
        
        # === QS essence ===
        self.use_qs_essence = use_qs_essence
        self.propagator = ThreadConstraintPropagator() if use_qs_essence else None
        self.verifier = EqualSigmaVerifier() if use_qs_essence else None
        self.booster = SuccessfulPatternBooster() if use_qs_essence else None
        
        # === Memory ===
        self.recent_rewards: deque = deque(maxlen=10)
        self.last_state_before: Optional[WorldState] = None
        self.last_primary_thread: Optional[str] = None
        
        # === Stats ===
        self.decision_counter = 0
        self.stats = {
            "total_decisions": 0,
            "mode_counts": {m.value: 0 for m in LoomMode},
            "primary_thread_counts": {},
            "world_type_counts": {},
            "context_counts": {},
            "sparse_active_history": [],
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "qs_propagated": 0,
            "qs_verification_rejected": 0,
            "qs_boost_applied": 0,
        }
    
    # ============================================================
    # Helpers
    # ============================================================
    
    def _build_conditions(self, state: WorldState) -> Dict:
        conditions = {}
        if self.map_layer.l2:
            trends = self.map_layer.get_state_trends()
            if trends:
                o_vol = abs(trends.get("O", 0))
                conditions["O_confidence"] = max(0.3, 1.0 - o_vol / 3.0)
            else:
                conditions["O_confidence"] = 0.7
        else:
            conditions["O_confidence"] = 0.7
        
        if len(self.recent_rewards) >= 3:
            conditions["recent_drawdown"] = sum(list(self.recent_rewards)[-3:]) < -0.5
        else:
            conditions["recent_drawdown"] = False
        conditions["true_veto"] = False
        
        if self.map_layer.l2:
            near_ruin = self.map_layer.near_ruin_count()
            conditions["observation_noise"] = (0.05 if near_ruin == 0 else
                                                 0.15 if near_ruin < 5 else 0.30)
        else:
            conditions["observation_noise"] = 0.05
        return conditions
    
    def _compute_risk_proximity(self, state: WorldState) -> float:
        r_part = max(0, (25 - state.R) / 25.0) * 0.5
        x_part = max(0, (state.X - 70) / 30.0) * 0.5
        return min(1.0, r_part + x_part)
    
    def _estimate_action_delta(self, action: Action) -> Dict:
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
    
    def _revalidate(self, state: WorldState, proposed: Action,
                      strict_sigma: bool = False) -> Tuple[bool, str]:
        """Revalidation Gate + (optional) Equal-Sigma strict check"""
        # EG check
        eg = self.emergency_guard.apply(state, proposed)
        if eg.applied:
            return False, f"revalidation_eg_failed: {eg.rule_triggered}"
        # Cumulative risk
        proj = self._estimate_action_delta(proposed)
        breached, _ = self.cumulative_risk.projected_breach_after(proj)
        if breached:
            return False, "revalidation_cumulative_breach"
        # Optional: Equal-Sigma strict
        if strict_sigma and self.verifier is not None:
            ver = self.verifier.verify(state, proposed, proj)
            if not ver.passed:
                return False, f"revalidation_sigma_failed: {ver.reason}"
        return True, "passed"
    
    def _generate_all_candidates_simple(self):
        return [Action(intent=i, strength=s)
                 for i in ["invest", "defend", "explore", "recover", "hold"]
                 for s in ["A", "B", "C"]]
    
    # ============================================================
    # Main decide
    # ============================================================
    
    def decide(self, observation: WorldState) -> LoomDecision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        
        # === Sensing ===
        conditions = self._build_conditions(observation)
        self.world_detector.update(observation)
        world_type, world_conf = self.world_detector.detect_world_type()
        context = self.context_classifier.classify(observation, conditions=conditions)
        risk_proximity = self._compute_risk_proximity(observation)
        
        # === Sparse Activation Decision ===
        sparse = self.sparse_controller.decide(
            observation, world_type, world_conf, context, risk_proximity,
            list(self.recent_rewards)
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
        
        # === Generate candidates from primary thread ===
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
            # Use stab_thread + small aggressive
            cands = self.stab_thread.generate(observation, conditions, self.map_layer)
        elif sparse.primary_mode == LoomMode.STAGNATION:
            cands = self.stab_thread.generate(observation, conditions, self.map_layer)
            # Add mutation
            mut_cands = self.strong_engine.mutation.generate(
                observation, cands[:4], self.map_layer
            )
            cands.extend(mut_cands[:2])
        else:  # NORMAL
            # Fallback: safety + minimal
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
        
        # === action_size_cap enforcement ===
        cap_order = {"A": 1, "B": 2, "C": 3}
        cap_lv = cap_order.get(sparse.action_size_cap, 3)
        cands = [c for c in cands 
                  if c.attack_candidate is None or
                     cap_order.get(c.attack_candidate.strength, 3) <= cap_lv]
        
        if not cands:
            # safety fallback
            cands = self.safety_thread.generate(observation, self.map_layer)
        
        # === QS-A: ThreadConstraintPropagator (kappa-divisor cascade) ===
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
                "total_used": propagated.total_budget_used,
            }
            self.stats["qs_propagated"] += 1
        
        # === Selection: ContextualMerger ===
        merger_result = self.contextual_merger.merge(cands, observation, context)
        selected_candidate = merger_result.best_candidate
        
        if selected_candidate is not None:
            current_action = selected_candidate.attack_candidate
            if selected_candidate.module == "AggressiveEngine":
                self.strong_engine.aggressive.record_selection(selected_candidate)
        else:
            current_action = Action("recover", "A")
        
        # === QS-S2: SuccessfulPatternBooster (apply boost) ===
        boost = 0.0
        if (self.use_qs_essence and self.booster is not None
            and selected_candidate is not None):
            # Get boost for primary thread × state
            from loom_core import MODULE_TO_THREAD
            thread_for_boost = MODULE_TO_THREAD.get(selected_candidate.module)
            if thread_for_boost is not None:
                boost = self.booster.get_boost(thread_for_boost.value, observation)
                if boost > 0:
                    self.stats["qs_boost_applied"] += 1
        
        # === Common Risk Floor (Invariants — v8.4.1 Safety Floor) ===
        status = "ACCEPT"
        guard_result = "no_intervention"
        
        # Invariant 2: EmergencyResourceGuard
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
        
        # Invariant 3: ActionIntensityThrottle
        th = self.throttle_guard.apply(observation, current_action)
        if th.applied:
            current_action = th.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            guard_result += f" | throttle: {th.rule_triggered}"
            self.stats["throttle_triggered"] += 1
        
        # ActivePattern + Revalidation Gate (Invariant 6)
        revalidation_result = "n/a"
        all_cands_simple = self._generate_all_candidates_simple()
        veto = VetoClassification.no_veto()
        ap_proposal = self.active_pattern.evaluate(
            observation, all_cands_simple, current_action, veto
        )
        # QS-S1: EqualSigmaVerifier (revalidation 強化)
        strict_sigma = (sparse.primary_mode in (LoomMode.SAFETY, LoomMode.SEVERE_CYCLE))
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
        
        # === Final aggressive accept tracking ===
        if (selected_candidate is not None
            and selected_candidate.module == "AggressiveEngine"
            and current_action == selected_candidate.attack_candidate):
            self.strong_engine.aggressive.record_final_accept(selected_candidate)
        
        # === Histories ===
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
        
        # Remember for update_reward
        self.last_state_before = observation
        self.last_primary_thread = sparse.primary_thread
        
        # Sigma verification (informational)
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
            metadata={"step": self.decision_counter},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        self.v71.update_reward(action, reward)
        self.recent_rewards.append(float(reward))
        
        # Severe Cycle Thread: track success for cyclic feedback
        if self.last_primary_thread == "SevereCycleThread":
            self.severe_thread.record_success(action, reward)
        
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)
        
        if self.map_layer.l1:
            self.map_layer.l1[-1].reward = float(reward)
        
        # QS-S2: SuccessfulPatternBooster (record success)
        if (self.use_qs_essence and self.booster is not None
            and reward > 0.5
            and self.last_state_before is not None
            and self.last_primary_thread is not None):
            self.booster.record_success(
                self.last_primary_thread,
                self.last_state_before,
                reward, self.decision_counter
            )
    
    def get_aggressive_counters(self) -> Dict:
        return dict(self.strong_engine.aggressive.counters)
    
    def get_sparse_summary(self) -> Dict:
        if not self.stats["sparse_active_history"]:
            return {}
        h = self.stats["sparse_active_history"]
        return {
            "mean_active": float(np.mean(h)),
            "median_active": float(np.median(h)),
            "max_active": int(max(h)),
            "min_active": int(min(h)),
        }


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    from noisy_world import NoisyObservationWorld
    
    print("=" * 70)
    print("Loom (LoomEngine v3) Test")
    print("=" * 70)
    
    for World, world_name in [
        (ChaoticWorld, "Chaotic"),
        (DriftingWorld, "Drifting"),
        (NoisyObservationWorld, "Noisy"),
    ]:
        print(f"\n--- {world_name} severe ---")
        for seed in [42, 123]:
            cfg = ChaosConfig.from_level("severe")
            world = World(cfg, seed=seed)
            eng = Loom(rng_manager=RNGManager(master_seed=seed + 200000))
            
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
            print(f"    Worlds detected: {eng.stats['world_type_counts']}")
            print(f"    Sparse: mean={sparse.get('mean_active', 0):.2f} "
                  f"max={sparse.get('max_active', 0)}")
            print(f"    Emergency: {eng.stats['emergency_triggered']}, "
                  f"Throttle: {eng.stats['throttle_triggered']}, "
                  f"AP: {eng.stats['ap_intervened']}")
            print(f"    QS: prop={eng.stats['qs_propagated']}, "
                  f"sigma_rej={eng.stats['qs_verification_rejected']}, "
                  f"boost={eng.stats['qs_boost_applied']}")
    
    print("\n[Loom 動作確認 ✅]")
