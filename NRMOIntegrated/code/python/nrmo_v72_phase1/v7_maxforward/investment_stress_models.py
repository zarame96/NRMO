"""
investment_stress_models.py — 自己完結 投資ストレス proxy モデル。
(旧: 外部 bundle 依存 → パッケージ内自己完結化)

注意: これは parametric *proxy* market dynamics であり、真の市場 dynamics でも
予測でもない。MaxForwardEngine の前進/非破滅挙動が相場レジームへ適応するかを
seed 固定で再現検証するための合成シナリオである。
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass

# 各シナリオの (drift μ, 通常 vol σ, crash 確率 p, crash 規模) — proxy パラメータ
_SCENARIOS = {
    "secular_bull":       dict(mu=0.0006, sd=0.009, crash_p=0.002, crash=-0.05),
    "slow_bear":          dict(mu=-0.0004, sd=0.012, crash_p=0.004, crash=-0.06),
    "fat_tail_crash":     dict(mu=0.0004, sd=0.010, crash_p=0.020, crash=-0.14),
    "inflation_cash_drag":dict(mu=0.0003, sd=0.011, crash_p=0.003, crash=-0.06),
}


class MarketScenario:
    """seed 固定で決定論的な equity return 系列を生成する proxy シナリオ。"""
    def __init__(self, name: str, seed: int, n_steps: int = 300):
        if name not in _SCENARIOS:
            raise ValueError(f"unknown scenario: {name}")
        self.name = name
        self.n_steps = n_steps
        p = _SCENARIOS[name]
        rng = np.random.default_rng(seed)
        # 通常リターン + 稀な fat-tail crash を事前生成 (決定論的)
        base = rng.normal(p["mu"], p["sd"], size=n_steps)
        crash_mask = rng.random(n_steps) < p["crash_p"]
        base[crash_mask] += p["crash"]
        self._returns = base
        self._vols = np.abs(base)
        self._i = 0

    def step(self):
        """(eqret, vol) を 1 期返す。系列末尾を超えたら最終分布で継続。"""
        if self._i < self.n_steps:
            r = float(self._returns[self._i]); v = float(self._vols[self._i])
            self._i += 1
        else:
            r, v = float(self._returns[-1]), float(self._vols[-1])
        return r, v


@dataclass
class StaticResult:
    scenario: str
    policy: str
    final_value: float
    peak: float
    max_drawdown: float


def run_static_policy(scenario: str, policy: str, seed: int, n_steps: int = 300) -> StaticResult:
    """固定ポリシー (例 buyhold_60 = equity 60% 固定) のベンチ値を返す。"""
    eq = 0.60 if policy == "buyhold_60" else float(policy.split("_")[-1]) / 100.0 \
        if policy.replace("_", "").split("_")[-1].isdigit() else 0.60
    cr = -0.00018 if scenario == "inflation_cash_drag" else 0.0
    mkt = MarketScenario(scenario, seed, n_steps)
    value, peak = 100.0, 100.0
    for _ in range(n_steps):
        eqret, _ = mkt.step()
        pret = eq * eqret + (1 - eq) * cr
        value *= (1 + pret)
        peak = max(peak, value)
    mdd = (peak - value) / peak if peak > 0 else 0.0
    return StaticResult(scenario, policy, value, peak, mdd)


if __name__ == "__main__":
    for sc in _SCENARIOS:
        r = run_static_policy(sc, "buyhold_60", 0)
        print(f"{sc:>20}: buyhold60 final={r.final_value:.1f} mdd={r.max_drawdown:.0%}")
