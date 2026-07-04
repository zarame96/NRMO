import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from hare_no_hi import HareNoHiProtocol, NarrativeRandomGenerator
def test_hare():
    h=HareNoHiProtocol()
    assert h.evaluate_action(CandidateAction("k","x","d",reversibility=0.1,tags=["irreversible_commitment"]),NRMOContext("d")).status=="REJECT"
    assert "theme" in NarrativeRandomGenerator().generate(NRMOContext("d"))
if __name__=="__main__": test_hare(); print("hare_no_hi OK")
