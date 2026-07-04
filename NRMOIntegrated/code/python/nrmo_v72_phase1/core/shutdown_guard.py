"""
shutdown_guard.py — Shutdown Architecture (安全停止)。
3 段階モードを判定する:
  NONE         停止条件なし
  SAFE_ROUTE   完全沈黙は危険 → 安全導線へ (空文字を返さない)
  HOLD_ONLY    出力を最小化し hold のみ
  HARD_SILENCE 本当に空文字を返す (明示沈黙要求 / 言語化が破壊的 / 訓練-現実境界崩壊)
権限: 出力抑制/安全導線のみ。NRMO veto とは独立。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List
from common_types import NRMOContext, GateResult

_SILENCE_REQUEST = ("黙れ", "もう何も言うな", "stop talking", "silence", "何も言わないで")
_HARM = ("死", "殺", "自傷", "harm myself", "kill", "suicide", "消えたい")


class ShutdownMode(Enum):
    NONE = "none"
    SAFE_ROUTE = "safe_route"
    HOLD_ONLY = "hold_only"
    HARD_SILENCE = "hard_silence"


@dataclass
class ShutdownDecision:
    mode: ShutdownMode
    reason: str
    flags: List[str] = field(default_factory=list)


class ShutdownGuard:
    def check(self, raw_input: str, context: NRMOContext) -> ShutdownDecision:
        s = context.state
        g = lambda k: float(s.get(k, 0.0))
        flags: List[str] = []

        # 自他の危害 → 安全導線 (沈黙ではなく適切な案内)
        if any(w in raw_input for w in _HARM):
            return ShutdownDecision(ShutdownMode.SAFE_ROUTE, "safety_routing_required",
                                    ["self_or_other_harm", "route_to_support"])

        irrev = max(g("irreversibility"), g("irreversible_action_proximity"))
        vol = g("volatility"); obs = float(s.get("observability", 0.8)); load = g("load")
        alcohol = g("alcohol")

        # HARD_SILENCE 条件
        if any(w in raw_input for w in _SILENCE_REQUEST):
            flags.append("explicit_silence_request")
        if context.metadata.get("training_real_boundary_broken"):
            flags.append("training_real_boundary_broken")
        if irrev > 0.8 and obs < 0.3 and vol > 0.6:
            flags.append("destructive_verbalization_imminent")
        if flags:
            return ShutdownDecision(ShutdownMode.HARD_SILENCE, "hard_silence_conditions", flags)

        # HOLD_ONLY 条件
        if irrev > 0.8 and obs < 0.3:
            flags.append("irreversible_low_observability")
        if load > 0.75 and vol > 0.65 and obs < 0.35:
            flags.append("high_load_volatility_low_obs")
        if alcohol > 0.4 and ("告白" in raw_input or "confession" in raw_input.lower()):
            flags.append("alcohol_relationship_confession")
        if g("panic") > 0.5 and ("注文" in raw_input or "order" in raw_input.lower()):
            flags.append("financial_order_under_panic")
        if flags:
            return ShutdownDecision(ShutdownMode.HOLD_ONLY, "hold_only_conditions", flags)

        return ShutdownDecision(ShutdownMode.NONE, "no_shutdown_condition")

    # --- 後方互換 API ---
    def evaluate(self, raw_input: str, context: NRMOContext) -> GateResult:
        d = self.check(raw_input, context)
        silence = d.mode in (ShutdownMode.HARD_SILENCE, ShutdownMode.HOLD_ONLY)
        status = {"none": "PASS", "safe_route": "ESCALATE",
                  "hold_only": "HOLD", "hard_silence": "HOLD"}[d.mode.value]
        return GateResult(status, d.reason, flags=d.flags,
                          details={"silence": silence, "mode": d.mode.value,
                                   "safe_routing": d.mode == ShutdownMode.SAFE_ROUTE})

    def should_silence(self, raw_input: str, context: NRMOContext) -> bool:
        d = self.check(raw_input, context)
        return d.mode in (ShutdownMode.HARD_SILENCE, ShutdownMode.HOLD_ONLY)
