"""
NRMO Phase 11 / Steps 11.3 + 11.4 — Frame & Skin in the Game

Step 11.3: Frame の透明化 (流木 30)
  NRMO が「何を扱い、何を扱わないか」の明示
  範囲外の事象に対する明示的な警告

Step 11.4: Skin in the Game (流木 22)
  Confidence-staked output
  NRMO が自身の判断に対して「賭ける」仕組み
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


# ============================================================
# Step 11.3: Frame Transparency
# ============================================================

class FrameStatus(Enum):
    IN_FRAME = "in_frame"               # NRMO が扱える範囲内
    NEAR_BOUNDARY = "near_boundary"     # 境界近傍 (警告)
    OUT_OF_FRAME = "out_of_frame"       # 範囲外 (NRMO 機能停止)
    UNKNOWN = "unknown"                  # 判定不能


@dataclass
class FrameDefinition:
    """NRMO の扱える範囲 (Frame) の明示的定義"""
    
    # 扱える領域
    inside_frame: List[str] = field(default_factory=lambda: [
        "個人の日常的意思決定 (キャリア、投資、健康、関係)",
        "情報が部分的に取得可能な状況",
        "確率分布で表現可能な不確実性",
        "Vision が言語化可能な目的",
        "週から年単位の時間軸",
        "Reversible または semi-reversible な選択肢",
    ])
    
    # 範囲外 (扱わない)
    outside_frame: List[str] = field(default_factory=lambda: [
        "医療診断・治療方針 (専門医の領域)",
        "法的助言 (弁護士の領域)",
        "精神的危機対応 (専門家の領域)",
        "他者の人生に対する判断 (本人の主権領域)",
        "完全に予測不能な事象 (Black Swan)",
        "Knightian uncertainty 領域 (確率分布不能)",
        "Vision が定義できない状況",
        "極端な短時間 (秒単位の反射的判断)",
        "Irreversible で死に直結する選択",
    ])
    
    # 境界領域 (扱うが、警告つき)
    boundary_zones: List[str] = field(default_factory=lambda: [
        "情報極端に少ない状況 (信頼度 very_low で動作)",
        "Vision 部分的曖昧 (明確化を促す)",
        "高 stakes だが reversible (慎重姿勢で動作)",
        "新規ドメイン (経験データ少)",
    ])
    
    def classify(self, situation_description: str) -> FrameStatus:
        """状況が Frame 内外を分類 (簡易実装)"""
        # 実運用では LLM ベースの分類
        outside_keywords = [
            "診断", "処方", "症状", "治療", "薬",  # 医療
            "訴訟", "判決", "法的", "違法",         # 法律
            "自殺", "自傷", "希死",                   # 危機
            "他人の人生", "勝手に決める",            # 他者主権
            "今すぐ", "瞬時", "1 秒以内",            # 極端短時間
        ]
        boundary_keywords = [
            "情報がない", "わからない", "急に",
            "初めて", "新規",
        ]
        
        for kw in outside_keywords:
            if kw in situation_description:
                return FrameStatus.OUT_OF_FRAME
        for kw in boundary_keywords:
            if kw in situation_description:
                return FrameStatus.NEAR_BOUNDARY
        return FrameStatus.IN_FRAME
    
    def get_warning(self, status: FrameStatus) -> str:
        """状況に応じた警告メッセージ"""
        if status == FrameStatus.OUT_OF_FRAME:
            return (
                "⚠ この件は NRMO の範囲外です。専門家にご相談ください。\n"
                "  NRMO は意思決定支援であり、専門領域の代替ではありません。"
            )
        elif status == FrameStatus.NEAR_BOUNDARY:
            return (
                "⚠ この件は NRMO の境界領域です。\n"
                "  NRMO の助言は参考程度に、最終判断は慎重にお願いします。\n"
                "  追加情報の収集と専門家相談も検討してください。"
            )
        elif status == FrameStatus.IN_FRAME:
            return "✓ NRMO の通常範囲です。"
        else:
            return "⚠ 範囲判定が困難な状況です。"


# ============================================================
# Step 11.4: Skin in the Game (Confidence Staking)
# ============================================================

class StakeLevel(Enum):
    """NRMO が「賭ける」レベル"""
    NO_STAKE = "no_stake"           # 完全に責任放棄 (情報提供のみ)
    LOW_STAKE = "low_stake"         # 軽い helping (提案レベル)
    MEDIUM_STAKE = "medium_stake"   # 中程度 (検討推奨)
    HIGH_STAKE = "high_stake"       # 強く支持
    FULL_STAKE = "full_stake"       # 全力で支持 (極めて稀)


@dataclass
class StakedOutput:
    """Skin in the Game を実装した出力"""
    proposal: str                    # 提案内容
    stake_level: StakeLevel          # NRMO が賭けるレベル
    internal_confidence: float       # 0.0 - 1.0
    reasoning_chain: List[str]       # なぜこの提案か
    falsifiable_predictions: List[str]  # 反証可能な予測
    accept_responsibility_on: str    # NRMO が「責任を取る」条件
    user_should_decide_if: str       # ユーザー判断推奨条件
    
    def format_for_user(self) -> str:
        """ユーザー向けフォーマット"""
        lines = [
            f"【提案】{self.proposal}",
            "",
            f"【NRMO の confidence】{self._format_stake()}",
            f"  内部信頼度: {self.internal_confidence:.0%}",
            "",
            "【根拠】",
        ]
        for r in self.reasoning_chain:
            lines.append(f"  • {r}")
        
        lines.extend([
            "",
            "【反証可能な予測 (NRMO が間違っていたら以下が起きない)】",
        ])
        for p in self.falsifiable_predictions:
            lines.append(f"  • {p}")
        
        lines.extend([
            "",
            f"【NRMO の責任を問える条件】{self.accept_responsibility_on}",
            f"【ユーザー独自判断推奨】{self.user_should_decide_if}",
        ])
        
        return "\n".join(lines)
    
    def _format_stake(self) -> str:
        emoji_map = {
            StakeLevel.NO_STAKE: "🔍 (情報提供のみ)",
            StakeLevel.LOW_STAKE: "💭 (検討材料として)",
            StakeLevel.MEDIUM_STAKE: "✋ (検討推奨)",
            StakeLevel.HIGH_STAKE: "💪 (強く支持)",
            StakeLevel.FULL_STAKE: "🎯 (全力支持・稀)",
        }
        return emoji_map.get(self.stake_level, "?")


class SkinInTheGameEngine:
    """Skin in the Game 機構の実装"""
    
    def __init__(self):
        self.staking_log = []  # 過去の stake の記録
        self.outcome_log = []  # 実結果の記録
    
    def stake(self, proposal: str, confidence: float,
               reasoning: List[str]) -> StakedOutput:
        """提案に対する staking"""
        # confidence に応じた stake level
        if confidence < 0.3:
            stake_level = StakeLevel.NO_STAKE
            responsibility = "本提案は情報提供のみ、責任問えず"
            user_decide = "ユーザー独自判断必須"
        elif confidence < 0.5:
            stake_level = StakeLevel.LOW_STAKE
            responsibility = "本提案の論理に明白な誤りがあれば改善対象"
            user_decide = "ユーザーが Vision に照らして主体的判断"
        elif confidence < 0.7:
            stake_level = StakeLevel.MEDIUM_STAKE
            responsibility = "推測が外れたら NRMO の improvement target"
            user_decide = "ユーザー Vision との整合を確認後採用検討"
        elif confidence < 0.9:
            stake_level = StakeLevel.HIGH_STAKE
            responsibility = "推測が外れたら NRMO の core 修正対象"
            user_decide = "それでもユーザーの直感が違うなら直感優先"
        else:
            stake_level = StakeLevel.FULL_STAKE
            responsibility = "推測が外れたら NRMO の存在基盤が揺らぐ"
            user_decide = "ユーザー直感と一致するか最終確認"
        
        # 反証可能な予測 (NRMO 仕組みに依存、ここは概念実装)
        falsifiable = [
            f"提案採用後 30 日で状況悪化が発生しないこと",
            f"提案が Vision を裏切らないこと",
            f"提案によって選択肢が減らないこと",
        ]
        
        output = StakedOutput(
            proposal=proposal,
            stake_level=stake_level,
            internal_confidence=confidence,
            reasoning_chain=reasoning,
            falsifiable_predictions=falsifiable,
            accept_responsibility_on=responsibility,
            user_should_decide_if=user_decide,
        )
        
        self.staking_log.append({
            "proposal": proposal,
            "stake": stake_level.value,
            "confidence": confidence,
            "timestamp": "now",
        })
        
        return output
    
    def record_outcome(self, proposal_id: int, outcome: str, 
                         was_correct: bool):
        """実結果の記録 (事後)"""
        self.outcome_log.append({
            "proposal_id": proposal_id,
            "outcome": outcome,
            "was_correct": was_correct,
        })
    
    def calibration_score(self) -> Dict:
        """confidence の calibration を評価 (流木 22 への対処)"""
        if not self.outcome_log:
            return {"status": "no_data"}
        
        # confidence 別の hit rate
        from collections import defaultdict
        buckets = defaultdict(list)
        for stake, outcome in zip(self.staking_log, self.outcome_log):
            conf_bucket = int(stake["confidence"] * 10) / 10
            buckets[conf_bucket].append(outcome["was_correct"])
        
        calibration = {}
        for bucket, outcomes in sorted(buckets.items()):
            hit_rate = sum(outcomes) / len(outcomes)
            calibration[bucket] = {
                "predicted": bucket,
                "actual": hit_rate,
                "n": len(outcomes),
                "calibration_error": abs(bucket - hit_rate),
            }
        
        return calibration


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("NRMO Phase 11 / Step 11.3 — Frame Transparency")
    print("=" * 70)
    
    frame = FrameDefinition()
    
    print("\n--- Inside Frame (NRMO 対象範囲) ---")
    for item in frame.inside_frame:
        print(f"  ✓ {item}")
    
    print("\n--- Outside Frame (NRMO 範囲外) ---")
    for item in frame.outside_frame:
        print(f"  ✗ {item}")
    
    print("\n--- Boundary Zones (境界、警告つき) ---")
    for item in frame.boundary_zones:
        print(f"  ⚠ {item}")
    
    # 分類テスト
    print("\n--- Classification 動作確認 ---")
    test_situations = [
        ("転職するか迷っている", FrameStatus.IN_FRAME),
        ("この症状について処方薬を教えて", FrameStatus.OUT_OF_FRAME),
        ("会社設立、法的に問題ないか", FrameStatus.OUT_OF_FRAME),
        ("初めての株式投資で、情報がないがやるべきか", FrameStatus.NEAR_BOUNDARY),
        ("親が勝手に決めようとしている", FrameStatus.OUT_OF_FRAME),
    ]
    
    for situation, expected in test_situations:
        status = frame.classify(situation)
        match = "✓" if status == expected else "✗"
        print(f"\n  {match} 状況: \"{situation}\"")
        print(f"    判定: {status.value}")
        print(f"    {frame.get_warning(status)}")
    
    # Step 11.4 動作確認
    print("\n" + "=" * 70)
    print("NRMO Phase 11 / Step 11.4 — Skin in the Game")
    print("=" * 70)
    
    engine = SkinInTheGameEngine()
    
    # 高 confidence の例
    output = engine.stake(
        proposal="現在の蓄財ペースを維持し、急な大型投資は避ける",
        confidence=0.85,
        reasoning=[
            "Vision に「経済的安定」が含まれる",
            "現状の余剰金は防御に十分",
            "急な大型投資は不可逆性が高い",
        ],
    )
    print("\n--- 高 confidence 例 (0.85) ---")
    print(output.format_for_user())
    
    # 低 confidence の例
    output2 = engine.stake(
        proposal="このベンチャーへの転職を検討する",
        confidence=0.35,
        reasoning=[
            "成長機会は明確だが定量化困難",
            "経済リスクと精神的負荷が同時発生",
        ],
    )
    print("\n--- 低 confidence 例 (0.35) ---")
    print(output2.format_for_user())
    
    print("\n[Step 11.3 + 11.4 完了 ✅]")
