import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from life_sop import LifeSOP
def test_life():
    c=NRMOContext("d"); c.state={"sleep_hours":3}
    assert LifeSOP().morning_startup(c)["mode"]=="SAFE"
    assert LifeSOP().night_non_recovery(c)["log_only"] is True
if __name__=="__main__": test_life(); print("life_sop OK")
