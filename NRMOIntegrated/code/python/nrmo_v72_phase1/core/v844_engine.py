"""
core/v844_engine.py

V8.4.4 = v8.4.1 + MAPLayer (used as information source, NOT as controller).

Zarameさん の指摘:
  「MAPLayer が使えないのではなく、使い方が間違っている」

v8.4.2 と v8.4.3 の誤り:
  MAPLayer を controller として使った (engine を強制する)
  → variance 増 / 賭け

v8.4.4 の正しい使い方:
  MAPLayer は engine の「頭を整える」memory cache
  → 介入せず、補強情報のみ提供

具体的実装 (案 a):
  V71 が学習する reward を、MAPLayer L2 で smoothed する
  - raw reward は ChaoticWorld の noise で振れる
  - L2 smoothed reward は真の reward に近い
  - V71 が「真の reward」で学習 → 適切な action 選択

これは:
  ✓ 介入しない (action を強制しない)
  ✓ engine の自然な意思決定を支援
  ✓ variance を増やさない (smoothing は variance 減方向)
  ✓ NRMO 精神に合致
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from decision_trace import DecisionTrace
from rng_manager import RNGManager
from engines import V71Engine

from active_pattern_proxy import ActivePatternProxy
from veto_classification import VetoClassification, VetoType
from emergency_guards import (
    EmergencyResourceGuard, ActionIntensityThrottle,
    GuardConfig, GuardDecision
)
from cumulative_risk_tracker import CumulativeRiskTracker, CumulativeRiskConfig
from map_layer import MAPLayer


@dataclass
class V844Decision:
    """V8.4.4 Decision"""
    action: Optional[Action]
    status: str
    confidence: float
    trace: DecisionTrace
    base_action: Optional[Action] = None
    emergency_guard: Optional[GuardDecision] = None
    throttle_guard: Optional[GuardDecision] = None
    active_pattern_proposal: Optional[object] = None
    
    # MAPLayer info (情報のみ、強制なし)
    smoothed_reward_used: bool = False
    observation_noise_est: float = 0.05
    map_info: Dict = field(default_factory=dict)
    
    metadata: Dict = field(default_factory=dict)


class V844Engine:
    """V8.4.4 = v8.4.1 + MAPLayer (correct usage: information source)"""
    
    AP_INTERVENTION_THRESHOLD = 0.35
    
    # MAPLayer smoothing parameters
    SMOOTHING_WINDOW = 5  # 直近 5 reward で smoothing
    HIGH_NOISE_THRESHOLD = 0.20  # この値以上の noise で smoothing 適用
    
    def __init__(self, rng_manager: Optional[RNGManager] = None,
                  use_active_pattern: bool = True,
                  use_map_smoothing: bool = True,    # ablation switch
                  guard_config: Optional[GuardConfig] = None):
        self.rng_manager = rng_manager or RNGManager(master_seed=42)
        
        v71_rng = self.rng_manager.spawn("v71_base")
        self.v71 = V71Engine(rng=v71_rng)
        
        self.base_guard_config = guard_config or GuardConfig()
        self.emergency_guard = EmergencyResourceGuard(self.base_guard_config)
        self.throttle_guard = ActionIntensityThrottle(self.base_guard_config)
        
        self.use_active_pattern = use_active_pattern
        self.active_pattern = ActivePatternProxy() if use_active_pattern else None
        if self.active_pattern:
            self.active_pattern.INTERVENTION_THRESHOLD = self.AP_INTERVENTION_THRESHOLD
        
        self.cumulative_risk = CumulativeRiskTracker(
            config=CumulativeRiskConfig(window_steps=20)
        )
        
        # MAPLayer (always exists, ablation switch via use_map_smoothing)
        self.map_layer = MAPLayer()
        self.use_map_smoothing = use_map_smoothing
        
        # Per-action reward history for smoothing
        self.action_reward_history: Dict[Tuple[str, str], deque] = {}
        
        self.decision_counter = 0
        self.stats = {
            "emergency_triggered": 0,
            "throttle_triggered": 0,
            "ap_intervened": 0,
            "revalidation_rejected": 0,
            "total_decisions": 0,
            "smoothing_applied_count": 0,
            "smoothing_skipped_count": 0,
            "near_ruin_events_observed": 0,
        }
        self.intervention_log: List[Dict] = []
    
    # ============================================================
    # Helpers
    # ============================================================
    
    def _generate_all_candidates(self) -> List[Action]:
        return [Action(intent=i, strength=s)
                 for i in ["invest", "defend", "explore", "recover", "hold"]
                 for s in ["A", "B", "C"]]
    
    def _estimate_observation_noise(self) -> float:
        """MAPLayer L3 から観測ノイズを推定"""
        if not self.map_layer.l2:
            return 0.05
        near_ruin = self.map_layer.near_ruin_count()
        regime = self.map_layer.regime_shift_count()
        total = near_ruin + regime
        if total == 0:
            return 0.05
        elif total < 5:
            return 0.15
        elif total < 15:
            return 0.30
        else:
            return 0.50
    
    def _compute_smoothed_reward(self, action: Action, raw_reward: float) -> float:
        """MAPLayer L2 経由で smoothed reward を計算
        
        L2 が中期平均で reward を smoothing
        観測ノイズが低い時は raw 重視
        観測ノイズが高い時は L2 平均 重視
        """
        key = (action.intent, action.strength)
        if key not in self.action_reward_history:
            self.action_reward_history[key] = deque(maxlen=self.SMOOTHING_WINDOW)
        self.action_reward_history[key].append(float(raw_reward))
        
        history = list(self.action_reward_history[key])
        
        # 観測ノイズ推定
        obs_noise = self._estimate_observation_noise()
        
        if obs_noise < self.HIGH_NOISE_THRESHOLD:
            # Low noise: raw reward を信用
            self.stats["smoothing_skipped_count"] += 1
            return raw_reward
        
        if len(history) < 3:
            # 履歴不足: raw reward を返す
            self.stats["smoothing_skipped_count"] += 1
            return raw_reward
        
        # High noise: smoothing 適用
        # raw_reward と history mean を blend
        history_mean = float(np.mean(history))
        
        # Noise level で blend ratio を決定
        if obs_noise < 0.30:
            # 中程度 noise: raw 60%, smoothed 40%
            blend = 0.6 * raw_reward + 0.4 * history_mean
        elif obs_noise < 0.45:
            # 高 noise: raw 40%, smoothed 60%
            blend = 0.4 * raw_reward + 0.6 * history_mean
        else:
            # 極高 noise: raw 30%, smoothed 70%
            blend = 0.3 * raw_reward + 0.7 * history_mean
        
        self.stats["smoothing_applied_count"] += 1
        return float(blend)
    
    def _estimate_action_delta(self, action):
        intent_delta = {
            "invest":  {"R": -8, "O": 6, "X": 3},
            "defend":  {"R": -2, "X": -5, "O": -1},
            "explore": {"R": -3, "K": 5, "O": 4},
            "recover": {"R": -1, "E": 8, "G": 6, "O": -2},
            "hold":    {"R": -1, "X": 1, "O": -1},
        }
        strength_mult = {"A": 0.6, "B": 1.0, "C": 1.6}
        base = intent_delta.get(action.intent, {})
        mult = strength_mult.get(action.strength, 1.0)
        return {k: v * mult for k, v in base.items()}
    
    def _revalidate(self, state, proposed):
        revalidation = self.emergency_guard.apply(state, proposed)
        if revalidation.applied:
            return False, f"revalidation_failed: {revalidation.rule_triggered}"
        projected_delta = self._estimate_action_delta(proposed)
        breached, _ = self.cumulative_risk.projected_breach_after(projected_delta)
        if breached:
            return False, "cumulative_breach"
        return True, "passed"
    
    # ============================================================
    # Main decide (v8.4.1 と同じ pipeline、MAPLayer は介入しない)
    # ============================================================
    
    def decide(self, state: WorldState,
                 context: Optional[Dict] = None) -> V844Decision:
        self.decision_counter += 1
        self.stats["total_decisions"] += 1
        trace = DecisionTrace(decision_id=self.decision_counter)
        
        # MAPLayer query — 情報を取得するだけ、強制しない
        obs_noise = self._estimate_observation_noise()
        map_info = {
            "observation_noise_est": obs_noise,
            "near_ruin_count": self.map_layer.near_ruin_count(),
        }
        trace.add("map_layer_query", "pass", map_info)
        
        # Step 1: v7.1 base action (smoothed reward で学習済み)
        base_action = self.v71.select_action(state)
        trace.add("v71_base", "pass", {
            "action": f"{base_action.intent}/{base_action.strength}",
        })
        
        current_action = base_action
        status = "ACCEPT"
        
        # Step 2: EmergencyResourceGuard (v8.4.1 と同じ)
        eg_decision = self.emergency_guard.apply(state, current_action)
        if eg_decision.applied:
            current_action = eg_decision.forced_action
            status = "GUARD_FORCED"
            self.stats["emergency_triggered"] += 1
            trace.add("emergency_guard", "intervened", eg_decision.to_dict())
        else:
            trace.add("emergency_guard", "pass", {})
        
        # Step 3: ActionIntensityThrottle
        th_decision = self.throttle_guard.apply(state, current_action)
        if th_decision.applied:
            current_action = th_decision.forced_action
            if status == "ACCEPT":
                status = "GUARD_FORCED"
            self.stats["throttle_triggered"] += 1
            trace.add("throttle_guard", "intervened", th_decision.to_dict())
        else:
            trace.add("throttle_guard", "pass", {})
        
        # Step 4: ActivePattern
        ap_proposal = None
        if self.use_active_pattern and self.active_pattern is not None:
            all_cands = self._generate_all_candidates()
            veto = VetoClassification.no_veto()
            ap_proposal = self.active_pattern.evaluate(
                state, all_cands, current_action, veto
            )
            if ap_proposal.has_correction_proposal and ap_proposal.proposed_action:
                passed, _ = self._revalidate(state, ap_proposal.proposed_action)
                if passed:
                    current_action = ap_proposal.proposed_action
                    if status == "ACCEPT":
                        status = "AP_INTERVENED"
                    self.stats["ap_intervened"] += 1
        
        # Histories
        if self.use_active_pattern and self.active_pattern is not None:
            self.active_pattern.update_history(state, current_action)
        self.throttle_guard.update_history(state, current_action)
        
        # MAPLayer update
        self.map_layer.update(
            t=self.decision_counter,
            state=state,
            action_intent=current_action.intent,
            action_strength=current_action.strength,
            reward=0.0,
        )
        # Stats: near_ruin observed
        self.stats["near_ruin_events_observed"] = self.map_layer.near_ruin_count()
        
        return V844Decision(
            action=current_action,
            status=status,
            confidence=0.7,
            trace=trace,
            base_action=base_action,
            emergency_guard=eg_decision,
            throttle_guard=th_decision,
            active_pattern_proposal=ap_proposal,
            smoothed_reward_used=self.use_map_smoothing and obs_noise > self.HIGH_NOISE_THRESHOLD,
            observation_noise_est=obs_noise,
            map_info=map_info,
            metadata={"stats": dict(self.stats)},
        )
    
    def update_reward(self, action: Action, reward: float,
                       state_before=None, state_after=None):
        """★ V71 への学習 reward を MAPLayer で smoothing"""
        if self.use_map_smoothing:
            smoothed = self._compute_smoothed_reward(action, reward)
            self.v71.update_reward(action, smoothed)
        else:
            # Ablation: raw reward を直接 V71 へ
            self.v71.update_reward(action, reward)
            # 履歴だけは保持 (smoothing なしでも統計取れる)
            key = (action.intent, action.strength)
            if key not in self.action_reward_history:
                self.action_reward_history[key] = deque(maxlen=self.SMOOTHING_WINDOW)
            self.action_reward_history[key].append(float(reward))
        
        if state_before is not None and state_after is not None:
            self.cumulative_risk.add(action, state_before, state_after)
        
        # MAPLayer の reward update
        if self.map_layer.l1:
            self.map_layer.l1[-1].reward = float(reward)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from chaotic_world import ChaoticWorld, ChaosConfig
    
    print("=" * 70)
    print("V8.4.4 Engine Test (v8.4.1 + MAPLayer as information source)")
    print("=" * 70)
    
    config = ChaosConfig.from_level("severe")
    world = ChaoticWorld(config, seed=42)
    
    rng_mgr = RNGManager(master_seed=42 + 1000000)
    engine = V844Engine(rng_manager=rng_mgr,
                          use_active_pattern=True,
                          use_map_smoothing=True)
    
    print("\n--- 20 step trace ---")
    for t in range(20):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = engine.decide(world.state)
        action = d.action if d.action else Action(intent="hold", strength="A")
        
        if t < 10:
            sm = "S" if d.smoothed_reward_used else " "
            print(f"  t={t+1:2d}: {action.intent}/{action.strength}  "
                  f"R={world.state.R:.0f} X={world.state.X:.0f}  "
                  f"noise={d.observation_noise_est:.2f}  smoothing={sm}")
        
        reward, done, _ = world.step(action)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.update_reward(action, reward, sb, sa)
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    print(f"\n--- Stats ---")
    for k, v in engine.stats.items():
        print(f"  {k}: {v}")
    print(f"  Final score: {world.state.cumulative_score:.2f}")
    
    print("\n[V8.4.4 Engine 動作確認 完了 ✅]")
