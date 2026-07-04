import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from shutdown_guard import ShutdownGuard
def test_silence():
    c=NRMOContext("d"); c.state={"irreversibility":0.9,"observability":0.1,"volatility":0.8}
    assert ShutdownGuard().should_silence("今すぐ送る",c) is True
    c2=NRMOContext("d"); c2.state={"irreversibility":0.1,"observability":0.9,"volatility":0.1}
    assert ShutdownGuard().should_silence("ログを残す",c2) is False
if __name__=="__main__": test_silence(); print("shutdown_guard OK")
