"""
core/emergency_guards.py

監査指摘 #3 への対応: EmergencyResourceGuard
監査指摘 #4 への対応: history-lagged 問題の解決 (current state を直接使う)
監査指摘 #6 への対応: B/C action 完全禁止 hard rule
監査の Minimal guard rules を厳密に実装.

これらは history-independent な hard guards.
ActivePattern の weighted score とは独立.
NRMO Core / Revalidation の前段に置く.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action


# ============================================================
# Configuration (監査仕様に従う)
# ============================================================

@dataclass
class GuardConfig:
    """Hard guard 閾値"""
    # Emergency Resource Guard
    r_emergency: float = 10.0      # R<=10: B/C 完全禁止、recover/A 強制
    r_critical: float = 15.0       # R<=15: B/C 禁止
    r_warning: float = 25.0        # R<=25: C 禁止
    
    # ActionIntensityThrottle
    rolling_window: int = 3
    r_drawdown_threshold: float = 0.20  # 3-step で R が 20% 以上低下
    consecutive_large_limit: int = 2     # B/C が 2 連続したら次は A
    
    # E (体力) emergency
    e_critical: float = 15.0       # E<=15: B/C 禁止
    
    # X (リスク) ceiling
    x_critical: float = 85.0       # X>=85: invest/explore 系の B/C 禁止


# ============================================================
# Guard result
# ============================================================

@dataclass
class GuardDecision:
    """Hard guard の決定"""
    applied: bool                  # guard が発動したか
    rule_triggered: str            # どの rule か
    original_action: Optional[Action] = None
    forced_action: Optional[Action] = None
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "applied": self.applied,
            "rule_triggered": self.rule_triggered,
            "original": (f"{self.original_action.intent}/{self.original_action.strength}"
                          if self.original_action else None),
            "forced": (f"{self.forced_action.intent}/{self.forced_action.strength}"
                        if self.forced_action else None),
            "reason": self.reason,
        }


# ============================================================
# EmergencyResourceGuard (history 非依存)
# ============================================================

class EmergencyResourceGuard:
    """R critical 時の B/C 完全禁止 (監査 Rule 1-3)
    
    History に依存しない、current state を直接見る hard guard.
    """
    
    def __init__(self, config: Optional[GuardConfig] = None):
        self.config = config or GuardConfig()
        self.triggered_count = 0
        self.triggered_history: List[Dict] = []
    
    def apply(self, state: WorldState, action: Action) -> GuardDecision:
        """current state を直接見て guard を適用"""
        cfg = self.config
        R = float(state.R)
        E = float(state.E)
        X = float(state.X)
        
        # Rule 1 (監査 R<=10): B/C/explore/invest 完全禁止、recover/A 強制
        if R <= cfg.r_emergency:
            forced = Action(intent="recover", strength="A")
            self.triggered_count += 1
            decision = GuardDecision(
                applied=True,
                rule_triggered="EMERGENCY_R<=10",
                original_action=action,
                forced_action=forced,
                reason=f"R={R:.1f} <= {cfg.r_emergency} (EMERGENCY): force recover/A",
            )
            self.triggered_history.append(decision.to_dict())
            return decision
        
        # Rule 2 (監査 R<=15): B/C 禁止
        if R <= cfg.r_critical and action.strength in ("B", "C"):
            # invest/explore B/C → recover/A
            if action.intent in ("invest", "explore"):
                forced = Action(intent="recover", strength="A")
            else:
                # defend/recover の B/C → 同じ intent の A
                forced = Action(intent=action.intent, strength="A")
            self.triggered_count += 1
            decision = GuardDecision(
                applied=True,
                rule_triggered="CRITICAL_R<=15",
                original_action=action,
                forced_action=forced,
                reason=f"R={R:.1f} <= {cfg.r_critical} (CRITICAL): block B/C",
            )
            self.triggered_history.append(decision.to_dict())
            return decision
        
        # Rule 3 (監査 R<=25): C 禁止
        if R <= cfg.r_warning and action.strength == "C":
            if action.intent in ("invest", "explore"):
                # C → A に縮小
                forced = Action(intent=action.intent, strength="A")
            else:
                forced = Action(intent=action.intent, strength="A")
            self.triggered_count += 1
            decision = GuardDecision(
                applied=True,
                rule_triggered="WARNING_R<=25",
                original_action=action,
                forced_action=forced,
                reason=f"R={R:.1f} <= {cfg.r_warning}: downsize C→A",
            )
            self.triggered_history.append(decision.to_dict())
            return decision
        
        # Rule 4: E critical
        if E <= cfg.e_critical and action.strength in ("B", "C"):
            if action.intent in ("invest", "explore"):
                forced = Action(intent="recover", strength="A")
            else:
                forced = Action(intent=action.intent, strength="A")
            self.triggered_count += 1
            decision = GuardDecision(
                applied=True,
                rule_triggered="E_CRITICAL",
                original_action=action,
                forced_action=forced,
                reason=f"E={E:.1f} <= {cfg.e_critical}: block B/C",
            )
            self.triggered_history.append(decision.to_dict())
            return decision
        
        # Rule 5: X ceiling
        if X >= cfg.x_critical and action.intent in ("invest", "explore"):
            if action.strength in ("B", "C"):
                forced = Action(intent="defend", strength="A")
                self.triggered_count += 1
                decision = GuardDecision(
                    applied=True,
                    rule_triggered="X_CEILING",
                    original_action=action,
                    forced_action=forced,
                    reason=f"X={X:.1f} >= {cfg.x_critical}: block invest/explore B/C",
                )
                self.triggered_history.append(decision.to_dict())
                return decision
        
        # No guard triggered
        return GuardDecision(
            applied=False,
            rule_triggered="none",
            original_action=action,
            reason="state above all thresholds",
        )


# ============================================================
# ActionIntensityThrottle (history を使う)
# ============================================================

class ActionIntensityThrottle:
    """連続大 action の制限 (監査 Rule 4-5)
    
    rolling R drawdown ≥ 0.20 で max_strength = A
    consecutive B/C ≥ 2 で次回 A 強制
    """
    
    def __init__(self, config: Optional[GuardConfig] = None):
        self.config = config or GuardConfig()
        self.action_history: deque = deque(maxlen=self.config.rolling_window + 2)
        self.r_history: deque = deque(maxlen=self.config.rolling_window + 1)
        self.consecutive_large = 0
        self.triggered_count = 0
        self.triggered_history: List[Dict] = []
    
    def apply(self, state: WorldState, action: Action) -> GuardDecision:
        cfg = self.config
        R_now = float(state.R)
        
        # Rule 4: rolling R drawdown
        if len(self.r_history) >= cfg.rolling_window:
            r_peak = max(self.r_history)
            if r_peak > 0:
                drawdown = (r_peak - R_now) / r_peak
                if drawdown >= cfg.r_drawdown_threshold:
                    if action.strength in ("B", "C"):
                        forced = Action(intent=action.intent, strength="A")
                        self.triggered_count += 1
                        decision = GuardDecision(
                            applied=True,
                            rule_triggered=f"R_DRAWDOWN_{drawdown:.2f}",
                            original_action=action,
                            forced_action=forced,
                            reason=f"rolling R drawdown={drawdown:.2f} >= {cfg.r_drawdown_threshold}",
                        )
                        self.triggered_history.append(decision.to_dict())
                        return decision
        
        # Rule 5: consecutive large
        if self.consecutive_large >= cfg.consecutive_large_limit:
            if action.strength in ("B", "C"):
                forced = Action(intent=action.intent, strength="A")
                self.triggered_count += 1
                decision = GuardDecision(
                    applied=True,
                    rule_triggered=f"CONSECUTIVE_LARGE_{self.consecutive_large}",
                    original_action=action,
                    forced_action=forced,
                    reason=f"consecutive B/C = {self.consecutive_large} >= {cfg.consecutive_large_limit}",
                )
                self.triggered_history.append(decision.to_dict())
                return decision
        
        # No throttle
        return GuardDecision(
            applied=False,
            rule_triggered="none",
            original_action=action,
            reason="within intensity limits",
        )
    
    def update_history(self, state: WorldState, final_action: Action):
        """毎 step 更新 (final action を記録)"""
        self.r_history.append(float(state.R))
        self.action_history.append({
            "intent": final_action.intent,
            "strength": final_action.strength,
        })
        if final_action.strength in ("B", "C"):
            self.consecutive_large += 1
        else:
            self.consecutive_large = 0


# ============================================================
# Unit Tests (監査要件 5)
# ============================================================

def run_emergency_guard_unit_tests():
    """監査要件 #5: EmergencyResourceGuard の unit test"""
    print("=" * 70)
    print("EmergencyResourceGuard Unit Tests")
    print("=" * 70)
    
    guard = EmergencyResourceGuard()
    
    test_cases = [
        # (R, E, X, action, expected_rule, expected_forced)
        (9, 70, 20, Action("invest", "B"),  "EMERGENCY_R<=10",  ("recover", "A")),
        (9, 70, 20, Action("invest", "C"),  "EMERGENCY_R<=10",  ("recover", "A")),
        (9, 70, 20, Action("explore", "A"), "EMERGENCY_R<=10",  ("recover", "A")),
        (9, 70, 20, Action("hold", "A"),    "EMERGENCY_R<=10",  ("recover", "A")),
        (14, 70, 20, Action("invest", "B"), "CRITICAL_R<=15",   ("recover", "A")),
        (14, 70, 20, Action("invest", "C"), "CRITICAL_R<=15",   ("recover", "A")),
        (14, 70, 20, Action("defend", "B"), "CRITICAL_R<=15",   ("defend", "A")),
        (14, 70, 20, Action("invest", "A"), "none",             None),
        (20, 70, 20, Action("invest", "C"), "WARNING_R<=25",    ("invest", "A")),
        (20, 70, 20, Action("invest", "B"), "none",             None),
        (60, 14, 20, Action("invest", "B"), "E_CRITICAL",       ("recover", "A")),
        (60, 70, 86, Action("invest", "B"), "X_CEILING",        ("defend", "A")),
        (60, 70, 30, Action("invest", "B"), "none",             None),
        (60, 70, 30, Action("explore", "C"), "none",            None),
    ]
    
    passed = 0
    failed = 0
    for i, (R, E, X, action, exp_rule, exp_forced) in enumerate(test_cases):
        state = WorldState(t=0, R=R, E=E, G=70, O=50, K=50, X=X,
                            cumulative_score=0.0, is_ruined=False)
        decision = guard.apply(state, action)
        
        rule_ok = decision.rule_triggered == exp_rule
        if exp_forced is None:
            forced_ok = not decision.applied
        else:
            forced_ok = (decision.applied and
                          decision.forced_action.intent == exp_forced[0] and
                          decision.forced_action.strength == exp_forced[1])
        
        if rule_ok and forced_ok:
            passed += 1
            print(f"  ✓ Test {i+1}: R={R} {action.intent}/{action.strength} → {decision.rule_triggered}")
        else:
            failed += 1
            print(f"  ✗ Test {i+1}: R={R} E={E} X={X} {action.intent}/{action.strength}")
            print(f"      Expected: {exp_rule}, forced={exp_forced}")
            print(f"      Got:      {decision.rule_triggered}, "
                  f"forced={(decision.forced_action.intent, decision.forced_action.strength) if decision.forced_action else None}")
    
    print(f"\nResult: {passed} passed, {failed} failed")
    return passed, failed


def run_throttle_unit_tests():
    """ActionIntensityThrottle の unit test"""
    print("\n" + "=" * 70)
    print("ActionIntensityThrottle Unit Tests")
    print("=" * 70)
    
    # Test 1: rolling R drawdown
    throttle = ActionIntensityThrottle()
    state100 = WorldState(t=0, R=100, E=70, G=70, O=50, K=50, X=20,
                            cumulative_score=0, is_ruined=False)
    state60 = WorldState(t=3, R=60, E=70, G=70, O=50, K=50, X=20,
                          cumulative_score=0, is_ruined=False)
    state90 = WorldState(t=3, R=90, E=70, G=70, O=50, K=50, X=20,
                          cumulative_score=0, is_ruined=False)
    
    # 履歴を 100, 95, 100 → 60 (40% drawdown)
    throttle.update_history(state100, Action("hold", "A"))
    state95 = WorldState(t=1, R=95, E=70, G=70, O=50, K=50, X=20,
                          cumulative_score=0, is_ruined=False)
    throttle.update_history(state95, Action("hold", "A"))
    throttle.update_history(state100, Action("hold", "A"))
    
    decision = throttle.apply(state60, Action("invest", "C"))
    test1_ok = decision.applied and "R_DRAWDOWN" in decision.rule_triggered
    print(f"  {'✓' if test1_ok else '✗'} Test 1 R drawdown: applied={decision.applied}, rule={decision.rule_triggered}")
    
    # Test 2: consecutive large
    throttle2 = ActionIntensityThrottle()
    state_stable = WorldState(t=0, R=60, E=70, G=70, O=50, K=50, X=20,
                                cumulative_score=0, is_ruined=False)
    throttle2.update_history(state_stable, Action("invest", "B"))
    throttle2.update_history(state_stable, Action("invest", "C"))
    # 3 連目で trigger
    decision2 = throttle2.apply(state_stable, Action("invest", "B"))
    test2_ok = decision2.applied and "CONSECUTIVE" in decision2.rule_triggered
    print(f"  {'✓' if test2_ok else '✗'} Test 2 Consecutive: applied={decision2.applied}, rule={decision2.rule_triggered}")
    
    # Test 3: no trigger (small drawdown, no consecutive)
    throttle3 = ActionIntensityThrottle()
    throttle3.update_history(state100, Action("invest", "A"))
    decision3 = throttle3.apply(state95, Action("invest", "B"))
    test3_ok = not decision3.applied
    print(f"  {'✓' if test3_ok else '✗'} Test 3 No trigger: applied={decision3.applied}")
    
    passed = sum([test1_ok, test2_ok, test3_ok])
    return passed, 3 - passed


if __name__ == "__main__":
    p1, f1 = run_emergency_guard_unit_tests()
    p2, f2 = run_throttle_unit_tests()
    
    total_p = p1 + p2
    total_f = f1 + f2
    print(f"\n{'='*70}")
    print(f"TOTAL: {total_p} passed, {total_f} failed")
    print(f"{'='*70}")
    
    if total_f == 0:
        print("\n✅ All hard guard unit tests PASSED")
    else:
        print(f"\n❌ {total_f} tests FAILED")
