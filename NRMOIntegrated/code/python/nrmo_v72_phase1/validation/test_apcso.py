import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from apcso import APCSO, APCSOConfig
def test_three_hold_exit():
    c=NRMOContext("d"); cs=[CandidateAction(f"c{i}","x","d",exposure=0.2*i) for i in range(4)]
    ps=APCSO().generate_proposal_set(cs,c,APCSOConfig())
    assert len(ps.choices)<=3 and ps.hold_option and ps.exit_option and "user" in ps.autonomy_note.lower()
    assert len(ps.choices)>=2
if __name__=="__main__": test_three_hold_exit(); print("apcso OK")
