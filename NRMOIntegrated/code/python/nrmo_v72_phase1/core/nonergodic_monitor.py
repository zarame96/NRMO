"""
nonergodic_monitor.py — 非エルゴード性監視。
時間平均と集合平均のズレ・吸収的失敗・回復不能性を検出する。
権限: 検出/助言のみ。NRMO 境界を変えない。
"""
from __future__ import annotations
from typing import List, Dict
from common_types import NRMOContext, CandidateAction, GateResult

_CRITICAL_DIMS = ("capital", "trust", "health", "R")


class NonErgodicMonitor:
    def detect_absorbing_failure(self, state: dict) -> GateResult:
        crit = []
        for d in _CRITICAL_DIMS:
            if d in state:
                v = float(state[d])
                # capital/trust/health は 0..1, R は 0..100 想定
                norm = v / 100.0 if d == "R" else v
                if norm <= 0.05:
                    crit.append(f"{d}_absorbing")
                elif norm <= 0.2:
                    crit.append(f"{d}_near_absorbing")
        if any("_absorbing" in c and "near" not in c for c in crit):
            return GateResult("REJECT", "absorbing_failure_reached", flags=crit)
        if crit:
            return GateResult("HOLD", "near_absorbing_failure", flags=crit)
        return GateResult("PASS", "no_absorbing_failure")

    def estimate_reachability_loss(self, state: dict, action: CandidateAction) -> float:
        """行動が将来到達可能集合をどれだけ削るか (0..1)。不可逆×高露出ほど大。"""
        irrev = 1.0 - action.reversibility
        return max(0.0, min(1.0, irrev * action.exposure))

    def evaluate_path_risk(self, trajectory: List[dict], context: NRMOContext) -> GateResult:
        if not trajectory:
            return GateResult("PASS", "no_trajectory")
        # 時間平均 (経路に沿った積) が単純平均より大きく劣化 = 非エルゴード危険
        last = trajectory[-1]
        af = self.detect_absorbing_failure(last)
        if af.status != "PASS":
            return af
        # 単調な資本減衰検出
        caps = [float(t.get("capital", t.get("R", 1))) for t in trajectory if ("capital" in t or "R" in t)]
        if len(caps) >= 3 and caps[-1] < caps[0] * 0.5:
            return GateResult("HOLD", "time_average_decay_detected",
                              flags=["nonergodic_decay"],
                              details={"start": caps[0], "end": caps[-1]})
        return GateResult("PASS", "path_risk_ok")
