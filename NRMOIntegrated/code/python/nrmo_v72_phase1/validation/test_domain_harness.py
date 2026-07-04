"""
test_domain_harness.py — 自己完結 domain harness の検証 (外部 bundle 非依存)。
store / investment(proxy) / romance(proxy) が外部依存なしで動くことを確認する。
"""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "v7_maxforward"))
sys.path.insert(0, os.path.join(_HERE, "..", "core"))
sys.path.insert(0, os.path.join(_HERE, "..", "..", ".."))   # code/python

import numpy as np, random


def test_no_external_bundle_paths():
    for fn in ("v7_adapters.py", "v7_validate.py"):
        p = os.path.join(_HERE, "..", "v7_maxforward", fn)
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        bad1 = "/tmp/" + "vbundle"; bad2 = "/tmp/" + "v6_repaired"
        assert bad1 not in txt and bad2 not in txt, f"external path in {fn}"


def test_investment_scenarios_deterministic_and_differentiated():
    from investment_stress_models import MarketScenario, run_static_policy
    # 決定論性
    a = [MarketScenario("fat_tail_crash", 7, 50).step()[0] for _ in range(50)]
    b = [MarketScenario("fat_tail_crash", 7, 50).step()[0] for _ in range(50)]
    assert a == b
    # シナリオ差: fat_tail の drawdown > secular_bull
    mdd_ft = np.mean([run_static_policy("fat_tail_crash", "buyhold_60", s).max_drawdown for s in range(10)])
    mdd_bull = np.mean([run_static_policy("secular_bull", "buyhold_60", s).max_drawdown for s in range(10)])
    assert mdd_ft > mdd_bull


def test_romance_proxy_guard_avoids_active_ruin():
    import romance_simulation_harness as R
    # 倫理 guard 整合: 拒絶/低相互性/高圧では supportive/observe/exit のみ → active_ruin に陥らない
    for reg in R.REGIMES:
        rr = random.Random(3); s = R.init_state(reg); oc = None
        for _ in range(40):
            # guard 準拠の安全行動のみ
            action = "graceful_exit" if s.rejections >= 1 or s.pressure >= 60 else "supportive_act"
            s = R.step(s, action, reg, rr)
            oc = R.outcome(s, reg, 40)
            if oc: break
        assert oc != "active_ruin"


def test_store_runs_without_external_deps():
    from v7_engine import MaxForwardEngine
    from v7_adapters import StoreDynamics
    from nrmo_universal_adapter import StoreState
    eng = MaxForwardEngine(); dyn = StoreDynamics()
    rng = np.random.default_rng(0); s = StoreState()
    for _ in range(60):
        a = eng.decide(dyn, s, rng); s = dyn.transition(s, a, rng)
        if dyn.is_ruin(s): break
    assert hasattr(s, "revenue_accum")


def test_engine_drives_all_three_domains():
    from v7_engine import MaxForwardEngine
    from v7_adapters import InvestmentDynamics, RomanceDynamics
    import romance_simulation_harness as R
    eng = MaxForwardEngine()
    # investment 1 episode
    dyn = InvestmentDynamics()
    rng = np.random.default_rng(1)
    roll = {"value": 100.0, "peak": 100.0, "equity": 0.5, "mu": 0.0003, "sd": 0.012}
    eq = eng.decide(dyn, roll, rng)
    assert 0.0 <= eq <= 1.0
    # romance 1 episode
    dynr = RomanceDynamics(R.REGIMES[0]); s = R.init_state(R.REGIMES[0])
    a = eng.decide(dynr, s, np.random.default_rng(2))
    assert a in R.ACTIONS


if __name__ == "__main__":
    test_no_external_bundle_paths()
    test_investment_scenarios_deterministic_and_differentiated()
    test_romance_proxy_guard_avoids_active_ruin()
    test_store_runs_without_external_deps()
    test_engine_drives_all_three_domains()
    print("domain_harness OK (store/investment/romance self-contained)")
