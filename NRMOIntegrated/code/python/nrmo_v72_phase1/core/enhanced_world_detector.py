"""
core/enhanced_world_detector.py

Drift-sensitive WorldDetector.

Per Zarameさん 指示 案 1:
  - X 連続上昇 trend を確定的 signal に
  - R 連続減少 trend を確定的 signal に
  - confidence threshold 0.45 → 0.25
  - history_size 15 → 8 (early detection)
"""
from __future__ import annotations
import os, sys
from typing import Optional, Tuple, List
from collections import deque
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState


class EnhancedWorldDetector:
    """Drift-sensitive 早期検出版.
    
    Detection logic:
      1. X 連続 3 step 上昇 (drift hint, ≥ +2/step)
      2. R 連続 3 step 減少 (drift hint, ≤ -2/step)
      3. 上記 2 条件で drift score を boost
      4. Confidence threshold 0.25 (低い = 早期発動)
      5. History 8 (早期判定可)
    """
    
    HISTORY_SIZE = 8         # 早期検出用 (元 15)
    DRIFT_MIN_HISTORY = 3    # drift 判定の最小 step (元 5)
    
    # Drift signature thresholds
    X_RISE_PER_STEP = 1.5     # X が 1 step あたり +1.5 以上 = drift sign
    R_DECAY_PER_STEP = 1.5    # R が 1 step あたり -1.5 以下 = drift sign
    CONSECUTIVE_NEEDED = 3    # この連続回数で確定的
    
    def __init__(self):
        self.history: deque = deque(maxlen=self.HISTORY_SIZE)
        self.x_rise_streak: int = 0
        self.r_decay_streak: int = 0
        self.prev_state: Optional[WorldState] = None
        self.early_drift_hint: bool = False  # 案 2 用
    
    def update(self, state: WorldState):
        self.history.append({
            "R": state.R, "E": state.E, "G": state.G,
            "O": state.O, "K": state.K, "X": state.X,
        })
        
        if self.prev_state is not None:
            dx = state.X - self.prev_state.X
            dr = state.R - self.prev_state.R
            
            # X rise streak
            if dx >= self.X_RISE_PER_STEP:
                self.x_rise_streak += 1
            else:
                self.x_rise_streak = 0
            
            # R decay streak
            if dr <= -self.R_DECAY_PER_STEP:
                self.r_decay_streak += 1
            else:
                self.r_decay_streak = 0
            
            # Early drift hint (案 2): X 上昇 OR R 減少 が 2+ step 連続
            self.early_drift_hint = (self.x_rise_streak >= 2 or 
                                        self.r_decay_streak >= 2)
        
        self.prev_state = state
    
    def detect_world_type(self) -> Tuple[str, float]:
        """Returns (world_type, confidence)"""
        n = len(self.history)
        if n < self.DRIFT_MIN_HISTORY:
            return "unknown", 0.0
        
        states = list(self.history)
        
        # === Drift detection: 強化版 ===
        # Method 1: X 持続上昇 / R 持続減少 streak (確定的 signal)
        x_drift_certain = self.x_rise_streak >= self.CONSECUTIVE_NEEDED
        r_drift_certain = self.r_decay_streak >= self.CONSECUTIVE_NEEDED
        
        # Method 2: 全 history 平均 trend
        if n >= 4:
            x_values = [s["X"] for s in states]
            r_values = [s["R"] for s in states]
            x_trend = float(np.polyfit(range(n), x_values, 1)[0])  # slope
            r_trend = float(np.polyfit(range(n), r_values, 1)[0])  # slope
            
            # drifting world: X 上昇 ∨ R 減少
            drift_score = 0.0
            if x_trend >= 0.8:
                drift_score += 0.35
            if x_trend >= 1.5:
                drift_score += 0.20
            if r_trend <= -0.8:
                drift_score += 0.30
            if r_trend <= -1.5:
                drift_score += 0.15
            
            # Streak boost (確定的)
            if x_drift_certain:
                drift_score += 0.40
            if r_drift_certain:
                drift_score += 0.30
            
            drift_score = min(1.0, drift_score)
        else:
            x_trend = 0
            r_trend = 0
            drift_score = 0.0
        
        # === Chaotic detection: variance based ===
        if n >= 4:
            # 各次元の variance
            r_var = float(np.var([s["R"] for s in states]))
            e_var = float(np.var([s["E"] for s in states]))
            g_var = float(np.var([s["G"] for s in states]))
            avg_var = (r_var + e_var + g_var) / 3.0
            
            # 高 variance + low trend = chaotic
            if avg_var > 50 and abs(x_trend) < 1.0 and abs(r_trend) < 1.0:
                chaotic_score = min(1.0, avg_var / 100.0)
            else:
                chaotic_score = max(0, avg_var / 200.0 - abs(x_trend) * 0.1)
        else:
            chaotic_score = 0.0
        
        # === Noisy detection: O / observation patterns ===
        if n >= 4:
            o_values = [s["O"] for s in states]
            o_var = float(np.var(o_values))
            if o_var > 80:
                noisy_score = min(1.0, o_var / 150.0)
            else:
                noisy_score = max(0, o_var / 200.0)
        else:
            noisy_score = 0.0
        
        # === Decision: 最大 score を world type に ===
        scores = {"drifting": drift_score, "chaotic": chaotic_score,
                    "noisy": noisy_score}
        best_world = max(scores, key=scores.get)
        best_score = scores[best_world]
        
        # Confidence threshold 0.25 (元 0.45)
        if best_score < 0.25:
            return "unknown", best_score
        
        return best_world, best_score
    
    def is_early_drift_hint(self) -> bool:
        """案 2: 早期 drift hint."""
        return self.early_drift_hint


if __name__ == "__main__":
    print("=" * 70)
    print("EnhancedWorldDetector Test")
    print("=" * 70)
    
    # Simulate drifting world (X 上昇, R 減少)
    print("\n--- Drifting world simulation ---")
    detector = EnhancedWorldDetector()
    for t in range(10):
        state = WorldState(t=t, R=70 - t*3, E=50, G=50, O=50, K=50,
                            X=20 + t*4,
                            cumulative_score=0, is_ruined=False)
        detector.update(state)
        wt, conf = detector.detect_world_type()
        hint = detector.is_early_drift_hint()
        print(f"  t={t}: R={state.R} X={state.X}, detected={wt} (conf={conf:.2f}), "
              f"hint={hint}, x_streak={detector.x_rise_streak}, "
              f"r_streak={detector.r_decay_streak}")
    
    # Simulate chaotic world (high variance, no trend)
    print("\n--- Chaotic world simulation ---")
    detector = EnhancedWorldDetector()
    rng = np.random.default_rng(42)
    for t in range(10):
        state = WorldState(t=t, R=50 + rng.normal(0, 10),
                            E=50 + rng.normal(0, 8), G=50, O=50, K=50,
                            X=40 + rng.normal(0, 5),
                            cumulative_score=0, is_ruined=False)
        detector.update(state)
        wt, conf = detector.detect_world_type()
        print(f"  t={t}: R={state.R:.0f} X={state.X:.0f}, detected={wt} (conf={conf:.2f})")
    
    print("\n[EnhancedWorldDetector 動作確認 ✅]")
