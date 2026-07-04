"""
secretary_console.py — NRMO+Z+PP Secretary Modules。
入力整形・感情フィルタ・ログ・境界管理・方向付けの人間向け OS。
権限: 記録と整形のみ。実行を強制しない。NRMO 境界を変えない。
"""
from __future__ import annotations
import re
from typing import Dict
from common_types import NRMOContext, GateResult

_ATTACK_WORDS = ["お前", "おまえ", "いつも", "絶対に", "最悪", "ばか", "馬鹿",
                 "you always", "you never", "idiot", "stupid"]
_RUMINATION = ["どうせ", "自分はだめ", "価値がない", "消えたい", "何度も考えて",
               "worthless", "i always fail"]


class FailureLogInput:
    def reconstruct(self, raw_event: str, context: NRMOContext) -> dict:
        cause = "fatigue" if any(w in raw_event for w in ("疲れ", "眠", "tired")) else "unknown"
        high_risk = any(w in raw_event for w in ("高リスク", "大きな", "全部", "high risk"))
        return {
            "event": raw_event,
            "cause_hypothesis": cause,
            "boundary_crossed": high_risk,
            "recurrence_condition": f"when {cause} and high-stakes decision co-occur",
            "unobserved_factors": ["counterparty_state", "long_horizon_effect"],
        }


class EmotionalFilter:
    def filter_output(self, draft: str, context: NRMOContext) -> str:
        out = draft
        for w in _ATTACK_WORDS:
            out = out.replace(w, "")
        # 相手を変える文 → 境界・事実・選択肢へ変換 (簡易)
        out = re.sub(r"(変われ|変えろ|change you)", "(boundary: I will state my limit)", out)
        out = re.sub(r"\s+", " ", out).strip()
        if not out:
            out = "(filtered: rephrase as boundary / fact / option)"
        return out


class MentalDetoxProtocol:
    def run(self, context: NRMOContext) -> GateResult:
        text = " ".join(str(v) for v in context.state.values()) + " " + (context.user_goal or "")
        hits = [w for w in _RUMINATION if w in text]
        if hits:
            return GateResult("HOLD", "rumination_detected",
                              flags=["detox"],
                              details={"action": "log_and_low_load_action", "markers": hits})
        return GateResult("PASS", "no_rumination")


class GovernanceLog:
    def __init__(self): self.entries = []
    def _rec(self, kind, payload, context):
        e = {"kind": kind, "payload": payload, "domain": context.domain}
        self.entries.append(e); return e
    def record_boundary(self, boundary: str, context: NRMOContext) -> dict:
        return self._rec("boundary", boundary, context)
    def record_agreement(self, agreement: str, context: NRMOContext) -> dict:
        return self._rec("agreement", agreement, context)
    def record_decision(self, decision: dict, context: NRMOContext) -> dict:
        return self._rec("decision", decision, context)


class OrientationModule:
    def orient(self, context: NRMOContext) -> dict:
        return {
            "BE": context.metadata.get("be", "steady, non-ruined operator"),
            "DO": context.metadata.get("do", "small forward action within boundary"),
            "HAVE": context.metadata.get("have", "optionality preserved"),
            "mode": context.mode,
            "meaning_reference": context.vision_reference or "(held by human)",
        }


class SecretaryConsole:
    def __init__(self):
        self.failure_log = FailureLogInput(); self.emotional_filter = EmotionalFilter()
        self.detox = MentalDetoxProtocol(); self.governance = GovernanceLog()
        self.orientation = OrientationModule()

    def process(self, raw_input: str, context: NRMOContext) -> dict:
        return {
            "R_failure_log": self.failure_log.reconstruct(raw_input, context),
            "W_filtered_output": self.emotional_filter.filter_output(raw_input, context),
            "Z_detox": self.detox.run(context).__dict__,
            "ORIENTATION": self.orientation.orient(context),
        }
