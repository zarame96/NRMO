import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from nonergodic_monitor import NonErgodicMonitor
def test_absorbing():
    assert NonErgodicMonitor().detect_absorbing_failure({"capital":0,"trust":0.1,"health":0.2}).status in ("HOLD","REJECT")
if __name__=="__main__": test_absorbing(); print("nonergodic OK")
