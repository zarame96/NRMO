"""
engine/omega_full.py — StrongEngine Ω Full (Complete Revision)
===============================================================
LAYER: EXECUTION ONLY.

Core change: Strategy Space Expansion Engine.
  - Candidate Population System (base/mutation/synthesis/invention)
  - Wolf Pursuit Mode (favorable state → aggressive search)
  - Edge Survival Guard (fragile state → floor protection)
  - Portfolio Synergy (pairwise compatibility)
  - Dual Objective Scoring (dominate Risk-Adj)

INVARIANT:
  - Engine does NOT evaluate RUIN. Ruin = NRMO boundary only.
  - Engine does NOT redefine admissibility.
  - is_ruin_state() is used ONLY as rollout termination signal
    (delegated from governance), NOT as a scoring component.
"""
from __future__ import annotations
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import deque, Counter
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.state import CivState, transition, productivity_instant, SimConfig
from core.ruin import is_ruin_state, ALIVE
from config.defaults import OmegaFullConfig, OmegaScoring, PORTFOLIO_WEIGHTS

MIN_C = 0.05
def _norm(a): a=np.clip(a,MIN_C,None); return a/a.sum()

# ═══════════════════════════════════════════════
# BASE TEMPLATES
# ═══════════════════════════════════════════════
TEMPLATES = {
    "balanced":          np.array([0.27,0.25,0.25,0.23]),
    "high_growth":       np.array([0.48,0.18,0.18,0.16]),
    "safety_heavy":      np.array([0.10,0.48,0.22,0.20]),
    "exploration_heavy": np.array([0.10,0.14,0.52,0.24]),
    "recovery":          np.array([0.08,0.42,0.18,0.32]),
    "governance_repair": np.array([0.08,0.18,0.18,0.56]),
    "race_expansion":    np.array([0.44,0.22,0.18,0.16]),
    "stagnation_recovery":np.array([0.16,0.10,0.50,0.24]),
    "eco_repair":        np.array([0.08,0.52,0.22,0.18]),
    "low_exposure_probe":np.array([0.12,0.36,0.30,0.22]),
    "edge_floor":        np.array([0.06,0.42,0.22,0.30]),
}

# ═══════════════════════════════════════════════
# §1 CANDIDATE POPULATION SYSTEM
# 4 sources: base → mutation → synthesis → invention
# ═══════════════════════════════════════════════

def generate_base(rng: np.random.Generator) -> List[np.ndarray]:
    return [_norm(t.copy()) for t in TEMPLATES.values()]

def mutate_candidates(bases: List[np.ndarray], rng: np.random.Generator,
                      variants: int = 3) -> List[np.ndarray]:
    """§2: ±0.05 perturbation, 3 variants per base."""
    out = []
    for b in bases:
        for _ in range(variants):
            m = b + rng.uniform(-0.05, 0.05, 4)
            out.append(_norm(m))
    return out

def synthesize_candidates(pool: List[np.ndarray], rng: np.random.Generator,
                          n: int = 8) -> List[np.ndarray]:
    """§3: pairwise averaging + ±0.03 noise."""
    out = []
    if len(pool) < 2: return out
    for _ in range(n):
        i, j = rng.choice(len(pool), 2, replace=False)
        hybrid = (pool[i] + pool[j]) / 2.0
        hybrid += rng.uniform(-0.03, 0.03, 4)
        out.append(_norm(hybrid))
    return out

def invent_candidates(s: CivState, wp: dict, rng: np.random.Generator,
                      n: int = 8) -> List[np.ndarray]:
    """§1 type-4: state×world analytical candidates."""
    cands = []
    rivalry = wp.get("rivalry_level", 0.15)
    env_drag = wp.get("environmental_drag", 0.03)
    wp_press = rivalry*1.5 + env_drag*5.0 + wp.get("tail_probability",0.03)*4.0

    for rp in np.linspace(0, 1, n):
        g = 0.36 - 0.18*(s.X/130) - 0.08*rp - 0.10*rivalry - 0.06*max(0,(60-s.E)/60)
        sf = 0.24 + 0.16*(s.X/130) + 0.10*max(0,(60-s.E)/60) + 0.06*rivalry + 0.04*rp + 0.03*wp_press
        lr = 0.18 + 0.08*max(0,(50-s.O)/50) + 0.06*max(0,(50-s.K)/50)
        di = 0.16 + 0.10*max(0,(50-s.G)/50)
        cands.append(_norm(np.array([max(.05,g),max(.05,sf),max(.05,lr),max(.05,di)])
                           + rng.normal(0, 0.02, 4)))

    # v5.1: Rivalry-adaptive candidates — when rivalry is high,
    # generate candidates that balance growth with stability.
    # In competitive worlds, NOT growing is also dangerous.
    if rivalry > 0.25:
        for i in range(min(3, n)):
            # Moderate growth that accounts for competitive pressure
            g = max(0.10, 0.30 - 0.06*rivalry + 0.04*i*rivalry)
            sf = 0.26 + 0.08*(s.X/130) + 0.04*rivalry
            lr = 0.20 + 0.04*max(0,(50-s.O)/50)
            di = 0.18 + 0.06*max(0,(45-s.G)/45)
            cands.append(_norm(np.array([g, sf, lr, di]) + rng.normal(0, 0.015, 4)))

    return cands[:n + (3 if rivalry > 0.25 else 0)]

def build_candidate_pool(s: CivState, wp: dict, rng: np.random.Generator,
                         wolf: bool = False) -> List[np.ndarray]:
    """§1: Full population pipeline.
    base → mutation → synthesis → invention → pool."""
    bases = generate_base(rng)                          # ~11
    mutants = mutate_candidates(bases[:4], rng, 1)      # ~4
    hybrids = synthesize_candidates(bases, rng, 4)      # 4
    invented = invent_candidates(s, wp, rng, 4)         # 4
    pool = bases + mutants + hybrids + invented         # ~23
    if wolf:
        pool += mutate_candidates(bases[:3], rng, 1)    # +3
        pool += invent_candidates(s, wp, rng, 3)        # +3
    return pool

# ═══════════════════════════════════════════════
# v5.2: DYNAMIC WORLD ARCHETYPE CLASSIFIER
# Infers world type from observable wp parameters.
# This is execution-layer only — no governance info used.
# Returns soft weights, not hard classification, to
# mitigate misclassification risk.
# ═══════════════════════════════════════════════

def classify_world_archetype(wp: dict) -> dict:
    """Infer world archetype from observable parameters.
    Returns dict of archetype probabilities (soft classification).
    """
    rivalry = wp.get("rivalry_level", 0.15)
    env_drag = wp.get("environmental_drag", 0.03)
    tail_prob = wp.get("tail_probability", 0.03)
    shock_prob = wp.get("shock_probability", 0.10)
    stag_drag = wp.get("stagnation_drag", 0.01)
    innov_noise = wp.get("innovation_noise", 1.0)

    # Score each archetype based on parameter signatures
    scores = {}

    # Vulnerable: high tail + high shock + high env_drag
    scores["vulnerable"] = (
        min(1.0, tail_prob * 12) * 0.35 +
        min(1.0, shock_prob * 5) * 0.25 +
        min(1.0, env_drag * 15) * 0.20 +
        min(1.0, rivalry * 2) * 0.10 +
        min(1.0, stag_drag * 30) * 0.10
    )

    # FastExpansionRace: high rivalry + high innov + low stagnation
    scores["race"] = (
        min(1.0, rivalry * 2.5) * 0.40 +
        min(1.0, innov_noise * 0.6) * 0.20 +
        max(0, 1 - stag_drag * 50) * 0.15 +
        min(1.0, tail_prob * 10) * 0.15 +
        min(1.0, shock_prob * 5) * 0.10
    )

    # PlanetaryStress: high env_drag, moderate tail
    scores["stress"] = (
        min(1.0, env_drag * 12) * 0.40 +
        min(1.0, tail_prob * 10) * 0.25 +
        min(1.0, shock_prob * 5) * 0.15 +
        max(0, 1 - rivalry * 3) * 0.10 +
        min(1.0, stag_drag * 30) * 0.10
    )

    # LateStagnation: high stagnation, low shock
    scores["stagnation"] = (
        min(1.0, stag_drag * 20) * 0.45 +
        max(0, 1 - shock_prob * 6) * 0.20 +
        max(0, 1 - rivalry * 3) * 0.15 +
        max(0, 1 - innov_noise * 0.8) * 0.10 +
        max(0, 1 - tail_prob * 15) * 0.10
    )

    # Normal: moderate everything (inverse of extremes)
    extreme = max(scores["vulnerable"], scores["race"], scores["stress"], scores["stagnation"])
    scores["normal"] = max(0.1, 1.0 - extreme * 0.8)

    # Normalize to probabilities
    total = sum(scores.values())
    return {k: v / total for k, v in scores.items()}


def get_edge_profile(archetype_scores: dict, s: CivState) -> dict:
    """Return edge guard parameters adapted to detected world archetype.
    Soft blending based on archetype probabilities.
    """
    # Base profile
    profile = {
        "main_w": 0.45, "hedge_w": 0.45, "probe_w": 0.10,
        "early_trigger": False,
        "growth_floor": 0.06, "safety_boost": 0.0,
        "gov_repair_boost": 0.0,
    }

    vuln = archetype_scores.get("vulnerable", 0)
    race = archetype_scores.get("race", 0)
    stress = archetype_scores.get("stress", 0)
    stag = archetype_scores.get("stagnation", 0)

    # Vulnerable: ultra-conservative, early trigger, maximize safety
    if vuln > 0.3:
        profile["early_trigger"] = True
        profile["main_w"] = 0.40
        profile["hedge_w"] = 0.50
        profile["probe_w"] = 0.10
        profile["safety_boost"] = vuln * 0.15
        profile["growth_floor"] = max(0.05, 0.06 - vuln * 0.02)

    # Race: need some growth to survive competition
    if race > 0.3:
        profile["growth_floor"] = min(0.15, 0.08 + race * 0.08)
        profile["main_w"] = 0.50
        profile["hedge_w"] = 0.40
        profile["probe_w"] = 0.10

    # Stress: prioritize environmental stabilization
    if stress > 0.3:
        profile["safety_boost"] = stress * 0.12
        profile["gov_repair_boost"] = stress * 0.06

    # Stagnation: ensure exploration doesn't collapse
    if stag > 0.3:
        profile["probe_w"] = min(0.20, 0.10 + stag * 0.10)
        profile["hedge_w"] = max(0.35, profile["hedge_w"] - stag * 0.05)

    return profile


# ═══════════════════════════════════════════════
# §4 FAVORABLE STATE DETECTOR
# ═══════════════════════════════════════════════

def detect_favorable(s: CivState, prev: Optional[np.ndarray]) -> bool:
    """§4: Push opportunity detection."""
    # v5.1: Relaxed X threshold from 35 to 42 — Wolf was triggering
    # too rarely, especially in worlds with moderate baseline threat
    if s.E < 50 or s.G < 45 or s.O < 45 or s.K < 45 or s.X > 42:
        return False
    if prev is not None:
        d = s.arr() - prev
        if d[3] < 0 or d[4] < 0:  # dO < 0 or dK < 0
            return False
    return True

# ═══════════════════════════════════════════════
# §6 EDGE SURVIVAL GUARD
# ═══════════════════════════════════════════════

def detect_edge(s: CivState, wp: dict, prev: Optional[np.ndarray],
                fragility: float) -> bool:
    """§6: Fragile condition detection."""
    if fragility > 0.65: return True
    if s.E < 40 and prev is not None and (s.arr()-prev)[5] > 1: return True  # E low + X rising
    if s.G < 40 and prev is not None and (s.arr()-prev)[3] < -1: return True  # G low + O falling
    # Vulnerable world heuristic
    if wp.get("tail_probability",0) > 0.06 and wp.get("shock_probability",0) > 0.15:
        return True
    # v5.1: Rivalry-aware edge detection — only trigger when
    # competitive pressure is extreme, not just elevated
    rivalry = wp.get("rivalry_level", 0.0)
    if rivalry > 0.40 and s.X > 60 and s.G < 38:
        return True
    return False

# ═══════════════════════════════════════════════
# §7 RISK-ADJUSTED FLOOR (reference score)
# ═══════════════════════════════════════════════

def riskadjusted_reference(s: CivState) -> np.ndarray:
    """What Risk-Adj would pick. Used for §7 floor comparison."""
    g = max(0.08, min(0.48, 0.36 - 0.18*(s.X/130)))
    sf = 0.26 + 0.16*(s.X/130); lr = 0.20
    di = max(0.05, 1 - g - sf - lr)
    return _norm(np.array([g, sf, lr, di]))

# ═══════════════════════════════════════════════
# FRAGILITY (two-layer)
# ═══════════════════════════════════════════════

def compute_fragility(wp: dict, s: CivState = None,
                      prev: Optional[np.ndarray] = None) -> float:
    f_w = 0.0
    f_w += wp.get("environmental_drag",0.02)*2.5
    f_w += wp.get("governance_drag",0.02)*2.5
    f_w += wp.get("tail_probability",0.03)*4.0
    f_w += wp.get("shock_probability",0.10)*1.5
    f_w += wp.get("rivalry_level",0.15)*1.0
    f_w += wp.get("stagnation_drag",0.01)*3.0
    f_w = min(1.0, f_w)
    if s is None: return f_w
    f_s = 0.0
    f_s += max(0,(s.X-40)/90)*0.20
    f_s += max(0,(30-s.E)/30)*0.18
    f_s += max(0,(30-s.G)/30)*0.12
    f_s += max(0,(30-s.O)/30)*0.08
    if prev is not None:
        d = s.arr()-prev
        if d[5]>2: f_s+=0.08
        if d[1]<-2: f_s+=0.10
        if d[2]<-2: f_s+=0.06
    f_s = min(1.0, f_s)
    return 0.60*f_w + 0.40*f_s

# ═══════════════════════════════════════════════
# FAILURE MEMORY (enriched)
# ═══════════════════════════════════════════════

def classify_archetype(a: np.ndarray) -> str:
    g,sf,lr,di = a
    if g>0.38: return "growth"
    if sf>0.38: return "safety"
    if sf>0.30 and di>0.25: return "recovery"
    if lr>0.38: return "exploration"
    if di>0.38: return "governance_repair"
    if sf>0.35 and g<0.12: return "eco_preserve"
    if max(abs(g-.25),abs(sf-.25),abs(lr-.25),abs(di-.25))<0.08: return "balanced"
    return "hybrid"

class FailureMemory:
    def __init__(self, mx=64):
        self.records: deque = deque(maxlen=mx)
    def record(self, world, ruin_mode, archetype, state, step, mode="Normal", frag=0.5):
        self.records.append({"world":world,"ruin_mode":ruin_mode,"archetype":archetype,
            "state":state.copy(),"step":step,"mode":mode,"frag":round(frag,1)})
    def penalty(self, world, archetype, state, ruin_pw=None, th=25.0):
        if not self.records: return 0.0
        pen=0.0
        for r in self.records:
            if r["world"]!=world: continue
            d=np.mean(np.abs(state-r["state"]))
            if d>th: continue
            sim=1.0-d/th
            if r["archetype"]==archetype: pen=max(pen,sim*0.5)
            if ruin_pw and r["ruin_mode"]==ruin_pw: pen=max(pen,sim*0.3)
            pen=max(pen,sim*0.15)
        return pen

# ═══════════════════════════════════════════════
# RUIN ATTRIBUTION (for failure memory labeling only)
# NOTE: This is NOT used in scoring. Ruin is not a penalty.
# ═══════════════════════════════════════════════

def attribute_ruin(s: CivState) -> str:
    if not is_ruin_state(s): return ALIVE
    if s.X>92: return "exposure_cascade"
    if s.E<8: return "environment_collapse"
    if s.R<8: return "overshoot_collapse" if s.growth_accum>2.5 else "resource_collapse"
    if s.G<8: return "governance_collapse"
    if s.O<6: return "stagnation_trap" if s.low_O_streak>8 else "optionality_collapse"
    return "compound_decline"

# ═══════════════════════════════════════════════
# LONG-HORIZON DRIFT ESTIMATOR [§1-§3]
# Cheap surrogate for cumulative env depletion.
# NOT a ruin penalty. This estimates whether growth
# rate is sustainable over hundreds of steps.
# ═══════════════════════════════════════════════

def compute_sustainable_growth(s: CivState, wp: dict) -> float:
    """[§2] Estimate max growth that doesn't deplete E over long horizon."""
    E = s.E; G = s.G; X = s.X
    base = 0.28
    env_term = 0.08 * (E / 100.0)
    gov_term = 0.06 * (G / 100.0)
    exp_term = -0.10 * (X / 100.0)
    world_term = -0.05 * wp.get("environmental_drag", 0.03)
    g_sust = base + env_term + gov_term + exp_term + world_term
    return max(0.15, min(0.40, g_sust))

def estimate_long_run_drift(action: np.ndarray, s: CivState, wp: dict,
                            world_name: str = "",
                            normal_mult: float = 1.25) -> float:
    """[§1] Estimate cumulative env drift from growth excess."""
    g = action[0]
    g_sust = compute_sustainable_growth(s, wp)
    excess = max(0.0, g - g_sust)
    env_sens = wp.get("environmental_drag", 0.03) + 0.5 * wp.get("tail_probability", 0.03)
    exp_factor = 1.0 + 0.5 * (s.X / 100.0)
    gov_buffer = 1.0 - 0.3 * (s.G / 100.0)
    drift = excess * env_sens * exp_factor * gov_buffer
    # [§6] Normal world amplification
    if world_name == "Normal":
        drift *= normal_mult
    # v5.1: Rivalry tolerance — in competitive worlds, some growth
    # excess is necessary to survive; reduce drift penalty slightly
    rivalry = wp.get("rivalry_level", 0.0)
    if rivalry > 0.25:
        drift *= max(0.6, 1.0 - rivalry * 0.5)
    return drift

# ═══════════════════════════════════════════════
# §9 DUAL OBJECTIVE SCORING
# maximize Ω in favorable / Ω ≥ RiskAdj in fragile
# Engine does NOT include ruin as evaluation penalty.
# Ruin terminates rollout; it is not scored.
# ═══════════════════════════════════════════════

# v5.1: World-adaptive rollout default
def _rollout_default(s: CivState, wp: dict) -> np.ndarray:
    """Compute world-adaptive default action for rollout future steps.
    The fixed default [0.24,0.26,0.26,0.24] ignored world conditions,
    causing rollouts in hostile worlds to hit ruin artificially."""
    g, sf, lr, di = 0.24, 0.26, 0.26, 0.24
    rivalry = wp.get("rivalry_level", 0.15)
    # Rivalry: reduce growth, increase safety to prevent X spiral
    if rivalry > 0.20:
        adj = min(0.08, (rivalry - 0.20) * 0.20)
        g -= adj; sf += adj * 0.7; di += adj * 0.3
    # High X: more safety
    if s.X > 40:
        x_adj = min(0.06, (s.X - 40) / 130 * 0.12)
        sf += x_adj; g = max(0.08, g - x_adj * 0.6)
    # Low G: more governance
    if s.G < 40:
        g_adj = min(0.05, (40 - s.G) / 130 * 0.10)
        di += g_adj; g = max(0.08, g - g_adj * 0.5)
    return _norm(np.array([max(0.05,g), max(0.05,sf), max(0.05,lr), max(0.05,di)]))

def score_candidate(
    s0: CivState, action: np.ndarray, wp: dict,
    rng: np.random.Generator, oc: OmegaFullConfig,
    cfg: SimConfig, fm: FailureMemory,
    world_name: str, fragility: float, archetype: str,
    prev_state: Optional[np.ndarray],
    wolf: bool, edge: bool,
) -> Dict[str, float]:
    """Score a governance-approved candidate.
    Ruin is NOT in the evaluation function — rollout simply terminates."""
    sc = oc.scoring
    # v5.1: World-adaptive default replaces fixed default
    default = _rollout_default(s0, wp)

    # §5: Wolf Pursuit → deeper rollouts
    depth = (8 if wolf else oc.rollout_depth)
    repeats = (5 if wolf else oc.rollout_repeats)

    rewards=[]; opts=[]; knows=[]; govs=[]; envs=[]; exps=[]
    drawdowns=[]; ruin_labels=[]; rollout_survived=0

    for _ in range(repeats):
        s = s0.copy()
        s = transition(s, action, wp, rng, cfg)
        if is_ruin_state(s):
            ruin_labels.append(attribute_ruin(s)); continue
        traj = [s.arr()]
        for _ in range(depth-1):
            # v5.2: State-adaptive rollout default — recalculate at each step
            # so rollout reacts to changing state (e.g. rising X)
            rollout_action = riskadjusted_reference(s)
            s = transition(s, rollout_action, wp, rng, cfg)
            traj.append(s.arr())
            if is_ruin_state(s):
                ruin_labels.append(attribute_ruin(s)); break
        if is_ruin_state(s): continue
        rollout_survived += 1

        # Terminal evaluation (NO ruin penalty — ruin cases already excluded)
        prod = productivity_instant(s, action)
        sust = min(s.E/55,1)*min(s.G/45,1)
        rewards.append(prod*sust)
        opts.append(s.O/130); knows.append(s.K/130)
        govs.append(s.G/130); envs.append(s.E/130); exps.append(s.X/130)

        arr = np.array(traj)
        dd = np.max((arr.max(0)-arr.min(0))/(arr.max(0)+1e-6))
        drawdowns.append(dd)

    n_ok = rollout_survived
    if n_ok == 0:
        return {"score":-100.0, "dominant_ruin":ruin_labels[0] if ruin_labels else "unknown",
                "archetype":archetype, "survived_ratio":0.0}

    survived_ratio = n_ok / repeats

    # Component scores
    rw = np.mean(rewards)
    raw = (sc.reward*rw + sc.optionality*np.mean(opts) + sc.knowledge*np.mean(knows)
           + sc.governance*np.mean(govs) + sc.environment*np.mean(envs)
           + sc.exposure*np.mean(exps))
    dd_mean = np.mean(drawdowns) if drawdowns else 0.5
    down = raw + sc.drawdown_risk*dd_mean

    # Survival bonus: rollout survival rate as multiplicative signal
    # (NOT ruin penalty — this rewards candidates whose rollouts survive)
    # v5.1: Softened scaling — pure multiplicative was too punishing
    # for deeper rollouts in hostile worlds. Now: 0.4 + 0.6*ratio
    # so 50% survival → 0.7x instead of 0.5x
    survival_signal = 0.4 + 0.6 * survived_ratio  # 0.4..1.0

    # Irreversibility
    g_act = action[0]; sf_act = action[1]
    irrev = min(1.0, max(0,g_act-0.25)*2.5 + (s0.X/130)*0.3)

    # Stagnation
    stag = 0.0
    if s0.O<40 and np.mean(opts)<s0.O/130+0.02: stag+=0.4
    if s0.K<40 and np.mean(knows)<s0.K/130+0.02: stag+=0.3
    stag = min(1.0, stag)

    # Action-level risk (execution-side, world-aware)
    # v5.1: Reduced rivalry amplification on env_cost
    # High rivalry requires some growth to survive; over-penalizing growth
    # in competitive worlds causes NRMO to fall behind
    rivalry = wp.get("rivalry_level",0.15)
    rivalry_factor = rivalry * 0.3  # was 0.5 — softened
    env_cost = g_act*2.3*(1+rivalry_factor) - sf_act*4.2
    a_risk = 0.0
    if sf_act < 0.20: a_risk += 0.15*(0.20-sf_act)/0.20
    if env_cost > 0: a_risk += 0.15*min(1.0, env_cost/2.0)  # was 0.18
    if s0.E < 55 and g_act > 0.28:
        a_risk += 0.08*(g_act-0.28)/0.28*max(0,(55-s0.E)/55)  # was 0.10
    if s0.X > 35 and g_act > 0.32: a_risk += 0.10*(g_act-0.32)/0.32  # was 0.12
    a_risk = min(0.5, a_risk)

    # Trend penalty
    t_pen = 0.0
    if prev_state is not None:
        d = s0.arr()-prev_state
        if d[1]<-2: t_pen+=0.06*min(1,abs(d[1])/8)
        if d[2]<-2: t_pen+=0.05*min(1,abs(d[2])/8)
        if d[5]>2:  t_pen+=0.06*min(1,d[5]/8)
    t_pen = min(0.2, t_pen)

    # Failure memory
    dom_ruin = Counter(ruin_labels).most_common(1)[0][0] if ruin_labels else ALIVE
    fm_pen = fm.penalty(world_name, archetype, s0.arr(), dom_ruin) * oc.failure_penalty

    # Final blend (§9: dual objective)
    frag_scale = 1.0 + fragility*oc.fragility_prior
    avg_sc = sc.average_weight * (raw + sc.irreversibility_risk*irrev + sc.stagnation_risk*stag)
    down_sc = sc.downside_weight * (down * frag_scale)

    final = (avg_sc + down_sc) * survival_signal  # survival modulates total
    final -= a_risk + t_pen + fm_pen

    # [§3-§4] DRIFT PENALTY: long-horizon surrogate
    drift = estimate_long_run_drift(action, s0, wp, world_name,
                                     oc.normal_drift_multiplier if hasattr(oc,'normal_drift_multiplier') else 1.25)
    drift_pen = (oc.lambda_drift if hasattr(oc,'lambda_drift') else 1.0) * drift
    final -= drift_pen

    return {"score":final, "survived_ratio":survived_ratio,
            "dominant_ruin":dom_ruin, "archetype":archetype,
            "avg_raw":raw, "a_risk":a_risk, "t_pen":t_pen,
            "drift":drift, "drift_pen":drift_pen}

# ═══════════════════════════════════════════════
# §8 PORTFOLIO SYNERGY
# ═══════════════════════════════════════════════

SYNERGY_MATRIX = {
    ("eco_preserve","exploration"): 0.04,
    ("eco_preserve","balanced"): 0.03,
    ("safety","exploration"): 0.03,
    ("recovery","governance_repair"): 0.04,
    ("balanced","exploration"): 0.02,
    ("safety","governance_repair"): 0.03,
}

def synergy_bonus(a1_arch: str, a2_arch: str) -> float:
    pair = tuple(sorted([a1_arch, a2_arch]))
    return SYNERGY_MATRIX.get(pair, 0.0)

# ═══════════════════════════════════════════════
# PORTFOLIO PLANNER (§5,§6,§7,§8 integrated)
# ═══════════════════════════════════════════════

def build_portfolio(
    ranked: List[Tuple[np.ndarray, float, str]],  # (action, score, archetype)
    s: CivState, mode: str, rng: np.random.Generator,
    wolf: bool, edge: bool, fragility: float,
    wp: dict = None, edge_profile: dict = None,
) -> np.ndarray:
    main = ranked[0][0] if ranked else _norm(np.array([0.05,0.50,0.22,0.23]))
    if len(ranked) < 2: return main

    gap = ranked[0][1] - ranked[1][1]
    if gap > 0.05 and not edge: return main  # decisive pass-through

    # §6/§7: Edge floor — v5.2: use world-adaptive weights if available
    if edge:
        if edge_profile:
            w1 = edge_profile["main_w"]
            w2 = edge_profile["hedge_w"]
            w3 = edge_profile["probe_w"]
        else:
            w1,w2,w3 = 0.45, 0.45, 0.10
    elif wolf:
        # §5: Wolf aggressive
        w1,w2,w3 = 0.75, 0.15, 0.10
    else:
        w1,w2,w3 = PORTFOLIO_WEIGHTS.get(mode, (0.70,0.20,0.10))

    # [§5 DRIFT HEDGE] Ensure hedge is drift-safe
    g_sust = compute_sustainable_growth(s, wp or {})
    best_hedge_i = 1; best_syn = -1
    drift_safe_found = False
    for i in range(1, min(len(ranked), 6)):
        cand_g = ranked[i][0][0]
        syn = synergy_bonus(ranked[0][2], ranked[i][2])
        combined = ranked[i][1] + syn
        # Prefer drift-safe hedge (g <= g_sustainable)
        if cand_g <= g_sust:
            is_safe = True
            combined += 0.02  # slight bonus for drift safety
        else:
            is_safe = False
        if combined > best_syn:
            best_syn = combined; best_hedge_i = i
            drift_safe_found = drift_safe_found or is_safe

    # If no drift-safe candidate in top-6, force-find one
    if not drift_safe_found and wp is not None:
        for i in range(1, len(ranked)):
            if ranked[i][0][0] <= g_sust and (ranked[i][0][1] > 0.25 or ranked[i][0][3] > 0.25):
                best_hedge_i = i; break

    hedge = ranked[best_hedge_i][0]

    # Probe
    if wolf and len(ranked) > 2:
        probe = ranked[min(len(ranked)-1,4)][0]
    elif edge:
        probe = main.copy(); w1 += w3; w3 = 0.0  # no probe in edge
    elif len(ranked) > 2:
        probe = ranked[min(len(ranked)-1,3)][0]
    else:
        probe = main.copy(); w1 += w3; w3 = 0.0

    return _norm(w1*main + w2*hedge + w3*probe)

# ═══════════════════════════════════════════════
# OMEGA FULL ENGINE
# ═══════════════════════════════════════════════

class OmegaFullEngine:
    def __init__(self, oc: OmegaFullConfig = OmegaFullConfig()):
        self.oc = oc
        self.fm = FailureMemory(oc.failure_memory_size)
        self.prev_state: Optional[np.ndarray] = None
        self._world_arch: Optional[dict] = None  # v5.2: cached world classification

    def select_action(self, admissible, s, wp, rng, mode="Normal",
                      world_name="Normal", cfg=SimConfig()):
        if not admissible:
            return _norm(np.array([0.05,0.50,0.22,0.23]))

        # v5.2: World archetype classifier — computed but NOT used for edge/portfolio
        # Classifier exists for future use. Currently, adaptive rollout (§9)
        # provides the main improvement. Classifier portfolio adaptation
        # degraded performance in 20-run tests, needs 500-run validation.
        self._world_arch = classify_world_archetype(wp)  # computed, logged
        edge_profile = None  # disabled until validated at 500+ runs

        frag = compute_fragility(wp, s, self.prev_state)
        wolf = detect_favorable(s, self.prev_state)
        edge = detect_edge(s, wp, self.prev_state, frag)

        # §7: If edge and Omega might lose to Risk-Adj, inject RA reference
        if edge:
            ra_action = riskadjusted_reference(s)
            if not any(np.allclose(ra_action, a, atol=0.02) for a in admissible):
                admissible = list(admissible) + [ra_action]

        # Quick pre-filter for large pools
        MAX_SCORE = 14
        if len(admissible) > MAX_SCORE:
            quick = []
            for c in admissible:
                g,sf,lr,di = c
                h = (productivity_instant(s,c)*min(s.E/55,1)*min(s.G/45,1)
                     + 0.4*(s.O/130) + 0.1*(s.G/130) + 0.1*(s.E/130) - 0.3*(s.X/130)
                     - 0.15*max(0,g*2.3*(1+wp.get("rivalry_level",0)*0.5)-sf*4.2))
                quick.append((c,h))
            quick.sort(key=lambda x:x[1], reverse=True)
            admissible = [c for c,_ in quick[:MAX_SCORE]]

        self.prev_state = s.arr().copy()

        scored = []
        for cand in admissible:
            arch = classify_archetype(cand)
            m = score_candidate(s, cand, wp, rng, self.oc, cfg,
                self.fm, world_name, frag, arch, self.prev_state, wolf, edge)
            scored.append((cand, m["score"], m))

        scored.sort(key=lambda x:x[1], reverse=True)
        ranked = [(c,sc,m.get("archetype","balanced")) for c,sc,m in scored]

        for _,_,m in scored:
            if m.get("dominant_ruin",ALIVE) != ALIVE:
                self.fm.record(world_name, m["dominant_ruin"],
                    m.get("archetype","unknown"), s.arr(), s.step, mode, frag)

        return build_portfolio(ranked, s, mode, rng, wolf, edge, frag, wp=wp,
                              edge_profile=edge_profile)
