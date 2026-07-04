"""
NRMO v7 Domain Dynamics — store / investment / romance
======================================================
各 domain の真の dynamics を DomainDynamics protocol で実装。
MaxForwardEngine はこれを rollout に使い、domain ごとの最大前進を創発させる。

第4原則: rollout は domain の真の dynamics で。
  - store/romance: dynamics 既知 → transition = real
  - investment:    将来が確率的 → rollout transition = 最近分布の継続 (最良推定),
                   実行は real market (harness 側)
"""
import os, sys
import numpy as np

# パッケージ内自己完結パス (外部 bundle 依存を撤廃)
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                   # investment_stress_models, romance_simulation_harness
sys.path.insert(0, os.path.join(_HERE, "..", "core"))       # world_models
sys.path.insert(0, os.path.join(_HERE, "..", ".."))   # nrmo_universal_adapter (code/python)


# ============================================================
# STORE
# ============================================================
class StoreDynamics:
    def __init__(self):
        from nrmo_universal_adapter import StoreOperationAdapter, StoreState
        from world_models import Action
        self.A = StoreOperationAdapter()
        self.StoreState = StoreState
        self.Action = Action

    def clone(self, s):
        return self.StoreState(**{k: getattr(s, k) for k in s.__dataclass_fields__})

    def transition(self, s, action, rng):
        return self.A.apply_action(action, s, rng)   # ★真の store dynamics

    def is_ruin(self, s):
        return self.A.is_ruin(s)

    def is_terminal(self, s):
        return False

    def wealth(self, s):
        return s.revenue_accum + s.cash

    def candidate_actions(self, s, wolf, edge):
        # 第1原則: 最大前進中心. 第3原則: 停滞(何もしない)は入れない.
        c = [self.Action("invest", "C"), self.Action("invest", "B"), self.Action("explore", "C")]
        if edge:  # 第2原則: 縁では前進方向を変える (止まらない)
            c += [self.Action("explore", "B"), self.Action("recover", "A")]
        return c

    def default_action(self, s):
        return self.Action("invest", "C")   # store の最大前進

    def action_spectrum(self, s):
        # 攻撃 → 防御の連続スペクトル (civ-sim が全部試す). 停滞(何もしない)は含めない.
        return [self.Action("invest","C"), self.Action("invest","B"), self.Action("invest","A"),
                self.Action("explore","C"), self.Action("explore","B"),
                self.Action("defend","A"), self.Action("recover","A")]

    def detect_favorable(self, s):
        return s.cash > 50 and s.inventory > 10

    def detect_edge(self, s):
        return s.cash < 30


# ============================================================
# INVESTMENT (rollout = 最近分布の継続を仮定)
# ============================================================
class InvestmentDynamics:
    def __init__(self, cash_return=0.0):
        self.cash_return = cash_return

    def clone(self, s):
        return dict(s)   # {value, peak, equity, mu, sd}

    def transition(self, s, eq, rng):
        eqret = rng.normal(s["mu"], s["sd"])           # ★最近分布から将来をsample
        pret = eq * eqret + (1 - eq) * self.cash_return
        v = s["value"] * (1 + pret)
        return {"value": v, "peak": max(s["peak"], v), "equity": eq,
                "mu": s["mu"], "sd": s["sd"]}

    def is_ruin(self, s):
        return (s["peak"] - s["value"]) / s["peak"] >= 0.40 if s["peak"] > 0 else False

    def is_terminal(self, s):
        return False

    def wealth(self, s):
        return s["value"]

    def candidate_actions(self, s, wolf, edge):
        # 最大前進(高equity)中心. cash100%(0.0=停滞)も入れるが rollout が評価して排除.
        return [0.9, 0.7, 0.5, 0.3, 0.0]

    def default_action(self, s):
        return s.get("equity", 0.5)

    def action_spectrum(self, s):
        return [0.9, 0.7, 0.5, 0.3, 0.1]   # 攻撃(高eq) → 防御(低eq)

    def detect_favorable(self, s):
        return s["mu"] > 0.0005       # 最近 trend up = 好機

    def detect_edge(self, s):
        return (s["peak"] - s["value"]) / s["peak"] >= 0.25 if s["peak"] > 0 else False


# ============================================================
# ROMANCE (+ 倫理 guard)
# ============================================================
class RomanceDynamics:
    OV = {"success": 100, "graceful_exit": 15, "clear_but_unresolved": 5,
          "stagnation": -40, "passive_ruin": -60, "active_ruin": -120, None: 0}

    def __init__(self, reg, horizon=40):
        import romance_simulation_harness as R
        import random
        self.R = R
        self.random = random
        self.reg = reg
        self.horizon = horizon

    def clone(self, s):
        n = self.R.State.__new__(self.R.State)
        for k, v in s.__dict__.items():
            setattr(n, k, v)
        return n

    def transition(self, s, action, rng):
        rr = self.random.Random(int(rng.integers(0, 10**9)))
        return self.R.step(s, action, self.reg, rr)   # ★真の romance dynamics

    def _outcome(self, s):
        return self.R.outcome(s, self.reg, self.horizon)

    def is_ruin(self, s):
        return self._outcome(s) in ("active_ruin", "passive_ruin")

    def is_terminal(self, s):
        oc = self._outcome(s)
        return oc is not None   # success / graceful_exit / unresolved / stagnation 確定

    def wealth(self, s):
        oc = self._outcome(s)
        if oc:
            return self.OV.get(oc, 0)
        # 未確定: 明確化・信頼・相互性の前進量で評価 (停滞は伸びない)
        return (s.clarity + s.reciprocity + s.trust) * 0.1

    def candidate_actions(self, s, wolf, edge):
        # ★倫理 guard: 相手の弱い反応・拒絶・圧力過多のときは pursuit を出さない
        if s.rejections >= 1 or s.reciprocity < 32 or s.pressure >= 60:
            return ["supportive_act", "observe_wait", "graceful_exit"]
        # 平時: 能動的前進候補 (明確化に向かう最大前進)
        return ["light_contact", "supportive_act", "invite_lowstakes", "direct_confession"]

    def default_action(self, s):
        if s.rejections >= 1 or s.reciprocity < 32:
            return "observe_wait" if s.rejections < 2 else "graceful_exit"
        return "invite_lowstakes" if s.clarity < 45 else "direct_confession"

    def action_spectrum(self, s):
        # 倫理 guard: 弱い反応・拒絶・圧力過多では攻撃側(pursuit)を除外
        if s.rejections >= 1 or s.reciprocity < 32 or s.pressure >= 60:
            return ["supportive_act", "observe_wait", "graceful_exit"]
        return ["direct_confession", "invite_lowstakes", "light_contact", "supportive_act"]

    def detect_favorable(self, s):
        return s.reciprocity >= 50 and s.rejections == 0

    def detect_edge(self, s):
        return s.pressure >= 50 or s.rejections >= 1


if __name__ == "__main__":
    sd = StoreDynamics()
    print("StoreDynamics OK, default =", sd.default_action(None).intent)
    inv = InvestmentDynamics()
    print("InvestmentDynamics OK, candidates =", inv.candidate_actions(None, False, False))
