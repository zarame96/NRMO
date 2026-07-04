"""
core/drifting_world.py

DriftingWorld — recover/A 一強の歪みを除去した別カオス world.

ChaoticWorld との違い:
  - recover/A は X を増やす方向 (放置 = 危険化)
  - invest/explore で X を下げられる (能動的な X 制御が必要)
  - O は時間で減衰 (機会窓に時間制限)
  - R は自然減少 (recover/A だけでは追いつかない)

NRMO v8.5.1 の真の generality 検証用:
  ChaoticWorld で機能した module diversity が
  DriftingWorld でも機能するかを確認.
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
    ChaoticEventLog,
)


class DriftingWorld(ChaoticWorld):
    """別構造のカオス world (recover/A 強化を排除)
    
    Key differences:
      - recover: X を増やす (放置できない)
      - invest:  X を下げる (能動的攻撃)
      - explore: X を軽く下げる + K, O 増
      - defend:  軽量、X 軽減
      - hold:    R 大消耗
      
      Natural decay:
        - R: -0.8/step (自然減少, recover/A 必要)
        - O: -0.5/step (機会窓減衰)
        - X: +0.5/step (危険自然上昇, attack 必要)
    """
    
    def _action_to_state_delta(self, action: Action) -> Dict[str, float]:
        """新 action mapping (recover/A 強化排除)"""
        intent = action.intent
        strength_mult = {"A": 0.6, "B": 1.0, "C": 1.6}.get(action.strength, 1.0)
        flip_mult = self.causal_flipper.get_flip_multiplier(intent)
        
        if intent == "invest":
            # 攻撃: R 消耗大、X 下げる、O 増、K 増 (active reduction of X)
            d = {"R": -8, "O": +5, "X": -6, "K": +2}
        elif intent == "defend":
            # 守り: 軽量、X 軽減
            d = {"R": -3, "X": -3, "O": -1}
        elif intent == "explore":
            # 探索: K + O + X 軽減
            d = {"R": -4, "K": +6, "O": +4, "X": -2}
        elif intent == "recover":
            # ★ 重要変更: recover は R 回復するが X 増加 (放置可能でない)
            d = {"R": +6, "E": +5, "G": +4, "O": -3, "X": +3}
        else:  # hold
            # ★ 重要変更: hold は X 増加大 (受け身ペナルティ)
            d = {"R": -2, "X": +3, "O": -2}
        
        return {k: v * strength_mult * flip_mult for k, v in d.items()}
    
    def _natural_decay(self):
        """time drift (受け身では生存できない設計)"""
        # 親クラスの decay も呼ぶ
        super()._natural_decay()
        # 追加 drift
        self.state.R = max(0, self.state.R - 0.5)   # R 自然減少
        self.state.O = max(0, self.state.O - 0.3)   # O 機会窓減衰
        self.state.X = min(100, self.state.X + 0.3) # X 自然上昇


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DriftingWorld Test")
    print("=" * 70)
    
    config = ChaosConfig.from_level("severe")
    world = DriftingWorld(config, seed=42)
    
    print(f"\nInitial state: R={world.state.R}, E={world.state.E}, "
          f"O={world.state.O}, X={world.state.X}")
    
    # Test 1: recover/A only (これは ChaoticWorld では強かった)
    print("\n--- recover/A only (DriftingWorld では生存困難なはず) ---")
    world1 = DriftingWorld(config, seed=42)
    for t in range(30):
        r, done, _ = world1.step(Action("recover", "A"))
        if t in [0, 5, 10, 15, 20, 25, 29]:
            print(f"  t={t+1:2d}: R={world1.state.R:.1f} E={world1.state.E:.1f} "
                  f"X={world1.state.X:.1f} O={world1.state.O:.1f}  "
                  f"score={world1.state.cumulative_score:.2f}  "
                  f"{'RUINED' if done else ''}")
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    # Test 2: invest/A only (DriftingWorld では強いはず)
    print("\n--- invest/A only ---")
    world2 = DriftingWorld(config, seed=42)
    for t in range(30):
        r, done, _ = world2.step(Action("invest", "A"))
        if t in [0, 5, 10, 15, 20, 25, 29]:
            print(f"  t={t+1:2d}: R={world2.state.R:.1f} E={world2.state.E:.1f} "
                  f"X={world2.state.X:.1f} O={world2.state.O:.1f}  "
                  f"score={world2.state.cumulative_score:.2f}  "
                  f"{'RUINED' if done else ''}")
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    # Test 3: mix (defend + invest)
    print("\n--- mix (R<40 で recover, X>60 で invest, else explore) ---")
    world3 = DriftingWorld(config, seed=42)
    for t in range(40):
        if world3.state.R < 40:
            a = Action("recover", "A")
        elif world3.state.X > 60:
            a = Action("invest", "A")
        else:
            a = Action("explore", "A")
        r, done, _ = world3.step(a)
        if t in [0, 5, 10, 20, 30, 39]:
            print(f"  t={t+1:2d}: R={world3.state.R:.1f} X={world3.state.X:.1f}  "
                  f"score={world3.state.cumulative_score:.2f}  ({a.intent}/{a.strength})  "
                  f"{'RUINED' if done else ''}")
        if done:
            print(f"  RUINED at step {t+1}, score={world3.state.cumulative_score:.2f}")
            break
    
    print("\n[DriftingWorld 動作確認 ✅]")
