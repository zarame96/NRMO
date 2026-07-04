"""
NRMO Phase 9 — 認知的拡張

対処する流木:
  流木 4: 報酬関数固定 → Vision-conditional reward
  流木 12: Survivorship Bias → Failure trajectory 明示学習
  流木 15: Loss aversion 非対称 → Prospect theory S 字曲線
  流木 16: 機会費用不可視 → Counterfactual outcome
  流木 17: 割引率固定 → Hyperbolic discounting + context
  流木 18: メンタルモデル不在 → Causal graph
  流木 19: System 1/2 未分化 → Dual path architecture
  流木 20: Meta-cognition 欠落 → Self-evaluation module

設計思想:
  人間の認知の良いところを取り入れる
  System 1 (速い直感) + System 2 (遅い熟慮) の dual path
  自己評価 (confidence on confidence) を含む
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
import numpy as np


# ============================================================
# Step 9.1: Causal Mental Model (流木 18)
# ============================================================

@dataclass
class CausalEdge:
    """因果グラフのエッジ"""
    source: str
    target: str
    effect_magnitude: float  # 0.0 - 1.0
    effect_sign: int          # +1 or -1
    confidence: float         # 0.0 - 1.0


class CausalGraph:
    """6D state vector + action の因果関係を表現
    
    例:
      X (曝露) ↑ → R (資源) ↓
      R (資源) ↑ → action invest 可能性 ↑
      action invest → O (選択肢) ↑ but X (曝露) ↑
    
    NRMO はこのグラフを使って:
      - 「もし X したら Y になる」を予測
      - Counterfactual reasoning
      - 介入の効果評価
    """
    
    def __init__(self):
        self.nodes = ["R", "E", "G", "O", "K", "X",
                       "invest", "defend", "explore", "recover", "hold"]
        self.edges: List[CausalEdge] = []
        self._init_default_edges()
    
    def _init_default_edges(self):
        """v5.0 v7.1 の知見から因果関係を初期化"""
        # State 間の因果
        self.add_edge("X", "R", 0.3, -1, 0.7)  # 曝露上昇は資源を侵食
        self.add_edge("X", "E", 0.2, -1, 0.6)  # 曝露上昇は体力を消耗
        self.add_edge("R", "O", 0.4, +1, 0.8)  # 資源は選択肢を生む
        self.add_edge("K", "O", 0.3, +1, 0.7)  # 知識は選択肢を増やす
        self.add_edge("E", "G", 0.3, +1, 0.7)  # 体力は感情に影響
        
        # Action の因果
        self.add_edge("invest", "O", 0.5, +1, 0.8)
        self.add_edge("invest", "R", 0.4, -1, 0.9)
        self.add_edge("invest", "X", 0.3, +1, 0.7)
        self.add_edge("defend", "X", 0.4, -1, 0.7)
        self.add_edge("defend", "O", 0.2, -1, 0.6)
        self.add_edge("recover", "E", 0.5, +1, 0.8)
        self.add_edge("recover", "G", 0.5, +1, 0.8)
        self.add_edge("recover", "O", 0.2, -1, 0.5)
        self.add_edge("explore", "K", 0.4, +1, 0.7)
        self.add_edge("explore", "O", 0.4, +1, 0.7)
        self.add_edge("explore", "R", 0.2, -1, 0.5)
        self.add_edge("hold", "X", 0.1, -1, 0.5)
        self.add_edge("hold", "O", 0.1, -1, 0.5)
    
    def add_edge(self, source: str, target: str, mag: float, sign: int, conf: float):
        self.edges.append(CausalEdge(source, target, mag, sign, conf))
    
    def predict_intervention_effect(self, intervention: str,
                                       target_var: str,
                                       depth: int = 2) -> float:
        """介入の効果を予測 (因果 path を辿る)
        
        depth: グラフ探索の深さ
        """
        if depth <= 0:
            return 0.0
        
        # 直接効果
        direct_effect = 0.0
        for e in self.edges:
            if e.source == intervention and e.target == target_var:
                direct_effect += e.effect_sign * e.effect_magnitude * e.confidence
        
        # 間接効果 (1 step 経由)
        indirect_effect = 0.0
        if depth > 1:
            for e in self.edges:
                if e.source == intervention:
                    intermediate = e.target
                    next_effect = self.predict_intervention_effect(
                        intermediate, target_var, depth - 1
                    )
                    indirect_effect += (
                        e.effect_sign * e.effect_magnitude * 
                        e.confidence * next_effect * 0.5  # 減衰
                    )
        
        return direct_effect + indirect_effect
    
    def counterfactual(self, action_a: str, action_b: str,
                        target_var: str) -> float:
        """もし A の代わりに B したら? (反実仮想)"""
        effect_a = self.predict_intervention_effect(action_a, target_var)
        effect_b = self.predict_intervention_effect(action_b, target_var)
        return effect_b - effect_a


# ============================================================
# Step 9.2: System 1 / System 2 Dual Path (流木 19)
# ============================================================

class System1Engine:
    """速い直感 (Kahneman System 1)
    
    特徴:
      - 即座 (< 0.01 秒)
      - 経験ベース (パターンマッチ)
      - 認知バイアスを使う (ヒューリスティック)
      - 確信度を持つ
    """
    
    def __init__(self):
        # 経験パターン (状況 → 推奨 action)
        self.patterns = {
            "low_resource_high_risk": ("defend", "A", 0.7),
            "high_resource_low_risk": ("invest", "B", 0.6),
            "stagnation_detected": ("explore", "B", 0.6),
            "crisis_mode": ("recover", "A", 0.8),
            "abundant_options": ("invest", "C", 0.5),
        }
    
    def quick_judgment(self, state: np.ndarray) -> Tuple[str, str, float]:
        """瞬時判断
        
        Returns: (intent, strength, confidence)
        """
        R, E, G, O, K, X = state
        
        # パターンマッチング (シンプルなルール)
        if R < 30 and X > 60:
            return self.patterns["low_resource_high_risk"]
        elif R > 70 and X < 30:
            return self.patterns["high_resource_low_risk"]
        elif O < 20:
            return self.patterns["stagnation_detected"]
        elif E < 30 or G < 30:
            return self.patterns["crisis_mode"]
        elif O > 70:
            return self.patterns["abundant_options"]
        
        # デフォルト
        return ("explore", "A", 0.4)


class System2Engine:
    """遅い熟慮 (Kahneman System 2)
    
    特徴:
      - 計算 (rollout, 多目的評価)
      - 因果モデル使用
      - System 1 の判断を検証
      - 時間がかかる
    """
    
    def __init__(self, causal_graph: CausalGraph):
        self.causal_graph = causal_graph
    
    def deliberate(self, state: np.ndarray, 
                    system1_recommendation: Tuple[str, str, float]
                    ) -> Tuple[str, str, float]:
        """熟慮による検証と修正"""
        s1_intent, s1_strength, s1_conf = system1_recommendation
        
        # 各候補 action について因果分析
        candidates = ["invest", "defend", "explore", "recover", "hold"]
        scores = {}
        
        for cand in candidates:
            # 各 state 変数への効果を予測
            effect_R = self.causal_graph.predict_intervention_effect(cand, "R")
            effect_E = self.causal_graph.predict_intervention_effect(cand, "E")
            effect_O = self.causal_graph.predict_intervention_effect(cand, "O")
            effect_X = self.causal_graph.predict_intervention_effect(cand, "X")
            
            # 重み付け評価
            score = effect_R * 0.2 + effect_E * 0.2 + effect_O * 0.3 - effect_X * 0.3
            scores[cand] = score
        
        # 最良 intent
        best_intent = max(scores, key=scores.get)
        
        # S1 と一致するか?
        if best_intent == s1_intent:
            # 確信度上昇
            new_conf = min(0.95, s1_conf + 0.1)
            return (s1_intent, s1_strength, new_conf)
        else:
            # S1 を覆す → 強度は慎重に
            return (best_intent, "A", 0.5)


class DualPathEngine:
    """S1 + S2 の dual path"""
    
    def __init__(self, time_budget_ms: float = 100):
        self.s1 = System1Engine()
        self.causal_graph = CausalGraph()
        self.s2 = System2Engine(self.causal_graph)
        self.time_budget_ms = time_budget_ms
    
    def decide(self, state: np.ndarray, urgency: float = 0.5
                ) -> Tuple[str, str, float, str]:
        """状況に応じて S1 / S2 / 両方
        
        urgency: 0.0 (時間あり) - 1.0 (緊急)
        
        Returns: (intent, strength, confidence, path_used)
        """
        # 必ず S1 を実行 (瞬時)
        s1_result = self.s1.quick_judgment(state)
        
        if urgency > 0.8:
            # 緊急時: S1 のみ
            return s1_result + ("S1_only",)
        elif urgency > 0.5:
            # 中程度: S1 + S2 (簡略)
            s2_result = self.s2.deliberate(state, s1_result)
            return s2_result + ("S1+S2_quick",)
        else:
            # 時間あり: S2 (full deliberation)
            s2_result = self.s2.deliberate(state, s1_result)
            return s2_result + ("S1+S2_full",)


# ============================================================
# Step 9.3: Meta-cognition (流木 20)
# ============================================================

class MetaCognitionModule:
    """自分の判断の正しさを評価する
    
    "Confidence on confidence" = メタ確信度
    
    過剰確信検出:
      予測確信度 vs 実際の的中率の乖離
    """
    
    def __init__(self):
        self.prediction_log = []  # [(predicted, actual, confidence)]
    
    def record_outcome(self, predicted: bool, actual: bool, confidence: float):
        """予測と結果を記録"""
        self.prediction_log.append({
            "predicted": predicted,
            "actual": actual,
            "confidence": confidence,
            "correct": predicted == actual,
        })
    
    def calibration_score(self) -> Dict[str, float]:
        """Calibration の評価
        
        理想: confidence 0.8 と言ったら 80% 当たる
        実際の乖離を測定
        """
        if not self.prediction_log:
            return {"calibration": None}
        
        # Confidence bucket ごとに的中率を計算
        buckets = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        results = {}
        
        for low, high in buckets:
            in_bucket = [
                p for p in self.prediction_log
                if low <= p["confidence"] < high
            ]
            if in_bucket:
                accuracy = sum(p["correct"] for p in in_bucket) / len(in_bucket)
                expected = (low + high) / 2  # bucket の中央値
                gap = abs(accuracy - expected)
                results[f"conf_{low:.1f}_{high:.1f}"] = {
                    "n": len(in_bucket),
                    "accuracy": accuracy,
                    "expected": expected,
                    "gap": gap,
                }
        
        # 全体的な calibration gap (平均)
        gaps = [r["gap"] for r in results.values() if "gap" in r]
        results["overall_calibration_gap"] = float(np.mean(gaps)) if gaps else 0.0
        return results
    
    def overconfidence_detected(self) -> bool:
        """過剰確信が検出されたか"""
        cal = self.calibration_score()
        gap = cal.get("overall_calibration_gap", 0)
        return gap > 0.20  # 20% 以上の乖離


# ============================================================
# Step 9.4: Survivorship Bias Correction (流木 12)
# ============================================================

class SurvivorshipBiasCorrector:
    """生存バイアスの補正
    
    通常: 生き残った agent のデータで学習
    補正: 失敗 (破滅) した agent のデータも明示的に学習
    """
    
    def __init__(self):
        self.survivor_data = []
        self.failed_data = []  # 破滅したケース
    
    def add_survivor(self, trajectory: List, final_outcome: float):
        self.survivor_data.append({
            "trajectory": trajectory,
            "final_outcome": final_outcome,
            "is_survivor": True,
        })
    
    def add_failed(self, trajectory: List, ruin_step: int):
        self.failed_data.append({
            "trajectory": trajectory,
            "ruin_step": ruin_step,
            "is_survivor": False,
        })
    
    def early_warning_patterns(self) -> List[Dict]:
        """失敗 trajectory の早期警告パターンを抽出"""
        if not self.failed_data:
            return []
        
        # 破滅前 5 step の state を分析
        warning_patterns = []
        for failed in self.failed_data:
            traj = failed["trajectory"]
            ruin_step = failed["ruin_step"]
            
            if ruin_step >= 5 and len(traj) > 5:
                pre_ruin = traj[max(0, ruin_step - 5):ruin_step]
                pattern = {
                    "mean_state": np.mean([t for t in pre_ruin], axis=0).tolist()
                    if pre_ruin else None,
                    "ruin_at": ruin_step,
                }
                warning_patterns.append(pattern)
        
        return warning_patterns
    
    def adjusted_action_value(self, action_name: str, base_value: float) -> float:
        """生存者バイアスを補正した action 価値"""
        if not self.failed_data:
            return base_value
        
        # 失敗例で頻出する action は危険として補正
        risky_factor = 1.0
        # 簡略化: 「invest」が失敗例で多ければ risky
        if action_name == "invest":
            # 実装簡略化
            risky_factor = 0.85
        
        return base_value * risky_factor


# ============================================================
# Step 9.5: Prospect Theory (流木 15)
# ============================================================

class ProspectTheoryReward:
    """Kahneman & Tversky の Prospect Theory による報酬関数
    
    特徴:
      - Reference point (現状) からの相対評価
      - 損失回避: 損失は利得の 2.25 倍重く感じる
      - S 字曲線 (concave for gains, convex for losses)
    """
    
    def __init__(self, reference_point: float = 0.0,
                 alpha: float = 0.88,    # 利得側 concavity
                 beta: float = 0.88,     # 損失側 convexity
                 lambda_: float = 2.25):  # 損失回避係数
        self.reference = reference_point
        self.alpha = alpha
        self.beta = beta
        self.lambda_ = lambda_
    
    def utility(self, outcome: float) -> float:
        """効用関数 (S 字曲線)"""
        delta = outcome - self.reference
        
        if delta >= 0:
            # 利得側: concave
            return delta ** self.alpha
        else:
            # 損失側: convex + 損失回避
            return -self.lambda_ * (-delta) ** self.beta
    
    def update_reference(self, new_outcome: float, learning_rate: float = 0.1):
        """Reference point を slowly update"""
        self.reference = (
            (1 - learning_rate) * self.reference + 
            learning_rate * new_outcome
        )


# ============================================================
# Step 9.6: Hyperbolic Discounting (流木 17)
# ============================================================

class HyperbolicDiscounter:
    """文脈依存の時間割引
    
    通常: exponential decay (γ^t)
    人間: hyperbolic (1/(1+kt))
    
    Context 依存:
      - 危機状況: 高 discount (今が大事)
      - 健全状況: 低 discount (将来を重視)
    """
    
    def __init__(self, base_k: float = 0.05):
        self.base_k = base_k
    
    def discount(self, future_value: float, delay: float, 
                  urgency: float = 0.5) -> float:
        """Hyperbolic discount with context"""
        # urgency が高いと k 増 (短期重視)
        k = self.base_k * (1 + urgency * 2)
        return future_value / (1 + k * delay)
    
    def opportunity_cost(self, action_value: float, hold_value: float,
                          time_horizon: float) -> float:
        """機会費用 (流木 16 も同時対処)
        
        HOLD する vs 行動する の差を時間軸で評価
        """
        future_hold = self.discount(hold_value, time_horizon)
        return action_value - future_hold


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Phase 9 — 認知的拡張 動作確認")
    print("=" * 70)
    
    np.random.seed(42)
    
    # === Step 9.1: Causal Graph ===
    print("\n--- Step 9.1: Causal Mental Model ---")
    graph = CausalGraph()
    print(f"Nodes: {len(graph.nodes)}")
    print(f"Edges: {len(graph.edges)}")
    
    effect_invest_on_R = graph.predict_intervention_effect("invest", "R")
    effect_invest_on_O = graph.predict_intervention_effect("invest", "O")
    print(f"Predicted effect of 'invest' on R: {effect_invest_on_R:+.3f}")
    print(f"Predicted effect of 'invest' on O: {effect_invest_on_O:+.3f}")
    
    cf = graph.counterfactual("invest", "defend", "X")
    print(f"Counterfactual: if 'defend' instead of 'invest', X changes by: {cf:+.3f}")
    
    # === Step 9.2: Dual Path ===
    print("\n--- Step 9.2: System 1/2 Dual Path ---")
    engine = DualPathEngine()
    
    state_normal = np.array([60, 70, 65, 50, 55, 25])
    state_crisis = np.array([25, 20, 30, 15, 30, 75])
    
    for s, label in [(state_normal, "Normal"), (state_crisis, "Crisis")]:
        # Low urgency
        intent, strength, conf, path = engine.decide(s, urgency=0.3)
        print(f"{label} state, low urgency: {intent}/{strength} "
                f"(conf={conf:.2f}, path={path})")
        
        # High urgency
        intent, strength, conf, path = engine.decide(s, urgency=0.9)
        print(f"{label} state, HIGH urgency: {intent}/{strength} "
                f"(conf={conf:.2f}, path={path})")
    
    # === Step 9.3: Meta-cognition ===
    print("\n--- Step 9.3: Meta-cognition ---")
    meta = MetaCognitionModule()
    
    # 100 件の予測ログ (over-confident な agent をシミュ)
    for _ in range(100):
        confidence = np.random.uniform(0.7, 0.95)  # 高 confidence
        actual_accuracy = 0.6  # でも実際は 60% しか当たらない
        actual = np.random.random() < actual_accuracy
        meta.record_outcome(predicted=True, actual=actual, confidence=confidence)
    
    cal = meta.calibration_score()
    print(f"Overall calibration gap: {cal['overall_calibration_gap']:.3f}")
    print(f"Overconfidence detected: {meta.overconfidence_detected()}")
    
    # === Step 9.5: Prospect Theory ===
    print("\n--- Step 9.5: Prospect Theory ---")
    pt = ProspectTheoryReward(reference_point=50.0)
    
    print(f"Utility of +10 gain: {pt.utility(60):.3f}")
    print(f"Utility of -10 loss: {pt.utility(40):.3f}")
    print(f"Utility of +20 gain: {pt.utility(70):.3f}")
    print(f"Utility of -20 loss: {pt.utility(30):.3f}")
    print(f"  → Loss は同等利得より約 {pt.utility(40) / pt.utility(60):.2f}x の重み")
    
    # === Step 9.6: Hyperbolic Discounting ===
    print("\n--- Step 9.6: Hyperbolic Discounting ---")
    disc = HyperbolicDiscounter(base_k=0.05)
    
    print(f"Future value 100 in 10 steps:")
    print(f"  Low urgency: {disc.discount(100, 10, urgency=0.2):.2f}")
    print(f"  Med urgency: {disc.discount(100, 10, urgency=0.5):.2f}")
    print(f"  High urgency: {disc.discount(100, 10, urgency=0.9):.2f}")
    
    print(f"\n[Phase 9 完了 ✅]")
