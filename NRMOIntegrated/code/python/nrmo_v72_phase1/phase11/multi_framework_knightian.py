"""
NRMO Phase 11 / Steps 11.5 + 11.6 — Multi-Framework + Knightian

Step 11.5: 代替フレームワークアンサンブル (流木 28)
  NRMO 単独ではなく、複数の意思決定理論を統合
  - Expected Utility Theory (EUT)
  - Prospect Theory (Kahneman)
  - Robust Decision Making (RDM)
  - Info-gap Decision Theory
  - NRMO

Step 11.6: Knightian Uncertainty の数学化 (流木 5, 29)
  確率分布で表現できない不確実性への対処
  - Imprecise probability (上下確率)
  - Choquet integral
  - Dempster-Shafer evidence theory
"""
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Callable
from enum import Enum
import numpy as np


# ============================================================
# Step 11.5: Multi-Framework Ensemble
# ============================================================

class DecisionFramework(Enum):
    """採用する意思決定フレームワーク"""
    EUT = "expected_utility"           # 期待効用理論
    PROSPECT = "prospect_theory"        # プロスペクト理論
    RDM = "robust_decision_making"     # 頑健意思決定
    INFO_GAP = "info_gap"               # 情報ギャップ理論
    NRMO = "nrmo_non_ruin"             # NRMO 本体
    MINIMAX = "minimax_regret"         # ミニマックス後悔


@dataclass
class DecisionOption:
    """各選択肢"""
    name: str
    outcomes: List[Tuple[float, float]]  # [(probability, payoff), ...]
    
    def expected_value(self) -> float:
        """EUT: 期待効用"""
        return sum(p * v for p, v in self.outcomes)
    
    def variance(self) -> float:
        ev = self.expected_value()
        return sum(p * (v - ev) ** 2 for p, v in self.outcomes)
    
    def worst_case(self) -> float:
        """最悪ケース"""
        return min(v for _, v in self.outcomes)
    
    def best_case(self) -> float:
        """最善ケース"""
        return max(v for _, v in self.outcomes)


# === 各フレームワークの実装 ===

def evaluate_EUT(option: DecisionOption) -> float:
    """期待効用 (リスク中立)"""
    return option.expected_value()


def evaluate_prospect_theory(option: DecisionOption,
                              reference: float = 0.0,
                              alpha: float = 0.88,
                              beta: float = 0.88,
                              lambda_loss: float = 2.25) -> float:
    """Prospect Theory (Kahneman-Tversky)
    
    Value function (S-shape):
      v(x) = (x - ref)^alpha,  if x >= ref
      v(x) = -lambda * (ref - x)^beta,  if x < ref
    
    Probability weighting:
      w(p) = p^gamma / (p^gamma + (1-p)^gamma)^(1/gamma)
    """
    gamma = 0.61
    
    def value_func(x):
        diff = x - reference
        if diff >= 0:
            return diff ** alpha
        return -lambda_loss * (-diff) ** beta
    
    def weight_func(p):
        return p ** gamma / (p ** gamma + (1 - p) ** gamma) ** (1 / gamma)
    
    return sum(weight_func(p) * value_func(v) for p, v in option.outcomes)


def evaluate_RDM(option: DecisionOption,
                  scenarios: List[List[Tuple[float, float]]] = None) -> float:
    """Robust Decision Making (Lempert-Popper-Bankes)
    
    複数 plausible scenarios across で worst-case を最大化
    """
    if scenarios is None:
        # デフォルト: option の outcome distribution を perturbation
        scenarios = [option.outcomes]
        # +/- 20% perturbation
        perturbed_high = [(p, v * 1.2) for p, v in option.outcomes]
        perturbed_low = [(p, v * 0.8) for p, v in option.outcomes]
        scenarios.extend([perturbed_high, perturbed_low])
    
    worst_ev = float('inf')
    for scenario in scenarios:
        ev = sum(p * v for p, v in scenario)
        worst_ev = min(worst_ev, ev)
    return worst_ev


def evaluate_info_gap(option: DecisionOption,
                       robustness_horizon: float = 0.3) -> float:
    """Info-gap Decision Theory (Ben-Haim)
    
    「想定値からどれだけずれても許容できるか」の robustness を測定
    """
    # 期待値の robustness を info gap として
    ev = option.expected_value()
    worst = option.worst_case()
    
    # robustness = どれだけ outcome がずれても worst_case 以上か
    gap_size = (ev - worst) / max(abs(ev), 1e-6)
    robustness = max(0, 1 - gap_size)
    return robustness


def evaluate_NRMO(option: DecisionOption,
                    ruin_threshold: float = -10.0,
                    sigma_weight: float = 0.5) -> float:
    """NRMO 評価 (簡略版)
    
    1. ruin 確率を最小化
    2. ruin 回避できる範囲で expected value 最大化
    3. variance も penalty
    """
    # ruin probability
    ruin_prob = sum(p for p, v in option.outcomes if v <= ruin_threshold)
    
    if ruin_prob > 0.05:  # 5% 以上の破滅確率
        return -1000  # 即座に disqualify
    
    ev = option.expected_value()
    var = option.variance()
    
    return ev - sigma_weight * np.sqrt(var)


def evaluate_minimax_regret(option: DecisionOption,
                              all_options: List[DecisionOption]) -> float:
    """Minimax Regret (Savage)
    
    各 outcome state で他選択肢との差 (後悔) を最小化
    """
    max_regret = 0
    for p, v in option.outcomes:
        # この outcome で取り得た最大値
        max_in_state = max(
            max((p2, v2) for p2, v2 in opt.outcomes if abs(p2 - p) < 0.1)[1]
            if any(abs(p2 - p) < 0.1 for p2, _ in opt.outcomes) else v
            for opt in all_options
        )
        regret = max_in_state - v
        max_regret = max(max_regret, regret)
    return -max_regret  # negative for maximization


# === Ensemble Engine ===

class MultiFrameworkEnsemble:
    """6 フレームワークを統合した意思決定"""
    
    def __init__(self, weights: Dict[DecisionFramework, float] = None):
        # デフォルト weights (NRMO 重視)
        self.weights = weights or {
            DecisionFramework.EUT: 0.15,
            DecisionFramework.PROSPECT: 0.20,
            DecisionFramework.RDM: 0.20,
            DecisionFramework.INFO_GAP: 0.10,
            DecisionFramework.NRMO: 0.25,   # 最重要
            DecisionFramework.MINIMAX: 0.10,
        }
    
    def evaluate_option(self, option: DecisionOption,
                        all_options: List[DecisionOption]) -> Dict:
        """全フレームワークで評価"""
        scores = {
            DecisionFramework.EUT: evaluate_EUT(option),
            DecisionFramework.PROSPECT: evaluate_prospect_theory(option),
            DecisionFramework.RDM: evaluate_RDM(option),
            DecisionFramework.INFO_GAP: evaluate_info_gap(option) * 10,
            DecisionFramework.NRMO: evaluate_NRMO(option),
            DecisionFramework.MINIMAX: evaluate_minimax_regret(option, all_options),
        }
        
        # 正規化のため、各フレームワークごとに [-1, 1] へスケール
        # (デモ用、本格的には全 option で正規化)
        
        # 加重和
        composite = sum(self.weights[fw] * scores[fw] for fw in scores)
        
        # 各フレームワーク間の disagreement (合意度)
        score_values = list(scores.values())
        score_mean = np.mean(score_values)
        score_std = np.std(score_values)
        agreement = 1 / (1 + score_std)  # 0-1, 1 が完全合意
        
        return {
            "option": option.name,
            "scores_by_framework": {fw.value: scores[fw] for fw in scores},
            "composite_score": composite,
            "agreement": agreement,
            "ranks_by_framework": {},  # rank 計算は別途
        }
    
    def select_best(self, options: List[DecisionOption]) -> Dict:
        """複数選択肢から最良を選ぶ"""
        evaluations = [self.evaluate_option(opt, options) for opt in options]
        
        # 各フレームワークでの rank
        for fw in DecisionFramework:
            sorted_evals = sorted(
                evaluations,
                key=lambda e: e["scores_by_framework"][fw.value],
                reverse=True,
            )
            for rank, e in enumerate(sorted_evals):
                e["ranks_by_framework"][fw.value] = rank + 1
        
        # Composite で best
        best = max(evaluations, key=lambda e: e["composite_score"])
        
        # 合意度低い場合は warning
        warnings = []
        if best["agreement"] < 0.3:
            warnings.append(
                "⚠ フレームワーク間の合意度低い。判断の robustness 低い可能性。"
            )
        
        return {
            "best_option": best["option"],
            "best_composite": best["composite_score"],
            "all_evaluations": evaluations,
            "warnings": warnings,
        }


# ============================================================
# Step 11.6: Knightian Uncertainty (Imprecise Probability)
# ============================================================

@dataclass
class ImpreciseProbability:
    """上下確率による Knightian uncertainty 表現
    
    通常: P(event) = 0.3 (precise)
    Knightian: P(event) ∈ [0.2, 0.5] (lower, upper bound)
    """
    lower: float  # 下界
    upper: float  # 上界
    
    def __post_init__(self):
        assert 0 <= self.lower <= self.upper <= 1
    
    @property
    def precision(self) -> float:
        """精度 (1 が完全確定、0 が完全不確実)"""
        return 1 - (self.upper - self.lower)
    
    @property
    def is_knightian(self) -> bool:
        """Knightian uncertainty かどうか (上下に差がある)"""
        return (self.upper - self.lower) > 0.05
    
    def midpoint(self) -> float:
        return (self.lower + self.upper) / 2


@dataclass
class ImpreciseOption:
    """Imprecise probability で表現された option"""
    name: str
    outcomes: List[Tuple[ImpreciseProbability, float]]
    
    def lower_expected_value(self) -> float:
        """下側期待値 (悲観的)"""
        # lower bound の確率で計算
        # ただし合計 1 にならないと不適切なので、normalize
        lowers = [p.lower for p, _ in self.outcomes]
        total_lower = sum(lowers)
        if total_lower == 0:
            return 0
        return sum(p.lower * v for p, v in self.outcomes) / total_lower if total_lower < 1 else sum(p.lower * v for p, v in self.outcomes)
    
    def upper_expected_value(self) -> float:
        """上側期待値 (楽観的)"""
        return sum(p.upper * v for p, v in self.outcomes)
    
    def choquet_integral(self) -> float:
        """Choquet integral (非加法的測度に基づく期待値)
        
        Knightian uncertainty 下での「期待値」概念の拡張
        """
        # outcomes を値で降順 sort
        sorted_outcomes = sorted(self.outcomes, key=lambda x: x[1], reverse=True)
        
        result = 0
        cumulative_capacity = 0
        for i, (prob, value) in enumerate(sorted_outcomes):
            if i == 0:
                marginal = prob.lower  # 最大値の capacity = lower
            else:
                # 累積 capacity の差
                # Choquet では「(union) - (previous union)」の capacity を使う
                prev_cumulative = cumulative_capacity
                cumulative_capacity = min(cumulative_capacity + prob.lower, 1.0)
                marginal = cumulative_capacity - prev_cumulative
            result += marginal * value
        return result


class KnightianAwareEngine:
    """Knightian uncertainty を扱える評価"""
    
    def evaluate(self, options: List[ImpreciseOption]) -> Dict:
        """Imprecise options を評価"""
        results = []
        for opt in options:
            ev_lower = opt.lower_expected_value()
            ev_upper = opt.upper_expected_value()
            choquet = opt.choquet_integral()
            
            # uncertainty の総量
            total_uncertainty = sum(
                (p.upper - p.lower) for p, _ in opt.outcomes
            ) / len(opt.outcomes)
            
            results.append({
                "option": opt.name,
                "EV_lower (悲観)": ev_lower,
                "EV_upper (楽観)": ev_upper,
                "Choquet": choquet,
                "uncertainty": total_uncertainty,
                "is_knightian": any(p.is_knightian for p, _ in opt.outcomes),
            })
        
        # Maxmin: lower expected value を最大化 (悲観的だが最も robust)
        maxmin_best = max(results, key=lambda r: r["EV_lower (悲観)"])
        
        # Choquet best: 非加法的測度での best
        choquet_best = max(results, key=lambda r: r["Choquet"])
        
        return {
            "all_results": results,
            "maxmin_best": maxmin_best["option"],
            "choquet_best": choquet_best["option"],
        }


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("NRMO Phase 11 / Step 11.5 — Multi-Framework Ensemble")
    print("=" * 70)
    
    # 3 つの選択肢を想定
    # opt_A: 低リスク低リターン
    # opt_B: 中リスク中リターン
    # opt_C: 高リスク高リターン (低確率で大損失)
    options = [
        DecisionOption("A: 低リスク (現状維持)",
                        outcomes=[(0.7, 1.0), (0.3, 0.0)]),
        DecisionOption("B: 中リスク (転職検討)",
                        outcomes=[(0.5, 5.0), (0.3, 0.0), (0.2, -2.0)]),
        DecisionOption("C: 高リスク (起業)",
                        outcomes=[(0.3, 20.0), (0.4, 0.0), (0.3, -15.0)]),
    ]
    
    ensemble = MultiFrameworkEnsemble()
    result = ensemble.select_best(options)
    
    print(f"\n最良の選択肢: {result['best_option']}")
    print(f"  Composite score: {result['best_composite']:.3f}")
    
    print("\n各選択肢の評価:")
    for e in result["all_evaluations"]:
        print(f"\n  [{e['option']}]")
        print(f"    Composite: {e['composite_score']:+.3f}, "
                f"Agreement: {e['agreement']:.2f}")
        for fw_name, score in e["scores_by_framework"].items():
            rank = e["ranks_by_framework"].get(fw_name, "?")
            print(f"    {fw_name:<25}: {score:+8.3f}  (rank {rank})")
    
    for w in result["warnings"]:
        print(f"\n{w}")
    
    # Step 11.6 動作確認
    print("\n" + "=" * 70)
    print("NRMO Phase 11 / Step 11.6 — Knightian Uncertainty")
    print("=" * 70)
    
    # 不確実性の異なる 3 options
    imp_options = [
        ImpreciseOption(
            name="A: 知っている領域 (precise)",
            outcomes=[
                (ImpreciseProbability(0.7, 0.7), 1.0),
                (ImpreciseProbability(0.3, 0.3), 0.0),
            ],
        ),
        ImpreciseOption(
            name="B: 部分知の領域 (some Knightian)",
            outcomes=[
                (ImpreciseProbability(0.4, 0.6), 5.0),
                (ImpreciseProbability(0.2, 0.4), 0.0),
                (ImpreciseProbability(0.1, 0.3), -2.0),
            ],
        ),
        ImpreciseOption(
            name="C: 未知領域 (full Knightian)",
            outcomes=[
                (ImpreciseProbability(0.1, 0.5), 20.0),
                (ImpreciseProbability(0.3, 0.6), 0.0),
                (ImpreciseProbability(0.1, 0.4), -15.0),
            ],
        ),
    ]
    
    knightian = KnightianAwareEngine()
    k_result = knightian.evaluate(imp_options)
    
    print("\n各選択肢:")
    for r in k_result["all_results"]:
        print(f"\n  [{r['option']}]")
        print(f"    EV 下界 (悲観): {r['EV_lower (悲観)']:+.3f}")
        print(f"    EV 上界 (楽観): {r['EV_upper (楽観)']:+.3f}")
        print(f"    Choquet: {r['Choquet']:+.3f}")
        print(f"    Uncertainty: {r['uncertainty']:.3f}")
        print(f"    Knightian: {r['is_knightian']}")
    
    print(f"\nMaxmin best (悲観的に最良): {k_result['maxmin_best']}")
    print(f"Choquet best: {k_result['choquet_best']}")
    
    print("\n[Step 11.5 + 11.6 完了 ✅]")
