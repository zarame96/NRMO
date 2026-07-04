"""
core/v843_engine.py

V8.4.3 = v8.4.1 + MAPLayer (predictive intervention) only.

v8.4.2 の adaptive_tightening が失敗した理由:
  reactive (事後対応): near_ruin 観測後に guard 強化 → 既に被害発生済み

v8.4.3 の方針:
  predictive (事前介入): L2 trend で「これから危機」を予測 → 危機発生前に介入

Pre-emergency signals:
  - R trend (L2 slope) < -1.5 かつ R < 40 → pre_r_emergency
  - X trend (L2 slope) > +1.5 かつ X > 50 → pre_x_critical
  - E trend (L2 slope) < -1.5 かつ E < 40 → pre_e_critical

介入レベル:
  severity > 0.6 → 強介入 (recover/A or defend/A 強制)
  severity > 0.4 → 軽介入 (B/C → A 縮小)

handoff doc § 5 制約:
  - MAPLayer only (他モジュール追加なし) ✓
  - ON/OFF ablation 可能 ✓
  - Deterministic RNG 維持 ✓
"""
from __future__ import annotations
import os
import sys
import copy
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
from map_layer import MAPLayer


@dataclass
class V843Decision:
    """V8.4.3 Decision"""
    action: Optional[Action]
    status: str  # "ACCEPT" / "GUARD_FORCED" / "AP_INTERVENED" / "PRE_EMERGENCY_FORCED"
    confidence: float
    trace: DecisionTrace
    base_action: Optional[Action] = None
    emergency_guard: Optional[GuardDecision] = None
    throttle_guard: Optional[GuardDecision] = None
    active_pattern_proposal: Optional[object] = None
    pre_emergency_signals: List[Dict] = field(default_factory=list)
    pre_emergency_intervention: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)


class V843Engine:
    """V8.4.3 = v8.4.1 + MAPLayer (predictive intervention)"""
    
    AP_INTERVENTION_THRESHOLD = 0.35
    
    # Pre-emergency thresholds (predictive, more sensitive for early detection)
    R_TREND_DECLINE_THRESHOLD = -1.2    # was -1.5, 早期検知
    X_TREND_RISE_THRESHOLD = +1.2       # was +1.5, 早期検知
    E_TREND_DECLINE_THRESHOLD = -1.2
    
    R_PRE_EMERGENCY_LEVEL = 45          # was 40, 早期検知 (R<=45 + 急減で signal)
    X_PRE_CRITICAL_LEVEL = 45           # was 50, 早期検知
    E_PRE_CRITICAL_LEVEL = 45           # was 40, 早期検知
    
    # Intervention severity (v8.4.3 improvement: thresholds raised to reduce 過剰介入)
    SEVERITY_STRONG = 0.70   # was 0.60
    SEVERITY_LIGHT = 0.50    # was 0.40
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  use_active_pattern: bool = True,
                  use_predictive: bool = True,      # ablation switch
                  guard_config: Optional[GuardConfig] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        v71_rng = self.rng_manager.spawn("v71_base")
        self.v71 = V71Engine(rng=v71_rng)
        
        self.base_guard_config = guard_config or GuardConfig()
        self.emergency_guard = EmergencyResourceGuard(self.base_guard_config)
        self.throttle_guard = ActionIntensityThrottle(self.base_guard_config)
        
        self.use_active_pattern = use_active_pattern
        self.active_pattern = ActivePatternProxy() if use_active_pattern else None
        if self.active_pattern:
            self.active_pattern.INTERVENTION_THRESHOLD = self.AP_INTERVENTION_THRESHOLD
        
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        # MAPLayer (predictive intervention の信号源)
        self.use_predictive = use_predictive
        self.map_layer = MAPLayer()  # 常に作成 (predictive OFF でも update する)
        
        self.decision_counter = 0
        self.stats = {
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "total_decisions": 0,
            # Predictive 関連
            "pre_emergency_signals_detected": 0,
            "pre_emergency_interventions": 0,
            "pre_r_emergency_count": 0,
            "pre_x_critical_count": 0,
            "pre_e_critical_count": 0,
        }
        self.intervention_log: List[Dict] = []
    
    # ============================================================
    # Predictive intervention (新規)
    # ============================================================
    
    def _detect_pre_emergency_signals(self, state: WorldState) -> List[Dict]:
        """MAPLayer L2 trends から「これから危機」を予測"""
        if not self.use_predictive or not self.map_layer.l2:
            return []
        
        trends = self.map_layer.get_state_trends()
        if not trends:
            return []
        
        r_trend = trends.get("R", 0)
        x_trend = trends.get("X", 0)
        e_trend = trends.get("E", 0)
        
        signals = []
        
        # Signal 1: R 急減トレンド + 中程度 R
        if r_trend < self.R_TREND_DECLINE_THRESHOLD and state.R < self.R_PRE_EMERGENCY_LEVEL:
            # severity = R 距離 + trend 強度
            r_distance = max(0, (self.R_PRE_EMERGENCY_LEVEL - state.R) / 25)
            trend_strength = min(1.0, abs(r_trend) / 3.0)
            severity = min(1.0, (r_distance + trend_strength) / 2 + 0.2)
            
            # 予測 step
            predicted_steps = max(1, int(state.R / max(0.5, abs(r_trend))))
            
            signals.append({
                "type": "pre_r_emergency",
                "severity": float(severity),
                "r_trend": float(r_trend),
                "r_now": float(state.R),
                "predicted_steps_to_emergency": predicted_steps,
            })
        
        # Signal 2: X 急増トレンド + 中程度 X
        if x_trend > self.X_TREND_RISE_THRESHOLD and state.X > self.X_PRE_CRITICAL_LEVEL:
            x_distance = max(0, (state.X - self.X_PRE_CRITICAL_LEVEL) / 35)
            trend_strength = min(1.0, x_trend / 3.0)
            severity = min(1.0, (x_distance + trend_strength) / 2 + 0.2)
            
            predicted_steps = max(1, int((85 - state.X) / max(0.5, x_trend)))
            
            signals.append({
                "type": "pre_x_critical",
                "severity": float(severity),
                "x_trend": float(x_trend),
                "x_now": float(state.X),
                "predicted_steps_to_critical": predicted_steps,
            })
        
        # Signal 3: E 急減
        if e_trend < self.E_TREND_DECLINE_THRESHOLD and state.E < self.E_PRE_CRITICAL_LEVEL:
            e_distance = max(0, (self.E_PRE_CRITICAL_LEVEL - state.E) / 25)
            trend_strength = min(1.0, abs(e_trend) / 3.0)
            severity = min(1.0, (e_distance + trend_strength) / 2 + 0.2)
            
            signals.append({
                "type": "pre_e_critical",
                "severity": float(severity),
                "e_trend": float(e_trend),
                "e_now": float(state.E),
            })
        
        return signals
    
    def _apply_predictive_intervention(self, state: WorldState,
                                          base_action: Action,
                                          signals: List[Dict]
                                          ) -> Tuple[Action, str, Optional[Dict]]:
        """Pre-emergency signal に基づいて事前介入 (context-aware + chaos-adaptive + revalidation)
        
        改善 K (chaos-adaptive):
          MAPLayer L3 event count から chaos level を推定
          高 chaos では介入を厳しく (variance 抑制)
        
        改善 M (NRMO Revalidation):
          proposed_action を emergency_guard で再評価
          guard が「拒否 = proposed 自体が violate」なら採用しない
        
        Returns: (intervened_action, reason, intervention_record)
        """
        if not signals:
            return base_action, "no_signals", None
        
        strongest = max(signals, key=lambda s: s["severity"])
        severity = strongest["severity"]
        signal_type = strongest["type"]
        
        # ★ 案 K: chaos-adaptive thresholds
        # L3 events から chaos を推定
        l3_events = self.map_layer.near_ruin_count() + self.map_layer.regime_shift_count()
        decision_count = self.decision_counter
        
        # chaos level 推定 (engine が world type を知らないので proxy)
        if decision_count < 20:
            # 初期段階 → 通常 threshold
            severity_strong = self.SEVERITY_STRONG
            severity_light = self.SEVERITY_LIGHT
        elif l3_events >= 15:
            # extreme/total chaos の proxy: LIGHT 無効 + STRONG 厳格
            severity_strong = 0.85
            severity_light = 2.0  # 実質無効化
        elif l3_events >= 5:
            # severe chaos の proxy: LIGHT 厳しく、STRONG わずか厳格
            severity_strong = 0.75
            severity_light = 0.65
        else:
            # mild/moderate chaos: 通常 threshold
            severity_strong = self.SEVERITY_STRONG
            severity_light = self.SEVERITY_LIGHT
        
        # state context
        O_high = state.O >= 60
        X_critical = state.X >= 70
        E_low = state.E <= 30
        R_very_low = state.R <= 20
        
        proposed_action = None
        intervention_level = None
        
        if severity >= severity_strong:
            intervention_level = "STRONG"
            if signal_type == "pre_r_emergency":
                if R_very_low or E_low:
                    proposed_action = Action(intent="recover", strength="A")
                elif X_critical:
                    proposed_action = Action(intent="defend", strength="A")
                elif O_high:
                    proposed_action = Action(intent="defend", strength="A")
                else:
                    proposed_action = Action(intent="recover", strength="A")
            elif signal_type == "pre_x_critical":
                if E_low:
                    proposed_action = Action(intent="recover", strength="A")
                else:
                    proposed_action = Action(intent="defend", strength="A")
            elif signal_type == "pre_e_critical":
                proposed_action = Action(intent="recover", strength="A")
        
        elif severity >= severity_light:
            intervention_level = "LIGHT"
            if base_action.strength in ("B", "C"):
                if (signal_type in ("pre_r_emergency", "pre_e_critical")
                    and base_action.intent in ("invest", "explore")
                    and (R_very_low or E_low)):
                    proposed_action = Action(intent="recover", strength="A")
                elif signal_type == "pre_x_critical" and base_action.intent == "invest":
                    proposed_action = Action(intent="defend", strength="A")
                else:
                    proposed_action = Action(intent=base_action.intent, strength="A")
        
        if proposed_action is None:
            return base_action, f"severity_below_chaos_adapted_threshold (sev={severity:.2f}, l3_events={l3_events})", None
        
        # ★ 案 M: NRMO Revalidation 経由
        # proposed_action が emergency_guard を通るか再評価
        revalidation = self.emergency_guard.apply(state, proposed_action)
        if revalidation.applied and revalidation.forced_action != proposed_action:
            # proposed_action 自体が guard で書き換えられる → 採用意味なし、base_action 維持
            self.stats["revalidation_rejected"] += 1
            return base_action, f"predictive_proposal_overridden_by_guard ({revalidation.rule_triggered})", None
        
        # 採用
        reason = f"{intervention_level}_{signal_type} (sev={severity:.2f}, l3={l3_events}, chaos_adapted)"
        record = {
            "signal_type": signal_type,
            "severity": severity,
            "intervention_level": intervention_level,
            "chaos_proxy_l3_events": l3_events,
            "context": {"O_high": O_high, "X_critical": X_critical,
                          "E_low": E_low, "R_very_low": R_very_low},
            "thresholds_used": {"strong": severity_strong, "light": severity_light},
            "from": f"{base_action.intent}/{base_action.strength}",
            "to": f"{proposed_action.intent}/{proposed_action.strength}",
            "revalidation_passed": True,
        }
        return proposed_action, reason, record
    
    # ============================================================
    # Helpers (v8.4.1 と同じ)
    # ============================================================
    
    def _generate_all_candidates(self) -> List[Action]:
        cands = []
        for intent in ["invest", "defend", "explore", "recover", "hold"]:
            for strength in ["A", "B", "C"]:
                cands.append(Action(intent=intent, strength=strength))
        return cands
    
    def _revalidate_proposed_action(self, state, proposed):
        revalidation = self.emergency_guard.apply(state, proposed)
        if revalidation.applied:
            return False, f"revalidation_failed: {revalidation.rule_triggered}"
        projected_delta = self._estimate_action_delta(proposed)
        breached, details = self.cumulative_risk.projected_breach_after(projected_delta)
        if breached:
            return False, f"cumulative_breach: {details['would_breaches'][:1]}"
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
                 context: Optional[Dict] = None) -> V843Decision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # Step 0: v7.1 base action
        base_action = self.v71.select_action(state)
        trace.add("v71_base", "pass", {
            "action": f"{base_action.intent}/{base_action.strength}",
        })
        
        # Step 1: ★ Predictive intervention (NEW: 早期介入)
        pre_signals = self._detect_pre_emergency_signals(state)
        pre_intervention_record = None
        current_action = base_action
        status = "ACCEPT"
        
        if pre_signals:
            self.stats["pre_emergency_signals_detected"] += 1
            for sig in pre_signals:
                if sig["type"] == "pre_r_emergency":
                    self.stats["pre_r_emergency_count"] += 1
                elif sig["type"] == "pre_x_critical":
                    self.stats["pre_x_critical_count"] += 1
                elif sig["type"] == "pre_e_critical":
                    self.stats["pre_e_critical_count"] += 1
            
            intervened_action, reason, record = self._apply_predictive_intervention(
                state, base_action, pre_signals
            )
            if record is not None:
                current_action = intervened_action
                pre_intervention_record = record
                self.stats["pre_emergency_interventions"] += 1
                status = "PRE_EMERGENCY_FORCED"
                self.intervention_log.append({
                    "decision_id": self.decision_counter,
                    "type": "pre_emergency",
                    **record,
                })
                trace.add("predictive_intervention", "intervened", record)
            else:
                trace.add("predictive_intervention", "below_threshold", {
                    "n_signals": len(pre_signals),
                    "max_severity": max(s["severity"] for s in pre_signals),
                })
        else:
            trace.add("predictive_intervention", "no_signals", {})
        
        # Step 2: EmergencyResourceGuard (v8.4.1 と同じ)
        emergency_decision = self.emergency_guard.apply(state, current_action)
        if emergency_decision.applied:
            current_action = emergency_decision.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            self.stats["emergency_triggered"] += 1
            self.intervention_log.append({
                "decision_id": self.decision_counter,
                "type": "emergency_guard",
                "rule": emergency_decision.rule_triggered,
                "to": f"{current_action.intent}/{current_action.strength}",
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
            trace.add("throttle_guard", "intervened", throttle_decision.to_dict())
        else:
            trace.add("throttle_guard", "pass", {"rule": "none"})
        
        # Step 4: ActivePattern
        ap_proposal = None
        if self.use_active_pattern and self.active_pattern is not None:
            all_candidates = self._generate_all_candidates()
            veto = VetoClassification.no_veto()
            ap_proposal = self.active_pattern.evaluate(
                state, all_candidates, current_action, veto
            )
            if ap_proposal.has_correction_proposal and ap_proposal.proposed_action:
                passed, reason = self._revalidate_proposed_action(
                    state, ap_proposal.proposed_action
                )
                if passed:
                    current_action = ap_proposal.proposed_action
                    if status == "ACCEPT":
                        status = "AP_INTERVENED"
                    self.stats["ap_intervened"] += 1
                else:
                    self.stats["revalidation_rejected"] += 1
            trace.add("active_pattern", "pass", {"score": ap_proposal.score})
        
        # Step 5: Histories
        if self.use_active_pattern and self.active_pattern is not None:
            self.active_pattern.update_history(state, current_action)
        self.throttle_guard.update_history(state, current_action)
        
        # MAPLayer update (post)
        self.map_layer.update(
            t=self.decision_counter,
            state=state,
            action_intent=current_action.intent,
            action_strength=current_action.strength,
            reward=0.0,
        )
        
        return V843Decision(
            action=current_action,
            status=status,
            confidence=0.7,
            trace=trace,
            base_action=base_action,
            emergency_guard=emergency_decision,
            throttle_guard=throttle_decision,
            active_pattern_proposal=ap_proposal,
            pre_emergency_signals=pre_signals,
            pre_emergency_intervention=pre_intervention_record,
            metadata={"stats": dict(self.stats)},
        )
    
    def update_reward(self, action, reward, state_before=None, state_after=None):
        self.v71.update_reward(action, reward)
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)
        if self.map_layer.l1:
            self.map_layer.l1[-1].reward = float(reward)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    
    print("=" * 70)
    print("V8.4.3 Engine Test (v8.4.1 + MAPLayer predictive intervention)")
    print("=" * 70)
    
    config = ChaosConfig.from_level("severe")
    world = ChaoticWorld(config, seed=42)
    
    rng_mgr = RNGManager(master_seed=42 + 900000)
    engine = V843Engine(rng_manager=rng_mgr,
                          use_active_pattern=True,
                          use_predictive=True)
    
    print("\n--- Pipeline trace (20 step) ---")
    for t in range(20):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = engine.decide(world.state)
        
        marker = ""
        if d.status == "PRE_EMERGENCY_FORCED": marker = " 🔮"
        elif d.status == "GUARD_FORCED": marker = " 🛡"
        elif d.status == "AP_INTERVENED": marker = " ⚡"
        
        sig_info = ""
        if d.pre_emergency_signals:
            n_sig = len(d.pre_emergency_signals)
            max_sev = max(s["severity"] for s in d.pre_emergency_signals)
            sig_info = f"  sigs={n_sig} max_sev={max_sev:.2f}"
        
        print(f"  t={t+1:2d}: base={d.base_action.intent}/{d.base_action.strength} "
              f"→ {d.action.intent}/{d.action.strength}{marker}  "
              f"R={world.state.R:.0f} X={world.state.X:.0f}{sig_info}")
        if d.pre_emergency_intervention:
            print(f"      [PRE] {d.pre_emergency_intervention['signal_type']} "
                  f"sev={d.pre_emergency_intervention['severity']:.2f}")
        if d.emergency_guard and d.emergency_guard.applied:
            print(f"      [EG] {d.emergency_guard.rule_triggered}")
        if d.throttle_guard and d.throttle_guard.applied:
            print(f"      [TH] {d.throttle_guard.rule_triggered}")
        
        reward, done, _ = world.step(d.action)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.update_reward(d.action, reward, sb, sa)
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    print(f"\n--- Stats ---")
    for k, v in engine.stats.items():
        print(f"  {k}: {v}")
    print(f"  Final score: {world.state.cumulative_score:.2f}")
    
    print("\n[V8.4.3 Engine 動作確認 完了 ✅]")
