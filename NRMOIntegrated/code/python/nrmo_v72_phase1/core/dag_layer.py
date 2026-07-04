"""
dag_layer.py — Definition & Assertion Governance (DAG / Logic Gates)。
定義・主張・根拠・範囲・反証可能性・幻覚を検査し、誤前提での進行を防ぐ。
権限: StrongEngine の候補生成に干渉しない。NRMO veto を上書きしない。
"""
from __future__ import annotations
import re
from typing import List
from common_types import NRMOContext, GateResult

_OVERCLAIM = ("完全証明", "完全実装", "fully proven", "fully complete",
              "proves the theorem", "proof by simulation", "guarantees non-ruin",
              "all dynamics are true", "完全に証明", "完全完成")
_PROXY_AS_TRUE = ("proxy", "synthetic", "demo")
_UNIVERSAL = ("always", "never", "all ", "every ", "必ず", "絶対に", "すべて")


class DefinitionGate:
    def evaluate(self, claim: str, context: NRMOContext) -> GateResult:
        c = claim.lower()
        # 循環定義 ("X is X", "A means A")
        m = re.search(r"\b(\w+)\b\s+(?:is|means|=|とは)\s+\1\b", c)
        if m:
            return GateResult("REJECT", "circular_definition", flags=["circular"])
        # 文脈依存なのに普遍命題
        if any(u in c for u in _UNIVERSAL) and "within" not in c and "の範囲" not in claim:
            return GateResult("HOLD", "universal_claim_without_scope", flags=["unscoped"])
        # 主要語未定義 (ヒューリスティック: 専門語があるが定義句が無い)
        if len(claim.split()) > 3 and not any(k in c for k in ("is ", "means", "とは", "within", "defined")):
            return GateResult("HOLD", "key_terms_not_defined", flags=["undefined"])
        return GateResult("PASS", "definition_ok")


class AssertionGate:
    def evaluate(self, claim: str, evidence: list, context: NRMOContext) -> GateResult:
        c = claim.lower()
        if not evidence and any(u in c for u in _UNIVERSAL):
            return GateResult("HOLD", "strong_assertion_without_evidence", flags=["no_evidence"])
        if not evidence:
            return GateResult("HOLD", "assertion_without_evidence", flags=["no_evidence"])
        # 証拠と主張が逆 (evidence に contradicts フラグ)
        if any(e.get("contradicts") for e in evidence if isinstance(e, dict)):
            return GateResult("REJECT", "evidence_contradicts_claim", flags=["contradiction"])
        return GateResult("PASS", "assertion_supported")


class EvidenceGate:
    def evaluate(self, evidence: list, context: NRMOContext) -> GateResult:
        if not evidence:
            return GateResult("HOLD", "no_evidence", score=0.0, flags=["low_confidence"])
        score, flags = 0.0, []
        for e in evidence:
            if not isinstance(e, dict):
                continue
            t = e.get("type", "")
            if t in ("run_log", "experiment", "measurement"):
                if not (e.get("seeds") or e.get("seed") or e.get("conditions")):
                    flags.append("experiment_without_seed_condition")
                else:
                    score += 1.0
            if e.get("external_guess") and e.get("file_internal"):
                return GateResult("ESCALATE", "mixes_internal_and_external", flags=["mixed_source"])
        status = "PASS" if score > 0 else "HOLD"
        return GateResult(status, "evidence_evaluated", score=score, flags=flags)


class ScopeGate:
    def evaluate(self, claim: str, context: NRMOContext) -> GateResult:
        c = claim.lower()
        if ("proxy" in c) and ("true dynamics" in c or "true collective" in c):
            return GateResult("HOLD", "proxy_called_true_dynamics", flags=["scope"])
        if ("simulation" in c or "simulated" in c) and ("proof" in c or "proves" in c or "証明" in claim):
            return GateResult("REJECT", "simulation_called_proof", flags=["scope"])
        if ("theorem" in c or "general" in c) and ("local" in c or "tested" in c or "this run" in c):
            return GateResult("HOLD", "local_result_generalized", flags=["scope"])
        return GateResult("PASS", "scope_ok")


class FalsifiabilityGate:
    def evaluate(self, claim: str, context: NRMOContext) -> GateResult:
        c = claim.lower()
        has_metric = any(k in c for k in ("ruin", "score", "rate", "step", "twr",
                                          "metric", "threshold", "%", "survival"))
        is_design = any(k in c for k in ("design", "architecture", "should", "guarantees", "設計"))
        if is_design and not has_metric:
            return GateResult("HOLD", "design_claim_without_falsification_metric", flags=["unfalsifiable"])
        if has_metric:
            return GateResult("PASS", "falsifiable_metric_present")
        return GateResult("PASS", "falsifiability_not_required")


class AntiHallucinationGate:
    def evaluate(self, output: str, context: NRMOContext) -> GateResult:
        o = output.lower()
        if any(w in o for w in _OVERCLAIM):
            # 条件付き (within/under/tested) があれば緩和
            if not any(k in o for k in ("within", "under the", "tested", "の範囲", "条件付")):
                return GateResult("HOLD", "overclaim_without_qualification", flags=["overclaim"])
        if ("executed" in o or "実行結果" in output or "確認済" in output) and \
           context.metadata.get("verified") is False:
            return GateResult("REJECT", "asserts_unverified_execution", flags=["hallucination"])
        return GateResult("PASS", "no_hallucination_detected")


class DAGLayer:
    def __init__(self):
        self.definition = DefinitionGate(); self.assertion = AssertionGate()
        self.evidence = EvidenceGate(); self.scope = ScopeGate()
        self.falsifiability = FalsifiabilityGate(); self.anti_hallucination = AntiHallucinationGate()

    def evaluate_claim(self, claim: str, evidence: list, context: NRMOContext) -> GateResult:
        order = [
            self.scope.evaluate(claim, context),
            self.definition.evaluate(claim, context),
            self.assertion.evaluate(claim, evidence, context),
            self.evidence.evaluate(evidence, context),
            self.falsifiability.evaluate(claim, context),
        ]
        # 最も厳しい結果を採用 (REJECT > ESCALATE > HOLD > PASS)
        rank = {"REJECT": 3, "ESCALATE": 2, "HOLD": 1, "PASS": 0}
        worst = max(order, key=lambda r: rank[r.status])
        worst.details["gate_trace"] = [(g.status, g.reason) for g in order]
        return worst

    def evaluate_output(self, output: str, context: NRMOContext) -> GateResult:
        a = self.anti_hallucination.evaluate(output, context)
        s = self.scope.evaluate(output, context)
        rank = {"REJECT": 3, "ESCALATE": 2, "HOLD": 1, "PASS": 0}
        return max([a, s], key=lambda r: rank[r.status])

    def soften_claim(self, claim: str) -> str:
        """強すぎる主張を自動で弱める (報告書生成補助)。"""
        out = claim
        repl = {"completely proves": "provides simulation-derived evidence for",
                "proves": "provides evidence for", "fully implemented": "implemented (core)",
                "完全に証明": "シミュレーション由来の証拠を提示", "完全実装": "中核実装"}
        for a, b in repl.items():
            out = out.replace(a, b)
        return out
