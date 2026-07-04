"""
NRMO 分離契約 参照 Engine (separation reference)
================================================
※ 本ファイルは「NRMO 分離契約 (propose→filter→select, ruin_penalty 排除)」の
   検証用の汎用参照実装。generator は汎用名 (ForwardPush/LowExposurePath/
   WeakDimRepair/Diversify/Baseline) で、本物の Wolf/Shinobi/MAPLayer/Norn/Skuld
   サブシステムは実コード (code/python/nrmo_v72_phase1/core/) を omega_full_integrated.py
   で駆動・検証する。本ファイルは本物の名前を騙らない。

添付批評への対応。設計契約 (合格条件 1-10):
  1. Engine は NRMO の外部にある
  2. Engine は自分で候補を生成する        (propose)
  3. NRMO は候補を削るだけ                (Governance.filter, veto only)
  4. Engine は admissible set 内だけで選ぶ (select; assert action in admissible)
  5. Engine は veto 閾値を見ない          (Governance は black box, filter() のみ)
  6. Engine は NRMO 境界を書き換えない    (Governance への参照を変異させない)
  7. Engine は失敗を学習し次回候補生成を変える (Memory → 生成分布)
  8. domain ごとの dynamics で rollout する
  9. 長期 horizon を扱える                (HorizonPolicy)
 10. 一発検証で再現できる                (run_all_validations.py)

★ruin_penalty は Engine から完全排除。
  破滅回避は NRMO が A_t を削ることのみで実現し、Engine は admissible 内で
  「最大前進」だけを選ぶ。rollout 中も各ステップで Governance.filter を黒箱として
  呼び、admissible が空 (=縁) になった枝は前進が止まる ⇒ 自然に低スコア化する。
  Engine は is_ruin も veto 閾値も一切参照しない。

自己完結 (numpy のみ)。実 nrmo_core への adapter も用意 (任意)。
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Protocol, Any, runtime_checkable

HOLD = "EXIT_HOLD"   # admissible が空のとき Engine が返す sentinel


# ============================================================
# 分離契約 (Protocols)
# ============================================================
@runtime_checkable
class Governance(Protocol):
    """NRMO 憲法層。veto only。Engine からは filter() だけが見える黒箱。"""
    def filter(self, candidates: list[np.ndarray], state: Any) -> list[np.ndarray]: ...


class DomainDynamics(Protocol):
    def clone(self, s): ...
    def transition(self, s, a, rng): ...
    def forward_value(self, s) -> float: ...   # 前進量 (domain 目的。wealth 固定ではない)
    def is_ruin(self, s) -> bool: ...           # ★Engine は呼ばない。harness/終端用のみ
    def context(self, s) -> dict: ...           # 地形特徴 (generator 用)


# ============================================================
# GoalInterpreter — 何を「前進」とみなすか (pluggable)
# ============================================================
class GoalInterpreter:
    def __init__(self, fn=None):
        self.fn = fn
    def value(self, dyn: DomainDynamics, s) -> float:
        return self.fn(dyn, s) if self.fn else dyn.forward_value(s)


# ============================================================
# 候補生成戦略 (各々が明確な機構。名前だけの空洞にしない)
# ============================================================
class Generator(Protocol):
    name: str
    def propose(self, dyn, s, ctx, rng, k: int) -> list[np.ndarray]: ...


def _clip_action(a):  # action = [g(前進), sf(安全), lr(学習), di(分散)]
    return np.clip(a, 0.0, 1.0)


class Baseline:
    name = "baseline"
    def propose(self, dyn, s, ctx, rng, k):
        return [_clip_action(np.array([g, 0.20, 0.20, 0.18]))
                for g in np.linspace(0.15, 0.70, k)]


class ForwardPush:
    """好機 (低暴露・余力) では深く攻める: 高 g・低 sf の非連続ジャンプ候補。"""
    name = "forward_push"
    def propose(self, dyn, s, ctx, rng, k):
        if not ctx.get("favorable", False):
            return []
        return [_clip_action(np.array([g, 0.05, 0.15, 0.05]))
                for g in np.linspace(0.65, 0.95, k)]


class LowExposurePath:
    """低露出ルート: 前進しつつ暴露を増やさない (高 sf+di, 中 g)。正面突破以外。"""
    name = "low_exposure"
    def propose(self, dyn, s, ctx, rng, k):
        return [_clip_action(np.array([g, 0.35, 0.25, 0.30]))
                for g in np.linspace(0.20, 0.45, k)]


class WeakDimRepair:
    """地形読み: 現在の最弱次元を補強する迂回候補を生成 (正面以外の経路)。"""
    name = "weak_dim_repair"
    def propose(self, dyn, s, ctx, rng, k):
        weak = ctx.get("weakest_dim", "G")
        # 最弱が暴露(X)なら暴露を下げる側、構造(G)なら構造を建て直す側へ振る
        if weak == "X":
            base = np.array([0.18, 0.50, 0.20, 0.25])   # 暴露低減を優先しつつ前進
        else:
            base = np.array([0.30, 0.30, 0.30, 0.20])   # 学習/構造再建寄り
        return [_clip_action(base + rng.normal(0, 0.04, 4)) for _ in range(k)]


class Diversify:
    name = "diversify"
    def propose(self, dyn, s, ctx, rng, k):
        return [_clip_action(np.array([0.35, 0.22, 0.20, d]))
                for d in np.linspace(0.25, 0.55, k)]


# ============================================================
# Memory — 失敗/成功を (局面バケット × generator) で学習し生成分布を変える
# ============================================================
class Memory:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.beta: dict[tuple, list[float]] = {}   # (bucket, gen) -> [success+1, fail+1]

    @staticmethod
    def bucket(ctx) -> tuple:
        return (ctx.get("exposure_band", "mid"), ctx.get("weakest_dim", "G"))

    def weight(self, ctx, gen_name, rng) -> float:
        if not self.enabled:
            return 1.0
        a, b = self.beta.get((self.bucket(ctx), gen_name), [1.0, 1.0])
        return float(rng.beta(a, b))            # Thompson sampling

    def update(self, ctx, gen_name, success: bool):
        if not self.enabled:
            return
        key = (self.bucket(ctx), gen_name)
        ab = self.beta.setdefault(key, [1.0, 1.0])
        ab[0 if success else 1] += 1.0


# ============================================================
# HorizonPolicy — 時系列/長期分岐の評価地平 (短期過防御・遅延破綻を回避)
# ============================================================
@dataclass
class HorizonPolicy:
    long_horizon: int = 60      # 長期評価地平 (短期 rollout の過防御を避ける)
    greedy_branch: bool = True  # rollout 内は admissible 最大前進を貪欲に継続


# ============================================================
# StrongEngine Ω Full 本体
# ============================================================
class StrongEngineOmegaFull:
    def __init__(self, generators=None, memory: Memory | None = None,
                 horizon: HorizonPolicy | None = None, candidates_per_gen: int = 3):
        self.generators = generators or [
            Baseline(), ForwardPush(), LowExposurePath(), WeakDimRepair(), Diversify()]
        self.memory = memory or Memory(enabled=True)
        self.horizon = horizon or HorizonPolicy()
        self.cpg = candidates_per_gen
        self.last_usage: dict[str, int] = {}    # 直近 propose の generator 別採用数

    # --- (2) 候補生成: 自分で出す。memory で各 generator の寄与数を変える ---
    def propose(self, dyn, s, goal, rng) -> list[tuple[np.ndarray, str]]:
        ctx = dyn.context(s)
        usage = {}
        out: list[tuple[np.ndarray, str]] = []
        for g in self.generators:
            w = self.memory.weight(ctx, g.name, rng)
            k = max(1, int(round(self.cpg * w))) if w > 0 else 0
            cands = g.propose(dyn, s, ctx, rng, k)
            usage[g.name] = len(cands)
            out += [(a, g.name) for a in cands]
        self.last_usage = usage
        return out

    # --- (4)(5)(8)(9) admissible 内のみで最大前進を選ぶ。veto 閾値も ruin も見ない ---
    def select(self, admissible: list[np.ndarray], dyn, s, goal,
               governance: Governance, rng) -> np.ndarray:
        best_a, best_score = None, -np.inf
        for a in admissible:
            score = self._forward_rollout(dyn, s, a, goal, governance, rng)
            if score > best_score:
                best_score, best_a = score, a
        return best_a

    def _forward_rollout(self, dyn, s, a, goal, governance, rng) -> float:
        """domain dynamics で a を適用後、admissible 内を貪欲前進で長期展開。
           ★スコアは前進量のみ。ruin_penalty 無し。admissible が空になれば
            前進が止まり、その枝のスコアは自然に低くなる (NRMO 効果の伝播)。"""
        cur = dyn.transition(dyn.clone(s), a, rng)
        for _ in range(self.horizon.long_horizon):
            cands = [c for c, _ in self.propose(dyn, cur, goal, rng)]
            adm = governance.filter(cands, cur)      # ★黒箱 NRMO を rollout 内でも適用
            if not adm:                              # 縁: 前進不能 → 展開停止
                break
            nxt = max(adm, key=lambda c2: goal.value(
                dyn, dyn.transition(dyn.clone(cur), c2, rng)))
            cur = dyn.transition(cur, nxt, rng)
        return goal.value(dyn, cur)

    # --- 1 ステップ: propose → NRMO.filter → select。完全分離 ---
    def step(self, governance: Governance, dyn, s, goal, rng):
        proposals = self.propose(dyn, s, goal, rng)
        cands = [a for a, _ in proposals]
        admissible = governance.filter(cands, s)        # (3) NRMO が削るだけ
        if not admissible:                               # empty → HOLD
            return HOLD, None
        action = self.select(admissible, dyn, s, goal, governance, rng)
        # (4) 不変条件: 選択は必ず admissible 内
        assert any(np.array_equal(action, c) for c in admissible), \
            "selected action must be in admissible set"
        # (7) 学習: 選んだ action を出した generator の成否を memory に反映
        gen = next((g for c, g in proposals if np.array_equal(c, action)), "baseline")
        ns = dyn.transition(dyn.clone(s), action, rng)
        success = (goal.value(dyn, ns) > goal.value(dyn, s)) and \
                  bool(governance.filter(
                      [a for a, _ in self.propose(dyn, ns, goal, rng)], ns))
        self.memory.update(dyn.context(s), gen, success)
        return action, gen
