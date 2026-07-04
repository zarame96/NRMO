import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from mode_selector import ModeSelector
def test_mode():
    c=NRMOContext("d"); c.state={"sleep_hours":2,"anger":0.8,"time_pressure":0.9}
    assert ModeSelector().select_mode(c)=="SAFE"
if __name__=="__main__": test_mode(); print("mode_selector OK")
