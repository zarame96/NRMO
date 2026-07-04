"""
NRMO Phase 11 / Step 11.2 — Falsifiability Specification

NRMO がいつ「失格」とみなされるかを明示的に定義。
Popper の科学的反証可能性原理に基づく。

「NRMO は破滅を避ける」だけでは反証不能。
「以下の条件で NRMO は失敗」を明文化することで初めて科学的検証可能になる。
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum


class FailureType(Enum):
    """NRMO 失格のタイプ (北極星 5 側面に対応)"""
    SOVEREIGNTY_LOST = "sovereignty_lost"           # 主権性喪失
    VISION_DRIFT = "vision_drift"                   # Vision 整合性喪失
    OPTIONALITY_COLLAPSE = "optionality_collapse"   # 選択肢喪失
    RUIN_OCCURRED = "ruin_occurred"                  # 不可逆破滅
    DECISION_PARALYSIS = "decision_paralysis"        # 持続性喪失
    
    # 補助的失格
    OVERCONFIDENCE = "overconfidence"                # 過剰確信
    FRAMEWORK_DRIFT = "framework_drift"              # NRMO 自体の崩壊


def _default_failure_detect(failure_type: "FailureType", observation: Dict) -> bool:
    """failure_type 別の既定検出 (FalsifiabilityCondition.is_triggered と
    FalsifiabilityMonitor が共有する単一の検出規約)。"""
    if not observation:
        return False
    o = observation
    if failure_type == FailureType.SOVEREIGNTY_LOST:
        return o.get("acceptance_rate", 0) > 0.95
    elif failure_type == FailureType.VISION_DRIFT:
        return o.get("vision_alignment", 1.0) < 0.3
    elif failure_type == FailureType.OPTIONALITY_COLLAPSE:
        return o.get("optionality_ratio", 1.0) < 0.7
    elif failure_type == FailureType.RUIN_OCCURRED:
        return bool(o.get("ruin_status", False))
    elif failure_type == FailureType.DECISION_PARALYSIS:
        return o.get("hold_ratio", 0) > 0.8
    elif failure_type == FailureType.OVERCONFIDENCE:
        return o.get("overconfidence_score", 0) > 0.3
    elif failure_type == FailureType.FRAMEWORK_DRIFT:
        return o.get("invariant_violation_rate", 0) > 0.05
    return False


@dataclass
class FalsifiabilityCondition:
    """NRMO の失格条件 (1 つ)"""
    failure_type: FailureType
    name: str                       # 短い名称
    description: str                # 詳細説明
    operational_definition: str     # 運用上の定義 (測定可能)
    detection_method: str           # 検出方法
    threshold: Optional[float] = None  # 数値閾値 (該当する場合)
    severity: int = 3               # 1 (warning) - 5 (catastrophic)
    
    def is_triggered(self, observation: Dict) -> bool:
        """この条件が triggered されるか判定。
        detector 関数 (self._detector) が設定されていればそれを使い、
        無ければ failure_type 別の既定検出を用いる (FalsifiabilityMonitor と同一規約)。"""
        detector = getattr(self, "_detector", None)
        if callable(detector):
            return bool(detector(observation, self))
        return _default_failure_detect(self.failure_type, observation)


# ============================================================
# Falsifiability 条件の全リスト (NRMO 失格条件)
# ============================================================

FALSIFIABILITY_CONDITIONS = [
    # === 5 側面に対応する核心的失格条件 ===
    
    FalsifiabilityCondition(
        failure_type=FailureType.SOVEREIGNTY_LOST,
        name="ユーザーの NRMO 盲信",
        description=(
            "ユーザーが自分で判断せず、NRMO の出力をそのまま採用するようになる。"
            "「NRMO がそう言うから」と理由を考えずに従う。"
        ),
        operational_definition=(
            "過去 N=30 判断のうち、"
            "NRMO 提案を 95% 以上そのまま採用、"
            "かつ判断時間が 10 秒未満 (吟味なし)"
        ),
        detection_method="判断ログから採用率と所要時間を集計",
        threshold=0.95,
        severity=5,
    ),
    
    FalsifiabilityCondition(
        failure_type=FailureType.VISION_DRIFT,
        name="Vision からの逸脱",
        description=(
            "ユーザーの判断が、明示された Vision (gains, protect) から"
            "徐々に乖離していく。"
        ),
        operational_definition=(
            "判断ログの Vision 整合性スコアが、"
            "30 判断にわたって monotonically decreasing"
        ),
        detection_method="Vision-Decision 整合性 LLM 評価",
        threshold=0.3,  # 整合性 30% 未満で警告
        severity=4,
    ),
    
    FalsifiabilityCondition(
        failure_type=FailureType.OPTIONALITY_COLLAPSE,
        name="選択肢の構造的喪失",
        description=(
            "ユーザーの将来選択肢数が時間とともに単調減少。"
            "NRMO 使用後の方が選択肢が少ない状態。"
        ),
        operational_definition=(
            "Optionality 指標 (O 次元) が、"
            "NRMO 使用後 6 ヶ月で 30% 以上減少"
        ),
        detection_method="O 次元の長期トレンド分析",
        threshold=0.7,  # 30% 減で trigger
        severity=4,
    ),
    
    FalsifiabilityCondition(
        failure_type=FailureType.RUIN_OCCURRED,
        name="不可逆破滅の発生",
        description=(
            "NRMO 利用中にユーザーが不可逆破滅状態に到達。"
            "金銭破綻、健康崩壊、法的破綻、関係破綻等。"
        ),
        operational_definition=(
            "ユーザー自己申告 or 外形的証拠で"
            "Recovery 不可能な状態を確認"
        ),
        detection_method="ユーザー自己申告 + 外部 indicator",
        threshold=None,
        severity=5,
    ),
    
    FalsifiabilityCondition(
        failure_type=FailureType.DECISION_PARALYSIS,
        name="判断不能状態",
        description=(
            "ユーザーが NRMO を使うほど判断できなくなる。"
            "分析過剰、判断回避、HOLD の連鎖。"
        ),
        operational_definition=(
            "過去 N=30 判断のうち、"
            "HOLD 比率 80% 以上"
            "かつ平均判断時間 > 1 時間"
        ),
        detection_method="HOLD 比率と所要時間の集計",
        threshold=0.8,
        severity=4,
    ),
    
    # === 補助的失格条件 ===
    
    FalsifiabilityCondition(
        failure_type=FailureType.OVERCONFIDENCE,
        name="NRMO の過剰確信",
        description=(
            "NRMO の出力に very_high 信頼度が頻出するが、"
            "実結果との乖離が大きい。"
        ),
        operational_definition=(
            "very_high 信頼度の判断で、"
            "事後 reality との乖離率 30% 以上"
        ),
        detection_method="信頼度と事後事実の対比",
        threshold=0.3,
        severity=3,
    ),
    
    FalsifiabilityCondition(
        failure_type=FailureType.FRAMEWORK_DRIFT,
        name="NRMO 自体の崩壊",
        description=(
            "NRMO の動作が、Document 00 の不変条件を継続的に違反。"
            "ガバナンス・実行分離崩壊、推奨と判定の混合等。"
        ),
        operational_definition=(
            "不変条件違反の発生頻度が、"
            "全判断の 5% を超える"
        ),
        detection_method="不変条件チェッカー (G8 強化版)",
        threshold=0.05,
        severity=5,
    ),
    
    # === 統計的失格条件 ===
    
    FalsifiabilityCondition(
        failure_type=FailureType.RUIN_OCCURRED,
        name="シミュレーション破滅率の悪化",
        description=(
            "再現性のあるシミュレーションで、"
            "NRMO 利用時の破滅率が、利用しない時より高い。"
        ),
        operational_definition=(
            "1000 runs × 5 worlds で、"
            "Ruin rate(NRMO) > Ruin rate(no NRMO) + 0.01"
        ),
        detection_method="シミュレーション再現性テスト",
        threshold=0.01,
        severity=4,
    ),
]


# ============================================================
# Falsifiability Monitor
# ============================================================

class FalsifiabilityMonitor:
    """NRMO の失格条件を継続的に監視"""
    
    def __init__(self):
        self.conditions = FALSIFIABILITY_CONDITIONS
        self.observations = []
        self.triggered_failures = []
    
    def add_observation(self, observation: Dict):
        """観測データを追加"""
        self.observations.append(observation)
    
    def check_all(self) -> List[Dict]:
        """全失格条件をチェック"""
        results = []
        for cond in self.conditions:
            try:
                triggered = self._check_condition(cond)
                results.append({
                    "condition": cond.name,
                    "type": cond.failure_type.value,
                    "triggered": triggered,
                    "severity": cond.severity,
                })
                if triggered:
                    self.triggered_failures.append(cond)
            except Exception as e:
                results.append({
                    "condition": cond.name,
                    "type": cond.failure_type.value,
                    "error": str(e),
                })
        return results
    
    def _check_condition(self, cond: FalsifiabilityCondition) -> bool:
        """個別条件のチェック。is_triggered (= 共有検出規約) に委譲。"""
        if not self.observations:
            return False
        return cond.is_triggered(self.observations[-1])
        
        return False
    
    def report(self) -> str:
        """現状レポート"""
        if not self.triggered_failures:
            return "NRMO is OPERATIONAL: 全失格条件 pass"
        
        lines = ["NRMO FALSIFICATION DETECTED:"]
        for f in self.triggered_failures:
            lines.append(f"  [Severity {f.severity}] {f.name}")
            lines.append(f"    Type: {f.failure_type.value}")
            lines.append(f"    Description: {f.description}")
        
        max_severity = max(f.severity for f in self.triggered_failures)
        if max_severity >= 5:
            lines.append("\n⚠ CATASTROPHIC: NRMO 即時運用停止推奨")
        elif max_severity >= 4:
            lines.append("\n⚠ SERIOUS: NRMO 緊急設計見直し")
        elif max_severity >= 3:
            lines.append("\n⚠ WARNING: NRMO 改善必要")
        
        return "\n".join(lines)


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("NRMO Phase 11 / Step 11.2 — Falsifiability Specification")
    print("=" * 70)
    
    print(f"\n全失格条件数: {len(FALSIFIABILITY_CONDITIONS)}")
    print("\nSeverity 別:")
    from collections import Counter
    severity_counts = Counter(c.severity for c in FALSIFIABILITY_CONDITIONS)
    for sev in sorted(severity_counts, reverse=True):
        print(f"  Severity {sev}: {severity_counts[sev]} 件")
    
    print("\n--- 全失格条件 ---")
    for i, cond in enumerate(FALSIFIABILITY_CONDITIONS, 1):
        print(f"\n[{i}] {cond.name} (Severity {cond.severity})")
        print(f"  Type: {cond.failure_type.value}")
        print(f"  Description: {cond.description}")
        print(f"  Operational: {cond.operational_definition}")
    
    # Monitor 動作確認
    print("\n" + "=" * 70)
    print("Falsifiability Monitor 動作確認")
    print("=" * 70)
    
    monitor = FalsifiabilityMonitor()
    
    # 観測データ追加 (健全な状態)
    monitor.add_observation({
        "acceptance_rate": 0.6,
        "vision_alignment": 0.85,
        "optionality_ratio": 0.95,
        "ruin_status": False,
        "hold_ratio": 0.15,
        "overconfidence_score": 0.1,
        "invariant_violation_rate": 0.01,
    })
    
    results = monitor.check_all()
    print("\n[健全状態]")
    for r in results:
        status = "TRIGGERED" if r.get("triggered") else "OK"
        print(f"  {status}: {r['condition']}")
    print(monitor.report())
    
    # 異常状態
    print("\n[異常状態]")
    monitor2 = FalsifiabilityMonitor()
    monitor2.add_observation({
        "acceptance_rate": 0.98,  # 主権性喪失
        "vision_alignment": 0.25,  # Vision drift
        "optionality_ratio": 0.65,  # Optionality collapse
        "ruin_status": False,
        "hold_ratio": 0.85,  # 判断不能
        "overconfidence_score": 0.4,  # 過剰確信
        "invariant_violation_rate": 0.06,  # Framework drift
    })
    
    results = monitor2.check_all()
    for r in results:
        status = "TRIGGERED" if r.get("triggered") else "OK"
        sev = f"[Sev {r['severity']}]" if r.get("triggered") else ""
        print(f"  {status} {sev}: {r['condition']}")
    print()
    print(monitor2.report())
