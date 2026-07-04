"""
core/noisy_world.py

NoisyObservationWorld — 観測ノイズ主体のカオス.

ChaoticWorld との違い:
  - state evolution は安定 (chaos events 少)
  - 但し observation に大きなノイズ
  - state.R が 50 でも、observed.R が 20 や 80 になる
  - agent は state を信頼できない

NRMO の本来の試練 (Knightian uncertainty):
  - 「危険か安全か分からない」を恒常的に経験
  - 賢い engine ほど、ノイズに騙される
  - シンプルな保守策が結果的に強い
"""
from __future__ import annotations
import os, sys
from typing import Dict, List, Optional, Tuple
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from chaotic_world import (
    ChaoticWorld, ChaosConfig, EvilEvent,
    AdversaryAgent, CausalFlipper, Goalpost, ObservationFilter,
)


class NoisyObservationWorld(ChaoticWorld):
    """観測ノイズ主体のカオス世界
    
    State dynamics は ChaoticWorld と同じだが:
      - observation に強い noise を加える
      - 全 state dimension に常時 ±15 程度のノイズ
      - 時折 ±30 (重大な observation distortion)
      - dimension が「壊れる」頻度を増やす
    """
    
    OBS_NOISE_STD = 12.0           # 通常ノイズ
    OBS_NOISE_SPIKE_STD = 25.0     # スパイク
    SPIKE_PROBABILITY = 0.15       # スパイク発生率
    BREAK_PROB_MULTIPLIER = 3.0    # dimension break 頻度倍率
    
    def observe(self) -> WorldState:
        """親クラスの observe を上書き: 強い noise を加える"""
        # 親の observe で broken_dim 処理を取得
        obs = super().observe()
        
        # 全 dimension に大きな noise を加える
        for dim in ["R", "E", "G", "O", "K", "X"]:
            if self.rng.random() < self.SPIKE_PROBABILITY:
                noise = float(self.rng.normal(0, self.OBS_NOISE_SPIKE_STD))
            else:
                noise = float(self.rng.normal(0, self.OBS_NOISE_STD))
            
            current = getattr(obs, dim)
            new_val = max(0, min(100, current + noise))
            setattr(obs, dim, new_val)
        
        return obs


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("NoisyObservationWorld Test")
    print("=" * 70)
    
    cfg = ChaosConfig.from_level("severe")
    world = NoisyObservationWorld(cfg, seed=42)
    
    print(f"\nTrue vs Observed (first 10 steps):")
    for t in range(10):
        true_state = WorldState(
            t=world.state.t, R=world.state.R, E=world.state.E,
            G=world.state.G, O=world.state.O, K=world.state.K,
            X=world.state.X,
            cumulative_score=world.state.cumulative_score,
            is_ruined=world.state.is_ruined,
        )
        obs = world.observe()
        
        print(f"  t={t}: True R={true_state.R:.0f} X={true_state.X:.0f} O={true_state.O:.0f}")
        print(f"       Obs  R={obs.R:.0f} X={obs.X:.0f} O={obs.O:.0f}  "
              f"(diff R{obs.R - true_state.R:+.0f} X{obs.X - true_state.X:+.0f} O{obs.O - true_state.O:+.0f})")
        
        r, done, _ = world.step(Action("hold", "A"))
        if done:
            break
    
    # Compare recover_fixed performance
    print(f"\n--- recover_fixed in NoisyObservationWorld (severe) ---")
    for seed in [1, 2, 3]:
        w = NoisyObservationWorld(cfg, seed=seed)
        for t in range(200):
            _, done, _ = w.step(Action("recover", "A"))
            if done:
                break
        print(f"  seed={seed}: score={w.state.cumulative_score:.2f}, steps={w.state.t}")
    
    print("\n[NoisyObservationWorld 動作確認 ✅]")
