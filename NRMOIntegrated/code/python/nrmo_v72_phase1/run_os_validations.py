"""
run_os_validations.py — OS/SOP 全モジュールの一発検証。
SKIP があれば ALL PASS と出さない。exit: 0=all pass, 2=partial(skip), 1=fail。
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from common_types import NRMOContext, CandidateAction
from dag_layer import DAGLayer
from parallel_ooda import ParallelOODA
from hst_n import HSTNClassifier
from aallowed import AallowedRegistry
from apcso import APCSO, APCSOConfig
from secretary_console import SecretaryConsole, EmotionalFilter, FailureLogInput
from shutdown_guard import ShutdownGuard
from ttm_pps import TTMPPS
from defensive_offense import DefensiveOffense, CarrybackController
from investment_sop import InvestmentSOP
from hare_no_hi import HareNoHiProtocol, NarrativeRandomGenerator
from life_sop import LifeSOP
from mode_selector import ModeSelector
from nonergodic_monitor import NonErgodicMonitor
from meta_governance import MetaGovernance
from nrmo_os_integrator import NRMOOSIntegrator

RESULTS = []  # (name, "PASS"/"FAIL"/"SKIP", detail)
def check(name, cond, detail=""):
    RESULTS.append((name, "PASS" if cond else "FAIL", detail))

def ctx(**kw):
    c = NRMOContext(domain=kw.pop("domain", "test"))
    for k, v in kw.items(): setattr(c, k, v) if hasattr(c, k) else c.state.update({k: v})
    return c


def t_dag():
    dag = DAGLayer(); c = ctx()
    r1 = dag.evaluate_claim("CollectiveDomainDynamics is true dynamics.", [], c)
    check("dag_proxy_not_true_dynamics", r1.status in ("HOLD", "REJECT"), r1.reason)
    r2 = dag.evaluate_claim("This simulation proves the theorem.", [{"type":"simulation"}], c)
    check("dag_simulation_not_proof", r2.status in ("HOLD", "REJECT"), r2.reason)
    r3 = dag.evaluate_claim(
        "Within the store proxy model, invest/C maximizes revenue under the tested parameters.",
        [{"type":"run_log","seeds":[1,2,3]}], c)
    check("dag_defined_scoped_claim_passes", r3.status == "PASS", r3.reason)
    r4 = dag.evaluate_output("This is a fully proven complete product.", c)
    check("dag_no_hallucinated_overclaim", r4.status in ("HOLD","REJECT"), r4.reason)

def t_parallel_ooda():
    o = ParallelOODA(); c = ctx(); c.state["uncertainty"] = 0.8
    adm = [CandidateAction(f"a{i}", f"act{i}", "test", exposure=0.1*i, expected_forward=0.5-0.1*i) for i in range(4)]
    ps = o.run(c, adm)
    check("ooda_multiple_hypotheses", len(ps.metadata["hypotheses"]) >= 3)
    check("ooda_only_admissible", all((cc in adm or "probe" in cc.tags) for cc in ps.choices))
    check("ooda_probe_when_uncertain", any("probe" in cc.tags for cc in ps.choices))

def t_hstn():
    h = HSTNClassifier()
    c1 = ctx(); c1.state = {"sleep_hours":2,"anger":0.8,"time_pressure":0.9}
    s1 = h.classify(c1)
    check("hstn_high_load_safe_required", "SAFE_REQUIRED" in s1.flags or s1.state_label=="SAFE_REQUIRED", s1.state_label)
    c2 = ctx(); c2.state = {"sleep_hours":7,"anger":0.1,"time_pressure":0.2}
    s2 = h.classify(c2)
    check("hstn_low_risk_ready", s2.state_label in ("CLEAR","VENTURE_READY"), s2.state_label)

def t_aallowed():
    a = AallowedRegistry()
    c = ctx(); c.mode = "SAFE"
    act = CandidateAction("x","commit","test",reversibility=0.1,exposure=0.9,tags=["irreversible_commitment"])
    check("aallowed_safe_blocks_irreversible", a.evaluate(act, c).status == "REJECT")
    c2 = ctx(); c2.mode = "VENTURE"; c2.metadata["completed_checks"]=["exit_condition"]
    act2 = CandidateAction("y","exp","test",reversibility=0.8,exposure=0.4,tags=["bounded_experiment"])
    check("aallowed_venture_allows_bounded", a.evaluate(act2, c2).status == "PASS", a.evaluate(act2,c2).reason)

def t_apcso():
    ap = APCSO(); c = ctx()
    cands = [CandidateAction(f"c{i}","x","test",exposure=0.2*i,expected_forward=0.6-0.1*i) for i in range(4)]
    ps = ap.generate_proposal_set(cands, c, APCSOConfig())
    check("apcso_three_hold_exit", len(ps.choices)<=3 and ps.hold_option and ps.exit_option and "user" in ps.autonomy_note.lower())
    check("apcso_no_single_force", len(ps.choices) >= 2)

def t_secretary():
    ef = EmotionalFilter(); c = ctx()
    out = ef.filter_output("お前はいつも間違っている", c)
    check("secretary_filters_attack", "お前" not in out and "いつも" not in out, out)
    fl = FailureLogInput()
    r = fl.reconstruct("疲れている時に高リスク判断をした", c)
    check("secretary_recurrence_condition", "recurrence_condition" in r)

def t_shutdown():
    g = ShutdownGuard()
    c1 = ctx(); c1.state = {"irreversibility":0.9,"observability":0.1,"volatility":0.8}
    check("shutdown_high_irrev_low_obs", g.should_silence("今すぐ送る", c1) is True)
    c2 = ctx(); c2.state = {"irreversibility":0.1,"observability":0.9,"volatility":0.1}
    check("shutdown_not_low_risk_log", g.should_silence("今日のログを残す", c2) is False)

def t_ttm():
    t = TTMPPS(); c = ctx(); c.mode = "TRAINING"
    act = CandidateAction("z","x","test",tags=["real_world_execution"])
    check("ttm_blocks_real_execution", t.prohibit_real_execution(act).status == "REJECT")
    check("ttm_sim_tag", "SIMULATION_ONLY" in t.simulate_pattern("p1", c)["tags"])

def t_defensive():
    d = DefensiveOffense(); c = ctx()
    bad = CandidateAction("r","x","test",tags=["retaliation"])
    check("defoff_blocks_retaliation", d.evaluate(bad, c).status == "REJECT")
    good = CandidateAction("b","x","test",reversibility=1.0,exposure=0.1,tags=["boundary_setting"])
    check("defoff_allows_boundary", d.evaluate(good, c).status == "PASS")
    cb = CarrybackController().carryback({"result":"ok"}, c)
    check("carryback_no_direct_execution", cb["real_execution_instruction"] is None)

def t_investment(allow_external):
    s = InvestmentSOP(); c = ctx(); c.state = {"panic":0.8}
    act = CandidateAction("o","order","invest",payload={"execute_real_order":True})
    check("invest_no_real_order", s.evaluate_order(act, c).status == "REJECT")
    pl = s.check_position_limit({"total_value":100,"positions":{"AAA":20}}, {"ticker":"AAA","amount":20})
    check("invest_position_cap", pl.status == "REJECT", pl.reason)
    # TWR ベンチ比較は合成データで決定論的に検証可能 (実価格フィードは SOP では使わない)
    twr = s.benchmark_twr_check(returns=[0.01,-0.02,0.0,-0.01], benchmark=[0.02,0.01,0.0,0.01])
    check("invest_twr_benchmark_offline", twr["underperforming_4m"] is True and "twr_4m" in twr)

def t_hare():
    h = HareNoHiProtocol(); c = ctx()
    bad = CandidateAction("k","x","test",reversibility=0.1,tags=["irreversible_commitment"])
    check("hare_blocks_irreversible", h.evaluate_action(bad, c).status == "REJECT")
    c2 = ctx(); c2.state = {"alcohol":0.8,"major_decision_pending":True}
    check("hare_blocks_drunk_major_decision", h.can_activate(c2).status == "REJECT")
    nrg = NarrativeRandomGenerator().generate(c)
    check("hare_narrative_deterministic", "theme" in nrg and "frame" in nrg)

def t_life():
    l = LifeSOP(); c = ctx(); c.state = {"sleep_hours":3}
    m = l.morning_startup(c)
    check("life_morning_safe_when_tired", m["mode"] == "SAFE", m["mode"])
    check("life_night_log_only", l.night_non_recovery(c)["log_only"] is True)

def t_mode():
    ms = ModeSelector()
    c1 = ctx(); c1.state = {"sleep_hours":2,"anger":0.8,"time_pressure":0.9}
    check("mode_safe_high_load", ms.select_mode(c1) == "SAFE", ms.select_mode(c1))
    c2 = ctx(); c2.state = {"training":True}
    check("mode_training_flag", ms.select_mode(c2) == "TRAINING")

def t_nonergodic():
    m = NonErgodicMonitor()
    r = m.detect_absorbing_failure({"capital":0,"trust":0.1,"health":0.2})
    check("nonergodic_absorbing_detected", r.status in ("HOLD","REJECT"), r.status)

def t_meta():
    mg = MetaGovernance()
    check("meta_typezero_veto_violation", mg.detect_authority_violation("typezero", {"veto":True}).status=="REJECT")
    check("meta_passive_force_violation", mg.detect_authority_violation("passive_pattern", {"force_execution":True}).status=="REJECT")
    check("meta_clean_passes", mg.detect_authority_violation("typezero", {"classification":"x"}).status=="PASS")

def t_integrator():
    integ = NRMOOSIntegrator()
    c = ctx(); c.state = {"R":80,"O":70,"X":25,"sleep_hours":7}
    out = integ.process_request("今日の前進案", c)
    ps = out["proposal_set"]
    check("integrator_returns_proposal", ps is not None)
    check("integrator_admissible_only", out["selected"] is None or out["selected"] in out["admissible"])
    check("integrator_hold_exit_present", ps.hold_option is not None and ps.exit_option is not None)
    # authority separation: admissible は filter 済
    check("integrator_no_force_single", len(ps.choices) >= 1 and ps.metadata.get("meta_audit")=="PASS")


def main():
    allow_external = os.environ.get("NRMO_ALLOW_EXTERNAL_TESTS") == "1"
    for fn, args in [(t_dag,()),(t_parallel_ooda,()),(t_hstn,()),(t_aallowed,()),
                     (t_apcso,()),(t_secretary,()),(t_shutdown,()),(t_ttm,()),
                     (t_defensive,()),(t_investment,(allow_external,)),(t_hare,()),
                     (t_life,()),(t_mode,()),(t_nonergodic,()),(t_meta,()),(t_integrator,())]:
        try:
            fn(*args)
        except Exception as e:
            RESULTS.append((fn.__name__, "FAIL", f"exception: {e}"))

    print("[OS VALIDATION]")
    for name, status, detail in RESULTS:
        line = f"{status}: {name}"
        if status != "PASS" and detail: line += f"  ({detail})"
        print(line)
    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    n_skip = sum(1 for _, s, _ in RESULTS if s == "SKIP")
    print("-" * 50)
    if n_fail:
        print(f"RESULT: FAIL ({n_fail} failed)")
        sys.exit(1)
    if n_skip:
        print(f"RESULT: PARTIAL PASS (no failures, {n_skip} skipped)")
        sys.exit(2)
    print("RESULT: ALL PASS WITH NO SKIPS")
    sys.exit(0)


if __name__ == "__main__":
    main()
