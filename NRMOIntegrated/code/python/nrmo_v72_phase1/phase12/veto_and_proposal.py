"""
phase12/veto_and_proposal.py

v8.3 — VETO 分類 + PassivePattern 提案構造

Zarame さんの 5 つの保護要件への対応:
  1. PassivePattern に最終上書き権限を持たせない (proposal only)
  2. true_veto / soft_veto は NRMO Core 側が明示する
  3. 小さな可逆行動の累積リスクを見る
  4. opportunity_loss の Goodhart 化を防ぐ (警告ライト扱い)
  5. PassivePattern 後に NRMO Revalidation を必ず通す
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import deque


class VetoType(Enum):
    """NRMO Core が明示出力する veto 分類"""
    NO_VETO     = "no_veto"      # 通常通過
    SOFT_VETO   = "soft_veto"    # uncertainty/ambiguity 駆動 (PassivePattern 介入可)
    TRUE_VETO   = "true_veto"    # 不可逆破滅/吸収的失敗駆動 (絶対不可侵)


@dataclass
class VetoClassification:
    """NRMO Core が PassivePattern に提供する分類
    
    重要原則: PassivePattern はこれを「読むだけ」、自分で分類しない.
    """
    veto_type: VetoType
    reason: str = ""
    
    # true_veto の根拠 (一つでも True なら true_veto)
    irreversible_threat: bool = False
    absorbing_failure_risk: float = 0.0
    ruin_boundary_breach: bool = False
    legal_ethical_breach: bool = False
    
    # soft_veto の根拠
    uncertainty_driven: bool = False
    model_disagreement: bool = False
    ambiguous_risk: bool = False
    loss_aversion_driven: bool = False
    
    # PassivePattern への保証
    can_be_intervened: bool = False  # NRMO Core が許可した場合のみ True
    
    def to_dict(self) -> Dict:
        return {
            "veto_type": self.veto_type.value,
            "reason": self.reason,
            "irreversible_threat": self.irreversible_threat,
            "absorbing_failure_risk": self.absorbing_failure_risk,
            "ruin_boundary_breach": self.ruin_boundary_breach,
            "legal_ethical_breach": self.legal_ethical_breach,
            "uncertainty_driven": self.uncertainty_driven,
            "model_disagreement": self.model_disagreement,
            "ambiguous_risk": self.ambiguous_risk,
            "loss_aversion_driven": self.loss_aversion_driven,
            "can_be_intervened": self.can_be_intervened,
        }
    
    @classmethod
    def no_veto(cls) -> "VetoClassification":
        """通常通過"""
        return cls(veto_type=VetoType.NO_VETO, reason="No veto triggered",
                    can_be_intervened=False)
    
    @classmethod
    def soft_veto(cls, reason: str, **kwargs) -> "VetoClassification":
        """soft veto: PassivePattern 介入可能"""
        return cls(veto_type=VetoType.SOFT_VETO, reason=reason,
                    can_be_intervened=True, **kwargs)
    
    @classmethod
    def true_veto(cls, reason: str, **kwargs) -> "VetoClassification":
        """true veto: 絶対不可侵"""
        return cls(veto_type=VetoType.TRUE_VETO, reason=reason,
                    can_be_intervened=False, **kwargs)


@dataclass
class PassivePatternProposal:
    """PassivePattern は『提案』のみ. 決定はしない."""
    score: float                       # PassivePatternScore (0.0 - 1.0)
    level: str                          # "none" / "mild" / "active" / "severe"
    components: Dict[str, float] = field(default_factory=dict)
    
    # Gating condition (5 つの保護要件の運用)
    gating_passed: bool = False
    gating_details: Dict = field(default_factory=dict)
    
    # 提案 (上書きではない)
    has_correction_proposal: bool = False
    original_action: Optional[object] = None  # Action 型 (循環 import 回避のため object)
    proposed_action: Optional[object] = None
    proposal_reason: str = ""
    
    # 累積リスク警告 (追加要件 3)
    cumulative_risk_warning: bool = False
    cumulative_risk_details: Optional[Dict] = None
    
    # NRMO Revalidation 必須
    requires_nrmo_revalidation: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "score": self.score,
            "level": self.level,
            "components": self.components,
            "gating_passed": self.gating_passed,
            "gating_details": self.gating_details,
            "has_correction_proposal": self.has_correction_proposal,
            "original_action": (
                f"{self.original_action.intent}/{self.original_action.strength}"
                if self.original_action else None
            ),
            "proposed_action": (
                f"{self.proposed_action.intent}/{self.proposed_action.strength}"
                if self.proposed_action else None
            ),
            "proposal_reason": self.proposal_reason,
            "cumulative_risk_warning": self.cumulative_risk_warning,
            "cumulative_risk_details": self.cumulative_risk_details,
            "requires_nrmo_revalidation": self.requires_nrmo_revalidation,
        }


@dataclass
class RevalidationResult:
    """NRMO Core が PassivePattern proposal を再評価した結果"""
    proposal_accepted: bool
    final_action: object  # Action 型
    rejection_reason: Optional[str] = None
    rejected_because: Optional[str] = None
    partial_acceptance: bool = False
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "proposal_accepted": self.proposal_accepted,
            "final_action": (
                f"{self.final_action.intent}/{self.final_action.strength}"
                if self.final_action else None
            ),
            "rejection_reason": self.rejection_reason,
            "rejected_because": self.rejected_because,
            "partial_acceptance": self.partial_acceptance,
            "notes": self.notes,
        }


# ============================================================
# 累積リスクトラッカー (追加要件 3)
# ============================================================

class CumulativeRiskTracker:
    """小さな可逆 action の累積を追跡
    
    Zarame さん要件 3: 個別 invest/A は可逆でも、N 回連続すれば不可逆相当.
    """
    
    # 閾値 (v8.3 初期値, paired Phase 4 で調整予定)
    R_DRAIN_THRESHOLD = 30.0    # 累積 R 減少
    X_RISE_THRESHOLD = 25.0     # 累積 X 上昇
    E_DRAIN_THRESHOLD = 25.0    # 累積 E 減少
    G_DRAIN_THRESHOLD = 25.0    # 累積 G 減少
    
    def __init__(self, window: int = 20):
        self.window = window
        self.history: deque = deque(maxlen=window)  # state delta の履歴
    
    def add(self, prev_state, new_state):
        """state 遷移を記録"""
        delta = {
            "R": new_state.R - prev_state.R,
            "E": new_state.E - prev_state.E,
            "G": new_state.G - prev_state.G,
            "O": new_state.O - prev_state.O,
            "K": new_state.K - prev_state.K,
            "X": new_state.X - prev_state.X,
        }
        self.history.append(delta)
    
    def cumulative_deltas(self) -> Dict[str, float]:
        """窓内累積 delta"""
        result = {"R": 0.0, "E": 0.0, "G": 0.0, "O": 0.0, "K": 0.0, "X": 0.0}
        for d in self.history:
            for k in result:
                result[k] += d.get(k, 0.0)
        return result
    
    def check_threshold_breach(self) -> Tuple[bool, Dict]:
        """累積が不可逆相当の閾値を超えたか
        
        Returns: (breached, details)
        """
        cum = self.cumulative_deltas()
        breaches = []
        
        if cum["R"] < -self.R_DRAIN_THRESHOLD:
            breaches.append({
                "type": "cumulative_R_drain",
                "value": cum["R"],
                "threshold": -self.R_DRAIN_THRESHOLD,
            })
        if cum["X"] > self.X_RISE_THRESHOLD:
            breaches.append({
                "type": "cumulative_X_rise",
                "value": cum["X"],
                "threshold": self.X_RISE_THRESHOLD,
            })
        if cum["E"] < -self.E_DRAIN_THRESHOLD:
            breaches.append({
                "type": "cumulative_E_drain",
                "value": cum["E"],
                "threshold": -self.E_DRAIN_THRESHOLD,
            })
        if cum["G"] < -self.G_DRAIN_THRESHOLD:
            breaches.append({
                "type": "cumulative_G_drain",
                "value": cum["G"],
                "threshold": -self.G_DRAIN_THRESHOLD,
            })
        
        return len(breaches) > 0, {
            "breaches": breaches,
            "cumulative": cum,
            "n_steps_tracked": len(self.history),
        }


if __name__ == "__main__":
    # 動作確認
    print("=== VetoClassification ===")
    nv = VetoClassification.no_veto()
    sv = VetoClassification.soft_veto("Knightian uncertainty triggered",
                                         uncertainty_driven=True)
    tv = VetoClassification.true_veto("Absorbing failure imminent",
                                         irreversible_threat=True,
                                         absorbing_failure_risk=0.85)
    print(f"  no_veto:   intervene? {nv.can_be_intervened}")
    print(f"  soft_veto: intervene? {sv.can_be_intervened}")
    print(f"  true_veto: intervene? {tv.can_be_intervened}")
    
    print("\n=== CumulativeRiskTracker ===")
    class MockState:
        def __init__(self, R, E, G, O, K, X):
            self.R, self.E, self.G, self.O, self.K, self.X = R, E, G, O, K, X
    
    tracker = CumulativeRiskTracker(window=20)
    s0 = MockState(60, 70, 70, 50, 60, 20)
    # 10 step で R が大きく下がる
    for i in range(10):
        s1 = MockState(s0.R - 4, s0.E - 1, s0.G - 1, s0.O, s0.K, s0.X + 1)
        tracker.add(s0, s1)
        s0 = s1
    
    breached, details = tracker.check_threshold_breach()
    print(f"After 10 step (R from 60 → 20): breached={breached}")
    print(f"  cumulative: {details['cumulative']}")
    if details["breaches"]:
        for b in details["breaches"]:
            print(f"  ✗ {b['type']}: value={b['value']:.1f}, "
                  f"threshold={b['threshold']:.1f}")
    
    print("\n[veto_and_proposal.py 動作確認 完了 ✅]")
