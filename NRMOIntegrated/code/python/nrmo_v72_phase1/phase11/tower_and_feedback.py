"""
NRMO Phase 11 / Steps 11.7 + 11.8 — Tower of Models + External Feedback

Step 11.7: Tower of Models 透明化 (流木 31)
  NRMO は何段階もの simplification の上にある
  各層の仮定と限界を明示

Step 11.8: External Feedback Integration (流木 11)
  目的論的循環の打破
  外部からの評価を取り込む仕組み
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


# ============================================================
# Step 11.7: Tower of Models Transparency
# ============================================================

@dataclass
class ModelLayer:
    """Tower の 1 層を表す"""
    name: str                          # 層の名前
    level: int                         # Tower での高さ (0 = 物理現実)
    represents: str                    # 何を表すか
    simplifications: List[str]         # この層で行った simplification
    assumptions: List[str]             # この層の仮定
    limitations: List[str]             # この層の限界
    valid_when: List[str]              # 有効な条件
    invalid_when: List[str]            # 無効になる条件


# NRMO の Tower of Models
NRMO_TOWER = [
    ModelLayer(
        name="Physical Reality",
        level=0,
        represents="物理的・社会的現実そのもの",
        simplifications=[],
        assumptions=["現実は単一かつ客観的に存在する"],
        limitations=["人間の認識は現実そのものではない"],
        valid_when=["特段の状況ではない (通常時)"],
        invalid_when=["量子効果、観測者効果が顕著な場合"],
    ),
    
    ModelLayer(
        name="Human Perception",
        level=1,
        represents="人間が認識する現実",
        simplifications=[
            "5 感に限定された観測",
            "認知バイアスによる selective attention",
            "言語化可能な部分のみ表現",
        ],
        assumptions=[
            "人間の認識は現実を近似的に捉える",
            "言語で表現された内容は思考を反映する",
        ],
        limitations=[
            "感覚の閾値以下の情報は失われる",
            "認知バイアスで歪む",
            "言語化困難な経験は伝達不能",
        ],
        valid_when=["健常な認知状態"],
        invalid_when=["極度のストレス、薬物影響、認知障害"],
    ),
    
    ModelLayer(
        name="Linguistic Description",
        level=2,
        represents="状況の言語的記述 (NRMO への入力)",
        simplifications=[
            "状況を有限個の単語で表現",
            "文脈の多くが省略される",
            "感情・直感が言語化される",
        ],
        assumptions=[
            "ユーザーは正直に状況を述べる",
            "重要な情報は省略されない",
        ],
        limitations=[
            "感情・直感を完全に言語化できない",
            "文化的・個人的文脈が失われる",
        ],
        valid_when=["ユーザーが詳細に説明する余裕がある時"],
        invalid_when=["緊急時、説明困難な複雑性"],
    ),
    
    ModelLayer(
        name="6D State Vector",
        level=3,
        represents="(R, E, G, O, K, X) で状況を表現",
        simplifications=[
            "全状況を 6 次元に圧縮",
            "次元間の独立性を仮定",
            "0-100 の数値範囲に正規化",
        ],
        assumptions=[
            "6 次元が状況の本質を捉える",
            "数値化が可能",
        ],
        limitations=[
            "6 次元に当てはまらない側面 (例: 創造性、愛) は失われる",
            "数値化困難なものを 50.0 で近似",
            "次元間の本来の相関を無視",
        ],
        valid_when=["定量化可能な意思決定領域"],
        invalid_when=["定性的判断 (芸術、倫理、愛)"],
    ),
    
    ModelLayer(
        name="World Parameters (11D)",
        level=4,
        represents="World の特性 (機会率、競争圧力など)",
        simplifications=[
            "11 次元で世界を表現",
            "パラメータは固定 (時間で不変)",
            "確率分布で表現可能",
        ],
        assumptions=[
            "11 次元で世界の動態を捉える",
            "Stationary process",
        ],
        limitations=[
            "Non-stationary process は扱えない",
            "Black Swan events を捉えない",
            "11 次元で表現できない構造 (e.g., network effects)",
        ],
        valid_when=["世界が比較的安定 (大変革なし)"],
        invalid_when=["パラダイムシフト、革命、危機"],
    ),
    
    ModelLayer(
        name="Probabilistic Outcome",
        level=5,
        represents="actions → 確率分布で表現された結果",
        simplifications=[
            "outcome を probability distribution で表現",
            "確率分布は normal or beta etc",
            "Markov 仮定 (現在状態のみで未来確率が決まる)",
        ],
        assumptions=[
            "全ての outcome は確率で表現可能",
            "Markov property holds",
        ],
        limitations=[
            "Knightian uncertainty は表現不可",
            "Path dependence は扱えない",
            "Fat-tail を過小評価する傾向",
        ],
        valid_when=["十分なデータで確率推定可能な領域"],
        invalid_when=["未知の未知 (unknown unknowns)"],
    ),
    
    ModelLayer(
        name="NRMO Decision",
        level=6,
        represents="NRMO の最終的判断 (提案)",
        simplifications=[
            "5 つの intent と 3 つの strength の組み合わせ",
            "「正しい行動」を 1 つ提案",
            "コスト・便益を数値で比較",
        ],
        assumptions=[
            "Action 空間は離散かつ有限",
            "Value function は加法的に分解可能",
        ],
        limitations=[
            "創造的な解 (新規 action) は提案できない",
            "両立不能なジレンマは扱いきれない",
            "倫理的判断は計算で代替不可",
        ],
        valid_when=["既存の選択肢から選ぶ状況"],
        invalid_when=["全く新しい選択肢が必要な状況"],
    ),
]


class TowerTransparencyEngine:
    """Tower of Models の透明化 engine"""
    
    def __init__(self, tower: List[ModelLayer] = NRMO_TOWER):
        self.tower = sorted(tower, key=lambda t: t.level)
    
    def show_full_tower(self) -> str:
        """全層を表示"""
        lines = ["NRMO Tower of Models (全 7 層):", "=" * 70]
        for layer in reversed(self.tower):  # 上から表示
            lines.append(f"\n[Level {layer.level}] {layer.name}")
            lines.append(f"  Represents: {layer.represents}")
            
            if layer.simplifications:
                lines.append(f"  Simplifications:")
                for s in layer.simplifications:
                    lines.append(f"    - {s}")
            
            if layer.assumptions:
                lines.append(f"  Assumptions:")
                for a in layer.assumptions:
                    lines.append(f"    - {a}")
            
            lines.append(f"  Valid when: {', '.join(layer.valid_when)}")
            lines.append(f"  Invalid when: {', '.join(layer.invalid_when)}")
        return "\n".join(lines)
    
    def estimate_total_distance_from_reality(self) -> float:
        """現実からの「距離」を概算 (各層の損失の蓄積)"""
        # 各層の simplification 数の平均
        avg_simplifications = sum(
            len(l.simplifications) for l in self.tower
        ) / max(len(self.tower), 1)
        
        # 距離 = 累積 simplification (概念的)
        # 1 つの simplification = 約 5% の情報損失と仮定
        distance = 1 - (0.95 ** sum(len(l.simplifications) for l in self.tower))
        return distance
    
    def validate_for_situation(self, situation_keywords: List[str]) -> Dict:
        """状況に応じて、どの層が valid/invalid か判定"""
        layers_status = []
        for layer in self.tower:
            invalid_match = any(
                any(kw in invalid for kw in situation_keywords)
                for invalid in layer.invalid_when
            )
            layers_status.append({
                "level": layer.level,
                "name": layer.name,
                "applicable": not invalid_match,
                "warnings": layer.invalid_when if invalid_match else [],
            })
        
        any_invalid = any(not l["applicable"] for l in layers_status)
        
        return {
            "layers": layers_status,
            "tower_intact": not any_invalid,
            "warning": (
                "⚠ Tower の一部が状況に不適合。NRMO 出力の信頼性低下"
                if any_invalid else "✓ Tower 全層が適用可能"
            ),
        }


# ============================================================
# Step 11.8: External Feedback Integration
# ============================================================

class FeedbackSource(Enum):
    """フィードバックの source"""
    USER_DIRECT = "user_direct"             # ユーザー直接フィードバック
    OUTCOME_OBSERVATION = "outcome"          # 実結果の観測
    PEER_EVALUATION = "peer"                 # 第三者評価
    EXPERT_REVIEW = "expert"                 # 専門家レビュー
    AUTOMATED_AUDIT = "automated_audit"      # 自動監査


@dataclass
class ExternalFeedback:
    """外部フィードバック (1 件)"""
    source: FeedbackSource
    timestamp: str
    target_decision_id: str          # どの判断に対するか
    feedback_type: str               # "agreement", "disagreement", "correction"
    content: str                     # フィードバック内容
    severity: int                    # 1-5
    actionable: bool                 # 修正アクション可能か


class ExternalFeedbackIntegrator:
    """外部 feedback を NRMO 改善に取り込む
    
    流木 11 (目的論的循環) への対処:
      NRMO 自身では NRMO の正しさを検証できない
      → 外部からの feedback で破る
    """
    
    def __init__(self):
        self.feedbacks: List[ExternalFeedback] = []
        self.improvement_log: List[Dict] = []
    
    def add_feedback(self, fb: ExternalFeedback):
        """フィードバック受領"""
        self.feedbacks.append(fb)
    
    def summary(self) -> Dict:
        """受領フィードバックの整理"""
        if not self.feedbacks:
            return {"status": "no_feedback"}
        
        by_source = {}
        by_type = {}
        for fb in self.feedbacks:
            by_source[fb.source.value] = by_source.get(fb.source.value, 0) + 1
            by_type[fb.feedback_type] = by_type.get(fb.feedback_type, 0) + 1
        
        # 多様性: 単一 source からのみだとバイアスあり
        source_diversity = len(by_source) / len(FeedbackSource)
        
        critical = [fb for fb in self.feedbacks if fb.severity >= 4]
        
        return {
            "total_feedbacks": len(self.feedbacks),
            "by_source": by_source,
            "by_type": by_type,
            "source_diversity": source_diversity,
            "critical_count": len(critical),
            "actionable_count": sum(1 for fb in self.feedbacks if fb.actionable),
        }
    
    def identify_systemic_issues(self) -> List[str]:
        """systemic な問題を identify"""
        issues = []
        
        # Pattern 1: 複数 source から同じ disagreement
        disagreements = [fb for fb in self.feedbacks 
                          if fb.feedback_type == "disagreement"]
        if len(disagreements) >= 3:
            sources = set(fb.source for fb in disagreements)
            if len(sources) >= 2:
                issues.append(
                    "複数 source から disagreement が報告されている"
                    " → systemic な誤判断の可能性"
                )
        
        # Pattern 2: Expert からの critical feedback
        expert_critical = [
            fb for fb in self.feedbacks
            if fb.source == FeedbackSource.EXPERT_REVIEW and fb.severity >= 4
        ]
        if expert_critical:
            issues.append(
                f"専門家から critical な指摘 {len(expert_critical)} 件"
                " → 設計見直し必要"
            )
        
        # Pattern 3: User confidence の傾向
        user_disagreements = [
            fb for fb in self.feedbacks 
            if fb.source == FeedbackSource.USER_DIRECT
            and fb.feedback_type == "disagreement"
        ]
        if len(user_disagreements) > len(self.feedbacks) * 0.3:
            issues.append(
                "ユーザーからの disagreement が 30% 超"
                " → NRMO の出力品質低下"
            )
        
        return issues
    
    def record_improvement(self, issue: str, action_taken: str):
        """フィードバックに基づく改善を記録"""
        self.improvement_log.append({
            "issue": issue,
            "action_taken": action_taken,
        })


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("NRMO Phase 11 / Step 11.7 — Tower of Models")
    print("=" * 70)
    
    tower_engine = TowerTransparencyEngine()
    
    # 全 Tower 表示
    print(tower_engine.show_full_tower())
    
    distance = tower_engine.estimate_total_distance_from_reality()
    print(f"\n\n現実からの累積距離 (概算): {distance:.1%}")
    print(f"  ↑ これだけの情報を失った上で NRMO は判断している")
    
    # 状況に応じた妥当性
    print("\n--- 通常状況 ---")
    result = tower_engine.validate_for_situation(["通常", "安定"])
    print(result["warning"])
    
    print("\n--- パラダイムシフト状況 ---")
    result = tower_engine.validate_for_situation(["パラダイムシフト", "革命"])
    print(result["warning"])
    for layer in result["layers"]:
        if not layer["applicable"]:
            print(f"  ✗ Level {layer['level']} ({layer['name']}) — invalid")
    
    # Step 11.8 動作確認
    print("\n" + "=" * 70)
    print("NRMO Phase 11 / Step 11.8 — External Feedback Integration")
    print("=" * 70)
    
    integrator = ExternalFeedbackIntegrator()
    
    # 複数 feedback を追加
    integrator.add_feedback(ExternalFeedback(
        source=FeedbackSource.USER_DIRECT,
        timestamp="2026-05-19",
        target_decision_id="decision_001",
        feedback_type="disagreement",
        content="NRMO は転職を推奨したが、Vision の「家族時間確保」と矛盾",
        severity=4,
        actionable=True,
    ))
    
    integrator.add_feedback(ExternalFeedback(
        source=FeedbackSource.EXPERT_REVIEW,
        timestamp="2026-05-19",
        target_decision_id="decision_002",
        feedback_type="disagreement",
        content="医療領域の判断に NRMO を使用しようとしている — Frame 外",
        severity=5,
        actionable=True,
    ))
    
    integrator.add_feedback(ExternalFeedback(
        source=FeedbackSource.OUTCOME_OBSERVATION,
        timestamp="2026-05-19",
        target_decision_id="decision_003",
        feedback_type="correction",
        content="NRMO の確率推定 30% に対し、実際は 10% で発生",
        severity=3,
        actionable=True,
    ))
    
    summary = integrator.summary()
    print(f"\n受領 feedback: {summary['total_feedbacks']} 件")
    print(f"  Source 別: {summary['by_source']}")
    print(f"  Type 別: {summary['by_type']}")
    print(f"  Source 多様性: {summary['source_diversity']:.0%}")
    print(f"  Critical: {summary['critical_count']} 件")
    print(f"  Actionable: {summary['actionable_count']} 件")
    
    print("\n--- Identified systemic issues ---")
    issues = integrator.identify_systemic_issues()
    for issue in issues:
        print(f"  ⚠ {issue}")
    
    print("\n[Step 11.7 + 11.8 完了 ✅]")
    print("\n" + "=" * 70)
    print("Phase 11 完成: 全 8 Steps 完了")
    print("=" * 70)
