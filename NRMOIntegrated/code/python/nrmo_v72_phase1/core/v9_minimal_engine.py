"""
core/v9_minimal_engine.py

V9.0 = V71Engine + EmergencyResourceGuard + SynthesisPathway.

引き算による最終形 (handoff doc § 13 honest 実行):
  
  実証された要素のみ残す:
    ✓ V71Engine (base)
    ✓ EmergencyResourceGuard (実証: drifting/mild で +36.81)
    ✓ SynthesisPathway (実証: drifting/mild で -18.77 寄与)
  
  削除された要素 (寄与ゼロまたは補助):
    ✗ ActionIntensityThrottle (最大 +1.24, 補助)
    ✗ ActivePattern (寄与 ≈ 0)
    ✗ Revalidation (AP 削除なら不要)
    ✗ CumulativeRiskTracker (補助)
    ✗ MAPLayer (information source として効果ゼロ確認済)
    ✗ DefensiveCandidate, RecoveryCandidate, ExplorationCandidate
      MutationPathway, InventionPathway, AggressiveEngineSubmodule
    ✗ ContextClassifier
    ✗ ContextualCandidateMerger
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from rng_manager import RNGManager
from engines import V71Engine
from emergency_guards import EmergencyResourceGuard, GuardConfig, GuardDecision


@dataclass
class V9Decision:
    """V9 decision"""
    action: Action
    status: str  # ACCEPT / GUARD_FORCED / SYNTHESIS_SELECTED
    v71_proposal: Action
    synthesis_proposal: Optional[Action] = None
    guard_decision: Optional[GuardDecision] = None
    reason: str = ""


class SynthesisPathwayStandalone:
    """V9 用 SynthesisPathway (standalone, 他モジュール非依存)
    
    State context から「合成 action」を直接生成:
      state の dominant feature を抽出
      適切な intent/strength を合成
    """
    
    def synthesize(self, state: WorldState, base_action: Action) -> Optional[Action]:
        """State から synthesis candidate を生成"""
        # State の features を判定
        R, E, G, O, K, X = state.R, state.E, state.G, state.O, state.K, state.X
        
        # Multiple weak signals を統合
        signals = []
        
        if X > 60:
            signals.append(("defend", "moderate" if X > 75 else "weak"))
        if R < 30:
            signals.append(("recover", "strong" if R < 20 else "moderate"))
        if E < 30:
            signals.append(("recover", "strong" if E < 20 else "moderate"))
        if O > 65 and R > 40:
            signals.append(("invest", "moderate"))
        if K < 30 and R > 40:
            signals.append(("explore", "weak"))
        
        if not signals:
            return None  # 合成不要
        
        # Multiple signals → 統合
        # 強い signal を優先
        strong_signals = [s for s in signals if s[1] == "strong"]
        if strong_signals:
            # Strong: recovery 優先 (NRMO 精神)
            for intent, _ in strong_signals:
                if intent == "recover":
                    return Action("recover", "A")
            return Action(strong_signals[0][0], "A")
        
        moderate_signals = [s for s in signals if s[1] == "moderate"]
        if moderate_signals:
            # X 高いとき defend を最優先
            for intent, _ in moderate_signals:
                if intent == "defend":
                    return Action("defend", "A")
            # 次に recover
            for intent, _ in moderate_signals:
                if intent == "recover":
                    return Action("recover", "A")
            # 次に invest (機会)
            for intent, _ in moderate_signals:
                if intent == "invest":
                    return Action("invest", "A")
            return Action(moderate_signals[0][0], "A")
        
        # Weak signals: base に近い保守的合成
        weak_signals = [s for s in signals if s[1] == "weak"]
        if weak_signals:
            return Action(weak_signals[0][0], "A")
        
        return None


class V9MinimalEngine:
    """V9.0 = V71 + EG + Synthesis (引き算最終形)"""
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  use_synthesis: bool = True,        # ablation switch
                  use_emergency_guard: bool = True,
                  guard_config: Optional[GuardConfig] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        v71_rng = self.rng_manager.spawn("v71_base")
        self.v71 = V71Engine(rng=v71_rng)
        
        self.use_synthesis = use_synthesis
        self.synthesis = SynthesisPathwayStandalone() if use_synthesis else None
        
        self.use_emergency_guard = use_emergency_guard
        self.guard_config = guard_config or GuardConfig()
        self.emergency_guard = EmergencyResourceGuard(self.guard_config)
        
        # Stats
        self.decision_counter = 0
        self.stats = {
            "total_decisions": 0,
            "synthesis_proposed": 0,
            "synthesis_selected": 0,
            "emergency_triggered": 0,
        }
    
    def _select_between(self, state: WorldState, v71_a: Action, 
                          syn_a: Optional[Action]) -> Tuple[Action, str]:
        """V71 vs Synthesis: 選択ルール
        
        シンプル:
          - synthesis_a がない → v71
          - state.X 高い + syn が defend → syn
          - state.R 低い + syn が recover → syn
          - state.O 高い + R 余裕 + syn が invest → syn
          - 他 → v71
        """
        if syn_a is None:
            return v71_a, "no_synthesis"
        
        # Synthesis を採用する条件
        if state.X > 60 and syn_a.intent == "defend":
            return syn_a, "syn_defend_at_high_X"
        
        if state.R < 30 and syn_a.intent == "recover":
            return syn_a, "syn_recover_at_low_R"
        
        if state.E < 30 and syn_a.intent == "recover":
            return syn_a, "syn_recover_at_low_E"
        
        if state.O > 65 and state.R > 40 and syn_a.intent == "invest":
            return syn_a, "syn_invest_at_opportunity"
        
        # Mild signal: state.X が中程度上昇傾向で defend
        if state.X > 50 and syn_a.intent == "defend":
            return syn_a, "syn_defend_at_mid_X"
        
        return v71_a, "v71_default"
    
    def decide(self, state: WorldState) -> V9Decision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        
        # Step 1: V71 base
        v71_a = self.v71.select_action(state)
        
        # Step 2: Synthesis
        syn_a = None
        if self.use_synthesis and self.synthesis is not None:
            syn_a = self.synthesis.synthesize(state, v71_a)
            if syn_a is not None:
                self.stats["synthesis_proposed"] += 1
        
        # Step 3: Selection
        chosen, reason = self._select_between(state, v71_a, syn_a)
        status = "ACCEPT"
        if syn_a is not None and chosen == syn_a:
            self.stats["synthesis_selected"] += 1
            status = "SYNTHESIS_SELECTED"
        
        # Step 4: Emergency Guard (hard rule)
        eg_decision = None
        if self.use_emergency_guard:
            eg_decision = self.emergency_guard.apply(state, chosen)
            if eg_decision.applied:
                chosen = eg_decision.forced_action
                status = "GUARD_FORCED"
                self.stats["emergency_triggered"] += 1
        
        return V9Decision(
            action=chosen,
            status=status,
            v71_proposal=v71_a,
            synthesis_proposal=syn_a,
            guard_decision=eg_decision,
            reason=reason,
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        self.v71.update_reward(action, reward)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    
    print("=" * 70)
    print("V9 Minimal Engine Test")
    print("=" * 70)
    
    for world_class, world_name in [(ChaoticWorld, "ChaoticWorld"),
                                       (DriftingWorld, "DriftingWorld")]:
        print(f"\n--- {world_name} (severe) ---")
        for seed in [42, 123, 456]:
            cfg = ChaosConfig.from_level("severe")
            world = world_class(cfg, seed=seed)
            rng_mgr = RNGManager(master_seed=seed + 200000)
            eng = V9MinimalEngine(rng_manager=rng_mgr,
                                     use_synthesis=True,
                                     use_emergency_guard=True)
            for t in range(200):
                sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                      "O": world.state.O, "K": world.state.K, "X": world.state.X}
                d = eng.decide(world.state)
                r, done, _ = world.step(d.action)
                sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                      "O": world.state.O, "K": world.state.K, "X": world.state.X}
                eng.update_reward(d.action, r, sb, sa)
                if done:
                    break
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}, "
                  f"syn_sel={eng.stats['synthesis_selected']}, "
                  f"EG={eng.stats['emergency_triggered']}")
    
    print("\n[V9 Minimal Engine 動作確認 ✅]")
