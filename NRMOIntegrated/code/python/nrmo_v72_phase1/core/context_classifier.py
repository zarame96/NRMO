"""
core/context_classifier.py

Context classification for ContextualCandidateMerger (handoff doc § 8).

Contexts:
  Emergency:    R critical, X critical, ruin proximity high
  Recovery:     R low, E low, recent drawdown
  Defense:      X high, instability rising, downside rising
  Opportunity:  O high, O confidence high, R sufficient, X acceptable
  Stagnation:   score stagnation, opportunity loss, passive pattern
  Uncertainty:  observation noise high, model disagreement, info value high
  Normal:       none of the above strongly applies
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from collections import deque


class Context(Enum):
    EMERGENCY = "Emergency"
    RECOVERY = "Recovery"
    DEFENSE = "Defense"
    OPPORTUNITY = "Opportunity"
    STAGNATION = "Stagnation"
    UNCERTAINTY = "Uncertainty"
    NORMAL = "Normal"


@dataclass
class ContextClassification:
    """Context classification result"""
    primary_context: Context
    secondary_contexts: List[Context] = field(default_factory=list)
    context_confidence: float = 0.5
    reason: str = ""
    raw_scores: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "primary_context": self.primary_context.value,
            "secondary_contexts": [c.value for c in self.secondary_contexts],
            "context_confidence": self.context_confidence,
            "reason": self.reason,
            "raw_scores": self.raw_scores,
        }


class ContextClassifier:
    """Classify state + history into context (handoff doc § 8)"""
    
    # Emergency thresholds
    EMERGENCY_R = 15
    EMERGENCY_X = 80
    
    # Recovery thresholds
    RECOVERY_R = 35
    RECOVERY_E = 35
    
    # Defense thresholds
    DEFENSE_X = 60
    
    # Opportunity thresholds
    OPP_O = 60
    OPP_X_MAX = 65
    OPP_R_MIN = 40
    OPP_CONFIDENCE = 0.65
    
    def __init__(self):
        # state history for trend/stagnation detection
        self.r_history: deque = deque(maxlen=10)
        self.x_history: deque = deque(maxlen=10)
        self.reward_history: deque = deque(maxlen=10)
        self.action_history: deque = deque(maxlen=10)
    
    def update_history(self, state, action, reward: float = 0.0):
        self.r_history.append(float(state.R))
        self.x_history.append(float(state.X))
        self.reward_history.append(float(reward))
        if action is not None:
            self.action_history.append((action.intent, action.strength))
    
    def _score_emergency(self, state) -> float:
        if state.R <= self.EMERGENCY_R:
            return 0.9 + min(0.1, (self.EMERGENCY_R - state.R) / 30)
        if state.X >= self.EMERGENCY_X:
            return 0.9 + min(0.1, (state.X - self.EMERGENCY_X) / 30)
        if state.R <= 25 and state.X >= 70:
            return 0.7
        return 0.0
    
    def _score_recovery(self, state) -> float:
        if state.R > 50:
            return 0.0
        # R low or E low
        r_score = max(0, (self.RECOVERY_R - state.R) / self.RECOVERY_R)
        e_score = max(0, (self.RECOVERY_E - state.E) / self.RECOVERY_E)
        score = max(r_score, e_score)
        
        # Recent drawdown
        if len(self.r_history) >= 3:
            r_decline = self.r_history[0] - self.r_history[-1]
            if r_decline > 10:
                score += min(0.3, r_decline / 30)
        
        return min(1.0, score)
    
    def _score_defense(self, state) -> float:
        if state.X < 50:  # Defense は X 中程度から
            return 0.0
        # X=50 で 0.0, X=60 で 0.33, X=70 で 0.67, X=80 で 1.0
        score = (state.X - 50) / 30
        score = max(0, min(1.0, score))
        
        # X rising bonus
        if len(self.x_history) >= 3:
            x_rise = self.x_history[-1] - self.x_history[0]
            if x_rise > 5:
                score = min(1.0, score + min(0.2, x_rise / 25))
        
        return score
    
    def _score_opportunity(self, state, conditions: Optional[Dict] = None) -> float:
        if state.O < self.OPP_O:
            return 0.0
        if state.X > self.OPP_X_MAX:
            return 0.0
        if state.R < self.OPP_R_MIN:
            return 0.0
        
        # Base score from O
        score = (state.O - self.OPP_O) / 40
        
        # O confidence bonus
        if conditions:
            confidence = conditions.get("O_confidence", 0.7)
            if confidence < self.OPP_CONFIDENCE:
                score *= 0.5  # downweight low confidence
            else:
                score += (confidence - self.OPP_CONFIDENCE) * 0.5
        
        return min(1.0, score)
    
    def _score_stagnation(self, state) -> float:
        if len(self.reward_history) < 5:
            return 0.0
        recent_avg_reward = sum(self.reward_history) / len(self.reward_history)
        if recent_avg_reward > 0.1:
            return 0.0
        
        # Score stagnation: reward near zero + state not improving
        score = max(0, 0.5 - recent_avg_reward) * 2
        
        # State improvement check
        if len(self.r_history) >= 5:
            r_change = self.r_history[-1] - self.r_history[0]
            if abs(r_change) < 5:  # no movement
                score += 0.3
        
        return min(1.0, score)
    
    def _score_uncertainty(self, conditions: Optional[Dict] = None) -> float:
        if conditions is None:
            return 0.0
        obs_noise = conditions.get("observation_noise", 0.05)
        if obs_noise > 0.30:
            return min(1.0, obs_noise * 1.5)
        return obs_noise * 0.5
    
    def classify(self, state, conditions: Optional[Dict] = None
                  ) -> ContextClassification:
        """Classify current state into primary context"""
        scores = {
            Context.EMERGENCY: self._score_emergency(state),
            Context.RECOVERY: self._score_recovery(state),
            Context.DEFENSE: self._score_defense(state),
            Context.OPPORTUNITY: self._score_opportunity(state, conditions),
            Context.STAGNATION: self._score_stagnation(state),
            Context.UNCERTAINTY: self._score_uncertainty(conditions),
        }
        
        # Emergency has absolute priority
        if scores[Context.EMERGENCY] >= 0.7:
            primary = Context.EMERGENCY
            confidence = scores[Context.EMERGENCY]
            reason = f"R={state.R:.0f} critical or X={state.X:.0f} critical"
        else:
            # Pick highest score
            primary = max(scores, key=scores.get)
            primary_score = scores[primary]
            
            if primary_score < 0.30:
                primary = Context.NORMAL
                confidence = 0.7
                reason = "no context strongly applies"
            else:
                confidence = primary_score
                reason = f"{primary.value} score={primary_score:.2f}"
        
        # Secondary contexts (score >= 0.30, not primary)
        secondary = [c for c, s in scores.items()
                      if s >= 0.30 and c != primary]
        
        return ContextClassification(
            primary_context=primary,
            secondary_contexts=secondary,
            context_confidence=float(confidence),
            reason=reason,
            raw_scores={c.value: float(s) for c, s in scores.items()},
        )


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from world_models import WorldState
    
    print("=" * 70)
    print("ContextClassifier Test")
    print("=" * 70)
    
    classifier = ContextClassifier()
    
    test_cases = [
        ("Emergency", WorldState(t=0, R=12, E=20, G=30, O=50, K=50, X=85,
                                   cumulative_score=0, is_ruined=False)),
        ("Recovery", WorldState(t=0, R=25, E=20, G=50, O=40, K=50, X=40,
                                  cumulative_score=0, is_ruined=False)),
        ("Defense", WorldState(t=0, R=60, E=60, G=60, O=40, K=50, X=70,
                                 cumulative_score=0, is_ruined=False)),
        ("Opportunity", WorldState(t=0, R=60, E=70, G=60, O=80, K=50, X=30,
                                     cumulative_score=0, is_ruined=False)),
        ("Normal", WorldState(t=0, R=55, E=55, G=55, O=50, K=50, X=40,
                                cumulative_score=0, is_ruined=False)),
    ]
    
    for label, state in test_cases:
        conds = {"O_confidence": 0.8} if label == "Opportunity" else None
        result = classifier.classify(state, conditions=conds)
        print(f"\n{label} (R={state.R} E={state.E} O={state.O} X={state.X}):")
        print(f"  Primary: {result.primary_context.value} "
              f"(confidence {result.context_confidence:.2f})")
        print(f"  Secondary: {[c.value for c in result.secondary_contexts]}")
        print(f"  Reason: {result.reason}")
    
    print("\n[ContextClassifier 動作確認 ✅]")
