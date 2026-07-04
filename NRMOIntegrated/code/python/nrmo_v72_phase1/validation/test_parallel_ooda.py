import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from parallel_ooda import ParallelOODA
def test_multi_hypotheses():
    c=NRMOContext("d"); c.state["uncertainty"]=0.8
    adm=[CandidateAction(f"a{i}","x","d",exposure=0.2*i) for i in range(3)]
    ps=ParallelOODA().run(c,adm)
    assert len(ps.metadata["hypotheses"])>=3
    assert all((x in adm or "probe" in x.tags) for x in ps.choices)
if __name__=="__main__": test_multi_hypotheses(); print("parallel_ooda OK")
