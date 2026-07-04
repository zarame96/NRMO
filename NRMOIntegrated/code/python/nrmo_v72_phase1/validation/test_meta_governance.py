import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from meta_governance import MetaGovernance
def test_meta():
    mg=MetaGovernance()
    assert mg.detect_authority_violation("typezero",{"veto":True}).status=="REJECT"
    assert mg.detect_authority_violation("typezero",{"classification":"x"}).status=="PASS"
if __name__=="__main__": test_meta(); print("meta_governance OK")
