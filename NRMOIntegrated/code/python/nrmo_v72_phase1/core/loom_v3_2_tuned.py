"""
core/loom_v3_2_tuned.py

Loom v3.2.1 — v3.2 の真因 3 修正版.

修正項目:
  1. drift_likelihood threshold: HARD 0.55 → 0.30, SOFT 0.30 → 0.15
  2. SevereCycle 条件厳格化: world_type=='chaotic' 必須 + chaotic_likelihood >= 0.70
  3. FF intervention 優先順序: drift signal 弱い (drift_lik < 0.20) 時のみ発火
"""
from __future__ import annotations
import os, sys
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from rng_manager import RNGManager
from emergency_guards import GuardConfig
from context_classifier import Context

from loom_v3 import LoomMode, SparseDecision
from loom_v3_2 import LoomV32, SociableSparseController
from sociable_detection_layer import (
    OrbitMetrics, FailureFaceDistribution, FailureFace
)


# ============================================================
# Tuned controller
# ============================================================

class SociableSparseControllerTuned(SociableSparseController):
    """3 修正版.
    
    - Hard Drift 0.30 (元 0.55)
    - Soft Drift 0.15 (元 0.30)
    - SevereCycle は chaotic 確定時のみ
    - FF intervention は drift signal 弱い時のみ
    """
    
    HARD_DRIFT_THRESHOLD = 0.30
    SOFT_DRIFT_THRESHOLD = 0.15
    FF_DRIFT_OVERRIDE_THRESHOLD = 0.20  # drift_lik これ以上なら FF intervention 抑制
    
    def decide_with_sociable(self, state, world_type, world_conf, context,
                                  risk_proximity, recent_rewards,
                                  early_drift_hint: bool,
                                  drift_oracle_gap_positive: bool,
                                  orbit_metrics: OrbitMetrics,
                                  failure_dist: FailureFaceDistribution,
                                  enable_failure_face_intervention: bool = False
                                  ) -> SparseDecision:
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
        
        drift_lik = orbit_metrics.drift_likelihood
        chaotic_lik = orbit_metrics.chaotic_likelihood
        
        # === HARD DRIFT (lowered threshold 0.30) ===
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
                    "ContextualMerger": 1.0,  # bypass
                },
                action_size_cap="A",
                reason=f"hard_drift(lik={drift_lik:.2f})_v9_absolute",
                oracle_reference="v9_minimal",
            )
        
        # === FF intervention (修正 3): drift_lik 弱い時のみ ===
        if (enable_failure_face_intervention 
            and failure_dist.dominant_face is not None
            and drift_lik < self.FF_DRIFT_OVERRIDE_THRESHOLD):
            face = failure_dist.dominant_face
            ratio = failure_dist.dominant_ratio
            
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
            
            if (face == FailureFace.GUARD_FORCED and ratio >= 0.45):
                return SparseDecision(
                    primary_mode=LoomMode.SAFETY,
                    primary_thread="SafetyThread",
                    secondary_threads=["RecoveryThread", "DefensiveThread"],
                    suppressed_threads={
                        "AggressiveThread": 0.95,
                        "MutationThread": 0.90,
                    },
                    action_size_cap="A",
                    reason=f"failure_face_guard_forced({ratio:.2f})",
                    oracle_reference="v8.4.1",
                )
            
            # No improvement cycle (drift miss 等は無視)
            if orbit_metrics.no_improvement_cycle_score >= 0.65:
                return SparseDecision(
                    primary_mode=LoomMode.STAGNATION,
                    primary_thread="MutationThread",
                    secondary_threads=["SynthesisThread", "ExplorationThread"],
                    suppressed_threads={
                        "RepeatedRecovery": 0.55,
                        "AggressiveC": 0.90,
                    },
                    action_size_cap="B",
                    reason=f"no_improvement_cycle",
                    oracle_reference="v8.5.1",
                )
        
        # === SOFT DRIFT (lowered threshold 0.15) ===
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
        
        # === SEVERE CYCLE (修正 2: chaotic 確定時のみ, noisy 排除) ===
        if (world_type == "chaotic"
            and world_conf >= 0.50
            and chaotic_lik >= 0.70  # ← 厳格化 (元 0.55)
            and orbit_metrics.reversal_rate >= 0.55):
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
                reason=f"severe_volatile(chaotic_lik={chaotic_lik:.2f})",
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
        
        # === Stabilization (Chaotic/Noisy default) ===
        if (world_type in ("chaotic", "noisy") or
            chaotic_lik >= 0.40 or
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
                reason="stabilization_chaotic_noisy",
                oracle_reference="v8.5.1",
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


class LoomV32Tuned(LoomV32):
    """v3.2 修正版.
    
    Sparse Controller を Tuned 版に差し替え.
    他の機能 (4 層 Sociable Detection, QS essence, Safety Floor) は同じ.
    """
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  guard_config: Optional[GuardConfig] = None,
                  use_qs_essence: bool = True,
                  enable_failure_face_intervention: bool = True):
        super().__init__(rng_manager=rng_manager,
                          guard_config=guard_config,
                          use_qs_essence=use_qs_essence,
                          enable_failure_face_intervention=enable_failure_face_intervention)
        
        # Tuned controller に差し替え
        self.sparse_controller = SociableSparseControllerTuned()


if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    from noisy_world import NoisyObservationWorld
    
    print("=" * 70)
    print("Loom v3.2.1 (Tuned) Test")
    print("=" * 70)
    
    for World, world_name in [(DriftingWorld, "Drifting"),
                                  (ChaoticWorld, "Chaotic"),
                                  (NoisyObservationWorld, "Noisy")]:
        print(f"\n--- {world_name} mild ---")
        for seed in [42, 123]:
            cfg = ChaosConfig.from_level("mild")
            world = World(cfg, seed=seed)
            eng = LoomV32Tuned(rng_manager=RNGManager(master_seed=seed + 200000),
                                  enable_failure_face_intervention=True)
            for t in range(200):
                d = eng.decide(world.observe())
                r, done, _ = world.step(d.action)
                eng.update_reward(d.action, r)
                if done:
                    break
            
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}")
            print(f"    Modes: {eng.stats['mode_counts']}")
            print(f"    HardDrift={eng.stats['hard_drift_count']}, "
                  f"SoftDrift={eng.stats['soft_drift_count']}, "
                  f"FF_int={eng.stats['failure_face_intervention_count']}, "
                  f"Merger_bypass={eng.stats['contextual_merger_bypass_count']}")
    
    print("\n[Loom v3.2.1 動作確認 ✅]")
