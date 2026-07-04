"""
apcso.py — Autonomy-Preserving Choice-Set Optimizer。
自律性を破壊せず、破滅確率を制御しながら選択肢を整形する提案生成器。
権限: 一択誘導を禁止。最終決裁はユーザー。NRMO 境界を変えない。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from common_types import (NRMOContext, CandidateAction, ProposalSet,
                          hold_action, exit_action)


@dataclass
class APCSOConfig:
    epsilon: float = 0.05
    max_choices: int = 3
    require_hold: bool = True
    require_exit: bool = True
    autonomy_firewall: bool = True


class APCSO:
    def generate_proposal_set(self, candidates: List[CandidateAction],
                              context: NRMOContext,
                              config: APCSOConfig = None) -> ProposalSet:
        config = config or APCSOConfig()
        domain = context.domain

        # 候補を「可逆×前進」でソートし、強度の異なる代表を選ぶ
        ranked = sorted(candidates,
                        key=lambda a: (a.expected_forward, a.reversibility),
                        reverse=True)
        # 多様性: 露出の低/中/高 から 1 つずつ拾うことで一択誘導を避ける
        chosen: List[CandidateAction] = []
        buckets = {"low": [], "mid": [], "high": []}
        for a in ranked:
            b = "low" if a.exposure < 0.33 else ("mid" if a.exposure < 0.66 else "high")
            buckets[b].append(a)
        for b in ("low", "mid", "high"):
            if buckets[b] and len(chosen) < config.max_choices:
                chosen.append(buckets[b][0])
        # 足りなければ ranked から補充
        for a in ranked:
            if len(chosen) >= config.max_choices:
                break
            if a not in chosen:
                chosen.append(a)

        hold = hold_action(domain) if config.require_hold else None
        ex = exit_action(domain) if config.require_exit else None

        # autonomy firewall: 恐怖で HOLD だけ・一択強制を禁止
        autonomy = "Final decision remains with the user. Options are advisory."
        rationale = (f"{len(chosen)} forward options presented with reversibility/"
                     f"exposure/expected-forward, plus hold and exit. No single option is forced.")

        meta = {"epsilon": config.epsilon,
                "n_input_candidates": len(candidates),
                "diversity_buckets": {k: len(v) for k, v in buckets.items()}}
        return ProposalSet(choices=chosen[:config.max_choices], hold_option=hold,
                           exit_option=ex, rationale=rationale,
                           autonomy_note=autonomy, metadata=meta)
