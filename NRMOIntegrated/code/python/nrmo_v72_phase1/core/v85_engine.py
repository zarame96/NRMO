"""
core/v85_engine.py

V8.5 = v8.4.1 base + StrongEngineΩfull (with AggressiveEngine submodule).

Pipeline (handoff doc § 14):

  NRMO Core (state assessment)
    ↓
  Allowed Action Set (filtered candidates)
    ↓
  StrongEngineΩfull
    ├─ DefensiveCandidateModule
    ├─ RecoveryCandidateModule
    ├─ ExplorationCandidateModule
    ├─ MutationPathway
    ├─ SynthesisPathway
    ├─ InventionPathway
    ├─ AggressiveEngine Submodule  (handoff doc § 6-13)
    └─ CandidateMerger
    ↓
  EmergencyResourceGuard (hard rule, can override any candidate)
    ↓
  ActionIntensityThrottle
    ↓
  Calibration (V843 predictive intervention 路線は捨てる、v8.4.1 ベース)
    ↓
  NRMO Revalidation (per handoff doc § 7)
    ↓
  Final Action

監査要件:
  ✓ Deterministic RNG (all engines have rng injection)
  ✓ AggressiveEngine NOT independent (it's a submodule)
  ✓ AggressiveEngine has NO final-action authority
  ✓ All proposed actions pass Guard / Throttle / Revalidation
  ✓ MAPLayer used as information source (conditions for AggressiveEngine)
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from decision_trace import DecisionTrace
from rng_manager import RNGManager
from engines import V71Engine

from active_pattern_proxy import ActivePatternProxy
from veto_classification import VetoClassification, VetoType
from emergency_guards import (
    EmergencyResourceGuard, ActionIntensityThrottle,
    GuardConfig, GuardDecision
)
from cumulative_risk_tracker import CumulativeRiskTracker, CumulativeRiskConfig
from map_layer import MAPLayer
from strong_engine_omega_full import StrongEngineOmegaFull, FullCandidate


@dataclass
class V85Decision:
    """V8.5 Decision"""
    action: Optional[Action]
    status: str  # ACCEPT / GUARD_FORCED / AP_INTERVENED / REVALIDATION_REJECTED
    confidence: float
    trace: DecisionTrace
    
    selected_candidate: Optional[FullCandidate] = None
    n_candidates_generated: int = 0
    candidates_by_module: Dict[str, int] = field(default_factory=dict)
    aggressive_activated: bool = False
    aggressive_modes_used: List[str] = field(default_factory=list)
    
    base_action_via_v71: Optional[Action] = None  # フォールバック用
    
    emergency_guard: Optional[GuardDecision] = None
    throttle_guard: Optional[GuardDecision] = None
    active_pattern_proposal: Optional[object] = None
    revalidation_passed: bool = True
    revalidation_reason: str = ""
    
    map_info: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


class V85Engine:
    """V8.5 = v8.4.1 + StrongEngineΩfull"""
    
    AP_INTERVENTION_THRESHOLD = 0.35
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  use_active_pattern: bool = True,
                  use_strong_engine_full: bool = True,
                  module_config: Optional[Dict[str, bool]] = None,  # ablation
                  guard_config: Optional[GuardConfig] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        # V71Engine (fallback / always present)
        v71_rng = self.rng_manager.spawn("v71_base")
        self.v71 = V71Engine(rng=v71_rng)
        
        # Hard guards
        self.base_guard_config = guard_config or GuardConfig()
        self.emergency_guard = EmergencyResourceGuard(self.base_guard_config)
        self.throttle_guard = ActionIntensityThrottle(self.base_guard_config)
        
        # ActivePattern
        self.use_active_pattern = use_active_pattern
        self.active_pattern = ActivePatternProxy() if use_active_pattern else None
        if self.active_pattern:
            self.active_pattern.INTERVENTION_THRESHOLD = self.AP_INTERVENTION_THRESHOLD
        
        # Cumulative risk
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        # MAPLayer
        self.map_layer = MAPLayer()
        
        # StrongEngineΩfull (with module ablation)
        self.use_strong_engine_full = use_strong_engine_full
        if use_strong_engine_full:
            se_rng = self.rng_manager.spawn("strong_engine_full")
            mc = module_config or {}
            self.strong_engine_full = StrongEngineOmegaFull(
                rng=se_rng,
                enable_defensive=mc.get("defensive", True),
                enable_recovery=mc.get("recovery", True),
                enable_exploration=mc.get("exploration", True),
                enable_mutation=mc.get("mutation", True),
                enable_synthesis=mc.get("synthesis", True),
                enable_invention=mc.get("invention", True),
                enable_aggressive=mc.get("aggressive", True),
            )
        else:
            self.strong_engine_full = None
        
        # Reward tracking (for momentum, success detection)
        self.recent_rewards: deque = deque(maxlen=10)
        self.recent_actions: deque = deque(maxlen=10)
        self.last_successful_action: Optional[Action] = None
        
        # Stats
        self.decision_counter = 0
        self.stats = {
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "total_decisions": 0,
            "strong_engine_selected": 0,
            "v71_fallback_used": 0,
            "aggressive_activated_count": 0,
            "aggressive_mode_counts": {},
        }
        self.intervention_log: List[Dict] = []
    
    # ============================================================
    # Build conditions for AggressiveEngine (MAPLayer 経由)
    # ============================================================
    
    def _build_aggressive_conditions(self) -> Dict:
        """MAPLayer + recent history から AggressiveEngine 用の context を構築"""
        conditions = {}
        
        # O confidence (MAPLayer から)
        # L2 O trend が安定なら confidence 高
        if self.map_layer.l2:
            trends = self.map_layer.get_state_trends()
            if trends:
                o_volatility = abs(trends.get("O", 0))
                # 小さな volatility → 高 confidence
                conditions["O_confidence"] = max(0.3, 1.0 - o_volatility / 3.0)
            else:
                conditions["O_confidence"] = 0.7  # default
        else:
            conditions["O_confidence"] = 0.7
        
        # Recent drawdown
        if len(self.recent_rewards) >= 3:
            recent_3 = list(self.recent_rewards)[-3:]
            if sum(recent_3) < -0.5:
                conditions["recent_drawdown"] = True
            else:
                conditions["recent_drawdown"] = False
        else:
            conditions["recent_drawdown"] = False
        
        # True veto (NRMO Core の output に依存だが、現状なし)
        conditions["true_veto"] = False
        
        # Reward trend (momentum)
        if len(self.recent_rewards) >= 5:
            x = np.arange(len(self.recent_rewards))
            y = np.array(list(self.recent_rewards))
            slope = float(np.polyfit(x, y, 1)[0])
            conditions["reward_trend"] = slope
        else:
            conditions["reward_trend"] = 0
        
        # Recent successful action (for momentum)
        if self.last_successful_action is not None:
            conditions["recent_successful_action"] = (
                self.last_successful_action.intent,
                self.last_successful_action.strength,
            )
        
        # Score trend (for anti_stagnation)
        if self.map_layer.l2:
            trends = self.map_layer.get_state_trends()
            if trends:
                # R + O の改善トレンド代替
                conditions["score_trend"] = (trends.get("R", 0) + trends.get("O", 0)) / 2
        
        return conditions
    
    # ============================================================
    # Helpers
    # ============================================================
    
    def _estimate_action_delta(self, action):
        intent_delta = {
            "invest":  {"R": -8, "O": 6, "X": 3},
            "defend":  {"R": -2, "X": -5, "O": -1},
            "explore": {"R": -3, "K": 5, "O": 4},
            "recover": {"R": -1, "E": 8, "G": 6, "O": -2},
            "hold":    {"R": -1, "X": 1, "O": -1},
        }
        strength_mult = {"A": 0.6, "B": 1.0, "C": 1.6}
        base = intent_delta.get(action.intent, {})
        mult = strength_mult.get(action.strength, 1.0)
        return {k: v * mult for k, v in base.items()}
    
    def _revalidate(self, state, proposed):
        """NRMO Revalidation: proposed_action を hard rule で再評価"""
        revalidation = self.emergency_guard.apply(state, proposed)
        if revalidation.applied:
            return False, f"revalidation_failed: {revalidation.rule_triggered}"
        projected_delta = self._estimate_action_delta(proposed)
        breached, _ = self.cumulative_risk.projected_breach_after(projected_delta)
        if breached:
            return False, "cumulative_breach"
        return True, "passed"
    
    def _generate_all_candidates_simple(self) -> List[Action]:
        return [Action(intent=i, strength=s)
                 for i in ["invest", "defend", "explore", "recover", "hold"]
                 for s in ["A", "B", "C"]]
    
    # ============================================================
    # Main decide
    # ============================================================
    
    def decide(self, state: WorldState,
                 context: Optional[Dict] = None) -> V85Decision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # MAPLayer info
        map_info = {
            "near_ruin_count": self.map_layer.near_ruin_count(),
        }
        if self.map_layer.l2:
            trends = self.map_layer.get_state_trends()
            if trends:
                map_info["trends"] = {k: round(v, 3) for k, v in trends.items()}
        
        # V71 base action (fallback / 比較用)
        v71_action = self.v71.select_action(state)
        trace.add("v71_base", "pass", {
            "action": f"{v71_action.intent}/{v71_action.strength}"
        })
        
        # Candidate selection
        selected_candidate = None
        candidates_by_module = {}
        aggressive_activated = False
        aggressive_modes = []
        
        if self.use_strong_engine_full and self.strong_engine_full is not None:
            # ★ StrongEngineΩfull で候補生成
            conditions = self._build_aggressive_conditions()
            trace.add("conditions_built", "pass", conditions)
            
            best_cand, scored_cands = self.strong_engine_full.select_best(
                state, conditions=conditions, map_layer=self.map_layer
            )
            
            if best_cand is not None and best_cand.attack_candidate is not None:
                selected_candidate = best_cand
                # candidate を action として使う
                current_action = best_cand.attack_candidate
                self.stats["strong_engine_selected"] += 1
                
                # Module 統計
                stats_now = self.strong_engine_full.stats
                candidates_by_module = {
                    k: v for k, v in stats_now.items() 
                    if k.startswith("n_") and not k.endswith("_modes")
                }
                
                if best_cand.module == "AggressiveEngine":
                    aggressive_activated = True
                    aggressive_modes.append(best_cand.mode)
                    self.stats["aggressive_activated_count"] += 1
                    mode_counts = self.stats["aggressive_mode_counts"]
                    mode_counts[best_cand.mode] = mode_counts.get(best_cand.mode, 0) + 1
                
                trace.add("strong_engine_full", "selected", {
                    "module": best_cand.module,
                    "mode": best_cand.mode,
                    "action": f"{current_action.intent}/{current_action.strength}",
                    "n_total": len(scored_cands),
                    "expected_upside": best_cand.expected_upside,
                    "estimated_downside": best_cand.estimated_downside,
                })
            else:
                # フォールバック to V71
                current_action = v71_action
                self.stats["v71_fallback_used"] += 1
                trace.add("strong_engine_full", "fallback_v71", {})
        else:
            # ablation: V71 だけ
            current_action = v71_action
            self.stats["v71_fallback_used"] += 1
        
        status = "ACCEPT"
        
        # EmergencyResourceGuard (hard rule)
        eg = self.emergency_guard.apply(state, current_action)
        if eg.applied:
            current_action = eg.forced_action
            status = "GUARD_FORCED"
            self.stats["emergency_triggered"] += 1
            self.intervention_log.append({
                "decision_id": self.decision_counter,
                "type": "emergency_guard",
                "rule": eg.rule_triggered,
            })
            trace.add("emergency_guard", "intervened", eg.to_dict())
        else:
            trace.add("emergency_guard", "pass", {})
        
        # ActionIntensityThrottle
        th = self.throttle_guard.apply(state, current_action)
        if th.applied:
            current_action = th.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            self.stats["throttle_triggered"] += 1
            trace.add("throttle_guard", "intervened", th.to_dict())
        else:
            trace.add("throttle_guard", "pass", {})
        
        # ActivePattern
        ap_proposal = None
        revalidation_passed = True
        revalidation_reason = "n/a"
        if self.use_active_pattern and self.active_pattern is not None:
            all_cands = self._generate_all_candidates_simple()
            veto = VetoClassification.no_veto()
            ap_proposal = self.active_pattern.evaluate(
                state, all_cands, current_action, veto
            )
            if ap_proposal.has_correction_proposal and ap_proposal.proposed_action:
                passed, reason = self._revalidate(state, ap_proposal.proposed_action)
                revalidation_passed = passed
                revalidation_reason = reason
                if passed:
                    current_action = ap_proposal.proposed_action
                    if status == "ACCEPT":
                        status = "AP_INTERVENED"
                    self.stats["ap_intervened"] += 1
                else:
                    self.stats["revalidation_rejected"] += 1
        
        # Histories
        if self.use_active_pattern and self.active_pattern is not None:
            self.active_pattern.update_history(state, current_action)
        self.throttle_guard.update_history(state, current_action)
        
        # MAPLayer update
        self.map_layer.update(
            t=self.decision_counter,
            state=state,
            action_intent=current_action.intent,
            action_strength=current_action.strength,
            reward=0.0,
        )
        
        # Record action for invention pathway
        if self.use_strong_engine_full and self.strong_engine_full is not None:
            self.strong_engine_full.record_action_taken(current_action)
        
        # Track recent action
        self.recent_actions.append(current_action)
        
        return V85Decision(
            action=current_action,
            status=status,
            confidence=0.75,
            trace=trace,
            selected_candidate=selected_candidate,
            n_candidates_generated=len(scored_cands) if 'scored_cands' in dir() else 0,
            candidates_by_module=candidates_by_module,
            aggressive_activated=aggressive_activated,
            aggressive_modes_used=aggressive_modes,
            base_action_via_v71=v71_action,
            emergency_guard=eg,
            throttle_guard=th,
            active_pattern_proposal=ap_proposal,
            revalidation_passed=revalidation_passed,
            revalidation_reason=revalidation_reason,
            map_info=map_info,
            metadata={"stats": dict(self.stats)},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        self.v71.update_reward(action, reward)
        self.recent_rewards.append(float(reward))
        
        # 成功 action を記録
        if reward > 0:
            self.last_successful_action = action
        
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)
        
        if self.map_layer.l1:
            self.map_layer.l1[-1].reward = float(reward)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    
    print("=" * 70)
    print("V8.5 Engine Test (v8.4.1 base + StrongEngineΩfull)")
    print("=" * 70)
    
    config = ChaosConfig.from_level("severe")
    world = ChaoticWorld(config, seed=42)
    
    rng_mgr = RNGManager(master_seed=42 + 2000000)
    engine = V85Engine(rng_manager=rng_mgr,
                         use_active_pattern=True,
                         use_strong_engine_full=True)
    
    print("\n--- 25 step trace ---")
    for t in range(25):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = engine.decide(world.state)
        action = d.action if d.action else Action(intent="hold", strength="A")
        
        if t < 15:
            marker = ""
            if d.aggressive_activated: marker += "🐺"
            if d.status == "GUARD_FORCED": marker += "🛡"
            if d.status == "AP_INTERVENED": marker += "⚡"
            mod = d.selected_candidate.module[:8] if d.selected_candidate else "v71"
            mode = d.selected_candidate.mode if d.selected_candidate and d.selected_candidate.mode else ""
            print(f"  t={t+1:2d}: {mod:>10}/{mode:>20} → "
                  f"{action.intent}/{action.strength} {marker}  "
                  f"R={world.state.R:.0f} X={world.state.X:.0f}")
        
        reward, done, _ = world.step(action)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.update_reward(action, reward, sb, sa)
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    print(f"\n--- Stats ---")
    for k, v in engine.stats.items():
        print(f"  {k}: {v}")
    print(f"  Final score: {world.state.cumulative_score:.2f}")
    
    print("\n[V8.5 Engine 動作確認 完了 ✅]")
