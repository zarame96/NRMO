"""
ttm_pps.py — Tactical Training Mode / Psychological Procedure Sandbox。
訓練と現実行動を混同しないサンドボックス。
権限: TRAINING では現実実行を禁止。carryback は分析/境界/準備のみ。
"""
from __future__ import annotations
from common_types import NRMOContext, CandidateAction, GateResult


class TTMPPS:
    def activate(self, context: NRMOContext) -> GateResult:
        context.metadata["ttm_active"] = True
        return GateResult("PASS", "training_sandbox_activated",
                          details={"mode": "TRAINING"})

    def terminate(self, context: NRMOContext) -> GateResult:
        context.metadata["ttm_active"] = False
        return GateResult("PASS", "training_sandbox_terminated")

    def simulate_pattern(self, pattern_id: str, context: NRMOContext) -> dict:
        return {"pattern_id": pattern_id, "result": "simulated",
                "tags": ["SIMULATION_ONLY"], "real_execution": False}

    def prohibit_real_execution(self, action: CandidateAction) -> GateResult:
        if "real_world_execution" in action.tags or action.payload.get("real_execution"):
            return GateResult("REJECT", "real_execution_prohibited_in_training",
                              flags=["SIMULATION_ONLY"])
        return GateResult("PASS", "simulation_only_ok", flags=["SIMULATION_ONLY"])
