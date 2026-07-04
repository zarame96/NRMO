"""
investment_sop.py — Investment SOP 判断支援。
実注文はしない。SOP 判定・ログ・リスクチェックのみ。
権限: 助言/ゲート判定。実行・断定推奨・内部知識での価格断定は禁止。
"""
from __future__ import annotations
from typing import Dict, List
from common_types import NRMOContext, CandidateAction, GateResult


class InvestmentSOP:
    def __init__(self, single_position_cap=0.25, sector_cap=0.40, min_cash=0.05):
        self.single_position_cap = single_position_cap
        self.sector_cap = sector_cap
        self.min_cash = min_cash

    def evaluate_order(self, action: CandidateAction, context: NRMOContext) -> GateResult:
        if action.payload.get("execute_real_order"):
            return GateResult("REJECT", "real_order_execution_prohibited",
                              flags=["no_execution"])
        flags = []
        s = context.state
        if float(s.get("panic", 0)) > 0.5 or float(s.get("fatigue", 0)) > 0.7:
            flags.append("panic_or_fatigue_flag")
        if action.payload.get("high_risk_product") and not action.payload.get("hedge"):
            flags.append("unhedged_high_risk_product")
        if action.reversibility < 0.2:
            flags.append("irreversible_loss_risk")
        status = "HOLD" if flags else "PASS"
        return GateResult(status, "investment_sop_evaluated", flags=flags,
                          details={"note": "decision-support only; no order placed"})

    def check_position_limit(self, portfolio: dict, order: dict) -> GateResult:
        total = float(portfolio.get("total_value", 0)) or 1.0
        new_pos = float(portfolio.get("positions", {}).get(order.get("ticker"), 0)) + float(order.get("amount", 0))
        frac = new_pos / total
        if frac > self.single_position_cap:
            return GateResult("REJECT", "single_position_exceeds_cap",
                              details={"fraction": round(frac, 3), "cap": self.single_position_cap})
        return GateResult("PASS", "position_within_cap", details={"fraction": round(frac, 3)})

    def check_liquidity(self, portfolio: dict, order: dict) -> GateResult:
        total = float(portfolio.get("total_value", 0)) or 1.0
        cash_after = (float(portfolio.get("cash", 0)) - float(order.get("amount", 0))) / total
        if cash_after < self.min_cash:
            return GateResult("REJECT", "cash_buffer_breached",
                              details={"cash_after": round(cash_after, 3), "min": self.min_cash})
        return GateResult("PASS", "liquidity_ok", details={"cash_after": round(cash_after, 3)})

    def benchmark_twr_check(self, returns: List[float], benchmark: List[float]) -> dict:
        def twr(rs):
            v = 1.0
            for r in rs: v *= (1 + r)
            return v - 1
        p4 = twr(returns[-4:]); b4 = twr(benchmark[-4:])
        p12 = twr(returns[-12:]); b12 = twr(benchmark[-12:])
        return {
            "twr_4m": round(p4, 4), "benchmark_4m": round(b4, 4),
            "twr_12m": round(p12, 4), "benchmark_12m": round(b12, 4),
            "underperforming_4m": p4 < b4,
            "underperforming_12m": p12 < b12,
            "note": "evidence-based comparison; not a recommendation",
        }
