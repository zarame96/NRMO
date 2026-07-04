"""
situation_parameters.py — 状況パラメータ抽出。
EngineとNRMOへ渡す状況ベクトルを明示化する。権限: 抽出のみ。
"""
from __future__ import annotations
from typing import Dict
from common_types import NRMOContext


class SituationParameterExtractor:
    KEYS = ["urgency", "reversibility", "exposure", "observability",
            "resource_availability", "social_risk", "capital_risk", "trust_risk",
            "health_risk", "opportunity_decay", "competitive_pressure"]

    def extract(self, context: NRMOContext) -> Dict[str, float]:
        s = context.state
        out = {}
        for k in self.KEYS:
            out[k] = float(s.get(k, 0.0))
        # 既知の別名から補完
        out["reversibility"] = float(s.get("reversibility", 1.0))
        out["observability"] = float(s.get("observability", 0.8))
        out["resource_availability"] = float(s.get("resource_availability", s.get("R", 50) / 100.0))
        return out
