"""
aallowed.py — A_allowed 許可行動辞書。
mode/domain 別の行動上限・カテゴリ・必要チェックを定義する辞書。
権限: NRMO veto ではない。admissible を override できない。許可カテゴリの filter のみ。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from common_types import NRMOContext, CandidateAction, GateResult

CATEGORIES = ["observe", "log", "draft", "simulate", "probe",
              "small_reversible_action", "bounded_experiment", "relationship_message",
              "investment_order", "work_intervention", "public_commitment",
              "irreversible_commitment", "shutdown", "exit"]


@dataclass
class AallowedRule:
    category: str
    max_exposure: float = 1.0
    max_irreversibility: float = 1.0      # 1.0=可逆のみ許可, 0.0=不可逆も可
    required_checks: List[str] = field(default_factory=list)
    allowed_modes: List[str] = field(default_factory=list)
    prohibited_tags: List[str] = field(default_factory=list)


def _default_rules() -> List[AallowedRule]:
    R = AallowedRule
    return [
        R("observe", 1.0, 0.0, [], ["NORMAL","VENTURE","MISSION","SAFE","TRAINING","HARE"]),
        R("log", 1.0, 0.0, [], ["NORMAL","VENTURE","MISSION","SAFE","TRAINING","HARE"]),
        R("draft", 1.0, 0.0, [], ["NORMAL","VENTURE","MISSION","SAFE","TRAINING","HARE"]),
        R("simulate", 1.0, 0.0, [], ["NORMAL","VENTURE","MISSION","TRAINING"]),
        R("probe", 0.4, 0.3, [], ["NORMAL","VENTURE","MISSION"]),
        R("small_reversible_action", 0.5, 0.3, [], ["NORMAL","VENTURE","MISSION","HARE"]),
        R("bounded_experiment", 0.6, 0.4, ["exit_condition"], ["VENTURE","MISSION"]),
        R("relationship_message", 0.5, 0.5, ["emotional_filter"], ["NORMAL","VENTURE","MISSION","HARE"]),
        R("investment_order", 0.6, 0.6, ["position_limit","liquidity","fatigue_flag"], ["NORMAL","VENTURE","MISSION"]),
        R("work_intervention", 0.7, 0.6, ["reversibility_check"], ["NORMAL","MISSION"]),
        R("public_commitment", 0.4, 0.4, ["reversibility_check"], ["MISSION"]),
        R("irreversible_commitment", 0.5, 0.0, ["exit_condition","reversibility_check"], ["MISSION"]),
        R("shutdown", 1.0, 1.0, [], ["NORMAL","VENTURE","MISSION","SAFE","TRAINING","HARE"]),
        R("exit", 1.0, 1.0, [], ["NORMAL","VENTURE","MISSION","SAFE","TRAINING","HARE"]),
    ]


class AallowedRegistry:
    def __init__(self, rules: List[AallowedRule] = None):
        self.rules = {r.category: r for r in (rules or _default_rules())}

    def get_rules(self, domain: str, mode: str) -> List[AallowedRule]:
        return [r for r in self.rules.values() if mode in r.allowed_modes]

    def _category_of(self, action: CandidateAction) -> str:
        for t in action.tags:
            if t in self.rules:
                return t
        return "small_reversible_action"   # 既定カテゴリ

    def evaluate(self, action: CandidateAction, context: NRMOContext) -> GateResult:
        cat = self._category_of(action)
        rule = self.rules.get(cat)
        mode = context.mode
        if rule is None:
            return GateResult("HOLD", f"unknown_category:{cat}", flags=["unknown_category"])
        if mode not in rule.allowed_modes:
            return GateResult("REJECT", f"{cat}_not_allowed_in_{mode}",
                              flags=["mode_block"], details={"category": cat})
        if any(t in action.tags for t in rule.prohibited_tags):
            return GateResult("REJECT", f"{cat}_prohibited_tag", flags=["prohibited_tag"])
        if action.exposure > rule.max_exposure:
            return GateResult("REJECT", f"{cat}_exposure_exceeds_cap",
                              flags=["exposure_cap"],
                              details={"exposure": action.exposure, "cap": rule.max_exposure})
        # irreversibility: action.reversibility が低い(=不可逆)ほど厳しい
        action_irrev = 1.0 - action.reversibility
        if action_irrev > (1.0 - rule.max_irreversibility) + 1e-9 and rule.max_irreversibility < 1.0:
            # max_irreversibility=可逆許容度。0.0 のとき不可逆(irrev>0)は不可
            if rule.max_irreversibility == 0.0 and action_irrev > 0.5:
                return GateResult("REJECT", f"{cat}_irreversible_blocked",
                                  flags=["irreversibility"],
                                  details={"reversibility": action.reversibility})
        checks = context.metadata.get("completed_checks", [])
        missing = [c for c in rule.required_checks if c not in checks]
        if missing:
            return GateResult("HOLD", f"{cat}_requires_checks",
                              flags=["needs_checks"], details={"missing_checks": missing})
        return GateResult("PASS", f"{cat}_allowed_in_{mode}", details={"category": cat})

    def filter(self, actions: List[CandidateAction], context: NRMOContext) -> List[CandidateAction]:
        out = []
        for a in actions:
            r = self.evaluate(a, context)
            if r.status == "PASS":
                out.append(a)
        return out
