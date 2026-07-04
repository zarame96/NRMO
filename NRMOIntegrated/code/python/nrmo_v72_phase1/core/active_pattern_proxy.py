"""
core/active_pattern_proxy.py

ActivePattern Proxy Layer

V8.3 のデバッグで判明: v8.3 の真の問題は「aggressive 暴走」.
R が枯渇するまで invest/C, explore/C を連発する.

PassivePattern が「動かなさすぎ」を検出するなら、
ActivePattern は「動きすぎ」を検出する.

役割:
  - resource_depletion: R 急減の検出
  - aggressive_streak: 大 strength action 連発
  - opportunity_overcommit: 機会窓に過剰投入
  - reckless_pursuit: state risk を無視した攻撃

非役割:
  - VETO の上書き (NRMO Revalidation 必須)
  - true_veto への介入
  - StrongEngine 候補の直接変更
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from veto_classification import VetoClassification, VetoType


# ============================================================
# Components
# ============================================================

@dataclass
class ActivePatternComponents:
    """ActivePattern の構成要素"""
    resource_depletion: float = 0.0       # R 急減
    aggressive_streak: float = 0.0         # 強 action 連発
    opportunity_overcommit: float = 0.0    # 機会過剰投入
    reckless_pursuit: float = 0.0          # state risk 無視
    state_deterioration: float = 0.0       # 状態悪化トレンド
    legitimate_aggression: float = 0.0     # 正当な攻め (減算)
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "resource_depletion": self.resource_depletion,
            "aggressive_streak": self.aggressive_streak,
            "opportunity_overcommit": self.opportunity_overcommit,
            "reckless_pursuit": self.reckless_pursuit,
            "state_deterioration": self.state_deterioration,
            "legitimate_aggression": self.legitimate_aggression,
        }


@dataclass
class ActivePatternProposal:
    """ActivePattern の提案 (上書きではない)"""
    score: float                              # 0.0 - 1.0
    level: str                                # "none" / "mild" / "active" / "severe"
    components: ActivePatternComponents
    
    gating_passed: bool
    gating_details: Dict
    
    veto_type: VetoType
    can_intervene: bool
    
    has_correction_proposal: bool
    original_action: Optional["Action"] = None
    proposed_action: Optional["Action"] = None
    proposal_reason: str = ""
    
    requires_nrmo_revalidation: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "score": self.score,
            "level": self.level,
            "components": self.components.to_dict(),
            "gating_passed": self.gating_passed,
            "veto_type": self.veto_type.value,
            "has_correction_proposal": self.has_correction_proposal,
            "original_action": (f"{self.original_action.intent}/{self.original_action.strength}"
                                if self.original_action else None),
            "proposed_action": (f"{self.proposed_action.intent}/{self.proposed_action.strength}"
                                if self.proposed_action else None),
            "proposal_reason": self.proposal_reason,
        }


# ============================================================
# ActivePatternProxy
# ============================================================

class ActivePatternProxy:
    """ActivePattern Proxy Layer"""
    
    WEIGHTS = {
        "resource_depletion": 0.30,
        "aggressive_streak": 0.25,
        "opportunity_overcommit": 0.15,
        "reckless_pursuit": 0.20,
        "state_deterioration": 0.20,
        "legitimate_aggression": -0.30,  # 減算
    }
    
    LEVEL_THRESHOLDS = {
        "none":   0.30,
        "mild":   0.50,
        "active": 0.70,
        # >= 0.70 は severe
    }
    
    INTERVENTION_THRESHOLD = 0.35  # この score 以上で介入提案 (v8.4 で下げる)
    
    def __init__(self):
        from collections import deque
        self.action_history: deque = deque(maxlen=10)
        self.R_history: deque = deque(maxlen=10)
        self.X_history: deque = deque(maxlen=10)
    
    def update_history(self, state, action):
        """毎 step 履歴更新"""
        self.action_history.append({
            "intent": action.intent if action else "none",
            "strength": action.strength if action else "A",
        })
        self.R_history.append(float(state.R))
        self.X_history.append(float(state.X))
    
    # ============================================================
    # Component computation
    # ============================================================
    
    def _compute_resource_depletion(self, state) -> float:
        """R 急減の検出"""
        if len(self.R_history) < 3:
            return 0.0
        
        R_now = self.R_history[-1]
        R_earlier = self.R_history[0]
        decline = R_earlier - R_now
        
        # R が急減 + 残り少ない
        if R_now < 30 and decline > 15:
            return 1.0
        if R_now < 40 and decline > 20:
            return 0.85
        if R_now < 25:
            return 0.9
        if decline > 25:
            return 0.7
        if decline > 15:
            return 0.4
        return 0.0
    
    def _compute_aggressive_streak(self, state, final_action) -> float:
        """大 strength action 連発"""
        if not self.action_history or final_action is None:
            return 0.0
        
        # 直近 N step の (intent, strength) 集計
        recent = list(self.action_history)[-7:]
        recent.append({
            "intent": final_action.intent,
            "strength": final_action.strength,
        })
        
        aggressive_count = 0
        for a in recent:
            if a["strength"] in ("B", "C"):
                aggressive_count += 1
            if a["intent"] in ("invest", "explore") and a["strength"] == "C":
                aggressive_count += 1  # double-count for C
        
        ratio = aggressive_count / (len(recent) * 1.5)  # max ~ 1.0
        return min(1.0, ratio)
    
    def _compute_opportunity_overcommit(self, state, final_action) -> float:
        """機会窓に過剰投入"""
        if final_action is None:
            return 0.0
        
        # O 高い + R 低い + invest/explore C → overcommit
        if (state.O > 70 and state.R < 35 
            and final_action.intent in ("invest", "explore")
            and final_action.strength == "C"):
            return 0.9
        
        if (state.O > 60 and state.R < 30
            and final_action.intent in ("invest", "explore")
            and final_action.strength in ("B", "C")):
            return 0.6
        
        return 0.0
    
    def _compute_reckless_pursuit(self, state, final_action) -> float:
        """state risk を無視した攻撃"""
        if final_action is None:
            return 0.0
        
        # X 高い + invest/explore C → 無謀
        if state.X > 50 and final_action.intent in ("invest", "explore"):
            if final_action.strength == "C":
                return min(1.0, (state.X - 50) / 30)
            if final_action.strength == "B":
                return min(0.6, (state.X - 50) / 40)
        
        # E 低い + aggressive
        if state.E < 35 and final_action.intent in ("invest", "explore"):
            if final_action.strength == "C":
                return min(1.0, (35 - state.E) / 35 + 0.3)
            if final_action.strength == "B":
                return min(0.6, (35 - state.E) / 50)
        
        return 0.0
    
    def _compute_state_deterioration(self, state) -> float:
        """状態悪化トレンド"""
        if len(self.R_history) < 4:
            return 0.0
        
        # R が単調減少 + X が単調増加 を見る
        R_decline = self.R_history[0] - self.R_history[-1]
        X_rise = self.X_history[-1] - self.X_history[0]
        
        score = 0.0
        if R_decline > 10:
            score += min(0.6, R_decline / 30)
        if X_rise > 10:
            score += min(0.4, X_rise / 30)
        
        return min(1.0, score)
    
    def _compute_legitimate_aggression(self, state, final_action) -> float:
        """正当な攻め (減算用)"""
        if final_action is None:
            return 0.0
        
        legitimate = 0.0
        
        # R 十分 + E 十分 + X 低い + invest/explore は legitimate
        if (state.R > 60 and state.E > 60 and state.X < 30
            and final_action.intent in ("invest", "explore")):
            legitimate = 0.7
        
        # 大きな機会 (O > 80) + R 余裕 (> 50) で aggressive
        if state.O > 80 and state.R > 50 and final_action.intent == "invest":
            legitimate = max(legitimate, 0.5)
        
        return min(1.0, legitimate)
    
    # ============================================================
    # Gating
    # ============================================================
    
    def _check_gating(self, state, candidates, veto_classification) -> Tuple[bool, Dict]:
        """ActivePattern 介入の許可条件
        
        - 縮小 action 候補が存在
        - true_veto ではない
        - 真に冒険的な action が選ばれている (現 final_action が aggressive)
        """
        smaller_exists = any(
            c.strength == "A" 
            for c in (candidates or [])
        )
        
        is_true_veto = veto_classification.veto_type == VetoType.TRUE_VETO
        
        details = {
            "smaller_exists": smaller_exists,
            "is_true_veto": is_true_veto,
        }
        
        gating = smaller_exists and not is_true_veto
        return gating, details
    
    # ============================================================
    # Correction proposal
    # ============================================================
    
    def _propose_correction(self, state, final_action,
                              veto_classification) -> Tuple[Optional["Action"], str]:
        """変換ルール
        
        Rule A1: invest/C → invest/A or defend/A (state による)
        Rule A2: explore/C → explore/A or recover/A
        Rule A3: 連続 aggressive → recover/A (resource 回復)
        """
        from world_models import Action
        
        if final_action is None:
            return None, "no_action"
        
        if veto_classification.veto_type == VetoType.TRUE_VETO:
            return None, "true_veto_protected"
        
        intent = final_action.intent
        strength = final_action.strength
        
        # Rule A1: invest/C
        if intent == "invest" and strength == "C":
            if state.R < 30:
                # R 危機的 → recover に切替
                return Action(intent="recover", strength="A"), \
                       "RuleA1: invest/C with low R → recover/A"
            if state.X > 50:
                # X 高い → defend
                return Action(intent="defend", strength="A"), \
                       "RuleA1: invest/C with high X → defend/A"
            # 通常 → 縮小
            return Action(intent="invest", strength="A"), \
                   "RuleA1: invest/C downsize → invest/A"
        
        # Rule A2: explore/C
        if intent == "explore" and strength == "C":
            if state.R < 30:
                return Action(intent="recover", strength="A"), \
                       "RuleA2: explore/C with low R → recover/A"
            return Action(intent="explore", strength="A"), \
                   "RuleA2: explore/C downsize → explore/A"
        
        # Rule A3: 連続 aggressive (resource 枯渇)
        if (intent in ("invest", "explore") and strength in ("B", "C")
            and state.R < 35):
            return Action(intent="recover", strength="A"), \
                   "RuleA3: continuous aggressive + low R → recover/A"
        
        # Rule A4: invest/B with high reckless score
        if intent == "invest" and strength == "B" and state.X > 60:
            return Action(intent="defend", strength="A"), \
                   "RuleA4: invest/B at high X → defend/A"
        
        return None, "no_rule_matched"
    
    # ============================================================
    # Main evaluate
    # ============================================================
    
    def evaluate(self, state, candidates: List, final_action,
                  veto_classification: VetoClassification
                  ) -> ActivePatternProposal:
        """主評価"""
        components = ActivePatternComponents(
            resource_depletion=self._compute_resource_depletion(state),
            aggressive_streak=self._compute_aggressive_streak(state, final_action),
            opportunity_overcommit=self._compute_opportunity_overcommit(state, final_action),
            reckless_pursuit=self._compute_reckless_pursuit(state, final_action),
            state_deterioration=self._compute_state_deterioration(state),
            legitimate_aggression=self._compute_legitimate_aggression(state, final_action),
        )
        
        # Score
        score = 0.0
        for key, weight in self.WEIGHTS.items():
            val = getattr(components, key, 0.0)
            score += val * weight
        score = max(0.0, min(1.0, score))
        
        # Level
        if score < self.LEVEL_THRESHOLDS["none"]:
            level = "none"
        elif score < self.LEVEL_THRESHOLDS["mild"]:
            level = "mild"
        elif score < self.LEVEL_THRESHOLDS["active"]:
            level = "active"
        else:
            level = "severe"
        
        # Gating
        gating_passed, gating_details = self._check_gating(
            state, candidates, veto_classification
        )
        
        # 補正提案
        proposed_action = None
        proposal_reason = ""
        has_proposal = False
        
        if score >= self.INTERVENTION_THRESHOLD and gating_passed:
            proposed_action, proposal_reason = self._propose_correction(
                state, final_action, veto_classification
            )
            has_proposal = proposed_action is not None
        elif score >= self.INTERVENTION_THRESHOLD and not gating_passed:
            proposal_reason = f"score_high_but_gating_failed: {gating_details}"
        else:
            proposal_reason = f"score_below_threshold ({score:.2f})"
        
        return ActivePatternProposal(
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
            requires_nrmo_revalidation=True,
        )
