"""
strong_engine_nrmo_adapter.py — 正式 Engine を実 nrmo_core に接続 (実コード接続)

実 nrmo_core.construct_admissible_set を Governance.filter として包む。
action 形式 [g, sf, lr, di] は nrmo_core が想定する候補ベクトルと同一。
これにより「Engine は実 NRMO の filter() だけを黒箱として使い、admissible 内で
最大前進を選ぶ」を実コードで実証する。

実行: NRMO_V6_ROOT=/path/to/NRMO_v6_Repaired python3 strong_engine_nrmo_adapter.py
(v6 が無ければ理由を表示して skip)
"""
from __future__ import annotations
import os, sys
import numpy as np

# 既定は同梱 v52_codebase を持つパッケージroot (自己完結)。env で上書き可。
_PKG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_DEFAULT = _PKG_ROOT  # 同梱 v52_codebase を既定参照 (自己完結)
_V6 = os.environ.get("NRMO_ROOT_PATH", os.environ.get("NRMO_V6_ROOT", _DEFAULT))
sys.path.insert(0, os.path.join(_V6, "v52_codebase"))
sys.path.insert(0, os.path.dirname(__file__))

from separation_engine import (
    StrongEngineOmegaFull, GoalInterpreter, Memory, HorizonPolicy, HOLD)

R, E, G, O, K, X = 0, 1, 2, 3, 4, 5


class RealNRMOGovernance:
    """実 nrmo_core を Governance(filter only) として包む黒箱。"""
    def __init__(self, mode="vnext"):
        from governance.nrmo_core import construct_admissible_set
        from core.state import CivState
        self._cas = construct_admissible_set
        self._CivState = CivState
        self.mode = mode

    def _civstate(self, s):
        return self._CivState(R=float(s[R]), E=float(s[E]), G=float(s[G]),
                              O=float(s[O]), K=float(s[K]), X=float(s[X]))

    def filter(self, candidates, state):
        adm, _flags = self._cas(list(candidates), self._civstate(state), self.mode)
        return adm


class CivLikeDomain:
    """nrmo_core の CivState 規約に合わせた proxy dynamics (前進量は能力ベース)。"""
    def clone(self, s): return s.copy()
    def forward_value(self, s): return float(s[R] + s[K] + s[O] + 0.5 * (s[E] + s[G]))
    def is_ruin(self, s): return bool(s[E] <= 5 or s[G] <= 5 or s[X] >= 100)
    def context(self, s):
        xb = "low" if s[X] < 40 else ("high" if s[X] > 70 else "mid")
        return dict(exposure_band=xb, weakest_dim="X" if s[X] > 60 else "G",
                    favorable=(s[X] < 40 and s[E] > 45 and s[G] > 45))
    def transition(self, s, a, rng):
        g, sf, lr, di = a
        n = s.copy()
        n[R] += 6 * g - 1.5 * sf; n[K] += 4 * lr + 2 * g; n[O] += 3 * g - 1.0
        n[E] += 1.5 - 2.0 * g + 1.5 * sf; n[G] += 1.0 - 1.5 * g + 1.0 * sf
        n[X] += 5 * g - 6 * sf - 3 * di + 1.0
        if rng.random() < min(0.6, 0.05 + 0.006 * max(0.0, n[X])):
            base = min(rng.exponential(6.0), 16.0)
            mag = base * (0.5 + n[X] / 100.0) * (1 - 0.6 * sf) * (1 - 0.4 * di)
            n[E] -= mag; n[G] -= 0.7 * mag
        n[R:K + 1] = np.clip(n[R:K + 1], 0, 200); n[X] = float(np.clip(n[X], 0, 110))
        return n


if __name__ == "__main__":
    print("=" * 60)
    print("正式 StrongEngine Ω Full × 実 nrmo_core (実コード接続)")
    print("=" * 60)
    try:
        gov = RealNRMOGovernance(mode="vnext")
    except Exception as e:
        print(f"SKIP: 実 nrmo_core を読めません ({e}). NRMO_V6_ROOT を設定してください。")
        sys.exit(0)

    eng = StrongEngineOmegaFull(memory=Memory(True), horizon=HorizonPolicy(long_horizon=20))
    dyn = CivLikeDomain(); goal = GoalInterpreter()
    rng = np.random.default_rng(0)
    s = np.array([55.0, 55.0, 55.0, 50.0, 50.0, 35.0]); f0 = dyn.forward_value(s)
    ruined = holds = inadm_violation = 0
    for _ in range(120):
        proposals = eng.propose(dyn, s, goal, rng)
        adm = gov.filter([a for a, _ in proposals], s)     # 実 nrmo_core が削る
        if not adm:
            holds += 1
            safe = np.array([0.10, 0.55, 0.20, 0.30])
            if gov.filter([safe], s): s = dyn.transition(s, safe, rng)
            continue
        a = eng.select(adm, dyn, s, goal, gov, rng)         # admissible 内で最大前進
        if not any(np.array_equal(a, c) for c in adm): inadm_violation += 1
        s = dyn.transition(s, a, rng)
        if dyn.is_ruin(s): ruined = 1; break
    print(f"  実 nrmo_core filter 接続 OK")
    print(f"  120 step: ruin={ruined}  前進量増分={dyn.forward_value(s)-f0:.0f}  "
          f"HOLD={holds}  admissible違反={inadm_violation}")
    print(f"  → Engine は実 NRMO の filter() のみを黒箱使用し、admissible 内で最大前進。")
