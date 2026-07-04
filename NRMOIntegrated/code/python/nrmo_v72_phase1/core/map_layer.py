"""
core/map_layer.py

MAPLayer — AMD Ryzen 3D V-Cache 風 多層キャッシュ

3 軸:
  軸 1: 6 state dimensions (R, E, G, O, K, X)
  軸 2: time horizon (L1 / L2 / L3)
  軸 3: strategy slot (各 unit の trajectory)

L1 (直近 cache):
  - 直近 5 step の 生 trajectory
  - 高解像度、毎 step update
  - 観測ノイズが低い時に参照

L2 (中期 cache):
  - 中期 30 step の rolling summary
  - mean / std / trend
  - 中解像度、低更新頻度
  - 観測ノイズが中程度の時に参照

L3 (長期 cache):
  - 長期全体の episodic memory
  - 重要事件 (regime shift, black swan, ruined attempt)
  - 低解像度、event 駆動
  - 観測ノイズが高い時 or 構造変化検知時に参照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState


# ============================================================
# Layer data types
# ============================================================

@dataclass
class L1Snapshot:
    """1 step の生 trajectory record"""
    t: int
    state: Dict[str, float]  # R, E, G, O, K, X
    action_intent: Optional[str] = None
    action_strength: Optional[str] = None
    reward: float = 0.0


@dataclass
class L2Summary:
    """中期 window の summary"""
    window_start: int
    window_end: int
    n_steps: int
    means: Dict[str, float]    # 6 dims
    stds: Dict[str, float]
    trends: Dict[str, float]   # linear slope
    avg_reward: float
    action_distribution: Dict[str, int]  # intent counts


@dataclass
class L3Event:
    """重要事件 episodic memory"""
    t: int
    event_type: str  # "regime_shift", "black_swan", "near_ruin", "great_success"
    state_before: Dict[str, float]
    state_after: Optional[Dict[str, float]] = None
    description: str = ""


# ============================================================
# MAPLayer
# ============================================================

class MAPLayer:
    """3D V-Cache 風 多層キャッシュ"""
    
    L1_WINDOW = 5
    L2_WINDOW = 30
    L3_MAX_EVENTS = 100
    L2_UPDATE_INTERVAL = 5  # 5 step ごとに L2 を再計算
    
    # Event detection thresholds
    NEAR_RUIN_X_THRESHOLD = 85
    NEAR_RUIN_R_THRESHOLD = 15
    GREAT_SUCCESS_REWARD = 5.0
    
    # 観測ノイズ閾値で L1/L2/L3 を切り替え
    LOW_NOISE_THRESHOLD = 0.15
    HIGH_NOISE_THRESHOLD = 0.40
    
    def __init__(self):
        # L1: 直近 trajectory (deque)
        self.l1: deque = deque(maxlen=self.L1_WINDOW)
        
        # L2: rolling summary list
        self.l2: List[L2Summary] = []
        
        # L3: episodic events
        self.l3: deque = deque(maxlen=self.L3_MAX_EVENTS)
        
        # 中期 update 用
        self.l2_buffer: deque = deque(maxlen=self.L2_WINDOW)
        self.last_l2_update_step = 0
        
        # Trend 検出用
        self.prev_state: Optional[L1Snapshot] = None
        
        # ★ Sociable Cycle Detection (per sociable numbers v6.9)
        # L3 cycle detection を sociable chain detection に拡張
        try:
            from sociable_essence import SociableCycleDetector
            self.sociable_cycle_detector = SociableCycleDetector()
        except ImportError:
            self.sociable_cycle_detector = None
    
    def update(self, t: int, state: WorldState, 
                 action_intent: Optional[str] = None,
                 action_strength: Optional[str] = None,
                 reward: float = 0.0):
        """各 step で呼ばれる"""
        snapshot = L1Snapshot(
            t=t,
            state={
                "R": float(state.R), "E": float(state.E), "G": float(state.G),
                "O": float(state.O), "K": float(state.K), "X": float(state.X),
            },
            action_intent=action_intent,
            action_strength=action_strength,
            reward=float(reward),
        )
        
        # L1 update
        self.l1.append(snapshot)
        self.l2_buffer.append(snapshot)
        
        # L2 update (interval ごと)
        if t - self.last_l2_update_step >= self.L2_UPDATE_INTERVAL:
            self._update_l2(t)
            self.last_l2_update_step = t
        
        # L3 event detection
        self._detect_events(snapshot)
        
        # ★ Sociable cycle detection (universal across all layers)
        if (self.sociable_cycle_detector is not None and 
            action_intent and action_strength):
            from world_models import Action
            self.sociable_cycle_detector.update(
                state, Action(action_intent, action_strength), reward
            )
        
        self.prev_state = snapshot
    
    def detect_sociable_cycle(self):
        """Sociable chain (k-cycle) を検出.
        Returns: CycleInfo or None.
        """
        if self.sociable_cycle_detector is None:
            return None
        return self.sociable_cycle_detector.detect_cycle()
    
    def _update_l2(self, t: int):
        """L2 summary を再計算"""
        if len(self.l2_buffer) < 5:
            return
        
        # 6 dims の mean/std/trend
        dims = ["R", "E", "G", "O", "K", "X"]
        means = {}
        stds = {}
        trends = {}
        
        for dim in dims:
            values = [snap.state[dim] for snap in self.l2_buffer]
            means[dim] = float(np.mean(values))
            stds[dim] = float(np.std(values))
            # Linear trend
            if len(values) > 2:
                x = np.arange(len(values))
                slope = float(np.polyfit(x, values, 1)[0])
                trends[dim] = slope
            else:
                trends[dim] = 0.0
        
        # Reward avg
        rewards = [snap.reward for snap in self.l2_buffer]
        avg_reward = float(np.mean(rewards)) if rewards else 0.0
        
        # Action distribution
        action_dist = {}
        for snap in self.l2_buffer:
            if snap.action_intent:
                action_dist[snap.action_intent] = action_dist.get(snap.action_intent, 0) + 1
        
        summary = L2Summary(
            window_start=self.l2_buffer[0].t if self.l2_buffer else t,
            window_end=t,
            n_steps=len(self.l2_buffer),
            means=means,
            stds=stds,
            trends=trends,
            avg_reward=avg_reward,
            action_distribution=action_dist,
        )
        self.l2.append(summary)
        # L2 履歴は最大 50 件
        if len(self.l2) > 50:
            self.l2 = self.l2[-50:]
    
    def _detect_events(self, snapshot: L1Snapshot):
        """L3 event 検出"""
        # Near ruin
        if snapshot.state["X"] >= self.NEAR_RUIN_X_THRESHOLD:
            self.l3.append(L3Event(
                t=snapshot.t,
                event_type="near_ruin",
                state_before=snapshot.state,
                description=f"X={snapshot.state['X']:.1f} reached near-ruin",
            ))
        elif snapshot.state["R"] <= self.NEAR_RUIN_R_THRESHOLD:
            self.l3.append(L3Event(
                t=snapshot.t,
                event_type="near_ruin",
                state_before=snapshot.state,
                description=f"R={snapshot.state['R']:.1f} dangerously low",
            ))
        
        # Great success
        if snapshot.reward > self.GREAT_SUCCESS_REWARD:
            self.l3.append(L3Event(
                t=snapshot.t,
                event_type="great_success",
                state_before=snapshot.state,
                description=f"reward={snapshot.reward:.2f}",
            ))
        
        # Regime shift (急激な state 変化)
        if self.prev_state is not None:
            big_changes = []
            for dim in ["R", "E", "G", "O", "X"]:
                delta = abs(snapshot.state[dim] - self.prev_state.state[dim])
                if delta > 20:  # 20 ポイント以上の急変
                    big_changes.append(f"{dim} {delta:.1f}")
            
            if len(big_changes) >= 2:
                self.l3.append(L3Event(
                    t=snapshot.t,
                    event_type="regime_shift",
                    state_before=self.prev_state.state,
                    state_after=snapshot.state,
                    description=f"big changes: {', '.join(big_changes)}",
                ))
    
    # ============================================================
    # 参照 API (観測ノイズに応じて層を切り替え)
    # ============================================================
    
    def query(self, observation_noise: float = 0.05) -> Dict:
        """観測ノイズに応じて適切な層を返す"""
        if observation_noise < self.LOW_NOISE_THRESHOLD:
            # L1 重視 (直近 raw)
            return {
                "primary_layer": "L1",
                "data": self._get_l1_view(),
                "secondary_layer": "L2",
                "secondary_data": self._get_l2_view(),
            }
        elif observation_noise < self.HIGH_NOISE_THRESHOLD:
            # L2 重視 (中期 smoothing)
            return {
                "primary_layer": "L2",
                "data": self._get_l2_view(),
                "secondary_layer": "L1",
                "secondary_data": self._get_l1_view(),
            }
        else:
            # L3 重視 (episodic, 構造変化検知)
            return {
                "primary_layer": "L3",
                "data": self._get_l3_view(),
                "secondary_layer": "L2",
                "secondary_data": self._get_l2_view(),
            }
    
    def _get_l1_view(self) -> Dict:
        """L1 raw view"""
        if not self.l1:
            return {"trajectory": [], "n_steps": 0}
        
        traj = []
        for snap in self.l1:
            traj.append({
                "t": snap.t,
                "state": snap.state,
                "action": (f"{snap.action_intent}/{snap.action_strength}"
                            if snap.action_intent else None),
                "reward": snap.reward,
            })
        return {"trajectory": traj, "n_steps": len(self.l1)}
    
    def _get_l2_view(self) -> Dict:
        """L2 summary view"""
        if not self.l2:
            return {"summaries": [], "n_windows": 0}
        
        # 最新 5 個の summary
        recent = self.l2[-5:]
        summaries = []
        for s in recent:
            summaries.append({
                "window": [s.window_start, s.window_end],
                "n_steps": s.n_steps,
                "means": s.means,
                "stds": s.stds,
                "trends": s.trends,
                "avg_reward": s.avg_reward,
                "action_dist": s.action_distribution,
            })
        return {"summaries": summaries, "n_windows": len(self.l2)}
    
    def _get_l3_view(self) -> Dict:
        """L3 episodic view"""
        if not self.l3:
            return {"events": [], "n_events": 0}
        
        # 最新 20 個の event
        recent = list(self.l3)[-20:]
        events = []
        for ev in recent:
            events.append({
                "t": ev.t,
                "type": ev.event_type,
                "description": ev.description,
            })
        
        # event type 集計
        from collections import Counter
        type_count = Counter(ev.event_type for ev in self.l3)
        
        return {
            "events": events,
            "n_events": len(self.l3),
            "type_count": dict(type_count),
        }
    
    # ============================================================
    # 派生指標 (engine が使う)
    # ============================================================
    
    def get_smoothed_state(self) -> Optional[Dict[str, float]]:
        """L2 ベースの平滑化 state"""
        if not self.l2:
            return None
        latest = self.l2[-1]
        return dict(latest.means)
    
    def get_state_trends(self) -> Optional[Dict[str, float]]:
        """各 dim の trend (slope)"""
        if not self.l2:
            return None
        return dict(self.l2[-1].trends)
    
    def near_ruin_count(self) -> int:
        return sum(1 for ev in self.l3 if ev.event_type == "near_ruin")
    
    def regime_shift_count(self) -> int:
        return sum(1 for ev in self.l3 if ev.event_type == "regime_shift")


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from world_models import World, WorldType, Action
    
    print("=" * 70)
    print("MAPLayer Test (AMD 3D V-Cache 風)")
    print("=" * 70)
    
    map_layer = MAPLayer()
    world = World(WorldType.NORMAL, seed=42)
    
    rng = np.random.default_rng(42)
    intents = ["invest", "defend", "explore", "recover", "hold"]
    strengths = ["A", "B", "C"]
    
    for t in range(50):
        action = Action(
            intent=str(rng.choice(intents)),
            strength=str(rng.choice(strengths)),
        )
        _, reward, done, _ = world.step(action)
        
        map_layer.update(
            t=t, state=world.state,
            action_intent=action.intent,
            action_strength=action.strength,
            reward=reward,
        )
        
        if done:
            print(f"Ruined at step {t+1}")
            break
    
    # L1 view (低ノイズ)
    print(f"\n--- Low noise (L1 primary) ---")
    view = map_layer.query(observation_noise=0.05)
    print(f"Primary: {view['primary_layer']}")
    print(f"L1 trajectory: {view['data']['n_steps']} steps")
    if view['data']['trajectory']:
        last = view['data']['trajectory'][-1]
        print(f"  Latest: t={last['t']}, state R={last['state']['R']:.1f}")
    
    # L2 view (中ノイズ)
    print(f"\n--- Mid noise (L2 primary) ---")
    view = map_layer.query(observation_noise=0.25)
    print(f"Primary: {view['primary_layer']}")
    print(f"L2 summaries: {view['data']['n_windows']}")
    if view['data']['summaries']:
        latest = view['data']['summaries'][-1]
        print(f"  Latest window: {latest['window']}")
        print(f"  Means: R={latest['means']['R']:.1f}, E={latest['means']['E']:.1f}")
        print(f"  Trends: R={latest['trends']['R']:.3f}, X={latest['trends']['X']:.3f}")
        print(f"  Action dist: {latest['action_dist']}")
    
    # L3 view (高ノイズ)
    print(f"\n--- High noise (L3 primary) ---")
    view = map_layer.query(observation_noise=0.50)
    print(f"Primary: {view['primary_layer']}")
    print(f"L3 events: {view['data']['n_events']}")
    if view['data']['events']:
        print(f"  Type count: {view['data']['type_count']}")
        for ev in view['data']['events'][-3:]:
            print(f"    t={ev['t']}, {ev['type']}: {ev['description']}")
    
    # Derived
    print(f"\n--- Derived indicators ---")
    smoothed = map_layer.get_smoothed_state()
    if smoothed:
        print(f"Smoothed state (L2): R={smoothed['R']:.1f}, E={smoothed['E']:.1f}, "
              f"O={smoothed['O']:.1f}, X={smoothed['X']:.1f}")
    
    print(f"Near-ruin events: {map_layer.near_ruin_count()}")
    print(f"Regime shift events: {map_layer.regime_shift_count()}")
    
    print("\n[MAPLayer 動作確認 完了 ✅]")
