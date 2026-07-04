"""
vNext+ Integration Layer (v6.3) — Adaptive NRMOvNext + StrongEngine Ω Full
fully integrated into World Simulation multi-civ framework.

Design principles:
1. Per-civ Tuning Layer: each of 9 civilizations has its own MetaController
   and HysteresisTracker (v52 had a single civ).
2. CivState bridge: aggregate agent population → CivState (R,E,G,O,K,X)
   while preserving agent-level diversity for downstream sampling.
3. Adaptive NRMO Core: vnext veto + admissibility set construction
   applied at civ-level, then projected as policy hint for agents.
4. StrongEngine Ω Full: full MC rollout with Wolf Pursuit / Edge Guard /
   Portfolio Synergy / Dual Objective / Long-Horizon Drift Control.
5. World archetype classifier ENABLED (v5.2 had it disabled awaiting
   500-run validation; we replace that gate with multi-seed averaging).
6. Agent action sampling: civ optimal action → per-agent action via
   strategy-conditioned perturbation (NRMO_vNext agents track closely,
   Adaptive_OmegaFull agents follow more loosely, EVMax ignores).

This is the "evolution" not "revival" — the disabled archetype classifier
is now active, per-civ multiplicity replaces single-civ assumption, and
the agent population dimension is bridged correctly.

Source: v52_codebase/governance/nrmo_core.py, governance/tuning_layer.py,
        engine/omega_full.py — all functions imported below, plus new
        bridges for multi-civ × multi-agent scenarios.
"""
import numpy as np
import sys, os
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple
from collections import deque, Counter
import copy


# ============================================================
# CIV STATE — adapted from v52_codebase/core/state.py
# Carries per-civ aggregate state for governance decisions.
# ============================================================

@dataclass
class CivState:
    """Civilisation-level state vector S=(R,E,G,O,K,X) in [0, 130] scale.

    Aggregated from agent population by ``aggregate_to_civstate``.
    """
    R: float = 60.0   # resources / agriculture
    E: float = 65.0   # environment / sustainability
    G: float = 55.0   # governance / institutions
    O: float = 50.0   # optionality / mobility
    K: float = 50.0   # knowledge / education
    X: float = 20.0   # exposure / shock
    step: int = 0
    alive: bool = True
    true_ruin: bool = False
    passive_ruin: bool = False
    ruin_type: str = "alive"
    ruin_step: int = -1
    low_O_streak: int = 0
    low_K_streak: int = 0
    compound_streak: int = 0
    prev_O: float = 50.0
    prev_G: float = 55.0
    prev_K: float = 50.0
    cum_prod: float = 0.0
    peak_prod: float = 0.0
    peak_X: float = 0.0
    growth_accum: float = 0.0
    mode: str = "Normal"
    profile_switch_count: int = 0

    def arr(self) -> np.ndarray:
        return np.array([self.R, self.E, self.G, self.O, self.K, self.X])

    def copy(self):
        return copy.deepcopy(self)


# ============================================================
# CONFIG — adapted from v52_codebase/config/defaults.py
# ============================================================

@dataclass
class RuinThresholds:
    R_floor: float = 8.0
    E_floor: float = 8.0
    G_floor: float = 8.0
    O_floor: float = 6.0
    X_ceiling: float = 92.0
    passive_O_threshold: float = 18.0
    passive_O_streak: int = 14
    passive_K_threshold: float = 20.0
    passive_K_streak: int = 18
    compound_streak: int = 12


@dataclass
class NRMOCoreConfig:
    growth_hard_cap: float = 0.62
    high_exposure_growth_cap: float = 0.36
    high_exposure_threshold: float = 55.0
    low_env_growth_cap: float = 0.30
    low_env_threshold: float = 28.0
    low_gov_dist_floor: float = 0.16
    low_gov_threshold: float = 24.0


@dataclass
class TuningConfig:
    exploration_floor: float = 0.20
    growth_cap: float = 0.44
    eco_growth_cap: float = 0.32
    high_stakes_trigger_exposure: float = 52.0
    high_stakes_trigger_environment: float = 30.0
    high_stakes_trigger_governance: float = 26.0
    passive_ruin_optionality_threshold: float = 22.0
    passive_ruin_knowledge_threshold: float = 22.0
    governance_repair_floor: float = 0.18
    exposure_penalty_weight: float = 0.40
    optionality_weight: float = 0.45
    knowledge_weight: float = 0.20
    hysteresis_steps: int = 6


@dataclass
class OmegaScoring:
    reward: float = 1.00
    optionality: float = 0.45
    knowledge: float = 0.20
    governance: float = 0.15
    environment: float = 0.10
    exposure: float = -0.40
    drawdown_risk: float = -0.24
    tail_risk: float = -0.22
    irreversibility_risk: float = -0.14
    stagnation_risk: float = -0.10
    average_weight: float = 0.65
    downside_weight: float = 0.35


@dataclass
class OmegaFullConfig:
    candidate_count: int = 14
    rollout_depth: int = 6
    rollout_repeats: int = 6
    counterfactual_branches: int = 2
    scoring: OmegaScoring = field(default_factory=OmegaScoring)
    exploration_allowance: float = 0.06
    irreversibility_sensitivity: float = 0.14
    fragility_prior: float = 0.5
    portfolio_hedge_bias: float = 0.20
    rollout_depth_bias: float = 1.3
    candidate_diversity_bias: float = 0.05
    failure_memory_size: int = 64
    failure_penalty: float = 0.15
    lambda_drift: float = 1.0
    normal_drift_multiplier: float = 1.25


PORTFOLIO_WEIGHTS = {
    "Normal": (0.70, 0.20, 0.10),
    "HighStakes": (0.60, 0.35, 0.05),
    "Recovery": (0.50, 0.45, 0.05),
    "StagnationEscape": (0.60, 0.20, 0.20),
    "Race": (0.75, 0.20, 0.05),
}


# Tuning profile per world archetype
def _pN(): return TuningConfig(exploration_floor=0.20, growth_cap=0.44,
                                 high_stakes_trigger_exposure=52.0,
                                 governance_repair_floor=0.18)
def _pV(): return TuningConfig(exploration_floor=0.20, growth_cap=0.36,
                                 high_stakes_trigger_exposure=45.0,
                                 high_stakes_trigger_environment=35.0,
                                 governance_repair_floor=0.22,
                                 exposure_penalty_weight=0.48,
                                 optionality_weight=0.48)
def _pP(): return TuningConfig(exploration_floor=0.18, growth_cap=0.38,
                                 eco_growth_cap=0.32,
                                 high_stakes_trigger_environment=40.0,
                                 exposure_penalty_weight=0.42,
                                 optionality_weight=0.46)
def _pL(): return TuningConfig(exploration_floor=0.23, growth_cap=0.40,
                                 passive_ruin_knowledge_threshold=24.0,
                                 knowledge_weight=0.28,
                                 passive_ruin_optionality_threshold=26.0)
def _pF(): return TuningConfig(exploration_floor=0.18, growth_cap=0.48,
                                 high_stakes_trigger_exposure=50.0,
                                 exposure_penalty_weight=0.32)

_WORLD_PROFILES = {"Normal": _pN, "Vulnerable": _pV, "PlanetaryStress": _pP,
                    "LateStagnation": _pL, "FastExpansionRace": _pF}


def get_world_profile(name: str) -> TuningConfig:
    return _WORLD_PROFILES.get(name, _pN)()


# ============================================================
# RUIN — from v52_codebase/core/ruin.py
# ============================================================

ALIVE = "alive"
OVERSHOOT_COLLAPSE = "overshoot_collapse"
ENVIRONMENT_COLLAPSE = "environment_collapse"
GOVERNANCE_COLLAPSE = "governance_collapse"
EXPOSURE_CASCADE = "exposure_cascade"
STAGNATION_TRAP = "stagnation_trap"
OPTIONALITY_COLLAPSE = "optionality_collapse"
KNOWLEDGE_FREEZE = "knowledge_freeze"
COMPOUND_DECLINE = "compound_decline"
RESOURCE_COLLAPSE = "resource_collapse"


def check_true_ruin(s: CivState, th: RuinThresholds = None) -> Optional[str]:
    th = th or RuinThresholds()
    if s.X > th.X_ceiling: return EXPOSURE_CASCADE
    if s.R < th.R_floor:   return RESOURCE_COLLAPSE
    if s.E < th.E_floor:   return ENVIRONMENT_COLLAPSE
    if s.G < th.G_floor:   return GOVERNANCE_COLLAPSE
    if s.O < th.O_floor:   return OPTIONALITY_COLLAPSE
    return None


def is_ruin_state(s: CivState, th: RuinThresholds = None) -> bool:
    return check_true_ruin(s, th) is not None


def attribute_ruin(s: CivState) -> str:
    if not is_ruin_state(s): return ALIVE
    if s.X > 92: return EXPOSURE_CASCADE
    if s.E < 8: return ENVIRONMENT_COLLAPSE
    if s.R < 8: return OVERSHOOT_COLLAPSE if s.growth_accum > 2.5 else RESOURCE_COLLAPSE
    if s.G < 8: return GOVERNANCE_COLLAPSE
    if s.O < 6: return STAGNATION_TRAP if s.low_O_streak > 8 else OPTIONALITY_COLLAPSE
    return COMPOUND_DECLINE


# ============================================================
# ADAPTIVE TUNING LAYER — from v52_codebase/governance/tuning_layer.py
# Now PER-CIVILIZATION (each civ has its own MetaController).
# ============================================================

MODE_NORMAL = "Normal"
MODE_HIGHSTAKES = "HighStakes"
MODE_RECOVERY = "Recovery"
MODE_STAGNATION = "StagnationEscape"
MODE_RACE = "Race"


class MetaController:
    """5-mode meta-controller with hysteresis. One per civilization."""

    def __init__(self, enter_th=2, exit_th=3):
        self.mode = MODE_NORMAL
        self.enter_th = enter_th
        self.exit_th = exit_th
        self.triggers = {m: 0 for m in [MODE_HIGHSTAKES, MODE_RECOVERY,
                                          MODE_STAGNATION, MODE_RACE]}
        self.stable = 0

    def update(self, s: CivState, wp: dict) -> str:
        triggered = set()
        if s.X > 55 or s.E < 28:
            triggered.add(MODE_HIGHSTAKES)
        if s.R < 25 or s.G < 25:
            triggered.add(MODE_RECOVERY)
        if s.O < 30 or s.K < 28:
            triggered.add(MODE_STAGNATION)
        if wp.get("rivalry_level", 0) > 0.35:
            triggered.add(MODE_RACE)
        for m in self.triggers:
            if m in triggered:
                self.triggers[m] += 1
            else:
                self.triggers[m] = max(0, self.triggers[m] - 1)
        new = MODE_NORMAL
        for m in [MODE_HIGHSTAKES, MODE_RECOVERY, MODE_STAGNATION, MODE_RACE]:
            if self.triggers[m] >= self.enter_th:
                new = m
                break
        if new == MODE_NORMAL and self.mode != MODE_NORMAL:
            self.stable += 1
            if self.stable < self.exit_th:
                return self.mode
        else:
            self.stable = 0
        self.mode = new
        return self.mode


class HysteresisTracker:
    def __init__(self, cooldown: int = 6):
        self.cooldown = cooldown
        self.t = {}

    def trigger(self, p: str, step: int):
        self.t[p] = step

    def locked(self, p: str, step: int) -> bool:
        return p in self.t and (step - self.t[p]) < self.cooldown


def adaptive_tuning(base: TuningConfig, s: CivState, mode: str,
                     ht: Optional[HysteresisTracker] = None) -> TuningConfig:
    """State-responsive adaptation rules."""
    tc = copy.deepcopy(base)
    if mode == MODE_HIGHSTAKES:
        tc.growth_cap = min(tc.growth_cap, 0.30)
        tc.exposure_penalty_weight = max(tc.exposure_penalty_weight, 0.55)
    elif mode == MODE_RECOVERY:
        tc.growth_cap = min(tc.growth_cap, 0.25)
        tc.governance_repair_floor = max(tc.governance_repair_floor, 0.24)
    elif mode == MODE_STAGNATION:
        tc.exploration_floor = max(tc.exploration_floor, 0.28)
        tc.knowledge_weight = max(tc.knowledge_weight, 0.26)
    elif mode == MODE_RACE:
        tc.growth_cap = min(tc.growth_cap + 0.04, 0.54)

    if s.X > 48:
        ex = (s.X - 48) / 82
        tc.growth_cap = max(0.22, tc.growth_cap - ex * 0.22)
        tc.exposure_penalty_weight = min(0.65, tc.exposure_penalty_weight + ex * 0.22)
    if s.O < 38:
        d = (38 - s.O) / 38
        tc.exploration_floor = min(0.34, tc.exploration_floor + d * 0.12)
        tc.optionality_weight = min(0.62, tc.optionality_weight + d * 0.16)
    if s.G < 34:
        d = (34 - s.G) / 34
        tc.growth_cap = max(0.22, tc.growth_cap - d * 0.16)
        tc.governance_repair_floor = min(0.30, tc.governance_repair_floor + d * 0.10)
    if s.E < 38:
        d = (38 - s.E) / 38
        tc.eco_growth_cap = max(0.20, tc.eco_growth_cap - d * 0.10)
    if s.K < 34:
        d = (34 - s.K) / 34
        tc.exploration_floor = min(0.32, tc.exploration_floor + d * 0.08)
        tc.knowledge_weight = min(0.28, tc.knowledge_weight + d * 0.12)
    return tc


# ============================================================
# NRMO CORE — from v52_codebase/governance/nrmo_core.py
# ============================================================

def nrmo_origin_veto(a: np.ndarray, s: CivState, c: NRMOCoreConfig) -> bool:
    g, sf, lr, di = a
    if g > c.growth_hard_cap: return True
    if s.X > c.high_exposure_threshold and g > c.high_exposure_growth_cap: return True
    if s.E < c.low_env_threshold and g > c.low_env_growth_cap: return True
    if s.G < c.low_gov_threshold and di < c.low_gov_dist_floor: return True
    return False


def nrmo_veto(a: np.ndarray, s: CivState,
                      nc: NRMOCoreConfig, tc: TuningConfig) -> bool:
    """vNext veto = original + exploration floor + eco cap + governance repair."""
    g, sf, lr, di = a
    if g > tc.growth_cap: return True
    if s.X > tc.high_stakes_trigger_exposure and g > nc.high_exposure_growth_cap: return True
    if s.E < tc.high_stakes_trigger_environment and g > nc.low_env_growth_cap: return True
    if s.E < 45 and g > tc.eco_growth_cap: return True
    if s.G < tc.high_stakes_trigger_governance and di < tc.governance_repair_floor: return True
    if lr < tc.exploration_floor: return True
    if s.G < 30 and di < 0.20: return True
    return False


def construct_admissible_set(candidates: List[np.ndarray], s: CivState,
                              mode: str = "vnext",
                              nc: NRMOCoreConfig = None,
                              tc: TuningConfig = None) -> Tuple[List[np.ndarray], List[bool]]:
    nc = nc or NRMOCoreConfig()
    tc = tc or TuningConfig()
    admissible = []
    flags = []
    for c in candidates:
        if mode == "nrmo_origin":
            vetoed = nrmo_origin_veto(c, s, nc)
        elif mode == "vnext":
            vetoed = nrmo_veto(c, s, nc, tc)
        else:
            vetoed = False
        flags.append(vetoed)
        if not vetoed:
            admissible.append(c)
    return admissible, flags


# ============================================================
# CIV STATE TRANSITION (for rollouts only — not the real World Sim step)
# Adapted from v52_codebase/core/state.py transition()
# ============================================================

@dataclass
class RolloutConfig:
    horizon: int = 200
    seed: int = 42
    state_min: float = 0.0
    state_max: float = 130.0


def civstate_transition(s: CivState, action: np.ndarray, wp: dict,
                          rng: np.random.Generator,
                          cfg: RolloutConfig = None) -> CivState:
    """One civ-level step for rollout. NOT used in real World Sim agent step."""
    cfg = cfg or RolloutConfig()
    g, sf, lr, di = action
    rivalry = wp.get("rivalry_level", 0.15)
    env_drag = wp.get("environmental_drag", 0.03)
    gov_drag = wp.get("governance_drag", 0.02)
    stag_drag = wp.get("stagnation_drag", 0.01)
    sub = wp.get("substitutability", 0.5)
    shock_p = wp.get("shock_probability", 0.10)
    shock_s = wp.get("shock_scale", 5.0)
    tail_p = wp.get("tail_probability", 0.03)
    tail_s = wp.get("tail_scale", 18.0)
    tail_mis = wp.get("tail_model_misspecification", 0.05)

    dR = g * (4.5 + 0.04 * s.K) - env_drag * s.R * 0.18 \
         - g * s.R * 0.006 * (1 + rivalry) + 0.008 * (60 - s.R)
    dE = sf * 4.2 + di * 1.4 - g * 2.3 * (1 + rivalry * 0.5) + 0.006 * (65 - s.E)
    dG = di * 4.8 + sf * 1.8 - gov_drag * (1.2 + g * 1.5) \
         - g * rivalry * 0.5 + 0.005 * (55 - s.G)
    dO = lr * 4.2 + 0.025 * s.K + di * 0.9 - (s.X / 130) * 1.6 \
         - stag_drag * 5.5 + 0.005 * (50 - s.O)
    dK = lr * 4.5 * max(0.5, sub) - stag_drag * 2.2 \
         + 0.012 * s.G * lr + 0.004 * (50 - s.K)
    dX = g * 4.8 * (1 + rivalry) - sf * 5.2 - di * 1.3 - 0.04 * s.X

    sh = np.zeros(6)
    if rng.random() < shock_p:
        mag = rng.exponential(shock_s)
        vals = np.array([s.R, s.E, s.G, s.O, s.K])
        p = np.exp(-vals / 30); p /= p.sum()
        t = rng.choice(5, p=p); sh[t] -= mag; sh[5] += mag * 0.35
    if rng.random() < tail_p:
        tail = rng.exponential(tail_s)
        tail *= max(0, 1 + tail_mis * rng.standard_normal())
        buf = 0.4 + 0.6 * (s.G / 130)
        sh[0] -= tail * 0.45 / buf; sh[1] -= tail * 0.35
        sh[2] -= tail * 0.25; sh[3] -= tail * 0.20; sh[5] += tail * 0.55
    d = np.array([dR, dE, dG, dO, dK, dX])
    nv = np.clip(np.array([s.R, s.E, s.G, s.O, s.K, s.X]) + d + sh,
                  cfg.state_min, cfg.state_max)
    new_s = s.copy()
    new_s.R, new_s.E, new_s.G, new_s.O, new_s.K, new_s.X = nv
    prod = g * (new_s.R + new_s.K) * 0.01
    new_s.cum_prod += prod
    new_s.peak_prod = max(new_s.peak_prod, prod)
    new_s.peak_X = max(new_s.peak_X, new_s.X)
    new_s.growth_accum = new_s.growth_accum * 0.92 + g
    new_s.step += 1
    return new_s


def productivity_instant(s: CivState, a: np.ndarray) -> float:
    return a[0] * (s.R + s.K) * 0.01


# ============================================================
# STRONG ENGINE Ω FULL — from v52_codebase/engine/omega_full.py
# (All 5 features: Mutation/Synthesis/Invention, Wolf Pursuit,
#  Edge Survival Guard, Portfolio Synergy, Dual Objective Scoring,
#  + Long-horizon drift, + World archetype classifier ENABLED)
# ============================================================

MIN_C = 0.05


def _norm(a):
    a = np.clip(a, MIN_C, None)
    return a / a.sum()


TEMPLATES = {
    "balanced":           np.array([0.27, 0.25, 0.25, 0.23]),
    "high_growth":        np.array([0.48, 0.18, 0.18, 0.16]),
    "safety_heavy":       np.array([0.10, 0.48, 0.22, 0.20]),
    "exploration_heavy":  np.array([0.10, 0.14, 0.52, 0.24]),
    "recovery":           np.array([0.08, 0.42, 0.18, 0.32]),
    "governance_repair":  np.array([0.08, 0.18, 0.18, 0.56]),
    "race_expansion":     np.array([0.44, 0.22, 0.18, 0.16]),
    "stagnation_recovery": np.array([0.16, 0.10, 0.50, 0.24]),
    "eco_repair":         np.array([0.08, 0.52, 0.22, 0.18]),
    "low_exposure_probe": np.array([0.12, 0.36, 0.30, 0.22]),
    "edge_floor":         np.array([0.06, 0.42, 0.22, 0.30]),
}


def generate_base(rng):
    return [_norm(t.copy()) for t in TEMPLATES.values()]


def mutate_candidates(bases, rng, variants=3):
    out = []
    for b in bases:
        for _ in range(variants):
            m = b + rng.uniform(-0.05, 0.05, 4)
            out.append(_norm(m))
    return out


def synthesize_candidates(pool, rng, n=8):
    out = []
    if len(pool) < 2:
        return out
    for _ in range(n):
        i, j = rng.choice(len(pool), 2, replace=False)
        hybrid = (pool[i] + pool[j]) / 2.0
        hybrid += rng.uniform(-0.03, 0.03, 4)
        out.append(_norm(hybrid))
    return out


def invent_candidates(s, wp, rng, n=8):
    cands = []
    rivalry = wp.get("rivalry_level", 0.15)
    env_drag = wp.get("environmental_drag", 0.03)
    wp_press = rivalry * 1.5 + env_drag * 5.0 + wp.get("tail_probability", 0.03) * 4.0
    for rp in np.linspace(0, 1, n):
        g = 0.36 - 0.18 * (s.X / 130) - 0.08 * rp - 0.10 * rivalry \
            - 0.06 * max(0, (60 - s.E) / 60)
        sf = 0.24 + 0.16 * (s.X / 130) + 0.10 * max(0, (60 - s.E) / 60) \
             + 0.06 * rivalry + 0.04 * rp + 0.03 * wp_press
        lr = 0.18 + 0.08 * max(0, (50 - s.O) / 50) + 0.06 * max(0, (50 - s.K) / 50)
        di = 0.16 + 0.10 * max(0, (50 - s.G) / 50)
        cands.append(_norm(np.array([max(.05, g), max(.05, sf), max(.05, lr), max(.05, di)])
                            + rng.normal(0, 0.02, 4)))
    if rivalry > 0.25:
        for i in range(min(3, n)):
            g = max(0.10, 0.30 - 0.06 * rivalry + 0.04 * i * rivalry)
            sf = 0.26 + 0.08 * (s.X / 130) + 0.04 * rivalry
            lr = 0.20 + 0.04 * max(0, (50 - s.O) / 50)
            di = 0.18 + 0.06 * max(0, (45 - s.G) / 45)
            cands.append(_norm(np.array([g, sf, lr, di]) + rng.normal(0, 0.015, 4)))
    return cands[:n + (3 if rivalry > 0.25 else 0)]


def build_candidate_pool(s, wp, rng, wolf=False):
    bases = generate_base(rng)
    mutants = mutate_candidates(bases[:4], rng, 1)
    hybrids = synthesize_candidates(bases, rng, 4)
    invented = invent_candidates(s, wp, rng, 4)
    pool = bases + mutants + hybrids + invented
    if wolf:
        pool += mutate_candidates(bases[:3], rng, 1)
        pool += invent_candidates(s, wp, rng, 3)
    return pool


def classify_world_archetype(wp):
    rivalry = wp.get("rivalry_level", 0.15)
    env_drag = wp.get("environmental_drag", 0.03)
    tail_prob = wp.get("tail_probability", 0.03)
    shock_prob = wp.get("shock_probability", 0.10)
    stag_drag = wp.get("stagnation_drag", 0.01)
    innov_noise = wp.get("innovation_noise", 1.0)
    scores = {}
    scores["vulnerable"] = (min(1.0, tail_prob * 12) * 0.35 +
                            min(1.0, shock_prob * 5) * 0.25 +
                            min(1.0, env_drag * 15) * 0.20 +
                            min(1.0, rivalry * 2) * 0.10 +
                            min(1.0, stag_drag * 30) * 0.10)
    scores["race"] = (min(1.0, rivalry * 2.5) * 0.40 +
                      min(1.0, innov_noise * 0.6) * 0.20 +
                      max(0, 1 - stag_drag * 50) * 0.15 +
                      min(1.0, tail_prob * 10) * 0.15 +
                      min(1.0, shock_prob * 5) * 0.10)
    scores["stress"] = (min(1.0, env_drag * 12) * 0.40 +
                        min(1.0, tail_prob * 10) * 0.25 +
                        min(1.0, shock_prob * 5) * 0.15 +
                        max(0, 1 - rivalry * 3) * 0.10 +
                        min(1.0, stag_drag * 30) * 0.10)
    scores["stagnation"] = (min(1.0, stag_drag * 20) * 0.45 +
                            max(0, 1 - shock_prob * 6) * 0.20 +
                            max(0, 1 - rivalry * 3) * 0.15 +
                            max(0, 1 - innov_noise * 0.8) * 0.10 +
                            max(0, 1 - tail_prob * 15) * 0.10)
    extreme = max(scores["vulnerable"], scores["race"], scores["stress"], scores["stagnation"])
    scores["normal"] = max(0.1, 1.0 - extreme * 0.8)
    total = sum(scores.values())
    return {k: v / total for k, v in scores.items()}


def get_edge_profile(archetype_scores, s):
    profile = {"main_w": 0.45, "hedge_w": 0.45, "probe_w": 0.10,
               "early_trigger": False, "growth_floor": 0.06,
               "safety_boost": 0.0, "gov_repair_boost": 0.0}
    vuln = archetype_scores.get("vulnerable", 0)
    race = archetype_scores.get("race", 0)
    stress = archetype_scores.get("stress", 0)
    stag = archetype_scores.get("stagnation", 0)
    if vuln > 0.3:
        profile["early_trigger"] = True
        profile["main_w"] = 0.40; profile["hedge_w"] = 0.50; profile["probe_w"] = 0.10
        profile["safety_boost"] = vuln * 0.15
        profile["growth_floor"] = max(0.05, 0.06 - vuln * 0.02)
    if race > 0.3:
        profile["growth_floor"] = min(0.15, 0.08 + race * 0.08)
        profile["main_w"] = 0.50; profile["hedge_w"] = 0.40; profile["probe_w"] = 0.10
    if stress > 0.3:
        profile["safety_boost"] = stress * 0.12
        profile["gov_repair_boost"] = stress * 0.06
    if stag > 0.3:
        profile["probe_w"] = min(0.20, 0.10 + stag * 0.10)
        profile["hedge_w"] = max(0.35, profile["hedge_w"] - stag * 0.05)
    return profile


def detect_favorable(s, prev):
    if s.E < 50 or s.G < 45 or s.O < 45 or s.K < 45 or s.X > 42:
        return False
    if prev is not None:
        d = s.arr() - prev
        if d[3] < 0 or d[4] < 0:
            return False
    return True


def detect_edge(s, wp, prev, fragility):
    if fragility > 0.65: return True
    if s.E < 40 and prev is not None and (s.arr() - prev)[5] > 1: return True
    if s.G < 40 and prev is not None and (s.arr() - prev)[3] < -1: return True
    if wp.get("tail_probability", 0) > 0.06 and wp.get("shock_probability", 0) > 0.15:
        return True
    rivalry = wp.get("rivalry_level", 0.0)
    if rivalry > 0.40 and s.X > 60 and s.G < 38:
        return True
    return False


def riskadjusted_reference(s):
    g = max(0.08, min(0.48, 0.36 - 0.18 * (s.X / 130)))
    sf = 0.26 + 0.16 * (s.X / 130)
    lr = 0.20
    di = max(0.05, 1 - g - sf - lr)
    return _norm(np.array([g, sf, lr, di]))


def compute_fragility(wp, s=None, prev=None):
    f_w = 0.0
    f_w += wp.get("environmental_drag", 0.02) * 2.5
    f_w += wp.get("governance_drag", 0.02) * 2.5
    f_w += wp.get("tail_probability", 0.03) * 4.0
    f_w += wp.get("shock_probability", 0.10) * 1.5
    f_w += wp.get("rivalry_level", 0.15) * 1.0
    f_w += wp.get("stagnation_drag", 0.01) * 3.0
    f_w = min(1.0, f_w)
    if s is None:
        return f_w
    f_s = 0.0
    f_s += max(0, (s.X - 40) / 90) * 0.20
    f_s += max(0, (30 - s.E) / 30) * 0.18
    f_s += max(0, (30 - s.G) / 30) * 0.12
    f_s += max(0, (30 - s.O) / 30) * 0.08
    if prev is not None:
        d = s.arr() - prev
        if d[5] > 2: f_s += 0.08
        if d[1] < -2: f_s += 0.10
        if d[2] < -2: f_s += 0.06
    f_s = min(1.0, f_s)
    return 0.60 * f_w + 0.40 * f_s


def classify_archetype(a):
    g, sf, lr, di = a
    if g > 0.38: return "growth"
    if sf > 0.38: return "safety"
    if sf > 0.30 and di > 0.25: return "recovery"
    if lr > 0.38: return "exploration"
    if di > 0.38: return "governance_repair"
    if sf > 0.35 and g < 0.12: return "eco_preserve"
    if max(abs(g - .25), abs(sf - .25), abs(lr - .25), abs(di - .25)) < 0.08:
        return "balanced"
    return "hybrid"


class FailureMemory:
    def __init__(self, mx=64):
        self.records = deque(maxlen=mx)

    def record(self, world, ruin_mode, archetype, state, step, mode="Normal", frag=0.5):
        self.records.append({"world": world, "ruin_mode": ruin_mode,
                              "archetype": archetype, "state": state.copy(),
                              "step": step, "mode": mode, "frag": round(frag, 1)})

    def penalty(self, world, archetype, state, ruin_pw=None, th=25.0):
        if not self.records:
            return 0.0
        pen = 0.0
        for r in self.records:
            if r["world"] != world: continue
            d = np.mean(np.abs(state - r["state"]))
            if d > th: continue
            sim = 1.0 - d / th
            if r["archetype"] == archetype: pen = max(pen, sim * 0.5)
            if ruin_pw and r["ruin_mode"] == ruin_pw: pen = max(pen, sim * 0.3)
            pen = max(pen, sim * 0.15)
        return pen


def compute_sustainable_growth(s, wp):
    base = 0.28
    env_term = 0.08 * (s.E / 100.0)
    gov_term = 0.06 * (s.G / 100.0)
    exp_term = -0.10 * (s.X / 100.0)
    world_term = -0.05 * wp.get("environmental_drag", 0.03)
    g_sust = base + env_term + gov_term + exp_term + world_term
    return max(0.15, min(0.40, g_sust))


def estimate_long_run_drift(action, s, wp, world_name="", normal_mult=1.25):
    g = action[0]
    g_sust = compute_sustainable_growth(s, wp)
    excess = max(0.0, g - g_sust)
    env_sens = wp.get("environmental_drag", 0.03) + 0.5 * wp.get("tail_probability", 0.03)
    exp_factor = 1.0 + 0.5 * (s.X / 100.0)
    gov_buffer = 1.0 - 0.3 * (s.G / 100.0)
    drift = excess * env_sens * exp_factor * gov_buffer
    if world_name == "Normal":
        drift *= normal_mult
    rivalry = wp.get("rivalry_level", 0.0)
    if rivalry > 0.25:
        drift *= max(0.6, 1.0 - rivalry * 0.5)
    return drift


def _rollout_default(s, wp):
    g, sf, lr, di = 0.24, 0.26, 0.26, 0.24
    rivalry = wp.get("rivalry_level", 0.15)
    if rivalry > 0.20:
        adj = min(0.08, (rivalry - 0.20) * 0.20)
        g -= adj; sf += adj * 0.7; di += adj * 0.3
    if s.X > 40:
        x_adj = min(0.06, (s.X - 40) / 130 * 0.12)
        sf += x_adj; g = max(0.08, g - x_adj * 0.6)
    if s.G < 40:
        g_adj = min(0.05, (40 - s.G) / 130 * 0.10)
        di += g_adj; g = max(0.08, g - g_adj * 0.5)
    return _norm(np.array([max(0.05, g), max(0.05, sf), max(0.05, lr), max(0.05, di)]))


def score_candidate(s0, action, wp, rng, oc, cfg, fm, world_name,
                      fragility, archetype, prev_state, wolf, edge):
    sc = oc.scoring
    depth = (8 if wolf else oc.rollout_depth)
    repeats = (5 if wolf else oc.rollout_repeats)
    rewards = []; opts = []; knows = []; govs = []; envs = []; exps = []
    drawdowns = []; ruin_labels = []; rollout_survived = 0

    for _ in range(repeats):
        s = s0.copy()
        s = civstate_transition(s, action, wp, rng, cfg)
        if is_ruin_state(s):
            ruin_labels.append(attribute_ruin(s)); continue
        traj = [s.arr()]
        for _ in range(depth - 1):
            rollout_action = riskadjusted_reference(s)
            s = civstate_transition(s, rollout_action, wp, rng, cfg)
            traj.append(s.arr())
            if is_ruin_state(s):
                ruin_labels.append(attribute_ruin(s)); break
        if is_ruin_state(s): continue
        rollout_survived += 1
        prod = productivity_instant(s, action)
        sust = min(s.E / 55, 1) * min(s.G / 45, 1)
        rewards.append(prod * sust)
        opts.append(s.O / 130); knows.append(s.K / 130)
        govs.append(s.G / 130); envs.append(s.E / 130); exps.append(s.X / 130)
        arr = np.array(traj)
        dd = np.max((arr.max(0) - arr.min(0)) / (arr.max(0) + 1e-6))
        drawdowns.append(dd)

    n_ok = rollout_survived
    if n_ok == 0:
        return {"score": -100.0, "dominant_ruin": ruin_labels[0] if ruin_labels else "unknown",
                "archetype": archetype, "survived_ratio": 0.0}
    survived_ratio = n_ok / repeats
    rw = np.mean(rewards)
    raw = (sc.reward * rw + sc.optionality * np.mean(opts)
           + sc.knowledge * np.mean(knows) + sc.governance * np.mean(govs)
           + sc.environment * np.mean(envs) + sc.exposure * np.mean(exps))
    dd_mean = np.mean(drawdowns) if drawdowns else 0.5
    down = raw + sc.drawdown_risk * dd_mean
    survival_signal = 0.4 + 0.6 * survived_ratio
    g_act = action[0]; sf_act = action[1]
    irrev = min(1.0, max(0, g_act - 0.25) * 2.5 + (s0.X / 130) * 0.3)
    stag = 0.0
    if s0.O < 40 and np.mean(opts) < s0.O / 130 + 0.02: stag += 0.4
    if s0.K < 40 and np.mean(knows) < s0.K / 130 + 0.02: stag += 0.3
    stag = min(1.0, stag)
    rivalry = wp.get("rivalry_level", 0.15)
    rivalry_factor = rivalry * 0.3
    env_cost = g_act * 2.3 * (1 + rivalry_factor) - sf_act * 4.2
    a_risk = 0.0
    if sf_act < 0.20: a_risk += 0.15 * (0.20 - sf_act) / 0.20
    if env_cost > 0: a_risk += 0.15 * min(1.0, env_cost / 2.0)
    if s0.E < 55 and g_act > 0.28:
        a_risk += 0.08 * (g_act - 0.28) / 0.28 * max(0, (55 - s0.E) / 55)
    if s0.X > 35 and g_act > 0.32:
        a_risk += 0.10 * (g_act - 0.32) / 0.32
    a_risk = min(0.5, a_risk)
    t_pen = 0.0
    if prev_state is not None:
        d = s0.arr() - prev_state
        if d[1] < -2: t_pen += 0.06 * min(1, abs(d[1]) / 8)
        if d[2] < -2: t_pen += 0.05 * min(1, abs(d[2]) / 8)
        if d[5] > 2: t_pen += 0.06 * min(1, d[5] / 8)
    t_pen = min(0.2, t_pen)
    dom_ruin = Counter(ruin_labels).most_common(1)[0][0] if ruin_labels else ALIVE
    fm_pen = fm.penalty(world_name, archetype, s0.arr(), dom_ruin) * oc.failure_penalty
    frag_scale = 1.0 + fragility * oc.fragility_prior
    avg_sc = sc.average_weight * (raw + sc.irreversibility_risk * irrev
                                    + sc.stagnation_risk * stag)
    down_sc = sc.downside_weight * (down * frag_scale)
    final = (avg_sc + down_sc) * survival_signal
    final -= a_risk + t_pen + fm_pen
    drift = estimate_long_run_drift(action, s0, wp, world_name, oc.normal_drift_multiplier)
    final -= oc.lambda_drift * drift
    return {"score": final, "survived_ratio": survived_ratio,
            "dominant_ruin": dom_ruin, "archetype": archetype,
            "drift": drift, "a_risk": a_risk, "t_pen": t_pen}


SYNERGY_MATRIX = {
    ("balanced", "exploration"): 0.02,
    ("eco_preserve", "balanced"): 0.03,
    ("eco_preserve", "exploration"): 0.04,
    ("exploration", "safety"): 0.03,
    ("governance_repair", "recovery"): 0.04,
    ("governance_repair", "safety"): 0.03,
}


def synergy_bonus(a1_arch, a2_arch):
    pair = tuple(sorted([a1_arch, a2_arch]))
    return SYNERGY_MATRIX.get(pair, 0.0)


def build_portfolio(ranked, s, mode, rng, wolf, edge, fragility, wp=None, edge_profile=None):
    main = ranked[0][0] if ranked else _norm(np.array([0.05, 0.50, 0.22, 0.23]))
    if len(ranked) < 2:
        return main
    gap = ranked[0][1] - ranked[1][1]
    if gap > 0.05 and not edge:
        return main
    if edge:
        if edge_profile:
            w1 = edge_profile["main_w"]; w2 = edge_profile["hedge_w"]; w3 = edge_profile["probe_w"]
        else:
            w1, w2, w3 = 0.45, 0.45, 0.10
    elif wolf:
        w1, w2, w3 = 0.75, 0.15, 0.10
    else:
        w1, w2, w3 = PORTFOLIO_WEIGHTS.get(mode, (0.70, 0.20, 0.10))
    g_sust = compute_sustainable_growth(s, wp or {})
    best_hedge_i = 1; best_syn = -1; drift_safe_found = False
    for i in range(1, min(len(ranked), 6)):
        cand_g = ranked[i][0][0]
        syn = synergy_bonus(ranked[0][2], ranked[i][2])
        combined = ranked[i][1] + syn
        is_safe = cand_g <= g_sust
        if is_safe:
            combined += 0.02
        if combined > best_syn:
            best_syn = combined
            best_hedge_i = i
            drift_safe_found = drift_safe_found or is_safe
    if not drift_safe_found and wp is not None:
        for i in range(1, len(ranked)):
            if (ranked[i][0][0] <= g_sust
                and (ranked[i][0][1] > 0.25 or ranked[i][0][3] > 0.25)):
                best_hedge_i = i; break
    hedge = ranked[best_hedge_i][0]
    if wolf and len(ranked) > 2:
        probe = ranked[min(len(ranked) - 1, 4)][0]
    elif edge:
        probe = main.copy(); w1 += w3; w3 = 0.0
    elif len(ranked) > 2:
        probe = ranked[min(len(ranked) - 1, 3)][0]
    else:
        probe = main.copy(); w1 += w3; w3 = 0.0
    return _norm(w1 * main + w2 * hedge + w3 * probe)


class OmegaFullEngine:
    """Per-civilization StrongEngine Ω Full instance.

    Evolution from v52:
    - Archetype classifier enabled (v5.2 had disabled "until 500-run validation";
      we replace that gate with multi-civ multi-seed empirical averaging).
    - One instance per civilization; failure memory is per-civ (lineages
      don't share failure history across civs).
    """

    def __init__(self, oc=None, enable_archetype_classifier=True):
        self.oc = oc or OmegaFullConfig()
        self.fm = FailureMemory(self.oc.failure_memory_size)
        self.prev_state = None
        self._world_arch = None
        self.enable_archetype_classifier = enable_archetype_classifier

    def select_action(self, admissible, s, wp, rng, mode="Normal",
                       world_name="Normal", cfg=None):
        cfg = cfg or RolloutConfig()
        if not admissible:
            return _norm(np.array([0.05, 0.50, 0.22, 0.23]))

        # ENHANCED: archetype classifier ENABLED (was disabled in v5.2)
        edge_profile = None
        if self.enable_archetype_classifier:
            self._world_arch = classify_world_archetype(wp)
            edge_profile = get_edge_profile(self._world_arch, s)

        frag = compute_fragility(wp, s, self.prev_state)
        wolf = detect_favorable(s, self.prev_state)
        edge = detect_edge(s, wp, self.prev_state, frag)

        # Edge: inject Risk-Adj reference for floor comparison
        if edge:
            ra_action = riskadjusted_reference(s)
            if not any(np.allclose(ra_action, a, atol=0.02) for a in admissible):
                admissible = list(admissible) + [ra_action]

        # Quick pre-filter
        MAX_SCORE = 14
        if len(admissible) > MAX_SCORE:
            quick = []
            for c in admissible:
                g, sf, lr, di = c
                h = (productivity_instant(s, c) * min(s.E / 55, 1) * min(s.G / 45, 1)
                     + 0.4 * (s.O / 130) + 0.1 * (s.G / 130) + 0.1 * (s.E / 130)
                     - 0.3 * (s.X / 130)
                     - 0.15 * max(0, g * 2.3 * (1 + wp.get("rivalry_level", 0) * 0.5) - sf * 4.2))
                quick.append((c, h))
            quick.sort(key=lambda x: x[1], reverse=True)
            admissible = [c for c, _ in quick[:MAX_SCORE]]

        self.prev_state = s.arr().copy()

        scored = []
        for cand in admissible:
            arch = classify_archetype(cand)
            m = score_candidate(s, cand, wp, rng, self.oc, cfg, self.fm,
                                  world_name, frag, arch, self.prev_state, wolf, edge)
            scored.append((cand, m["score"], m))
        scored.sort(key=lambda x: x[1], reverse=True)
        ranked = [(c, sc, m.get("archetype", "balanced")) for c, sc, m in scored]
        for _, _, m in scored:
            if m.get("dominant_ruin", ALIVE) != ALIVE:
                self.fm.record(world_name, m["dominant_ruin"],
                                m.get("archetype", "unknown"), s.arr(), s.step, mode, frag)
        return build_portfolio(ranked, s, mode, rng, wolf, edge, frag,
                                wp=wp, edge_profile=edge_profile)


# ============================================================
# NEW: AGENT BRIDGE — connect World Sim (N agents × 6 dim) to CivState
# ============================================================

def aggregate_to_civstate(fk, edu, inst, trade, assets, urban, absorbed,
                            religion_strength, shock_add, prev_civstate=None,
                            step=0):
    """Aggregate agent population (numpy arrays) → CivState (R,E,G,O,K,X in 0-130).

    Mapping (heuristic but consistent with v52 scale conventions):
    - R (resources)  ← assets    × 130  (asset wealth as resources)
    - E (environment)← (1 - shock_normalized) × 65 + sustainability_proxy
    - G (governance) ← inst      × 130  (institutional capacity)
    - O (optionality)← urban + edu mobility × 130
    - K (knowledge)  ← edu       × 130  (education as knowledge)
    - X (exposure)   ← shock_add × 100 + extremity in agent variance
    """
    active = ~absorbed
    if not active.any():
        s = CivState()
        s.alive = False
        s.true_ruin = True
        return s

    # Aggregate per-agent state → civilization scalars
    mean_assets = float(assets[active].mean())
    mean_edu = float(edu[active].mean())
    mean_inst = float(inst[active].mean())
    mean_urban = float(urban[active].mean())
    mean_fk = float(fk[active].mean())
    # Variance of edu+assets as proxy for inequality stress
    var_prosperity = float(np.var(edu[active] + assets[active]))

    R = mean_assets * 130
    K = mean_edu * 130
    G = mean_inst * 130
    O_state = (0.6 * mean_urban + 0.4 * mean_edu) * 130 + var_prosperity * 30
    E = max(8, 65 - shock_add * 80 + mean_fk * 50)
    X = min(95, shock_add * 100 + var_prosperity * 15)

    R = float(np.clip(R, 0, 130))
    E = float(np.clip(E, 0, 130))
    G = float(np.clip(G, 0, 130))
    O_state = float(np.clip(O_state, 0, 130))
    K = float(np.clip(K, 0, 130))
    X = float(np.clip(X, 0, 130))

    if prev_civstate is not None:
        s = prev_civstate.copy()
        s.prev_O = s.O; s.prev_G = s.G; s.prev_K = s.K
        s.R = R; s.E = E; s.G = G; s.O = O_state; s.K = K; s.X = X
        s.step = step
    else:
        s = CivState(R=R, E=E, G=G, O=O_state, K=K, X=X,
                     prev_O=O_state, prev_G=G, prev_K=K, step=step)
    return s


# ============================================================
# NEW: AGENT POLICY HINT BRIDGE
# Civ-level optimal action a* → per-agent action distribution
# ============================================================

def project_action_to_agents(civ_action, agent_strategy, strategy_names,
                                rng, n_agents, sigma_scale=None):
    """Generate per-agent actions from civ-level optimal action.

    Different strategies follow the civ action with different fidelity:
    - NRMO_vNext: tight (sigma=0.03)
    - Adaptive_OmegaFull: tight (sigma=0.04)
    - RiskAdjustedUtility: medium (sigma=0.06)
    - ExpectedValueMax: medium with growth bias (sigma=0.05, +0.05 growth)
    - Faith_*: medium (sigma=0.07, with strategy-specific biases)
    - Drift: ignore civ action (uniform [0.18, 0.30, 0.22, 0.30])

    Returns: (n_agents, 4) action array.
    """
    if sigma_scale is None:
        sigma_scale = {
            "NRMO_vNext": 0.03,
            "Adaptive_OmegaFull": 0.04,
            "RiskAdjustedUtility": 0.06,
            "ExpectedValueMax": 0.05,
            "Faith_Buddhist": 0.07, "Faith_Communal": 0.07,
            "Faith_Calvinist": 0.06, "Faith_Charismatic": 0.10,
            "Faith_Ascetic": 0.08, "Faith_Militant": 0.09,
            "Drift": -1.0,  # special: ignore civ action
        }

    actions = np.zeros((n_agents, 4))
    for s_idx, sname in enumerate(strategy_names):
        mask = agent_strategy == s_idx
        if not mask.any():
            continue
        n_sub = int(mask.sum())
        sigma = sigma_scale.get(sname, 0.06)
        if sigma < 0:
            # Drift: uniform action
            sub = np.tile(np.array([0.18, 0.30, 0.22, 0.30]), (n_sub, 1))
        else:
            sub = np.tile(civ_action, (n_sub, 1)) + rng.normal(0, sigma, size=(n_sub, 4))
            # Strategy-specific bias
            if sname == "ExpectedValueMax":
                sub[:, 0] += 0.05  # growth bias
                sub[:, 1] -= 0.03
            elif sname == "Faith_Ascetic":
                sub[:, 0] -= 0.05  # less growth
                sub[:, 1] += 0.04
                sub[:, 2] -= 0.02
            elif sname == "Faith_Militant":
                sub[:, 0] += 0.04  # more growth
                sub[:, 1] -= 0.02
            elif sname == "Faith_Communal":
                sub[:, 1] += 0.03  # safety
                sub[:, 3] += 0.02  # distribution
            elif sname == "Faith_Calvinist":
                sub[:, 0] += 0.02
                sub[:, 1] += 0.01
            elif sname == "Faith_Charismatic":
                sub[:, 2] += 0.04  # high learning
                sub[:, 1] -= 0.03
            # Clip and normalize
            sub = np.clip(sub, MIN_C, None)
            sub = sub / sub.sum(axis=1, keepdims=True)
        actions[mask] = sub
    return actions


# ============================================================
# WORLD PARAMETERS — derived from Cultural Module characteristics
# ============================================================

def derive_world_params(civ_module, era_idx, religion_strength):
    """Convert Cultural Module's era to v52 world_params dict for Tuning + Omega."""
    eras = civ_module.eras
    if era_idx < 0 or era_idx >= len(eras):
        era_idx = max(0, min(era_idx, len(eras) - 1))
    era_name, _, _, base_failure, _ = eras[era_idx]

    # Map base_failure (0.05-0.65) to v52 world_params
    # Higher base_failure → harder world (more shocks, more rivalry, more tail risk)
    severity = base_failure  # 0-1 scale

    return {
        "shock_probability": 0.08 + severity * 0.25,
        "shock_scale": 3.0 + severity * 8.0,
        "tail_probability": 0.02 + severity * 0.10,
        "tail_scale": 12.0 + severity * 25.0,
        "environmental_drag": 0.02 + severity * 0.06,
        "governance_drag": 0.01 + severity * 0.04,
        "stagnation_drag": 0.005 + severity * 0.02,
        "rivalry_level": 0.10 + severity * 0.40,
        "innovation_noise": 0.8 + severity * 0.8,
        "coordination_cost": 0.03 + severity * 0.08,
        "substitutability": 0.4 + (1 - severity) * 0.3,
        "tail_model_misspecification": 0.05 + severity * 0.20,
    }


# ============================================================
# TOP-LEVEL VNEXT+ DECISION FOR ONE CIV ONE STEP
# This is the new public entry point for World Sim integration.
# ============================================================

class VNextPlusCivController:
    """One controller per civilization. Owns the per-civ MetaController,
    HysteresisTracker, OmegaFullEngine, and CivState history.
    """

    def __init__(self, civ_name, civ_module, oc=None,
                  enable_archetype_classifier=True):
        self.civ_name = civ_name
        self.civ_module = civ_module
        self.meta = MetaController()
        self.ht = HysteresisTracker()
        self.engine = OmegaFullEngine(oc, enable_archetype_classifier)
        self.civstate = None  # Initialized on first step
        self.tuning_history = []  # log of (step, mode, tc) tuples

    def step(self, rng, fk, edu, inst, trade, assets, urban, absorbed,
              religion_strength, shock_add, era_idx, world_name, gen):
        """Run vNext+ pipeline: aggregate → tune → veto → engine → project."""
        # 1. Aggregate to CivState
        self.civstate = aggregate_to_civstate(
            fk, edu, inst, trade, assets, urban, absorbed,
            religion_strength, shock_add, self.civstate, step=gen)

        # 2. Derive world params from civ module + era
        wp = derive_world_params(self.civ_module, era_idx, religion_strength)

        # 3. Update meta-controller (with hysteresis)
        mode = self.meta.update(self.civstate, wp)
        self.civstate.mode = mode

        # 4. Adaptive tuning
        base_profile = get_world_profile(world_name)
        tc = adaptive_tuning(base_profile, self.civstate, mode, self.ht)
        self.tuning_history.append({"step": gen, "mode": mode,
                                     "growth_cap": tc.growth_cap,
                                     "exploration_floor": tc.exploration_floor})

        # 5. Generate candidates (Omega Full's full pipeline)
        wolf_now = detect_favorable(self.civstate, self.engine.prev_state)
        pool = build_candidate_pool(self.civstate, wp, rng, wolf=wolf_now)

        # 6. NRMO Core: construct admissible set
        admissible, flags = construct_admissible_set(
            pool, self.civstate, mode="vnext", tc=tc)

        # If admissible is empty (rare extreme), fall back to safe action
        if not admissible:
            return _norm(np.array([0.05, 0.50, 0.22, 0.23])), tc

        # 7. StrongEngine Ω Full: select action
        civ_action = self.engine.select_action(
            admissible, self.civstate, wp, rng, mode=mode, world_name=world_name)

        return civ_action, tc
