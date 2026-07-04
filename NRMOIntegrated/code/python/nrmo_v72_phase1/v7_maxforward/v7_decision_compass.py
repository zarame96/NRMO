"""
import os
NRMO v7 Phase E — DecisionCompass の二層構造化 (実コード接続)
============================================================

Master Spec §5 の設計に忠実な実装。

DecisionCompass = 現実の個人意思決定アプリ = 完全に現実側。
  ・搭載 engine   = StrongEngine Ω Full (現実 domain = 個人の意思決定)
  ・civ-sim       = MaxForwardEngine を内部に持ち、選択肢の極端を試して最善を算出
  ・憲法境界(Loom) = 実 nrmo_core (governance: YES/NO/HOLD のみ。rank/score/select しない)
  ・出力          = ユーザーに見せるのは「破滅しない最大前進」の提案

【gov-exec 分離 (不可侵)】
  governance (nrmo_core) が admissible set A_t = NRMO(X_t) を構築。
  engine (二層) は A_t の中だけで探索: a_t = Engine(A_t)。
  engine は veto ロジック・閾値を一切見ない。admissible set を override できない。

【第4原則】rollout は対象 domain のdomain-native proxy dynamics (civstate_transition) で行う。
【Max-Forward】default = 最大前進。停滞 (過剰な慎重) は spectrum から除外。
              破滅成分だけ governance が削る。縁では HOLD (止めるのではなく方向転換指示)。
"""
from __future__ import annotations
import sys, os
import numpy as np

# --- 実コード読み込み ---
_V6 = os.environ.get("NRMO_ROOT_PATH", os.environ.get("NRMO_V6_ROOT",
      os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")))
sys.path.insert(0, os.path.join(_V6, "v52_codebase"))
sys.path.insert(0, os.path.join(_V6, "world_sim_v50", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from governance.nrmo_core import construct_admissible_set   # 実 governance (veto)
from core.state import CivState                              # 6D 個人状況ベクトル
from vnext_plus import civstate_transition, is_ruin_state, RolloutConfig  # domain-native proxy dynamics
from v7_two_layer import MaxForwardEngine, StrongEngineOmegaFull          # v7 二層 engine


# ============================================================
# 個人意思決定 domain (CivState を「個人の状況」として再解釈)
#   R=資源/蓄え E=心身/環境 G=生活の安定/構造 O=選択肢/自由度 K=技能/知識 X=暴露/リスク
# ============================================================
class PersonalDecisionDynamics:
    """個人の意思決定を現実 domain として扱う。dynamics は実 civstate_transition。"""
    def __init__(self, wp=None):
        self.cfg = RolloutConfig()
        self.wp = wp or {"rivalry_level": 0.10, "shock_freq": 0.06,
                         "shock_probability": 0.06, "tail_probability": 0.03,
                         "environmental_drag": 0.025, "governance_drag": 0.02,
                         "stagnation_drag": 0.03, "innovation_noise": 1.0}

    def clone(self, s): return s.copy()
    def transition(self, s, a, rng):
        return civstate_transition(s, a, self.wp, rng, self.cfg)  # domain-native proxy dynamics
    def is_ruin(self, s): return is_ruin_state(s)
    def is_terminal(self, s): return False
    def wealth(self, s):
        # 個人の前進量 = 蓄え+心身+安定+選択肢+技能 - 暴露
        return s.R + s.E + s.G + s.O + s.K - s.X

    def candidate_spectrum(self, s):
        """engine が生成する候補 action (攻撃〜防御)。停滞は含めない。
           [g(前進度), sf(安全余裕), lr(学習/探索), di(分散/ヘッジ)]"""
        return [np.array([0.95, 0.02, 0.02, 0.01]),  # 暴走 (governance が削る想定)
                np.array([0.55, 0.10, 0.20, 0.15]),  # 強い前進
                np.array([0.42, 0.18, 0.22, 0.18]),  # 前進
                np.array([0.30, 0.28, 0.24, 0.18]),  # バランス
                np.array([0.18, 0.42, 0.22, 0.18])]  # 慎重 (前進は維持)

    def detect_edge(self, s):
        return s.X > 55 or s.G < 35 or s.E < 38


class _Restricted:
    """governance-admissible な action だけを spectrum として返す薄い wrapper。
       これにより engine (二層) は admissible set の中だけで探索する (gov-exec 分離)。"""
    def __init__(self, base: PersonalDecisionDynamics, actions):
        self.base = base; self._actions = list(actions)
    def clone(self, s): return self.base.clone(s)
    def transition(self, s, a, rng): return self.base.transition(s, a, rng)
    def is_ruin(self, s): return self.base.is_ruin(s)
    def is_terminal(self, s): return self.base.is_terminal(s)
    def wealth(self, s): return self.base.wealth(s)
    def action_spectrum(self, s): return self._actions


# ============================================================
# DecisionCompass: real-side application layer
# ============================================================
class DecisionCompass:
    def __init__(self, mode: str = "vnext", sim_horizon: int = 40):
        # 現実側 engine = StrongEngine Ω Full, 内部に civ-sim MaxForwardEngine
        self.civsim = MaxForwardEngine(n_trials=6, sim_horizon=sim_horizon)
        self.strong = StrongEngineOmegaFull(self.civsim)
        self.dyn = PersonalDecisionDynamics()
        self.mode = mode   # governance veto モード: 'nrmo'|'vnext'|'none'

    def recommend(self, s: CivState, rng: np.random.Generator) -> dict:
        """「破滅しない最大前進」の提案を返す。"""
        # 1) engine が候補を生成 (governance は候補生成を知らない)
        candidates = self.dyn.candidate_spectrum(s)

        # 2) ★governance 境界★: 実 nrmo_core が admissible set を構築 (veto only)
        admissible, flags = construct_admissible_set(candidates, s, self.mode)
        n_vetoed = sum(flags)

        # 3) admissible が空 = governance HOLD: 止めるのではなく方向転換指示
        if not admissible:
            return dict(decision="EXIT_HOLD", action=None,
                        n_candidates=len(candidates), n_vetoed=n_vetoed,
                        rationale="現状は破滅の縁。前進候補が全て veto。"
                                  "暴露を下げる/構造を整える方向転換を先に。")

        # 4) ★engine は admissible set の中だけで探索★ (a_t = Engine(A_t))
        peaks = self.civsim.explore(_Restricted(self.dyn, admissible), s, rng)
        best = peaks["best"]; ap = peaks["attack_peak"]; dp = peaks["defense_peak"]

        # 5) 「破滅しない最大前進」= admissible 内で生存担保しつつ前進量最大
        return dict(
            decision="ALLOW", action=best["action"],
            n_candidates=len(candidates), n_vetoed=n_vetoed,
            n_admissible=len(admissible),
            forward=float(best["action"][0]), survival=best["survival"],
            wealth=best["wealth"],
            attack_peak_g=float(ap["action"][0]), defense_peak_g=float(dp["action"][0]),
            rationale=(f"admissible {len(admissible)}/{len(candidates)} 内で最大前進。"
                       f"より攻撃的な候補は governance が veto (破滅成分) か "
                       f"civ-sim で生存不可。より慎重側は前進量が劣り却下 (停滞=ruin)。"))

    def step(self, s: CivState, rng: np.random.Generator):
        """1 ステップ実行 (推奨 → 遷移 → observe)。HOLD なら最も安全な admissible へ。"""
        rec = self.recommend(s, rng)
        if rec["decision"] == "EXIT_HOLD":
            # HOLD: 暴露を下げる最も防御的な候補を governance に通るまで探す
            for a in reversed(self.dyn.candidate_spectrum(s)):
                adm, _ = construct_admissible_set([a], s, self.mode)
                if adm: action = adm[0]; break
            else:
                action = np.array([0.10, 0.55, 0.20, 0.18])  # 最終退避
        else:
            action = rec["action"]
        ns = self.dyn.transition(s, action, rng)
        self.strong.observe(action, ns, self.dyn)
        return ns, rec


# ============================================================
# 検証
# ============================================================
if __name__ == "__main__":
    print("=" * 64)
    print("Phase E: DecisionCompass 二層構造化 (実 nrmo_core + 実 dynamics + v7 二層)")
    print("=" * 64)

    dc = DecisionCompass(mode="vnext")
    rng = np.random.default_rng(0)

    # --- A. 単発推奨: 健全な状況 vs 縁の状況 ---
    print("\n[A] 単発推奨 (gov-exec 分離: governance=admissible, engine=A_t 内探索):")
    cases = {
        "健全 (低暴露・安定)": CivState(R=60, E=58, G=55, O=52, K=52, X=28),
        "やや過熱 (高暴露)":   CivState(R=58, E=50, G=48, O=50, K=50, X=64),
        "縁 (高暴露・低統治)": CivState(R=42, E=38, G=28, O=40, K=40, X=72),
    }
    for label, s in cases.items():
        rec = dc.recommend(s, np.random.default_rng(1))
        if rec["decision"] == "ALLOW":
            print(f"  {label}: ALLOW 前進g={rec['forward']:.2f} "
                  f"(admissible {rec['n_admissible']}/{rec['n_candidates']}, "
                  f"veto {rec['n_vetoed']}, surv={rec['survival']:.0%})")
        else:
            print(f"  {label}: {rec['decision']} (veto {rec['n_vetoed']}/{rec['n_candidates']}) "
                  f"— {rec['rationale']}")

    # --- B. gov-exec 分離の実証: engine は admissible を override できない ---
    print("\n[B] gov-exec 分離 (engine は veto された候補を選べない):")
    s = cases["健全 (低暴露・安定)"]
    cands = dc.dyn.candidate_spectrum(s)
    adm, flags = construct_admissible_set(cands, s, "vnext")
    print(f"  候補 g 値: {[f'{c[0]:.2f}' for c in cands]}")
    print(f"  veto flags: {flags}  → admissible g 値: {[f'{a[0]:.2f}' for a in adm]}")
    rec = dc.recommend(s, np.random.default_rng(1))
    print(f"  engine 選択 g={rec['forward']:.2f} は admissible 内: "
          f"{any(abs(rec['forward']-a[0])<1e-9 for a in adm)}")

    # --- C. 軌道実行: ruin 0% で最大前進を続けられるか ---
    print("\n[C] 軌道実行 (個人の意思決定を 200 ステップ, 12 seeds):")
    rr, finals, holds = [], [], []
    for seed in range(12):
        rng = np.random.default_rng(100 + seed)
        s = CivState(R=55, E=52, G=50, O=50, K=50, X=35)
        ruined = False; nhold = 0
        for _ in range(200):
            s, rec = dc.step(s, rng)
            if rec["decision"] == "EXIT_HOLD": nhold += 1
            if dc.dyn.is_ruin(s): ruined = True; break
        rr.append(ruined); finals.append(dc.dyn.wealth(s) if not ruined else 0)
        holds.append(nhold)
    surv = [f for f in finals if f > 0]
    print(f"  ruin={np.mean(rr):.0%}  最終前進量(生存時)={np.mean(surv) if surv else 0:.0f}"
          f"  HOLD発生平均={np.mean(holds):.1f}/200")
    print("  → governance が破滅成分を削り、engine が admissible 内で最大前進を継続。")
