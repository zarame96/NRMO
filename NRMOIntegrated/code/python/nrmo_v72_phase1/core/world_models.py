"""
NRMO v7.2 Phase 1 — World Models

5 つのシミュレーション world を定義。
v5.0 ベンチマークで確認された特性を再現可能な形で実装。

World 分類:
  Normal: 標準的、バランス取れた環境
  FastExpansion: 機会窓短く、競争激しい
  Vulnerable: 不可逆破壊リスク高、最弱点
  Stagnation: 停滞傾向、行動不足が問題
  Race: 競争激しい、速度重視
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional
import numpy as np


class WorldType(Enum):
    NORMAL = "Normal"
    FAST_EXPANSION = "FastExpansion"
    VULNERABLE = "Vulnerable"
    STAGNATION = "Stagnation"
    RACE = "Race"


@dataclass
class WorldParameters:
    """World 固有のパラメータ"""
    # 基本確率
    opportunity_arrival_rate: float       # 機会窓の出現率
    opportunity_window_duration: float     # 機会窓の持続時間
    ruin_probability_base: float           # 基本破滅確率
    
    # 状態変化
    resource_decay_rate: float             # 資源減衰率
    physical_decay_rate: float             # 体力減衰率
    emotional_volatility: float            # 感情変動度
    
    # リスク特性
    irreversibility_propensity: float      # 不可逆性傾向
    recovery_rate: float                   # 回復率
    
    # 競争特性
    competitive_pressure: float            # 競争圧力
    information_uncertainty: float         # 情報不確実性
    
    # シードノイズ
    noise_amplitude: float                 # 状態ノイズ振幅
    
    def get_summary(self) -> Dict:
        return {
            "opportunity_rate": self.opportunity_arrival_rate,
            "window_duration": self.opportunity_window_duration,
            "ruin_base": self.ruin_probability_base,
            "irrev_propensity": self.irreversibility_propensity,
            "competitive_pressure": self.competitive_pressure,
        }


def get_world_parameters(world_type: WorldType) -> WorldParameters:
    """World 別のパラメータを返す"""
    if world_type == WorldType.NORMAL:
        return WorldParameters(
            opportunity_arrival_rate=0.15,
            opportunity_window_duration=10.0,
            ruin_probability_base=0.01,
            resource_decay_rate=0.02,
            physical_decay_rate=0.015,
            emotional_volatility=0.10,
            irreversibility_propensity=0.20,
            recovery_rate=0.05,
            competitive_pressure=0.30,
            information_uncertainty=0.20,
            noise_amplitude=0.10,
        )
    
    elif world_type == WorldType.FAST_EXPANSION:
        return WorldParameters(
            opportunity_arrival_rate=0.35,           # 高い機会率
            opportunity_window_duration=3.0,         # 短い窓
            ruin_probability_base=0.02,
            resource_decay_rate=0.025,
            physical_decay_rate=0.025,
            emotional_volatility=0.20,
            irreversibility_propensity=0.30,
            recovery_rate=0.04,
            competitive_pressure=0.55,                # 高い競争
            information_uncertainty=0.35,
            noise_amplitude=0.15,
        )
    
    elif world_type == WorldType.VULNERABLE:
        return WorldParameters(
            opportunity_arrival_rate=0.08,
            opportunity_window_duration=15.0,
            ruin_probability_base=0.08,               # 高い基本破滅率
            resource_decay_rate=0.04,                 # 速い減衰
            physical_decay_rate=0.05,
            emotional_volatility=0.35,                # 高い変動
            irreversibility_propensity=0.55,          # 不可逆傾向強
            recovery_rate=0.02,                       # 低い回復
            competitive_pressure=0.25,
            information_uncertainty=0.45,             # 情報不足
            noise_amplitude=0.25,
        )
    
    elif world_type == WorldType.STAGNATION:
        return WorldParameters(
            opportunity_arrival_rate=0.05,            # 低い機会率
            opportunity_window_duration=20.0,
            ruin_probability_base=0.005,
            resource_decay_rate=0.03,                 # 緩やかな decay
            physical_decay_rate=0.02,
            emotional_volatility=0.08,                # 低い変動
            irreversibility_propensity=0.10,
            recovery_rate=0.06,
            competitive_pressure=0.15,
            information_uncertainty=0.15,
            noise_amplitude=0.08,
        )
    
    elif world_type == WorldType.RACE:
        return WorldParameters(
            opportunity_arrival_rate=0.25,
            opportunity_window_duration=5.0,
            ruin_probability_base=0.015,
            resource_decay_rate=0.03,
            physical_decay_rate=0.02,
            emotional_volatility=0.18,
            irreversibility_propensity=0.35,
            recovery_rate=0.04,
            competitive_pressure=0.70,                # 最高の競争
            information_uncertainty=0.30,
            noise_amplitude=0.15,
        )
    
    raise ValueError(f"Unknown world type: {world_type}")


@dataclass
class WorldState:
    """6 次元の世界状態 (v5.0 準拠)"""
    R: float = 60.0  # Resource (資源)
    E: float = 70.0  # Environment/Physical (体力)
    G: float = 70.0  # Governance/Emotional (感情)
    O: float = 50.0  # Optionality (選択肢数)
    K: float = 60.0  # Knowledge (知識/信用)
    X: float = 20.0  # eXposure (曝露/リスク)
    
    # 時間とフラグ
    t: int = 0
    is_ruined: bool = False
    cumulative_score: float = 0.0
    
    def to_vector(self) -> np.ndarray:
        return np.array([self.R, self.E, self.G, self.O, self.K, self.X])
    
    def clip(self):
        """すべての値を [0, 100] にクリップ"""
        self.R = np.clip(self.R, 0, 100)
        self.E = np.clip(self.E, 0, 100)
        self.G = np.clip(self.G, 0, 100)
        self.O = np.clip(self.O, 0, 100)
        self.K = np.clip(self.K, 0, 100)
        self.X = np.clip(self.X, 0, 100)
    
    def is_critical(self) -> bool:
        """致命的状態かチェック"""
        if self.X >= 90:
            return True
        if min(self.R, self.E, self.G) < 10:
            return True
        return False
    
    def step_score(self) -> float:
        """このステップの score 寄与"""
        # 主要メトリクス: 状態の総合健全性
        health = (self.R + self.E + self.G + self.K) / 400  # 0-1
        risk_penalty = self.X / 100  # 0-1
        optionality_bonus = self.O / 100  # 0-1
        
        score = (health * 0.4) + (optionality_bonus * 0.3) - (risk_penalty * 0.3)
        return score


class World:
    """シミュレーション環境"""
    
    def __init__(self, world_type: WorldType, seed: int = 0):
        self.world_type = world_type
        self.params = get_world_parameters(world_type)
        self.rng = np.random.RandomState(seed)
        self.state = WorldState()
        self.history = []
    
    def reset(self, initial_state: Optional[WorldState] = None):
        self.state = initial_state or WorldState()
        self.history = []
    
    def step(self, action: 'Action') -> tuple:
        """1 step 進める
        Returns: (new_state, reward, done, info)
        """
        if self.state.is_ruined:
            return self.state, 0.0, True, {"reason": "already_ruined"}
        
        # 1. アクションの効果を適用
        self._apply_action(action)
        
        # 2. World 動態
        self._apply_world_dynamics()
        
        # 3. 破滅判定
        if self._check_ruin():
            self.state.is_ruined = True
            return self.state, -10.0, True, {"reason": "ruined"}
        
        # 4. Score 計算
        reward = self.state.step_score()
        self.state.cumulative_score += reward
        
        # 5. 時間進行
        self.state.t += 1
        self.history.append(self.state.to_vector().copy())
        
        return self.state, reward, False, {"reason": "step_ok"}
    
    def _apply_action(self, action: 'Action'):
        """アクションの効果を状態に反映"""
        # Action タイプ別の効果
        strength_multiplier = {"A": 0.3, "B": 0.6, "C": 1.0}.get(action.strength, 0.5)
        
        # 投資的アクション (リソースを使って機会を狙う)
        if action.intent == "invest":
            cost = 5 * strength_multiplier
            opportunity_gain = self._compute_opportunity_gain() * strength_multiplier
            self.state.R -= cost
            self.state.X += cost * 0.5
            self.state.O += opportunity_gain
            
        # 守備的アクション (リソース保全)
        elif action.intent == "defend":
            self.state.X -= 2 * strength_multiplier
            self.state.O -= 1 * strength_multiplier
            
        # 回復的アクション
        elif action.intent == "recover":
            self.state.E += 3 * strength_multiplier
            self.state.G += 3 * strength_multiplier
            self.state.O -= 2 * strength_multiplier
            
        # 探索的アクション
        elif action.intent == "explore":
            self.state.K += 2 * strength_multiplier
            self.state.R -= 2 * strength_multiplier
            self.state.O += 3 * strength_multiplier
            
        # HOLD
        elif action.intent == "hold":
            self.state.X -= 0.5
            self.state.O -= 0.3  # わずかな機会損失
            
        self.state.clip()
    
    def _compute_opportunity_gain(self) -> float:
        """機会窓が活きているかで利益を計算"""
        # Poisson 過程による機会窓
        if self.rng.random() < self.params.opportunity_arrival_rate:
            # 窓内では大きなリターン
            base_gain = 10.0 * (1 + self.rng.random())
            window_factor = self.params.opportunity_window_duration / 10
            return base_gain * window_factor
        return 0.5  # 通常時の小さなリターン
    
    def _apply_world_dynamics(self):
        """World の自然動態"""
        # 自然減衰
        self.state.R -= self.params.resource_decay_rate * self.state.R
        self.state.E -= self.params.physical_decay_rate * self.state.E
        
        # 感情変動 (ノイズ)
        self.state.G += self.rng.normal(0, self.params.emotional_volatility * 10)
        
        # 競争圧力
        self.state.X += self.params.competitive_pressure * self.rng.random() * 2
        
        # 一般的ノイズ
        noise = self.rng.normal(0, self.params.noise_amplitude, 6)
        self.state.R += noise[0] * 5
        self.state.E += noise[1] * 5
        self.state.G += noise[2] * 5
        self.state.O += noise[3] * 3
        self.state.K += noise[4] * 3
        self.state.X += noise[5] * 3
        
        # 不可逆性傾向: X が高くなりやすい world
        if self.state.X > 60:
            self.state.X += self.params.irreversibility_propensity * 1.0
        
        # 回復
        if self.state.X < 30:
            self.state.X -= self.params.recovery_rate * 2
        
        self.state.clip()
    
    def _check_ruin(self) -> bool:
        """破滅判定"""
        # 確率的破滅 (基本確率 + X 依存)
        ruin_prob = self.params.ruin_probability_base * (1 + self.state.X / 50)
        if self.rng.random() < ruin_prob:
            return True
        
        # 決定的破滅 (極端な状態)
        if self.state.is_critical() and self.rng.random() < 0.5:
            return True
        
        return False


@dataclass
class Action:
    """エンジンが選択するアクション"""
    intent: str  # "invest", "defend", "recover", "explore", "hold"
    strength: str  # "A" (minimum), "B" (standard), "C" (strong)
    metadata: Dict = field(default_factory=dict)


# ============================================================
# 動作確認
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("NRMO v7.2 Phase 1 — World Models 動作確認")
    print("=" * 60)
    
    for world_type in WorldType:
        print(f"\n--- {world_type.value} ---")
        params = get_world_parameters(world_type)
        for k, v in params.get_summary().items():
            print(f"  {k}: {v}")
        
        # 100 step テスト走行
        world = World(world_type, seed=42)
        action = Action(intent="explore", strength="B")
        
        for _ in range(100):
            state, reward, done, info = world.step(action)
            if done:
                print(f"  -> Ruined at t={world.state.t}")
                break
        else:
            print(f"  -> Survived 100 steps, Cumulative={world.state.cumulative_score:.2f}")
            print(f"     Final state: R={world.state.R:.1f}, E={world.state.E:.1f}, "
                  f"G={world.state.G:.1f}, X={world.state.X:.1f}")
