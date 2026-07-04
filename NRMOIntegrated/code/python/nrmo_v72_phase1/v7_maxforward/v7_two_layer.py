"""
NRMO v7 二層構造 — 設計者意図の正しい実装
==========================================

【現実側】StrongEngine Ω Full
  主役。あらゆる探索・推論・意思決定 (範囲無制限)。
  現実 domain の真の dynamics で最大前進。破滅は避ける。
  civ-sim には接続せず、civ-sim の知見 (ピーク・最善スコア) を使う。
  Loom layer もこちら側 (現実側)。

【civ-sim 側】MaxForwardEngine
  StrongEngine Ω Full に接続し、バーチャル環境内でそれを模倣する。
  ・超積極的な死・破滅を許容 (フィードバックを得るため)
  ・極端な慎重は排除
  ・極端な攻撃性のピークと極端な防御のピークを算出し、最善スコアを目指す

【双方向】現実 ⇄ civ-sim が情報をやり取りして蓄積する。
"""
from __future__ import annotations
from typing import Any
import numpy as np


class MaxForwardEngine:
    """civ-sim 側。死を恐れず攻撃/防御の極端を試し、ピークと最善スコアを算出する。

    現実ではないので破滅してよい。破滅は罰ではなくフィードバック信号。
    極端な慎重 (停滞) は spectrum から既に除外されている (DomainDynamics 側)。
    """

    def __init__(self, n_trials: int = 6, sim_horizon: int = 20,
                 viable_survival: float = 0.5):
        self.n_trials = n_trials
        self.sim_horizon = sim_horizon
        self.viable_survival = viable_survival
        self.memory: list[dict] = []   # 現実からのフィードバック蓄積

    def explore(self, dyn, state: Any, rng: np.random.Generator) -> dict:
        """攻撃〜防御の spectrum を civ-sim 内で全部試す (死を許容)。
        攻撃ピーク / 防御ピーク / 最善スコアを返す。"""
        spectrum = list(dyn.action_spectrum(state))
        results = []
        for rank, action in enumerate(spectrum):
            survs, deaths = 0, 0
            wealths = []
            for _ in range(self.n_trials):
                s = dyn.clone(state)
                died = False
                for _ in range(self.sim_horizon):
                    s = dyn.transition(s, action, rng)
                    if dyn.is_ruin(s):          # 死は許容: 記録するだけ
                        died = True
                        break
                    if dyn.is_terminal(s):
                        break
                if died:
                    deaths += 1
                else:
                    survs += 1
                    wealths.append(dyn.wealth(s))
            results.append({
                "rank": rank, "action": action,
                "survival": survs / self.n_trials,
                "death": deaths / self.n_trials,
                "wealth": (float(np.mean(wealths)) if wealths else -1e9),
            })

        # 最善スコア: 生存を担保しつつ富 (前進量) を最大化
        #   survival を sqrt で効かせ、生存しない極端攻撃を割り引く
        def score(r): return r["wealth"] * (r["survival"] ** 0.5)
        best = max(results, key=score)

        # 攻撃ピーク = 生存可能な範囲で最も攻撃的 (rank 最小)
        viable = [r for r in results if r["survival"] >= self.viable_survival]
        attack_peak = min(viable, key=lambda r: r["rank"]) if viable else results[-1]
        defense_peak = max(viable, key=lambda r: r["rank"]) if viable else results[0]

        return {"results": results, "best": best,
                "attack_peak": attack_peak, "defense_peak": defense_peak,
                "best_score": score(best)}

    def feedback(self, info: dict) -> None:
        """現実側からの実行結果を蓄積 (双方向)。"""
        self.memory.append(info)


class StrongEngineOmegaFull:
    """現実側。あらゆる探索・推論・意思決定を担う主役。

    civ-sim (MaxForwardEngine) に「攻撃/防御の極端を試して最善を出して」と依頼し、
    その最善スコアの行動で現実を最大前進させる。現実では破滅を避ける。
    """

    def __init__(self, civsim: MaxForwardEngine):
        self.civsim = civsim
        self.history: list[dict] = []

    def decide(self, dyn, state: Any, rng: np.random.Generator) -> Any:
        peaks = self.civsim.explore(dyn, state, rng)
        # civ-sim が算出した最善スコアの行動で前進
        return peaks["best"]["action"]

    def observe(self, action, next_state, dyn) -> None:
        """現実の実行結果を civ-sim にフィードバック (双方向蓄積)。"""
        info = {"action": str(action), "wealth": dyn.wealth(next_state),
                "ruin": dyn.is_ruin(next_state)}
        self.history.append(info)
        self.civsim.feedback(info)


if __name__ == "__main__":
    civ = MaxForwardEngine()
    strong = StrongEngineOmegaFull(civ)
    print("二層構造 OK:")
    print("  現実側 StrongEngine Ω Full → civsim に接続:", strong.civsim is civ)
    print("  civ-sim MaxForwardEngine: n_trials=%d, sim_horizon=%d" % (civ.n_trials, civ.sim_horizon))
