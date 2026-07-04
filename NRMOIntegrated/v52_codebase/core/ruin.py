"""
core/ruin.py — Ruin detection and cause classification
========================================================
LAYER: GOVERNANCE
Ruin is a BOUNDARY CONDITION, not a utility penalty.
This module is called by NRMO Core, never by Engine.
Engine delegates ruin checks here via governance interface.
"""
from __future__ import annotations
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.state import CivState
from config.defaults import RuinThresholds

# ═══════════════════════════════════════════════
# Ruin pathway labels (SOURCE: monograph)
# ═══════════════════════════════════════════════
ALIVE               = "alive"
OVERSHOOT_COLLAPSE  = "overshoot_collapse"
ENVIRONMENT_COLLAPSE= "environment_collapse"
GOVERNANCE_COLLAPSE = "governance_collapse"
EXPOSURE_CASCADE    = "exposure_cascade"
STAGNATION_TRAP     = "stagnation_trap"
OPTIONALITY_COLLAPSE= "optionality_collapse"
KNOWLEDGE_FREEZE    = "knowledge_freeze"
COMPOUND_DECLINE    = "compound_decline"
RESOURCE_COLLAPSE   = "resource_collapse"

# ═══════════════════════════════════════════════
# TRUE RUIN — boundary condition, not penalty
# ═══════════════════════════════════════════════

def check_true_ruin(s: CivState, th: RuinThresholds) -> Optional[str]:
    """Returns ruin cause label if ruin, else None.
    This is an admissibility boundary check, not a score."""
    if s.X > th.X_ceiling: return EXPOSURE_CASCADE
    if s.R < th.R_floor:   return RESOURCE_COLLAPSE
    if s.E < th.E_floor:   return ENVIRONMENT_COLLAPSE
    if s.G < th.G_floor:   return GOVERNANCE_COLLAPSE
    if s.O < th.O_floor:   return OPTIONALITY_COLLAPSE
    return None

# ═══════════════════════════════════════════════
# PASSIVE RUIN — structural decline detection
# ═══════════════════════════════════════════════

def update_passive_ruin(s: CivState, th: RuinThresholds) -> Optional[str]:
    """Detect passive ruin patterns. Updates streak counters in-place."""
    if s.O < th.passive_O_threshold: s.low_O_streak += 1
    else: s.low_O_streak = max(0, s.low_O_streak - 2)
    if s.low_O_streak >= th.passive_O_streak: return STAGNATION_TRAP

    if s.K < th.passive_K_threshold: s.low_K_streak += 1
    else: s.low_K_streak = max(0, s.low_K_streak - 2)
    if s.low_K_streak >= th.passive_K_streak: return KNOWLEDGE_FREEZE

    o_dn = s.O < s.prev_O - 0.3
    g_dn = s.G < s.prev_G - 0.3
    k_flat = abs(s.K - s.prev_K) < 1.0
    if o_dn and g_dn and k_flat: s.compound_streak += 1
    else: s.compound_streak = max(0, s.compound_streak - 1)
    if s.compound_streak >= th.compound_streak: return COMPOUND_DECLINE

    s.prev_O = s.O; s.prev_G = s.G; s.prev_K = s.K
    return None

def detect_overshoot(s: CivState) -> bool:
    return s.growth_accum > 3.0 and s.true_ruin

# ═══════════════════════════════════════════════
# GOVERNANCE-PROVIDED RUIN CHECK FOR ROLLOUTS
# Engine calls this; it does NOT own the definition.
# ═══════════════════════════════════════════════

def is_ruin_state(s: CivState, th: RuinThresholds = RuinThresholds()) -> bool:
    """Governance-defined ruin boundary check.
    Engine may call this during rollout but CANNOT redefine it."""
    return check_true_ruin(s, th) is not None
