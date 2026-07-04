"""
core/contextual_candidate_merger.py

ContextualCandidateMerger (handoff doc § 7-10).

Replaces single-score CandidateMerger with:
  1. Emergency / true VETO check
  2. Context classification (delegated to ContextClassifier)
  3. Module eligibility filtering (§ 9)
  4. Context-dependent weighting
  5. Candidate scoring (with recovery penalties § 10)
  6. Repetition / diversity penalty
  7. Final candidate selection

Invariant (§ 7):
  Merger does NOT bypass NRMO Core, EmergencyResourceGuard,
  ActionIntensityThrottle, Calibration, or Revalidation.
  These are handled OUTSIDE Merger (in V851Engine pipeline).
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import deque

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from world_models import WorldState, Action
from context_classifier import Context, ContextClassification
from strong_engine_omega_full import FullCandidate


# ============================================================
# Module Eligibility Tables (handoff doc § 9)
# ============================================================

# Map: Context -> set of eligible module names
# Module names: "DefensiveCandidate", "RecoveryCandidate", "ExplorationCandidate",
#                "MutationPathway", "SynthesisPathway", "InventionPathway", "AggressiveEngine"

ELIGIBILITY_TABLE: Dict[Context, Dict[str, str]] = {
    # status: "eligible" | "suppressed" | "limited"
    Context.EMERGENCY: {
        "RecoveryCandidate":   "eligible",
        "DefensiveCandidate":  "eligible",
        "ExplorationCandidate": "suppressed",
        "MutationPathway":     "suppressed",
        "SynthesisPathway":    "suppressed",
        "InventionPathway":    "suppressed",
        "AggressiveEngine":    "suppressed",
    },
    Context.RECOVERY: {
        "RecoveryCandidate":   "eligible",
        "DefensiveCandidate":  "eligible",
        "ExplorationCandidate": "limited",      # only A strength
        "MutationPathway":     "limited",       # high-risk suppressed
        "SynthesisPathway":    "suppressed",
        "InventionPathway":    "suppressed",
        "AggressiveEngine":    "limited",       # B/C suppressed
    },
    Context.DEFENSE: {
        "RecoveryCandidate":   "eligible",
        "DefensiveCandidate":  "eligible",
        "ExplorationCandidate": "limited",      # A only
        "MutationPathway":     "limited",
        "SynthesisPathway":    "suppressed",
        "InventionPathway":    "suppressed",
        "AggressiveEngine":    "limited",       # B/C suppressed
    },
    Context.OPPORTUNITY: {
        "RecoveryCandidate":   "limited",       # downweight if R sufficient
        "DefensiveCandidate":  "limited",
        "ExplorationCandidate": "eligible",
        "MutationPathway":     "limited",
        "SynthesisPathway":    "eligible",
        "InventionPathway":    "limited",
        "AggressiveEngine":    "eligible",
    },
    Context.STAGNATION: {
        "RecoveryCandidate":   "limited",       # penalize if not improving
        "DefensiveCandidate":  "limited",
        "ExplorationCandidate": "eligible",
        "MutationPathway":     "eligible",
        "SynthesisPathway":    "eligible",
        "InventionPathway":    "eligible",
        "AggressiveEngine":    "limited",       # Small Reversible only
    },
    Context.UNCERTAINTY: {
        "RecoveryCandidate":   "eligible",
        "DefensiveCandidate":  "eligible",
        "ExplorationCandidate": "eligible",
        "MutationPathway":     "limited",
        "SynthesisPathway":    "limited",
        "InventionPathway":    "suppressed",
        "AggressiveEngine":    "suppressed",    # high-risk suppressed
    },
    Context.NORMAL: {
        "RecoveryCandidate":   "eligible",
        "DefensiveCandidate":  "eligible",
        "ExplorationCandidate": "eligible",
        "MutationPathway":     "limited",
        "SynthesisPathway":    "eligible",
        "InventionPathway":    "limited",
        "AggressiveEngine":    "limited",       # small reversible OK
    },
}


# ============================================================
# Context-Dependent Weights
# ============================================================

CONTEXT_WEIGHTS: Dict[Context, Dict[str, float]] = {
    # base weights: w_upside, w_downside, w_reversibility
    Context.EMERGENCY: {"upside": 0.5, "downside": 2.5, "reversibility": 1.0},
    Context.RECOVERY:  {"upside": 0.8, "downside": 1.8, "reversibility": 0.7},
    Context.DEFENSE:   {"upside": 0.7, "downside": 2.0, "reversibility": 0.7},
    # Opportunity: upside 重視, downside 軽減 (機会捕捉)
    Context.OPPORTUNITY: {"upside": 1.5, "downside": 1.0, "reversibility": 0.3},
    Context.STAGNATION:  {"upside": 1.3, "downside": 1.2, "reversibility": 0.4},
    Context.UNCERTAINTY: {"upside": 0.8, "downside": 1.5, "reversibility": 0.6},
    Context.NORMAL:      {"upside": 1.0, "downside": 1.5, "reversibility": 0.5},
}


# ============================================================
# ContextualCandidateMerger
# ============================================================

@dataclass
class MergerResult:
    """Merger 結果"""
    best_candidate: Optional[FullCandidate]
    best_score: float
    all_scored: List[Tuple[FullCandidate, float, str]]  # (cand, score, status)
    context: ContextClassification
    n_eligible: int
    n_suppressed: int
    diagnostics: Dict = field(default_factory=dict)


class ContextualCandidateMerger:
    """Context-aware candidate merging (handoff doc § 7-10)"""
    
    # Strength penalty for "limited" modules
    LIMITED_PENALTY_BASE = 0.15
    LIMITED_HIGH_STRENGTH_PENALTY = 0.30  # B/C in limited modules
    SUPPRESSED_HARD_PENALTY = 10.0  # 事実上除外
    
    # Recovery dominance penalties (§ 10)
    RECOVERY_R_HIGH_PENALTY = 0.30      # R >= 60
    RECOVERY_OPP_PENALTY = 0.25         # O>=70 + X<=60 + R>=40
    RECOVERY_CONSECUTIVE_PENALTY = 0.20  # per consecutive recover
    RECOVERY_STAGNATION_PENALTY = 0.20
    RECOVERY_LOW_MARGINAL_PENALTY = 0.20
    
    # Diversity penalty
    REPETITION_PENALTY_BASE = 0.10
    
    def __init__(self):
        self.consecutive_recover_count = 0
        self.last_selected_module: Optional[str] = None
        self.module_selection_history: deque = deque(maxlen=10)
        self.action_history: deque = deque(maxlen=10)
        
        # Stats
        self.stats = {
            "merges_total": 0,
            "candidates_seen": 0,
            "candidates_suppressed": 0,
            "candidates_limited": 0,
            "context_counts": {},
            "module_selection_counts": {},
            "context_module_table": {},  # context_name -> {module_name -> count}
        }
    
    # ============================================================
    # Score modifiers
    # ============================================================
    
    def _eligibility_status(self, candidate: FullCandidate,
                              context: Context) -> str:
        """Return: 'eligible' | 'suppressed' | 'limited'"""
        table = ELIGIBILITY_TABLE.get(context, ELIGIBILITY_TABLE[Context.NORMAL])
        return table.get(candidate.module, "limited")
    
    def _is_limited_high_strength(self, candidate: FullCandidate) -> bool:
        """B/C strength of limited modules"""
        if candidate.attack_candidate is None:
            return False
        return candidate.attack_candidate.strength in ("B", "C")
    
    def _base_score(self, candidate: FullCandidate, context: Context) -> float:
        """Context-dependent base scoring"""
        weights = CONTEXT_WEIGHTS[context]
        return (
            weights["upside"] * candidate.expected_upside
            - weights["downside"] * candidate.estimated_downside
            + weights["reversibility"] * candidate.reversibility
        )
    
    def _apply_recovery_penalties(self, candidate: FullCandidate,
                                    state: WorldState,
                                    context: Context,
                                    base_score: float) -> Tuple[float, List[str]]:
        """Recovery dominance penalties (handoff doc § 10)"""
        if candidate.module != "RecoveryCandidate":
            return base_score, []
        
        penalties = []
        score = base_score
        
        # R >= 60
        if state.R >= 60:
            score -= self.RECOVERY_R_HIGH_PENALTY
            penalties.append(f"R_high_{state.R:.0f}")
        
        # Opportunity context (O>=70 + X<=60 + R>=40)
        if state.O >= 70 and state.X <= 60 and state.R >= 40:
            score -= self.RECOVERY_OPP_PENALTY
            penalties.append("opp_context")
        
        # Consecutive recover
        if self.consecutive_recover_count >= 2:
            penalty = self.RECOVERY_CONSECUTIVE_PENALTY * self.consecutive_recover_count
            score -= penalty
            penalties.append(f"consec_recover_{self.consecutive_recover_count}")
        
        # Stagnation
        if context == Context.STAGNATION:
            score -= self.RECOVERY_STAGNATION_PENALTY
            penalties.append("stagnation_active")
        
        # Marginal recovery utility low (E and R both high → recovery low utility)
        if state.E >= 70 and state.R >= 50:
            score -= self.RECOVERY_LOW_MARGINAL_PENALTY
            penalties.append("low_marginal")
        
        return score, penalties
    
    def _apply_diversity_penalty(self, candidate: FullCandidate,
                                   score: float) -> Tuple[float, str]:
        """Repetition / diversity penalty (§ 7 step 6)"""
        if candidate.module == self.last_selected_module:
            # Same module selected last time
            penalty = self.REPETITION_PENALTY_BASE
            
            # Count consecutive same-module selections
            consec = 0
            for m in reversed(self.module_selection_history):
                if m == candidate.module:
                    consec += 1
                else:
                    break
            if consec >= 3:
                penalty += 0.10 * (consec - 2)
            
            return score - penalty, f"repetition_{consec+1}"
        return score, "no_repetition"
    
    def _apply_eligibility_modifier(self, candidate: FullCandidate,
                                       eligibility: str,
                                       score: float) -> Tuple[float, str]:
        """Apply eligibility-based score modifier"""
        if eligibility == "suppressed":
            return score - self.SUPPRESSED_HARD_PENALTY, "suppressed"
        elif eligibility == "limited":
            if self._is_limited_high_strength(candidate):
                # B/C strength in limited modules -> heavier penalty
                return score - self.LIMITED_HIGH_STRENGTH_PENALTY, "limited_BC"
            else:
                return score - self.LIMITED_PENALTY_BASE, "limited_A"
        return score, "eligible"
    
    # ============================================================
    # Main merge
    # ============================================================
    
    def merge(self, candidates: List[FullCandidate],
                state: WorldState,
                context: ContextClassification,
                additional_conditions: Optional[Dict] = None,
                # ★ sociable essence hooks (optional)
                failure_tracker=None,
                apply_canonical_dedup: bool = False,
                ) -> MergerResult:
        """全候補から最良を選ぶ (context-aware + sociable essence).
        
        Per sociable numbers エッセンス:
          - failure_tracker: pre-rejection
          - apply_canonical_dedup: candidate dedup
        """
        self.stats["merges_total"] += 1
        
        ctx_name = context.primary_context.value
        self.stats["context_counts"][ctx_name] = \
            self.stats["context_counts"].get(ctx_name, 0) + 1
        
        # === Sociable Essence Pre-processing ===
        if failure_tracker is not None:
            try:
                from loom_core import MODULE_TO_THREAD
                filtered = []
                n_rejected = 0
                for cand in candidates:
                    thread = MODULE_TO_THREAD.get(cand.module)
                    if thread is None:
                        filtered.append(cand)
                        continue
                    should_reject, _ = failure_tracker.should_pre_reject(
                        thread.value, state
                    )
                    if should_reject:
                        n_rejected += 1
                        continue
                    filtered.append(cand)
                if not filtered:
                    rec_keep = [c for c in candidates if c.module == "RecoveryCandidate"]
                    filtered = rec_keep[:1] if rec_keep else list(candidates[:1])
                candidates = filtered
                self.stats.setdefault("sociable_pre_rejected", 0)
                self.stats["sociable_pre_rejected"] += n_rejected
            except ImportError:
                pass
        
        if apply_canonical_dedup:
            try:
                from sociable_essence import CandidateCanonicalizer
                candidates, n_removed = CandidateCanonicalizer.deduplicate(candidates)
                self.stats.setdefault("sociable_dedup_removed", 0)
                self.stats["sociable_dedup_removed"] += n_removed
            except ImportError:
                pass
        
        if not candidates:
            return MergerResult(
                best_candidate=None,
                best_score=0.0,
                all_scored=[],
                context=context,
                n_eligible=0, n_suppressed=0,
            )
        
        scored: List[Tuple[FullCandidate, float, str]] = []
        n_eligible = 0
        n_suppressed = 0
        n_limited = 0
        
        for cand in candidates:
            self.stats["candidates_seen"] += 1
            
            # 1. Eligibility check
            eligibility = self._eligibility_status(cand, context.primary_context)
            
            # 2. Base score (context-dependent)
            base = self._base_score(cand, context.primary_context)
            
            # 3. Recovery penalties (§ 10)
            score_after_recovery, rec_penalties = self._apply_recovery_penalties(
                cand, state, context.primary_context, base
            )
            
            # 4. Eligibility modifier
            score_after_elig, elig_status = self._apply_eligibility_modifier(
                cand, eligibility, score_after_recovery
            )
            
            # 5. Diversity penalty
            final_score, div_status = self._apply_diversity_penalty(cand, score_after_elig)
            
            # Status string
            status_parts = [elig_status]
            if rec_penalties:
                status_parts.append("rec_pen:" + "+".join(rec_penalties))
            if div_status != "no_repetition":
                status_parts.append(div_status)
            status = "|".join(status_parts)
            
            scored.append((cand, final_score, status))
            
            if eligibility == "suppressed":
                n_suppressed += 1
                self.stats["candidates_suppressed"] += 1
            elif eligibility == "limited":
                n_limited += 1
                self.stats["candidates_limited"] += 1
            else:
                n_eligible += 1
        
        # Sort by score (descending)
        scored.sort(key=lambda x: -x[1])
        
        # Best candidate
        best_cand, best_score, best_status = scored[0]
        
        # Update history
        self.last_selected_module = best_cand.module
        self.module_selection_history.append(best_cand.module)
        if best_cand.attack_candidate:
            self.action_history.append(
                (best_cand.attack_candidate.intent, best_cand.attack_candidate.strength)
            )
        
        # Consecutive recover tracking
        if best_cand.module == "RecoveryCandidate":
            self.consecutive_recover_count += 1
        else:
            self.consecutive_recover_count = 0
        
        # Module selection stats
        self.stats["module_selection_counts"][best_cand.module] = \
            self.stats["module_selection_counts"].get(best_cand.module, 0) + 1
        
        # context × module table
        cm_table = self.stats["context_module_table"]
        if ctx_name not in cm_table:
            cm_table[ctx_name] = {}
        cm_table[ctx_name][best_cand.module] = \
            cm_table[ctx_name].get(best_cand.module, 0) + 1
        
        return MergerResult(
            best_candidate=best_cand,
            best_score=best_score,
            all_scored=scored,
            context=context,
            n_eligible=n_eligible,
            n_suppressed=n_suppressed,
            diagnostics={
                "selected_status": best_status,
                "n_limited": n_limited,
                "n_candidates_total": len(candidates),
            },
        )


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    from world_models import WorldState
    from context_classifier import ContextClassifier
    
    print("=" * 70)
    print("ContextualCandidateMerger Test")
    print("=" * 70)
    
    # Mock candidates
    candidates = [
        FullCandidate(
            module="RecoveryCandidate",
            attack_candidate=Action("recover", "A"),
            expected_upside=0.5, estimated_downside=0.05, reversibility=0.95,
            reason="recovery",
        ),
        FullCandidate(
            module="DefensiveCandidate",
            attack_candidate=Action("defend", "A"),
            expected_upside=0.3, estimated_downside=0.05, reversibility=0.95,
            reason="defensive",
        ),
        FullCandidate(
            module="AggressiveEngine",
            mode="wolf_pursuit",
            attack_candidate=Action("invest", "B"),
            expected_upside=0.7, estimated_downside=0.25, reversibility=0.55,
            reason="wolf pursuit",
        ),
        FullCandidate(
            module="ExplorationCandidate",
            attack_candidate=Action("explore", "A"),
            expected_upside=0.4, estimated_downside=0.10, reversibility=0.90,
            reason="explore",
        ),
    ]
    
    classifier = ContextClassifier()
    merger = ContextualCandidateMerger()
    
    test_states = [
        ("Opportunity", WorldState(t=0, R=60, E=70, G=60, O=80, K=50, X=30,
                                     cumulative_score=0, is_ruined=False)),
        ("Emergency", WorldState(t=0, R=12, E=20, G=30, O=50, K=50, X=85,
                                   cumulative_score=0, is_ruined=False)),
        ("Normal", WorldState(t=0, R=55, E=55, G=55, O=50, K=50, X=40,
                                cumulative_score=0, is_ruined=False)),
        ("Defense", WorldState(t=0, R=60, E=60, G=60, O=40, K=50, X=70,
                                 cumulative_score=0, is_ruined=False)),
    ]
    
    for label, state in test_states:
        print(f"\n[{label}] state R={state.R} E={state.E} O={state.O} X={state.X}")
        conds = {"O_confidence": 0.8}
        ctx = classifier.classify(state, conditions=conds)
        print(f"  Context: {ctx.primary_context.value} (conf {ctx.context_confidence:.2f})")
        
        result = merger.merge(candidates, state, ctx)
        print(f"  Best: {result.best_candidate.module} "
              f"({result.best_candidate.attack_candidate.intent}/{result.best_candidate.attack_candidate.strength})")
        print(f"  Score: {result.best_score:.3f}")
        print(f"  Status: {result.diagnostics['selected_status']}")
        print(f"  Eligible/Limited/Suppressed: {result.n_eligible}/{result.diagnostics['n_limited']}/{result.n_suppressed}")
        print(f"  All scored:")
        for c, s, st in result.all_scored:
            print(f"    {c.module:<22} {c.attack_candidate.intent}/{c.attack_candidate.strength}  "
                  f"score={s:+6.3f}  [{st}]")
    
    print("\n[ContextualCandidateMerger 動作確認 ✅]")
