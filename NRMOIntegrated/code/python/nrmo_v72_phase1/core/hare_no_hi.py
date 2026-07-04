"""
hare_no_hi.py — Hare-no-Hi / Festival Protocol + Narrative Random Generator。
祝祭・例外日・意味回復のための運用モード。日常合理性からの一時離脱を安全に許可。
権限: 祝祭行動の評価のみ。破滅的浪費・不可逆・境界侵害・翌日破壊は禁止。
"""
from __future__ import annotations
import hashlib
from typing import Dict
from common_types import NRMOContext, CandidateAction, GateResult

_SACRED_DESTROYING = ["sacred_destroy", "border_violation", "relationship_break",
                      "境界侵害", "irreversible_commitment"]


class HareNoHiProtocol:
    def can_activate(self, context: NRMOContext) -> GateResult:
        s = context.state
        if float(s.get("alcohol", 0)) > 0.4 and s.get("major_decision_pending"):
            return GateResult("REJECT", "alcohol_with_major_decision", flags=["unsafe_activate"])
        if float(s.get("load", 0)) > 0.85:
            return GateResult("HOLD", "too_loaded_for_festival", flags=["recover_first"])
        return GateResult("PASS", "festival_can_activate")

    def activate(self, context: NRMOContext) -> dict:
        context.mode = "HARE"
        return {"mode": "HARE", "protocol": "festival",
                "allow": ["festive_action", "small_indulgence", "memorialize",
                          "narrativize", "warm_relational_expression", "temporary_rationality_break"],
                "note": "daily-rationality suspended within bounds"}

    def evaluate_action(self, action: CandidateAction, context: NRMOContext) -> GateResult:
        if any(t in action.tags for t in _SACRED_DESTROYING):
            return GateResult("REJECT", "sacred_destroying_action_forbidden",
                              flags=["forbidden"])
        if action.reversibility < 0.2:
            return GateResult("REJECT", "irreversible_commitment_in_festival", flags=["forbidden"])
        if action.exposure > 0.6:
            return GateResult("HOLD", "excessive_indulgence_risk", flags=["next_day_protection"])
        return GateResult("PASS", "festive_action_allowed")

    def terminate(self, context: NRMOContext) -> dict:
        context.mode = "NORMAL"
        return {"mode": "NORMAL", "note": "festival ended; return to daily SOP"}


class NarrativeRandomGenerator:
    """祝祭の意味づけ用に、決定論的(seed)に温かい物語要素を生成。浪費誘導はしない。"""
    THEMES = ["小さな祝祭", "節目の記憶化", "感謝の表現", "静かな達成の確認",
              "関係性の温かい一場面", "日常からの一歩の離脱"]
    FRAMES = ["これは続いてきたことの確認", "これは未来への小さな投資",
              "これは無駄ではなく意味", "これは記録に値する日"]

    def generate(self, context: NRMOContext) -> dict:
        seed_src = (context.user_goal or "") + context.domain + str(context.metadata.get("day", ""))
        h = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest(), 16)
        theme = self.THEMES[h % len(self.THEMES)]
        frame = self.FRAMES[(h // 7) % len(self.FRAMES)]
        return {"theme": theme, "frame": frame,
                "suggested_scale": "small / non-ruinous",
                "note": "narrative for meaning-recovery, not spending pressure"}
