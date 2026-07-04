import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from aallowed import AallowedRegistry
def test_safe_blocks_irreversible():
    c=NRMOContext("d"); c.mode="SAFE"
    a=CandidateAction("x","c","d",reversibility=0.1,exposure=0.9,tags=["irreversible_commitment"])
    assert AallowedRegistry().evaluate(a,c).status=="REJECT"
if __name__=="__main__": test_safe_blocks_irreversible(); print("aallowed OK")
