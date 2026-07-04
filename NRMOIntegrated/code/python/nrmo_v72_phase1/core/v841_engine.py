"""
core/v841_engine.py

V8.4.1 Complete Engine.

監査指摘への完全対応:
  ✓ Deterministic RNG 完全固定 (V71Engine も rng 注入)
  ✓ EmergencyResourceGuard (history 非依存 hard rule)
  ✓ ActionIntensityThrottle (rolling drawdown + consecutive)
  ✓ ActivePatternProxy (threshold=0.35 事前固定)
  ✓ Revalidation 実装 (proposed_action が R floor 等を violate しないか再確認)
  ✓ CumulativeRiskTracker 統合
  ✓ ablation switch (ActivePattern OFF/ON)
  ✓ intervention trace 詳細出力

Pipeline:
  v7.1 (with rng)
    → V71Engine base action
    → EmergencyResourceGuard (Rule 1-5, hard)
    → ActionIntensityThrottle (Rule 4-5)
    → ActivePattern (score-based proposal, threshold=0.35)
    → Revalidation (proposed_action を Emergency Guard で再チェック)
    → final action
    → history update
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from decision_trace import DecisionTrace
from rng_manager import RNGManager
from engines import V71Engine

from active_pattern_proxy import ActivePatternProxy, ActivePatternProposal
from veto_classification import VetoClassification, VetoType
from emergency_guards import (
    EmergencyResourceGuard, ActionIntensityThrottle, 
    GuardConfig, GuardDecision
)
from cumulative_risk_tracker import CumulativeRiskTracker, CumulativeRiskConfig


@dataclass
class V841Decision:
    """V8.4.1 Decision result"""
    action: Optional[Action]
    status: str  # "ACCEPT" / "GUARD_FORCED" / "AP_INTERVENED"
    confidence: float
    trace: DecisionTrace
    
    # 詳細 trace
    base_action: Optional[Action] = None
    emergency_guard: Optional[GuardDecision] = None
    throttle_guard: Optional[GuardDecision] = None
    active_pattern_proposal: Optional[ActivePatternProposal] = None
    revalidation_passed: bool = True
    revalidation_reason: str = ""
    
    metadata: Dict = field(default_factory=dict)


class V841Engine:
    """V8.4.1 完全実装"""
    
    # AP threshold は事前固定 (監査要件 2)
    AP_INTERVENTION_THRESHOLD = 0.35
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  use_active_pattern: bool = True,  # ablation 用
                  guard_config: Optional[GuardConfig] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        # V71Engine に rng 注入 (監査要件 1)
        v71_rng = self.rng_manager.spawn("v71_base")
        self.v71 = V71Engine(rng=v71_rng)
        
        # Hard guards (history 非依存)
        self.emergency_guard = EmergencyResourceGuard(guard_config)
        self.throttle_guard = ActionIntensityThrottle(guard_config)
        
        # ActivePattern (ablation switch)
        self.use_active_pattern = use_active_pattern
        self.active_pattern = ActivePatternProxy() if use_active_pattern else None
        # threshold 事前固定
        if self.active_pattern:
            self.active_pattern.INTERVENTION_THRESHOLD = self.AP_INTERVENTION_THRESHOLD
        
        # CumulativeRisk
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        # Stats
        self.decision_counter = 0
        self.stats = {
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "total_decisions": 0,
        }
        # 詳細 trace 履歴
        self.intervention_log: List[Dict] = []
    
    # ============================================================
    # Candidate generation (15 = 5 intents × 3 strengths)
    # ============================================================
    
    def _generate_all_candidates(self) -> List[Action]:
        cands = []
        for intent in ["invest", "defend", "explore", "recover", "hold"]:
            for strength in ["A", "B", "C"]:
                cands.append(Action(intent=intent, strength=strength))
        return cands
    
    # ============================================================
    # Revalidation (監査要件 7)
    # ============================================================
    
    def _revalidate_proposed_action(self, state: WorldState,
                                       proposed: Action) -> Tuple_bool_str:
        """proposed_action が hard rule を violate しないか再確認"""
        # Emergency Guard で proposed_action を再チェック
        revalidation = self.emergency_guard.apply(state, proposed)
        if revalidation.applied:
            # proposed_action 自体が hard rule に違反 → 拒否
            return False, f"revalidation_failed: {revalidation.rule_triggered}"
        
        # Cumulative risk projected check
        # proposed_action を取ったときの累積影響を予測
        projected_delta = self._estimate_action_delta(proposed)
        breached, details = self.cumulative_risk.projected_breach_after(projected_delta)
        if breached:
            return False, f"cumulative_breach_predicted: {details['would_breaches'][:1]}"
        
        return True, "passed"
    
    def _estimate_action_delta(self, action: Action) -> Dict[str, float]:
        """action による state delta 予測"""
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
                 context: Optional[Dict] = None) -> V841Decision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        trace = DecisionTrace(decision_id=self.decision_counter)
        
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
        
        # Step 2: EmergencyResourceGuard (hard rule, 即時)
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
            })
            trace.add("emergency_guard", "intervened", emergency_decision.to_dict())
        else:
            trace.add("emergency_guard", "pass", {"rule": "none"})
        
        # Step 3: ActionIntensityThrottle (history を使う)
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
                "from": f"{emergency_decision.forced_action.intent if emergency_decision.applied else base_action.intent}/...",
                "to": f"{current_action.intent}/{current_action.strength}",
            })
            trace.add("throttle_guard", "intervened", throttle_decision.to_dict())
        else:
            trace.add("throttle_guard", "pass", {"rule": "none"})
        
        # Step 4: ActivePattern (ablation OFF なら skip)
        if self.use_active_pattern and self.active_pattern is not None:
            all_candidates = self._generate_all_candidates()
            veto = VetoClassification.no_veto()
            
            ap_proposal = self.active_pattern.evaluate(
                state, all_candidates, current_action, veto
            )
            
            trace.add("active_pattern", 
                       "warning" if ap_proposal.has_correction_proposal else "pass",
                       ap_proposal.to_dict())
            
            # Step 5: Revalidation (監査要件)
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
                        "ap_level": ap_proposal.level,
                        "from": f"{ap_proposal.original_action.intent}/{ap_proposal.original_action.strength}",
                        "to": f"{current_action.intent}/{current_action.strength}",
                        "reason": ap_proposal.proposal_reason,
                    })
                    trace.add("revalidation", "passed", {
                        "accepted_proposal": True,
                    })
                else:
                    self.stats["revalidation_rejected"] += 1
                    trace.add("revalidation", "rejected", {
                        "reason": reason,
                    })
                    # current_action は変更しない
        
        # Step 6: 履歴更新 (final action でする)
        if self.use_active_pattern and self.active_pattern is not None:
            self.active_pattern.update_history(state, current_action)
        self.throttle_guard.update_history(state, current_action)
        
        return V841Decision(
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
            metadata={"stats": dict(self.stats)},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before: Optional[Dict] = None,
                       state_after: Optional[Dict] = None):
        self.v71.update_reward(action, reward)
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)


# Tuple type alias (Python compat)
from typing import Tuple
Tuple_bool_str = Tuple[bool, str]


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from world_models import World, WorldType
    from chaotic_world import ChaoticWorld, ChaosConfig
    
    print("=" * 70)
    print("V8.4.1 Complete Engine Test")
    print("=" * 70)
    
    # ChaoticWorld severe で動作確認
    config = ChaosConfig.from_level("severe")
    world = ChaoticWorld(config, seed=42)
    
    rng_mgr = RNGManager(master_seed=42 + 700000)
    engine = V841Engine(rng_manager=rng_mgr, use_active_pattern=True)
    
    print(f"\n--- Pipeline trace (15 step) ---")
    for t in range(15):
        state_before = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                         "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = engine.decide(world.state)
        
        marker = ""
        if d.status == "GUARD_FORCED": marker = " 🛡"
        if d.status == "AP_INTERVENED": marker = " ⚡"
        
        print(f"  t={t+1:2d}: base={d.base_action.intent}/{d.base_action.strength} "
              f"→ final={d.action.intent}/{d.action.strength}{marker}  "
              f"R={world.state.R:.0f} E={world.state.E:.0f} X={world.state.X:.0f}")
        if d.emergency_guard and d.emergency_guard.applied:
            print(f"      [EG] {d.emergency_guard.rule_triggered}")
        if d.throttle_guard and d.throttle_guard.applied:
            print(f"      [TH] {d.throttle_guard.rule_triggered}")
        if d.active_pattern_proposal and d.active_pattern_proposal.has_correction_proposal:
            print(f"      [AP] score={d.active_pattern_proposal.score:.2f}, "
                  f"reval={d.revalidation_passed}")
        
        reward, done, _ = world.step(d.action)
        state_after = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                         "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.update_reward(d.action, reward, state_before, state_after)
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    print(f"\n--- Stats ---")
    print(f"  Total decisions: {engine.stats['total_decisions']}")
    print(f"  Emergency Guard: {engine.stats['emergency_triggered']}")
    print(f"  Throttle Guard:  {engine.stats['throttle_triggered']}")
    print(f"  AP intervened:   {engine.stats['ap_intervened']}")
    print(f"  Reval rejected:  {engine.stats['revalidation_rejected']}")
    print(f"  Score:           {world.state.cumulative_score:.2f}")
    
    print("\n[V8.4.1 Complete Engine 動作確認 ✅]")
