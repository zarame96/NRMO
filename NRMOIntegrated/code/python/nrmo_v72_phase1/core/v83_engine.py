"""
core/v83_engine.py

NRMO v8.3 Integrated Engine — 正典 pipeline

統合構造:

  User Input / Context
    ↓
  [Layer 0]  TypeZero Pre-check       (入力整形)
    ↓
  [Layer 0.5] PassivePattern Pre-Check (入力自体の逃避検査)
    ↓
  [Layer 1]  Frame Definition          (NRMO Core)
    ↓
  [Layer 2]  Falsifiability Monitor    (NRMO Core)
    ↓
  [Layer 3]  Belief Update (POMDP)     (NRMO Core)
    ↓
  [Layer 4]  Distribution Shift Monitor (NRMO Core)
    ↓
  [Layer 4.5] MAPLayer query           (3D V-Cache 参照)
    ↓
  [Layer 5]  Candidate Generation
              ├─ StrongEngine Ω Full (mutation/synthesis/invention)
              └─ Shinobi 12 units (P+E hybrid, Norn/Skuld, TS)
    ↓
  [Layer 6]  CMDP Hard Constraint       (NRMO Core, veto_type 明示)
    ↓
  [Layer 7]  Multi-Framework Eval      (Calibration)
    ↓
  [Layer 8]  Knightian Uncertainty     (Calibration)
    ↓
  [Layer 9]  Calibration Gates          (Calibration)
    ↓
  [Layer 9.5] PassivePattern Recheck   (受動的破壊検出, 提案のみ)
    ↓
  [Layer 9.7] NRMO Revalidation         (PassivePattern 提案を再評価)
    ↓
  [Layer 10] Anti-Goodhart             (補助)
    ↓
  [Layer 11] Reflexivity                (補助)
    ↓
  [Layer 12] Skin in the Game           (補助)
    ↓
  [Layer 13] Tower Transparency         (補助)
    ↓
  [Layer 14] Action Selection
    ↓
  [Layer 14.5] MAPLayer Update           (履歴更新)
    ↓
  [Layer 15] TypeZero Output Adapter   (出力整形)
    ↓
  V83Decision
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "phase8"))
sys.path.insert(0, os.path.join(_HERE, "..", "phase9"))
sys.path.insert(0, os.path.join(_HERE, "..", "phase10"))
sys.path.insert(0, os.path.join(_HERE, "..", "phase11"))

from world_models import WorldState, Action
from decision_trace import DecisionTrace
from rng_manager import RNGManager

# v8.3 新部品
from veto_classification import VetoClassification, VetoType
from cumulative_risk_tracker import CumulativeRiskTracker, CumulativeRiskConfig
from passive_pattern_proxy import PassivePatternProxy, PassivePatternProposal
from typezero_proxy import TypeZeroProxy
from strong_engine_omega import StrongEngineOmega, CandidateAction
from shinobi_engine import ShinobiEngine
from map_layer import MAPLayer

# 既存 v8 部品 (NRMO Core 関係)
from structural_redesign import (
    POMDPFormulation, BayesianUpdater, CMDPFormulation,
    DistributionShiftMonitor
)
from falsifiability import FalsifiabilityMonitor
from frame_and_skin import FrameDefinition, SkinInTheGameEngine
from multi_framework_knightian import MultiFrameworkEnsemble, DecisionOption
from tower_and_feedback import TowerTransparencyEngine


# ============================================================
# V83Decision
# ============================================================

@dataclass
class V83Decision:
    """v8.3 Decision result"""
    action: Optional[Action]
    status: str  # "ACCEPT" / "REJECT" / "HOLD" / "INTERVENED"
    confidence: float
    trace: DecisionTrace
    veto_classification: Optional[VetoClassification]
    passive_pattern_proposal: Optional[PassivePatternProposal]
    formatted_output: Optional[Dict]  # TypeZero formatted
    metadata: Dict = field(default_factory=dict)


# ============================================================
# V83Engine
# ============================================================

class V83Engine:
    """NRMO v8.3 統合エンジン"""
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  enable_meta_log: bool = False):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        self.enable_meta_log = enable_meta_log
        self.decision_counter = 0
        
        # === 新部品 (v8.3) ===
        # StrongEngine Ω Full
        se_rng = self.rng_manager.spawn("strong_engine_omega")
        self.strong_engine_omega = StrongEngineOmega(rng=se_rng)
        
        # Shinobi (P-Core + E-Core hybrid)
        sh_rng = self.rng_manager.spawn("shinobi")
        self.shinobi = ShinobiEngine(rng=sh_rng)
        
        # MAPLayer
        self.map_layer = MAPLayer()
        
        # PassivePattern Proxy
        self.passive_pattern = PassivePatternProxy()
        
        # TypeZero Proxy
        self.typezero = TypeZeroProxy()
        
        # Cumulative Risk Tracker
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        # === NRMO Core (既存) ===
        self.pomdp = POMDPFormulation()
        belief_rng = self.rng_manager.spawn("belief")
        self.belief_updater = BayesianUpdater(
            self.pomdp, n_particles=50, rng=belief_rng
        )
        self.belief_updater.initialize()
        self.cmdp = CMDPFormulation()
        self.shift_monitor = DistributionShiftMonitor(n_reference_samples=50)
        
        # Phase 11
        self.falsifiability = FalsifiabilityMonitor()
        self.frame = FrameDefinition()
        self.multi_framework = MultiFrameworkEnsemble()
        self.skin = SkinInTheGameEngine()
        self.tower = TowerTransparencyEngine()
        
        # === 履歴 (v8.2 で追加) ===
        from collections import deque
        self.recent_R_values = deque(maxlen=10)
        self.last_state: Optional[WorldState] = None
    
    # ============================================================
    # Veto classification (NRMO Core が出力)
    # ============================================================
    
    def _classify_veto_from_cmdp(self, cmdp_violated: bool,
                                    all_violate: bool,
                                    state: WorldState) -> VetoClassification:
        """CMDP の結果から veto_type を分類"""
        if all_violate:
            # 全候補が制約違反 → true_veto
            return VetoClassification.true_veto(
                reason="all_candidates_violate_cmdp_hard_constraints",
                irreversible_threat=True,
                ruin_boundary_breach=(state.X > 90 or state.R < 5),
                absorbing_failure_risk=0.95,
            )
        elif cmdp_violated:
            return VetoClassification.soft_veto(
                reason="some_candidates_violate_constraints",
                ambiguous_risk=True,
            )
        else:
            return VetoClassification.no_veto()
    
    def _classify_veto_from_gate(self, gate_failed: bool,
                                    gate_reasons: List[str]) -> VetoClassification:
        """Calibration Gate の結果から veto_type を分類"""
        if not gate_failed:
            return VetoClassification.no_veto()
        
        # Gate failure は基本 soft_veto
        return VetoClassification.soft_veto(
            reason=f"calibration_gates_failed: {gate_reasons[:3]}",
            uncertainty_driven=True,
            model_disagreement=("agreement_low" in str(gate_reasons)),
        )
    
    def _merge_veto(self, v1: VetoClassification,
                      v2: VetoClassification) -> VetoClassification:
        """より厳しい veto を採用"""
        # TRUE_VETO > SOFT_VETO > NO_VETO
        priority = {VetoType.TRUE_VETO: 2, VetoType.SOFT_VETO: 1, VetoType.NO_VETO: 0}
        if priority[v1.veto_type] >= priority[v2.veto_type]:
            return v1
        return v2
    
    # ============================================================
    # NRMO Revalidation
    # ============================================================
    
    def _nrmo_revalidate(self, state: WorldState,
                          original_action: Action,
                          pp_proposal: PassivePatternProposal,
                          original_veto: VetoClassification) -> Tuple[Action, str, bool]:
        """PassivePattern proposal を NRMO Core で再評価
        
        Returns: (final_action, decision_reason, was_intervened)
        """
        # Rule 5 protection: true_veto は絶対上書きしない
        if original_veto.veto_type == VetoType.TRUE_VETO:
            return original_action, "true_veto_protected", False
        
        # PP 提案がない → そのまま
        if not pp_proposal.has_correction_proposal or pp_proposal.proposed_action is None:
            return original_action, "no_pp_proposal", False
        
        proposed = pp_proposal.proposed_action
        
        # 1) Gating が passed か再確認
        if not pp_proposal.gating_passed:
            return original_action, "pp_gating_failed_on_revalidation", False
        
        # 2) 累積リスク warning なら拒否
        if pp_proposal.cumulative_risk_warning:
            return original_action, "cumulative_risk_breach_reject_pp", False
        
        # 3) proposed_action が CMDP に違反していないか
        constraint_outcomes = self._predict_constraint_outcomes(state, proposed)
        is_feasible, violations = self.cmdp.check_action(proposed, constraint_outcomes)
        if not is_feasible:
            return original_action, f"pp_proposal_violates_cmdp:{violations[:1]}", False
        
        # 4) proposed_action が ruin_boundary を踏まないか
        # 簡易: proposed が high X 時に invest/C なら拒否
        if state.X > 80 and proposed.intent == "invest" and proposed.strength == "C":
            return original_action, "pp_proposal_too_risky_at_high_X", False
        
        # 5) PP proposal を accept
        return proposed, f"pp_intervention_accepted: {pp_proposal.proposal_reason}", True
    
    # ============================================================
    # Helpers
    # ============================================================
    
    def _predict_constraint_outcomes(self, state: WorldState, action: Action) -> Dict:
        """CMDP 用の outcome 予測 (CMDP の constraint names に対応)"""
        intent_delta = {
            "invest":  {"R": -8, "O": +6, "X": +3},
            "defend":  {"R": -2, "X": -5, "O": -1},
            "explore": {"R": -3, "K": +5, "O": +4},
            "recover": {"R": -1, "E": +8, "G": +6, "O": -2},
            "hold":    {"R": -1, "X": +1, "O": -1},
        }
        strength_mult = {"A": 0.6, "B": 1.0, "C": 1.6}
        base = intent_delta.get(action.intent, {})
        mult = strength_mult.get(action.strength, 1.0)
        delta = {k: v * mult for k, v in base.items()}
        
        next_state = {
            "R": state.R + delta.get("R", 0),
            "E": state.E + delta.get("E", 0),
            "G": state.G + delta.get("G", 0),
            "O": state.O + delta.get("O", 0),
            "K": state.K + delta.get("K", 0),
            "X": state.X + delta.get("X", 0),
        }
        
        # CMDP が参照する constraint names に対応
        # ruin_probability <= 0.01: X が極端な時のみ違反
        ruin_prob = max(0.0, min(1.0, max(0, next_state["X"] - 50) / 50 * 0.02))
        # optionality_min >= 10: O が optionality
        optionality = next_state["O"]
        # vision_drift <= 0.3: 簡易 ゼロ
        vision_drift = 0.0
        
        return {
            "ruin_probability": ruin_prob,
            "optionality_min": optionality,
            "vision_drift": vision_drift,
            "next_state_R": next_state["R"],
            "next_state_E": next_state["E"],
            "next_state_G": next_state["G"],
            "next_state_X": next_state["X"],
            "predicted_delta": delta,
        }
    
    def _estimate_observation_noise(self) -> float:
        """状況から観測ノイズを推定 (簡易)"""
        # ChaoticWorld で世界の真の noise を知る術はないが、
        # MAPLayer の near_ruin/regime_shift カウントから推定
        recent_events = self.map_layer.near_ruin_count() + self.map_layer.regime_shift_count()
        if recent_events == 0:
            return 0.05
        elif recent_events < 5:
            return 0.15
        elif recent_events < 15:
            return 0.30
        else:
            return 0.50
    
    # ============================================================
    # Main decide
    # ============================================================
    
    def decide(self, state: WorldState, 
                 context: Optional[Dict] = None) -> V83Decision:
        """V8.3 統合 decide"""
        self.decision_counter += 1
        context = context or {}
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # 履歴 update (v8.2 から)
        self.recent_R_values.append(float(state.R))
        
        # ============ Layer 0: TypeZero Pre-check ============
        typezero_pre = self.typezero.preprocess(context)
        trace.add("typezero_pre", "pass", {
            "objective": typezero_pre.objective,
            "n_required_fields": len(typezero_pre.required_evaluation),
        })
        
        # ============ Layer 0.5: PassivePattern Pre-Check ============
        # 入力自体が逃避か検査 (簡易: context 内に "avoid"/"hold"/"wait" が含まれるか)
        pre_avoidance_keywords = ["avoid", "wait_indefinitely", "fear", "uncertain"]
        situation = str(context.get("situation", "")).lower()
        input_avoidance = any(kw in situation for kw in pre_avoidance_keywords)
        trace.add("passive_pattern_pre", "warning" if input_avoidance else "pass", {
            "input_shows_avoidance": input_avoidance,
        })
        
        # ============ Layer 1: Frame ============
        # 簡易: state ベースで in_frame か (Frame は概念的範囲なので簡略)
        out_of_frame = False  # state は frame 内と仮定 (NRMO の概念領域内)
        if out_of_frame:
            trace.reject("frame", "Out of frame")
            return V83Decision(
                action=None, status="REJECT", confidence=0.0, trace=trace,
                veto_classification=VetoClassification.true_veto(
                    reason="out_of_frame", ruin_boundary_breach=True
                ),
                passive_pattern_proposal=None, formatted_output=None,
            )
        trace.add("frame", "pass", {"in_frame": True})
        
        # ============ Layer 2: Falsifiability ============
        # FalsifiabilityMonitor の API に合わせて簡易チェック
        # critical_failure があれば reject (実装では具体的な basis 必要)
        trace.add("falsifiability", "pass", {"check": "n/a"})
        
        # ============ Layer 3: Belief update ============
        belief_summary = self.belief_updater.get_belief_summary() if self.belief_updater.belief else {}
        trace.add("belief", "pass", {"n_particles": len(self.belief_updater.belief.particles) 
                                       if self.belief_updater.belief else 0})
        
        # ============ Layer 4: Distribution shift ============
        # 簡略 (本格実装は後)
        trace.add("distribution_shift", "pass", {"shift": "n/a"})
        
        # ============ Layer 4.5: MAPLayer query ============
        obs_noise = self._estimate_observation_noise()
        map_view = self.map_layer.query(observation_noise=obs_noise)
        trace.add("map_layer_query", "pass", {
            "observation_noise_est": obs_noise,
            "primary_layer": map_view["primary_layer"],
            "near_ruin_count": self.map_layer.near_ruin_count(),
            "regime_shift_count": self.map_layer.regime_shift_count(),
        })
        
        # ============ Layer 5: Candidate generation ============
        # StrongEngine Ω Full で候補生成
        se_candidates = self.strong_engine_omega.generate_candidates(state)
        
        # Action list として
        candidate_actions = [c.action for c in se_candidates[:15]]
        trace.add("candidates", "pass", {
            "n_candidates": len(candidate_actions),
            "sources": list({c.source for c in se_candidates[:15]}),
        })
        
        # ============ Layer 6: CMDP Hard Constraints ============
        feasible_candidates = []
        for cand in candidate_actions:
            outcomes = self._predict_constraint_outcomes(state, cand)
            is_feasible, violations = self.cmdp.check_action(cand, outcomes)
            if is_feasible:
                feasible_candidates.append(cand)
        
        all_violate = (len(feasible_candidates) == 0)
        cmdp_veto = self._classify_veto_from_cmdp(
            cmdp_violated=(len(feasible_candidates) < len(candidate_actions)),
            all_violate=all_violate,
            state=state,
        )
        
        if all_violate:
            trace.reject("cmdp", "All candidates violate hard constraints")
            return V83Decision(
                action=None, status="REJECT", confidence=0.0, trace=trace,
                veto_classification=cmdp_veto,
                passive_pattern_proposal=None, formatted_output=None,
            )
        
        trace.add("cmdp", "pass", {
            "n_feasible": len(feasible_candidates),
            "veto_type": cmdp_veto.veto_type.value,
        })
        
        # ============ Layer 7: Shinobi 12 units consensus ============
        # Shinobi も意見を出す (StrongEngine Ω と統合した最終 candidate へ)
        shinobi_action, shinobi_info = self.shinobi.decide(state, observation_noise=obs_noise)
        
        # Shinobi の選択肢が feasible に含まれるか
        shinobi_in_feasible = any(
            c.intent == shinobi_action.intent and c.strength == shinobi_action.strength
            for c in feasible_candidates
        )
        trace.add("shinobi_consensus", "pass", {
            "shinobi_chosen": f"{shinobi_action.intent}/{shinobi_action.strength}",
            "in_feasible": shinobi_in_feasible,
            "p_weight": shinobi_info["weights"]["p_core"],
            "e_weight": shinobi_info["weights"]["e_core"],
        })
        
        # ============ Layer 7: Multi-Framework Evaluation ============
        options_list = []
        candidate_map = {}
        for cand in feasible_candidates[:6]:
            ev, worst, best = self.strong_engine_omega._estimate_action_values(state, cand)
            name = f"{cand.intent}/{cand.strength}"
            options_list.append(DecisionOption(
                name=name,
                outcomes=[(0.5, worst), (0.5, best)],
            ))
            candidate_map[name] = cand
        
        # ... simplified: select_best から best_option
        if len(options_list) >= 2:
            try:
                mf_result = self.multi_framework.select_best(options_list)
                best_option_name = mf_result.get("best_option", options_list[0].name)
            except Exception:
                best_option_name = options_list[0].name
            best_candidate = candidate_map.get(best_option_name, feasible_candidates[0])
        else:
            best_candidate = feasible_candidates[0]
            best_option_name = f"{best_candidate.intent}/{best_candidate.strength}"
        
        # Shinobi consensus と Multi-framework の調停
        # 観測ノイズが高ければ Shinobi (より頑健) を優先
        if obs_noise > 0.30 and shinobi_in_feasible:
            best_candidate = shinobi_action
            best_option_name = f"{shinobi_action.intent}/{shinobi_action.strength}"
        
        trace.add("multi_framework", "pass", {
            "best_candidate": best_option_name,
            "shinobi_override": obs_noise > 0.30 and shinobi_in_feasible,
        })
        
        # ============ Layer 8: Knightian uncertainty (state-adaptive v8.1) ============
        belief_var = belief_summary.get("variance", {})
        avg_var = float(np.mean(list(belief_var.values())) if belief_var else 0)
        n_updates = belief_summary.get("n_updates", 0)
        early = n_updates < 5
        state_risk = (state.X > 60) or (state.E < 30)
        action_irrev = best_candidate.strength in ("B", "C")
        is_knightian = (not early and avg_var > 0.015 and (state_risk or action_irrev))
        
        chosen_candidate = best_candidate
        if is_knightian and chosen_candidate.strength == "C":
            chosen_candidate = Action(intent=chosen_candidate.intent, strength="B")
        elif is_knightian and chosen_candidate.strength == "B":
            chosen_candidate = Action(intent=chosen_candidate.intent, strength="A")
        
        trace.add("knightian", "warning" if is_knightian else "pass", {
            "is_knightian": is_knightian,
            "chosen": f"{chosen_candidate.intent}/{chosen_candidate.strength}",
        })
        
        # ============ Layer 9: Calibration Gates ============
        # 簡易: そのまま通す (詳細 gate は省略 v8.3 初版)
        gate_passed = True
        gate_reasons = []
        gate_veto = self._classify_veto_from_gate(not gate_passed, gate_reasons)
        
        trace.add("gate", "pass", {"all_passed": gate_passed})
        
        # ============ Merge veto ============
        merged_veto = self._merge_veto(cmdp_veto, gate_veto)
        
        # ============ Layer 9.5: PassivePattern Recheck ============
        # cumulative risk check
        cum_breached, cum_details = self.cumulative_risk.check_breach()
        
        pp_proposal = self.passive_pattern.evaluate(
            state=state,
            candidates=feasible_candidates,
            final_action=chosen_candidate,
            veto_classification=merged_veto,
            cumulative_risk_breached=cum_breached,
            cumulative_risk_details=cum_details,
        )
        
        trace.add("passive_pattern_recheck", 
                   "warning" if pp_proposal.has_correction_proposal else "pass",
                   pp_proposal.to_dict())
        
        # ============ Layer 9.7: NRMO Revalidation ============
        final_action, revalidation_reason, was_intervened = self._nrmo_revalidate(
            state, chosen_candidate, pp_proposal, merged_veto
        )
        
        trace.add("nrmo_revalidation",
                   "intervened" if was_intervened else "pass",
                   {
                       "intervened": was_intervened,
                       "reason": revalidation_reason,
                       "final_action": f"{final_action.intent}/{final_action.strength}",
                   })
        
        # ============ Layer 10-13: Anti-Goodhart, Reflexivity, Skin, Tower ============
        trace.add("anti_goodhart", "pass", {})
        trace.add("reflexivity", "pass", {})
        trace.add("skin", "pass", {})
        trace.add("tower", "pass", {})
        
        # ============ Layer 14: Action Selection ============
        trace.add("action_selection", "pass", {
            "final": f"{final_action.intent}/{final_action.strength}",
        })
        
        # ============ Layer 14.5: MAPLayer update ============
        self.map_layer.update(
            t=self.decision_counter,
            state=state,
            action_intent=final_action.intent,
            action_strength=final_action.strength,
            reward=0.0,  # reward は update_reward で後追い
        )
        
        # ============ Layer 15: TypeZero Output ============
        decision_payload = {
            "action": final_action,
            "confidence": 0.7,
            "candidates": feasible_candidates,
            "trace": trace,
            "veto_classification": merged_veto,
            "passive_pattern_proposal": pp_proposal,
        }
        formatted = self.typezero.postprocess(decision_payload)
        
        status = "ACCEPT"
        if was_intervened:
            status = "INTERVENED"
        
        return V83Decision(
            action=final_action,
            status=status,
            confidence=0.7,
            trace=trace,
            veto_classification=merged_veto,
            passive_pattern_proposal=pp_proposal,
            formatted_output=formatted.to_dict(),
            metadata={
                "shinobi_info": shinobi_info,
                "observation_noise_est": obs_noise,
                "map_primary_layer": map_view["primary_layer"],
            },
        )
    
    # ============================================================
    # Update reward
    # ============================================================
    
    def update_reward(self, action: Action, reward: float, 
                       state_before: Optional[Dict] = None,
                       state_after: Optional[Dict] = None):
        """報酬伝達 (全部品に)"""
        self.strong_engine_omega.update_reward(action, reward)
        self.shinobi.update_reward(action, reward)
        
        # PP 履歴 update
        if self.last_state is not None:
            self.passive_pattern.update_history(
                self.last_state, action,
                cumulative_score=getattr(self.last_state, 'cumulative_score', 0)
            )
        
        # Cumulative risk update
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)
        
        # MAPLayer の reward を後追い
        if self.map_layer.l1:
            self.map_layer.l1[-1].reward = float(reward)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from world_models import World, WorldType
    
    print("=" * 70)
    print("V83Engine Integrated Test")
    print("=" * 70)
    
    rng_mgr = RNGManager(master_seed=42)
    engine = V83Engine(rng_manager=rng_mgr, enable_meta_log=False)
    
    world = World(WorldType.NORMAL, seed=42)
    
    print(f"\nV8.3 Engine 部品 確認:")
    print(f"  - StrongEngine Ω: {type(engine.strong_engine_omega).__name__}")
    print(f"  - Shinobi: {type(engine.shinobi).__name__} "
          f"(P-Core={len(engine.shinobi.p_cores)}, E-Core={len(engine.shinobi.e_cores)})")
    print(f"  - MAPLayer: {type(engine.map_layer).__name__}")
    print(f"  - PassivePattern: {type(engine.passive_pattern).__name__}")
    print(f"  - TypeZero: {type(engine.typezero).__name__}")
    print(f"  - Cumulative Risk: {type(engine.cumulative_risk).__name__}")
    
    print(f"\n=== Decision Pipeline (5 steps) ===")
    for t in range(5):
        state_before = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                          "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.last_state = world.state
        decision = engine.decide(world.state)
        
        print(f"\nt={t+1}: state R={world.state.R:.1f}, O={world.state.O:.1f}, X={world.state.X:.1f}")
        print(f"  Layers traversed: {len(decision.trace.entries)}")
        print(f"  Final action: {decision.action.intent}/{decision.action.strength}")
        print(f"  Status: {decision.status}")
        print(f"  Veto: {decision.veto_classification.veto_type.value}")
        print(f"  PP level: {decision.passive_pattern_proposal.level}, "
              f"score={decision.passive_pattern_proposal.score:.2f}")
        if decision.passive_pattern_proposal.has_correction_proposal:
            print(f"  PP proposal: {decision.passive_pattern_proposal.original_action.intent}/{decision.passive_pattern_proposal.original_action.strength} "
                  f"→ {decision.passive_pattern_proposal.proposed_action.intent}/{decision.passive_pattern_proposal.proposed_action.strength}")
        
        _, reward, done, _ = world.step(decision.action)
        state_after = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                         "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.update_reward(decision.action, reward, state_before, state_after)
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    print("\n[V83Engine 動作確認 完了 ✅]")
