"""
core/viability.py — Avoidability Window (Viability Kernel approximation)
==========================================================================
LAYER: GOVERNANCE (shared utility, callable from Core AND Engine)

Introduced: v7.2 (TimeHorizonLayer / Horizon-Integrated Core revision)
Theory ref: NRMOIntegrated/chapters/ch27_time_horizon.tex (v7.2)
            NRMOIntegrated/docs/proposal_ch27_time_horizon_v2.md

Purpose:
    Approximate membership in the Viability Kernel — the set of states
    from which at least one action sequence exists that avoids True
    Ruin within a given horizon. Used to detect Passive Ruin: choosing
    an action, while the avoidability window is open, that closes it.

Design note (separation of concerns):
    This module extracts ONLY the Monte Carlo rollout-survival logic
    that already existed inside engine/omega_full.py::score_candidate().
    It deliberately does NOT import engine-specific scoring components
    (drift penalty, portfolio synergy, failure memory) — those remain
    execution-layer concerns. This keeps the governance/execution
    separation (INV-4 lineage) intact: Core may call this module,
    Engine may call this module, but this module does not encode any
    engine-specific optimisation objective.

Status: PROPOSAL-GRADE, UNVALIDATED (see ch27 v7.2 Open Items).
    No simulation results exist yet for this code path. Per project
    practice (v8.x precedent), this must be validated on the civ-sim
    side (MaxForwardEngine) before any real-side (Strong Engine)
    deployment.
"""
from __future__ import annotations
import numpy as np
from typing import Callable, Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.state import CivState, transition, SimConfig
from core.ruin import is_ruin_state, RuinThresholds


def _default_rollout_action(s: CivState) -> np.ndarray:
    """Fallback rollout policy when caller supplies none.
    Mirrors the world-adaptive default used in omega_full.py's
    riskadjusted_reference(), reproduced narrowly here to avoid
    importing engine-layer code into governance."""
    g = max(0.08, min(0.48, 0.36 - 0.18 * (s.X / 130)))
    sf = 0.26 + 0.16 * (s.X / 130)
    lr = 0.20
    di = max(0.05, 1 - g - sf - lr)
    a = np.clip(np.array([g, sf, lr, di]), 0.05, None)
    return a / a.sum()


def viability_score(
    state: CivState,
    wp: dict,
    rng: np.random.Generator,
    horizon: int,
    cfg: SimConfig = SimConfig(),
    th: RuinThresholds = RuinThresholds(),
    n_rollouts: int = 30,
    rollout_action_fn: Optional[Callable[[CivState], np.ndarray]] = None,
) -> float:
    """
    Approximate P(state is in the Viability Kernel at this horizon)
    via Monte Carlo rollout survival rate.

    Returns a value in [0.0, 1.0]. Higher = more of the sampled
    continuations avoid True Ruin within `horizon` steps.

    NOTE: this measures survival under a *fixed default policy*
    (or caller-supplied rollout_action_fn), not under an optimal
    policy. It is therefore a conservative *lower bound* on true
    Viability Kernel membership, not the kernel itself. This is a
    known approximation gap — see ch27 v7.2 §4.
    """
    action_fn = rollout_action_fn or _default_rollout_action
    survived = 0
    for _ in range(n_rollouts):
        s = state.copy()
        ruined = False
        for _ in range(horizon):
            a = action_fn(s)
            s = transition(s, a, wp, rng, cfg)
            if is_ruin_state(s, th):
                ruined = True
                break
        if not ruined:
            survived += 1
    return survived / n_rollouts


def window_open(
    state: CivState, wp: dict, rng: np.random.Generator, horizon: int,
    threshold: float = 0.5, **kwargs,
) -> bool:
    """True if the avoidability window is judged open at this horizon."""
    return viability_score(state, wp, rng, horizon, **kwargs) > threshold


def closes_window(
    state_after: CivState, wp: dict, rng: np.random.Generator, horizon: int,
    threshold: float = 0.5, **kwargs,
) -> bool:
    """True if state_after falls below the viability threshold —
    i.e. this candidate action would close a previously open window."""
    return viability_score(state_after, wp, rng, horizon, **kwargs) <= threshold


def passive_ruin_window_signal(
    state_before: CivState,
    candidate_action: np.ndarray,
    wp: dict,
    rng: np.random.Generator,
    cfg: SimConfig,
    horizon_set: list[int],
    threshold: float = 0.5,
    n_rollouts: int = 30,
) -> tuple[bool, Optional[int]]:
    """
    Core-facing entry point.

    Evaluates, for each horizon in horizon_set, whether applying
    candidate_action to state_before would move the state from
    "window open" to "window closed" (Passive Ruin, choice-time
    definition — ch27 v7.2 §2).

    Returns (signal: bool, binding_horizon: int | None).
    If multiple horizons trigger, the smallest (most urgent) is
    returned as binding_horizon — mirrors the True Ruin Minimax
    convention (most restrictive horizon governs).
    """
    state_after = transition(state_before.copy(), candidate_action, wp, rng, cfg)
    triggered = []
    for h in sorted(horizon_set):
        before_open = window_open(state_before, wp, rng, h,
                                   threshold=threshold, n_rollouts=n_rollouts)
        after_closed = closes_window(state_after, wp, rng, h,
                                      threshold=threshold, n_rollouts=n_rollouts)
        if before_open and after_closed:
            triggered.append(h)

    if triggered:
        return True, triggered[0]
    return False, None
