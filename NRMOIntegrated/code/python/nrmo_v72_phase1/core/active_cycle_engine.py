"""
core/active_cycle_engine.py

ActiveCycleEngine — Maximum + Active + Cyclic.

設計思想:
  - Maximum: 全 module 要素を入れる (引き算ではなく組合せ)
  - Active: 受け身 (recover/A 一辺倒) を抑制、能動的候補を bias
  - Cycle: 過去 cycle の outcome を current decision に反映 (feedback loop)

ActiveCycle の核となる新機能:
  1. ActiveBias: 受動連続カウント → 能動候補を強制 priority up
  2. CyclicFeedback: 過去 cycle の reward trend を current scoring に反映
  3. OpportunityExpansion: Opportunity context をより緩い条件で発生
  4. SynthesisDefault: Synthesis を default として常に評価対象
  5. AggressiveActivation: AggressiveEngine 発動条件緩和 (制御された範囲で)

NRMO 精神は維持:
  - All candidates pass EmergencyResourceGuard, Throttle, Revalidation
  - Hard rule (R <= critical → recover/A 強制) は不変
  - AggressiveEngine は submodule (最終決定権なし)
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
from context_classifier import ContextClassifier, Context, ContextClassification
from contextual_candidate_merger import (
    ContextualCandidateMerger, MergerResult, 
    ELIGIBILITY_TABLE, CONTEXT_WEIGHTS
)
from v9_minimal_engine import SynthesisPathwayStandalone


# ============================================================
# Cycle history tracking
# ============================================================

@dataclass
class CycleRecord:
    """1 cycle の記録"""
    step: int
    action: Action
    module: str
    context: Context
    state_before_R: float
    state_after_R: float
    reward: float
    was_active: bool  # invest/explore = active, recover/defend/hold = passive


@dataclass
class ActiveCycleDecision:
    """ActiveCycleEngine decision"""
    action: Action
    status: str
    confidence: float
    trace: DecisionTrace
    
    context: Optional[ContextClassification] = None
    selected_candidate: Optional[FullCandidate] = None
    standalone_synthesis_action: Optional[Action] = None
    
    consecutive_passive_count: int = 0
    active_bias_applied: bool = False
    opportunity_expanded: bool = False
    
    v71_proposal: Optional[Action] = None
    emergency_guard: Optional[GuardDecision] = None
    throttle_guard: Optional[GuardDecision] = None
    
    metadata: Dict = field(default_factory=dict)


class ActiveCycleEngine:
    """ActiveCycle Maximum Engine
    
    全要素を入れ、ActiveCycle 思想で organised:
      - V71 + EG + TH + AP + Revalidation + CumRisk (v8.4.1 base)
      - MAPLayer + ContextClassifier (sensing)
      - StrongEngineΩfull 全 module + ContextualMerger (selection)
      - SynthesisPathwayStandalone (default synthesis)
      - ActiveCycle bias + CyclicFeedback (active control)
    """
    
    # ActiveCycle parameters
    PASSIVE_CONSECUTIVE_THRESHOLD = 3   # この回数 passive が続くと active bias
    OPPORTUNITY_EXPANSION_O = 55         # Opportunity 認定 O 閾値 (元 60)
    OPPORTUNITY_EXPANSION_R = 35         # 元 40
    OPPORTUNITY_EXPANSION_X = 70         # 元 65
    
    # Synthesis bias
    SYNTHESIS_PRIORITY_BOOST = 0.20     # contextual merger で synthesis score にプラス
    
    # CyclicFeedback
    CYCLE_HISTORY_LENGTH = 20
    ACTIVE_REWARD_BOOST_THRESHOLD = 0.5  # 直近 active で正 reward → 更に active 推奨
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  use_active_bias: bool = True,           # ablation
                  use_cyclic_feedback: bool = True,       # ablation
                  use_opportunity_expansion: bool = True, # ablation
                  use_synthesis_default: bool = True,     # ablation
                  module_config: Optional[Dict[str, bool]] = None,
                  guard_config: Optional[GuardConfig] = None,
                  # ★ Sociable essence (per sociable numbers v6.9)
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
        
        # === Maximum elements ===
        # V71
        v71_rng = self.rng_manager.spawn("v71_base")
        self.v71 = V71Engine(rng=v71_rng)
        
        # Hard guards (v8.4.1 base)
        self.base_guard_config = guard_config or GuardConfig()
        self.emergency_guard = EmergencyResourceGuard(self.base_guard_config)
        self.throttle_guard = ActionIntensityThrottle(self.base_guard_config)
        
        # ActivePattern (v8.4.1 から継承)
        self.active_pattern = ActivePatternProxy()
        self.active_pattern.INTERVENTION_THRESHOLD = 0.35
        
        # Cumulative risk
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        # Sensing layers
        self.map_layer = MAPLayer()
        self.context_classifier = ContextClassifier()
        
        # StrongEngineΩfull with all modules
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
        
        # Contextual merger
        self.contextual_merger = ContextualCandidateMerger()
        
        # Standalone synthesis (V9 提案)
        self.use_synthesis_default = use_synthesis_default
        self.synthesis_standalone = SynthesisPathwayStandalone() if use_synthesis_default else None
        
        # === ActiveCycle specific ===
        self.use_active_bias = use_active_bias
        self.use_cyclic_feedback = use_cyclic_feedback
        self.use_opportunity_expansion = use_opportunity_expansion
        
        # Cycle history
        self.cycle_history: deque = deque(maxlen=self.CYCLE_HISTORY_LENGTH)
        self.consecutive_passive_count = 0
        self.recent_rewards: deque = deque(maxlen=10)
        self.last_successful_active_action: Optional[Action] = None
        
        # Stats
        self.decision_counter = 0
        self.stats = {
            "total_decisions": 0,
            "active_bias_applied": 0,
            "opportunity_expanded": 0,
            "synthesis_default_used": 0,
            "cyclic_feedback_active": 0,
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "module_selection_counts": {},
            "context_counts": {},
            "active_action_count": 0,
            "passive_action_count": 0,
        }
        self.intervention_log: List[Dict] = []
    
    # ============================================================
    # ActiveCycle: condition builder & adapter
    # ============================================================
    
    def _is_active_intent(self, intent: str) -> bool:
        """invest/explore = active, recover/defend/hold = passive"""
        return intent in ("invest", "explore")
    
    def _build_conditions(self) -> Dict:
        """AggressiveEngine 用の conditions + cyclic feedback"""
        conditions = {}
        
        # O confidence
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
        
        # Active feedback (CyclicFeedback)
        if self.use_cyclic_feedback and self.last_successful_active_action:
            conditions["recent_successful_action"] = (
                self.last_successful_active_action.intent,
                self.last_successful_active_action.strength,
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
    
    def _expand_opportunity_check(self, state: WorldState,
                                     context: ContextClassification) -> ContextClassification:
        """OpportunityExpansion: 緩い条件で Opportunity を作る"""
        if not self.use_opportunity_expansion:
            return context
        
        if context.primary_context == Context.NORMAL:
            # Normal だが Opportunity 候補条件をチェック
            if (state.O >= self.OPPORTUNITY_EXPANSION_O and
                state.R >= self.OPPORTUNITY_EXPANSION_R and
                state.X <= self.OPPORTUNITY_EXPANSION_X):
                # Opportunity に昇格 (confidence 控えめ)
                self.stats["opportunity_expanded"] += 1
                return ContextClassification(
                    primary_context=Context.OPPORTUNITY,
                    secondary_contexts=[Context.NORMAL],
                    context_confidence=0.55,  # 控えめ confidence
                    reason=f"OpportunityExpansion: O={state.O:.0f}, R={state.R:.0f}, X={state.X:.0f}",
                    raw_scores=context.raw_scores,
                )
        
        return context
    
    def _apply_active_bias(self, merger_result: MergerResult, 
                             state: WorldState) -> MergerResult:
        """ActiveBias: consecutive passive が多ければ active candidate を boost"""
        if not self.use_active_bias:
            return merger_result
        
        if self.consecutive_passive_count < self.PASSIVE_CONSECUTIVE_THRESHOLD:
            return merger_result
        
        if not merger_result.all_scored:
            return merger_result
        
        # Active candidates の score を boost
        rescored = []
        for cand, score, status in merger_result.all_scored:
            if cand.attack_candidate and self._is_active_intent(cand.attack_candidate.intent):
                # boost (passive 連続数に比例)
                boost = 0.15 * (self.consecutive_passive_count - self.PASSIVE_CONSECUTIVE_THRESHOLD + 1)
                new_score = score + boost
                new_status = status + f"|active_bias_+{boost:.2f}"
                rescored.append((cand, new_score, new_status))
            else:
                rescored.append((cand, score, status))
        
        # Re-sort
        rescored.sort(key=lambda x: -x[1])
        
        # 最良 が変わったか
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
                              "active_bias_changed_best": True,
                              "passive_count": self.consecutive_passive_count},
            )
        
        return merger_result
    
    def _apply_synthesis_default(self, candidates: List[FullCandidate],
                                    state: WorldState,
                                    base_action: Action) -> List[FullCandidate]:
        """SynthesisDefault: standalone synthesis を必ず候補に加える"""
        if not self.use_synthesis_default or self.synthesis_standalone is None:
            return candidates
        
        syn_action = self.synthesis_standalone.synthesize(state, base_action)
        if syn_action is None:
            return candidates
        
        self.stats["synthesis_default_used"] += 1
        
        # FullCandidate に wrap
        synthesis_default_cand = FullCandidate(
            module="SynthesisStandalone",
            attack_candidate=syn_action,
            safe_variant=Action(syn_action.intent, "A"),
            minimum_reversible_variant=Action("hold", "A"),
            expected_upside=0.55,
            estimated_downside=0.12,
            reversibility=0.85,
            reason="synthesis_standalone_default",
        )
        return candidates + [synthesis_default_cand]
    
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
                 context_override: Optional[Dict] = None) -> ActiveCycleDecision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # === Sensing ===
        # V71 base
        v71_a = self.v71.select_action(state)
        trace.add("v71_base", "pass", {"action": f"{v71_a.intent}/{v71_a.strength}"})
        
        # Conditions for AggressiveEngine
        conditions = self._build_conditions()
        
        # Context classification + OpportunityExpansion
        context = self.context_classifier.classify(state, conditions=conditions)
        context = self._expand_opportunity_check(state, context)
        trace.add("context_classify", "pass", context.to_dict())
        
        ctx_name = context.primary_context.value
        self.stats["context_counts"][ctx_name] = self.stats["context_counts"].get(ctx_name, 0) + 1
        
        # === Candidate generation (Maximum) ===
        all_cands = self.strong_engine_full.generate_all_candidates(
            state, conditions=conditions, map_layer=self.map_layer,
            failure_tracker=self.failure_tracker if self.enable_sociable_essence else None,
            apply_canonical_dedup=self.enable_sociable_essence,
        )
        
        # SynthesisDefault: synthesis standalone を加える
        all_cands = self._apply_synthesis_default(all_cands, state, v71_a)
        
        # === Merger (ContextualCandidateMerger + ActiveBias) ===
        merger_result = self.contextual_merger.merge(
            all_cands, state, context,
            failure_tracker=self.failure_tracker if self.enable_sociable_essence else None,
            apply_canonical_dedup=self.enable_sociable_essence,
        )
        merger_result = self._apply_active_bias(merger_result, state)
        
        selected_candidate = merger_result.best_candidate
        
        if selected_candidate is not None:
            current_action = selected_candidate.attack_candidate
            mod_name = selected_candidate.module
            self.stats["module_selection_counts"][mod_name] = \
                self.stats["module_selection_counts"].get(mod_name, 0) + 1
            
            # AggressiveEngine selection tracking
            if mod_name == "AggressiveEngine":
                self.strong_engine_full.aggressive.record_selection(selected_candidate)
        else:
            current_action = v71_a
        
        # === Safety pipeline ===
        status = "ACCEPT"
        
        # EmergencyResourceGuard (hard rule)
        eg = self.emergency_guard.apply(state, current_action)
        if eg.applied:
            if selected_candidate and selected_candidate.module == "AggressiveEngine":
                self.strong_engine_full.aggressive.record_block(
                    selected_candidate, f"guard_{eg.rule_triggered}"
                )
            current_action = eg.forced_action
            status = "GUARD_FORCED"
            self.stats["emergency_triggered"] += 1
            trace.add("emergency_guard", "intervened", eg.to_dict())
        else:
            trace.add("emergency_guard", "pass", {})
        
        # Throttle
        th = self.throttle_guard.apply(state, current_action)
        if th.applied:
            current_action = th.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            self.stats["throttle_triggered"] += 1
        
        # ActivePattern (Maximum なので含める)
        all_cands_simple = self._generate_all_candidates_simple()
        veto = VetoClassification.no_veto()
        ap_proposal = self.active_pattern.evaluate(
            state, all_cands_simple, current_action, veto
        )
        if ap_proposal.has_correction_proposal and ap_proposal.proposed_action:
            passed, _ = self._revalidate(state, ap_proposal.proposed_action)
            if passed:
                current_action = ap_proposal.proposed_action
                if status == "ACCEPT":
                    status = "AP_INTERVENED"
                self.stats["ap_intervened"] += 1
            else:
                self.stats["revalidation_rejected"] += 1
        
        # AggressiveEngine final acceptance
        if (selected_candidate is not None 
            and selected_candidate.module == "AggressiveEngine"
            and current_action == selected_candidate.attack_candidate):
            self.strong_engine_full.aggressive.record_final_accept(selected_candidate)
        
        # === Update histories ===
        self.active_pattern.update_history(state, current_action)
        self.throttle_guard.update_history(state, current_action)
        self.context_classifier.update_history(
            state, current_action, 
            self.recent_rewards[-1] if self.recent_rewards else 0.0
        )
        
        # MAPLayer
        self.map_layer.update(
            t=self.decision_counter,
            state=state,
            action_intent=current_action.intent,
            action_strength=current_action.strength,
            reward=0.0,
        )
        
        # Strong engine invention pathway
        self.strong_engine_full.record_action_taken(current_action)
        
        # === ActiveCycle: passive tracking ===
        is_active = self._is_active_intent(current_action.intent)
        if is_active:
            self.consecutive_passive_count = 0
            self.stats["active_action_count"] += 1
        else:
            self.consecutive_passive_count += 1
            self.stats["passive_action_count"] += 1
        
        # ★ Sociable: remember for failure tracking
        if self.enable_sociable_essence:
            self.last_state_for_sociable = state
            self.last_module_for_sociable = (
                selected_candidate.module if selected_candidate is not None else None
            )
        
        return ActiveCycleDecision(
            action=current_action,
            status=status,
            confidence=0.75,
            trace=trace,
            context=context,
            selected_candidate=selected_candidate,
            consecutive_passive_count=self.consecutive_passive_count,
            active_bias_applied=merger_result.diagnostics.get("active_bias_changed_best", False),
            opportunity_expanded=(context.primary_context == Context.OPPORTUNITY
                                   and "OpportunityExpansion" in context.reason),
            v71_proposal=v71_a,
            emergency_guard=eg,
            throttle_guard=th,
            metadata={"stats": dict(self.stats)},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        self.v71.update_reward(action, reward)
        self.recent_rewards.append(float(reward))
        
        # CyclicFeedback: 成功した active action を記録
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
    
    print("=" * 70)
    print("ActiveCycleEngine Test")
    print("=" * 70)
    
    for world_class, world_name in [(ChaoticWorld, "ChaoticWorld"),
                                       (DriftingWorld, "DriftingWorld")]:
        print(f"\n--- {world_name} (severe) ---")
        for seed in [42, 123, 456]:
            cfg = ChaosConfig.from_level("severe")
            world = world_class(cfg, seed=seed)
            rng_mgr = RNGManager(master_seed=seed + 200000)
            eng = ActiveCycleEngine(rng_manager=rng_mgr,
                                       use_active_bias=True,
                                       use_cyclic_feedback=True,
                                       use_opportunity_expansion=True,
                                       use_synthesis_default=True)
            for t in range(200):
                observed = world.observe()
                d = eng.decide(observed)
                r, done, _ = world.step(d.action)
                eng.update_reward(d.action, r)
                if done:
                    break
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}, "
                  f"active_bias={eng.stats['active_bias_applied']}, "
                  f"opp_exp={eng.stats['opportunity_expanded']}, "
                  f"syn_def={eng.stats['synthesis_default_used']}, "
                  f"EG={eng.stats['emergency_triggered']}")
    
    print("\n[ActiveCycleEngine 動作確認 ✅]")
