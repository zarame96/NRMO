"""
parallel_ooda.py — Parallel OODA 思考統治系。
複数仮説・複数観測・複数行動案を同時に保持する。
権限: admissible 外を選ばない。NRMO 境界を変えない。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
from common_types import NRMOContext, CandidateAction, ProposalSet, hold_action, exit_action


@dataclass
class Observation:
    raw: dict
    source: str
    confidence: float


@dataclass
class OrientationHypothesis:
    hypothesis_id: str
    description: str
    confidence: float
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)


class OODALoop:
    def observe(self, context: NRMOContext) -> List[Observation]:
        s = context.state; obs = []
        obs.append(Observation({"state": dict(s)}, "current_state", 0.9))
        if context.history:
            obs.append(Observation({"history_len": len(context.history)}, "history", 0.7))
        for key, src in (("hstn", "HST-N"), ("map_terrain", "MAPLayer"),
                         ("passive_pattern", "PassivePattern"), ("dag", "DAG"),
                         ("external_log", "external")):
            if key in context.metadata:
                obs.append(Observation({key: context.metadata[key]}, src, 0.6))
        return obs

    def orient(self, observations: List[Observation]) -> List[OrientationHypothesis]:
        st = {}
        for o in observations:
            if o.source == "current_state":
                st = o.raw.get("state", {})
        unc = float(st.get("uncertainty", 0.5))
        ruin_prox = float(st.get("ruin_proximity", st.get("X", 0) / 100.0))
        opp = float(st.get("opportunity", st.get("O", 50) / 100.0))
        H = [
            OrientationHypothesis("H1", "Opportunity loss is the main risk", opp,
                                  risks=["stagnation"], opportunities=["forward_move"]),
            OrientationHypothesis("H2", "Ruin proximity is the main risk", ruin_prox,
                                  risks=["absorbing_failure"], opportunities=["defense"]),
            OrientationHypothesis("H3", "Information insufficiency is the main risk", unc,
                                  risks=["wrong_premise"], opportunities=["probe"]),
            OrientationHypothesis("H4", "Judgment degraded by fatigue/emotion",
                                  float(st.get("fatigue", st.get("load", 0.0)) or 0.0),
                                  risks=["impulsive_action"], opportunities=["hold"]),
            OrientationHypothesis("H5", "Strategic offensive window", opp * (1 - ruin_prox),
                                  risks=["overreach"], opportunities=["aggressive_forward"]),
        ]
        return H

    def decide(self, hypotheses: List[OrientationHypothesis],
               admissible: List[CandidateAction]) -> List[CandidateAction]:
        # admissible からのみ選ぶ (vetoed は構造的に届かない)
        return list(admissible)

    def act_plan(self, decisions: List[CandidateAction], domain: str,
                 uncertain: bool) -> ProposalSet:
        choices = list(decisions)[:3]
        meta = {"action_palette": ["reversible_small", "probe", "full", "hold", "exit"]}
        return ProposalSet(choices=choices, hold_option=hold_action(domain),
                           exit_option=exit_action(domain),
                           rationale="parallel OODA: multiple hypotheses retained",
                           metadata=meta)


class ParallelOODA:
    def __init__(self):
        self.loop = OODALoop(); self._feedback: List[dict] = []

    def run(self, context: NRMOContext, candidates: List[CandidateAction]) -> ProposalSet:
        obs = self.loop.observe(context)
        hyps = self.loop.orient(obs)
        decisions = self.loop.decide(hyps, candidates)   # candidates は admissible 前提
        uncertain = float(context.metadata.get("uncertainty",
                          context.state.get("uncertainty", 0.0))) > 0.6
        ps = self.loop.act_plan(decisions, context.domain, uncertain)
        # 不確実時は probe を必ず含める
        if uncertain and not any("probe" in c.tags for c in ps.choices):
            probe = CandidateAction("probe", "Probe / gather info", context.domain,
                                    reversibility=1.0, exposure=0.1, tags=["probe"])
            ps.choices = ([probe] + ps.choices)[:3]
        ps.metadata["hypotheses"] = [h.__dict__ for h in hyps]
        ps.metadata["observations"] = len(obs)
        return ps

    def update_feedback(self, result: dict) -> None:
        self._feedback.append(result)
