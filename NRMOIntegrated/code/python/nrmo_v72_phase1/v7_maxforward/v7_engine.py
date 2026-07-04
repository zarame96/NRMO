"""
NRMO v7 Engine — Max-Forward Principle の正式実装
=================================================

設計者意図 (NRMO Constitution v7) の正式コード化。

旧 OmegaFullEngine の問題:
  rollout が civ-sim dynamics (civstate_transition) を内部固定で持ち、
  適用先 domain と乖離 → domain での最大前進を選べず破滅 (store で実証)。

v7 の解決 (第4原則):
  engine は domain の真の dynamics で rollout する。
  state/action は domain-native のまま (変換による情報損失を排除)。
  OmegaFullEngine の機能 (Wolf Pursuit / Edge Guard / MC rollout / portfolio)
  を domain-agnostic に移植。

第1原則: default = 最大前進
第2原則: 破滅成分だけ削る
第3原則: 停滞は ruin として候補から排除
第4原則: rollout は domain の真の dynamics で
第5原則: 前進と方向転換は rollout から創発させる
"""
from __future__ import annotations
from typing import Protocol, Any, Sequence, runtime_checkable
import numpy as np


@runtime_checkable
class DomainDynamics(Protocol):
    """各 domain が実装する真の dynamics. engine はこれを rollout に使う."""

    def clone(self, state: Any) -> Any:
        """state の独立コピー (rollout の副作用防止)."""
        ...

    def transition(self, state: Any, action: Any, rng: np.random.Generator) -> Any:
        """真の 1-step 遷移. ★ここが domain の真の世界."""
        ...

    def is_ruin(self, state: Any) -> bool:
        """不可逆破滅 (absorbing ruin) か."""
        ...

    def is_terminal(self, state: Any) -> bool:
        """非破滅の終端 (例: romance の success/graceful_exit 確定). 既定 False."""
        ...

    def wealth(self, state: Any) -> float:
        """前進・富の指標 (大きいほど前進). 停滞は増えない."""
        ...

    def candidate_actions(self, state: Any, wolf: bool, edge: bool) -> Sequence[Any]:
        """行動候補. 第1原則=最大前進中心. 第3原則=停滞は含めない.
        edge(縁) のときだけ前進方向を変える候補を足す (止まらない)."""
        ...

    def default_action(self, state: Any) -> Any:
        """rollout 内の default = その domain の最大前進."""
        ...

    def detect_favorable(self, state: Any) -> bool:
        """Wolf Pursuit: 好機か (より深く読み、より攻める)."""
        ...

    def detect_edge(self, state: Any) -> bool:
        """Edge Guard: 不可逆破滅の縁か (前進方向を変える)."""
        ...


class MaxForwardEngine:
    """OmegaFullEngine の思想を domain-native に移植した v7 engine.

    Wolf Pursuit + Edge Guard + MC rollout (domain dynamics) で
    「破滅しない範囲での最大前進」を rollout から創発させる.
    """

    def __init__(self, base_depth: int = 6, wolf_depth: int = 10,
                 repeats: int = 4, ruin_penalty: float = 1e5):
        self.base_depth = base_depth
        self.wolf_depth = wolf_depth
        self.repeats = repeats
        self.ruin_penalty = ruin_penalty

    def _rollout_value(self, dyn: DomainDynamics, state: Any, action: Any,
                       depth: int, rng: np.random.Generator) -> float:
        """1 候補を domain dynamics で MC rollout し価値を返す.
        破滅は大罰 (第2原則: 破滅成分を削る).
        その後は default=最大前進 で継続 (第1原則).
        生存して富が増えるほど高評価. 停滞は富が増えず低評価 (第3原則)."""
        total = 0.0
        for _ in range(self.repeats):
            s = dyn.clone(state)
            s = dyn.transition(s, action, rng)
            if dyn.is_ruin(s):
                total -= self.ruin_penalty
                continue
            if dyn.is_terminal(s):          # 非破滅の終端 (romance success 等)
                total += dyn.wealth(s)
                continue
            ruined = False
            for _ in range(depth - 1):
                s = dyn.transition(s, dyn.default_action(s), rng)
                if dyn.is_ruin(s):
                    total -= self.ruin_penalty * 0.5
                    ruined = True
                    break
                if dyn.is_terminal(s):       # 終端確定で rollout 終了
                    break
            if not ruined:
                total += dyn.wealth(s)   # 生存前提の富 = 前進量
        return total / self.repeats

    def decide(self, dyn: DomainDynamics, state: Any,
               rng: np.random.Generator) -> Any:
        """第1-5原則に従って action を選ぶ.

        - wolf(好機): 深く読んで攻める (Wolf Pursuit)
        - edge(縁):   前進方向を変える候補を加える (Edge Guard, 止まらない)
        - 各候補を domain dynamics で rollout し、最大前進を創発させる
        """
        wolf = dyn.detect_favorable(state)
        edge = dyn.detect_edge(state)
        candidates = list(dyn.candidate_actions(state, wolf, edge))
        if not candidates:
            return dyn.default_action(state)   # 最悪でも最大前進 (停滞しない)
        depth = self.wolf_depth if wolf else self.base_depth
        best, best_val = candidates[0], -np.inf
        for action in candidates:
            v = self._rollout_value(dyn, state, action, depth, rng)
            if v > best_val:
                best_val, best = v, action
        return best


# ============================================================
# 自己テスト: import できるか + protocol の最小確認
# ============================================================
if __name__ == "__main__":
    eng = MaxForwardEngine()
    print("MaxForwardEngine OK:",
          f"base_depth={eng.base_depth}, wolf_depth={eng.wolf_depth}, repeats={eng.repeats}")
    print("DomainDynamics protocol methods:",
          [m for m in dir(DomainDynamics) if not m.startswith("_")])
