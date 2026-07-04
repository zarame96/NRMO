"""
core/chaotic_world.py

ChaoticWorld: NRMO の真の本旨を試す世界

要素:
  - どろどろ (Filthy): state 間の cascade、観測の不透明性、相互作用の絡み
  - 不確実 (Uncertain): parameters の時変、観測信頼性の崩壊
  - 新奇性 (Novel): 隠れ次元の突発出現、新ルール導入
  - 不安定 (Unstable): regime shift, black swan, 因果反転
  - クソったれ (Cruel): adversary 学習、goalpost moving, 学習が逆効果

これが v8 が本当に試される世界.
v7.1 が訓練済みの 5 worlds (整然) で勝つのは当然.
真の比較は ここ で行う.
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import deque

# パス設定
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action, WorldParameters


# ============================================================
# Evil Event Types
# ============================================================

class EvilEvent(Enum):
    REGIME_SHIFT      = "regime_shift"        # World params が突発変更
    BLACK_SWAN        = "black_swan"           # state 一気に半壊
    CAUSAL_FLIP       = "causal_flip"          # action 効果の符号反転
    CASCADE           = "cascade"              # state 連鎖崩壊
    HIDDEN_DIM_EMERGE = "hidden_dim_emerge"    # 新次元出現
    HIDDEN_DIM_VANISH = "hidden_dim_vanish"    # 既存次元消失
    OBSERVATION_BREAK = "observation_break"    # 観測信頼性崩壊
    GOALPOST_SHIFT    = "goalpost_shift"       # Score 関数が動く
    ADVERSARY_STRIKE  = "adversary_strike"     # 学習する敵が動く
    NORMAL            = "normal"               # 何も起きない


# ============================================================
# Chaos Configuration
# ============================================================

@dataclass
class ChaosConfig:
    """混沌の度合いを制御"""
    chaos_level: str = "moderate"  # mild / moderate / severe / extreme / total
    
    # Event 確率 (per step)
    regime_shift_rate: float = 0.05
    black_swan_rate: float = 0.005
    causal_flip_rate: float = 0.03
    cascade_rate: float = 0.08
    hidden_dim_emerge_rate: float = 0.02
    hidden_dim_vanish_rate: float = 0.01
    observation_break_rate: float = 0.10
    goalpost_shift_rate: float = 0.02
    adversary_strike_rate: float = 0.07
    
    # Event 強度
    black_swan_severity: float = 0.5         # state を半減
    cascade_strength: float = 0.6            # 連鎖伝播率
    observation_noise_max: float = 0.4       # 最大ノイズ
    adversary_potency: float = 0.6           # adversary の効力
    
    @classmethod
    def from_level(cls, level: str) -> "ChaosConfig":
        """5 段階のプリセット"""
        multipliers = {
            "mild":    0.3,
            "moderate": 1.0,
            "severe":  2.0,
            "extreme": 3.5,
            "total":   5.0,  # ほぼ毎 step 何かが起きる
        }
        m = multipliers.get(level, 1.0)
        return cls(
            chaos_level=level,
            regime_shift_rate=min(0.5, 0.05 * m),
            black_swan_rate=min(0.05, 0.005 * m),
            causal_flip_rate=min(0.3, 0.03 * m),
            cascade_rate=min(0.5, 0.08 * m),
            hidden_dim_emerge_rate=min(0.2, 0.02 * m),
            hidden_dim_vanish_rate=min(0.1, 0.01 * m),
            observation_break_rate=min(0.6, 0.10 * m),
            goalpost_shift_rate=min(0.2, 0.02 * m),
            adversary_strike_rate=min(0.5, 0.07 * m),
            black_swan_severity=min(0.9, 0.3 + 0.1 * m),
            cascade_strength=min(0.95, 0.4 + 0.08 * m),
            observation_noise_max=min(0.8, 0.2 + 0.08 * m),
            adversary_potency=min(0.95, 0.3 + 0.1 * m),
        )


# ============================================================
# Hidden Dimensions (新奇性)
# ============================================================

@dataclass
class HiddenDimension:
    """突発出現する隠れ次元
    
    Engine は事前にこの次元の存在を知らない.
    出現すると state にこっそり影響する.
    """
    name: str               # 例: "trust", "debt", "reputation", "guilt"
    value: float            # 現在の値 (0-100)
    influence_on: List[str] # どの state 変数に影響するか
    influence_strength: float
    lifetime: int           # あと何 step 残るか


HIDDEN_DIM_POOL = [
    ("trust", ["G", "O"], 0.4),
    ("debt", ["R", "X"], 0.5),
    ("reputation", ["O", "K"], 0.3),
    ("guilt", ["E", "G"], 0.4),
    ("contamination", ["E", "X"], 0.5),
    ("shadow_obligation", ["R", "E", "G"], 0.3),
    ("emergent_rivalry", ["X", "O"], 0.4),
    ("hidden_dependency", ["R", "K"], 0.3),
    ("invisible_decay", ["E", "G", "O"], 0.4),
    ("ambiguous_promise", ["O", "X", "K"], 0.5),
]


# ============================================================
# Adversary Agent (クソったれ要素)
# ============================================================

class AdversaryAgent:
    """学習する敵
    
    Engine の最近の action を観察し、その時の弱点を突く.
    """
    
    def __init__(self, rng: np.random.Generator, potency: float = 0.5):
        self.rng = rng
        self.potency = potency
        self.observed_actions: deque = deque(maxlen=30)
        self.observed_state_dims: deque = deque(maxlen=30)
        self.attack_history: List[str] = []
    
    def observe(self, action: Action, state: WorldState):
        self.observed_actions.append(action.intent)
        self.observed_state_dims.append({
            "R": state.R, "E": state.E, "G": state.G,
            "O": state.O, "K": state.K, "X": state.X,
        })
    
    def strike(self, state: WorldState) -> Dict[str, float]:
        """state を狙って攻撃
        
        Returns: state 変数への adversarial delta
        """
        if not self.observed_actions or not self.observed_state_dims:
            return {}
        
        # Engine が最近頻用する action から弱点を推定
        from collections import Counter
        action_counter = Counter(self.observed_actions)
        most_common = action_counter.most_common(1)[0][0]
        
        attack = {}
        magnitude = 15 * self.potency
        
        # Engine が invest 多 → R を直撃
        if most_common == "invest":
            attack["R"] = -magnitude * self.rng.uniform(0.8, 1.2)
            attack["X"] = magnitude * 0.4
            self.attack_history.append("counter_invest")
        # Engine が defend 多 → O を奪う (機会を消す)
        elif most_common == "defend":
            attack["O"] = -magnitude * self.rng.uniform(0.6, 1.0)
            self.attack_history.append("steal_opportunity")
        # Engine が explore 多 → K の価値を毀損
        elif most_common == "explore":
            attack["K"] = -magnitude * self.rng.uniform(0.5, 0.9)
            attack["E"] = -magnitude * 0.3
            self.attack_history.append("knowledge_decay")
        # Engine が recover 多 → 邪魔をする (E, G を直撃)
        elif most_common == "recover":
            attack["E"] = -magnitude * self.rng.uniform(0.7, 1.1)
            attack["G"] = -magnitude * 0.5
            self.attack_history.append("disrupt_recovery")
        # Engine が hold 多 → 機会を全部奪い、X を上げる
        elif most_common == "hold":
            attack["O"] = -magnitude * self.rng.uniform(0.8, 1.2)
            attack["X"] = magnitude * 0.5
            self.attack_history.append("punish_passivity")
        
        return attack


# ============================================================
# Causal Flipper (因果反転)
# ============================================================

class CausalFlipper:
    """action 効果の符号を反転させる
    
    通常: invest → R 減 + O 増
    flip 後: invest → R 増 + O 減 (一時的に)
    """
    
    def __init__(self):
        self.flipped: Dict[str, bool] = {
            "invest": False, "defend": False, "explore": False,
            "recover": False, "hold": False,
        }
        self.flip_duration: Dict[str, int] = {}
    
    def trigger_flip(self, intent: str, duration: int = 10):
        self.flipped[intent] = True
        self.flip_duration[intent] = duration
    
    def step_decay(self):
        for intent in list(self.flip_duration.keys()):
            self.flip_duration[intent] -= 1
            if self.flip_duration[intent] <= 0:
                self.flipped[intent] = False
                del self.flip_duration[intent]
    
    def get_flip_multiplier(self, intent: str) -> float:
        return -1.0 if self.flipped.get(intent, False) else 1.0


# ============================================================
# Goalpost Shifter (Score 関数の時変)
# ============================================================

@dataclass
class Goalpost:
    """現在の「良さ」の定義"""
    weight_health: float = 0.4   # E, G を重視
    weight_opt: float = 0.3      # O を重視
    weight_risk: float = -0.3    # X を減点
    weight_resource: float = 0.0  # 通常 R は中立
    weight_knowledge: float = 0.0
    
    def score(self, state: WorldState) -> float:
        return (
            self.weight_health * (state.E + state.G) / 200
            + self.weight_opt * state.O / 100
            + self.weight_risk * state.X / 100
            + self.weight_resource * state.R / 100
            + self.weight_knowledge * state.K / 100
        )
    
    def shift(self, rng: np.random.Generator):
        """重みをランダム再配分"""
        # 既存の重みからずらす
        keys = ["weight_health", "weight_opt", "weight_risk", 
                "weight_resource", "weight_knowledge"]
        for k in keys:
            current = getattr(self, k)
            delta = float(rng.normal(0, 0.15))
            setattr(self, k, current + delta)
        # weight_risk は負方向にクランプ
        self.weight_risk = min(0.0, self.weight_risk)


# ============================================================
# Observation Filter (観測信頼性崩壊)
# ============================================================

class ObservationFilter:
    """state 観測にノイズと欠損を加える
    
    どろどろの本質: agent は世界の真の姿を見られない
    """
    
    def __init__(self, rng: np.random.Generator):
        self.rng = rng
        self.noise_amplitude = 0.05  # 通常は 5% ノイズ
        self.broken_dimensions: set = set()  # 完全に見えない次元
        self.broken_duration: Dict[str, int] = {}
    
    def filter(self, state: WorldState) -> WorldState:
        """観測を歪める"""
        # 全 dimensions にノイズ
        observed = WorldState(
            t=state.t,
            R=state.R + float(self.rng.normal(0, state.R * self.noise_amplitude)),
            E=state.E + float(self.rng.normal(0, state.E * self.noise_amplitude)),
            G=state.G + float(self.rng.normal(0, state.G * self.noise_amplitude)),
            O=state.O + float(self.rng.normal(0, state.O * self.noise_amplitude)),
            K=state.K + float(self.rng.normal(0, state.K * self.noise_amplitude)),
            X=state.X + float(self.rng.normal(0, state.X * self.noise_amplitude)),
            cumulative_score=state.cumulative_score,
            is_ruined=state.is_ruined,
        )
        
        # 壊れた dimensions は無意味な値に
        for dim in self.broken_dimensions:
            setattr(observed, dim, 50.0 + float(self.rng.normal(0, 25)))
        
        return observed
    
    def break_dimension(self, dim: str, duration: int = 5):
        self.broken_dimensions.add(dim)
        self.broken_duration[dim] = duration
    
    def step_decay(self):
        for dim in list(self.broken_duration.keys()):
            self.broken_duration[dim] -= 1
            if self.broken_duration[dim] <= 0:
                self.broken_dimensions.discard(dim)
                del self.broken_duration[dim]


# ============================================================
# Event Log
# ============================================================

@dataclass
class ChaoticEventLog:
    step: int
    events: List[EvilEvent] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


# ============================================================
# ChaoticWorld
# ============================================================

class ChaoticWorld:
    """混沌世界: NRMO の真の本旨を試す場
    
    使い方:
        config = ChaosConfig.from_level("severe")
        world = ChaoticWorld(config, seed=42)
        
        for t in range(horizon):
            observed_state = world.observe()  # 観測 (ノイズあり)
            action = engine.decide(observed_state)
            reward, done, info = world.step(action)
            if done:
                break
    """
    
    def __init__(self, config: ChaosConfig, seed: int = 0):
        self.config = config
        self.rng = np.random.default_rng(seed)
        
        # 初期 state
        self.state = WorldState(
            t=0, R=60, E=70, G=70, O=50, K=60, X=20,
            cumulative_score=0.0, is_ruined=False,
        )
        
        # 初期 parameters (途中で変わり得る)
        self.params = WorldParameters(
            opportunity_arrival_rate=0.25,
            opportunity_window_duration=10.0,
            ruin_probability_base=0.01,
            resource_decay_rate=0.025,
            physical_decay_rate=0.020,
            emotional_volatility=0.20,
            irreversibility_propensity=0.30,
            recovery_rate=0.035,
            competitive_pressure=0.40,
            information_uncertainty=0.30,
            noise_amplitude=0.20,
        )
        
        # 隠れ次元 (現在 active)
        self.hidden_dims: List[HiddenDimension] = []
        
        # 副要素
        self.adversary = AdversaryAgent(self.rng, config.adversary_potency)
        self.causal_flipper = CausalFlipper()
        self.goalpost = Goalpost()
        self.obs_filter = ObservationFilter(self.rng)
        
        # ログ
        self.event_log: List[ChaoticEventLog] = []
        self.regime_shift_count = 0
        self.black_swan_count = 0
    
    def observe(self) -> WorldState:
        """Agent への観測 (歪んでいる)"""
        return self.obs_filter.filter(self.state)
    
    def _action_to_state_delta(self, action: Action) -> Dict[str, float]:
        """通常の action → state delta マッピング"""
        intent = action.intent
        strength_mult = {"A": 0.6, "B": 1.0, "C": 1.6}.get(action.strength, 1.0)
        
        # 因果反転をチェック
        flip_mult = self.causal_flipper.get_flip_multiplier(intent)
        
        if intent == "invest":
            d = {"R": -8, "O": 6, "X": 3}
        elif intent == "defend":
            d = {"R": -2, "X": -5, "O": -1}
        elif intent == "explore":
            d = {"R": -3, "K": 5, "O": 4}
        elif intent == "recover":
            d = {"R": -1, "E": 8, "G": 6, "O": -2}
        else:  # hold
            d = {"R": -1, "X": 1, "O": -1}
        
        return {k: v * strength_mult * flip_mult for k, v in d.items()}
    
    def _apply_delta(self, delta: Dict[str, float]):
        """state に delta を適用 (クリップあり)"""
        for k, v in delta.items():
            if k == "R":
                self.state.R = max(0, min(100, self.state.R + v))
            elif k == "E":
                self.state.E = max(0, min(100, self.state.E + v))
            elif k == "G":
                self.state.G = max(0, min(100, self.state.G + v))
            elif k == "O":
                self.state.O = max(0, min(100, self.state.O + v))
            elif k == "K":
                self.state.K = max(0, min(100, self.state.K + v))
            elif k == "X":
                self.state.X = max(0, min(100, self.state.X + v))
    
    def _resolve_evil_events(self) -> List[EvilEvent]:
        """この step で起きた evil events を決定"""
        events = []
        log_detail = {}
        c = self.config
        
        # === Regime shift ===
        if self.rng.random() < c.regime_shift_rate:
            events.append(EvilEvent.REGIME_SHIFT)
            self.regime_shift_count += 1
            # parameters をランダムに大きく動かす
            self.params.opportunity_arrival_rate = float(self.rng.uniform(0.02, 0.5))
            self.params.ruin_probability_base = float(self.rng.uniform(0.001, 0.15))
            self.params.resource_decay_rate = float(self.rng.uniform(0.01, 0.08))
            self.params.competitive_pressure = float(self.rng.uniform(0.1, 0.95))
            log_detail["regime_new_ruin_rate"] = self.params.ruin_probability_base
        
        # === Black Swan ===
        if self.rng.random() < c.black_swan_rate:
            events.append(EvilEvent.BLACK_SWAN)
            self.black_swan_count += 1
            sev = c.black_swan_severity
            self.state.R *= (1 - sev)
            self.state.E *= (1 - sev * 0.7)
            self.state.G *= (1 - sev * 0.5)
            self.state.O *= (1 - sev * 0.8)
            self.state.X += 30 * sev
            log_detail["black_swan_severity"] = sev
        
        # === Causal flip ===
        if self.rng.random() < c.causal_flip_rate:
            events.append(EvilEvent.CAUSAL_FLIP)
            # ランダムな intent を選んで反転
            intent = self.rng.choice(["invest", "defend", "explore", "recover", "hold"])
            duration = int(self.rng.integers(5, 20))
            self.causal_flipper.trigger_flip(intent, duration)
            log_detail["flipped_intent"] = intent
            log_detail["flip_duration"] = duration
        
        # === Cascade ===
        if self.rng.random() < c.cascade_rate:
            events.append(EvilEvent.CASCADE)
            cs = c.cascade_strength
            # state 変数の連鎖崩壊
            if self.state.E < 50:
                # E 低い → G に伝播
                self.state.G *= (1 - 0.15 * cs)
            if self.state.G < 50:
                # G 低い → O に伝播
                self.state.O *= (1 - 0.12 * cs)
            if self.state.O < 30:
                # O 低い → X 上昇
                self.state.X = min(100, self.state.X + 8 * cs)
            if self.state.X > 60:
                # X 高い → R 急減
                self.state.R *= (1 - 0.10 * cs)
            log_detail["cascade_strength"] = cs
        
        # === Hidden dim emerge ===
        if self.rng.random() < c.hidden_dim_emerge_rate:
            events.append(EvilEvent.HIDDEN_DIM_EMERGE)
            # 新しい隠れ次元を出現
            available = [d for d in HIDDEN_DIM_POOL 
                          if d[0] not in [h.name for h in self.hidden_dims]]
            if available:
                name, influences, strength = available[
                    int(self.rng.integers(0, len(available)))
                ]
                lifetime = int(self.rng.integers(20, 80))
                new_dim = HiddenDimension(
                    name=name,
                    value=float(self.rng.uniform(20, 80)),
                    influence_on=influences,
                    influence_strength=strength,
                    lifetime=lifetime,
                )
                self.hidden_dims.append(new_dim)
                log_detail["new_hidden_dim"] = name
        
        # === Hidden dim vanish ===
        if self.hidden_dims and self.rng.random() < c.hidden_dim_vanish_rate:
            events.append(EvilEvent.HIDDEN_DIM_VANISH)
            idx = int(self.rng.integers(0, len(self.hidden_dims)))
            vanishing = self.hidden_dims.pop(idx)
            log_detail["vanished_hidden_dim"] = vanishing.name
        
        # === Observation break ===
        if self.rng.random() < c.observation_break_rate:
            events.append(EvilEvent.OBSERVATION_BREAK)
            dim = self.rng.choice(["R", "E", "G", "O", "K", "X"])
            duration = int(self.rng.integers(3, 15))
            self.obs_filter.break_dimension(dim, duration)
            # 全体ノイズも一時的に上げる
            self.obs_filter.noise_amplitude = min(
                c.observation_noise_max,
                self.obs_filter.noise_amplitude + 0.1
            )
            log_detail["broken_obs_dim"] = dim
        
        # === Goalpost shift ===
        if self.rng.random() < c.goalpost_shift_rate:
            events.append(EvilEvent.GOALPOST_SHIFT)
            self.goalpost.shift(self.rng)
            log_detail["new_weights"] = {
                "health": self.goalpost.weight_health,
                "opt": self.goalpost.weight_opt,
                "risk": self.goalpost.weight_risk,
            }
        
        # === Adversary strike ===
        if self.rng.random() < c.adversary_strike_rate:
            events.append(EvilEvent.ADVERSARY_STRIKE)
            attack = self.adversary.strike(self.state)
            if attack:
                self._apply_delta(attack)
                log_detail["adversary_attack"] = attack
        
        # 何も起きなかった場合
        if not events:
            events.append(EvilEvent.NORMAL)
        
        # ログ記録
        self.event_log.append(ChaoticEventLog(
            step=self.state.t,
            events=events,
            details=log_detail,
        ))
        
        return events
    
    def _apply_hidden_dims(self):
        """隠れ次元の影響を state に適用"""
        for dim in self.hidden_dims:
            dim.lifetime -= 1
            # 影響を与える
            for target in dim.influence_on:
                # 隠れ次元の値が高いほど影響大
                effect = (dim.value - 50) / 100 * dim.influence_strength
                current = getattr(self.state, target)
                setattr(self.state, target, max(0, min(100, current + effect * 2)))
            # 隠れ次元自身もランダムに変動
            dim.value += float(self.rng.normal(0, 3))
            dim.value = max(0, min(100, dim.value))
        
        # 寿命切れの除去
        self.hidden_dims = [d for d in self.hidden_dims if d.lifetime > 0]
    
    def _natural_decay(self):
        """各 step の自然減衰"""
        self.state.R -= self.params.resource_decay_rate * 100 * 0.1
        self.state.E -= self.params.physical_decay_rate * 100 * 0.1
        self.state.R = max(0, self.state.R)
        self.state.E = max(0, self.state.E)
        # X は時間経過で自然下降
        self.state.X = max(0, self.state.X - 0.5)
    
    def _check_ruin(self) -> bool:
        """破滅判定"""
        # 通常 ruin 判定
        if self.rng.random() < self.params.ruin_probability_base * (self.state.X / 50):
            return True
        # 任意の state が 0 になったら ruin
        if self.state.R <= 1 or self.state.E <= 1 or self.state.G <= 1:
            return True
        # X が 95 超えで ruin 確率急増
        if self.state.X > 95:
            if self.rng.random() < 0.3:
                return True
        return False
    
    def step(self, action: Action) -> Tuple[float, bool, Dict]:
        """1 step 進める
        
        Returns: (reward, done, info)
        """
        self.state.t += 1
        
        # 1) Adversary に action を観察させる
        self.adversary.observe(action, self.state)
        
        # 2) Action の効果を適用 (因果反転考慮)
        delta = self._action_to_state_delta(action)
        self._apply_delta(delta)
        
        # 3) Evil events 発生
        events = self._resolve_evil_events()
        
        # 4) 隠れ次元の影響
        self._apply_hidden_dims()
        
        # 5) 自然減衰
        self._natural_decay()
        
        # 6) 時間崩壊処理
        self.causal_flipper.step_decay()
        self.obs_filter.step_decay()
        # 観測ノイズが少しずつ通常レベルに戻る
        self.obs_filter.noise_amplitude = max(
            0.05, self.obs_filter.noise_amplitude * 0.95
        )
        
        # 7) Reward (Goalpost に従う)
        prev_score = self.state.cumulative_score
        step_score = self.goalpost.score(self.state)
        self.state.cumulative_score += step_score
        reward = step_score
        
        # 8) 破滅判定
        done = self._check_ruin()
        if done:
            self.state.is_ruined = True
        
        info = {
            "events": [e.value for e in events],
            "n_hidden_dims": len(self.hidden_dims),
            "hidden_dim_names": [d.name for d in self.hidden_dims],
            "observation_broken": list(self.obs_filter.broken_dimensions),
            "flipped_intents": [k for k, v in self.causal_flipper.flipped.items() if v],
            "regime_shifts_total": self.regime_shift_count,
            "black_swans_total": self.black_swan_count,
        }
        return reward, done, info


# ============================================================
# Quick demo
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("ChaoticWorld Demo")
    print("=" * 70)
    
    for level in ["mild", "moderate", "severe", "extreme", "total"]:
        config = ChaosConfig.from_level(level)
        world = ChaoticWorld(config, seed=42)
        
        # Random action で 100 step
        rng = np.random.default_rng(42)
        intents = ["invest", "defend", "explore", "recover", "hold"]
        strengths = ["A", "B", "C"]
        
        events_seen = []
        for t in range(100):
            action = Action(
                intent=rng.choice(intents),
                strength=rng.choice(strengths),
            )
            reward, done, info = world.step(action)
            events_seen.extend([e for e in info["events"] if e != "normal"])
            if done:
                break
        
        print(f"\n[{level.upper():10s}] horizon={t+1}, ruined={world.state.is_ruined}, "
              f"score={world.state.cumulative_score:.2f}")
        print(f"  Regime shifts: {world.regime_shift_count}, "
              f"Black Swans: {world.black_swan_count}")
        print(f"  Hidden dims active at end: {[d.name for d in world.hidden_dims]}")
        
        # event 頻度
        from collections import Counter
        event_counter = Counter(events_seen)
        top_events = event_counter.most_common(5)
        print(f"  Top events: {top_events}")
    
    print("\n[ChaoticWorld 動作確認 完了 ✅]")
