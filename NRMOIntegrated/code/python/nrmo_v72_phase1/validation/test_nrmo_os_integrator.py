import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from nrmo_os_integrator import NRMOOSIntegrator
def test_integrator():
    c=NRMOContext("d"); c.state={"R":80,"O":70,"X":25,"sleep_hours":7}
    out=NRMOOSIntegrator().process_request("前進案",c)
    assert out["proposal_set"] is not None
    assert out["selected"] is None or out["selected"] in out["admissible"]
if __name__=="__main__": test_integrator(); print("os_integrator OK")
