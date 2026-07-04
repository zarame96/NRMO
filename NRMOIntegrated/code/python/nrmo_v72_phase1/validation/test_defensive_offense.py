import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from defensive_offense import DefensiveOffense, CarrybackController
def test_def():
    d=DefensiveOffense()
    assert d.evaluate(CandidateAction("r","x","d",tags=["retaliation"]),NRMOContext("d")).status=="REJECT"
    assert CarrybackController().carryback({"result":"ok"},NRMOContext("d"))["real_execution_instruction"] is None
if __name__=="__main__": test_def(); print("defensive_offense OK")
