"""internal_audit.py — 内部監査 (確定版): 完全性 + 最大前進 × 破綻回避"""
from __future__ import annotations
import os, sys
import numpy as np
_CORE = os.environ.get("NRMO_V6_CORE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
sys.path.insert(0, _CORE)
from world_models import WorldState, Action
from chaotic_world import ChaoticWorld, ChaosConfig
from drifting_world import DriftingWorld
from noisy_world import NoisyObservationWorld
from loom_v3_1_shadow import LoomV31Shadow
from loom_core import LoomCore
from loom_engine import LoomEngine

def make_world(kind, seed):
    cfg = ChaosConfig()
    return {"chaotic": ChaoticWorld, "drifting": DriftingWorld,
            "noisy": NoisyObservationWorld}[kind](cfg, seed=seed)
def step_world(world, a):
    out = world.step(a)
    if len(out) == 4: _, r, done, info = out
    else: r, done, info = out
    return r, done

class Canonical:
    name = "Canonical(LoomV31+Shadow)"
    def __init__(self): self.e = LoomV31Shadow()
    def act(self, s): return self.e.decide(s).action
    def learn(self, a, r, sb, sa):
        try: self.e.update_reward(a, r, sb, sa)
        except TypeError:
            try: self.e.update_reward(a, r)
            except Exception: pass
class NaiveMaxForward:
    name = "NaiveMaxForward(invest C)"
    def __init__(self): pass
    def act(self, s): return Action("invest", "C")
    def learn(self, *a): pass
class PureDefensive:
    name = "PureDefensive(recover A)"
    def __init__(self): pass
    def act(self, s): return Action("recover", "A")
    def learn(self, *a): pass

def run_survival(engine_cls, kind, seed, steps=150):
    world = make_world(kind, seed); eng = engine_cls()
    for t in range(steps):
        sb = world.observe(); a = eng.act(sb)
        r, done = step_world(world, a); sa = world.observe()
        eng.learn(a, r, sb, sa)
        if done or world.state.is_ruined:
            return world.state.t, float(world.state.cumulative_score)
    return world.state.t, float(world.state.cumulative_score)

def part2(seeds=20, steps=150):
    kinds = ("chaotic", "drifting", "noisy"); agg = {}
    for E in (Canonical, NaiveMaxForward, PureDefensive):
        for kind in kinds:
            surv, sc = [], []
            for sd in range(seeds):
                st, score = run_survival(E, kind, 2000 + sd, steps)
                surv.append(st); sc.append(score)
            agg[(E.name, kind)] = (float(np.mean(surv)), float(np.mean(sc)))
    return kinds, agg

def part3a():
    checks = []
    safe = WorldState(R=85, E=70, G=70, O=75, K=60, X=25)
    d = LoomCore().decide_weaving(safe, {"O_confidence":0.95}, cumulative_exposure=0.0)
    checks.append(("safe_strong_opp_unlocks_C", d.action_size_cap == "C"))
    d2 = LoomCore().decide_weaving(WorldState(R=85,E=70,G=70,O=75,K=60,X=60), {"O_confidence":0.95}, cumulative_exposure=0.0)
    checks.append(("high_X_blocks_C", d2.action_size_cap != "C"))
    d3 = LoomCore().decide_weaving(WorldState(R=45,E=70,G=70,O=75,K=60,X=25), {"O_confidence":0.95}, cumulative_exposure=0.0)
    checks.append(("low_R_blocks_C", d3.action_size_cap != "C"))
    d4 = LoomCore().decide_weaving(safe, {"O_confidence":0.95}, cumulative_exposure=0.85)
    checks.append(("cumulative_clamp_overrides_to_A", d4.action_size_cap == "A"))
    return checks

def part3b(steps=40):
    eng = LoomEngine(); favorable = WorldState(R=85, E=75, G=72, O=78, K=65, X=22)
    intents, strengths = {}, {}
    for _ in range(steps):
        a = eng.decide(favorable).action
        intents[a.intent] = intents.get(a.intent, 0) + 1
        strengths[a.strength] = strengths.get(a.strength, 0) + 1
    fwd = intents.get("invest", 0) + intents.get("explore", 0)
    return intents, strengths, fwd / max(1, steps)

if __name__ == "__main__":
    print("="*72); print("内部監査 (確定版): 完全性 + 最大前進 × 破綻回避"); print("="*72)
    print("\n[Part 2] 破綻回避 — hostile world 生存ステップ数 (20 seeds, max 150)")
    kinds, agg = part2()
    print(f"  {'engine':<28}" + "".join(f"{k:>12}" for k in kinds))
    for name in ("Canonical(LoomV31+Shadow)","NaiveMaxForward(invest C)","PureDefensive(recover A)"):
        print(f"  {name:<28}" + "".join(f"{agg[(name,k)][0]:>8.0f}st  " for k in kinds))
    print("  (score 平均)")
    for name in ("Canonical(LoomV31+Shadow)","NaiveMaxForward(invest C)","PureDefensive(recover A)"):
        print(f"  {name:<28}" + "".join(f"{agg[(name,k)][1]:>9.1f}   " for k in kinds))
    can_surv=np.mean([agg[("Canonical(LoomV31+Shadow)",k)][0] for k in kinds])
    naive_surv=np.mean([agg[("NaiveMaxForward(invest C)",k)][0] for k in kinds])
    can_sc=np.mean([agg[("Canonical(LoomV31+Shadow)",k)][1] for k in kinds])
    def_sc=np.mean([agg[("PureDefensive(recover A)",k)][1] for k in kinds])
    print("\n[Part 3a] 最大前進 — C 解禁 gating (決定論)")
    c3a=part3a()
    for n,ok in c3a: print(f"  {'PASS' if ok else 'FAIL'}: {n}")
    print("\n[Part 3b] 最大前進 — 好機状態で前進を実際に出すか (LoomEngine)")
    intents,strengths,fwd_share=part3b()
    print(f"  intents={intents} strengths={strengths} 前進比率={fwd_share*100:.0f}%")
    print("\n[総合判定]")
    j1=can_surv>naive_surv+2; j2=can_sc>=def_sc-1.0; j3=all(ok for _,ok in c3a); j4=fwd_share>0.0
    print(f"  (1) 破綻回避: Canonical 生存 {can_surv:.0f}st > Naive {naive_surv:.0f}st -> {'PASS' if j1 else 'FAIL'}")
    print(f"  (2) 非自滅 : Canonical score {can_sc:.1f} >= Defensive {def_sc:.1f}-1 -> {'PASS' if j2 else 'FAIL'}")
    print(f"  (3) 前進gating: 安全のみC/危険抑制/累積clamp -> {'PASS' if j3 else 'FAIL'}")
    print(f"  (4) 前進発火: 好機で前進 ({fwd_share*100:.0f}%) -> {'PASS' if j4 else 'FAIL'}")
    print("="*72); print("AUDIT PASS" if (j1 and j2 and j3 and j4) else "AUDIT: 要確認")
