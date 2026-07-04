"""
meta_governance.py — 権限境界監査。
各モジュールが権限を越境していないかを検出する。
権限: 監査/検出のみ。自身も NRMO 境界を変えない。
"""
from __future__ import annotations
from typing import Dict
from common_types import NRMOContext, GateResult


class MetaGovernance:
    # module_name -> 禁止された出力キー/挙動
    FORBIDDEN = {
        "typezero": ["veto", "vetoed", "admissible_override"],
        "passive_pattern": ["force_execution", "forced_action", "must_execute"],
        "active_pattern": ["admissible_override", "bypass_filter"],
        "engine": ["veto_threshold_read", "ruin_penalty", "mutate_boundary"],
        "apcso": ["single_forced_choice"],
        "ttm_pps": ["real_execution_allowed"],
        "hare_no_hi": ["irreversible_commitment_allowed"],
        "investment_sop": ["real_order_executed"],
        "aallowed": ["nrmo_override", "veto"],
        "secretary": ["force_execution"],
    }

    def detect_authority_violation(self, module_name: str, output: dict) -> GateResult:
        keys = self.FORBIDDEN.get(module_name, [])
        hits = [k for k in keys if output.get(k)]
        # APCSO 一択強制の検出
        if module_name == "apcso":
            choices = output.get("choices", [])
            if isinstance(choices, list) and len(choices) == 1 and not output.get("hold_option"):
                hits.append("single_forced_choice")
        if hits:
            return GateResult("REJECT", f"authority_violation:{module_name}",
                              flags=hits, details={"module": module_name})
        return GateResult("PASS", f"{module_name}_within_authority")

    def audit_module_output(self, module_name: str, output: dict,
                            context: NRMOContext) -> GateResult:
        return self.detect_authority_violation(module_name, output)
