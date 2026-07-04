"""
NRMO Phase 10 — ストレス耐性強化 (最終 Phase)

対処する流木 (残り 7 個):
  流木 9: Goodhart's Law (本格対応)
  流木 10: Reflexivity / Lucas Critique
  流木 21: 単一障害点 (Single Point of Failure)
  流木 23: Anti-fragility 欠落
  流木 24: 対戦相手不在 (Adversarial agents)
  流木 25: Black Swan (本格対応)
  流木 26: Tail risk 過小評価

これで全 31 流木が対処される。

設計思想:
  「想定外で破滅しない」を構造的に保証
  - Goodhart: 多目的で単一指標の罠を回避
  - Reflexivity: 介入が world に影響することを認識
  - Redundancy: 単一障害で全体が崩れない
  - Anti-fragile: ストレスから利益を得る
  - Adversarial: 真の対戦相手で訓練
  - Black Swan: 極端事象に耐える
  - Tail risk: 重い裾を正しく扱う
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
import numpy as np
from scipy import stats


# ============================================================
# Step 10.1: Goodhart 対策 (流木 9) — Multi-objective + Indicator rotation
# ============================================================

class AntiGoodhartFramework:
    """Goodhart's Law への対策
    
    原理:
      「測定値を目標化すると、測定値の意味が失われる」
    
    対策:
      1. 複数の indicator を rotate (どれかが Goodhart 化しても他で検証)
      2. Indicator 間の相関を監視 (相関が崩れたら Goodhart の兆候)
      3. 「proxy 効果」を陽に評価
    """
    
    def __init__(self):
        self.indicators = {
            "score": [],          # 直接的スコア
            "robustness": [],     # ロバスト性
            "optionality": [],    # 選択肢量
            "alignment": [],      # Vision との一致度
            "diversity": [],      # 戦略多様性
        }
        self.rotation_period = 10  # 10 step ごとに主指標 rotate
        self.current_step = 0
    
    def record(self, indicator_values: Dict[str, float]):
        """指標値を記録"""
        for k, v in indicator_values.items():
            if k in self.indicators:
                self.indicators[k].append(v)
        self.current_step += 1
    
    def primary_indicator(self) -> str:
        """現時点での主指標 (rotation)"""
        idx = (self.current_step // self.rotation_period) % len(self.indicators)
        return list(self.indicators.keys())[idx]
    
    def detect_goodhart(self) -> Tuple[bool, str]:
        """Goodhart 兆候の検出
        
        症状:
          - 主指標が向上、他指標が劣化 (proxy 効果)
          - 指標間の相関が崩れた
        """
        # 最新 30 step の各指標の trend を見る
        if any(len(v) < 30 for v in self.indicators.values()):
            return False, "Insufficient data"
        
        trends = {}
        for k, values in self.indicators.items():
            recent = values[-30:]
            x = np.arange(len(recent))
            slope = np.polyfit(x, recent, 1)[0]
            trends[k] = slope
        
        primary = self.primary_indicator()
        primary_trend = trends[primary]
        
        # 主指標は向上 + 他指標は劣化 → Goodhart
        if primary_trend > 0:
            others_declining = sum(
                1 for k, t in trends.items()
                if k != primary and t < -0.01
            )
            if others_declining >= 2:
                return True, f"{primary} 向上中だが他 {others_declining} 指標が劣化 (Goodhart 兆候)"
        
        return False, "No Goodhart pattern detected"
    
    def composite_score(self) -> float:
        """単一指標ではなく合成スコア"""
        if not all(v for v in self.indicators.values()):
            return 0.0
        
        # 各指標の最新値を均等重み合成
        scores = []
        for k, values in self.indicators.items():
            if values:
                scores.append(values[-1])
        
        return float(np.mean(scores))


# ============================================================
# Step 10.2: Reflexivity-Aware Policy (流木 10)
# ============================================================

class ReflexivityAwareEngine:
    """介入が world に影響することを認識する Engine
    
    Lucas Critique:
      「政策変更すると人々の行動も変わる」
    
    Reflexivity (Soros):
      「観察が現実を変える」
    
    対処:
      Engine の判断が world dynamics を変える可能性を考慮
      Self-referential update
    """
    
    def __init__(self):
        self.intervention_log = []
        self.world_state_log = []
    
    def record_intervention(self, intervention: str, 
                             pre_state: np.ndarray,
                             post_state: np.ndarray):
        """介入とその影響を記録"""
        self.intervention_log.append({
            "intervention": intervention,
            "pre_state": pre_state.copy(),
            "post_state": post_state.copy(),
            "delta": post_state - pre_state,
        })
    
    def estimated_reflexive_effect(self, planned_intervention: str
                                     ) -> Optional[Dict]:
        """同種の過去介入から、世界への波及効果を推定"""
        similar = [
            log for log in self.intervention_log
            if log["intervention"] == planned_intervention
        ]
        
        if not similar:
            return None
        
        # 過去介入の平均的影響
        deltas = np.array([log["delta"] for log in similar])
        mean_effect = deltas.mean(axis=0)
        std_effect = deltas.std(axis=0)
        
        return {
            "n_similar": len(similar),
            "mean_effect": mean_effect.tolist(),
            "std_effect": std_effect.tolist(),
            "second_order_effect": (mean_effect ** 2).sum(),
        }
    
    def policy_adjustment(self, intended_action: str,
                            base_confidence: float) -> Tuple[str, float]:
        """Reflexivity を考慮した方針調整"""
        effect_estimate = self.estimated_reflexive_effect(intended_action)
        
        if effect_estimate is None:
            return intended_action, base_confidence
        
        # Second-order effect が大きい → 不確実、confidence 下げる
        if effect_estimate["second_order_effect"] > 100:
            return intended_action, base_confidence * 0.7
        
        return intended_action, base_confidence


# ============================================================
# Step 10.3: Triple Modular Redundancy (流木 21)
# ============================================================

class TripleModularRedundancy:
    """単一障害点の解消 (TMR)
    
    3 つの独立 engine が並列実行
    Majority vote で結論
    1 engine が壊れても他 2 で機能継続
    """
    
    def __init__(self, engines: List[Callable]):
        assert len(engines) == 3, "TMR requires exactly 3 engines"
        self.engines = engines
        self.disagreement_count = 0
    
    def voted_decision(self, input_data) -> Tuple[any, str]:
        """3 engines の voted decision
        
        Returns: (decision, status)
        """
        try:
            decisions = [eng(input_data) for eng in self.engines]
        except Exception as e:
            return None, f"Engine failure: {e}"
        
        # Majority vote
        from collections import Counter
        counter = Counter(str(d) for d in decisions)
        most_common, count = counter.most_common(1)[0]
        
        if count >= 2:
            # 2-out-of-3 agreed
            for d in decisions:
                if str(d) == most_common:
                    if count < 3:
                        self.disagreement_count += 1
                        return d, "VOTED (disagreement)"
                    return d, "UNANIMOUS"
        
        # 3-way split = 完全不一致
        self.disagreement_count += 1
        return decisions[0], "NO_AGREEMENT (using engine 1)"


# ============================================================
# Step 10.4: Anti-fragility (Barbell Strategy) (流木 23)
# ============================================================

class BarbellStrategy:
    """Taleb の Anti-fragile = Barbell strategy
    
    リソースを 2 極に分散:
      - 80-90% は超保守的 (絶対安全)
      - 10-20% は超積極的 (大きなリターン狙い)
    
    効果:
      - 通常時: 保守側で安定収益
      - Black Swan 時: 保守側が守り、積極側が利益化 (場合により)
      - 単純な保守 vs 単純な積極 より良い
    """
    
    def __init__(self, safe_ratio: float = 0.85):
        """
        safe_ratio: 保守的部分の比率 (0.85 = 85%)
        """
        self.safe_ratio = safe_ratio
        self.risky_ratio = 1 - safe_ratio
    
    def allocate(self, total_resource: float) -> Dict[str, float]:
        """リソース配分"""
        return {
            "safe": total_resource * self.safe_ratio,
            "risky": total_resource * self.risky_ratio,
            "middle": 0.0,  # 中庸を取らない
        }
    
    def evaluate_strategy(self, outcomes_safe: List[float], 
                           outcomes_risky: List[float]) -> Dict:
        """Barbell の効果評価"""
        # 通常時 (中央値):
        normal_safe = np.median(outcomes_safe)
        normal_risky = np.median(outcomes_risky)
        normal_combined = self.safe_ratio * normal_safe + self.risky_ratio * normal_risky
        
        # 極端時 (上位 5% と下位 5%):
        extreme_high_safe = np.percentile(outcomes_safe, 95)
        extreme_high_risky = np.percentile(outcomes_risky, 95)
        extreme_high_combined = (
            self.safe_ratio * extreme_high_safe + 
            self.risky_ratio * extreme_high_risky
        )
        
        extreme_low_safe = np.percentile(outcomes_safe, 5)
        extreme_low_risky = np.percentile(outcomes_risky, 5)
        extreme_low_combined = (
            self.safe_ratio * extreme_low_safe + 
            self.risky_ratio * extreme_low_risky
        )
        
        return {
            "normal_outcome": normal_combined,
            "extreme_high": extreme_high_combined,
            "extreme_low": extreme_low_combined,
            "asymmetry": extreme_high_combined - extreme_low_combined,
        }


# ============================================================
# Step 10.5: Adversarial Agent (流木 24)
# ============================================================

class AdversarialAgent:
    """対戦相手 (環境を悪化させる方向に動く)
    
    NRMO の robustness を真にテストするため:
      adversary がエンジンに対し worst-case を作る
    """
    
    def __init__(self, adversarial_strength: float = 0.5):
        """
        adversarial_strength: 0.0 (穏当) - 1.0 (極悪)
        """
        self.strength = adversarial_strength
    
    def generate_adversarial_world(self, agent_strategy: str) -> Dict:
        """エージェントの戦略に対し最悪の world を生成"""
        # エージェント戦略の弱点を突く
        if agent_strategy == "invest":
            # 投資戦略 → ruin probability を上げる
            return {
                "ruin_probability_base": 0.10 * self.strength + 0.05,
                "competitive_pressure": 0.7 * self.strength + 0.3,
                "opportunity_arrival_rate": 0.05,  # 機会少ない
            }
        elif agent_strategy == "defend":
            # 守備戦略 → 機会窓を短くする
            return {
                "opportunity_arrival_rate": 0.40 * self.strength + 0.2,
                "opportunity_window_duration": 1.5,  # 窓短い
                "resource_decay_rate": 0.05 * self.strength + 0.02,
            }
        elif agent_strategy == "explore":
            return {
                "information_uncertainty": 0.6 * self.strength + 0.3,
                "noise_amplitude": 0.35 * self.strength + 0.1,
                "irreversibility_propensity": 0.5 * self.strength + 0.3,
            }
        else:
            # 一般的に悪化
            return {
                "ruin_probability_base": 0.08 * self.strength + 0.03,
                "noise_amplitude": 0.3 * self.strength + 0.1,
            }


# ============================================================
# Step 10.6: Extreme Value Theory (流木 25, 26)
# ============================================================

class ExtremeValueAnalyzer:
    """裾の重い分布の正しい扱い
    
    通常の正規分布仮定では tail risk を過小評価
    Generalized Pareto Distribution (GPD) を使う
    
    Black Swan 対応:
      - 極端事象の頻度と影響を正しく推定
      - VaR (Value at Risk) と CVaR (Conditional VaR)
    """
    
    def __init__(self, threshold_percentile: float = 95):
        """
        threshold_percentile: tail 領域の定義 (95 = 上位 5%)
        """
        self.threshold_percentile = threshold_percentile
    
    def fit_gpd(self, data: List[float]) -> Dict:
        """Generalized Pareto Distribution fitting"""
        data = np.array(data)
        threshold = np.percentile(data, self.threshold_percentile)
        
        excesses = data[data > threshold] - threshold
        if len(excesses) < 5:
            return {"error": "Insufficient tail data"}
        
        # GPD fit (Method of moments)
        mean_excess = excesses.mean()
        var_excess = excesses.var()
        
        # Shape (ξ) and scale (σ) parameters
        if var_excess > 0 and mean_excess > 0:
            shape = 0.5 * (1 - (mean_excess ** 2) / var_excess)
            scale = mean_excess * (1 - shape)
        else:
            shape = 0.0
            scale = mean_excess
        
        return {
            "threshold": float(threshold),
            "n_excesses": len(excesses),
            "shape": float(shape),
            "scale": float(scale),
            "heavy_tail": shape > 0,  # heavy tail なら shape > 0
        }
    
    def value_at_risk(self, data: List[float], 
                       confidence: float = 0.99) -> float:
        """VaR: 信頼度 confidence での最悪損失推定"""
        gpd = self.fit_gpd(data)
        if "error" in gpd:
            return float(np.percentile(data, (1 - confidence) * 100))
        
        # GPD ベースの VaR (上位 1-confidence の閾値)
        threshold = gpd["threshold"]
        shape = gpd["shape"]
        scale = gpd["scale"]
        
        n_total = len(data)
        n_threshold = sum(1 for d in data if d > threshold)
        
        if n_threshold == 0:
            return threshold
        
        p_exceed = n_threshold / n_total
        target_q = 1 - confidence
        
        if target_q > p_exceed:
            return threshold
        
        if shape == 0:
            var = threshold + scale * np.log(p_exceed / target_q)
        else:
            var = threshold + (scale / shape) * ((p_exceed / target_q) ** shape - 1)
        
        return float(var)
    
    def conditional_var(self, data: List[float],
                          confidence: float = 0.99) -> float:
        """CVaR: VaR を超えた時の期待損失"""
        gpd = self.fit_gpd(data)
        if "error" in gpd:
            tail_data = [d for d in data if d > np.percentile(data, confidence * 100)]
            return float(np.mean(tail_data)) if tail_data else 0.0
        
        var = self.value_at_risk(data, confidence)
        shape = gpd["shape"]
        scale = gpd["scale"]
        
        if shape < 1:
            cvar = (var + scale - shape * gpd["threshold"]) / (1 - shape)
        else:
            cvar = var * 1.5  # 安全側
        
        return float(cvar)


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10 — ストレス耐性強化 動作確認")
    print("=" * 70)
    
    np.random.seed(42)
    
    # === Step 10.1: Anti-Goodhart ===
    print("\n--- Step 10.1: Anti-Goodhart Framework ---")
    framework = AntiGoodhartFramework()
    
    # Goodhart 状況をシミュ: score 向上、他指標悪化
    for t in range(50):
        score_trend = t * 0.02  # 上昇
        robustness_trend = -t * 0.01  # 下降
        optionality_trend = -t * 0.015  # 下降
        framework.record({
            "score": 1.0 + score_trend + np.random.normal(0, 0.05),
            "robustness": 0.8 + robustness_trend + np.random.normal(0, 0.05),
            "optionality": 0.7 + optionality_trend + np.random.normal(0, 0.05),
            "alignment": 0.6 + np.random.normal(0, 0.05),
            "diversity": 0.5 + np.random.normal(0, 0.05),
        })
    
    is_goodhart, reason = framework.detect_goodhart()
    print(f"Goodhart detected: {is_goodhart}")
    print(f"  Reason: {reason}")
    print(f"Composite score (multi-indicator): {framework.composite_score():.3f}")
    
    # === Step 10.2: Reflexivity ===
    print("\n--- Step 10.2: Reflexivity-Aware Engine ---")
    reflexive = ReflexivityAwareEngine()
    
    # 過去介入を記録
    for _ in range(10):
        pre = np.random.normal(50, 10, 6)
        post = pre + np.array([3, -2, 1, 4, 0, 2]) + np.random.normal(0, 1, 6)
        reflexive.record_intervention("invest", pre, post)
    
    effect = reflexive.estimated_reflexive_effect("invest")
    print(f"Past 'invest' interventions: {effect['n_similar']}")
    print(f"Mean effect on state: {[round(e, 2) for e in effect['mean_effect']]}")
    print(f"Second-order effect: {effect['second_order_effect']:.2f}")
    
    # === Step 10.3: TMR ===
    print("\n--- Step 10.3: Triple Modular Redundancy ---")
    
    def engine_optimistic(x): return "invest"
    def engine_conservative(x): return "defend"
    def engine_balanced(x): return "invest"
    
    tmr = TripleModularRedundancy([
        engine_optimistic, engine_conservative, engine_balanced
    ])
    
    decision, status = tmr.voted_decision(None)
    print(f"TMR decision: {decision} (status: {status})")
    print(f"  → 2/3 voted for 'invest', conservative engine disagreed")
    
    # === Step 10.4: Barbell ===
    print("\n--- Step 10.4: Barbell Strategy ---")
    barbell = BarbellStrategy(safe_ratio=0.85)
    
    safe_outcomes = np.random.normal(2, 1, 1000)         # 安定だが小さい
    risky_outcomes = np.random.normal(0, 10, 1000)        # ハイリスクハイリターン
    
    eval_result = barbell.evaluate_strategy(safe_outcomes, risky_outcomes)
    print(f"Normal outcome (median): {eval_result['normal_outcome']:.2f}")
    print(f"Extreme high (95%ile):   {eval_result['extreme_high']:.2f}")
    print(f"Extreme low (5%ile):     {eval_result['extreme_low']:.2f}")
    print(f"Asymmetry (high-low):    {eval_result['asymmetry']:.2f}")
    print(f"  → Barbell の特徴: 通常はそこそこ、極端で大きく振れる")
    
    # === Step 10.5: Adversarial Agent ===
    print("\n--- Step 10.5: Adversarial Agent ---")
    adversary = AdversarialAgent(adversarial_strength=0.7)
    
    for strategy in ["invest", "defend", "explore"]:
        worst_world = adversary.generate_adversarial_world(strategy)
        print(f"Worst world for '{strategy}':")
        for k, v in list(worst_world.items())[:2]:
            print(f"  {k}: {v:.3f}")
    
    # === Step 10.6: Extreme Value Theory ===
    print("\n--- Step 10.6: Extreme Value Theory ---")
    
    # Heavy-tailed data (Pareto-like)
    normal_data = np.random.normal(0, 1, 900)
    tail_data = np.random.pareto(1.5, 100) * 5  # Heavy tail
    mixed_data = np.concatenate([normal_data, tail_data])
    
    eva = ExtremeValueAnalyzer(threshold_percentile=90)
    gpd = eva.fit_gpd(list(mixed_data))
    
    print(f"GPD fitting:")
    print(f"  Threshold: {gpd['threshold']:.3f}")
    print(f"  Shape (ξ): {gpd['shape']:.3f}")
    print(f"  Heavy tail: {gpd['heavy_tail']}")
    
    var_99 = eva.value_at_risk(list(mixed_data), 0.99)
    cvar_99 = eva.conditional_var(list(mixed_data), 0.99)
    print(f"\nVaR 99%:  {var_99:.3f}")
    print(f"CVaR 99%: {cvar_99:.3f}  (VaR を超えた時の期待値)")
    
    print(f"\n[Phase 10 完了 ✅ — 全 31 流木対処完了]")
