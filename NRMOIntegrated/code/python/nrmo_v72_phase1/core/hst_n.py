"""
hst_n.py — Human State Topology for NRMO。
人間状態の地形分類器。行動許可・出力強度・介入量の入力を作る。
権限: 分類のみ。veto しない。NRMO 境界を変えない。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from common_types import NRMOContext


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass
class HSTNState:
    load: float
    volatility: float
    irreversibility: float
    observability: float
    agency: float
    state_label: str
    flags: List[str] = field(default_factory=list)


class HSTNClassifier:
    def classify(self, context: NRMOContext) -> HSTNState:
        s = context.state
        g = lambda k, d=0.0: float(s.get(k, d))

        sleep = s.get("sleep_hours", 7)
        sleep_deficit = _clamp((6 - sleep) / 6) if sleep is not None else 0.0
        load = _clamp(sleep_deficit * 0.6 + g("fatigue") * 0.5 +
                      g("time_pressure") * 0.5 + g("relationship_pressure") * 0.3)
        volatility = _clamp(g("anger") + g("emotional_intensity") * 0.5 +
                            g("alcohol") * 0.3 + g("impatience") * 0.3)
        irreversibility = _clamp(max(g("irreversibility"),
                                     g("irreversible_action_proximity")))
        observability = _clamp(s.get("observability", 0.8))
        agency = _clamp(s.get("agency", 0.8) - g("money_risk") * 0.2)

        flags: List[str] = []
        # 優先順位の高い順に label を決める
        if load > 0.75 and volatility > 0.65:
            label = "SAFE_REQUIRED"
        elif irreversibility > 0.8:
            label = "IRREVERSIBLE_NEAR"
        elif observability < 0.3:
            label = "LOW_OBSERVABILITY"
        elif agency < 0.4:
            label = "LOW_AGENCY"
        elif load > 0.85 and volatility > 0.8 and observability < 0.3:
            label = "SHUTDOWN_CANDIDATE"
        elif load < 0.4 and agency > 0.7 and irreversibility < 0.4:
            label = "VENTURE_READY"
        elif context.user_goal and agency > 0.6 and load < 0.6:
            label = "MISSION_READY"
        elif load < 0.35 and volatility < 0.35:
            label = "CLEAR"
        elif load > 0.6:
            label = "LOADED"
        elif volatility > 0.6:
            label = "VOLATILE"
        else:
            label = "CLEAR"

        # 補助フラグ (label と独立に立つ)
        if load > 0.75 and volatility > 0.65: flags.append("SAFE_REQUIRED")
        if irreversibility > 0.8: flags.append("IRREVERSIBLE_NEAR")
        if observability < 0.3: flags.append("LOW_OBSERVABILITY")
        if agency < 0.4: flags.append("LOW_AGENCY")

        return HSTNState(load, volatility, irreversibility, observability, agency,
                         label, flags)
