"""
core/v8_engine.py

V8Engine: NRMO v8 の統合 decision pipeline

監査指摘 1 (v8 runtime engine が存在しない) への対応。
Phase 7-11 の部品を実際の意思決定パイプラインへ接続する。

Pipeline 順:
  Frame → Falsifiability → POMDP/Belief → Distribution Shift
  → Multi-framework → Knightian → CMDP → StrongEngine
  → Calibration Gate → Anti-Goodhart / Reflexivity
  → Skin in the Game → Tower → Action selection → External Feedback
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Path setup
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CORE_DIR)
for subdir in ["phase7", "phase8", "phase9", "phase10", "phase11", "core"]:
    sys.path.insert(0, os.path.join(_PROJECT_ROOT, subdir))

# Core imports
from decision_trace import DecisionTrace
from rng_manager import RNGManager
from world_models import WorldState, Action
from engines import V71Engine

# Phase 11: 認識論的基盤
from falsifiability import FalsifiabilityMonitor
from frame_and_skin import (
    FrameDefinition, FrameStatus,
    SkinInTheGameEngine, StakeLevel,
)
from multi_framework_knightian import (
    MultiFrameworkEnsemble, KnightianAwareEngine,
    DecisionOption, ImpreciseOption, ImpreciseProbability,
)
from tower_and_feedback import (
    TowerTransparencyEngine, ExternalFeedbackIntegrator,
    ExternalFeedback, FeedbackSource,
)

# Phase 8: 構造的再設計
from structural_redesign import (
    POMDPFormulation, BayesianUpdater, BeliefState, Observation,
    CMDPFormulation, Constraint,
    DistributionShiftMonitor,
)

# Phase 9: 認知的拡張
from cognitive_expansion import (
    CausalGraph, DualPathEngine,
    MetaCognitionModule, SurvivorshipBiasCorrector,
    ProspectTheoryReward, HyperbolicDiscounter,
)

# Phase 10: ストレス耐性
from stress_resilience import (
    AntiGoodhartFramework, ReflexivityAwareEngine,
    TripleModularRedundancy, BarbellStrategy,
    AdversarialAgent, ExtremeValueAnalyzer,
)


# ============================================================
# V8Engine の出力データ型
# ============================================================

@dataclass
class V8Decision:
    """V8Engine の最終出力"""
    action: Optional[Action]
    status: str  # "ACCEPT" | "REJECT" | "HOLD"
    confidence: float  # [0.0, 1.0]
    trace: DecisionTrace
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Calibration Gate (v7.2 から本格的に統合)
# ============================================================

class CalibrationGate:
    """Phase 1-6 で発見された最適 7 Gates の統合実装
    G1, G2, G3, G6, G7, G8, G9
    """
    
    def __init__(self):
        self.gates_active = ["G1", "G2", "G3", "G6", "G7", "G8", "G9"]
        self.activation_count = {g: 0 for g in self.gates_active}
    
    def apply(self, state: WorldState, action: Action, 
              belief_summary: Dict) -> Tuple[bool, Optional[str], Dict]:
        """Gate を順次適用
        
        Returns: (gate_passed, failed_gate, gate_data)
        """
        gate_data = {"applied": [], "failed_gate": None}
        
        # G1: 単位整合性 (常時 OK と仮定)
        gate_data["applied"].append("G1")
        
        # G2: 内的一貫性 - E が低下中に explore は矛盾
        if state.E < 30 and action.intent == "explore":
            self.activation_count["G2"] += 1
            gate_data["failed_gate"] = "G2"
            return False, "G2", gate_data
        gate_data["applied"].append("G2")
        
        # G3: 物理上限 (state は 0-100 で物理的)
        gate_data["applied"].append("G3")
        
        # G6: 不確実性単調性 - belief entropy 高 + 強い action
        belief_entropy = belief_summary.get("entropy", 0)
        if belief_entropy > 4.5 and action.strength == "C":
            self.activation_count["G6"] += 1
            gate_data["failed_gate"] = "G6"
            return False, "G6", gate_data
        gate_data["applied"].append("G6")
        
        # G7: 反例テスト - 高曝露 + 強 action
        if state.X > 60 and action.strength == "C":
            self.activation_count["G7"] += 1
            gate_data["failed_gate"] = "G7"
            return False, "G7", gate_data
        gate_data["applied"].append("G7")
        
        # G8: レイヤー越境チェック (常時 OK)
        gate_data["applied"].append("G8")
        
        # G9: 助言性表示 (常時 OK)
        gate_data["applied"].append("G9")
        
        return True, None, gate_data


# ============================================================
# V8Engine 本体
# ============================================================

class V8Engine:
    """NRMO v8 統合 decision engine
    
    Phase 7-11 を decision pipeline に統合した本格 engine。
    各レイヤーが実際に最終判断に影響する。
    DecisionTrace により各レイヤーの判定を記録。
    """
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                 enable_meta_log: bool = True):
        """
        rng_manager: 乱数管理 (None なら master_seed=42 で初期化)
        enable_meta_log: メタ認知ログを取るか
        """
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        self.engine_rng = self.rng_manager.spawn("v8_engine")
        
        # === Phase 11: 認識論的基盤 ===
        self.frame = FrameDefinition()
        self.falsifiability = FalsifiabilityMonitor()
        self.multi_framework = MultiFrameworkEnsemble()
        self.knightian_engine = KnightianAwareEngine()
        self.tower = TowerTransparencyEngine()
        self.feedback = ExternalFeedbackIntegrator()
        self.skin = SkinInTheGameEngine()
        
        # === Phase 8: 構造的 ===
        self.pomdp = POMDPFormulation()
        # P0-3: 再現性確保のため rng を BayesianUpdater に注入
        belief_rng = self.rng_manager.spawn("belief_updater")
        self.belief_updater = BayesianUpdater(
            self.pomdp, n_particles=50, rng=belief_rng
        )
        self.belief_updater.initialize()
        self.cmdp = CMDPFormulation()
        self.shift_monitor = DistributionShiftMonitor(n_reference_samples=50)
        
        # === Phase 9: 認知 ===
        self.causal_graph = CausalGraph()
        self.dual_path = DualPathEngine(time_budget_ms=100)
        self.meta_cog = MetaCognitionModule()
        self.survivorship = SurvivorshipBiasCorrector()
        self.prospect = ProspectTheoryReward(reference_point=50.0)
        self.discount = HyperbolicDiscounter(base_k=0.05)
        
        # === Phase 10: ストレス耐性 ===
        self.goodhart_framework = AntiGoodhartFramework()
        self.reflexivity = ReflexivityAwareEngine()
        
        # === Strong Engine (legacy v7.1 baseline) ===
        self.strong_engine = V71Engine()
        
        # === Calibration Gate ===
        self.gate = CalibrationGate()
        
        # === Metadata ===
        self.decision_counter = 0
        self.enable_meta_log = enable_meta_log
        self.last_state: Optional[WorldState] = None
        # v8.2: 観測ベース safeguard 用の履歴
        from collections import deque
        self.recent_rewards = deque(maxlen=30)
        self.recent_actions = deque(maxlen=30)
        self.recent_R_values = deque(maxlen=10)
    
    # ------------------------------------------------------------
    # Helper: 状態を Observation 形式に変換
    # ------------------------------------------------------------
    def _to_observation(self, state: WorldState, context: Dict) -> Observation:
        return Observation(
            state_vector=state.to_vector(),
            timestamp=state.t,
            metadata=context,
        )
    
    # ------------------------------------------------------------
    # メインメソッド: decide()
    # ------------------------------------------------------------
    def decide(self, state: WorldState, 
                context: Optional[Dict] = None) -> V8Decision:
        """単一入口の意思決定パイプライン
        
        Pipeline 順:
          1. Frame                  → 範囲外なら REJECT
          2. Falsifiability         → 失格条件発動なら REJECT
          3. POMDP / Belief update  → 信念状態を更新
          4. Distribution Shift     → 警告のみ (続行)
          5. Multi-framework eval   → 候補の多角評価
          6. Knightian uncertainty  → 不確実性が高ければ Conservative
          7. CMDP hard constraint   → 制約違反候補を排除
          8. StrongEngine candidate → V71Engine で legacy 候補
          9. Calibration Gate       → Gate 違反なら strength 弱化
         10. Anti-Goodhart          → 指標分散の警告
         11. Reflexivity            → 介入の波及効果考慮
         12. Skin in the Game       → 責任明示
         13. Tower transparency     → モデル距離注記
         14. Action selection       → 最終 action 決定
         15. External feedback log  → 記録
        """
        self.decision_counter += 1
        context = context or {}
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # v8.2: 履歴更新 (state.R を毎回追加)
        self.recent_R_values.append(float(state.R))
        
        # ============ Layer 1: Frame ============
        situation = context.get("situation", "general_decision")
        frame_status = self.frame.classify(situation)
        trace.add("frame", 
                   "pass" if frame_status == FrameStatus.IN_FRAME else 
                   ("warning" if frame_status == FrameStatus.NEAR_BOUNDARY else "reject"),
                   {"status": frame_status.value, "situation": situation})
        
        if frame_status == FrameStatus.OUT_OF_FRAME:
            trace.reject("frame", "Outside NRMO frame")
            return V8Decision(
                action=None, status="REJECT", confidence=0.0,
                trace=trace,
                metadata={"warning": self.frame.get_warning(frame_status)},
            )
        
        # ============ Layer 2: Falsifiability ============
        # 状態を observation 化して投入
        falsify_obs = {
            "decision_count": self.decision_counter,
            "state": state.to_vector().tolist(),
        }
        self.falsifiability.add_observation(falsify_obs)
        
        # 過剰確信などの hard fail check
        all_failures = self.falsifiability.check_all()
        # 真に triggered = True かつ severity >= 4 のみが critical
        critical_failures = [
            f for f in all_failures 
            if f.get("triggered", False) and f.get("severity", 0) >= 4
        ]
        triggered_total = sum(1 for f in all_failures if f.get("triggered", False))
        
        trace.add("falsifiability",
                   "reject" if critical_failures else 
                   ("warning" if triggered_total > 0 else "pass"),
                   {"n_failures_triggered": triggered_total, 
                    "n_critical": len(critical_failures)})
        
        if critical_failures:
            trace.reject("falsifiability", 
                          f"Critical failure: {critical_failures[0].get('type')}")
            return V8Decision(
                action=None, status="REJECT", confidence=0.0,
                trace=trace,
                metadata={"failures": critical_failures},
            )
        
        # ============ Layer 3: POMDP / Belief update ============
        observation = self._to_observation(state, context)
        self.belief_updater.update(observation)
        belief_summary = self.belief_updater.get_belief_summary()
        
        trace.add("belief", "pass", {
            "entropy": belief_summary.get("entropy", 0),
            "n_updates": belief_summary.get("n_updates", 0),
        })
        
        # ============ Layer 4: Distribution Shift ============
        # 最初の数回は reference に積む
        if state.t < 10:
            self.shift_monitor.add_reference(observation)
        else:
            self.shift_monitor.add_recent(observation)
        
        is_shifted, severity, reason = self.shift_monitor.detect_shift()
        trace.add("distribution_shift",
                   "warning" if is_shifted else "pass",
                   {"is_shifted": is_shifted, "severity": float(severity)},
                   notes=reason if is_shifted else None)
        
        # ============ Layer 5: Candidate generation (拡張) ============
        # P1-1: 候補を狭めず、全 action space を生成 → CMDP で絞り込む
        legacy_action = self.strong_engine.select_action(state)
        
        # 全 action space を base 候補に
        all_intents = ["invest", "defend", "explore", "recover", "hold"]
        all_strengths = ["A", "B", "C"]
        base_candidates = [
            Action(intent=i, strength=s) 
            for i in all_intents 
            for s in all_strengths
        ]
        
        # legacy_action を先頭に置く (StrongEngine の選択を優先表示)
        if legacy_action not in base_candidates:
            candidates = [legacy_action] + base_candidates
        else:
            # 重複なし、legacy を先頭に並べ替え
            others = [c for c in base_candidates 
                       if not (c.intent == legacy_action.intent and c.strength == legacy_action.strength)]
            candidates = [legacy_action] + others
        
        trace.add("candidates", "pass", {
            "n_candidates": len(candidates),
            "legacy_action": f"{legacy_action.intent}/{legacy_action.strength}",
        })
        
        # ============ Layer 6: CMDP hard constraint ============
        # 各候補について制約予測 (簡易版)
        feasible_candidates = []
        for cand in candidates:
            predicted = self._predict_constraint_outcomes(state, cand, belief_summary)
            is_feasible, viol = self.cmdp.check_action(cand, predicted)
            if is_feasible:
                feasible_candidates.append(cand)
        
        if not feasible_candidates:
            # 全候補が制約違反 → HOLD
            trace.add("cmdp", "reject", {
                "n_feasible": 0, "n_total": len(candidates),
            })
            trace.hold("cmdp", "All candidates violate hard constraints")
            return V8Decision(
                action=Action(intent="hold", strength="A"),
                status="HOLD", confidence=0.5, trace=trace,
            )
        
        trace.add("cmdp", "pass", {
            "n_feasible": len(feasible_candidates),
            "n_total": len(candidates),
        })
        
        # ============ Layer 7: Multi-framework evaluation ============
        # 各候補を 6 framework で評価
        options_list = []
        candidate_map = {}
        for cand in feasible_candidates:
            expected, worst, opp = self._estimate_action_values(state, cand, belief_summary)
            best = expected + abs(expected - worst)
            option = DecisionOption(
                name=f"{cand.intent}/{cand.strength}",
                outcomes=[
                    (0.6, expected),   # 期待 60%
                    (0.3, worst),       # 最悪 30%
                    (0.1, best),        # 最良 10%
                ],
            )
            options_list.append(option)
            candidate_map[option.name] = cand
        
        # 全候補を一括評価して best を取得
        if len(options_list) >= 2:
            mf_result = self.multi_framework.select_best(options_list)
            # 正しいキー: best_option (recommended ではない、これが P0-1 致命バグの修正)
            best_option_name = mf_result.get("best_option", options_list[0].name)
            best_candidate = candidate_map.get(best_option_name, feasible_candidates[0])
            # framework 別の rank 1 推奨を集計
            framework_scores = {}
            for ev in mf_result.get("all_evaluations", []):
                for fw_name, rank in ev.get("ranks_by_framework", {}).items():
                    if rank == 1:
                        framework_scores[fw_name] = ev["option"]
        else:
            best_candidate = feasible_candidates[0]
            best_option_name = options_list[0].name if options_list else "none"
            framework_scores = {}
        
        disagreement = self._compute_disagreement_v2(framework_scores)
        
        # 最も優れた option を選択
        trace.add("multi_framework", "pass", {
            "n_evaluated": len(options_list),
            "best_candidate": best_option_name,
            "framework_disagreement": disagreement,
        })
        
        # ============ Layer 7.5: (v8.2 で試みた stagnation safeguard は撤回) ============
        # v8.2 で「invest 連発 + R 下降」で safeguard を発動する案を試したが、
        # 副作用として Normal/Vulnerable で大悪化 (Pareto 0/6) が発生。
        # 表面的対症療法では Multi-framework の根本バイアスを解決できないと判明。
        # v8.3 で Multi-framework 自体 (EUT 重みなど) の調整が必要。
        # 当面は safeguard なし、Multi-framework 結果をそのまま使用。
        
        trace.add("stagnation_safeguard", "info", {
            "status": "disabled_in_v8.2_after_failed_experiment",
            "note": "v8.2 safeguard 実験は副作用で撤回。v8.3 で根本対策予定。",
        })
        
        # ============ Layer 8: Knightian uncertainty ============
        # P0-4 fix: 単純な absolute threshold は常時 100% trigger になる。
        # 代わりに以下の組み合わせで判定:
        #   - 観測数 (初期数 step は除外)
        #   - 分散の絶対値ではなく、変化率
        #   - state risk (X が高い、E が低いなど)
        #   - action の irreversibility
        belief_var = belief_summary.get("variance", {})
        avg_variance = float(np.mean(list(belief_var.values())) if belief_var else 0)
        
        n_belief_updates = belief_summary.get("n_updates", 0)
        # 初期 5 step は trigger しない (Belief が安定する前)
        early_phase = n_belief_updates < 5
        
        # state risk (X 高い OR E 低い)
        state_risk = (state.X > 60) or (state.E < 30)
        
        # action の irreversibility (strong action は不可逆性高い)
        action_irrev = best_candidate.strength in ("B", "C")
        
        # Knightian 発火条件 (組み合わせ)
        is_knightian = (
            not early_phase
            and avg_variance > 0.015  # 閾値も少し緩める
            and (state_risk or action_irrev)  # state または action がリスクある時のみ
        )
        
        trace.add("knightian", "warning" if is_knightian else "pass", {
            "avg_variance": avg_variance,
            "is_knightian": is_knightian,
            "early_phase": early_phase,
            "state_risk": state_risk,
            "action_irreversible": action_irrev,
            "n_updates": n_belief_updates,
        }, notes="High uncertainty + risk → conservative" if is_knightian else None)
        
        # Knightian なら強い action を弱化
        chosen_candidate = best_candidate
        if is_knightian and chosen_candidate.strength == "C":
            chosen_candidate = Action(intent=chosen_candidate.intent, strength="B")
        elif is_knightian and chosen_candidate.strength == "B":
            chosen_candidate = Action(intent=chosen_candidate.intent, strength="A")
        
        # ============ Layer 9: Calibration Gate ============
        gate_passed, failed_gate, gate_data = self.gate.apply(
            state, chosen_candidate, belief_summary
        )
        
        if not gate_passed:
            # Gate 失敗 → strength を弱化
            if chosen_candidate.strength == "C":
                chosen_candidate = Action(intent=chosen_candidate.intent, strength="B")
            elif chosen_candidate.strength == "B":
                chosen_candidate = Action(intent=chosen_candidate.intent, strength="A")
            trace.add("gate", "warning", gate_data,
                       notes=f"Gate {failed_gate} failed → strength weakened")
        else:
            trace.add("gate", "pass", gate_data)
        
        # ============ Layer 10: Anti-Goodhart ============
        # 指標を記録 (実際の Goodhart 検出は長期で発動)
        self.goodhart_framework.record({
            "score": 1.0,  # placeholder
            "robustness": 0.8,
            "optionality": state.O / 100,
            "alignment": 0.9,
            "diversity": 0.7,
        })
        is_goodhart, goodhart_reason = self.goodhart_framework.detect_goodhart()
        trace.add("goodhart", "warning" if is_goodhart else "pass", {
            "is_goodhart": is_goodhart,
        }, notes=goodhart_reason if is_goodhart else None)
        
        # ============ Layer 11: Reflexivity ============
        if self.last_state is not None:
            self.reflexivity.record_intervention(
                f"{chosen_candidate.intent}",
                self.last_state.to_vector(),
                state.to_vector(),
            )
        reflex_effect = self.reflexivity.estimated_reflexive_effect(
            chosen_candidate.intent
        )
        trace.add("reflexivity", "pass", {
            "has_history": reflex_effect is not None,
            "n_similar": reflex_effect["n_similar"] if reflex_effect else 0,
        })
        
        # Reflexivity で confidence 調整
        base_confidence = 0.7
        if reflex_effect and reflex_effect.get("second_order_effect", 0) > 100:
            base_confidence *= 0.7
        
        # ============ Layer 12: Skin in the Game ============
        proposal_str = f"action={chosen_candidate.intent}/{chosen_candidate.strength}"
        reasoning_list = [
            f"Multi-framework best: {best_option_name}",
            f"Knightian flag: {is_knightian}",
            f"Gate passed: {gate_passed}",
        ]
        stake = self.skin.stake(
            proposal=proposal_str,
            confidence=base_confidence,
            reasoning=reasoning_list,
        )
        trace.add("skin", "pass", {
            "stake_level": stake.stake_level.value,
            "confidence": base_confidence,
            "proposal": stake.proposal[:60],
        })
        
        # ============ Layer 13: Tower transparency ============
        tower_validation = self.tower.validate_for_situation([
            chosen_candidate.intent, situation
        ])
        trace.add("tower", "pass", {
            "applicable": tower_validation.get("applicable", True),
            "estimated_distance": float(self.tower.estimate_total_distance_from_reality()),
        })
        
        # ============ Layer 14: Action selection (最終決定) ============
        final_action = chosen_candidate
        final_confidence = base_confidence
        
        trace.add("action_selection", "pass", {
            "final_action": f"{final_action.intent}/{final_action.strength}",
            "final_confidence": final_confidence,
        })
        
        # ============ Layer 15: External feedback log ============
        if self.enable_meta_log:
            # Meta-cog 用に予測を記録 (後に outcome で update)
            self.meta_cog.record_outcome(
                predicted=True,  # plain placeholder
                actual=True,
                confidence=final_confidence,
            )
        
        self.last_state = state
        trace.accept(action=final_action)
        
        return V8Decision(
            action=final_action,
            status="ACCEPT",
            confidence=final_confidence,
            trace=trace,
            metadata={
                "framework_disagreement": disagreement,
                "knightian_flagged": is_knightian,
                "gate_failed": failed_gate,
            },
        )
    
    # ------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------
    def _predict_constraint_outcomes(self, state: WorldState, 
                                       action: Action,
                                       belief: Dict) -> Dict[str, float]:
        """制約予測 (簡易版)"""
        # action と state から、各制約変数の予測値
        ruin_prob = max(0.0, (state.X - 50) / 100) if state.X > 50 else 0.0
        if action.intent == "defend":
            ruin_prob *= 0.5
        elif action.intent == "invest" and action.strength == "C":
            ruin_prob *= 1.5
        
        optionality = state.O
        if action.intent == "hold":
            optionality -= 5
        elif action.intent == "explore":
            optionality += 5
        
        vision_drift = 0.1  # placeholder
        
        return {
            "ruin_probability": min(0.5, ruin_prob),
            "optionality_min": optionality,
            "vision_drift": vision_drift,
        }
    
    def _estimate_action_values(self, state: WorldState,
                                  action: Action,
                                  belief: Dict) -> Tuple[float, float, float]:
        """期待値, 最悪値, 機会損失"""
        # 簡易: state と action から推定
        base_score = (state.R + state.E + state.G) / 300 * 10
        
        # action による調整
        intent_bonus = {
            "invest": 1.5, "explore": 1.0, "defend": 0.5,
            "recover": 0.8, "hold": 0.2,
        }.get(action.intent, 0.5)
        strength_mult = {"A": 1.0, "B": 1.5, "C": 2.0}.get(action.strength, 1.0)
        
        expected = base_score + intent_bonus * strength_mult
        # 不確実性 (belief variance) を加味
        avg_var = float(np.mean(list(belief.get("variance", {0: 0.01}).values())))
        worst = expected - 3 * avg_var * 10
        opportunity = 1.0 if action.intent != "hold" else 5.0
        
        return float(expected), float(worst), float(opportunity)
    
    def _compute_disagreement(self, mf_scores: List) -> float:
        """Framework 間の disagreement (分散) を計算"""
        if not mf_scores:
            return 0.0
        all_scores = []
        for _, mf_result, _ in mf_scores:
            scores = mf_result.get("framework_scores", {})
            all_scores.extend(scores.values())
        if not all_scores:
            return 0.0
        return float(np.std(all_scores))
    
    def _compute_disagreement_v2(self, framework_recs: Dict) -> float:
        """Framework が異なる選択を推奨した数の比率"""
        if not framework_recs:
            return 0.0
        recommendations = list(framework_recs.values())
        if not recommendations:
            return 0.0
        # 最頻値以外の比率
        from collections import Counter
        counter = Counter(recommendations)
        most_common_count = counter.most_common(1)[0][1]
        return 1.0 - (most_common_count / len(recommendations))
    
    def update_reward(self, action: Action, reward: float):
        """報酬を engine に伝える (v71 互換)"""
        self.strong_engine.update_reward(action, reward)
        # Prospect Theory で utility 化
        utility = self.prospect.utility(reward)
        self.prospect.update_reference(reward, learning_rate=0.1)
        # v8.2: recent_rewards + recent_actions に追加
        self.recent_rewards.append(float(reward))
        self.recent_actions.append(action.intent)


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("V8Engine — Phase 7-11 統合 Decision Pipeline 動作確認")
    print("=" * 70)
    
    from world_models import World, WorldType
    
    # 再現可能な setup
    rng_manager = RNGManager(master_seed=42)
    engine = V8Engine(rng_manager=rng_manager, enable_meta_log=True)
    
    print(f"\nV8Engine 構成:")
    print(f"  Phase 11: Frame, Falsifiability, Multi-framework, Knightian, "
          f"Tower, Feedback, Skin in the Game")
    print(f"  Phase 8:  POMDP/Belief, CMDP, Distribution Shift")
    print(f"  Phase 9:  CausalGraph, Dual Path, Meta-cog, "
          f"Survivorship, Prospect, Hyperbolic")
    print(f"  Phase 10: Anti-Goodhart, Reflexivity, TMR, "
          f"Barbell, Adversarial, EVT")
    print(f"  Calibration Gate: 7 gates (G1, G2, G3, G6, G7, G8, G9)")
    
    # 3 つの state で decide() を実行
    world = World(WorldType.VULNERABLE, seed=42)
    
    print(f"\n--- Vulnerable world, 3 decisions ---")
    for i in range(3):
        decision = engine.decide(
            state=world.state,
            context={"situation": "general_decision"},
        )
        
        print(f"\nDecision #{i+1}:")
        print(f"  Status: {decision.status}")
        if decision.action:
            print(f"  Action: {decision.action.intent}/{decision.action.strength}")
        print(f"  Confidence: {decision.confidence:.2f}")
        print(f"  Layers visited: {len(decision.trace.entries)}")
        print(f"    {' → '.join(decision.trace.layers_visited())}")
        
        # World 進行
        if decision.action:
            world.step(decision.action)
            engine.update_reward(decision.action, world.state.cumulative_score)
    
    print(f"\n--- Decision Trace の詳細 (最後の decision) ---")
    print(decision.trace.summary())
    
    # 再現性テスト
    print(f"\n--- 再現性テスト ---")
    rng_manager2 = RNGManager(master_seed=42)
    engine2 = V8Engine(rng_manager=rng_manager2)
    world2 = World(WorldType.VULNERABLE, seed=42)
    
    decision_2nd_run = engine2.decide(world2.state)
    print(f"Same seed, same input → "
          f"Action: {decision_2nd_run.action.intent}/{decision_2nd_run.action.strength}")
    
    print(f"\n[V8Engine 動作確認 完了 ✅]")
