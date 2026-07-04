"""
core/veto_classification.py

NRMO Core が PassivePattern に提供する veto 分類.
PassivePattern が分類するのではない. NRMO Core が明示出力する.

要件:
  - true_veto: 不可逆破滅、絶対上書き不可
  - soft_veto: 恐怖・不確実性駆動、PassivePattern 介入可
  - no_veto: 通常承認
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class VetoType(Enum):
    TRUE_VETO = "true_veto"      # 上書き禁止
    SOFT_VETO = "soft_veto"      # PassivePattern 介入可
    NO_VETO   = "no_veto"        # 通常承認


@dataclass
class VetoClassification:
    """NRMO Core が出力する veto 分類"""
    veto_type: VetoType
    reason: str
    
    # true_veto の根拠 (該当時 True)
    irreversible_threat: bool = False
    absorbing_failure_risk: float = 0.0  # 0-1
    ruin_boundary_breach: bool = False
    legal_ethical_breach: bool = False
    
    # soft_veto の根拠 (該当時 True)
    uncertainty_driven: bool = False
    model_disagreement: bool = False
    ambiguous_risk: bool = False
    loss_aversion_driven: bool = False
    
    # PassivePattern への保証 (NRMO Core が判断)
    can_be_intervened: bool = False
    
    # 反証可能性
    falsifiable_evidence: List[str] = field(default_factory=list)
    
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
            "falsifiable_evidence": self.falsifiable_evidence,
        }
    
    @classmethod
    def true_veto(cls, reason: str, **kwargs) -> "VetoClassification":
        return cls(
            veto_type=VetoType.TRUE_VETO,
            reason=reason,
            can_be_intervened=False,
            **kwargs,
        )
    
    @classmethod
    def soft_veto(cls, reason: str, **kwargs) -> "VetoClassification":
        return cls(
            veto_type=VetoType.SOFT_VETO,
            reason=reason,
            can_be_intervened=True,
            **kwargs,
        )
    
    @classmethod
    def no_veto(cls) -> "VetoClassification":
        return cls(
            veto_type=VetoType.NO_VETO,
            reason="approved",
            can_be_intervened=False,  # 介入の必要なし
        )
