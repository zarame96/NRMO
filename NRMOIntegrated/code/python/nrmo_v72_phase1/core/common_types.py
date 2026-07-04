"""
common_types.py — NRMO Integrated v7.2 OS/SOP 共通データ型。
権限分離の不変条件を型レベルでも明確にするための最小・監査可能な型集合。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal

DecisionStatus = Literal["PASS", "HOLD", "REJECT", "ESCALATE"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
ModeName = Literal["NORMAL", "VENTURE", "MISSION", "SAFE", "TRAINING", "HARE"]
ActionPermission = Literal["ALLOW", "HOLD", "BLOCK"]


@dataclass
class NRMOContext:
    domain: str
    mode: ModeName = "NORMAL"
    user_goal: Optional[str] = None
    vision_reference: Optional[str] = None        # Vision は人間側。NRMO は参照のみ。
    state: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateAction:
    action_id: str
    label: str
    domain: str
    payload: Dict[str, Any] = field(default_factory=dict)
    reversibility: float = 1.0      # 1.0 = 完全可逆, 0.0 = 不可逆
    exposure: float = 0.0           # 0..1 露出/賭け金
    expected_forward: float = 0.0   # 前進期待 (Engine が評価; ruin は混ぜない)
    time_horizon: str = "short"     # short / mid / long / ultra
    tags: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.action_id)

    def __eq__(self, other):
        return isinstance(other, CandidateAction) and other.action_id == self.action_id


@dataclass
class GateResult:
    status: DecisionStatus
    reason: str
    score: float = 0.0
    flags: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProposalSet:
    choices: List[CandidateAction]
    hold_option: Optional[CandidateAction] = None
    exit_option: Optional[CandidateAction] = None
    rationale: str = ""
    autonomy_note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


def hold_action(domain: str) -> CandidateAction:
    return CandidateAction("hold", "Hold / wait", domain,
                           reversibility=1.0, exposure=0.0, tags=["hold"])

def exit_action(domain: str) -> CandidateAction:
    return CandidateAction("exit", "Exit / withdraw", domain,
                           reversibility=1.0, exposure=0.0, tags=["exit"])
