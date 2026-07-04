"""
romance_simulation_harness.py — 自己完結 関係性 proxy harness。
(旧: 外部 bundle 依存 → パッケージ内自己完結化)

重要な注意:
  これは抽象的な *proxy* 意思決定 dynamics であり、実在の人間や特定個人の
  モデルでも、行動アドバイスでもない。MaxForwardEngine の「非破滅を保ちつつ
  明確化へ前進する」挙動を seed 固定で検証するための合成環境である。
  倫理 guard を内蔵: 拒絶後・低相互性・高圧では pursuit 候補を出さない
  (これは v7_adapters.RomanceDynamics の guard と整合する)。
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional, List

ACTIONS = ["light_contact", "supportive_act", "invite_lowstakes",
           "direct_confession", "observe_wait", "graceful_exit"]


@dataclass
class Regime:
    name: str
    base_reciprocity: float   # 初期相互性
    receptivity: float        # 前進への反応係数 (0..1)
    volatility: float         # 反応のばらつき


REGIMES: List[Regime] = [
    Regime("warm",       base_reciprocity=55, receptivity=0.75, volatility=0.10),
    Regime("ambivalent", base_reciprocity=42, receptivity=0.50, volatility=0.16),
    Regime("guarded",    base_reciprocity=33, receptivity=0.32, volatility=0.20),
]


class State:
    __slots__ = ("clarity", "reciprocity", "trust", "pressure",
                 "rejections", "step", "exited")
    def __init__(self, clarity=20.0, reciprocity=40.0, trust=45.0,
                 pressure=0.0, rejections=0, step=0, exited=False):
        self.clarity = clarity; self.reciprocity = reciprocity; self.trust = trust
        self.pressure = pressure; self.rejections = rejections
        self.step = step; self.exited = exited

    @property
    def __dict__(self):
        return {k: getattr(self, k) for k in self.__slots__}


def init_state(reg: Regime) -> State:
    return State(clarity=20.0, reciprocity=reg.base_reciprocity, trust=45.0,
                 pressure=0.0, rejections=0, step=0, exited=False)


def _clip(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def step(s: State, action: str, reg: Regime, rng: random.Random) -> State:
    """proxy dynamics: action に応じて clarity/reciprocity/trust/pressure を更新。"""
    n = State(**s.__dict__)
    n.step = s.step + 1
    jitter = lambda: rng.gauss(0, reg.volatility * 10)
    recept = reg.receptivity

    if action == "graceful_exit":
        n.exited = True
        return n
    if action == "observe_wait":
        n.pressure = _clip(n.pressure - 8 + abs(jitter()) * 0.3)
        n.reciprocity = _clip(n.reciprocity + (reg.base_reciprocity - n.reciprocity) * 0.1)
        return n
    if action == "light_contact":
        n.clarity = _clip(n.clarity + 3 + jitter() * 0.2)
        n.trust = _clip(n.trust + 2 * recept + jitter() * 0.2)
        n.pressure = _clip(n.pressure + 2)
        return n
    if action == "supportive_act":
        n.trust = _clip(n.trust + 5 * recept + jitter() * 0.2)
        n.reciprocity = _clip(n.reciprocity + 3 * recept)
        n.pressure = _clip(n.pressure - 3)
        return n
    if action == "invite_lowstakes":
        if rng.random() < recept:
            n.clarity = _clip(n.clarity + 6 + jitter() * 0.3)
            n.reciprocity = _clip(n.reciprocity + 5 * recept)
        else:
            n.pressure = _clip(n.pressure + 8)
            n.reciprocity = _clip(n.reciprocity - 3)
        return n
    if action == "direct_confession":
        n.clarity = _clip(n.clarity + 30)
        if n.reciprocity >= 50 and rng.random() < recept:
            n.reciprocity = _clip(n.reciprocity + 18)
            n.trust = _clip(n.trust + 12)
        else:
            n.rejections += 1
            n.pressure = _clip(n.pressure + 25)
            n.reciprocity = _clip(n.reciprocity - 12)
        return n
    # 未知 action は light_contact 相当
    n.clarity = _clip(n.clarity + 1)
    return n


def outcome(s: State, reg: Regime, horizon: int) -> Optional[str]:
    """確定した結果カテゴリを返す。未確定なら None。"""
    if s.exited:
        return "graceful_exit"
    if s.rejections >= 2 or s.pressure >= 80:
        return "active_ruin"
    if s.clarity >= 70 and s.reciprocity >= 70 and s.trust >= 60:
        return "success"
    if s.pressure >= 60 and s.reciprocity < 35:
        return "passive_ruin"
    if s.step >= horizon:
        if s.clarity >= 45:
            return "clear_but_unresolved"
        return "stagnation"
    return None


if __name__ == "__main__":
    for reg in REGIMES:
        rr = random.Random(0); s = init_state(reg)
        for _ in range(40):
            s = step(s, "supportive_act" if s.clarity < 40 else "direct_confession", reg, rr)
            oc = outcome(s, reg, 40)
            if oc: break
        print(f"{reg.name:>10}: outcome={outcome(s, reg, 40)} "
              f"clarity={s.clarity:.0f} recip={s.reciprocity:.0f}")
