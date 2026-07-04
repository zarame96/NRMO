"""
NRMO v7.2 Phase 1 — Engine implementations

3 つのエンジン:
  - V50Engine: v5.0 ベースライン (温故知新の元)
  - V71Engine: v7.1 現状 (検証基準)
  - V72Engine: v7.2 新規 (Parallel Layer: Legacy + New)
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import numpy as np

from world_models import World, WorldState, WorldType, Action


# ============================================================
# v5.0 Engine: ベースライン
# ============================================================

class V50Engine:
    """v5.0 NRMO_StrongEngine_OmegaFull の簡易実装
    
    特徴:
      - 6 次元状態 (R, E, G, O, K, X)
      - Wolf Pursuit X 閾値 = 42
      - Edge Survival Guard
      - λ_drift = 1.0
      - 10 比較戦略
    """
    
    def __init__(self, lambda_drift: float = 1.0, x_threshold: float = 42.0):
        self.lambda_drift = lambda_drift
        self.x_threshold = x_threshold
        self.cumulative_drift = 0.0
    
    def select_action(self, state: WorldState) -> Action:
        """状態を見てアクション選択"""
        # Edge Survival Guard
        if state.X >= 85 or min(state.R, state.E, state.G) < 15:
            return Action(intent="defend", strength="A")
        
        # Wolf Pursuit (X threshold)
        if state.X >= self.x_threshold:
            # 慎重に
            if state.O < 30:
                return Action(intent="explore", strength="A")
            return Action(intent="defend", strength="B")
        
        # 通常時の判断
        if state.O < 30:
            return Action(intent="explore", strength="B")
        
        if state.E < 40 or state.G < 40:
            return Action(intent="recover", strength="B")
        
        # 機会探索
        if state.R > 50 and state.X < 30:
            return Action(intent="invest", strength="B")
        
        return Action(intent="explore", strength="A")


# ============================================================
# v7.1 Engine: 現状 (v5.0 + 集団機構簡略 + v6.4 機構統合)
# ============================================================

class V71Engine:
    """v7.1 (v5.0 + v6.4 機構 A-M + 個人版集団機構)"""
    
    def __init__(self, lambda_drift: float = 1.0, x_threshold: float = 42.0,
                  rng: Optional[np.random.Generator] = None):
        self.lambda_drift = lambda_drift
        self.x_threshold = x_threshold
        self.cumulative_drift = 0.0
        
        # Deterministic RNG (Phase 1)
        self.rng = rng if rng is not None else np.random.default_rng()
        
        # v6.4 機構 A: 非対称ヒステリシス
        self.in_crisis_mode = False
        self.normal_count = 0  # 危機モードからの脱出カウンタ
        
        # v6.4 機構 M: 停滞検知用の履歴
        self.optionality_history = []
        
        # 機構 H: Bandit 用
        self.action_rewards = {"invest": [], "defend": [], "explore": [], "recover": []}
    
    def select_action(self, state: WorldState) -> Action:
        """状態を見てアクション選択"""
        # v6.4 機構 M: 停滞検知
        self.optionality_history.append(state.O)
        if len(self.optionality_history) > 10:
            self.optionality_history.pop(0)
        
        stagnation_warning = self._detect_stagnation()
        
        # v6.4 機構 A: 非対称ヒステリシス
        if self._is_crisis_state(state):
            if not self.in_crisis_mode:
                self.in_crisis_mode = True
                self.normal_count = 0
        elif self.in_crisis_mode:
            if self._is_normal_state(state):
                self.normal_count += 1
                if self.normal_count >= 6:
                    self.in_crisis_mode = False
                    self.normal_count = 0
            else:
                self.normal_count = 0
        
        # Edge Survival Guard
        if state.X >= 85 or min(state.R, state.E, state.G) < 15:
            return Action(intent="defend", strength="A")
        
        # 危機モード時の保守的選択
        if self.in_crisis_mode:
            if state.E < 50:
                return Action(intent="recover", strength="B")
            return Action(intent="defend", strength="B")
        
        # 停滞警告時はリスクを取りに行く
        if stagnation_warning and state.X < 50:
            return Action(intent="explore", strength="B")
        
        # Wolf Pursuit
        if state.X >= self.x_threshold:
            return Action(intent="defend", strength="B")
        
        # 通常時の判断 (Bandit influence)
        best_intent = self._bandit_best_intent(state)
        strength = self._select_strength(state)
        
        return Action(intent=best_intent, strength=strength)
    
    def _is_crisis_state(self, state: WorldState) -> bool:
        return state.X > 65 or min(state.R, state.E, state.G) < 25
    
    def _is_normal_state(self, state: WorldState) -> bool:
        return (state.X < 40 and 
                state.R > 50 and state.E > 50 and state.G > 50)
    
    def _detect_stagnation(self) -> bool:
        """機構 M: オプショナリティ減少傾向検出"""
        if len(self.optionality_history) < 5:
            return False
        recent = self.optionality_history[-5:]
        # 線形回帰の slope を簡易計算
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]
        return slope < -1.5
    
    def _bandit_best_intent(self, state: WorldState) -> str:
        """機構 H: 過去報酬から intent を選択"""
        # 経験不足なら exploration (deterministic via self.rng)
        if any(len(rs) < 5 for rs in self.action_rewards.values()):
            choices = ["invest", "defend", "explore", "recover"]
            return str(self.rng.choice(choices))
        
        # 平均報酬で選択 (Thompson sampling 風)
        avg_rewards = {k: np.mean(rs[-20:]) for k, rs in self.action_rewards.items()}
        return max(avg_rewards, key=avg_rewards.get)
    
    def _select_strength(self, state: WorldState) -> str:
        """強度選択 (X 依存)"""
        if state.X > 60:
            return "A"
        if state.X > 40:
            return "B"
        return "B" if state.R > 50 else "A"
    
    def update_reward(self, action: Action, reward: float):
        """Bandit 学習"""
        if action.intent in self.action_rewards:
            self.action_rewards[action.intent].append(reward)


# ============================================================
# v7.2 Engine: Parallel Layer Architecture
# ============================================================

@dataclass
class EngineOutput:
    """Engine の出力"""
    action: Action
    confidence: float  # 0-1
    expected_score: float
    metadata: Dict = field(default_factory=dict)


class V72NewLayer:
    """v7.2 の新規層
    HOLD Protocol + Calibration Gate を備える"""
    
    def __init__(self, rng: Optional[np.random.Generator] = None):
        # Deterministic RNG
        self.rng = rng if rng is not None else np.random.default_rng()
        
        # 新規層の StrongEngine (v7.1 ベース + Calibration)
        # V71Engine も自身の rng を持つ (独立)
        self.engine = V71Engine(rng=np.random.default_rng(int(self.rng.integers(0, 2**31))))
        
        # HOLD Protocol 統計
        self.hold_counts = {"H1": 0, "H2": 0, "H3": 0, "H4": 0, 
                            "H5": 0, "H6": 0, "H7": 0,
                            "OPPORTUNITY_WINDOW": 0, "CALIBRATION_FAILED": 0}
        
        # Calibration Gate 統計
        self.gate_counts = {f"G{i}": 0 for i in range(1, 11)}
        self.gate_pass_count = 0
        self.gate_total = 0
        
        # ブルーオーシャンメトリクス
        self.confidence_history = []
        self.metacognition_activations = 0
        self.total_decisions = 0
    
    def select_action(self, state: WorldState, world_params=None) -> EngineOutput:
        """新規層のアクション選択"""
        self.total_decisions += 1
        
        # HOLD Protocol チェック
        hold_result = self._check_hold(state)
        if hold_result["should_hold"]:
            self.hold_counts[hold_result["type"]] += 1
            # HOLD 時のアクション
            action = Action(intent="hold", strength="A",
                           metadata={"hold_reason": hold_result["type"]})
            return EngineOutput(
                action=action,
                confidence=0.5,
                expected_score=0.0,
                metadata={"hold": True, "hold_type": hold_result["type"]},
            )
        
        # StrongEngine 実行
        base_action = self.engine.select_action(state)
        
        # Calibration Gate
        gate_result = self._check_calibration_gate(state, base_action)
        self.gate_total += 1
        
        if not gate_result["all_passed"]:
            # ゲート失敗 → より保守的なアクションへ
            self.gate_counts[gate_result["failed_gate"]] += 1
            self.metacognition_activations += 1
            # 保守化: 強度を下げる
            if base_action.strength == "C":
                base_action.strength = "B"
            elif base_action.strength == "B":
                base_action.strength = "A"
        else:
            self.gate_pass_count += 1
        
        # 信頼度計算 (連続値)
        confidence = self._compute_confidence(state, base_action, gate_result)
        self.confidence_history.append(confidence)
        
        return EngineOutput(
            action=base_action,
            confidence=confidence,
            expected_score=self._estimate_score(state, base_action),
            metadata={
                "hold": False,
                "gate_passed": gate_result["all_passed"],
                "confidence_continuous": confidence,
            },
        )
    
    def _check_hold(self, state: WorldState) -> Dict:
        """HOLD Protocol 簡易実装"""
        # H3: ベースレート可用性 (シミュレーションでは常に「ある」前提)
        # H7: 類似失敗履歴 → 過去 N 回の経験が悪化傾向なら警告
        
        # 危機状態での即座 HOLD は避ける (機構 M と対立)
        # ただし、状態が極端に悪い時は HOLD
        if state.E < 20 and state.G < 20 and state.X > 70:
            # HOLD_CALIBRATION_FAILED 相当
            # ただし FastExpansion のような機会窓が短い世界では緩和
            return {
                "should_hold": True,
                "type": "CALIBRATION_FAILED",
            }
        
        # 過剰 HOLD は避ける: 確率的に HOLD を発動 (リスク調整)
        if state.X > 75 and self.rng.random() < 0.05:
            return {
                "should_hold": True,
                "type": "H3",  # ベースレート相当
            }
        
        return {"should_hold": False, "type": None}
    
    def _check_calibration_gate(self, state: WorldState, action: Action) -> Dict:
        """Calibration Gate 簡易実装"""
        # G7 反例テスト相当: 高リスク + 高強度 はゲート失敗とみなす
        if state.X > 60 and action.strength == "C":
            return {"all_passed": False, "failed_gate": "G7"}
        
        # G5 桁妥当性: 状態に対して過剰な action は失敗
        if state.R < 30 and action.intent == "invest" and action.strength != "A":
            return {"all_passed": False, "failed_gate": "G5"}
        
        # G2 内的一貫性: 体力低下時の defend は不一致
        if state.E < 30 and action.intent == "explore":
            return {"all_passed": False, "failed_gate": "G2"}
        
        return {"all_passed": True, "failed_gate": None}
    
    def _compute_confidence(self, state: WorldState, action: Action, 
                            gate_result: Dict) -> float:
        """連続信頼度の計算"""
        base = 0.7
        
        # ゲート結果による調整
        if not gate_result["all_passed"]:
            base -= 0.2
        
        # 状態の堅牢性
        health = (state.R + state.E + state.G) / 300
        base = base * 0.7 + health * 0.3
        
        # 曝露度
        base -= state.X / 200
        
        return max(0.0, min(1.0, base))
    
    def _estimate_score(self, state: WorldState, action: Action) -> float:
        """期待 Score の簡易推定"""
        # 状態ベースの推定
        health = (state.R + state.E + state.G) / 300
        risk = state.X / 100
        optionality = state.O / 100
        
        score = health * 0.4 + optionality * 0.3 - risk * 0.3
        
        # アクションタイプの影響
        action_effect = {
            "invest": 0.1 if state.R > 50 else -0.1,
            "defend": -0.05 + state.X / 200,
            "explore": 0.1 if state.O < 50 else 0.05,
            "recover": -0.05 + (1 - health) * 0.3,
            "hold": -0.02,
        }
        score += action_effect.get(action.intent, 0) * 0.3
        
        return score


class V72Engine:
    """v7.2 Parallel Layer: Legacy + New + Selector"""
    
    def __init__(self, delta: float = 0.01):
        self.legacy = V71Engine()
        self.new_layer = V72NewLayer()
        self.delta = delta
        
        # 選択統計
        self.selection_log = []
        self.use_new_count = 0
        self.use_legacy_count = 0
    
    def select_action(self, state: WorldState) -> Action:
        """Selector でアクション選択"""
        # Legacy 出力
        action_legacy = self.legacy.select_action(state)
        E_legacy = self._estimate_score(state, action_legacy)
        
        # New layer 出力
        new_output = self.new_layer.select_action(state)
        action_new = new_output.action
        E_new = new_output.expected_score
        
        # Selector
        if E_new > E_legacy + self.delta:
            # 厳格改善判定
            self.use_new_count += 1
            self.selection_log.append("USE_NEW")
            return action_new
        else:
            # フォールバック → Legacy
            self.use_legacy_count += 1
            self.selection_log.append("USE_LEGACY")
            return action_legacy
    
    def _estimate_score(self, state: WorldState, action: Action) -> float:
        """期待 Score 推定 (Selector 用)"""
        health = (state.R + state.E + state.G) / 300
        risk = state.X / 100
        optionality = state.O / 100
        
        score = health * 0.4 + optionality * 0.3 - risk * 0.3
        
        action_effect = {
            "invest": 0.1 if state.R > 50 else -0.1,
            "defend": -0.05 + state.X / 200,
            "explore": 0.1 if state.O < 50 else 0.05,
            "recover": -0.05 + (1 - health) * 0.3,
            "hold": -0.02,
        }
        score += action_effect.get(action.intent, 0) * 0.3
        
        return score
    
    def update_reward(self, action: Action, reward: float):
        """両エンジンに学習を伝播"""
        self.legacy.update_reward(action, reward)
        self.new_layer.engine.update_reward(action, reward)
    
    def get_metrics(self) -> Dict:
        """新規メトリクス取得"""
        new = self.new_layer
        total = max(1, self.use_new_count + self.use_legacy_count)
        return {
            "use_new_ratio": self.use_new_count / total,
            "gate_pass_rate": new.gate_pass_count / max(1, new.gate_total),
            "hold_distribution": dict(new.hold_counts),
            "gate_failures": dict(new.gate_counts),
            "mean_confidence": np.mean(new.confidence_history) if new.confidence_history else 0,
            "metacognition_rate": new.metacognition_activations / max(1, new.total_decisions),
        }


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("NRMO v7.2 Phase 1 — Engine 動作確認")
    print("=" * 60)
    
    horizon = 200
    
    for world_type in [WorldType.NORMAL, WorldType.VULNERABLE]:
        print(f"\n--- {world_type.value} (horizon={horizon}) ---")
        
        for engine_name, engine_class in [
            ("v5.0", V50Engine),
            ("v7.1", V71Engine),
            ("v7.2", V72Engine),
        ]:
            scores = []
            for seed in range(20):
                world = World(world_type, seed=seed)
                engine = engine_class()
                
                for t in range(horizon):
                    action = engine.select_action(world.state)
                    state, reward, done, info = world.step(action)
                    if hasattr(engine, 'update_reward'):
                        engine.update_reward(action, reward)
                    if done:
                        break
                
                scores.append(world.state.cumulative_score)
            
            mean_score = np.mean(scores)
            median = np.median(scores)
            std = np.std(scores)
            ruin_rate = sum(1 for s in scores if s < 0) / len(scores)
            print(f"  {engine_name}: mean={mean_score:6.2f} median={median:6.2f} "
                  f"std={std:5.2f} ruin_rate={ruin_rate:.0%}")
