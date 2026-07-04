"""
core/loom_v3_1_shadow.py

Loom v3.1 + Sociable Shadow Layer.

Per Zarameさん 最終判断 (案 B):
  行動主体:   Loom v3.1 (凍結)
  観測主体:   Sociable Detection 4 層
  行動介入:   OFF (default)
  学習・分析: ON

理論更新:
  Detection ≠ Intervention
  
  観測・検出・正規化は常時 ON.
  行動介入は hysteresis / dwell time / confidence / ablation 必要.

このファイル:
  Loom v3.1 の挙動を完全保存 + Sociable Detection 4 層を Shadow Layer
  として常時 record する.
  Sociable detection は score / action に影響を与えない (観測のみ).
"""
from __future__ import annotations
import os, sys
from typing import Dict, Optional
from collections import deque

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from rng_manager import RNGManager
from emergency_guards import GuardConfig

from loom_v3 import LoomDecision
from loom_v3_1 import LoomV31
from sociable_detection_layer import (
    SociableDetectionSystem, SociableDetectionReport,
)


class LoomV31Shadow(LoomV31):
    """Loom v3.1 + Sociable Shadow Detection Layer.
    
    Per Zarameさん 案 B:
      行動 = v3.1 と完全に同じ
      観測 = Sociable 4 層を常時 record (shadow)
      介入 = なし
    
    Shadow Detection の役割:
      - state/action/module の trace
      - canonical state/failure/orbit ID
      - cycle/orbit metrics (drift_lik, chaotic_lik 等)
      - failure-face distribution
      - score 影響なし (観測のみ)
    """
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  guard_config: Optional[GuardConfig] = None,
                  use_qs_essence: bool = True):
        super().__init__(rng_manager=rng_manager,
                          guard_config=guard_config,
                          use_qs_essence=use_qs_essence)
        
        # === Sociable Shadow Layer (常時 ON, 観測のみ) ===
        self.sociable_shadow = SociableDetectionSystem()
        
        # Last decision tracking (for shadow record)
        self.last_module: str = "none"
        self.last_guard_intervention: bool = False
        self.last_throttle_intervention: bool = False
        self.last_revalidation_rejected: bool = False
        self.last_primary_mode: str = "Normal"
        
        # Shadow-only stats (no influence on behavior)
        self.shadow_stats = {
            "total_shadow_records": 0,
            "shadow_dominant_faces": {},
            "shadow_drift_lik_history": [],
            "shadow_chaotic_lik_history": [],
            "shadow_noisy_lik_history": [],
        }
    
    def decide(self, observation: WorldState) -> LoomDecision:
        """Decision logic は v3.1 と完全に同じ.
        
        Sociable Detection の結果は trace に含めるが、決定には影響しない.
        """
        # === v3.1 の決定 (override せず, super 呼び出し) ===
        decision = super().decide(observation)
        
        # Track for shadow record
        self.last_module = (decision.selected_candidate.module 
                              if decision.selected_candidate else "fallback")
        self.last_guard_intervention = (decision.emergency_guard is not None 
                                           and decision.emergency_guard.applied)
        self.last_throttle_intervention = (decision.throttle_guard is not None
                                              and decision.throttle_guard.applied)
        self.last_revalidation_rejected = "rejected" in decision.revalidation_result
        self.last_primary_mode = decision.primary_mode
        
        # Shadow record を decision metadata に追加 (trace 用)
        shadow_report = self.sociable_shadow.get_report()
        if shadow_report.n_observation_records > 5:  # warmup
            decision.metadata["sociable_shadow"] = {
                "drift_lik": shadow_report.orbit_metrics.drift_likelihood,
                "chaotic_lik": shadow_report.orbit_metrics.chaotic_likelihood,
                "noisy_lik": shadow_report.orbit_metrics.noisy_likelihood,
                "drift_escape": shadow_report.orbit_metrics.drift_escape_score,
                "directional_persistence": shadow_report.orbit_metrics.directional_persistence,
                "reversal_rate": shadow_report.orbit_metrics.reversal_rate,
                "no_improvement_cycle": shadow_report.orbit_metrics.no_improvement_cycle_score,
                "dominant_failure_face": (
                    shadow_report.failure_distribution.dominant_face.value
                    if shadow_report.failure_distribution.dominant_face else None
                ),
                "dominant_failure_ratio": shadow_report.failure_distribution.dominant_ratio,
                "near_success_count": shadow_report.failure_distribution.near_success_count,
                "failure_entropy": shadow_report.failure_distribution.failure_face_entropy,
                "canonical_states": shadow_report.canonical_stats.get("canonical_states", 0),
                "canonical_failures": shadow_report.canonical_stats.get("canonical_failures", 0),
                "observation_records": shadow_report.n_observation_records,
            }
        else:
            decision.metadata["sociable_shadow"] = {"warmup": True}
        
        return decision
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        """v3.1 update + Sociable Shadow record"""
        # v3.1 super
        super().update_reward(action, reward, state_before, state_after)
        
        # === Shadow record (観測のみ, 行動への影響なし) ===
        if self.last_state_before is not None:
            world_type = "unknown"
            if self.stats["world_type_counts"]:
                world_type = max(self.stats["world_type_counts"],
                                  key=self.stats["world_type_counts"].get)
            context_name = "unknown"
            if self.stats["context_counts"]:
                context_name = max(self.stats["context_counts"],
                                    key=self.stats["context_counts"].get)
            
            self.sociable_shadow.update(
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
                stabilization_overuse=False,  # 行動介入なしなので無視
                drift_miss=False,
            )
            self.shadow_stats["total_shadow_records"] += 1
            
            # Track dominant failure face
            rep = self.sociable_shadow.get_report()
            if rep.failure_distribution.dominant_face is not None:
                face_name = rep.failure_distribution.dominant_face.value
                self.shadow_stats["shadow_dominant_faces"][face_name] = \
                    self.shadow_stats["shadow_dominant_faces"].get(face_name, 0) + 1
            
            # Track likelihood history
            self.shadow_stats["shadow_drift_lik_history"].append(
                rep.orbit_metrics.drift_likelihood
            )
            self.shadow_stats["shadow_chaotic_lik_history"].append(
                rep.orbit_metrics.chaotic_likelihood
            )
            self.shadow_stats["shadow_noisy_lik_history"].append(
                rep.orbit_metrics.noisy_likelihood
            )
    
    def get_shadow_report(self) -> SociableDetectionReport:
        """Public access to shadow report"""
        return self.sociable_shadow.get_report()
    
    def get_shadow_summary(self) -> Dict:
        """全 step での shadow detection 要約"""
        import numpy as np
        
        drift_hist = self.shadow_stats["shadow_drift_lik_history"]
        chaotic_hist = self.shadow_stats["shadow_chaotic_lik_history"]
        noisy_hist = self.shadow_stats["shadow_noisy_lik_history"]
        
        summary = {
            "total_records": self.shadow_stats["total_shadow_records"],
            "dominant_failure_faces": dict(self.shadow_stats["shadow_dominant_faces"]),
        }
        if drift_hist:
            summary["drift_likelihood_avg"] = float(np.mean(drift_hist))
            summary["drift_likelihood_max"] = float(np.max(drift_hist))
            summary["drift_likelihood_p75"] = float(np.percentile(drift_hist, 75))
        if chaotic_hist:
            summary["chaotic_likelihood_avg"] = float(np.mean(chaotic_hist))
        if noisy_hist:
            summary["noisy_likelihood_avg"] = float(np.mean(noisy_hist))
        
        rep = self.sociable_shadow.get_report()
        summary["canonical_stats"] = rep.canonical_stats
        summary["final_dominant_face"] = (
            rep.failure_distribution.dominant_face.value 
            if rep.failure_distribution.dominant_face else None
        )
        summary["final_failure_entropy"] = rep.failure_distribution.failure_face_entropy
        
        return summary


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    
    print("=" * 70)
    print("Loom v3.1 + Sociable Shadow Layer Test")
    print("=" * 70)
    
    for World, world_name in [(DriftingWorld, "Drifting"), (ChaoticWorld, "Chaotic")]:
        print(f"\n--- {world_name} mild ---")
        for seed in [42, 123]:
            cfg = ChaosConfig.from_level("mild")
            world = World(cfg, seed=seed)
            eng = LoomV31Shadow(rng_manager=RNGManager(master_seed=seed + 200000))
            
            for t in range(200):
                d = eng.decide(world.observe())
                r, done, _ = world.step(d.action)
                eng.update_reward(d.action, r)
                if done:
                    break
            
            shadow_sum = eng.get_shadow_summary()
            sparse = eng.get_sparse_summary()
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}")
            print(f"    Modes: {eng.stats['mode_counts']}")
            print(f"    Shadow records: {shadow_sum['total_records']}")
            if 'drift_likelihood_avg' in shadow_sum:
                print(f"    Shadow drift_lik avg={shadow_sum['drift_likelihood_avg']:.3f}, "
                      f"chaotic_lik avg={shadow_sum['chaotic_likelihood_avg']:.3f}, "
                      f"noisy_lik avg={shadow_sum['noisy_likelihood_avg']:.3f}")
            print(f"    Failure faces: {shadow_sum.get('dominant_failure_faces', {})}")
            print(f"    Canonical: {shadow_sum.get('canonical_stats', {})}")
            print(f"    Sparse: mean={sparse.get('mean_active', 0):.2f}")
    
    print("\n[Loom v3.1 Shadow 動作確認 ✅]")
