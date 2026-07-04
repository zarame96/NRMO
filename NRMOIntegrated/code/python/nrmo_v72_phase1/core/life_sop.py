"""
life_sop.py — NRMO Life SOP v2.0。
日次の Morning / Noon / Night の軽量ループ。
権限: 助言/記録のみ。過剰反省を避ける。NRMO 境界を変えない。
"""
from __future__ import annotations
from typing import Dict
from common_types import NRMOContext


class LifeSOP:
    def morning_startup(self, context: NRMOContext) -> dict:
        s = context.state
        sleep = s.get("sleep_hours", 7)
        load = "high" if (sleep is not None and sleep < 5) or float(s.get("fatigue", 0)) > 0.6 else "ok"
        mode = "SAFE" if load == "high" else context.mode
        return {
            "sleep_load_check": {"sleep_hours": sleep, "load": load},
            "mode": mode,
            "today_non_ruin_boundary": "no irreversible high-exposure action today",
            "today_small_forward_action": "one reversible step toward the goal",
        }

    def noon_intervention(self, context: NRMOContext) -> dict:
        return {
            "intervention": "execute the one small forward action if not done",
            "passive_pattern_check": context.metadata.get("passive_pattern", "check_stagnation"),
            "opportunity_loss_check": "any closing window today?",
        }

    def night_non_recovery(self, context: NRMOContext) -> dict:
        return {
            "reflection_policy": "log, do not over-reflect / no self-attack",
            "log_only": True,
            "tomorrow_small_action": "convert today's residue into one small action",
        }

    def daily_summary(self, context: NRMOContext) -> dict:
        return {
            "morning": self.morning_startup(context),
            "noon": self.noon_intervention(context),
            "night": self.night_non_recovery(context),
        }
