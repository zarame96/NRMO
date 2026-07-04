"""
core/v84_minimal_engine.py

引き算アプローチ:
  v7.1 baseline + ActivePattern Detector のみ.

V8.3 のデバッグ結果から、最重要は ActivePattern (aggressive 暴走の抑制).
StrongEngine Ω, Shinobi, MAPLayer, PassivePattern などは省く.

これで v7.1 を超えるかを測定.
超えれば次に 1 部品ずつ追加.
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from decision_trace import DecisionTrace
from rng_manager import RNGManager
from engines import V71Engine

# v8.3 から ActivePattern と必要部品のみ
from active_pattern_proxy import ActivePatternProxy, ActivePatternProposal
from veto_classification import VetoClassification, VetoType


@dataclass
class V84Decision:
    action: Optional[Action]
    status: str
    confidence: float
    trace: DecisionTrace
    active_pattern_proposal: Optional[ActivePatternProposal] = None
    metadata: Dict = field(default_factory=dict)


class V84MinimalEngine:
    """v7.1 + ActivePattern Detector のみ"""
    
    def __init__(self, rng_manager: Optional[RNGManager] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        self.v71 = V71Engine()
        self.active_pattern = ActivePatternProxy()
        self.decision_counter = 0
    
    def decide(self, state: WorldState, 
                 context: Optional[Dict] = None) -> V84Decision:
        self.decision_counter += 1
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # 1) v7.1 で base action
        base_action = self.v71.select_action(state)
        trace.add("v71_base", "pass", {
            "action": f"{base_action.intent}/{base_action.strength}",
        })
        
        # 2) 候補を 15 全部生成 (ActivePattern 用)
        from world_models import Action as A
        all_candidates = []
        for intent in ["invest", "defend", "explore", "recover", "hold"]:
            for strength in ["A", "B", "C"]:
                all_candidates.append(A(intent=intent, strength=strength))
        
        # 3) 簡易 veto classification (no_veto がデフォルト)
        veto = VetoClassification.no_veto()
        
        # 4) ActivePattern evaluate
        ap_proposal = self.active_pattern.evaluate(
            state, all_candidates, base_action, veto
        )
        trace.add("active_pattern", 
                   "warning" if ap_proposal.has_correction_proposal else "pass",
                   ap_proposal.to_dict())
        
        # 5) 介入があれば proposed_action を採用
        final_action = base_action
        was_intervened = False
        if (ap_proposal.has_correction_proposal 
            and ap_proposal.proposed_action is not None
            and veto.veto_type != VetoType.TRUE_VETO):
            final_action = ap_proposal.proposed_action
            was_intervened = True
            trace.add("intervention", "intervened", {
                "from": f"{base_action.intent}/{base_action.strength}",
                "to": f"{final_action.intent}/{final_action.strength}",
                "reason": ap_proposal.proposal_reason,
            })
        
        # 6) Active Pattern 履歴 update
        self.active_pattern.update_history(state, final_action)
        
        return V84Decision(
            action=final_action,
            status="INTERVENED" if was_intervened else "ACCEPT",
            confidence=0.7,
            trace=trace,
            active_pattern_proposal=ap_proposal,
            metadata={"was_intervened": was_intervened},
        )
    
    def update_reward(self, action: Action, reward: float):
        self.v71.update_reward(action, reward)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from world_models import World, WorldType
    from chaotic_world import ChaoticWorld, ChaosConfig
    
    print("=" * 70)
    print("V8.4 Minimal Engine Test (v7.1 + ActivePattern)")
    print("=" * 70)
    
    # ChaoticWorld mild で動作確認
    config = ChaosConfig.from_level("mild")
    world = ChaoticWorld(config, seed=42)
    
    rng_mgr = RNGManager(master_seed=42 + 600000)
    engine = V84MinimalEngine(rng_manager=rng_mgr)
    
    intervention_count = 0
    for t in range(30):
        d = engine.decide(world.state)
        if d.status == "INTERVENED":
            intervention_count += 1
        
        if t < 12:
            ap_score = d.active_pattern_proposal.score if d.active_pattern_proposal else 0
            marker = "!" if d.status == "INTERVENED" else " "
            print(f"  t={t+1:2d}: {d.action.intent:7s}/{d.action.strength} {marker}  "
                  f"R={world.state.R:.0f} O={world.state.O:.0f} X={world.state.X:.0f}  "
                  f"AP={ap_score:.2f}")
        
        reward, done, _ = world.step(d.action)
        engine.update_reward(d.action, reward)
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    print(f"\n  Score: {world.state.cumulative_score:.2f}, steps={t+1}")
    print(f"  Interventions: {intervention_count}")
    
    print("\n[V84 Minimal 動作確認 完了 ✅]")
