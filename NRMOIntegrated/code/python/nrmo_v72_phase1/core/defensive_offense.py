"""
defensive_offense.py — 防御のための攻め / Carryback。
破滅境界を守るために必要な能動行動を許可する (報復・支配・感情攻撃は禁止)。
権限: 候補評価/生成のみ。NRMO 境界を変えない。
"""
from __future__ import annotations
from typing import List
from common_types import NRMOContext, CandidateAction, GateResult

_FORBIDDEN = ["retaliation", "revenge", "domination", "emotional_attack",
              "irreversible_escalation", "報復", "支配"]
_ALLOWED = ["boundary_setting", "preventive_check", "small_first_move",
            "early_clarification", "low_exposure_observation", "experimental_intervention"]


class DefensiveOffense:
    def evaluate(self, action: CandidateAction, context: NRMOContext) -> GateResult:
        if any(t in action.tags for t in _FORBIDDEN):
            return GateResult("REJECT", "forbidden_offensive_action",
                              flags=["aggression_not_defensive"])
        if action.reversibility < 0.3 and action.exposure > 0.6:
            return GateResult("HOLD", "irreversible_high_exposure_escalation",
                              flags=["escalation_risk"])
        if any(t in action.tags for t in _ALLOWED) or action.reversibility >= 0.5:
            return GateResult("PASS", "defensive_offense_allowed")
        return GateResult("HOLD", "needs_review")

    def generate_defensive_actions(self, context: NRMOContext) -> List[CandidateAction]:
        d = context.domain
        return [
            CandidateAction("def_boundary", "Set explicit boundary", d,
                            reversibility=1.0, exposure=0.1, tags=["boundary_setting"]),
            CandidateAction("def_clarify", "Early clarification of misunderstanding", d,
                            reversibility=1.0, exposure=0.2, tags=["early_clarification"]),
            CandidateAction("def_probe", "Low-exposure observation/probe", d,
                            reversibility=1.0, exposure=0.15, tags=["low_exposure_observation", "probe"]),
            CandidateAction("def_first_move", "Small reversible first move", d,
                            reversibility=0.8, exposure=0.25, tags=["small_first_move", "small_reversible_action"]),
        ]


class CarrybackController:
    def carryback(self, training_result: dict, context: NRMOContext) -> dict:
        """訓練結果を現実へ持ち帰る — ただし分析/境界/準備に限定。実行指示化は禁止。"""
        return {
            "analysis": training_result.get("result", ""),
            "boundaries_learned": training_result.get("boundaries", []),
            "preparation_notes": training_result.get("notes", []),
            "real_execution_instruction": None,   # 禁止: 訓練→即実行は変換しない
            "tags": ["analysis_only", "no_direct_execution"],
        }
