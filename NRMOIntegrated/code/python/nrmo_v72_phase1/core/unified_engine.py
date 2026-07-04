"""
core/unified_engine.py

UnifiedEngine — 1 engine 内に全 system が同居, 内部協調で最良結果.

Architecture (1 engine 内に全要素):

  Sensing Layer:
    - V71Engine (Bandit base)
    - MAPLayer (memory cache)
    - ContextClassifier (situation awareness)
    - WorldTypeDetector (world signature awareness)
    - EnginePerformanceTracker (internal feedback)
  
  Generation Layer (Maximum candidates):
    - StrongEngineΩfull (8 modules)
      - Defensive, Recovery, Exploration
      - Mutation, Synthesis, Invention pathways
      - AggressiveEngine Submodule (4 modes)
    - SynthesisPathwayStandalone (V9 由来)
  
  Selection Layer (intelligent merging):
    - ContextualCandidateMerger (context-aware scoring)
    - ActiveCycleBias (受動連続抑制)
    - CyclicFeedback (過去 cycle 反映)
    - OpportunityExpansion (機会拡張)
    - WorldAdaptiveWeighting (世界に応じた module 重み調整)  ← 新概念
  
  Safety Pipeline (NRMO 不可侵):
    - EmergencyResourceGuard (hard rule)
    - ActionIntensityThrottle
    - ActivePatternProxy
    - Revalidation
    - CumulativeRiskTracker

全要素が常に動作 (切替ではなく内部協調).
World type → module weight 動的調整 (sub-engine switching ではない).
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque, Counter
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
from context_classifier import ContextClassifier, Context, ContextClassification
from contextual_candidate_merger import (
    ContextualCandidateMerger, MergerResult, 
    ELIGIBILITY_TABLE, CONTEXT_WEIGHTS
)
from v9_minimal_engine import SynthesisPathwayStandalone
from meta_engine import WorldTypeDetector


# ============================================================
# World-Adaptive Module Weighting
# ============================================================
# Honest benchmark findings から導出:
#   chaotic:    v8.5.1 / ActiveCycle / Synthesis 多用が強い → Aggressive 強化
#   drifting:   v9_minimal (引き算 + Synthesis) が強い → SynthesisStandalone 強化
#   noisy:      v8.5.1 / recover_fixed が強い → Recovery + Defensive 強化

WORLD_MODULE_WEIGHT_BOOSTS: Dict[str, Dict[str, float]] = {
    "chaotic": {
        "AggressiveEngine":     +0.15,
        "SynthesisPathway":     +0.10,
        "ExplorationCandidate": +0.05,
    },
    "drifting": {
        "SynthesisStandalone":  +0.25,  # V9 由来, drifting で実証
        "SynthesisPathway":     +0.15,
        "AggressiveEngine":     -0.15,  # drifting では active が裏目
        "MutationPathway":       0.0,
    },
    "noisy": {
        "RecoveryCandidate":    +0.05,  # 受け身 safer
        "DefensiveCandidate":   +0.05,
        "SynthesisPathway":     +0.05,
        "AggressiveEngine":     -0.10,  # 観測ノイズで攻撃は危険
    },
    "unknown": {
        # 緩い default boost (warmup 期)
    },
}


# ============================================================
# UnifiedDecision
# ============================================================

@dataclass
class UnifiedDecision:
    """UnifiedEngine decision"""
    action: Action
    status: str
    confidence: float
    trace: DecisionTrace
    
    context: Optional[ContextClassification] = None
    world_type: str = "unknown"
    world_confidence: float = 0.0
    
    selected_candidate: Optional[FullCandidate] = None
    n_candidates_generated: int = 0
    
    consecutive_passive_count: int = 0
    active_bias_applied: bool = False
    opportunity_expanded: bool = False
    world_adaptive_weights_applied: bool = False
    
    v71_proposal: Optional[Action] = None
    emergency_guard: Optional[GuardDecision] = None
    throttle_guard: Optional[GuardDecision] = None
    
    metadata: Dict = field(default_factory=dict)


# ============================================================
# UnifiedEngine
# ============================================================

class UnifiedEngine:
    """UnifiedEngine — 1 engine 内に全 system, 内部協調.
    
    全要素を常時動作.
    World type → module weight 動的調整 (sub-engine switching ではない).
    NRMO 精神 (hard guard, revalidation) 不可侵.
    """
    
    # ActiveCycle parameters
    PASSIVE_CONSECUTIVE_THRESHOLD = 3
    OPPORTUNITY_EXPANSION_O = 55
    OPPORTUNITY_EXPANSION_R = 35
    OPPORTUNITY_EXPANSION_X = 70
    
    # WorldAware parameters
    WORLD_DETECT_HISTORY_SIZE = 15
    WORLD_BOOST_WARMUP = 8  # 序盤は boost 抑制
    
    # CyclicFeedback
    ACTIVE_REWARD_BOOST_THRESHOLD = 0.5
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  # ablation switches
                  use_active_bias: bool = True,
                  use_cyclic_feedback: bool = True,
                  use_opportunity_expansion: bool = True,
                  use_synthesis_default: bool = True,
                  use_world_adaptive_weights: bool = True,
                  # module config
                  module_config: Optional[Dict[str, bool]] = None,
                  guard_config: Optional[GuardConfig] = None,
                  # ★ Sociable essence
                  enable_sociable_essence: bool = False):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        # === Sociable essence ===
        self.enable_sociable_essence = enable_sociable_essence
        if enable_sociable_essence:
            from sociable_essence import FailureFaceTracker
            self.failure_tracker = FailureFaceTracker()
            self.last_state_for_sociable: Optional[WorldState] = None
            self.last_module_for_sociable: Optional[str] = None
        else:
            self.failure_tracker = None
        
        # === Sensing Layer ===
        v71_rng = self.rng_manager.spawn("v71_base")
        self.v71 = V71Engine(rng=v71_rng)
        
        self.map_layer = MAPLayer()
        self.context_classifier = ContextClassifier()
        self.world_detector = WorldTypeDetector(history_size=self.WORLD_DETECT_HISTORY_SIZE)
        
        # === Generation Layer ===
        se_rng = self.rng_manager.spawn("strong_engine")
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
        
        self.use_synthesis_default = use_synthesis_default
        self.synthesis_standalone = SynthesisPathwayStandalone() if use_synthesis_default else None
        
        # === Selection Layer ===
        self.contextual_merger = ContextualCandidateMerger()
        
        self.use_active_bias = use_active_bias
        self.use_cyclic_feedback = use_cyclic_feedback
        self.use_opportunity_expansion = use_opportunity_expansion
        self.use_world_adaptive_weights = use_world_adaptive_weights
        
        # ActiveCycle state
        self.consecutive_passive_count = 0
        self.recent_rewards: deque = deque(maxlen=10)
        self.last_successful_active_action: Optional[Action] = None
        
        # === Safety Layer ===
        self.base_guard_config = guard_config or GuardConfig()
        self.emergency_guard = EmergencyResourceGuard(self.base_guard_config)
        self.throttle_guard = ActionIntensityThrottle(self.base_guard_config)
        self.active_pattern = ActivePatternProxy()
        self.active_pattern.INTERVENTION_THRESHOLD = 0.35
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        # Stats
        self.decision_counter = 0
        self.stats = {
            "total_decisions": 0,
            "active_bias_applied": 0,
            "opportunity_expanded": 0,
            "synthesis_default_used": 0,
            "world_adaptive_applied": 0,
            "cyclic_feedback_active": 0,
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "module_selection_counts": {},
            "context_counts": {},
            "world_type_counts": {},
            "active_action_count": 0,
            "passive_action_count": 0,
        }
        self.intervention_log: List[Dict] = []
    
    # ============================================================
    # Helpers
    # ============================================================
    
    def _is_active_intent(self, intent: str) -> bool:
        return intent in ("invest", "explore")
    
    def _build_conditions(self) -> Dict:
        conditions = {}
        # O confidence
        if self.map_layer.l2:
            trends = self.map_layer.get_state_trends()
            if trends:
                o_vol = abs(trends.get("O", 0))
                conditions["O_confidence"] = max(0.3, 1.0 - o_vol / 3.0)
            else:
                conditions["O_confidence"] = 0.7
        else:
            conditions["O_confidence"] = 0.7
        
        # Drawdown
        if len(self.recent_rewards) >= 3:
            recent_3 = list(self.recent_rewards)[-3:]
            conditions["recent_drawdown"] = sum(recent_3) < -0.5
        else:
            conditions["recent_drawdown"] = False
        
        conditions["true_veto"] = False
        
        if len(self.recent_rewards) >= 5:
            x = np.arange(len(self.recent_rewards))
            y = np.array(list(self.recent_rewards))
            conditions["reward_trend"] = float(np.polyfit(x, y, 1)[0])
        else:
            conditions["reward_trend"] = 0
        
        if self.use_cyclic_feedback and self.last_successful_active_action:
            conditions["recent_successful_action"] = (
                self.last_successful_active_action.intent,
                self.last_successful_active_action.strength,
            )
        
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
    
    def _expand_opportunity_check(self, state, context):
        if not self.use_opportunity_expansion:
            return context
        if context.primary_context == Context.NORMAL:
            if (state.O >= self.OPPORTUNITY_EXPANSION_O and
                state.R >= self.OPPORTUNITY_EXPANSION_R and
                state.X <= self.OPPORTUNITY_EXPANSION_X):
                self.stats["opportunity_expanded"] += 1
                return ContextClassification(
                    primary_context=Context.OPPORTUNITY,
                    secondary_contexts=[Context.NORMAL],
                    context_confidence=0.55,
                    reason=f"OpportunityExpansion: O={state.O:.0f}, R={state.R:.0f}",
                    raw_scores=context.raw_scores,
                )
        return context
    
    def _apply_synthesis_default(self, candidates, state, base_action):
        if not self.use_synthesis_default or self.synthesis_standalone is None:
            return candidates
        syn_action = self.synthesis_standalone.synthesize(state, base_action)
        if syn_action is None:
            return candidates
        self.stats["synthesis_default_used"] += 1
        return candidates + [FullCandidate(
            module="SynthesisStandalone",
            attack_candidate=syn_action,
            safe_variant=Action(syn_action.intent, "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.55,
            estimated_downside=0.12,
            reversibility=0.85,
            reason="synthesis_standalone_default",
        )]
    
    def _apply_world_adaptive_weights(self, candidates: List[FullCandidate],
                                         world_type: str,
                                         world_confidence: float) -> List[FullCandidate]:
        """★ 新概念: World type に応じて candidate の upside/downside を調整
        
        Sub-engine 切替ではなく、module 内部重みを world 適応的に変更.
        """
        if not self.use_world_adaptive_weights:
            return candidates
        if self.decision_counter < self.WORLD_BOOST_WARMUP:
            return candidates
        if world_confidence < 0.4:
            return candidates  # 確信ない時は調整しない
        
        boosts = WORLD_MODULE_WEIGHT_BOOSTS.get(world_type, {})
        if not boosts:
            return candidates
        
        self.stats["world_adaptive_applied"] += 1
        
        # FullCandidate を変更 (upside boost / downside reduce)
        adjusted = []
        for cand in candidates:
            module = cand.module
            boost = boosts.get(module, 0.0)
            
            # Confidence でスケール
            scaled_boost = boost * world_confidence
            
            if scaled_boost != 0:
                # 新 FullCandidate (upside + scaled_boost, downside - scaled_boost/2)
                adjusted_cand = FullCandidate(
                    module=cand.module,
                    mode=cand.mode,
                    attack_candidate=cand.attack_candidate,
                    safe_variant=cand.safe_variant,
                    minimum_reversible_variant=cand.minimum_reversible_variant,
                    expected_upside=cand.expected_upside + scaled_boost,
                    estimated_downside=max(0, cand.estimated_downside - scaled_boost / 2),
                    reversibility=cand.reversibility,
                    required_conditions=cand.required_conditions,
                    stop_conditions=cand.stop_conditions,
                    reason=cand.reason + f"|world_boost({world_type}:{scaled_boost:+.2f})",
                )
                adjusted.append(adjusted_cand)
            else:
                adjusted.append(cand)
        
        return adjusted
    
    def _apply_active_bias(self, merger_result, state):
        if not self.use_active_bias:
            return merger_result
        if self.consecutive_passive_count < self.PASSIVE_CONSECUTIVE_THRESHOLD:
            return merger_result
        if not merger_result.all_scored:
            return merger_result
        
        rescored = []
        for cand, score, status in merger_result.all_scored:
            if cand.attack_candidate and self._is_active_intent(cand.attack_candidate.intent):
                boost = 0.15 * (self.consecutive_passive_count - self.PASSIVE_CONSECUTIVE_THRESHOLD + 1)
                rescored.append((cand, score + boost, status + f"|active_bias_+{boost:.2f}"))
            else:
                rescored.append((cand, score, status))
        
        rescored.sort(key=lambda x: -x[1])
        new_best = rescored[0][0]
        if new_best != merger_result.best_candidate:
            self.stats["active_bias_applied"] += 1
            return MergerResult(
                best_candidate=new_best,
                best_score=rescored[0][1],
                all_scored=rescored,
                context=merger_result.context,
                n_eligible=merger_result.n_eligible,
                n_suppressed=merger_result.n_suppressed,
                diagnostics={**merger_result.diagnostics,
                              "active_bias_changed_best": True},
            )
        return merger_result
    
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
            return False, f"revalidation_failed"
        projected_delta = self._estimate_action_delta(proposed)
        breached, _ = self.cumulative_risk.projected_breach_after(projected_delta)
        if breached:
            return False, "cumulative_breach"
        return True, "passed"
    
    def _generate_all_candidates_simple(self):
        return [Action(intent=i, strength=s)
                 for i in ["invest", "defend", "explore", "recover", "hold"]
                 for s in ["A", "B", "C"]]
    
    # ============================================================
    # Main decide
    # ============================================================
    
    def decide(self, observation: WorldState) -> UnifiedDecision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # === Sensing Layer ===
        self.world_detector.update(observation)
        world_type, world_conf = self.world_detector.detect_world_type()
        self.stats["world_type_counts"][world_type] = \
            self.stats["world_type_counts"].get(world_type, 0) + 1
        
        v71_a = self.v71.select_action(observation)
        trace.add("v71_base", "pass", {"action": f"{v71_a.intent}/{v71_a.strength}"})
        
        conditions = self._build_conditions()
        context = self.context_classifier.classify(observation, conditions=conditions)
        context = self._expand_opportunity_check(observation, context)
        
        ctx_name = context.primary_context.value
        self.stats["context_counts"][ctx_name] = self.stats["context_counts"].get(ctx_name, 0) + 1
        
        # === Generation Layer (Maximum) ===
        all_cands = self.strong_engine_full.generate_all_candidates(
            observation, conditions=conditions, map_layer=self.map_layer,
            failure_tracker=self.failure_tracker if self.enable_sociable_essence else None,
            apply_canonical_dedup=self.enable_sociable_essence,
        )
        all_cands = self._apply_synthesis_default(all_cands, observation, v71_a)
        
        # ★ World adaptive weighting (新)
        all_cands = self._apply_world_adaptive_weights(all_cands, world_type, world_conf)
        
        # === Selection Layer ===
        merger_result = self.contextual_merger.merge(
            all_cands, observation, context,
            failure_tracker=self.failure_tracker if self.enable_sociable_essence else None,
            apply_canonical_dedup=self.enable_sociable_essence,
        )
        merger_result = self._apply_active_bias(merger_result, observation)
        
        selected_candidate = merger_result.best_candidate
        if selected_candidate is not None:
            current_action = selected_candidate.attack_candidate
            mod_name = selected_candidate.module
            self.stats["module_selection_counts"][mod_name] = \
                self.stats["module_selection_counts"].get(mod_name, 0) + 1
            if mod_name == "AggressiveEngine":
                self.strong_engine_full.aggressive.record_selection(selected_candidate)
        else:
            current_action = v71_a
        
        # === Safety Layer ===
        status = "ACCEPT"
        
        eg = self.emergency_guard.apply(observation, current_action)
        if eg.applied:
            if selected_candidate and selected_candidate.module == "AggressiveEngine":
                self.strong_engine_full.aggressive.record_block(
                    selected_candidate, f"guard_{eg.rule_triggered}"
                )
            current_action = eg.forced_action
            status = "GUARD_FORCED"
            self.stats["emergency_triggered"] += 1
        
        th = self.throttle_guard.apply(observation, current_action)
        if th.applied:
            current_action = th.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            self.stats["throttle_triggered"] += 1
        
        all_cands_simple = self._generate_all_candidates_simple()
        veto = VetoClassification.no_veto()
        ap_proposal = self.active_pattern.evaluate(
            observation, all_cands_simple, current_action, veto
        )
        if ap_proposal.has_correction_proposal and ap_proposal.proposed_action:
            passed, _ = self._revalidate(observation, ap_proposal.proposed_action)
            if passed:
                current_action = ap_proposal.proposed_action
                if status == "ACCEPT":
                    status = "AP_INTERVENED"
                self.stats["ap_intervened"] += 1
            else:
                self.stats["revalidation_rejected"] += 1
        
        if (selected_candidate is not None 
            and selected_candidate.module == "AggressiveEngine"
            and current_action == selected_candidate.attack_candidate):
            self.strong_engine_full.aggressive.record_final_accept(selected_candidate)
        
        # === Update histories ===
        self.active_pattern.update_history(observation, current_action)
        self.throttle_guard.update_history(observation, current_action)
        self.context_classifier.update_history(
            observation, current_action,
            self.recent_rewards[-1] if self.recent_rewards else 0.0
        )
        
        self.map_layer.update(
            t=self.decision_counter,
            state=observation,
            action_intent=current_action.intent,
            action_strength=current_action.strength,
            reward=0.0,
        )
        
        self.strong_engine_full.record_action_taken(current_action)
        
        # ActiveCycle passive tracking
        if self._is_active_intent(current_action.intent):
            self.consecutive_passive_count = 0
            self.stats["active_action_count"] += 1
        else:
            self.consecutive_passive_count += 1
            self.stats["passive_action_count"] += 1
        
        # ★ Sociable: remember for failure tracking
        if self.enable_sociable_essence:
            self.last_state_for_sociable = observation
            self.last_module_for_sociable = (
                selected_candidate.module if selected_candidate is not None else None
            )
        
        return UnifiedDecision(
            action=current_action,
            status=status,
            confidence=0.75,
            trace=trace,
            context=context,
            world_type=world_type,
            world_confidence=world_conf,
            selected_candidate=selected_candidate,
            n_candidates_generated=len(all_cands),
            consecutive_passive_count=self.consecutive_passive_count,
            active_bias_applied=merger_result.diagnostics.get("active_bias_changed_best", False),
            opportunity_expanded=(context.primary_context == Context.OPPORTUNITY
                                   and "OpportunityExpansion" in context.reason),
            world_adaptive_weights_applied=(self.use_world_adaptive_weights and
                                              world_conf >= 0.4 and
                                              self.decision_counter >= self.WORLD_BOOST_WARMUP),
            v71_proposal=v71_a,
            emergency_guard=eg,
            throttle_guard=th,
            metadata={"stats": dict(self.stats)},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        self.v71.update_reward(action, reward)
        self.recent_rewards.append(float(reward))
        
        if (reward > self.ACTIVE_REWARD_BOOST_THRESHOLD and 
            self._is_active_intent(action.intent)):
            self.last_successful_active_action = action
            self.stats["cyclic_feedback_active"] += 1
        
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)
        
        if self.map_layer.l1:
            self.map_layer.l1[-1].reward = float(reward)
        
        # ★ Sociable failure tracking
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
    
    def get_aggressive_counters(self) -> Dict:
        return dict(self.strong_engine_full.aggressive.counters)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    from noisy_world import NoisyObservationWorld
    
    print("=" * 70)
    print("UnifiedEngine Test")
    print("=" * 70)
    
    for world_class, world_name in [
        (ChaoticWorld, "Chaotic"),
        (DriftingWorld, "Drifting"),
        (NoisyObservationWorld, "Noisy"),
    ]:
        print(f"\n--- {world_name} (severe) ---")
        for seed in [42, 123]:
            cfg = ChaosConfig.from_level("severe")
            world = world_class(cfg, seed=seed)
            rng_mgr = RNGManager(master_seed=seed + 200000)
            eng = UnifiedEngine(rng_manager=rng_mgr,
                                   use_active_bias=True,
                                   use_cyclic_feedback=True,
                                   use_opportunity_expansion=True,
                                   use_synthesis_default=True,
                                   use_world_adaptive_weights=True)
            for t in range(200):
                d = eng.decide(world.observe())
                r, done, _ = world.step(d.action)
                eng.update_reward(d.action, r)
                if done:
                    break
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}")
            print(f"    world detected: {eng.stats['world_type_counts']}")
            print(f"    modules selected: {eng.stats['module_selection_counts']}")
            print(f"    world_adaptive: {eng.stats['world_adaptive_applied']}, "
                  f"active_bias: {eng.stats['active_bias_applied']}, "
                  f"opp_exp: {eng.stats['opportunity_expanded']}")
            print(f"    aggressive: {eng.get_aggressive_counters()}")
    
    print("\n[UnifiedEngine 動作確認 ✅]")
