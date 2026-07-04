"""
mode_selector.py — モード選択 (NORMAL/VENTURE/MISSION/SAFE/TRAINING/HARE)。
Type ZERO / HST-N / Aallowed / Passive Pattern / Context を統合して現在モードを選ぶ。
権限: モード選択のみ。NRMO 境界を変えない。
"""
from __future__ import annotations
from common_types import NRMOContext, ModeName
from hst_n import HSTNClassifier


class ModeSelector:
    def __init__(self, hstn: HSTNClassifier = None):
        self.hstn = hstn or HSTNClassifier()

    def select_mode(self, context: NRMOContext) -> ModeName:
        s = context.state
        # 明示フラグが最優先
        if context.metadata.get("training_flag") or s.get("training"):
            return "TRAINING"
        hstn = self.hstn.classify(context)

        # high load + high volatility → SAFE
        if hstn.load > 0.75 and hstn.volatility > 0.65:
            return "SAFE"
        if hstn.state_label in ("SAFE_REQUIRED", "SHUTDOWN_CANDIDATE", "IRREVERSIBLE_NEAR"):
            return "SAFE"
        # festival flag + safe conditions → HARE
        if (context.metadata.get("festival_flag") or s.get("festival")) and \
           hstn.load < 0.7 and float(s.get("alcohol", 0)) <= 0.4:
            return "HARE"
        # mission defined + sufficient agency → MISSION
        if context.user_goal and context.metadata.get("mission") and hstn.agency > 0.6 and hstn.load < 0.6:
            return "MISSION"
        # low risk + growth opportunity → VENTURE
        if hstn.load < 0.4 and hstn.agency > 0.7 and hstn.irreversibility < 0.4 and \
           float(s.get("opportunity", s.get("O", 0) / 100.0)) > 0.5:
            return "VENTURE"
        return "NORMAL"
