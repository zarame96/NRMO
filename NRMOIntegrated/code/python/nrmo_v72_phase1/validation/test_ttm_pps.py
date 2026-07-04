import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from ttm_pps import TTMPPS
def test_blocks_real():
    a=CandidateAction("z","x","d",tags=["real_world_execution"])
    assert TTMPPS().prohibit_real_execution(a).status=="REJECT"
if __name__=="__main__": test_blocks_real(); print("ttm_pps OK")
