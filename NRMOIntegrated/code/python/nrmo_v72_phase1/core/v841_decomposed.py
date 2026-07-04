"""
core/v841_decomposed.py

V8.4.1 の構成要素別 ablation engine.

V8.4.1 components:
  1. V71Engine (base)
  2. EmergencyResourceGuard (EG)
  3. ActionIntensityThrottle (TH)
  4. ActivePatternProxy (AP)
  5. Revalidation (passed_action を EG で再確認)
  6. CumulativeRiskTracker (累積 risk)

Variants for ablation:
  v71_pure:        V71Engine only (no guard, no AP)
  v71_eg_only:     V71 + EG
  v71_th_only:     V71 + TH
  v71_eg_th:       V71 + EG + TH (no AP, no revalidation)
  v71_full_no_ap:  V71 + EG + TH + Reval + CumRisk (no AP)
  v841_full:       V71 + EG + TH + AP + Reval + CumRisk (= v8.4.1)
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from decision_trace import DecisionTrace
from rng_manager import RNGManager
from engines import V71Engine
from active_pattern_proxy import ActivePatternProxy
from veto_classification import VetoClassification, VetoType
from emergency_guards import (
    EmergencyResourceGuard, ActionIntensityThrottle,
    GuardConfig, GuardDecision
)
from cumulative_risk_tracker import CumulativeRiskTracker, CumulativeRiskConfig


class V841DecomposedEngine:
    """V8.4.1 を構成要素別に ablation 可能にした engine"""
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  use_emergency_guard: bool = True,
                  use_throttle: bool = True,
                  use_active_pattern: bool = True,
                  use_revalidation: bool = True,
                  use_cumulative_risk: bool = True,
                  guard_config: Optional[GuardConfig] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        v71_rng = self.rng_manager.spawn("v71_base")
        self.v71 = V71Engine(rng=v71_rng)
        
        self.base_guard_config = guard_config or GuardConfig()
        
        # Ablation flags
        self.use_emergency_guard = use_emergency_guard
        self.use_throttle = use_throttle
        self.use_active_pattern = use_active_pattern
        self.use_revalidation = use_revalidation
        self.use_cumulative_risk = use_cumulative_risk
        
        # Components (always created, conditionally used)
        self.emergency_guard = EmergencyResourceGuard(self.base_guard_config)
        self.throttle_guard = ActionIntensityThrottle(self.base_guard_config)
        self.active_pattern = ActivePatternProxy()
        self.active_pattern.INTERVENTION_THRESHOLD = 0.35
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        self.decision_counter = 0
        self.stats = {
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "total_decisions": 0,
        }
    
    def _generate_all_candidates(self) -> List[Action]:
        return [Action(i, s) for i in ["invest", "defend", "explore", "recover", "hold"]
                 for s in ["A", "B", "C"]]
    
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
        if not self.use_revalidation:
            return True, "revalidation_disabled"
        revalidation = self.emergency_guard.apply(state, proposed)
        if revalidation.applied:
            return False, f"revalidation_failed: {revalidation.rule_triggered}"
        if self.use_cumulative_risk:
            projected_delta = self._estimate_action_delta(proposed)
            breached, _ = self.cumulative_risk.projected_breach_after(projected_delta)
            if breached:
                return False, "cumulative_breach"
        return True, "passed"
    
    def decide(self, state: WorldState, context=None):
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        
        # V71 base
        current_action = self.v71.select_action(state)
        
        # EmergencyResourceGuard
        if self.use_emergency_guard:
            eg = self.emergency_guard.apply(state, current_action)
            if eg.applied:
                current_action = eg.forced_action
                self.stats["emergency_triggered"] += 1
        
        # ActionIntensityThrottle
        if self.use_throttle:
            th = self.throttle_guard.apply(state, current_action)
            if th.applied:
                current_action = th.forced_action
                self.stats["throttle_triggered"] += 1
        
        # ActivePattern
        if self.use_active_pattern:
            all_cands = self._generate_all_candidates()
            veto = VetoClassification.no_veto()
            ap = self.active_pattern.evaluate(state, all_cands, current_action, veto)
            if ap.has_correction_proposal and ap.proposed_action:
                passed, _ = self._revalidate(state, ap.proposed_action)
                if passed:
                    current_action = ap.proposed_action
                    self.stats["ap_intervened"] += 1
                else:
                    self.stats["revalidation_rejected"] += 1
        
        # Histories
        if self.use_active_pattern:
            self.active_pattern.update_history(state, current_action)
        if self.use_throttle:
            self.throttle_guard.update_history(state, current_action)
        
        return current_action
    
    def update_reward(self, action, reward, state_before=None, state_after=None):
        self.v71.update_reward(action, reward)
        if self.use_cumulative_risk and state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)


# ============================================================
# Variant factory
# ============================================================

VARIANTS_HARD_GUARD = {
    "v71_pure": {
        "use_emergency_guard": False, "use_throttle": False,
        "use_active_pattern": False, "use_revalidation": False,
        "use_cumulative_risk": False,
    },
    "v71_eg_only": {
        "use_emergency_guard": True, "use_throttle": False,
        "use_active_pattern": False, "use_revalidation": False,
        "use_cumulative_risk": False,
    },
    "v71_th_only": {
        "use_emergency_guard": False, "use_throttle": True,
        "use_active_pattern": False, "use_revalidation": False,
        "use_cumulative_risk": False,
    },
    "v71_eg_th": {
        "use_emergency_guard": True, "use_throttle": True,
        "use_active_pattern": False, "use_revalidation": False,
        "use_cumulative_risk": False,
    },
    "v71_full_no_ap": {
        "use_emergency_guard": True, "use_throttle": True,
        "use_active_pattern": False, "use_revalidation": True,
        "use_cumulative_risk": True,
    },
    "v841_full": {
        "use_emergency_guard": True, "use_throttle": True,
        "use_active_pattern": True, "use_revalidation": True,
        "use_cumulative_risk": True,
    },
}


if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    
    print("=" * 70)
    print("V841 Decomposed Engine Test")
    print("=" * 70)
    
    for world_class, world_name in [(ChaoticWorld, "ChaoticWorld"), 
                                       (DriftingWorld, "DriftingWorld")]:
        print(f"\n--- {world_name} (severe) ---")
        for variant_name, variant_cfg in VARIANTS_HARD_GUARD.items():
            cfg = ChaosConfig.from_level("severe")
            world = world_class(cfg, seed=42)
            rng_mgr = RNGManager(master_seed=42 + 200000)
            eng = V841DecomposedEngine(rng_manager=rng_mgr, **variant_cfg)
            
            for t in range(200):
                sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                      "O": world.state.O, "K": world.state.K, "X": world.state.X}
                a = eng.decide(world.state)
                r, done, _ = world.step(a)
                sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                      "O": world.state.O, "K": world.state.K, "X": world.state.X}
                eng.update_reward(a, r, sb, sa)
                if done:
                    break
            
            print(f"  {variant_name:<18}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}, EG={eng.stats['emergency_triggered']}, "
                  f"TH={eng.stats['throttle_triggered']}, AP={eng.stats['ap_intervened']}")
    
    print("\n[V841 Decomposed 動作確認 ✅]")
