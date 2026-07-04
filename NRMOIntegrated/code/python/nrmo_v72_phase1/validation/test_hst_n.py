import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from hst_n import HSTNClassifier
def test_safe_required():
    c=NRMOContext("d"); c.state={"sleep_hours":2,"anger":0.8,"time_pressure":0.9}
    s=HSTNClassifier().classify(c); assert s.state_label=="SAFE_REQUIRED" or "SAFE_REQUIRED" in s.flags
if __name__=="__main__": test_safe_required(); print("hst_n OK")
