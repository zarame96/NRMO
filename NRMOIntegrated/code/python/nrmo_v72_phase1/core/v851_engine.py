"""
core/v851_engine.py

V8.5.1 = v8.5 + ContextualCandidateMerger.

Pipeline (handoff doc § 7):
  1. Emergency / true VETO check
  2. Context classification
  3. Module eligibility filtering
  4. Context-dependent weighting
  5. Candidate scoring (with recovery penalties § 10)
  6. Repetition / diversity penalty
  7. EmergencyResourceGuard
  8. ActionIntensityThrottle
  9. Calibration
  10. NRMO Revalidation
  11. Final candidate selection

Invariant: Merger does NOT bypass guards/throttle/revalidation.
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
from context_classifier import ContextClassifier, ContextClassification, Context
from contextual_candidate_merger import ContextualCandidateMerger, MergerResult


@dataclass
class V851Decision:
    """V8.5.1 Decision"""
    action: Optional[Action]
    status: str
    confidence: float
    trace: DecisionTrace
    
    # Context
    context: Optional[ContextClassification] = None
    
    # Candidate selection
    selected_candidate: Optional[FullCandidate] = None
    merger_result: Optional[MergerResult] = None
    n_candidates_generated: int = 0
    
    # Pipeline
    base_action_via_v71: Optional[Action] = None
    emergency_guard: Optional[GuardDecision] = None
    throttle_guard: Optional[GuardDecision] = None
    active_pattern_proposal: Optional[object] = None
    revalidation_passed: bool = True
    revalidation_reason: str = ""
    
    metadata: Dict = field(default_factory=dict)


class V851Engine:
    """V8.5.1 = V85 + ContextualCandidateMerger"""
    
    AP_INTERVENTION_THRESHOLD = 0.35
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  use_active_pattern: bool = True,
                  use_strong_engine_full: bool = True,
                  use_contextual_merger: bool = True,  # ablation: contextual vs original
                  module_config: Optional[Dict[str, bool]] = None,
                  aggressive_forced_diagnostic: bool = False,  # § 11
                  guard_config: Optional[GuardConfig] = None,
                  # ★ Sociable essence (per sociable numbers v6.9 handoff)
                  enable_sociable_essence: bool = False):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        # === Sociable essence (shared across StrongEngine + Merger) ===
        self.enable_sociable_essence = enable_sociable_essence
        if enable_sociable_essence:
            from sociable_essence import FailureFaceTracker
            self.failure_tracker = FailureFaceTracker()
            self.last_state_for_sociable: Optional[WorldState] = None
            self.last_module_for_sociable: Optional[str] = None
        else:
            self.failure_tracker = None
        
        # V71 base
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
        self.aggressive_forced_diagnostic = aggressive_forced_diagnostic
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
        
        # ContextClassifier
        self.context_classifier = ContextClassifier()
        
        # Merger: contextual or original (ablation)
        self.use_contextual_merger = use_contextual_merger
        if use_contextual_merger:
            self.contextual_merger = ContextualCandidateMerger()
        else:
            self.contextual_merger = None
        
        # Reward tracking
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
            "context_counts": {},
            "module_selection_counts": {},
            "context_module_table": {},
        }
        self.intervention_log: List[Dict] = []
    
    # ============================================================
    # Build AggressiveEngine conditions
    # ============================================================
    
    def _build_conditions(self) -> Dict:
        conditions = {}
        
        # O confidence (from MAPLayer L2 trends)
        if self.map_layer.l2:
            trends = self.map_layer.get_state_trends()
            if trends:
                o_volatility = abs(trends.get("O", 0))
                conditions["O_confidence"] = max(0.3, 1.0 - o_volatility / 3.0)
            else:
                conditions["O_confidence"] = 0.7
        else:
            conditions["O_confidence"] = 0.7
        
        # Recent drawdown
        if len(self.recent_rewards) >= 3:
            recent_3 = list(self.recent_rewards)[-3:]
            conditions["recent_drawdown"] = sum(recent_3) < -0.5
        else:
            conditions["recent_drawdown"] = False
        
        conditions["true_veto"] = False
        
        # Reward trend
        if len(self.recent_rewards) >= 5:
            x = np.arange(len(self.recent_rewards))
            y = np.array(list(self.recent_rewards))
            slope = float(np.polyfit(x, y, 1)[0])
            conditions["reward_trend"] = slope
        else:
            conditions["reward_trend"] = 0
        
        if self.last_successful_action is not None:
            conditions["recent_successful_action"] = (
                self.last_successful_action.intent,
                self.last_successful_action.strength,
            )
        
        # Score trend
        if self.map_layer.l2:
            trends = self.map_layer.get_state_trends()
            if trends:
                conditions["score_trend"] = (trends.get("R", 0) + trends.get("O", 0)) / 2
        
        # Observation noise
        if self.map_layer.l2:
            near_ruin = self.map_layer.near_ruin_count()
            if near_ruin == 0:
                conditions["observation_noise"] = 0.05
            elif near_ruin < 5:
                conditions["observation_noise"] = 0.15
            elif near_ruin < 15:
                conditions["observation_noise"] = 0.30
            else:
                conditions["observation_noise"] = 0.50
        else:
            conditions["observation_noise"] = 0.05
        
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
                 context_override: Optional[Dict] = None) -> V851Decision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # V71 base (fallback)
        v71_action = self.v71.select_action(state)
        trace.add("v71_base", "pass", {
            "action": f"{v71_action.intent}/{v71_action.strength}"
        })
        
        selected_candidate = None
        merger_result = None
        context_class = None
        n_candidates = 0
        
        if self.use_strong_engine_full and self.strong_engine_full is not None:
            # Step 1: Build conditions
            conditions = self._build_conditions()
            
            # Step 2: Context classification
            context_class = self.context_classifier.classify(state, conditions=conditions)
            trace.add("context_classify", "pass", context_class.to_dict())
            
            ctx_name = context_class.primary_context.value
            self.stats["context_counts"][ctx_name] = \
                self.stats["context_counts"].get(ctx_name, 0) + 1
            
            # Step 3: Generate all candidates (with optional forced diagnostic)
            all_cands = self.strong_engine_full.generate_all_candidates(
                state, conditions=conditions, map_layer=self.map_layer,
                aggressive_forced_diagnostic=self.aggressive_forced_diagnostic,
                failure_tracker=self.failure_tracker if self.enable_sociable_essence else None,
                apply_canonical_dedup=self.enable_sociable_essence,
            )
            n_candidates = len(all_cands)
            
            # Step 4: Merge (contextual or original)
            if self.use_contextual_merger and self.contextual_merger is not None:
                merger_result = self.contextual_merger.merge(
                    all_cands, state, context_class,
                    failure_tracker=self.failure_tracker if self.enable_sociable_essence else None,
                    apply_canonical_dedup=self.enable_sociable_essence,
                )
                if merger_result.best_candidate is not None:
                    selected_candidate = merger_result.best_candidate
                    current_action = selected_candidate.attack_candidate
                    # AggressiveEngine selection tracking
                    if selected_candidate.module == "AggressiveEngine":
                        self.strong_engine_full.aggressive.record_selection(selected_candidate)
                else:
                    current_action = v71_action
                    self.stats["v71_fallback_used"] += 1
            else:
                # Original merger (legacy v8.5)
                from strong_engine_omega_full import CandidateMerger
                if not hasattr(self, '_original_merger'):
                    self._original_merger = CandidateMerger()
                scored = self._original_merger.merge(all_cands, state)
                if scored:
                    selected_candidate = scored[0][0]
                    current_action = selected_candidate.attack_candidate
                else:
                    current_action = v71_action
                    self.stats["v71_fallback_used"] += 1
            
            if selected_candidate is not None:
                self.stats["strong_engine_selected"] += 1
                mod_name = selected_candidate.module
                self.stats["module_selection_counts"][mod_name] = \
                    self.stats["module_selection_counts"].get(mod_name, 0) + 1
                
                # context × module table
                cm = self.stats["context_module_table"]
                if ctx_name not in cm:
                    cm[ctx_name] = {}
                cm[ctx_name][mod_name] = cm[ctx_name].get(mod_name, 0) + 1
                
                trace.add("merger_select", "pass", {
                    "module": mod_name,
                    "mode": selected_candidate.mode,
                    "action": f"{current_action.intent}/{current_action.strength}",
                })
        else:
            # SE OFF
            current_action = v71_action
            self.stats["v71_fallback_used"] += 1
        
        status = "ACCEPT"
        
        # Step 5+: EmergencyResourceGuard
        eg = self.emergency_guard.apply(state, current_action)
        if eg.applied:
            # If this was an AggressiveEngine candidate, record block
            if selected_candidate is not None and selected_candidate.module == "AggressiveEngine":
                self.strong_engine_full.aggressive.record_block(
                    selected_candidate, f"guard_{eg.rule_triggered}"
                )
            # ★ Sociable: Guard 介入 = strong failure signal
            if (self.enable_sociable_essence and self.failure_tracker is not None
                and selected_candidate is not None):
                try:
                    from sociable_essence import FailureFace
                    from loom_core import MODULE_TO_THREAD
                    thread = MODULE_TO_THREAD.get(selected_candidate.module)
                    if thread is not None:
                        self.failure_tracker.record_failure(
                            thread.value, FailureFace.GUARD_REJECTION,
                            state, self.decision_counter
                        )
                except ImportError:
                    pass
            current_action = eg.forced_action
            status = "GUARD_FORCED"
            self.stats["emergency_triggered"] += 1
            trace.add("emergency_guard", "intervened", eg.to_dict())
        else:
            trace.add("emergency_guard", "pass", {})
        
        # Throttle
        th = self.throttle_guard.apply(state, current_action)
        if th.applied:
            # ★ Sociable: Throttle 介入 = failure signal
            if (self.enable_sociable_essence and self.failure_tracker is not None
                and selected_candidate is not None):
                try:
                    from sociable_essence import FailureFace
                    from loom_core import MODULE_TO_THREAD
                    thread = MODULE_TO_THREAD.get(selected_candidate.module)
                    if thread is not None:
                        self.failure_tracker.record_failure(
                            thread.value, FailureFace.REVERSIBILITY_LOW,
                            state, self.decision_counter
                        )
                except ImportError:
                    pass
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
            all_cands_simple = self._generate_all_candidates_simple()
            veto = VetoClassification.no_veto()
            ap_proposal = self.active_pattern.evaluate(
                state, all_cands_simple, current_action, veto
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
        
        # Final aggressive accept tracking
        if (selected_candidate is not None 
            and selected_candidate.module == "AggressiveEngine"
            and current_action == selected_candidate.attack_candidate):
            self.strong_engine_full.aggressive.record_final_accept(selected_candidate)
        
        # Histories
        if self.use_active_pattern and self.active_pattern is not None:
            self.active_pattern.update_history(state, current_action)
        self.throttle_guard.update_history(state, current_action)
        self.context_classifier.update_history(state, current_action, 
                                                  self.recent_rewards[-1] if self.recent_rewards else 0.0)
        
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
        
        self.recent_actions.append(current_action)
        
        # ★ Sociable: remember for next update_reward attribution
        if self.enable_sociable_essence:
            self.last_state_for_sociable = state
            self.last_module_for_sociable = (
                selected_candidate.module if selected_candidate is not None
                else None
            )
        
        return V851Decision(
            action=current_action,
            status=status,
            confidence=0.75,
            trace=trace,
            context=context_class,
            selected_candidate=selected_candidate,
            merger_result=merger_result,
            n_candidates_generated=n_candidates,
            base_action_via_v71=v71_action,
            emergency_guard=eg,
            throttle_guard=th,
            active_pattern_proposal=ap_proposal,
            revalidation_passed=revalidation_passed,
            revalidation_reason=revalidation_reason,
            metadata={"stats": dict(self.stats)},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        self.v71.update_reward(action, reward)
        self.recent_rewards.append(float(reward))
        
        if reward > 0:
            self.last_successful_action = action
        
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)
        
        if self.map_layer.l1:
            self.map_layer.l1[-1].reward = float(reward)
        
        # ★ Sociable failure tracking (per sociable numbers v6.9)
        # Failure signal:
        #   - reward < -0.05 (緩和)
        #   - Emergency Guard 介入
        #   - Throttle 介入
        #   - AP revalidation rejected
        # これらは別 path で record されるので、reward は緩い threshold で OK
        if (self.enable_sociable_essence and self.failure_tracker is not None
            and reward < -0.05
            and self.last_state_for_sociable is not None
            and self.last_module_for_sociable is not None):
            try:
                from sociable_essence import FailureFace
                from loom_core import MODULE_TO_THREAD
                thread = MODULE_TO_THREAD.get(self.last_module_for_sociable)
                if thread is not None:
                    s = self.last_state_for_sociable
                    if s.R <= 20:
                        face = FailureFace.R_CRITICAL
                    elif s.X >= 70:
                        face = FailureFace.X_HIGH
                    elif action.strength == "C":
                        face = FailureFace.REVERSIBILITY_LOW
                    else:
                        face = FailureFace.REPETITION
                    self.failure_tracker.record_failure(
                        thread.value, face, s, self.decision_counter
                    )
            except ImportError:
                pass
    
    # ============================================================
    # AggressiveEngine counter access (handoff doc § 12)
    # ============================================================
    
    def get_aggressive_counters(self) -> Dict:
        if self.strong_engine_full is None:
            return {}
        return dict(self.strong_engine_full.aggressive.counters)
    
    def get_aggressive_mode_counters(self) -> Dict:
        if self.strong_engine_full is None:
            return {}
        return dict(self.strong_engine_full.aggressive.mode_counters)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    
    print("=" * 70)
    print("V8.5.1 Engine Test")
    print("=" * 70)
    
    config = ChaosConfig.from_level("moderate")
    world = ChaoticWorld(config, seed=42)
    
    rng_mgr = RNGManager(master_seed=42 + 3000000)
    engine = V851Engine(rng_manager=rng_mgr,
                          use_active_pattern=True,
                          use_strong_engine_full=True,
                          use_contextual_merger=True)
    
    print("\n--- 25 step trace ---")
    for t in range(25):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = engine.decide(world.state)
        action = d.action if d.action else Action("hold", "A")
        
        if t < 20:
            marker = ""
            if d.status == "GUARD_FORCED": marker += "🛡"
            if d.status == "AP_INTERVENED": marker += "⚡"
            
            ctx = d.context.primary_context.value[:5] if d.context else "????"
            mod = d.selected_candidate.module[:7] if d.selected_candidate else "v71"
            
            print(f"  t={t+1:2d}: [{ctx:>5}] {mod:>8} → "
                  f"{action.intent}/{action.strength} {marker}  "
                  f"R={world.state.R:.0f} X={world.state.X:.0f} O={world.state.O:.0f}")
        
        reward, done, _ = world.step(action)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.update_reward(action, reward, sb, sa)
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    print(f"\n--- Stats ---")
    print(f"  Context counts: {engine.stats['context_counts']}")
    print(f"  Module selection: {engine.stats['module_selection_counts']}")
    print(f"  Aggressive counters: {engine.get_aggressive_counters()}")
    print(f"  Final score: {world.state.cumulative_score:.2f}")
    
    print("\n[V8.5.1 Engine 動作確認 完了 ✅]")
