"""
NRMO v7 検証 harness — 本物の MaxForwardEngine + DomainDynamics で 3 domain
proof_1/2/3 (簡易版) を、正式実装した engine で再現する。
"""
import os, sys, numpy as np
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                   # v7_engine, v7_adapters, *_harness
sys.path.insert(0, os.path.join(_HERE, "..", "core"))       # world_models
sys.path.insert(0, os.path.join(_HERE, "..", ".."))   # nrmo_universal_adapter (code/python)
from v7_engine import MaxForwardEngine
from v7_adapters import StoreDynamics, InvestmentDynamics, RomanceDynamics


def validate_store():
    from nrmo_universal_adapter import StoreState
    eng = MaxForwardEngine(); dyn = StoreDynamics()
    rr, sv, scs = [], [], []
    for seed in range(10):
        rng = np.random.default_rng(seed); ds = StoreState(); ruined=False; step=0
        for step in range(300):
            action = eng.decide(dyn, ds, rng)        # 本物の engine
            ds = dyn.transition(ds, action, rng)     # 実行 (store: real=transition)
            if dyn.is_ruin(ds): ruined=True; break
        rr.append(ruined); sv.append(step+1); scs.append(ds.revenue_accum)
    print(f"  store    : ruin={np.mean(rr):.0%} surv={np.mean(sv):.0f} revenue={np.mean(scs):.0f}")


def validate_investment():
    from investment_stress_models import MarketScenario, run_static_policy
    eng = MaxForwardEngine()
    SCEN = ["secular_bull","slow_bear","fat_tail_crash","inflation_cash_drag"]
    print("  investment (avg_eq が相場適応するか):")
    for sc in SCEN:
        cr = -0.00018 if sc=="inflation_cash_drag" else 0.0
        dyn = InvestmentDynamics(cash_return=cr)
        vals, eqs, ruins = [], [], []
        for seed in range(15):
            market = MarketScenario(sc, seed, 300)
            value, peak, equity, retbuf = 100.0, 100.0, 0.5, []
            rng = np.random.default_rng(seed+5000); ruined=False; eqlist=[]
            for step in range(300):
                mu = float(np.mean(retbuf)) if len(retbuf)>=3 else 0.0003
                sd = float(np.std(retbuf)+1e-6) if len(retbuf)>=3 else 0.012
                roll = {"value":value,"peak":peak,"equity":equity,"mu":mu,"sd":sd}
                eq = eng.decide(dyn, roll, rng)              # 本物の engine
                value *= (1-abs(eq-equity)*0.001); equity=eq; eqlist.append(eq)
                eqret, vol = market.step()                   # 実行 (real market)
                pret = eq*eqret + (1-eq)*cr
                value *= (1+pret); peak=max(peak,value)
                retbuf.append(pret)
                if len(retbuf)>20: retbuf.pop(0)
                if (peak-value)/peak >= 0.40: ruined=True; break
            vals.append(value); eqs.append(np.mean(eqlist)); ruins.append(ruined)
        bh = np.mean([run_static_policy(sc,"buyhold_60",s).final_value for s in range(15)])
        print(f"    {sc:>20}: avg_eq={np.mean(eqs):.2f} val={np.mean(vals):.1f} ruin={np.mean(ruins):.0%} (buyhold60={bh:.1f})")


def validate_romance():
    import romance_simulation_harness as R
    import random
    eng = MaxForwardEngine(base_depth=6, repeats=4)
    CATS=["success","graceful_exit","clear_but_unresolved","stagnation","passive_ruin","active_ruin"]
    agg={c:0 for c in CATS}; total=0
    for reg in R.REGIMES:
        dyn = RomanceDynamics(reg)
        for seed in range(30):
            rng=np.random.default_rng(seed); rr=random.Random(seed)
            s=R.init_state(reg); oc=None
            for st in range(40):
                action = eng.decide(dyn, s, rng)     # 本物の engine
                s = R.step(s, action, reg, rr)       # 実行 (real)
                oc = R.outcome(s, reg, 40)
                if oc: break
            oc = oc or "stagnation"
            agg[oc]=agg.get(oc,0)+1; total+=1
    print(f"  romance  : success={agg['success']/total:.0%} clean={agg['graceful_exit']/total:.0%} "
          f"passive+stag={(agg['passive_ruin']+agg['stagnation'])/total:.0%} active={agg['active_ruin']/total:.0%}")


if __name__ == "__main__":
    print("本物の MaxForwardEngine + DomainDynamics による 3 domain 検証")
    print("="*60)
    validate_store()
    validate_investment()
    validate_romance()
