"""
core/shinobi_engine.py

Shinobi Engine — Intel P-Core + E-Core hybrid architecture 模倣

12 units 構成:
  P-Core (Performance) × 4: StrongEngine Ω Full 全機能、高コスト
  E-Core (Efficiency)  × 8: 軽量 Bandit、低コスト、ノイズ耐性

Norn (primary task manager):
  - 状況を判定し、task を P/E に振り分け
  - 信頼性高 + 余裕 → P-Core 主導
  - 信頼性低 or 緊急 → E-Core 主導
  - 合議: weighted vote

Skuld (backup task manager):
  - Norn が unavailable な時の fallback
  - シンプルな heuristic

Thompson Sampling:
  - defensive learner: 守備系 (defend, recover, hold) で学習
  - race learner: 攻撃系 (invest, explore) で学習
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import Counter, deque
from enum import Enum
import numpy as np
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import Action, WorldState
from strong_engine_omega import StrongEngineOmega, CandidateAction
from engines import V71Engine


# ============================================================
# Core types
# ============================================================

class CoreType(Enum):
    P_CORE = "p_core"  # Performance
    E_CORE = "e_core"  # Efficiency


@dataclass
class CoreUnit:
    """1 unit の状態"""
    core_id: int
    core_type: CoreType
    engine: object  # StrongEngineOmega or V71Engine
    last_action: Optional[Action] = None
    last_reward: float = 0.0
    cumulative_reward: float = 0.0
    n_calls: int = 0
    n_successes: int = 0  # reward > 0 のカウント
    health: float = 1.0   # 0-1, unit の信頼度


# ============================================================
# Thompson Sampling Learners
# ============================================================

class ThompsonSamplingLearner:
    """Beta-Bernoulli Thompson Sampling
    
    Beta(α, β) で各 (intent, strength) の success rate を学習.
    """
    
    def __init__(self, name: str, focus_intents: List[str],
                  rng: Optional[np.random.Generator] = None):
        self.name = name
        self.focus_intents = focus_intents  # ["defend", "recover", "hold"] etc.
        self.rng = rng if rng is not None else np.random.default_rng()
        
        # Beta posterior: (alpha, beta)
        self.posteriors: Dict[Tuple[str, str], List[float]] = {}
    
    def _get_key(self, action: Action) -> Optional[Tuple[str, str]]:
        if action.intent in self.focus_intents:
            return (action.intent, action.strength)
        return None
    
    def update(self, action: Action, reward: float):
        key = self._get_key(action)
        if key is None:
            return
        
        if key not in self.posteriors:
            self.posteriors[key] = [1.0, 1.0]  # Beta(1,1) = Uniform
        
        # reward > 0 を success として扱う
        if reward > 0:
            self.posteriors[key][0] += 1.0  # alpha
        else:
            self.posteriors[key][1] += 1.0  # beta
    
    def sample_success_rate(self, intent: str, strength: str) -> float:
        """Beta から sample"""
        key = (intent, strength)
        if key not in self.posteriors:
            return float(self.rng.beta(1.0, 1.0))
        a, b = self.posteriors[key]
        return float(self.rng.beta(a, b))
    
    def recommend(self) -> Optional[Action]:
        """この learner の focus 範囲で最良を Thompson sample"""
        if not self.focus_intents:
            return None
        
        best_action = None
        best_sample = -np.inf
        
        for intent in self.focus_intents:
            for strength in ["A", "B", "C"]:
                sample = self.sample_success_rate(intent, strength)
                if sample > best_sample:
                    best_sample = sample
                    best_action = Action(intent=intent, strength=strength)
        
        return best_action


# ============================================================
# Norn (Primary Task Manager)
# ============================================================

class NornTaskManager:
    """Norn = 主タスク管理者 (Norse mythology: Past)
    
    状況に応じて P/E core への振り分けを決定.
    """
    
    # P-Core 優先条件
    P_CORE_PREFERRED = {
        "complex_decision": True,
        "high_stake": True,
        "novel_situation": True,
    }
    
    # E-Core 優先条件
    E_CORE_PREFERRED = {
        "high_observation_noise": True,
        "time_critical": True,
        "low_stake": True,
        "chaotic_world": True,
    }
    
    def assign_weight(self, state: WorldState,
                       observation_noise: float = 0.05,
                       urgency: float = 0.0) -> Dict[CoreType, float]:
        """P と E の重み (合計 1.0)
        
        Returns:
          {P_CORE: weight, E_CORE: weight}
        """
        # 観測ノイズが高い → E-Core 重み増
        # state.X 極端 → P-Core (慎重判断)
        # state がノーマル → P/E 均等
        
        # P 重み計算
        p_weight = 0.5
        
        # P 重み増: 高 stake (R 低い or X 高い)
        if state.X > 70:
            p_weight += 0.15
        if state.R < 30:
            p_weight += 0.10
        
        # P 重み減: 観測ノイズ高い (P の精緻計算が無意味)
        p_weight -= observation_noise * 0.8
        
        # P 重み減: urgency 高 (E の単純判断の方が速い)
        p_weight -= urgency * 0.3
        
        # クリップ
        p_weight = max(0.1, min(0.9, p_weight))
        e_weight = 1.0 - p_weight
        
        return {
            CoreType.P_CORE: p_weight,
            CoreType.E_CORE: e_weight,
        }


class SkuldTaskManager:
    """Skuld = バックアップ task 管理者 (Norse mythology: Future)
    
    Norn が unavailable な時の fallback. シンプル.
    """
    
    def assign_weight(self, state: WorldState, **kwargs) -> Dict[CoreType, float]:
        """シンプルに 50/50"""
        return {
            CoreType.P_CORE: 0.5,
            CoreType.E_CORE: 0.5,
        }


# ============================================================
# ShinobiEngine
# ============================================================

class ShinobiEngine:
    """12 units の hybrid 並列実行 + majority vote"""
    
    N_P_CORE = 4
    N_E_CORE = 8
    
    def __init__(self, rng: Optional[np.random.Generator] = None):
        self.rng = rng if rng is not None else np.random.default_rng()
        
        # P-Core × 4 (StrongEngine Ω Full)
        self.p_cores: List[CoreUnit] = []
        for i in range(self.N_P_CORE):
            # 各 P-Core は独立な rng で多様性
            p_rng = np.random.default_rng(self.rng.integers(0, 2**31))
            engine = StrongEngineOmega(rng=p_rng)
            self.p_cores.append(CoreUnit(
                core_id=i,
                core_type=CoreType.P_CORE,
                engine=engine,
            ))
        
        # E-Core × 8 (V71Engine, 軽量)
        self.e_cores: List[CoreUnit] = []
        for i in range(self.N_E_CORE):
            engine = V71Engine()
            self.e_cores.append(CoreUnit(
                core_id=i + self.N_P_CORE,
                core_type=CoreType.E_CORE,
                engine=engine,
            ))
        
        # Task managers
        self.norn = NornTaskManager()
        self.skuld = SkuldTaskManager()
        self.norn_available = True
        
        # Thompson Sampling learners
        ts_rng_def = np.random.default_rng(self.rng.integers(0, 2**31))
        ts_rng_race = np.random.default_rng(self.rng.integers(0, 2**31))
        self.defensive_learner = ThompsonSamplingLearner(
            "defensive", focus_intents=["defend", "recover", "hold"],
            rng=ts_rng_def,
        )
        self.race_learner = ThompsonSamplingLearner(
            "race", focus_intents=["invest", "explore"],
            rng=ts_rng_race,
        )
        
        # Stats
        self.last_assignment: Dict[CoreType, float] = {}
        self.last_votes: Dict[Tuple[str, str], float] = {}
    
    def decide(self, state: WorldState,
                 observation_noise: float = 0.05,
                 urgency: float = 0.0) -> Tuple[Action, Dict]:
        """12 units の合議で action 決定
        
        Returns: (chosen_action, info_dict)
        """
        # 1) Task assignment (Norn or Skuld)
        if self.norn_available:
            weights = self.norn.assign_weight(state, observation_noise, urgency)
        else:
            weights = self.skuld.assign_weight(state)
        self.last_assignment = weights
        
        # 2) 各 unit の vote を集計 (weighted)
        votes: Dict[Tuple[str, str], float] = {}
        
        for core in self.p_cores:
            action = core.engine.select_action(state)
            key = (action.intent, action.strength)
            # P-Core の重み (unit 健康度も乗算)
            vote_weight = weights[CoreType.P_CORE] / self.N_P_CORE * core.health
            votes[key] = votes.get(key, 0.0) + vote_weight
            core.last_action = action
            core.n_calls += 1
        
        for core in self.e_cores:
            action = core.engine.select_action(state)
            key = (action.intent, action.strength)
            vote_weight = weights[CoreType.E_CORE] / self.N_E_CORE * core.health
            votes[key] = votes.get(key, 0.0) + vote_weight
            core.last_action = action
            core.n_calls += 1
        
        # 3) Thompson Sampling learners からの提案も加える
        def_rec = self.defensive_learner.recommend()
        race_rec = self.race_learner.recommend()
        
        # state に応じて TS の重みを調整
        # X 高い → defensive を重視
        # O 高い → race を重視
        ts_def_weight = 0.05 + state.X / 100 * 0.15
        ts_race_weight = 0.05 + state.O / 100 * 0.15
        
        if def_rec:
            key = (def_rec.intent, def_rec.strength)
            votes[key] = votes.get(key, 0.0) + ts_def_weight
        if race_rec:
            key = (race_rec.intent, race_rec.strength)
            votes[key] = votes.get(key, 0.0) + ts_race_weight
        
        self.last_votes = dict(votes)
        
        # 4) Majority vote (weighted argmax)
        best_key = max(votes, key=votes.get)
        chosen_action = Action(intent=best_key[0], strength=best_key[1])
        
        info = {
            "norn_used": self.norn_available,
            "weights": {k.value: v for k, v in weights.items()},
            "votes": {f"{k[0]}/{k[1]}": v for k, v in votes.items()},
            "chosen": f"{chosen_action.intent}/{chosen_action.strength}",
            "ts_defensive_rec": (f"{def_rec.intent}/{def_rec.strength}" 
                                   if def_rec else None),
            "ts_race_rec": (f"{race_rec.intent}/{race_rec.strength}"
                              if race_rec else None),
        }
        return chosen_action, info
    
    def select_action(self, state: WorldState) -> Action:
        """互換 API"""
        action, _ = self.decide(state)
        return action
    
    def update_reward(self, action: Action, reward: float):
        """全 unit に reward を伝達"""
        # P-Cores
        for core in self.p_cores:
            if core.last_action is not None:
                if hasattr(core.engine, "update_reward"):
                    core.engine.update_reward(core.last_action, reward)
                core.cumulative_reward += reward
                if reward > 0:
                    core.n_successes += 1
                # Health update (success rate ベース)
                if core.n_calls > 5:
                    core.health = 0.5 + 0.5 * (core.n_successes / core.n_calls)
        
        # E-Cores
        for core in self.e_cores:
            if core.last_action is not None:
                if hasattr(core.engine, "update_reward"):
                    core.engine.update_reward(core.last_action, reward)
                core.cumulative_reward += reward
                if reward > 0:
                    core.n_successes += 1
                if core.n_calls > 5:
                    core.health = 0.5 + 0.5 * (core.n_successes / core.n_calls)
        
        # TS learners
        self.defensive_learner.update(action, reward)
        self.race_learner.update(action, reward)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from world_models import World, WorldType
    
    print("=" * 70)
    print("Shinobi Engine Test (12 units = 4 P-Core + 8 E-Core)")
    print("=" * 70)
    
    rng = np.random.default_rng(42)
    engine = ShinobiEngine(rng=rng)
    
    world = World(WorldType.NORMAL, seed=42)
    
    print(f"\nP-Cores: {len(engine.p_cores)}, E-Cores: {len(engine.e_cores)}")
    
    for t in range(5):
        action, info = engine.decide(world.state)
        print(f"\nt={t+1}: state R={world.state.R:.1f}, O={world.state.O:.1f}, X={world.state.X:.1f}")
        print(f"  Weights: P={info['weights']['p_core']:.2f}, E={info['weights']['e_core']:.2f}")
        print(f"  Top votes: {sorted(info['votes'].items(), key=lambda x: -x[1])[:3]}")
        print(f"  Chosen: {info['chosen']}")
        print(f"  TS def: {info['ts_defensive_rec']}, race: {info['ts_race_rec']}")
        
        _, reward, done, _ = world.step(action)
        engine.update_reward(action, reward)
        if done:
            break
    
    # 高観測ノイズ環境
    print("\n=== 高観測ノイズ環境 (E-Core 重みアップ予想) ===")
    action, info = engine.decide(world.state, observation_noise=0.5)
    print(f"  Weights: P={info['weights']['p_core']:.2f}, E={info['weights']['e_core']:.2f}")
    
    # 緊急度高
    print("\n=== 緊急度高 ===")
    action, info = engine.decide(world.state, urgency=0.7)
    print(f"  Weights: P={info['weights']['p_core']:.2f}, E={info['weights']['e_core']:.2f}")
    
    print("\n[Shinobi Engine 動作確認 完了 ✅]")
