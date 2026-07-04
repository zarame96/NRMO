import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from dag_layer import DAGLayer
def test_proxy_not_true_dynamics():
    assert DAGLayer().evaluate_claim("X is true dynamics.", [], NRMOContext("d")).status in ("HOLD","REJECT")
def test_scoped_evidence_passes():
    r = DAGLayer().evaluate_claim("Within the store proxy model, invest maximizes revenue under tested parameters.", [{"type":"run_log","seeds":[1]}], NRMOContext("d"))
    assert r.status == "PASS"
if __name__=="__main__": test_proxy_not_true_dynamics(); test_scoped_evidence_passes(); print("dag_layer OK")
