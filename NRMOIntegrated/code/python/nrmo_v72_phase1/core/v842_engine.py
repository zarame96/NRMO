"""
core/v842_engine.py

V8.4.2 Engine = v8.4.1 (frozen baseline) + MAPLayer only.

Strict isolation (per handoff doc § 5):
  - NO PassivePattern addition
  - NO StrongEngineΩfull addition
  - NO Shinobi addition
  - NO other module additions

MAPLayer integration philosophy:
  MAPLayer provides observation_noise estimation and near_ruin history.
  This context is fed into hard guards / throttle for ADAPTIVE threshold
  adjustment. MAPLayer does NOT generate candidates or directly select actions.
  
  Specifically:
    - If MAPLayer detects near_ruin history → guard r_warning tightens
    - If MAPLayer detects high observation noise → throttle becomes stricter
    - If MAPLayer detects state deterioration trend → r_drawdown threshold tightens
  
  The MAPLayer's role is purely contextual augmentation of existing guards,
  not new authority.

v8.4.2 acceptance criteria (per handoff doc § 5):
  1. Does not degrade v8.4.1 in mild/moderate/severe
  2. Improves or stabilizes extreme/total
  3. MAPLayer ON/OFF ablation shows measurable benefit
  4. Deterministic RNG remains intact
  5. Intervention traces remain explainable
  6. No additional early-ruin mechanism appears
  7. No uncontrolled candidate amplification occurs
"""
from __future__ import annotations
import os
import sys
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from decision_trace import DecisionTrace
from rng_manager import RNGManager
from engines import V71Engine
from v841_engine import V841Engine, V841Decision

from active_pattern_proxy import ActivePatternProxy
from veto_classification import VetoClassification, VetoType
from emergency_guards import (
    EmergencyResourceGuard, ActionIntensityThrottle,
    GuardConfig, GuardDecision
)
from cumulative_risk_tracker import CumulativeRiskTracker, CumulativeRiskConfig
from map_layer import MAPLayer


@dataclass
class V842Decision(V841Decision):
    """V8.4.2 Decision (extends V841Decision with MAPLayer info)"""
    map_layer_info: Dict = field(default_factory=dict)
    adaptive_config: Dict = field(default_factory=dict)  # 動的調整された guard config


class V842Engine:
    """V8.4.2 = v8.4.1 + MAPLayer only
    
    Composed (not inherited) to make ablation explicit.
    """
    
    # AP threshold pre-fixed (v8.4.1 から継承)
    AP_INTERVENTION_THRESHOLD = 0.35
    
    # MAPLayer-based adaptive adjustment thresholds
    NEAR_RUIN_HISTORY_THRESHOLD = 3   # この件数以上で guard 強化
    OBS_NOISE_HIGH_THRESHOLD = 0.30
    OBS_NOISE_VERY_HIGH_THRESHOLD = 0.50
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  use_active_pattern: bool = True,
                  use_map_layer: bool = True,         # ablation switch
                  guard_config: Optional[GuardConfig] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        # V71Engine (deterministic RNG)
        v71_rng = self.rng_manager.spawn("v71_base")
        self.v71 = V71Engine(rng=v71_rng)
        
        # Base guards (v8.4.1 と同じ)
        self.base_guard_config = guard_config or GuardConfig()
        self.emergency_guard = EmergencyResourceGuard(self.base_guard_config)
        self.throttle_guard = ActionIntensityThrottle(self.base_guard_config)
        
        # ActivePattern (ablation switch, v8.4.1 から継承)
        self.use_active_pattern = use_active_pattern
        self.active_pattern = ActivePatternProxy() if use_active_pattern else None
        if self.active_pattern:
            self.active_pattern.INTERVENTION_THRESHOLD = self.AP_INTERVENTION_THRESHOLD
        
        # CumulativeRisk
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        # ★ MAPLayer (v8.4.2 新規追加)
        self.use_map_layer = use_map_layer
        self.map_layer = MAPLayer() if use_map_layer else None
        
        # Stats
        self.decision_counter = 0
        self.stats = {
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "total_decisions": 0,
            # MAPLayer 関連
            "map_adaptive_tightening_count": 0,
            "near_ruin_events_observed": 0,
            "obs_noise_high_count": 0,
        }
        self.intervention_log: List[Dict] = []
    
    # ============================================================
    # MAPLayer-based adaptive adjustment
    # ============================================================
    
    def _estimate_observation_noise(self) -> float:
        """MAPLayer から観測ノイズを推定"""
        if not self.use_map_layer or self.map_layer is None:
            return 0.05  # default
        
        # MAPLayer の event count から推定
        near_ruin = self.map_layer.near_ruin_count()
        regime_shift = self.map_layer.regime_shift_count()
        total_events = near_ruin + regime_shift
        
        if total_events == 0:
            return 0.05
        elif total_events < 5:
            return 0.15
        elif total_events < 15:
            return 0.30
        else:
            return 0.50
    
    def _compute_adaptive_guard_config(self) -> GuardConfig:
        """MAPLayer 情報で guard 閾値を動的調整
        
        - near_ruin 履歴が多い → r_warning を上げる (保守化)
        - 観測ノイズが高い → consecutive_large_limit を下げる
        - state trend が悪化 → r_drawdown_threshold を下げる
        """
        if not self.use_map_layer or self.map_layer is None:
            return self.base_guard_config
        
        adapted = copy.deepcopy(self.base_guard_config)
        
        near_ruin = self.map_layer.near_ruin_count()
        obs_noise = self._estimate_observation_noise()
        
        tightening_applied = False
        
        # Adjustment 1: Near-ruin history → r_warning 強化
        if near_ruin >= self.NEAR_RUIN_HISTORY_THRESHOLD:
            adapted.r_warning = min(35, self.base_guard_config.r_warning + 5)
            adapted.r_critical = min(20, self.base_guard_config.r_critical + 3)
            tightening_applied = True
            self.stats["near_ruin_events_observed"] = near_ruin
        
        # Adjustment 2: 観測ノイズ高い → throttle 強化
        if obs_noise > self.OBS_NOISE_HIGH_THRESHOLD:
            adapted.consecutive_large_limit = max(1, 
                self.base_guard_config.consecutive_large_limit - 1)
            tightening_applied = True
            self.stats["obs_noise_high_count"] += 1
        
        # Adjustment 3: 非常に高い観測ノイズ → r_drawdown 強化
        if obs_noise > self.OBS_NOISE_VERY_HIGH_THRESHOLD:
            adapted.r_drawdown_threshold = max(0.15,
                self.base_guard_config.r_drawdown_threshold - 0.05)
            tightening_applied = True
        
        # Adjustment 4: state trend が悪化 (L2 trends)
        if self.map_layer.l2:
            trends = self.map_layer.get_state_trends()
            if trends:
                # R trend 急減 or X trend 急増
                if trends.get("R", 0) < -1.0 or trends.get("X", 0) > 1.0:
                    adapted.r_warning = min(35, adapted.r_warning + 3)
                    tightening_applied = True
        
        if tightening_applied:
            self.stats["map_adaptive_tightening_count"] += 1
        
        return adapted
    
    # ============================================================
    # Candidate generation
    # ============================================================
    
    def _generate_all_candidates(self) -> List[Action]:
        cands = []
        for intent in ["invest", "defend", "explore", "recover", "hold"]:
            for strength in ["A", "B", "C"]:
                cands.append(Action(intent=intent, strength=strength))
        return cands
    
    # ============================================================
    # Revalidation (v8.4.1 と同じ)
    # ============================================================
    
    def _revalidate_proposed_action(self, state, proposed):
        revalidation = self.emergency_guard.apply(state, proposed)
        if revalidation.applied:
            return False, f"revalidation_failed: {revalidation.rule_triggered}"
        
        projected_delta = self._estimate_action_delta(proposed)
        breached, details = self.cumulative_risk.projected_breach_after(projected_delta)
        if breached:
            return False, f"cumulative_breach_predicted: {details['would_breaches'][:1]}"
        
        return True, "passed"
    
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
    
    # ============================================================
    # Main decide
    # ============================================================
    
    def decide(self, state: WorldState, 
                 context: Optional[Dict] = None) -> V842Decision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # ★ MAPLayer query (context augmentation)
        map_info = {}
        if self.use_map_layer and self.map_layer is not None:
            obs_noise = self._estimate_observation_noise()
            map_view = self.map_layer.query(observation_noise=obs_noise)
            map_info = {
                "observation_noise_est": obs_noise,
                "primary_layer": map_view["primary_layer"],
                "near_ruin_count": self.map_layer.near_ruin_count(),
                "regime_shift_count": self.map_layer.regime_shift_count(),
            }
            trace.add("map_layer_query", "pass", map_info)
            
            # 動的 guard config 計算
            adaptive_config = self._compute_adaptive_guard_config()
            # Engine の guard config を一時的に変更
            self.emergency_guard.config = adaptive_config
            self.throttle_guard.config = adaptive_config
        else:
            adaptive_config = self.base_guard_config
        
        adaptive_config_dict = {
            "r_warning": adaptive_config.r_warning,
            "r_critical": adaptive_config.r_critical,
            "r_emergency": adaptive_config.r_emergency,
            "consecutive_large_limit": adaptive_config.consecutive_large_limit,
            "r_drawdown_threshold": adaptive_config.r_drawdown_threshold,
        }
        
        # Step 1: v7.1 base action
        base_action = self.v71.select_action(state)
        trace.add("v71_base", "pass", {
            "action": f"{base_action.intent}/{base_action.strength}",
        })
        
        current_action = base_action
        status = "ACCEPT"
        emergency_decision = None
        throttle_decision = None
        ap_proposal = None
        revalidation_passed = True
        revalidation_reason = "n/a"
        
        # Step 2: EmergencyResourceGuard (with adaptive config)
        emergency_decision = self.emergency_guard.apply(state, current_action)
        if emergency_decision.applied:
            current_action = emergency_decision.forced_action
            status = "GUARD_FORCED"
            self.stats["emergency_triggered"] += 1
            self.intervention_log.append({
                "decision_id": self.decision_counter,
                "type": "emergency_guard",
                "rule": emergency_decision.rule_triggered,
                "state": {"R": state.R, "E": state.E, "X": state.X, "O": state.O},
                "from": f"{base_action.intent}/{base_action.strength}",
                "to": f"{current_action.intent}/{current_action.strength}",
                "map_info": map_info,
            })
            trace.add("emergency_guard", "intervened", emergency_decision.to_dict())
        else:
            trace.add("emergency_guard", "pass", {"rule": "none"})
        
        # Step 3: ActionIntensityThrottle
        throttle_decision = self.throttle_guard.apply(state, current_action)
        if throttle_decision.applied:
            current_action = throttle_decision.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            self.stats["throttle_triggered"] += 1
            self.intervention_log.append({
                "decision_id": self.decision_counter,
                "type": "throttle",
                "rule": throttle_decision.rule_triggered,
                "to": f"{current_action.intent}/{current_action.strength}",
            })
            trace.add("throttle_guard", "intervened", throttle_decision.to_dict())
        else:
            trace.add("throttle_guard", "pass", {"rule": "none"})
        
        # Step 4: ActivePattern (if enabled)
        if self.use_active_pattern and self.active_pattern is not None:
            all_candidates = self._generate_all_candidates()
            veto = VetoClassification.no_veto()
            ap_proposal = self.active_pattern.evaluate(
                state, all_candidates, current_action, veto
            )
            trace.add("active_pattern",
                       "warning" if ap_proposal.has_correction_proposal else "pass",
                       ap_proposal.to_dict())
            
            if ap_proposal.has_correction_proposal and ap_proposal.proposed_action:
                passed, reason = self._revalidate_proposed_action(
                    state, ap_proposal.proposed_action
                )
                revalidation_passed = passed
                revalidation_reason = reason
                
                if passed:
                    current_action = ap_proposal.proposed_action
                    if status == "ACCEPT":
                        status = "AP_INTERVENED"
                    self.stats["ap_intervened"] += 1
                    self.intervention_log.append({
                        "decision_id": self.decision_counter,
                        "type": "active_pattern",
                        "ap_score": ap_proposal.score,
                        "reason": ap_proposal.proposal_reason,
                    })
                    trace.add("revalidation", "passed", {"accepted_proposal": True})
                else:
                    self.stats["revalidation_rejected"] += 1
                    trace.add("revalidation", "rejected", {"reason": reason})
        
        # Step 5: Update histories
        if self.use_active_pattern and self.active_pattern is not None:
            self.active_pattern.update_history(state, current_action)
        self.throttle_guard.update_history(state, current_action)
        
        # ★ MAPLayer update (post)
        if self.use_map_layer and self.map_layer is not None:
            self.map_layer.update(
                t=self.decision_counter,
                state=state,
                action_intent=current_action.intent,
                action_strength=current_action.strength,
                reward=0.0,
            )
        
        return V842Decision(
            action=current_action,
            status=status,
            confidence=0.7,
            trace=trace,
            base_action=base_action,
            emergency_guard=emergency_decision,
            throttle_guard=throttle_decision,
            active_pattern_proposal=ap_proposal,
            revalidation_passed=revalidation_passed,
            revalidation_reason=revalidation_reason,
            map_layer_info=map_info,
            adaptive_config=adaptive_config_dict,
            metadata={"stats": dict(self.stats)},
        )
    
    def update_reward(self, action, reward, state_before=None, state_after=None):
        self.v71.update_reward(action, reward)
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)
        # MAPLayer の reward を後追い
        if self.use_map_layer and self.map_layer is not None and self.map_layer.l1:
            self.map_layer.l1[-1].reward = float(reward)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    
    print("=" * 70)
    print("V8.4.2 Engine Test (v8.4.1 + MAPLayer only)")
    print("=" * 70)
    
    config = ChaosConfig.from_level("severe")
    world = ChaoticWorld(config, seed=42)
    
    rng_mgr = RNGManager(master_seed=42 + 800000)
    engine = V842Engine(rng_manager=rng_mgr, 
                          use_active_pattern=True,
                          use_map_layer=True)
    
    print(f"\n--- Pipeline trace (15 step) ---")
    for t in range(15):
        state_before = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                         "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = engine.decide(world.state)
        
        marker = ""
        if d.status == "GUARD_FORCED": marker = " 🛡"
        if d.status == "AP_INTERVENED": marker = " ⚡"
        
        # MAPLayer info
        ml_info = d.map_layer_info
        adj = "adj" if engine.stats["map_adaptive_tightening_count"] > 0 else "   "
        
        print(f"  t={t+1:2d}: base={d.base_action.intent}/{d.base_action.strength} "
              f"→ {d.action.intent}/{d.action.strength}{marker}  "
              f"R={world.state.R:.0f} X={world.state.X:.0f}  "
              f"obs_noise={ml_info.get('observation_noise_est', 0):.2f} {adj}  "
              f"r_warn={d.adaptive_config['r_warning']:.0f}")
        if d.emergency_guard and d.emergency_guard.applied:
            print(f"      [EG] {d.emergency_guard.rule_triggered}")
        if d.throttle_guard and d.throttle_guard.applied:
            print(f"      [TH] {d.throttle_guard.rule_triggered}")
        
        reward, done, _ = world.step(d.action)
        state_after = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                         "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.update_reward(d.action, reward, state_before, state_after)
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    print(f"\n--- Stats ---")
    for k, v in engine.stats.items():
        print(f"  {k}: {v}")
    print(f"  Final score: {world.state.cumulative_score:.2f}")
    
    print("\n[V8.4.2 Engine 動作確認 完了 ✅]")
