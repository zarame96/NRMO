"""
time_horizon.py — 時間軸分類 (short/mid/long/ultra)。
権限: 分類のみ。
"""
from __future__ import annotations
from common_types import NRMOContext, CandidateAction


class TimeHorizonClassifier:
    def classify(self, action: CandidateAction, context: NRMOContext) -> str:
        if action.time_horizon in ("short", "mid", "long", "ultra"):
            return action.time_horizon
        h = action.payload.get("horizon_days", 1)
        if h <= 7: return "short"
        if h <= 90: return "mid"
        if h <= 365 * 3: return "long"
        return "ultra"
