"""
core/passive_pattern_proxy.py

PassivePattern Proxy Layer (v8.3)

役割:
  - 受動的破壊の検出 (機会損失、可逆行動抑圧、停滞、過剰観察、恐怖駆動 hold)
  - 縮小可逆実行への変換「提案」 (上書き権限なし)
  
非役割:
  - VETO の上書き
  - true_veto の分類 (NRMO Core が分類)
  - 最終決定 (NRMO Revalidation が決定)
  
仕様:
  - PassivePatternScore = 加重和
  - Gating condition で発火制限
  - 提案は always requires_nrmo_revalidation=True
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np

from veto_classification import VetoClassification, VetoType


# ============================================================
# Components
# ============================================================

@dataclass
class PassivePatternComponents:
    """5 要素 + legitimate_waiting"""
    opportunity_loss: float = 0.0
    reversible_action_suppression: float = 0.0
    stagnation_duration: float = 0.0
    over_observation: float = 0.0
    fear_based_hold: float = 0.0
    legitimate_waiting: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "opportunity_loss": self.opportunity_loss,
            "reversible_action_suppression": self.reversible_action_suppression,
            "stagnation_duration": self.stagnation_duration,
            "over_observation": self.over_observation,
            "fear_based_hold": self.fear_based_hold,
            "legitimate_waiting": self.legitimate_waiting,
        }


@dataclass
class PassivePatternProposal:
    """PassivePattern の提案 (上書きではない)"""
    score: float                              # 0.0 - 1.0
    level: str                                # "none" / "mild" / "active" / "severe"
    components: PassivePatternComponents
    
    # Gating result
    gating_passed: bool
    gating_details: Dict
    
    # Veto context (NRMO Core から受領)
    veto_type: VetoType
    can_intervene: bool
    
    # 提案 (上書きではない)
    has_correction_proposal: bool
    original_action: Optional["Action"] = None
    proposed_action: Optional["Action"] = None
    proposal_reason: str = ""
    
    # 累積リスク警告
    cumulative_risk_warning: bool = False
    cumulative_risk_details: Optional[Dict] = None
    
    # 必ず NRMO Revalidation
    requires_nrmo_revalidation: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "score": self.score,
            "level": self.level,
            "components": self.components.to_dict(),
            "gating_passed": self.gating_passed,
            "gating_details": self.gating_details,
            "veto_type": self.veto_type.value,
            "can_intervene": self.can_intervene,
            "has_correction_proposal": self.has_correction_proposal,
            "original_action": (f"{self.original_action.intent}/{self.original_action.strength}"
                                if self.original_action else None),
            "proposed_action": (f"{self.proposed_action.intent}/{self.proposed_action.strength}"
                                if self.proposed_action else None),
            "proposal_reason": self.proposal_reason,
            "cumulative_risk_warning": self.cumulative_risk_warning,
            "cumulative_risk_details": self.cumulative_risk_details,
            "requires_nrmo_revalidation": self.requires_nrmo_revalidation,
        }


# ============================================================
# PassivePatternProxy
# ============================================================

class PassivePatternProxy:
    """PassivePattern Proxy Layer
    
    Pre-check と Post-check の両方で呼ばれる.
    """
    
    # スコア重み
    WEIGHTS = {
        "opportunity_loss": 0.25,
        "reversible_action_suppression": 0.25,
        "stagnation_duration": 0.20,
        "over_observation": 0.15,
        "fear_based_hold": 0.15,
        "legitimate_waiting": -0.25,  # 減算
    }
    
    # Level 閾値
    LEVEL_THRESHOLDS = {
        "none": 0.30,
        "mild": 0.55,
        "active": 0.75,
        # >= 0.75 は "severe"
    }
    
    # Gating 閾値
    RUIN_PROXIMITY_CRITICAL = 0.85  # X / 100 がこれ以上なら critical
    LEGITIMATE_WAITING_MAX_DURATION = 15  # legitimate も期限あり
    
    def __init__(self):
        # 履歴管理
        self.score_history: deque = deque(maxlen=50)
        self.action_history: deque = deque(maxlen=30)
        self.state_R_history: deque = deque(maxlen=20)
        self.state_O_history: deque = deque(maxlen=20)
        self.cumulative_score_history: deque = deque(maxlen=20)
        self.explore_streak: int = 0
        self.legitimate_waiting_streak: int = 0
    
    def update_history(self, state, action, cumulative_score: float):
        """1 step ごとに履歴を update (V8Engine から呼ぶ)"""
        self.action_history.append({
            "intent": action.intent if action else "none",
            "strength": action.strength if action else "A",
        })
        self.state_R_history.append(float(state.R))
        self.state_O_history.append(float(state.O))
        self.cumulative_score_history.append(float(cumulative_score))
        
        # explore 連発カウント
        if action and action.intent == "explore":
            self.explore_streak += 1
        else:
            self.explore_streak = 0
    
    # ============================================================
    # 各 component の計算
    # ============================================================
    
    def _compute_opportunity_loss(self, state, candidates: List,
                                    final_action) -> float:
        """opportunity_loss
        
        条件:
          O >= 65 (機会あり)
          E >= 45 (体力ある)
          X <= 65 (破綻リスク極端でない)
          かつ final_action が hold / over-defend / low-impact explore
        """
        O_norm = state.O / 100
        E_norm = state.E / 100
        X_norm = state.X / 100
        
        if not (O_norm >= 0.65 and E_norm >= 0.45 and X_norm <= 0.65):
            return 0.0
        
        if final_action is None:
            return 0.5
        
        # 受動的 action か
        intent = final_action.intent
        strength = final_action.strength
        
        passive_actions = {
            ("hold", "A"): 0.8, ("hold", "B"): 0.85, ("hold", "C"): 0.9,
            ("defend", "C"): 0.6, ("defend", "B"): 0.4,
            ("explore", "A"): 0.3,  # low-impact explore
        }
        
        return passive_actions.get((intent, strength), 0.0)
    
    def _compute_reversible_action_suppression(self, candidates: List,
                                                  final_action) -> float:
        """候補集合に small reversible action があったのに採用されなかったか"""
        if not candidates or final_action is None:
            return 0.0
        
        reversible_candidates = [
            c for c in candidates
            if c.strength == "A" and c.intent in ("invest", "explore", "engage")
        ]
        
        if not reversible_candidates:
            return 0.0
        
        # final_action がそれら可逆 small action か
        if final_action.strength == "A" and final_action.intent in (
            "invest", "explore", "engage"
        ):
            return 0.0  # 採用された
        
        # final_action が hold / no-op / heavy defend
        if final_action.intent == "hold":
            return 0.85
        if final_action.intent == "defend" and final_action.strength in ("B", "C"):
            return 0.65
        
        return 0.3
    
    def _compute_stagnation_duration(self, state) -> float:
        """cumulative_score と state 改善の停滞期間"""
        if len(self.cumulative_score_history) < 5:
            return 0.0
        
        # 直近 N step の score 差分
        scores = list(self.cumulative_score_history)
        recent_n = min(10, len(scores) - 1)
        deltas = [scores[i+1] - scores[i] 
                   for i in range(len(scores) - recent_n - 1, len(scores) - 1)]
        avg_delta = float(np.mean(deltas)) if deltas else 0
        
        # 停滞度
        if avg_delta < 0.05:
            stagnation = min(1.0, (0.05 - avg_delta) / 0.10)
        else:
            stagnation = 0.0
        
        # state 改善停滞
        if len(self.state_O_history) >= 5:
            O_trend = self.state_O_history[-1] - self.state_O_history[-5]
            if O_trend < 0 and state.X > 60:
                stagnation = min(1.0, stagnation + 0.2)
        
        return stagnation
    
    def _compute_over_observation(self) -> float:
        """explore 連発 + 実行に移らない"""
        if self.explore_streak < 3:
            return 0.0
        
        return min(1.0, (self.explore_streak - 2) * 0.2)
    
    def _compute_fear_based_hold(self, state, final_action,
                                    veto_classification: VetoClassification) -> float:
        """恐怖駆動 hold の判定
        
        条件:
          hold の理由が ruin_boundary ではなく、
          uncertainty / ambiguous_risk / loss_aversion 起因
          かつ small reversible action が残っている
        """
        if final_action is None or final_action.intent != "hold":
            return 0.0
        
        # NRMO Core が ruin_boundary 起因と分類していれば fear ではない
        if veto_classification.ruin_boundary_breach:
            return 0.0
        if veto_classification.irreversible_threat:
            return 0.0
        
        fear_score = 0.0
        if veto_classification.uncertainty_driven:
            fear_score += 0.4
        if veto_classification.ambiguous_risk:
            fear_score += 0.3
        if veto_classification.loss_aversion_driven:
            fear_score += 0.4
        if veto_classification.model_disagreement:
            fear_score += 0.2
        
        return min(1.0, fear_score)
    
    def _compute_legitimate_waiting(self, state, final_action) -> float:
        """legitimate な保留
        
        - E <= 30 で recover
        - X >= 75 で defend
        - high irreversible risk で hold
        """
        if final_action is None:
            return 0.0
        
        legitimate = 0.0
        
        if state.E <= 30 and final_action.intent == "recover":
            legitimate += 0.7
        if state.X >= 75 and final_action.intent == "defend":
            legitimate += 0.7
        if state.X >= 90 and final_action.intent == "hold":
            legitimate += 0.5
        
        # legitimate waiting が長期化したら減衰 (要件)
        if legitimate > 0:
            self.legitimate_waiting_streak += 1
            if self.legitimate_waiting_streak > self.LEGITIMATE_WAITING_MAX_DURATION:
                # 長期化 → legitimate でなくなる
                legitimate *= max(0.0, 1 - (self.legitimate_waiting_streak - 
                                              self.LEGITIMATE_WAITING_MAX_DURATION) * 0.1)
        else:
            self.legitimate_waiting_streak = 0
        
        return min(1.0, legitimate)
    
    # ============================================================
    # Gating Condition
    # ============================================================
    
    def _check_gating(self, state, candidates: List,
                       veto_classification: VetoClassification,
                       cumulative_risk_breached: bool) -> Tuple[bool, Dict]:
        """PassivePattern 介入を許可する条件
        
        全て満たす必要あり:
          1. small_reversible_action_exists
          2. true_veto == false
          3. ruin_proximity < critical_threshold
          4. cumulative_risk が breach していない
        """
        small_reversible_exists = any(
            c.strength == "A" and c.intent in ("invest", "explore", "engage")
            for c in (candidates or [])
        )
        
        is_true_veto = veto_classification.veto_type == VetoType.TRUE_VETO
        
        ruin_proximity = state.X / 100
        below_critical = ruin_proximity < self.RUIN_PROXIMITY_CRITICAL
        
        cumulative_ok = not cumulative_risk_breached
        
        details = {
            "small_reversible_exists": small_reversible_exists,
            "is_true_veto": is_true_veto,
            "ruin_proximity": ruin_proximity,
            "below_critical": below_critical,
            "cumulative_ok": cumulative_ok,
        }
        
        gating_passed = (
            small_reversible_exists
            and not is_true_veto
            and below_critical
            and cumulative_ok
        )
        return gating_passed, details
    
    # ============================================================
    # Correction proposal (上書きではない)
    # ============================================================
    
    def _propose_correction(self, state, candidates: List,
                              final_action,
                              veto_classification: VetoClassification
                              ) -> Tuple[Optional["Action"], str]:
        """変換ルール (確定版)
        
        Rule 1: hold/no-op
          if small reversible action exists:
              uncertainty high + info value remains → explore/A
              O high + E sufficient + X moderate → invest/A
              E low → recover/A
              else → maintain/A (hold/A のまま)
              
        Rule 2: over-defend
          X below critical + opportunity suppressed → defend/A
        
        Rule 3: oversized aggression
          invest/C with high X → invest/A or explore/A (X 段階で分岐)
        
        Rule 4: soft_veto with reversible
          → minimum reversible action
        
        Rule 5: true_veto → never override
        """
        from world_models import Action
        
        if final_action is None:
            return None, "no_action_to_correct"
        
        # Rule 5: true_veto は触らない (gating で既に弾かれているはずだが念のため)
        if veto_classification.veto_type == VetoType.TRUE_VETO:
            return None, "true_veto_protected"
        
        intent = final_action.intent
        strength = final_action.strength
        O = state.O
        E = state.E
        X = state.X
        
        # Rule 1: hold/no-op
        if intent == "hold":
            # 高 uncertainty (small reversible exists 前提)
            if veto_classification.uncertainty_driven and E >= 45:
                return Action(intent="explore", strength="A"), \
                       "Rule1_uncertainty_high_explore"
            
            if O >= 65 and E >= 50 and X <= 60:
                return Action(intent="invest", strength="A"), \
                       "Rule1_opportunity_invest"
            
            if E < 40:
                return Action(intent="recover", strength="A"), \
                       "Rule1_E_low_recover"
            
            return None, "Rule1_no_appropriate_alternative"
        
        # Rule 2: over-defend
        if intent == "defend" and strength in ("B", "C") and X < 75:
            return Action(intent="defend", strength="A"), \
                   "Rule2_over_defend_mitigated"
        
        # Rule 3: oversized aggression
        if intent == "invest" and strength == "C":
            if 60 <= X < 75:
                return Action(intent="invest", strength="A"), \
                       "Rule3_invest_C_moderate_X_downsize"
            if 75 <= X < 90:
                return Action(intent="explore", strength="A"), \
                       "Rule3_invest_C_high_X_to_explore"
            # X >= 90 は true_veto candidate (NRMO Core で扱われるべき)
        
        return None, "no_rule_matched"
    
    # ============================================================
    # Main evaluation
    # ============================================================
    
    def evaluate(self, state, candidates: List, final_action,
                  veto_classification: VetoClassification,
                  cumulative_risk_breached: bool = False,
                  cumulative_risk_details: Optional[Dict] = None
                  ) -> PassivePatternProposal:
        """主評価関数
        
        Returns: PassivePatternProposal (上書きではない、提案のみ)
        """
        # Components 計算
        components = PassivePatternComponents(
            opportunity_loss=self._compute_opportunity_loss(state, candidates, final_action),
            reversible_action_suppression=self._compute_reversible_action_suppression(
                candidates, final_action),
            stagnation_duration=self._compute_stagnation_duration(state),
            over_observation=self._compute_over_observation(),
            fear_based_hold=self._compute_fear_based_hold(state, final_action, 
                                                           veto_classification),
            legitimate_waiting=self._compute_legitimate_waiting(state, final_action),
        )
        
        # Score 計算
        score = 0.0
        for key, weight in self.WEIGHTS.items():
            val = getattr(components, key, 0.0)
            score += val * weight
        score = max(0.0, min(1.0, score))
        
        # Level 判定
        if score < self.LEVEL_THRESHOLDS["none"]:
            level = "none"
        elif score < self.LEVEL_THRESHOLDS["mild"]:
            level = "mild"
        elif score < self.LEVEL_THRESHOLDS["active"]:
            level = "active"
        else:
            level = "severe"
        
        # Gating check
        gating_passed, gating_details = self._check_gating(
            state, candidates, veto_classification, cumulative_risk_breached
        )
        
        # 補正提案 (score >= 0.55 かつ gating passed)
        proposed_action = None
        proposal_reason = ""
        has_proposal = False
        
        if score >= 0.55 and gating_passed:
            proposed_action, proposal_reason = self._propose_correction(
                state, candidates, final_action, veto_classification
            )
            has_proposal = proposed_action is not None
        elif score >= 0.55 and not gating_passed:
            proposal_reason = f"score_high_but_gating_failed: {gating_details}"
        else:
            proposal_reason = f"score_below_threshold ({score:.2f})"
        
        return PassivePatternProposal(
            score=score,
            level=level,
            components=components,
            gating_passed=gating_passed,
            gating_details=gating_details,
            veto_type=veto_classification.veto_type,
            can_intervene=veto_classification.can_be_intervened,
            has_correction_proposal=has_proposal,
            original_action=final_action,
            proposed_action=proposed_action,
            proposal_reason=proposal_reason,
            cumulative_risk_warning=cumulative_risk_breached,
            cumulative_risk_details=cumulative_risk_details,
            requires_nrmo_revalidation=True,
        )
