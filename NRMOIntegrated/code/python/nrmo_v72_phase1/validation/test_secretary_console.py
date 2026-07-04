import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from secretary_console import EmotionalFilter, FailureLogInput
def test_filter_and_log():
    out=EmotionalFilter().filter_output("お前はいつも間違っている",NRMOContext("d"))
    assert "お前" not in out and "いつも" not in out
    assert "recurrence_condition" in FailureLogInput().reconstruct("疲れている時に高リスク判断をした",NRMOContext("d"))
if __name__=="__main__": test_filter_and_log(); print("secretary OK")
