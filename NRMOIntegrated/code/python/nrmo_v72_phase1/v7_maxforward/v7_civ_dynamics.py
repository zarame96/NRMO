"""
import os
NRMO v7 — 文明 (civilization) を現実 domain として扱う DomainDynamics
これまで「civ-sim」とされていたものを、現実側の一 domain に再配置。
"""
import sys, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "..", "..", "world_sim_v50", "src"))
from vnext_plus import CivState, civstate_transition, is_ruin_state, RolloutConfig

class CivilizationDynamics:
    """文明を現実 domain として扱う。
    現実 StrongEngine Ω Full がこの真の dynamics で最大前進する。
    civ-sim 側 MaxForwardEngine は同じ dynamics で死を恐れず極端を探索する。
    """
    def __init__(self, wp=None):
        self.cfg = RolloutConfig()
        self.wp = wp or {"rivalry_level":0.15,"shock_freq":0.08,"shock_probability":0.08,
                         "tail_probability":0.04,"environmental_drag":0.03,
                         "governance_drag":0.03,"stagnation_drag":0.02,"innovation_noise":1.0}
    def clone(self, s): return s.copy()
    def transition(self, s, action, rng):
        return civstate_transition(s, action, self.wp, rng, self.cfg)  # 文明の真の dynamics
    def is_ruin(self, s): return is_ruin_state(s)
    def is_terminal(self, s): return False
    def wealth(self, s):
        # 文明の繁栄 = 資源+環境+統治+選択肢+知識 - 暴露
        return s.R + s.E + s.G + s.O + s.K - s.X
    def action_spectrum(self, s):
        # 攻撃(成長最大) → 防御(安全最大). 停滞は含めない (全て前進).
        return [np.array([0.55,0.10,0.20,0.15]),   # 最大成長 (攻撃ピーク候補)
                np.array([0.45,0.18,0.22,0.15]),   # 強成長
                np.array([0.30,0.28,0.24,0.18]),   # バランス
                np.array([0.18,0.42,0.22,0.18]),   # 防御
                np.array([0.10,0.52,0.20,0.18])]   # 最大防御 (防御ピーク候補)
    def default_action(self, s):
        return np.array([0.50,0.15,0.20,0.15])     # 文明の最大前進
    def detect_favorable(self, s):
        return s.E>=50 and s.G>=45 and s.O>=45 and s.K>=45 and s.X<=42
    def detect_edge(self, s):
        return s.X > 55 or s.G < 40 or s.E < 40

# ===== 二層構造で文明 domain を検証 =====
if __name__ == "__main__":
    from v7_two_layer import MaxForwardEngine, StrongEngineOmegaFull

    civ = MaxForwardEngine(n_trials=5, sim_horizon=12)
    strong = StrongEngineOmegaFull(civ)
    dyn = CivilizationDynamics()

    print("文明 domain を二層構造で検証 (現実 StrongEngine + civ-sim MaxForward)")
    rr, finals, peaks_log = [], [], []
    for seed in range(8):
        rng = np.random.default_rng(seed); s = CivState(); ruined=False; step=0
        for step in range(300):
            action = strong.decide(dyn, s, rng)
            s = dyn.transition(s, action, rng)
            strong.observe(action, s, dyn)
            if dyn.is_ruin(s): ruined=True; break
        rr.append(ruined); finals.append(dyn.wealth(s) if not ruined else 0)
    print(f"  ruin={np.mean(rr):.0%}  surv_steps_mean(生存時 final wealth)={np.mean([f for f in finals if f>0]) if any(f>0 for f in finals) else 0:.0f}")

    # civ-sim が初期状態で算出する攻撃/防御ピーク
    s0 = CivState()
    pk = civ.explore(dyn, s0, np.random.default_rng(0))
    print(f"\n  civ-sim 探索 (初期文明状態):")
    for r in pk["results"]:
        a = r["action"]; lbl = f"g={a[0]:.2f}"
        print(f"    {lbl}: survival={r['survival']:.0%} wealth={r['wealth']:.0f}")
    bp = pk["best"]["action"]
    print(f"  → 最善: g={bp[0]:.2f} sf={bp[1]:.2f} (wealth={pk['best']['wealth']:.0f})")
    print(f"  → 攻撃ピーク: g={pk['attack_peak']['action'][0]:.2f} (survival={pk['attack_peak']['survival']:.0%})")
