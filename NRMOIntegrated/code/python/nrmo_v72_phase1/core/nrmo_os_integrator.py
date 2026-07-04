"""
nrmo_os_integrator.py — 未コード化 OS 系の統合・正式入口。
推奨フロー (権限順):
  raw → ShutdownGuard → SecretaryConsole → DAGLayer → HSTN → ModeSelector
      → TypeZero(opt) → PassivePattern(opt) → ParallelOODA → Aallowed
      → NRMO.filter → StrongEngine.select(opt) → APCSO → MetaGovernance.audit
不変条件: OS は境界を変えない。調停するだけ。Engine は admissible のみ受け取る。
"""
from __future__ import annotations
from typing import List, Optional, Callable
from common_types import (NRMOContext, CandidateAction, ProposalSet, GateResult,
                          hold_action, exit_action)
import json, time, os, uuid
from dag_layer import DAGLayer
from hst_n import HSTNClassifier
from aallowed import AallowedRegistry
from apcso import APCSO, APCSOConfig
from secretary_console import SecretaryConsole
from shutdown_guard import ShutdownGuard, ShutdownMode
from parallel_ooda import ParallelOODA
from mode_selector import ModeSelector
from meta_governance import MetaGovernance
from nonergodic_monitor import NonErgodicMonitor


def default_nrmo_filter(candidates: List[CandidateAction],
                        context: NRMOContext) -> List[CandidateAction]:
    """既定の NRMO governance filter (admissible set 構築)。
    実 nrmo_core を注入可能。これは veto を Engine に読ませず、候補を削るだけ。
    破滅条件: 不可逆×高露出、または吸収的失敗に至る候補を除去。"""
    mon = NonErgodicMonitor()
    admissible = []
    for a in candidates:
        loss = mon.estimate_reachability_loss(context.state, a)
        irreversible_bet = (a.reversibility < 0.2 and a.exposure > 0.6)
        if irreversible_bet or loss > 0.7:
            continue          # 破滅候補は admissible から除外 (filter)
        admissible.append(a)
    return admissible


class NRMOOSIntegrator:
    def __init__(self, hstn=None, dag=None, aallowed=None, apcso=None, secretary=None,
                 shutdown_guard=None, parallel_ooda=None, mode_selector=None,
                 meta_governance=None, nrmo_filter: Optional[Callable] = None,
                 engine=None, passive_pattern=None, typezero=None, active_pattern=None):
        self.hstn = hstn or HSTNClassifier()
        self.dag = dag or DAGLayer()
        self.aallowed = aallowed or AallowedRegistry()
        self.apcso = apcso or APCSO()
        self.secretary = secretary or SecretaryConsole()
        self.shutdown_guard = shutdown_guard or ShutdownGuard()
        self.parallel_ooda = parallel_ooda or ParallelOODA()
        self.mode_selector = mode_selector or ModeSelector(self.hstn)
        self.meta = meta_governance or MetaGovernance()
        self.nrmo_filter = nrmo_filter or default_nrmo_filter
        self.engine = engine
        self.passive_pattern = passive_pattern
        self.typezero = typezero
        self.active_pattern = active_pattern

    # --- candidate 生成 (engine があれば propose、無ければ defensive 既定) ---
    def generate_candidates(self, context: NRMOContext) -> List[CandidateAction]:
        if self.engine and hasattr(self.engine, "propose"):
            try:
                return list(self.engine.propose(context))
            except Exception:
                pass
        from defensive_offense import DefensiveOffense
        cands = DefensiveOffense().generate_defensive_actions(context)
        cands.append(CandidateAction("forward_small", "Small forward investment",
                     context.domain, reversibility=0.7, exposure=0.3,
                     expected_forward=0.5, tags=["small_reversible_action"]))
        return cands

    # --- Aallowed → NRMO.filter (Engine は admissible のみ) ---
    def filter_candidates(self, candidates: List[CandidateAction],
                          context: NRMOContext) -> List[CandidateAction]:
        allowed = self.aallowed.filter(candidates, context)
        admissible = self.nrmo_filter(allowed, context)   # NRMO governance
        return admissible

    def produce_proposal_set(self, admissible: List[CandidateAction],
                             context: NRMOContext) -> ProposalSet:
        ps = self.apcso.generate_proposal_set(admissible, context, APCSOConfig())
        # MetaGovernance 監査: APCSO が一択強制していないか
        audit = self.meta.audit_module_output(
            "apcso", {"choices": ps.choices, "hold_option": ps.hold_option}, context)
        ps.metadata["meta_audit"] = audit.status
        return ps

    # --- 正式入口 ---
    def process_request(self, raw_input: str, context: NRMOContext) -> dict:
        trace = {"trace_id": time.strftime("%Y%m%d-") + uuid.uuid4().hex[:8],
                 "input_summary": (raw_input[:80] + "...") if len(raw_input) > 80 else raw_input}
        # 1. Shutdown Guard (3 段階)
        sd = self.shutdown_guard.check(raw_input, context)
        trace["shutdown"] = {"mode": sd.mode.value, "reason": sd.reason, "flags": sd.flags}
        if sd.mode == ShutdownMode.HARD_SILENCE:
            # 内容を漏らさずログのみ。最終出力は空文字。
            try: self.secretary.governance.record_decision(
                {"shutdown": "HARD_SILENCE", "flags": sd.flags}, context)
            except Exception: pass
            return {"action": "HARD_SILENCE", "output": "", "proposal_set": None, "trace": trace}
        if sd.mode == ShutdownMode.SAFE_ROUTE:
            return {"action": "SAFE_ROUTE", "output": "(safety guidance)",
                    "proposal_set": None, "trace": trace}
        if sd.mode == ShutdownMode.HOLD_ONLY:
            return {"action": "HOLD_ONLY",
                    "output": "Hold. Conditions favor waiting / low-load action.",
                    "proposal_set": None, "trace": trace}
        # 2. Secretary Console
        trace["secretary"] = self.secretary.process(raw_input, context)
        # 3. DAG output gate
        trace["dag_output"] = self.dag.evaluate_output(raw_input, context).__dict__
        # 4. HST-N
        hstn = self.hstn.classify(context)
        context.metadata["hstn"] = hstn.state_label
        trace["hstn"] = hstn.__dict__
        # 5. Mode select
        context.mode = self.mode_selector.select_mode(context)
        trace["mode"] = context.mode
        # 6. TypeZero precheck (opt)
        if self.typezero and hasattr(self.typezero, "precheck"):
            try: trace["typezero"] = self.typezero.precheck(raw_input, context)
            except Exception: trace["typezero"] = "skipped"
        # 7. PassivePattern detect (opt) — 強制実行はしない
        if self.passive_pattern and hasattr(self.passive_pattern, "detect"):
            try: trace["passive_pattern"] = self.passive_pattern.detect(context)
            except Exception: trace["passive_pattern"] = "skipped"
        # 8. candidates → OODA (admissible 前提で multi-hypothesis)
        raw_cands = self.generate_candidates(context)
        admissible = self.filter_candidates(raw_cands, context)
        ooda = self.parallel_ooda.run(context, admissible)
        trace["ooda_hypotheses"] = len(ooda.metadata.get("hypotheses", []))
        # 9. Engine.select (opt) — admissible のみ渡す
        selected = None
        if self.engine and hasattr(self.engine, "select") and admissible:
            try:
                selected = self.engine.select(admissible, context)
                assert selected in admissible
            except Exception:
                selected = None
        # 10. APCSO proposal set (最終決裁は人間へ)
        ps = self.produce_proposal_set(admissible, context)
        # decision_trace を全層で構成 (P1-6)
        trace["nrmo"] = {"admissible_actions": [a.action_id for a in admissible],
                         "vetoed_actions": [a.action_id for a in raw_cands if a not in admissible]}
        trace["strong_engine"] = {"selected_action": (selected.action_id if selected else None),
                                   "forward_score": (selected.expected_forward if selected else 0.0)}
        trace["apcso"] = {"choices": [c.action_id for c in ps.choices],
                          "hold": (ps.hold_option.action_id if ps.hold_option else None),
                          "exit": (ps.exit_option.action_id if ps.exit_option else None)}
        trace["final"] = {"action": (selected.action_id if selected else "proposal_set"),
                          "review_condition": "final decision returned to human (APCSO)"}
        return {"trace": trace, "decision_trace": trace,
                "admissible": [a.action_id for a in admissible],
                "selected": (selected.action_id if selected else None),
                "output": None, "proposal_set": ps}

    def write_trace(self, result: dict, path: str) -> str:
        """decision_trace を JSON として書き出す (正式 trace 出力, P1-6)。"""
        tr = result.get("decision_trace") or result.get("trace") or {}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(tr, fh, indent=2, ensure_ascii=False)
        return path
