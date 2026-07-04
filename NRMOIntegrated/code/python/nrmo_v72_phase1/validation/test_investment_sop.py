import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common_types import NRMOContext, CandidateAction
from investment_sop import InvestmentSOP
def test_no_real_order():
    a=CandidateAction("o","order","invest",payload={"execute_real_order":True})
    assert InvestmentSOP().evaluate_order(a,NRMOContext("invest")).status=="REJECT"
if __name__=="__main__": test_no_real_order(); print("investment_sop OK")
