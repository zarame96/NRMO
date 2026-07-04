"""
core/cumulative_risk_tracker.py

追加要件 3: 小さな可逆行動の累積リスクを見る.
個別 invest/A は可逆でも、N 回連続で累積すれば不可逆相当.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque


@dataclass
class CumulativeRiskConfig:
    """累積リスク閾値 (実験で調整)"""
    window_steps: int = 20
    
    # 累積閾値 (この値を超えたら不可逆相当)
    r_drain_threshold: float = 30.0    # R 累積減少
    e_drain_threshold: float = 25.0    # E 累積減少
    x_rise_threshold: float = 25.0     # X 累積上昇
    o_drain_threshold: float = 30.0    # O 累積減少 (機会喪失)


class CumulativeRiskTracker:
    """小さな可逆 action の累積を追跡"""
    
    def __init__(self, config: Optional[CumulativeRiskConfig] = None):
        self.config = config or CumulativeRiskConfig()
        self.action_history: deque = deque(maxlen=self.config.window_steps)
    
    def add(self, action, state_before: Dict[str, float], 
             state_after: Dict[str, float]):
        """1 step の delta を記録"""
        delta = {
            k: state_after[k] - state_before[k]
            for k in ["R", "E", "G", "O", "K", "X"]
            if k in state_before and k in state_after
        }
        self.action_history.append({
            "action_intent": action.intent if action else "none",
            "action_strength": action.strength if action else "A",
            "delta": delta,
        })
    
    def cumulative_delta(self) -> Dict[str, float]:
        """window 内の累積 delta"""
        cum = {"R": 0, "E": 0, "G": 0, "O": 0, "K": 0, "X": 0}
        for entry in self.action_history:
            for k, v in entry["delta"].items():
                cum[k] = cum.get(k, 0) + v
        return cum
    
    def exposure_scalar(self) -> float:
        """累積 risk を 0-1 の単一スカラに正規化 (各次元の閾値比の最大)。
        LoomCore.RiskState.cumulative_exposure へ供給する用。"""
        cum = self.cumulative_delta()
        c = self.config
        ratios = [
            max(0.0, -cum.get("R", 0.0)) / c.r_drain_threshold,
            max(0.0, -cum.get("E", 0.0)) / c.e_drain_threshold,
            max(0.0,  cum.get("X", 0.0)) / c.x_rise_threshold,
            max(0.0, -cum.get("O", 0.0)) / c.o_drain_threshold,
        ]
        return float(min(1.0, max(ratios))) if ratios else 0.0

    def check_breach(self) -> Tuple[bool, Dict]:
        """累積閾値を超えたか判定
        
        Returns: (is_breaching, details)
        """
        cum = self.cumulative_delta()
        breaches = []
        
        if cum["R"] < -self.config.r_drain_threshold:
            breaches.append({
                "type": "cumulative_r_drain",
                "value": cum["R"],
                "threshold": -self.config.r_drain_threshold,
            })
        
        if cum["E"] < -self.config.e_drain_threshold:
            breaches.append({
                "type": "cumulative_e_drain",
                "value": cum["E"],
                "threshold": -self.config.e_drain_threshold,
            })
        
        if cum["X"] > self.config.x_rise_threshold:
            breaches.append({
                "type": "cumulative_x_rise",
                "value": cum["X"],
                "threshold": self.config.x_rise_threshold,
            })
        
        if cum["O"] < -self.config.o_drain_threshold:
            breaches.append({
                "type": "cumulative_o_drain_opportunity_loss",
                "value": cum["O"],
                "threshold": -self.config.o_drain_threshold,
            })
        
        return len(breaches) > 0, {
            "breaches": breaches,
            "cumulative_delta": cum,
            "window_size": len(self.action_history),
        }
    
    def projected_breach_after(self, projected_delta: Dict[str, float]
                                 ) -> Tuple[bool, Dict]:
        """ある proposed_action を取った場合に累積閾値を超えるか予測
        
        proposed_action を実行したと仮定し、累積に加算して check
        """
        cum = self.cumulative_delta()
        # 仮想的に proposed_delta を加算
        projected = {k: cum.get(k, 0) + projected_delta.get(k, 0) 
                      for k in ["R", "E", "G", "O", "K", "X"]}
        
        breaches = []
        if projected["R"] < -self.config.r_drain_threshold:
            breaches.append({"type": "would_cumulative_r_drain", 
                              "value": projected["R"]})
        if projected["E"] < -self.config.e_drain_threshold:
            breaches.append({"type": "would_cumulative_e_drain",
                              "value": projected["E"]})
        if projected["X"] > self.config.x_rise_threshold:
            breaches.append({"type": "would_cumulative_x_rise",
                              "value": projected["X"]})
        
        return len(breaches) > 0, {
            "would_breaches": breaches,
            "projected_cumulative": projected,
        }
