"""
core/meta_engine.py

MetaEngine — 全 sub-engine を world 適応的に統合する meta engine.

Architecture:
  MetaEngine
    ├─ Sub-engines (lazy / on-demand activation):
    │    - V71Engine (baseline)
    │    - V841Engine (hard guard baseline)
    │    - V851Engine (contextual merger)
    │    - V9MinimalEngine (引き算)
    │    - ActiveCycleEngine (maximum + active)
    ├─ WorldTypeDetector: state pattern → world type estimate
    ├─ EnginePerformanceTracker: each engine's recent reward
    ├─ EngineSelector: rule + learning で active engine 選択
    └─ Final EmergencyResourceGuard: hard rule

Operating modes:
  - "rule_based":     world type 推定だけで engine 選択 (high speed)
  - "performance":    各 engine の recent performance に基づく選択
  - "hybrid":         rule + performance の組合せ (default)
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque, Counter
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from rng_manager import RNGManager
from engines import V71Engine
from emergency_guards import EmergencyResourceGuard, GuardConfig, GuardDecision

from v841_engine import V841Engine
from v851_engine import V851Engine
from v9_minimal_engine import V9MinimalEngine
from active_cycle_engine import ActiveCycleEngine


# ============================================================
# World Type Detection
# ============================================================

class WorldTypeDetector:
    """State observation から world type を推定
    
    Heuristics (我々の honest 観察に基づく):
      - ChaoticWorld:   chaos events 多, observation 安定
      - DriftingWorld:  R 自然減少, X 自然上昇
      - NoisyWorld:     observation の volatility 高い (連続観測が大きく揺れる)
    """
    
    def __init__(self, history_size: int = 15):
        self.history_size = history_size
        # State observation history
        self.r_history: deque = deque(maxlen=history_size)
        self.x_history: deque = deque(maxlen=history_size)
        self.observation_volatility: deque = deque(maxlen=history_size)
        
        self.last_obs: Optional[Dict] = None
    
    def update(self, observation: WorldState):
        """新観測の追加"""
        # Volatility: 前回観測との dimension 差
        if self.last_obs is not None:
            volatility = (abs(observation.R - self.last_obs["R"]) +
                            abs(observation.X - self.last_obs["X"]) +
                            abs(observation.O - self.last_obs["O"])) / 3
            self.observation_volatility.append(volatility)
        
        self.r_history.append(observation.R)
        self.x_history.append(observation.X)
        self.last_obs = {
            "R": observation.R, "X": observation.X, "O": observation.O,
            "E": observation.E, "G": observation.G, "K": observation.K
        }
    
    def detect_world_type(self) -> Tuple[str, float]:
        """world type 推定 → (type, confidence)"""
        if len(self.r_history) < 5:
            return "unknown", 0.3
        
        # Drift detection: R が時間で減少傾向 + X が増加傾向 → drifting
        if len(self.r_history) >= 8:
            r_first_half = list(self.r_history)[:4]
            r_second_half = list(self.r_history)[-4:]
            x_first_half = list(self.x_history)[:4]
            x_second_half = list(self.x_history)[-4:]
            
            r_decline = float(np.mean(r_first_half) - np.mean(r_second_half))
            x_rise = float(np.mean(x_second_half) - np.mean(x_first_half))
            
            # DriftingWorld signature: R 強い減少 + X 強い上昇
            if r_decline >= 5 and x_rise >= 3:
                return "drifting", min(1.0, 0.6 + (r_decline + x_rise) / 30)
        
        # Noisy detection: observation volatility 高い
        if len(self.observation_volatility) >= 5:
            avg_vol = float(np.mean(self.observation_volatility))
            if avg_vol > 10.0:
                return "noisy", min(1.0, avg_vol / 20)
        
        # Default: chaotic
        return "chaotic", 0.6


# ============================================================
# Engine Performance Tracker
# ============================================================

class EnginePerformanceTracker:
    """各 sub-engine の recent reward を track"""
    
    def __init__(self, window_size: int = 15):
        self.window_size = window_size
        # engine_name -> deque of rewards
        self.engine_rewards: Dict[str, deque] = {}
        # engine_name -> total accumulated reward (lifetime)
        self.engine_lifetime: Dict[str, float] = {}
        # engine_name -> count of decisions made
        self.engine_decisions: Dict[str, int] = {}
    
    def init_engine(self, engine_name: str):
        if engine_name not in self.engine_rewards:
            self.engine_rewards[engine_name] = deque(maxlen=self.window_size)
            self.engine_lifetime[engine_name] = 0.0
            self.engine_decisions[engine_name] = 0
    
    def record(self, engine_name: str, reward: float):
        self.init_engine(engine_name)
        self.engine_rewards[engine_name].append(float(reward))
        self.engine_lifetime[engine_name] += float(reward)
        self.engine_decisions[engine_name] += 1
    
    def recent_average(self, engine_name: str) -> Optional[float]:
        """直近 window_size step の平均 reward"""
        if engine_name not in self.engine_rewards:
            return None
        rewards = self.engine_rewards[engine_name]
        if len(rewards) == 0:
            return None
        return float(np.mean(rewards))
    
    def best_engine(self, candidates: Optional[List[str]] = None) -> Optional[str]:
        """recent performance で最良 engine"""
        candidates = candidates or list(self.engine_rewards.keys())
        scored = []
        for name in candidates:
            avg = self.recent_average(name)
            if avg is not None:
                scored.append((name, avg))
        if not scored:
            return None
        scored.sort(key=lambda x: -x[1])
        return scored[0][0]


# ============================================================
# Engine Selector (rule + performance)
# ============================================================

# Honest benchmark findings: world → best engine ranking
# (from active_cycle_benchmark results)
WORLD_BEST_ENGINE_RANKING: Dict[str, List[str]] = {
    "chaotic":   ["active_cycle", "v851", "v9", "v841", "v71"],
    "drifting":  ["v9", "v841", "active_cycle", "v851", "v71"],
    "noisy":     ["v851", "active_cycle", "v9", "v841", "v71"],
    "unknown":   ["v851", "active_cycle", "v9", "v841", "v71"],
}


class EngineSelector:
    """world type と performance に基づく engine 選択
    
    Modes:
      "rule_based":  world type → preferred engine list の top
      "performance": tracker.best_engine
      "hybrid":      world type top 2 から、performance で選ぶ
    """
    
    def __init__(self, mode: str = "hybrid",
                  min_streak: int = 5,
                  warmup_steps: int = 10):
        self.mode = mode
        self.min_streak = min_streak  # 切替前の最小 step (thrashing 防止)
        self.warmup_steps = warmup_steps  # 序盤の固定 engine 期間
        
        self.current_engine = "v851"  # default
        self.current_streak = 0
        self.total_decisions = 0
        self.switch_count = 0
        self.switch_history: List[Tuple[int, str, str, str]] = []  # (step, from, to, reason)
    
    def select(self, world_type: str, world_confidence: float,
                tracker: EnginePerformanceTracker) -> str:
        self.total_decisions += 1
        
        # Warmup: 最初は固定
        if self.total_decisions <= self.warmup_steps:
            return self.current_engine
        
        # 切替判断
        if self.current_streak < self.min_streak:
            self.current_streak += 1
            return self.current_engine
        
        new_engine = self._propose_engine(world_type, world_confidence, tracker)
        
        if new_engine != self.current_engine:
            self.switch_count += 1
            self.switch_history.append(
                (self.total_decisions, self.current_engine, new_engine,
                  f"world={world_type}({world_confidence:.2f})")
            )
            self.current_engine = new_engine
            self.current_streak = 0
        else:
            self.current_streak += 1
        
        return self.current_engine
    
    def _propose_engine(self, world_type: str, world_confidence: float,
                          tracker: EnginePerformanceTracker) -> str:
        if self.mode == "rule_based":
            ranking = WORLD_BEST_ENGINE_RANKING.get(world_type,
                                                       WORLD_BEST_ENGINE_RANKING["unknown"])
            return ranking[0]
        
        elif self.mode == "performance":
            best = tracker.best_engine()
            if best is None:
                return self.current_engine
            return best
        
        else:  # hybrid
            ranking = WORLD_BEST_ENGINE_RANKING.get(world_type,
                                                       WORLD_BEST_ENGINE_RANKING["unknown"])
            top2 = ranking[:2]
            
            # Performance check: top 2 のうち performance が良い方
            perf_best = tracker.best_engine(candidates=top2)
            if perf_best is not None:
                return perf_best
            
            # No performance data yet → world top
            if world_confidence > 0.6:
                return top2[0]
            else:
                return self.current_engine  # 確信ない時は現状維持


# ============================================================
# MetaEngine
# ============================================================

@dataclass
class MetaDecision:
    """MetaEngine decision"""
    action: Action
    status: str
    confidence: float
    active_engine: str
    world_type: str
    world_confidence: float
    emergency_guard: Optional[GuardDecision] = None
    metadata: Dict = field(default_factory=dict)


class MetaEngine:
    """全 sub-engine を統合する meta engine
    
    Operation:
      1. observation → WorldTypeDetector.update + detect
      2. EngineSelector.select(world_type, performance)
      3. active engine が action を出す
      4. EmergencyResourceGuard で hard rule 適用 (最終)
      5. reward を受け取り、active engine の performance を track
    """
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  mode: str = "hybrid",
                  min_streak: int = 5,
                  enabled_engines: Optional[List[str]] = None,
                  guard_config: Optional[GuardConfig] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        # Available engines (lazy initialization)
        self.enabled_engines = enabled_engines or [
            "v71", "v841", "v851", "v9", "active_cycle"
        ]
        
        # Sub-engines (initialize all upfront for clean rng state)
        self.sub_engines: Dict[str, object] = {}
        for name in self.enabled_engines:
            self.sub_engines[name] = self._build_engine(name)
        
        # World type detector
        self.world_detector = WorldTypeDetector(history_size=15)
        
        # Performance tracker
        self.performance_tracker = EnginePerformanceTracker(window_size=15)
        
        # Engine selector
        self.engine_selector = EngineSelector(mode=mode, min_streak=min_streak)
        # Default engine to one of the enabled
        if self.engine_selector.current_engine not in self.enabled_engines:
            self.engine_selector.current_engine = self.enabled_engines[0]
        
        # Final hard guard
        self.guard_config = guard_config or GuardConfig()
        self.final_emergency_guard = EmergencyResourceGuard(self.guard_config)
        
        # Stats
        self.decision_counter = 0
        self.stats = {
            "total_decisions": 0,
            "engine_decisions": {},  # engine_name -> count
            "world_type_counts": {},  # world_type -> count
            "switch_count": 0,
            "final_emergency_triggered": 0,
        }
    
    def _build_engine(self, name: str):
        if name == "v71":
            return V71Engine(rng=self.rng_manager.spawn("v71_meta"))
        elif name == "v841":
            return V841Engine(rng_manager=self.rng_manager, use_active_pattern=True)
        elif name == "v851":
            return V851Engine(rng_manager=self.rng_manager,
                                use_active_pattern=True,
                                use_strong_engine_full=True,
                                use_contextual_merger=True)
        elif name == "v9":
            return V9MinimalEngine(rng_manager=self.rng_manager,
                                      use_synthesis=True,
                                      use_emergency_guard=True)
        elif name == "active_cycle":
            return ActiveCycleEngine(rng_manager=self.rng_manager,
                                        use_active_bias=True,
                                        use_cyclic_feedback=True,
                                        use_opportunity_expansion=True,
                                        use_synthesis_default=True)
        raise ValueError(f"Unknown engine: {name}")
    
    def _get_action_from_engine(self, engine_name: str, observation: WorldState) -> Action:
        """各 sub-engine の API 違いを統一"""
        eng = self.sub_engines[engine_name]
        if engine_name == "v71":
            return eng.select_action(observation)
        elif engine_name in ("v841", "v851"):
            d = eng.decide(observation)
            return d.action if d.action else Action("hold", "A")
        elif engine_name == "v9":
            d = eng.decide(observation)
            return d.action
        elif engine_name == "active_cycle":
            d = eng.decide(observation)
            return d.action
        raise ValueError(f"Unknown engine: {engine_name}")
    
    def _update_reward_for_engine(self, engine_name: str, action: Action, reward: float,
                                    state_before=None, state_after=None):
        eng = self.sub_engines[engine_name]
        if engine_name == "v71":
            eng.update_reward(action, reward)
        elif engine_name in ("v841", "v851"):
            eng.update_reward(action, reward, state_before, state_after)
        elif engine_name == "v9":
            eng.update_reward(action, reward, state_before, state_after)
        elif engine_name == "active_cycle":
            eng.update_reward(action, reward)
    
    # ============================================================
    # Main API
    # ============================================================
    
    def decide(self, observation: WorldState) -> MetaDecision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        
        # 1. World type 推定
        self.world_detector.update(observation)
        world_type, world_conf = self.world_detector.detect_world_type()
        self.stats["world_type_counts"][world_type] = \
            self.stats["world_type_counts"].get(world_type, 0) + 1
        
        # 2. Active engine 選択
        active_engine_name = self.engine_selector.select(
            world_type, world_conf, self.performance_tracker
        )
        # Ensure it's enabled
        if active_engine_name not in self.enabled_engines:
            active_engine_name = self.enabled_engines[0]
            self.engine_selector.current_engine = active_engine_name
        
        # 3. Get action from active engine
        chosen = self._get_action_from_engine(active_engine_name, observation)
        
        # 4. Final Emergency Guard (hard rule)
        eg = self.final_emergency_guard.apply(observation, chosen)
        if eg.applied:
            chosen = eg.forced_action
            status = "GUARD_FORCED"
            self.stats["final_emergency_triggered"] += 1
        else:
            status = "ACCEPT"
        
        # 5. Tracking
        self.stats["engine_decisions"][active_engine_name] = \
            self.stats["engine_decisions"].get(active_engine_name, 0) + 1
        self.stats["switch_count"] = self.engine_selector.switch_count
        
        return MetaDecision(
            action=chosen,
            status=status,
            confidence=world_conf,
            active_engine=active_engine_name,
            world_type=world_type,
            world_confidence=world_conf,
            emergency_guard=eg,
            metadata={"step": self.decision_counter},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        """全 sub-engine の reward を update + active engine の performance を track"""
        # Update reward for all engines (for internal learning)
        for name in self.enabled_engines:
            try:
                self._update_reward_for_engine(name, action, reward, state_before, state_after)
            except Exception:
                pass  # graceful degradation
        
        # Track performance only for active engine
        active = self.engine_selector.current_engine
        self.performance_tracker.record(active, reward)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    from drifting_world import DriftingWorld
    from noisy_world import NoisyObservationWorld
    
    print("=" * 70)
    print("MetaEngine Test")
    print("=" * 70)
    
    for world_class, world_name in [
        (ChaoticWorld, "Chaotic"),
        (DriftingWorld, "Drifting"),
        (NoisyObservationWorld, "Noisy"),
    ]:
        print(f"\n--- {world_name} (severe) ---")
        for seed in [42, 123]:
            cfg = ChaosConfig.from_level("severe")
            world = world_class(cfg, seed=seed)
            rng_mgr = RNGManager(master_seed=seed + 200000)
            meta = MetaEngine(rng_manager=rng_mgr, mode="hybrid", min_streak=5)
            
            engine_usage = {}
            for t in range(150):
                observed = world.observe()
                d = meta.decide(observed)
                engine_usage[d.active_engine] = engine_usage.get(d.active_engine, 0) + 1
                r, done, _ = world.step(d.action)
                meta.update_reward(d.action, r)
                if done:
                    break
            print(f"  seed={seed}: score={world.state.cumulative_score:.2f}, "
                  f"steps={world.state.t}")
            print(f"    Engine usage: {engine_usage}")
            print(f"    World types: {meta.stats['world_type_counts']}")
            print(f"    Switches: {meta.stats['switch_count']}")
            if meta.engine_selector.switch_history:
                print(f"    First 3 switches: {meta.engine_selector.switch_history[:3]}")
    
    print("\n[MetaEngine 動作確認 ✅]")
