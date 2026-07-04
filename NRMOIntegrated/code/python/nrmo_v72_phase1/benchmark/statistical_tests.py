"""
NRMO v7.2 Phase 1 — 統計検定モジュール

8 つの収束基準の自動チェック:
  基準 1: KS test 分布同一性
  基準 2: Mann-Whitney U 中央値差
  基準 3: Bootstrap 95% CI 重なり
  基準 4: 全 horizon Pareto 改善
  基準 5: Long Run plateau 同等
  基準 6: 軌跡 attractor 同一性
  基準 7: 破滅率の非発散
  基準 8: 統計収束
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats


@dataclass
class TestResult:
    """単一検定の結果"""
    test_name: str
    passed: bool
    p_value: Optional[float] = None
    statistic: Optional[float] = None
    details: Dict = field(default_factory=dict)
    interpretation: str = ""


@dataclass
class ConvergenceReport:
    """8 基準の総合レポート"""
    cell_id: str  # e.g. "Normal_H200"
    baseline_name: str
    candidate_name: str
    
    criterion_1_ks: TestResult
    criterion_2_mannwhitney: TestResult
    criterion_3_bootstrap: TestResult
    criterion_4_pareto: TestResult
    criterion_5_plateau: Optional[TestResult] = None  # H=5000 のみ
    criterion_6_attractor: Optional[TestResult] = None
    criterion_7_ruin: TestResult = None
    criterion_8_statistical: TestResult = None
    
    all_passed: bool = False
    
    def summarize(self) -> Dict:
        return {
            "cell": self.cell_id,
            "all_passed": self.all_passed,
            "individual": {
                "C1_KS": self.criterion_1_ks.passed,
                "C2_MW": self.criterion_2_mannwhitney.passed,
                "C3_Boot": self.criterion_3_bootstrap.passed,
                "C4_Pareto": self.criterion_4_pareto.passed,
                "C5_Plateau": self.criterion_5_plateau.passed if self.criterion_5_plateau else None,
                "C6_Attractor": self.criterion_6_attractor.passed if self.criterion_6_attractor else None,
                "C7_Ruin": self.criterion_7_ruin.passed if self.criterion_7_ruin else None,
                "C8_Statistical": self.criterion_8_statistical.passed if self.criterion_8_statistical else None,
            }
        }


# ============================================================
# 個別検定の実装
# ============================================================

def criterion_1_ks_test(baseline_samples: np.ndarray, 
                         candidate_samples: np.ndarray,
                         alpha: float = 0.05) -> TestResult:
    """基準 1: KS test
    
    H0: baseline 分布 = candidate 分布
    
    合格条件:
      p > alpha (有意差なし、つまり同等とみなせる)
      OR
      candidate の中央値が baseline より高い (片側改善)
    """
    statistic, p_value = stats.ks_2samp(baseline_samples, candidate_samples)
    
    candidate_median = np.median(candidate_samples)
    baseline_median = np.median(baseline_samples)
    candidate_better = candidate_median >= baseline_median
    
    # 合格条件: p > alpha (同一性) OR 改善方向の差
    passed = (p_value > alpha) or candidate_better
    
    interpretation = (
        f"KS統計量={statistic:.4f}, p={p_value:.4f}; "
        f"baseline_median={baseline_median:.4f}, candidate_median={candidate_median:.4f}"
    )
    
    return TestResult(
        test_name="KS Test",
        passed=passed,
        p_value=p_value,
        statistic=statistic,
        details={
            "candidate_better": candidate_better,
            "baseline_median": baseline_median,
            "candidate_median": candidate_median,
        },
        interpretation=interpretation,
    )


def criterion_2_mann_whitney(baseline_samples: np.ndarray,
                              candidate_samples: np.ndarray,
                              alpha: float = 0.05) -> TestResult:
    """基準 2: Mann-Whitney U test
    
    H0: 中央値に差なし
    alternative: candidate >= baseline (片側)
    
    合格条件:
      p > alpha (有意差なし)
      OR
      candidate > baseline で有意 (改善検出)
    """
    # 両側検定で同等性確認
    statistic_two, p_two = stats.mannwhitneyu(
        baseline_samples, candidate_samples, alternative='two-sided'
    )
    
    # 片側検定で改善方向の確認
    statistic_one, p_one = stats.mannwhitneyu(
        candidate_samples, baseline_samples, alternative='greater'
    )
    
    # 合格: 同等 (両側 p > alpha) または改善 (片側 p < alpha)
    passed = (p_two > alpha) or (p_one < alpha)
    
    interpretation = (
        f"両側p={p_two:.4f}, 片側(改善)p={p_one:.4f}"
    )
    
    return TestResult(
        test_name="Mann-Whitney U",
        passed=passed,
        p_value=p_two,
        statistic=statistic_two,
        details={"one_sided_p": p_one, "two_sided_p": p_two},
        interpretation=interpretation,
    )


def criterion_3_bootstrap_ci(baseline_samples: np.ndarray,
                              candidate_samples: np.ndarray,
                              n_resamples: int = 10000,
                              confidence: float = 0.95) -> TestResult:
    """基準 3: Bootstrap 95% CI 重なり
    
    両分布の bootstrap CI を計算し、重なるか確認
    """
    rng = np.random.RandomState(0)
    
    def bootstrap_ci(samples, statistic_fn=np.median, n=n_resamples):
        boot_stats = []
        for _ in range(n):
            resample = rng.choice(samples, size=len(samples), replace=True)
            boot_stats.append(statistic_fn(resample))
        boot_stats = np.array(boot_stats)
        alpha = 1 - confidence
        lower = np.percentile(boot_stats, alpha / 2 * 100)
        upper = np.percentile(boot_stats, (1 - alpha / 2) * 100)
        return lower, upper, np.mean(boot_stats)
    
    b_low, b_high, b_mean = bootstrap_ci(baseline_samples)
    c_low, c_high, c_mean = bootstrap_ci(candidate_samples)
    
    # 重なり判定
    ci_overlap = not (c_high < b_low or b_high < c_low)
    # または candidate が完全に baseline 以上
    candidate_above = c_low >= b_low
    
    passed = ci_overlap or candidate_above
    
    interpretation = (
        f"baseline CI=[{b_low:.4f}, {b_high:.4f}], "
        f"candidate CI=[{c_low:.4f}, {c_high:.4f}], "
        f"overlap={ci_overlap}, candidate_above={candidate_above}"
    )
    
    return TestResult(
        test_name="Bootstrap CI",
        passed=passed,
        details={
            "baseline_ci": (b_low, b_high),
            "candidate_ci": (c_low, c_high),
            "overlap": ci_overlap,
            "candidate_above": candidate_above,
        },
        interpretation=interpretation,
    )


def criterion_4_pareto(baseline_samples: np.ndarray,
                       candidate_samples: np.ndarray,
                       tolerance: float = 0.005) -> TestResult:
    """基準 4: Pareto 改善
    
    candidate の全主要統計値が baseline - tolerance 以上
    """
    metrics = {}
    
    # 中央値
    b_med = np.median(baseline_samples)
    c_med = np.median(candidate_samples)
    metrics["median"] = (b_med, c_med, c_med >= b_med - tolerance)
    
    # 平均
    b_mean = np.mean(baseline_samples)
    c_mean = np.mean(candidate_samples)
    metrics["mean"] = (b_mean, c_mean, c_mean >= b_mean - tolerance)
    
    # p25 (悲観シナリオ)
    b_p25 = np.percentile(baseline_samples, 25)
    c_p25 = np.percentile(candidate_samples, 25)
    metrics["p25"] = (b_p25, c_p25, c_p25 >= b_p25 - tolerance)
    
    # p75 (楽観シナリオ)
    b_p75 = np.percentile(baseline_samples, 75)
    c_p75 = np.percentile(candidate_samples, 75)
    metrics["p75"] = (b_p75, c_p75, c_p75 >= b_p75 - tolerance)
    
    passed = all(check for _, _, check in metrics.values())
    
    interpretation = "; ".join(
        f"{k}: {b:.4f}→{c:.4f} {'✓' if ok else '✗'}"
        for k, (b, c, ok) in metrics.items()
    )
    
    return TestResult(
        test_name="Pareto Improvement",
        passed=passed,
        details={k: {"baseline": b, "candidate": c, "passed": ok}
                 for k, (b, c, ok) in metrics.items()},
        interpretation=interpretation,
    )


def criterion_5_plateau(baseline_long_run: np.ndarray,
                         candidate_long_run: np.ndarray,
                         tolerance: float = 0.005,
                         plateau_window: int = 500) -> TestResult:
    """基準 5: Long Run plateau 同等
    
    最後 plateau_window ステップの平均値を比較
    """
    # plateau 値 = 最後 N runs の平均
    b_plateau = np.mean(baseline_long_run[-plateau_window:])
    c_plateau = np.mean(candidate_long_run[-plateau_window:])
    
    diff = c_plateau - b_plateau
    passed = diff >= -tolerance
    
    interpretation = (
        f"baseline plateau={b_plateau:.4f}, candidate plateau={c_plateau:.4f}, "
        f"diff={diff:.4f}"
    )
    
    return TestResult(
        test_name="Plateau Equivalence",
        passed=passed,
        details={
            "baseline_plateau": b_plateau,
            "candidate_plateau": c_plateau,
            "diff": diff,
        },
        interpretation=interpretation,
    )


def criterion_7_ruin_rate(baseline_samples: np.ndarray,
                           candidate_samples: np.ndarray,
                           ruin_threshold: float = 0.0,
                           tolerance: float = 0.005) -> TestResult:
    """基準 7: 破滅率の非発散
    
    candidate の破滅率が baseline 以下 (+tolerance 以内)
    """
    b_ruin = np.mean(baseline_samples < ruin_threshold)
    c_ruin = np.mean(candidate_samples < ruin_threshold)
    
    passed = c_ruin <= b_ruin + tolerance
    
    interpretation = (
        f"baseline ruin_rate={b_ruin:.4f}, candidate={c_ruin:.4f}, "
        f"diff={c_ruin - b_ruin:.4f}"
    )
    
    return TestResult(
        test_name="Ruin Rate Non-Divergence",
        passed=passed,
        details={"baseline_ruin": b_ruin, "candidate_ruin": c_ruin},
        interpretation=interpretation,
    )


def criterion_8_statistical_convergence(samples: np.ndarray,
                                         se_threshold: float = 0.001) -> TestResult:
    """基準 8: 統計収束
    
    σ/√n が十分小さいか確認
    """
    n = len(samples)
    sigma = np.std(samples)
    se = sigma / np.sqrt(n)
    
    passed = se < se_threshold
    
    interpretation = (
        f"n={n}, σ={sigma:.4f}, SE={se:.6f}, threshold={se_threshold}"
    )
    
    return TestResult(
        test_name="Statistical Convergence",
        passed=passed,
        statistic=se,
        details={"n": n, "sigma": sigma, "se": se},
        interpretation=interpretation,
    )


# ============================================================
# 統合検定
# ============================================================

def run_all_tests(baseline_samples: np.ndarray,
                   candidate_samples: np.ndarray,
                   cell_id: str = "default",
                   baseline_name: str = "v7.1",
                   candidate_name: str = "v7.2",
                   long_run_baseline: Optional[np.ndarray] = None,
                   long_run_candidate: Optional[np.ndarray] = None,
                   ) -> ConvergenceReport:
    """全 8 基準を実行 (一部は long run データがない場合スキップ)"""
    report = ConvergenceReport(
        cell_id=cell_id,
        baseline_name=baseline_name,
        candidate_name=candidate_name,
        criterion_1_ks=criterion_1_ks_test(baseline_samples, candidate_samples),
        criterion_2_mannwhitney=criterion_2_mann_whitney(baseline_samples, candidate_samples),
        criterion_3_bootstrap=criterion_3_bootstrap_ci(baseline_samples, candidate_samples),
        criterion_4_pareto=criterion_4_pareto(baseline_samples, candidate_samples),
        criterion_7_ruin=criterion_7_ruin_rate(baseline_samples, candidate_samples),
        criterion_8_statistical=criterion_8_statistical_convergence(candidate_samples),
    )
    
    if long_run_baseline is not None and long_run_candidate is not None:
        report.criterion_5_plateau = criterion_5_plateau(long_run_baseline, long_run_candidate)
    
    # 総合判定 (利用可能な全基準を AND)
    results = [
        report.criterion_1_ks,
        report.criterion_2_mannwhitney,
        report.criterion_3_bootstrap,
        report.criterion_4_pareto,
        report.criterion_7_ruin,
        report.criterion_8_statistical,
    ]
    if report.criterion_5_plateau:
        results.append(report.criterion_5_plateau)
    
    report.all_passed = all(r.passed for r in results)
    
    return report


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("統計検定モジュール 動作確認")
    print("=" * 60)
    
    # ケース 1: 改善ケース
    print("\n--- Case 1: 改善ケース (candidate > baseline) ---")
    np.random.seed(42)
    baseline = np.random.normal(0.50, 0.10, 1000)
    candidate = np.random.normal(0.55, 0.10, 1000)
    
    report = run_all_tests(baseline, candidate, "Test_Improvement")
    summary = report.summarize()
    print(f"All passed: {summary['all_passed']}")
    for k, v in summary['individual'].items():
        if v is not None:
            print(f"  {k}: {'✓' if v else '✗'}")
    
    # ケース 2: 悪化ケース
    print("\n--- Case 2: 悪化ケース (candidate < baseline) ---")
    baseline = np.random.normal(0.50, 0.10, 1000)
    candidate = np.random.normal(0.40, 0.10, 1000)
    
    report = run_all_tests(baseline, candidate, "Test_Regression")
    summary = report.summarize()
    print(f"All passed: {summary['all_passed']}")
    for k, v in summary['individual'].items():
        if v is not None:
            print(f"  {k}: {'✓' if v else '✗'}")
    
    # ケース 3: 同等ケース
    print("\n--- Case 3: 同等ケース ---")
    baseline = np.random.normal(0.50, 0.10, 1000)
    candidate = np.random.normal(0.50, 0.10, 1000)
    
    report = run_all_tests(baseline, candidate, "Test_Equivalent")
    summary = report.summarize()
    print(f"All passed: {summary['all_passed']}")
    for k, v in summary['individual'].items():
        if v is not None:
            print(f"  {k}: {'✓' if v else '✗'}")
