"""
import os
NRMO v7 Phase D — collective_engine の二層構造接続 (実コード接続版)
================================================================

Master Spec §8 の設計に忠実な実装。

【現実側】CollectiveStrongEngine (collective_engine_v71.py の実クラス)
  集団全体を最大前進させる。破滅の縁 (shock 接近) で triage / insurance により
  「集団を守りながら前進」(止めるのではなく方向転換)。
  - forecast_next_shock → 縁の検出 (detect_edge 相当)
  - select_configuration → 集団の最大前進 action (実コードのパイプライン)

【civ-sim 側】集団 MaxForwardEngine (本ファイル)
  攻撃 (全体成長) 〜 防御 (triage退避) の連続 spectrum を、
  ★真の集団 dynamics★ で ★長期地平★ にわたり死を恐れず試し、
  攻撃ピーク / 防御ピーク / 最善構成を算出する。

【第4原則の徹底】
  実 CollectiveStrongEngine の内部スコアリングは _rollout_collective という
  「軽量固定モデル」を使っている (collective_engine_v71.py L667 のコメント参照:
   "lightweight model ... without invoking the full agent population step")。
  これは引き継ぎ書 §7 が禁じる「engine 内部に civ-sim 固定 dynamics を持たせる」
  反パターン。Phase D ではスコアリングを civ-sim 側の真の集団 dynamics・長期地平に
  置き換える。

【双方向】observe() / feedback() で現実 ⇄ civ-sim が情報蓄積。

【世界依存性】穏やかな世界 = 攻撃最善 / fat-tail 世界 = 保険込みが最善 を spectrum 探索で発見。
【評価地平】長期評価が必須。ただし最善の向きは domain 構造依存:
  ・単一文明 domain (§8/文明): 短期→防御, 長期→成長 (成長複利が地平で顕在化)
  ・本 集団保険 domain         : 短期→攻撃, 長期→やや防御 (薄保険の累積tailが顕在化)
  両者とも「長期評価が真のコスト構造を顕在化させる」点は共通 (第1原則)。
"""
from __future__ import annotations
import sys, os, copy
from dataclasses import dataclass, field
from typing import Any
import numpy as np

# --- 実コード (現実側 engine) を読み込む ---
_V6_SRC = os.environ.get(
    "NRMO_V6_SRC", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "..", "world_sim_v50", "src"))
sys.path.insert(0, _V6_SRC)
from collective_engine_v71 import (   # 実コード
    CollectiveStrongEngine, CollectiveEngineConfig, CollectiveConfiguration,
    forecast_next_shock, CollectiveEngineState,
)


# ============================================================
# 集団 domain の「真の」状態 (現実側がこの上で最大前進する)
# ============================================================
@dataclass
class CollectiveState:
    """集団 (多 lineage 文明) の真の動態状態。"""
    W: float = 100.0      # 集団総産出 (= 前進量 / wealth)
    D: float = 1.0        # 多様性 (lineage entropy proxy) 0..1.5
    C: float = 0.5        # 結束 cohesion 0..1
    X: float = 30.0       # shock 暴露 0..100
    cont: float = 1.0     # 継続性 / 生存性 0..1
    pf: float = 0.30      # family pool (薄い初期値: 保険は積み立てて作る)
    pl: float = 0.30      # lineage pool
    pc: float = 0.30      # civ pool
    t: int = 0

    def copy(self) -> "CollectiveState":
        return copy.copy(self)


def config_from_aggression(a: float) -> CollectiveConfiguration:
    """スカラ a∈[0,1] を実 CollectiveConfiguration にマップ。
       a=0 → 全攻撃 (成長最大・保険最小) / a=1 → 全防御 (triage退避・保険最大)。
       停滞は spectrum に含めない (両端とも前進方向の選択)。"""
    a = float(np.clip(a, 0.0, 1.0))
    return CollectiveConfiguration(
        family_pool_rate = 0.08 + 0.30 * a,
        lineage_pool_rate= 0.05 + 0.22 * a,
        civ_pool_rate    = 0.03 + 0.16 * a,
        family_coverage  = 0.40 + 0.45 * a,
        lineage_coverage = 0.25 + 0.45 * a,
        civ_coverage     = 0.15 + 0.40 * a,
        budget_augment_multiplier = 1.0 + 0.6 * a,
        # triage 重み: 防御寄りほど脆弱性/多様性を優先
        triage_w_knowledge   = 0.30 - 0.05 * a,
        triage_w_productivity= 0.25 - 0.05 * a,
        triage_w_diversity   = 0.20 + 0.10 * a,
        triage_w_vulnerability=0.25 + 0.10 * a,
        rescue_rate_cap  = 0.15 + 0.25 * a,
    )


def _aggression_of(cfg: CollectiveConfiguration) -> float:
    """config の攻撃度を逆算 (budget_augment を代理に)。0=攻撃 1=防御。"""
    return float(np.clip((cfg.budget_augment_multiplier - 1.0) / 0.6, 0.0, 1.0))


# ============================================================
# 集団 domain の「真の」 dynamics (DomainDynamics プロトコル)
#   ★ engine 内部の軽量固定 rollout を使わず、ここで真の動態を回す (第4原則)
# ============================================================
class CollectiveDomainDynamics:
    """集団を現実 domain として扱う真の dynamics。

    成長 (攻撃) と triage/insurance (防御) のトレードオフを、shock・fat-tail・
    停滞ブリード込みでモデル化。世界 (world_params) 次第で最善が攻撃/防御に動く。
    """
    def __init__(self, world_params: dict | None = None):
        self.wp = world_params or dict(
            base_growth=0.050, shock_probability=0.18, shock_scale=5.0,
            tail_probability=0.07, tail_scale=28.0, environmental_drag=0.012,
            exposure_drift=0.4)

    # --- protocol ---
    def clone(self, s: CollectiveState) -> CollectiveState:
        return s.copy()

    def wealth(self, s: CollectiveState) -> float:
        # 前進量 = 総産出を多様性で割引調整 (monoculture は脆い)
        return s.W * (0.6 + 0.4 * min(1.0, s.D))

    def is_ruin(self, s: CollectiveState) -> bool:
        return (s.cont <= 0.05) or (s.W <= 35.0) or (s.D <= 0.05)

    def is_terminal(self, s: CollectiveState) -> bool:
        return False

    def detect_edge(self, s: CollectiveState) -> bool:
        # 破滅の縁: 暴露高 / 継続性低下 / 多様性低下 (やや早めに検出して破滅成分を削る)
        return (s.X > 52.0) or (s.cont < 0.68) or (s.D < 0.48)

    def detect_favorable(self, s: CollectiveState) -> bool:
        return (s.X < 40.0) and (s.cont > 0.85) and (s.C > 0.45)

    def default_action(self, s: CollectiveState) -> CollectiveConfiguration:
        return config_from_aggression(0.20)   # 最大前進寄り default

    def action_spectrum(self, s: CollectiveState):
        # 攻撃(成長最大, rank0) → 防御(triage退避最大, rank last). 停滞は含めない.
        return [config_from_aggression(a) for a in (0.0, 0.25, 0.5, 0.75, 1.0)]

    # --- 真の遷移 ---
    def transition(self, s: CollectiveState, cfg: CollectiveConfiguration,
                   rng: np.random.Generator) -> CollectiveState:
        wp = self.wp
        ns = s.copy(); ns.t = s.t + 1

        a = _aggression_of(cfg)                         # 0 攻撃 .. 1 防御
        # 保険に振り向ける資源は成長から差し引かれる (protection drag)
        protection_drag = (cfg.family_pool_rate + cfg.lineage_pool_rate +
                           cfg.civ_pool_rate) * cfg.budget_augment_multiplier
        net_growth = wp["base_growth"] * (1.0 - 0.35 * protection_drag) \
                     - wp["environmental_drag"]
        ns.W *= (1.0 + net_growth)

        # pool への積み立て (継続性に比例)
        ns.pf += cfg.family_pool_rate * ns.cont
        ns.pl += cfg.lineage_pool_rate * ns.cont
        ns.pc += cfg.civ_pool_rate * ns.cont

        # shock (通常 + fat-tail). 需要は集団規模に比例 (大文明ほど大災害)
        if rng.random() < wp["shock_probability"]:
            if rng.random() < wp["tail_probability"]:
                mag = rng.exponential(wp["tail_scale"]) / 30.0   # 巨大 shock
            else:
                mag = rng.exponential(wp["shock_scale"]) / 30.0
            size_factor = float(np.sqrt(max(1.0, ns.W) / 100.0))
            demand = mag * (0.5 + 0.01 * s.X) * size_factor      # 暴露・規模で増幅
            # 階層保険で rescue (triage は有効 coverage を底上げ)
            triage_eff = 1.0 + 0.25 * a
            cov_f = min(demand, ns.pf * cfg.family_coverage) * cfg.budget_augment_multiplier * triage_eff
            demand -= cov_f; ns.pf = max(0.0, ns.pf - cov_f)
            cov_l = min(max(0, demand), ns.pl * cfg.lineage_coverage) * cfg.budget_augment_multiplier * triage_eff
            demand -= cov_l; ns.pl = max(0.0, ns.pl - cov_l)
            cov_c = min(max(0, demand), ns.pc * cfg.civ_coverage) * cfg.budget_augment_multiplier * triage_eff
            demand -= cov_c; ns.pc = max(0.0, ns.pc - cov_c)
            uncovered = max(0.0, demand)
            ns.cont = ns.cont - uncovered * 0.50
            ns.W   *= (1.0 - min(0.6, uncovered * 0.30))
            ns.D    = ns.D - uncovered * 0.12
            ns.C    = ns.C + 0.04 * (cov_f + cov_l + cov_c) - 0.08 * uncovered
        else:
            ns.cont = min(1.0, ns.cont + 0.02)   # 平時はゆるやか回復

        # ★ 停滞 = ruin: 過度な防御で純成長がほぼ無いと passive death が進む
        if net_growth < 0.005:
            ns.cont -= 0.04
            ns.D    -= 0.01

        # 暴露ドリフト / 減衰 / clip
        ns.X = s.X + wp["exposure_drift"] * (0.5 + net_growth * 5) - 0.3 * (cov_f if 'cov_f' in dir() else 0)
        ns.pf *= 0.92; ns.pl *= 0.92; ns.pc *= 0.92
        ns.C  = float(np.clip(ns.C * 0.99, 0.0, 1.0))
        ns.D  = float(np.clip(ns.D, 0.0, 1.5))
        ns.cont = float(np.clip(ns.cont, 0.0, 1.0))
        ns.X  = float(np.clip(ns.X, 0.0, 100.0))
        return ns


# ============================================================
# civ-sim 側: 集団 MaxForwardEngine
#   真の集団 dynamics を長期地平で回し、攻撃/防御ピーク・最善構成を算出
# ============================================================
class CollectiveMaxForwardEngine:
    def __init__(self, n_trials: int = 6, sim_horizon: int = 60,
                 viable_survival: float = 0.5):
        self.n_trials = n_trials
        self.sim_horizon = sim_horizon          # ★長期地平が default
        self.viable_survival = viable_survival
        self.memory: list[dict] = []

    def explore(self, dyn: CollectiveDomainDynamics, state: CollectiveState,
                rng: np.random.Generator) -> dict:
        spectrum = list(dyn.action_spectrum(state))
        results = []
        for rank, cfg in enumerate(spectrum):
            survs = deaths = 0
            wealths = []
            for _ in range(self.n_trials):
                s = dyn.clone(state); died = False
                for _ in range(self.sim_horizon):
                    s = dyn.transition(s, cfg, rng)     # 真の dynamics (死は許容)
                    if dyn.is_ruin(s): died = True; break
                    if dyn.is_terminal(s): break
                if died: deaths += 1
                else: survs += 1; wealths.append(dyn.wealth(s))
            results.append(dict(
                rank=rank, aggression=_aggression_of(cfg), cfg=cfg,
                survival=survs / self.n_trials, death=deaths / self.n_trials,
                wealth=(float(np.mean(wealths)) if wealths else -1e9)))

        def score(r): return r["wealth"] * (r["survival"] ** 0.5)
        best = max(results, key=score)
        viable = [r for r in results if r["survival"] >= self.viable_survival]
        attack_peak  = min(viable, key=lambda r: r["rank"]) if viable else results[-1]
        defense_peak = max(viable, key=lambda r: r["rank"]) if viable else results[0]
        return dict(results=results, best=best, attack_peak=attack_peak,
                    defense_peak=defense_peak, best_score=score(best))

    def feedback(self, info: dict) -> None:
        self.memory.append(info)


# ============================================================
# 現実側: CollectiveStrongEngine を二層構造に接続する bridge
# ============================================================
class CollectiveStrongEngineRealSide:
    """現実側の主役。実 CollectiveStrongEngine を保持し、
       破滅を避けつつ集団を最大前進させる。縁では triage 方向転換。
       スコアリングは civ-sim (真の dynamics・長期地平) に委譲 (第4原則)。"""

    def __init__(self, civsim: CollectiveMaxForwardEngine,
                 civ_name: str = "civ0",
                 engine_cfg: CollectiveEngineConfig | None = None):
        self.civsim = civsim
        # ★実コードの現実側 engine を実体として保持 (実コード接続)
        self.real_engine = CollectiveStrongEngine(civ_name, engine_cfg)
        self.history: list[dict] = []

    def decide(self, dyn: CollectiveDomainDynamics, s: CollectiveState,
               rng: np.random.Generator) -> CollectiveConfiguration:
        # 1) civ-sim に真の dynamics・長期地平で攻撃/防御ピーク・最善を算出させる
        peaks = self.civsim.explore(dyn, s, rng)
        best_cfg = peaks["best"]["cfg"]

        # 2) 実 CollectiveStrongEngine の forecast で破滅の縁を検出 (W)
        forecast = forecast_next_shock(
            self.real_engine.state, s.X, dyn.wp, self.real_engine.cfg)

        # 3) 縁では「止める」のではなく triage 方向転換 (より防御寄りへ前進)
        #    縁判定は状態ベース (detect_edge) 主体。forecast は高基準の補助
        #    (低基準だと world_params 成分が張り付き常時防御=過度な防御に倒れる)。
        at_edge = dyn.detect_edge(s) or (forecast >= 0.60)
        if at_edge:
            # civ-sim の防御ピーク (生存可能な最も防御的) へ寄せる = 守りながら前進
            redirected = peaks["defense_peak"]["cfg"]
            chosen = redirected
            mode = "edge_triage_redirect"
        else:
            chosen = best_cfg                 # 平時は最大前進 (civ-sim 最善)
            mode = "max_forward"

        self.real_engine.state.shock_history.append(forecast)
        self.history.append(dict(mode=mode, forecast=forecast,
                                 aggression=_aggression_of(chosen)))
        return chosen

    def observe(self, cfg, next_state: CollectiveState,
                dyn: CollectiveDomainDynamics) -> None:
        info = dict(aggression=_aggression_of(cfg),
                    wealth=dyn.wealth(next_state),
                    cont=next_state.cont, ruin=dyn.is_ruin(next_state))
        self.civsim.feedback(info)

    def real_engine_call(self, s: CollectiveState, dyn: CollectiveDomainDynamics,
                         rng: np.random.Generator):
        """実 CollectiveStrongEngine.select_configuration を実際に呼ぶ
           (実コード接続の実証用)。"""
        class _CivStateShim:  # civ_state.X が必要
            def __init__(self, X): self.X = X
        return self.real_engine.select_configuration(
            civ_state=_CivStateShim(s.X), world_params=dyn.wp,
            pool_levels=dict(family=s.pf, lineage=s.pl, civ=s.pc, cohesion=s.C),
            pressure_indicators=dict(inequality=0.2, exposure=s.X / 100.0),
            partner_civs=[], partner_balances={}, partner_states={},
            rivalry_pairs={}, inequality=0.2, rng=rng)


# ============================================================
# 検証
# ============================================================
def run_real_side(dyn: CollectiveDomainDynamics, horizon: int, n_seeds: int,
                  sim_horizon: int):
    """現実側 (二層) を horizon 世代まわし ruin率・最終 wealth を測る。"""
    rr, finals, modes = [], [], []
    for seed in range(n_seeds):
        rng = np.random.default_rng(1000 + seed)
        civ = CollectiveMaxForwardEngine(n_trials=4, sim_horizon=sim_horizon)
        strong = CollectiveStrongEngineRealSide(civ)
        s = CollectiveState(); ruined = False
        for _ in range(horizon):
            cfg = strong.decide(dyn, s, rng)
            s = dyn.transition(s, cfg, rng)
            strong.observe(cfg, s, dyn)
            if dyn.is_ruin(s): ruined = True; break
        rr.append(ruined)
        finals.append(dyn.wealth(s) if not ruined else 0.0)
        modes += [h["mode"] for h in strong.history]
    redirect_rate = (modes.count("edge_triage_redirect") / len(modes)) if modes else 0.0
    surv_w = [f for f in finals if f > 0]
    return dict(ruin=float(np.mean(rr)),
                final_wealth=(float(np.mean(surv_w)) if surv_w else 0.0),
                redirect_rate=redirect_rate)


def civsim_best_aggression(dyn, sim_horizon, seed=0):
    civ = CollectiveMaxForwardEngine(n_trials=6, sim_horizon=sim_horizon)
    pk = civ.explore(dyn, CollectiveState(), np.random.default_rng(seed))
    return pk


if __name__ == "__main__":
    print("=" * 64)
    print("Phase D: collective_engine 二層構造接続 (実コード CollectiveStrongEngine)")
    print("=" * 64)

    # --- A. 実コード接続の実証: 実 select_configuration を呼ぶ ---
    dyn0 = CollectiveDomainDynamics()
    civ = CollectiveMaxForwardEngine()
    strong = CollectiveStrongEngineRealSide(civ)
    cfg_real, diag = strong.real_engine_call(CollectiveState(), dyn0,
                                             np.random.default_rng(0))
    print("\n[A] 実 CollectiveStrongEngine.select_configuration 実行 OK:")
    print(f"    forecast={diag['forecast']:.3f}  n_admissible={diag['n_admissible']}"
          f"  best_archetype={diag.get('best_archetype')}")
    print(f"    → 実コード接続 確認。ただし内部スコアは _rollout_collective (軽量固定)。")
    print(f"      Phase D ではスコアを civ-sim 真 dynamics・長期地平に置換 (第4原則)。")

    # --- B. 世界依存性: 穏やかな世界 vs fat-tail 世界 ---
    calm = CollectiveDomainDynamics(dict(
        base_growth=0.050, shock_probability=0.06, shock_scale=4.0,
        tail_probability=0.005, tail_scale=18.0, environmental_drag=0.010,
        exposure_drift=0.3))
    fattail = CollectiveDomainDynamics(dict(
        base_growth=0.045, shock_probability=0.22, shock_scale=6.0,
        tail_probability=0.10, tail_scale=30.0, environmental_drag=0.018,
        exposure_drift=0.6))
    print("\n[B] 世界依存性 (civ-sim 探索, 長期地平 sim_horizon=60):")
    for name, d in (("穏やかな世界", calm), ("fat-tail 世界", fattail)):
        pk = civsim_best_aggression(d, sim_horizon=60)
        b = pk["best"]
        print(f"  {name}: 最善 aggression={b['aggression']:.2f} "
              f"(survival={b['survival']:.0%} wealth={b['wealth']:.0f})  "
              f"攻撃ピーク a={pk['attack_peak']['aggression']:.2f} / "
              f"防御ピーク a={pk['defense_peak']['aggression']:.2f}")
        for r in pk["results"]:
            print(f"      a={r['aggression']:.2f}: surv={r['survival']:.0%} "
                  f"wealth={r['wealth']:.0f}")

    # --- C. 評価地平: domain 構造で向きが変わる (正直な所見) ---
    print("\n[C] 評価地平の効果 (標準世界, civ-sim 最善 aggression: 0=攻撃 1=防御):")
    for h in (8, 20, 60, 120):
        pk = civsim_best_aggression(dyn0, sim_horizon=h)
        print(f"  sim_horizon={h:3d}: 最善 aggression={pk['best']['aggression']:.2f} "
              f"(wealth={pk['best']['wealth']:.0f})")
    print("  所見: この集団保険 domain では 短期→攻撃 / 長期→やや防御(保険) が最善。")
    print("        理由: 保険が薄い攻撃側の破滅リスクは地平とともに累積するため、")
    print("        長期評価ほど保険(triage)が報われる。これは単一文明 domain の")
    print("        §8/文明 (短期→防御, 長期→成長; 成長複利が地平で顕在化) とは")
    print("        ★逆向き★。どちらも『長期評価が真のコスト構造を顕在化させる』点は")
    print("        共通で、顕在化するコスト (複利成長 vs 累積tail) が domain で異なる。")
    print("        → 評価地平は必須だが、最善の向きは世界依存 + domain構造依存 (第1原則)。")

    # --- D. 現実側二層の動作 (ruin率・縁での triage 方向転換率) ---
    print("\n[D] 現実側二層 (CollectiveStrongEngineRealSide) の動作:")
    for name, d in (("標準世界", dyn0), ("fat-tail 世界", fattail)):
        r = run_real_side(d, horizon=80, n_seeds=40, sim_horizon=40)
        print(f"  {name}: ruin={r['ruin']:.0%}  最終wealth(生存時)={r['final_wealth']:.0f}"
              f"  縁での triage方向転換率={r['redirect_rate']:.0%}")
