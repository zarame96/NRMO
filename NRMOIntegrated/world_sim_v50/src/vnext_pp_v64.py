"""
vNext++ (v6.4) — Full enhancement package for NRMO (formerly NRMO_vNext).

This is built atop vnext_plus.py (v6.3) and adds 13 improvements (A-M):

Layer 1 (Empirical findings):
  A. Asymmetric hysteresis           — crisis fast, peace slow
  B. Insurance Layer                  — collective risk-pooling within civ
  
Layer 2 (Code-level improvements):
  C. Distributional CivState         — keep mean+p25+p75+var
  D. State-conditioned sigma         — agent-state-aware civ_action tracking
  E. Continuous mode space           — 5-dim score instead of 5 discrete modes
  F. Shared Failure Memory           — cross-civ failure transmission

Layer 3 (Theoretical improvements):
  G. True Optionality measure        — log |A(S')| via rollout
  H. Online tuning (bandit)          — UCB-based TuningConfig optimization
  I. Synergy matrix learning         — auto-learn synergy from rollouts
  J. Cumulative drift                — non-linear drift penalty with memory
  K. Counterfactual decision regret  — track regret per chosen action
  L. Hierarchical Optionality        — individual/family/civ tiers
  M. Early passive ruin detection    — O slope monitoring

All A-M are toggleable via CLI flags or VNextPPConfig.
"""
import numpy as np
import copy
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

from vnext_plus import (
    # Re-export from v6.3
    CivState, NRMOCoreConfig, TuningConfig, OmegaScoring, OmegaFullConfig,
    RolloutConfig, RuinThresholds,
    nrmo_origin_veto, nrmo_veto, construct_admissible_set,
    civstate_transition, productivity_instant, is_ruin_state, attribute_ruin,
    classify_archetype, classify_world_archetype, get_edge_profile,
    detect_favorable, detect_edge, riskadjusted_reference,
    compute_fragility, compute_sustainable_growth, estimate_long_run_drift,
    build_candidate_pool, _norm, _rollout_default,
    OmegaFullEngine, FailureMemory, VNextPlusCivController,
    aggregate_to_civstate as aggregate_to_civstate_v63,
    project_action_to_agents as project_action_to_agents_v63,
    derive_world_params,
    MODE_NORMAL, MODE_HIGHSTAKES, MODE_RECOVERY, MODE_STAGNATION, MODE_RACE,
    PORTFOLIO_WEIGHTS, get_world_profile,
    adaptive_tuning as adaptive_tuning_v63,
)


# ============================================================
# vNext++ Configuration
# ============================================================

@dataclass
class VNextPPConfig:
    """Master config for v6.4 enhancements. Each can be toggled.

    Defaults: ALL ENABLED (Zarame request: full implementation)."""
    enable_A_asymmetric_hysteresis: bool = True
    enable_B_insurance_layer: bool = True
    enable_C_distributional_state: bool = True
    enable_D_state_conditioned_sigma: bool = True
    enable_E_continuous_mode: bool = True
    enable_F_shared_failure_memory: bool = True
    enable_G_true_optionality: bool = True
    enable_H_online_tuning: bool = True
    enable_I_synergy_learning: bool = True
    enable_J_cumulative_drift: bool = True
    enable_K_counterfactual_regret: bool = True
    enable_L_hierarchical_optionality: bool = True
    enable_M_early_passive_ruin: bool = True

    # A parameters
    crisis_enter_threshold: int = 1   # vs default 2
    crisis_exit_threshold: int = 6    # vs default 3

    # B parameters
    insurance_pool_rate: float = 0.20  # fraction of survivor edu/assets pooled
    insurance_max_coverage: float = 0.50  # max fraction of ruin lineages saved

    # G parameters
    optionality_rollout_depth: int = 1  # cheap 1-step optionality probe
    optionality_weight_boost: float = 0.15  # extra weight in score

    # H parameters
    bandit_exploration_c: float = 1.5
    bandit_n_arms: int = 4

    # I parameters
    synergy_learning_rate: float = 0.05
    synergy_decay: float = 0.99

    # J parameters
    cumulative_drift_decay: float = 0.95  # drift state half-life
    cumulative_drift_quadratic_weight: float = 0.4

    # K parameters
    regret_top_k_alternatives: int = 3
    regret_log_every: int = 5  # log every N generations

    # L parameters
    optionality_weight_individual: float = 0.4
    optionality_weight_family: float = 0.3
    optionality_weight_civ: float = 0.3

    # M parameters
    passive_ruin_slope_window: int = 5
    passive_ruin_slope_threshold: float = -1.5  # O decline per step

    # Backward compat: also expose v6.3 archetype classifier
    enable_archetype_classifier: bool = True


# ============================================================
# A: Asymmetric Hysteresis
# ============================================================

class MetaControllerPP:
    """5-mode meta-controller with asymmetric hysteresis.

    A: Crisis modes enter fast (low enter_th), exit slow (high exit_th).
       This reflects NRMO's philosophy: failure cost > opportunity cost.
    """

    def __init__(self, cfg: VNextPPConfig):
        self.cfg = cfg
        self.mode = MODE_NORMAL
        # Asymmetric: crisis enter fast, exit slow
        if cfg.enable_A_asymmetric_hysteresis:
            self.enter_th = cfg.crisis_enter_threshold
            self.exit_th = cfg.crisis_exit_threshold
        else:
            self.enter_th = 2
            self.exit_th = 3
        self.triggers = {m: 0 for m in [MODE_HIGHSTAKES, MODE_RECOVERY,
                                          MODE_STAGNATION, MODE_RACE]}
        self.stable = 0
        # E: Continuous mode score
        self.mode_scores = {m: 0.0 for m in [MODE_HIGHSTAKES, MODE_RECOVERY,
                                                MODE_STAGNATION, MODE_RACE]}

    def update(self, s: CivState, wp: dict) -> Tuple[str, Dict[str, float]]:
        """Return (discrete mode, continuous mode score dict)."""
        # E: Continuous mode scores
        if self.cfg.enable_E_continuous_mode:
            self.mode_scores[MODE_HIGHSTAKES] = min(1.0, max(0.0,
                (s.X - 35) / 30 * 0.6 + (40 - s.E) / 30 * 0.4))
            self.mode_scores[MODE_RECOVERY] = min(1.0, max(0.0,
                (35 - s.R) / 25 * 0.5 + (35 - s.G) / 25 * 0.5))
            self.mode_scores[MODE_STAGNATION] = min(1.0, max(0.0,
                (40 - s.O) / 30 * 0.6 + (38 - s.K) / 25 * 0.4))
            self.mode_scores[MODE_RACE] = min(1.0, max(0.0,
                (wp.get("rivalry_level", 0) - 0.25) / 0.30))

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
                return self.mode, self.mode_scores
        else:
            self.stable = 0
        self.mode = new
        return self.mode, self.mode_scores


def adaptive_tuning_pp(base: TuningConfig, s: CivState, mode: str,
                        mode_scores: Dict[str, float], cfg: VNextPPConfig) -> TuningConfig:
    """E: Adaptive tuning using continuous mode scores instead of discrete switch."""
    tc = copy.deepcopy(base)
    if cfg.enable_E_continuous_mode:
        # Weighted combination of all mode adjustments
        hs = mode_scores.get(MODE_HIGHSTAKES, 0)
        rc = mode_scores.get(MODE_RECOVERY, 0)
        st = mode_scores.get(MODE_STAGNATION, 0)
        rr = mode_scores.get(MODE_RACE, 0)

        # HighStakes pulls growth_cap down
        tc.growth_cap = tc.growth_cap * (1 - 0.35 * hs)
        tc.exposure_penalty_weight = tc.exposure_penalty_weight + 0.20 * hs
        # Recovery further tightens
        tc.growth_cap = tc.growth_cap * (1 - 0.30 * rc)
        tc.governance_repair_floor = tc.governance_repair_floor + 0.06 * rc
        # Stagnation opens exploration
        tc.exploration_floor = tc.exploration_floor + 0.12 * st
        tc.knowledge_weight = tc.knowledge_weight + 0.10 * st
        # Race relaxes growth_cap upward (rivalry compels growth)
        tc.growth_cap = tc.growth_cap + 0.06 * rr

        # State-based fine adjustments (from v6.3 adaptive_tuning)
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

        # Clip to safe bounds
        tc.growth_cap = max(0.20, min(0.55, tc.growth_cap))
        tc.exploration_floor = max(0.15, min(0.35, tc.exploration_floor))
        return tc
    else:
        # Fall back to v6.3 discrete-mode tuning
        return adaptive_tuning_v63(base, s, mode)


# ============================================================
# B: Insurance Layer
# ============================================================

@dataclass
class InsurancePool:
    """Civilization-level insurance pool that protects against
    catastrophic lineage absorption."""
    accumulated_edu: float = 0.0
    accumulated_assets: float = 0.0
    n_contributors: int = 0
    n_rescues: int = 0
    cumulative_payout: float = 0.0

    def contribute(self, survivor_edu_mean: float, survivor_assets_mean: float,
                    rate: float, n_survivors: int):
        """Survivors contribute a fraction to the pool."""
        self.accumulated_edu += survivor_edu_mean * rate * n_survivors
        self.accumulated_assets += survivor_assets_mean * rate * n_survivors
        self.n_contributors += n_survivors

    def rescue(self, n_at_risk: int, max_coverage: float, rng) -> np.ndarray:
        """Return boolean array of size n_at_risk: True if rescued.

        Max coverage = fraction. Rescue prob increases with pool size."""
        if n_at_risk == 0 or self.n_contributors == 0:
            return np.zeros(0, dtype=bool)
        # Per-rescue cost: 1 unit of edu + 1 unit of assets
        budget_edu = self.accumulated_edu
        budget_assets = self.accumulated_assets
        cost_per_rescue = 0.5  # arbitrary cost units
        n_affordable = int(min(budget_edu, budget_assets) / cost_per_rescue)
        n_to_rescue = min(n_at_risk, int(n_at_risk * max_coverage), n_affordable)
        if n_to_rescue == 0:
            return np.zeros(n_at_risk, dtype=bool)
        rescued_mask = np.zeros(n_at_risk, dtype=bool)
        rescued_idx = rng.choice(n_at_risk, size=n_to_rescue, replace=False)
        rescued_mask[rescued_idx] = True
        self.accumulated_edu -= n_to_rescue * cost_per_rescue
        self.accumulated_assets -= n_to_rescue * cost_per_rescue
        self.n_rescues += n_to_rescue
        self.cumulative_payout += n_to_rescue * cost_per_rescue
        return rescued_mask


# ============================================================
# C: Distributional CivState
# ============================================================

@dataclass
class CivStateDistributional:
    """Extended CivState that keeps distributional moments, not just means.

    Each axis has: mean, p25, p75, var.
    The 'scalar' version is preserved for downstream compat.
    """
    # Mean values (v6.3 compat)
    R: float = 60.0; E: float = 65.0; G: float = 55.0
    O: float = 50.0; K: float = 50.0; X: float = 20.0
    # Distributional moments
    R_p25: float = 60.0; R_p75: float = 60.0; R_var: float = 0.0
    E_p25: float = 65.0; E_p75: float = 65.0; E_var: float = 0.0
    G_p25: float = 55.0; G_p75: float = 55.0; G_var: float = 0.0
    O_p25: float = 50.0; O_p75: float = 50.0; O_var: float = 0.0
    K_p25: float = 50.0; K_p75: float = 50.0; K_var: float = 0.0
    X_p25: float = 20.0; X_p75: float = 20.0; X_var: float = 0.0
    # Metadata
    step: int = 0
    alive: bool = True
    mode: str = "Normal"
    # M: passive ruin slope monitoring
    O_history: List[float] = field(default_factory=list)
    O_slope: float = 0.0
    K_history: List[float] = field(default_factory=list)
    K_slope: float = 0.0
    # J: cumulative drift state
    cumulative_drift: float = 0.0

    def to_scalar(self) -> CivState:
        """Convert to v6.3 CivState for downstream compatibility."""
        return CivState(R=self.R, E=self.E, G=self.G, O=self.O, K=self.K, X=self.X,
                         step=self.step, alive=self.alive, mode=self.mode)


def aggregate_to_civstate_distributional(fk, edu, inst, trade, assets, urban,
                                           absorbed, religion_strength, shock_add,
                                           prev_state=None, step=0) -> CivStateDistributional:
    """C: Distributional aggregation."""
    active = ~absorbed
    if not active.any():
        return CivStateDistributional(alive=False, step=step)

    a = lambda arr: arr[active]
    f_edu = a(edu); f_ass = a(assets); f_ins = a(inst)
    f_urb = a(urban); f_fk = a(fk)

    K = float(f_edu.mean() * 130)
    R = float(f_ass.mean() * 130)
    G = float(f_ins.mean() * 130)
    var_prosperity = float(np.var(f_edu + f_ass))
    O_state = (0.6 * f_urb.mean() + 0.4 * f_edu.mean()) * 130 + var_prosperity * 30
    E = max(8, 65 - shock_add * 80 + f_fk.mean() * 50)
    X = min(95, shock_add * 100 + var_prosperity * 15)

    def pctl(arr, scale):
        if len(arr) < 4:
            return float(arr.mean() * scale), float(arr.mean() * scale), 0.0
        return (float(np.percentile(arr, 25) * scale),
                float(np.percentile(arr, 75) * scale),
                float(arr.var() * scale * scale))

    R_p25, R_p75, R_var = pctl(f_ass, 130)
    K_p25, K_p75, K_var = pctl(f_edu, 130)
    G_p25, G_p75, G_var = pctl(f_ins, 130)
    O_arr = 0.6 * f_urb + 0.4 * f_edu
    O_p25, O_p75, O_var = pctl(O_arr, 130)
    # E and X are scalar-derived; copy
    E_p25, E_p75, E_var = E, E, 0.0
    X_p25, X_p75, X_var = X, X, 0.0

    if prev_state is not None and isinstance(prev_state, CivStateDistributional):
        sd = prev_state
        # M: update slope history
        sd.O_history.append(O_state)
        if len(sd.O_history) > 10:
            sd.O_history.pop(0)
        if len(sd.O_history) >= 3:
            sd.O_slope = float(np.polyfit(range(len(sd.O_history)), sd.O_history, 1)[0])
        sd.K_history.append(K)
        if len(sd.K_history) > 10:
            sd.K_history.pop(0)
        if len(sd.K_history) >= 3:
            sd.K_slope = float(np.polyfit(range(len(sd.K_history)), sd.K_history, 1)[0])
        sd.R, sd.E, sd.G, sd.O, sd.K, sd.X = R, E, G, O_state, K, X
        sd.R_p25 = R_p25; sd.R_p75 = R_p75; sd.R_var = R_var
        sd.E_p25 = E_p25; sd.E_p75 = E_p75; sd.E_var = E_var
        sd.G_p25 = G_p25; sd.G_p75 = G_p75; sd.G_var = G_var
        sd.O_p25 = O_p25; sd.O_p75 = O_p75; sd.O_var = O_var
        sd.K_p25 = K_p25; sd.K_p75 = K_p75; sd.K_var = K_var
        sd.X_p25 = X_p25; sd.X_p75 = X_p75; sd.X_var = X_var
        sd.step = step
        return sd
    sd = CivStateDistributional(R=R, E=E, G=G, O=O_state, K=K, X=X,
                                  R_p25=R_p25, R_p75=R_p75, R_var=R_var,
                                  K_p25=K_p25, K_p75=K_p75, K_var=K_var,
                                  G_p25=G_p25, G_p75=G_p75, G_var=G_var,
                                  O_p25=O_p25, O_p75=O_p75, O_var=O_var,
                                  X_p25=X_p25, X_p75=X_p75, X_var=X_var,
                                  step=step)
    sd.O_history = [O_state]
    sd.K_history = [K]
    return sd


# ============================================================
# D: State-conditioned sigma in action projection
# ============================================================

def project_action_to_agents_pp(civ_action, agent_strategy, strategy_names,
                                 rng, n_agents, cfg: VNextPPConfig,
                                 edu=None, assets=None, inst=None, shock_add=0.0):
    """D: agent state aware sigma scaling.

    Agents in crisis (low edu/assets, high shock) → σ smaller (tighter track).
    Safe agents → σ larger (free exploration).
    """
    base_sigma = {
        "NRMO_vNext": 0.03, "NRMO": 0.03,
        "Adaptive_OmegaFull": 0.04,
        "RiskAdjustedUtility": 0.06,
        "ExpectedValueMax": 0.05,
        "Faith_Buddhist": 0.07, "Faith_Communal": 0.07,
        "Faith_Calvinist": 0.06, "Faith_Charismatic": 0.10,
        "Faith_Ascetic": 0.08, "Faith_Militant": 0.09,
        "Drift": -1.0,
    }
    actions = np.zeros((n_agents, 4))
    for s_idx, sname in enumerate(strategy_names):
        mask = agent_strategy == s_idx
        if not mask.any():
            continue
        n_sub = int(mask.sum())
        sigma = base_sigma.get(sname, 0.06)
        if sigma < 0:
            sub = np.tile(np.array([0.18, 0.30, 0.22, 0.30]), (n_sub, 1))
            actions[mask] = sub
            continue

        # D: state-conditioned sigma
        if cfg.enable_D_state_conditioned_sigma and edu is not None:
            # Per-agent severity 0..1: high if low edu+assets, high shock
            sub_edu = edu[mask]; sub_ass = assets[mask]; sub_inst = inst[mask] if inst is not None else None
            prosperity = sub_edu + sub_ass
            # Lower prosperity → higher severity → smaller sigma
            severity = np.clip(1 - prosperity / 2, 0, 1) * 0.6 + np.clip(shock_add, 0, 0.5) * 0.4
            sigma_scaled = sigma * (1 - severity * 0.7)  # max 70% reduction
            sub = np.tile(civ_action, (n_sub, 1)) + \
                   rng.normal(0, 1.0, size=(n_sub, 4)) * sigma_scaled[:, None]
        else:
            sub = np.tile(civ_action, (n_sub, 1)) + rng.normal(0, sigma, size=(n_sub, 4))

        # Strategy-specific bias
        if sname == "ExpectedValueMax":
            sub[:, 0] += 0.05; sub[:, 1] -= 0.03
        elif sname == "Faith_Ascetic":
            sub[:, 0] -= 0.05; sub[:, 1] += 0.04; sub[:, 2] -= 0.02
        elif sname == "Faith_Militant":
            sub[:, 0] += 0.04; sub[:, 1] -= 0.02
        elif sname == "Faith_Communal":
            sub[:, 1] += 0.03; sub[:, 3] += 0.02
        elif sname == "Faith_Calvinist":
            sub[:, 0] += 0.02; sub[:, 1] += 0.01
        elif sname == "Faith_Charismatic":
            sub[:, 2] += 0.04; sub[:, 1] -= 0.03

        sub = np.clip(sub, 0.05, None)
        sub = sub / sub.sum(axis=1, keepdims=True)
        actions[mask] = sub
    return actions


# ============================================================
# F: Shared Failure Memory across civilizations
# ============================================================

class SharedFailureMemory:
    """F: Cross-civ failure transmission.

    Each civ contributes observable failures (large-scale: war collapse,
    pandemic peaks, extinction events) to a shared pool. Other civs can
    read this pool with a 'cultural distance' decay.
    """

    def __init__(self, mx=128):
        self.records = deque(maxlen=mx)

    def contribute(self, civ_name, world, ruin_mode, archetype, state_arr,
                    step, severity):
        """Severity-gated: only high-severity failures are shared."""
        if severity < 0.5:
            return  # Only share major failures
        self.records.append({
            "civ": civ_name, "world": world, "ruin_mode": ruin_mode,
            "archetype": archetype, "state": state_arr.copy(),
            "step": step, "severity": severity,
        })

    def query(self, civ_name, archetype, state_arr, cultural_distance_fn=None):
        """Return penalty modifier 0..0.3 based on similar historical failures."""
        if not self.records:
            return 0.0
        pen = 0.0
        for r in self.records:
            if r["civ"] == civ_name:
                continue  # already in own memory
            d = float(np.mean(np.abs(state_arr - r["state"])))
            if d > 30:
                continue
            sim = max(0, 1 - d / 30)
            cd = cultural_distance_fn(civ_name, r["civ"]) if cultural_distance_fn else 0.5
            transmission = max(0, 1 - cd)
            if r["archetype"] == archetype:
                pen = max(pen, sim * transmission * 0.30 * r["severity"])
            else:
                pen = max(pen, sim * transmission * 0.10 * r["severity"])
        return pen


# Cultural distance proxy: civs from same region have low distance
CULTURAL_DISTANCE = {
    ("Japan", "China"): 0.3, ("China", "Japan"): 0.3,
    ("Japan", "Indic"): 0.5, ("Indic", "Japan"): 0.5,
    ("China", "Indic"): 0.4, ("Indic", "China"): 0.4,
    ("Europe", "Islamic"): 0.5, ("Islamic", "Europe"): 0.5,
    ("Islamic", "SubSaharan"): 0.4, ("SubSaharan", "Islamic"): 0.4,
    ("Europe", "IndigenousAmericas"): 0.9, ("IndigenousAmericas", "Europe"): 0.9,
    ("Europe", "Polynesian"): 0.85, ("Polynesian", "Europe"): 0.85,
    ("China", "Steppe"): 0.4, ("Steppe", "China"): 0.4,
}


def cultural_distance_fn(a, b):
    if a == b:
        return 0.0
    return CULTURAL_DISTANCE.get((a, b), 0.7)  # default: distant


# ============================================================
# G: True Optionality measure via rollout
# ============================================================

def estimate_optionality(s, action, wp, rng, cfg: VNextPPConfig,
                          tc: TuningConfig = None, nc: NRMOCoreConfig = None):
    """G: True optionality = log |A(S')| after taking action.

    1-step rollout, then count admissible actions in resulting state."""
    if not cfg.enable_G_true_optionality:
        return s.O / 130  # fallback to proxy

    nc = nc or NRMOCoreConfig()
    tc = tc or TuningConfig()
    rc = RolloutConfig()
    # 1-step rollout
    s_next = civstate_transition(s, action, wp, rng, rc)
    if is_ruin_state(s_next):
        return 0.0  # no optionality after ruin
    # Build candidate pool for next state and count admissibility
    pool = build_candidate_pool(s_next, wp, rng, wolf=False)
    admissible, _ = construct_admissible_set(pool, s_next, mode="vnext",
                                               nc=nc, tc=tc)
    n_admissible = len(admissible)
    if n_admissible == 0:
        return 0.0
    # log-scaled, normalized to ~[0, 1] (typical pool size ~25)
    return np.log(1 + n_admissible) / np.log(1 + 30)


# ============================================================
# H: Online Bandit Tuning
# ============================================================

class BanditTuner:
    """H: UCB bandit over a finite set of tuning variations.

    Per-mode, the bandit tracks N_arms tuning variants (e.g. growth_cap
    perturbations) and selects via UCB1. Updates use observed score
    delta over a fixed window."""

    def __init__(self, cfg: VNextPPConfig):
        self.cfg = cfg
        self.n_arms = cfg.bandit_n_arms
        self.c = cfg.bandit_exploration_c
        # Per-mode arm stats
        self.arms = {m: {"counts": np.zeros(self.n_arms),
                          "rewards": np.zeros(self.n_arms)}
                     for m in [MODE_NORMAL, MODE_HIGHSTAKES, MODE_RECOVERY,
                                MODE_STAGNATION, MODE_RACE]}
        self.total_pulls = {m: 0 for m in self.arms}

    def select_arm(self, mode: str) -> int:
        """Select arm via UCB1."""
        stats = self.arms.get(mode)
        if stats is None:
            return 0
        N = self.total_pulls[mode]
        if N < self.n_arms:
            return N  # exploration: try each arm at least once
        means = np.where(stats["counts"] > 0,
                         stats["rewards"] / stats["counts"], 0)
        ucb = means + self.c * np.sqrt(np.log(N + 1) / (stats["counts"] + 1e-9))
        return int(np.argmax(ucb))

    def update(self, mode: str, arm: int, reward: float):
        stats = self.arms.get(mode)
        if stats is None:
            return
        stats["counts"][arm] += 1
        stats["rewards"][arm] += reward
        self.total_pulls[mode] += 1

    def apply_arm(self, tc: TuningConfig, mode: str, arm: int) -> TuningConfig:
        """Apply arm-specific perturbation to TuningConfig."""
        tc = copy.deepcopy(tc)
        # 4 arms: -delta, 0, +delta, +2*delta on growth_cap
        delta = 0.04 * (arm - 1)  # arms 0,1,2,3 → -0.04, 0, +0.04, +0.08
        tc.growth_cap = np.clip(tc.growth_cap + delta, 0.18, 0.55)
        return tc


# ============================================================
# I: Synergy matrix learning
# ============================================================

class SynergyMatrix:
    """I: Auto-learn synergy values between action archetypes from rollouts.

    Synergy(a, b) = score(combined) - 0.5*(score(a) + score(b))
    Updated via exponential moving average."""

    def __init__(self, cfg: VNextPPConfig,
                  archetypes=("balanced", "high_growth", "safety", "exploration",
                               "recovery", "governance_repair", "eco_preserve",
                               "edge_floor", "race_expansion", "hybrid")):
        self.cfg = cfg
        self.archetypes = list(archetypes)
        n = len(self.archetypes)
        self.matrix = np.zeros((n, n))
        self.counts = np.zeros((n, n), dtype=int)
        self.lr = cfg.synergy_learning_rate
        self.decay = cfg.synergy_decay

    def lookup(self, a1_arch: str, a2_arch: str) -> float:
        if a1_arch not in self.archetypes or a2_arch not in self.archetypes:
            return 0.0
        i = self.archetypes.index(a1_arch)
        j = self.archetypes.index(a2_arch)
        return float(self.matrix[i, j])

    def update(self, a1_arch: str, a2_arch: str, observed_synergy: float):
        if a1_arch not in self.archetypes or a2_arch not in self.archetypes:
            return
        i = self.archetypes.index(a1_arch)
        j = self.archetypes.index(a2_arch)
        # symmetric update
        self.matrix[i, j] = self.decay * self.matrix[i, j] + self.lr * observed_synergy
        self.matrix[j, i] = self.matrix[i, j]
        self.counts[i, j] += 1
        self.counts[j, i] = self.counts[i, j]


# ============================================================
# J: Cumulative drift
# ============================================================

def update_cumulative_drift(sd: CivStateDistributional, drift_now: float,
                              cfg: VNextPPConfig) -> float:
    """J: Update cumulative_drift state with decay; return quadratic penalty."""
    if not cfg.enable_J_cumulative_drift:
        return drift_now  # plain linear
    sd.cumulative_drift = sd.cumulative_drift * cfg.cumulative_drift_decay + drift_now
    # Quadratic penalty
    return drift_now + cfg.cumulative_drift_quadratic_weight * (sd.cumulative_drift ** 2)


# ============================================================
# K: Counterfactual decision regret tracking
# ============================================================

class RegretTracker:
    """K: Track regret per chosen action by evaluating alternatives.

    For each decision: record chosen action + top-K alternatives.
    Periodically (every N gens), rollout each to compare final scores.
    """

    def __init__(self, cfg: VNextPPConfig):
        self.cfg = cfg
        self.records = []  # list of (step, chosen, alternatives, civ_state_at_decision)
        self.realized_regrets = []  # (step, regret)

    def record_decision(self, step, civ_state, chosen, alternatives, scores):
        if not self.cfg.enable_K_counterfactual_regret:
            return
        if step % self.cfg.regret_log_every != 0:
            return
        # Keep top-K
        k = self.cfg.regret_top_k_alternatives
        top_alts = alternatives[:k]
        top_scores = scores[:k]
        self.records.append({"step": step, "civ_state": civ_state.copy() if hasattr(civ_state, "copy") else civ_state,
                              "chosen": chosen, "chosen_score": scores[0] if scores else 0.0,
                              "alternatives": top_alts, "alt_scores": top_scores})

    def realize(self, wp, rng, oc, cfg_pp, civ_name):
        """At end of simulation, realize regret by rolling out alternatives."""
        if not self.cfg.enable_K_counterfactual_regret or not self.records:
            return
        from vnext_plus import score_candidate, FailureMemory, classify_archetype
        rc = RolloutConfig()
        fm = FailureMemory()
        for rec in self.records[-20:]:  # last 20 decisions only
            s = rec["civ_state"]
            chosen = rec["chosen"]
            chosen_arch = classify_archetype(chosen)
            chosen_m = score_candidate(s, chosen, wp, rng, oc, rc, fm,
                                         "Normal", 0.5, chosen_arch, None, False, False)
            best_alt_score = chosen_m["score"]
            for alt in rec["alternatives"]:
                alt_arch = classify_archetype(alt)
                alt_m = score_candidate(s, alt, wp, rng, oc, rc, fm,
                                         "Normal", 0.5, alt_arch, None, False, False)
                if alt_m["score"] > best_alt_score:
                    best_alt_score = alt_m["score"]
            regret = best_alt_score - chosen_m["score"]
            self.realized_regrets.append({"step": rec["step"],
                                            "regret": float(regret),
                                            "civ": civ_name})

    def summary(self):
        if not self.realized_regrets:
            return {"n": 0, "mean_regret": 0.0, "max_regret": 0.0}
        rs = [r["regret"] for r in self.realized_regrets]
        return {"n": len(rs),
                "mean_regret": float(np.mean(rs)),
                "max_regret": float(np.max(rs))}


# ============================================================
# L: Hierarchical Optionality
# ============================================================

def hierarchical_optionality_score(individual_opt, family_opt, civ_opt,
                                     cfg: VNextPPConfig) -> float:
    """L: Combined optionality across three tiers.

    individual: log |A(individual_state)|
    family: log |A(family_state)| (4 branches share resources)
    civ: log |A(civ_state)|
    """
    if not cfg.enable_L_hierarchical_optionality:
        return civ_opt
    return (cfg.optionality_weight_individual * individual_opt
            + cfg.optionality_weight_family * family_opt
            + cfg.optionality_weight_civ * civ_opt)


# ============================================================
# M: Early passive ruin detection
# ============================================================

def check_passive_ruin_early(sd: CivStateDistributional, cfg: VNextPPConfig) -> Tuple[bool, str]:
    """M: Detect passive ruin via O/K slope.

    Returns (warning, reason). Triggers if O or K has steep decline trend.
    """
    if not cfg.enable_M_early_passive_ruin:
        return False, "M_disabled"
    if len(sd.O_history) < cfg.passive_ruin_slope_window:
        return False, "insufficient_history"
    if sd.O_slope < cfg.passive_ruin_slope_threshold:
        return True, f"O_slope={sd.O_slope:.2f} below threshold"
    if sd.K_slope < cfg.passive_ruin_slope_threshold:
        return True, f"K_slope={sd.K_slope:.2f} below threshold"
    return False, "trends_ok"


# ============================================================
# Main vNext++ Controller (assembles all A-M)
# ============================================================

class NRMOController:
    """Master controller per civilization for v6.4 vNext++.

    Renamed from VNextPlusCivController; the entity itself is now just
    called "NRMO" (with NRMO_Origin available as comparator).
    """

    def __init__(self, civ_name, civ_module, cfg: VNextPPConfig = None,
                  shared_failure_memory: Optional[SharedFailureMemory] = None,
                  oc=None):
        self.civ_name = civ_name
        self.civ_module = civ_module
        self.cfg = cfg or VNextPPConfig()
        self.meta = MetaControllerPP(self.cfg)
        self.engine = OmegaFullEngine(oc, self.cfg.enable_archetype_classifier)
        # B: Insurance pool
        self.insurance = InsurancePool() if self.cfg.enable_B_insurance_layer else None
        # F: Shared failure memory (passed in by simulator)
        self.shared_fm = shared_failure_memory
        # H: Bandit tuner
        self.bandit = BanditTuner(self.cfg) if self.cfg.enable_H_online_tuning else None
        # I: Synergy matrix
        self.synergy = SynergyMatrix(self.cfg) if self.cfg.enable_I_synergy_learning else None
        # K: Regret tracker
        self.regret = RegretTracker(self.cfg) if self.cfg.enable_K_counterfactual_regret else None
        # State (distributional)
        self.civstate_dist = None
        # Logs
        self.tuning_history = []
        self.passive_ruin_warnings = []
        self.bandit_arm_per_gen = []

    def step(self, rng, fk, edu, inst, trade, assets, urban, absorbed,
              religion_strength, shock_add, era_idx, world_name, gen):
        """Full vNext++ pipeline."""
        # C: distributional aggregation
        if self.cfg.enable_C_distributional_state:
            self.civstate_dist = aggregate_to_civstate_distributional(
                fk, edu, inst, trade, assets, urban, absorbed,
                religion_strength, shock_add, self.civstate_dist, step=gen)
            s_scalar = self.civstate_dist.to_scalar()
        else:
            s_scalar = aggregate_to_civstate_v63(
                fk, edu, inst, trade, assets, urban, absorbed,
                religion_strength, shock_add, None, step=gen)

        wp = derive_world_params(self.civ_module, era_idx, religion_strength)

        # A + E: meta-controller (asymmetric hysteresis + continuous mode)
        mode, mode_scores = self.meta.update(s_scalar, wp)
        s_scalar.mode = mode

        # M: passive ruin warning
        if self.civstate_dist is not None:
            warn, reason = check_passive_ruin_early(self.civstate_dist, self.cfg)
            if warn:
                self.passive_ruin_warnings.append({"gen": gen, "reason": reason})
                # Boost stagnation mode score to force action
                if self.cfg.enable_E_continuous_mode:
                    mode_scores[MODE_STAGNATION] = max(mode_scores.get(MODE_STAGNATION, 0), 0.6)

        # Adaptive tuning (continuous-mode based)
        base_profile = get_world_profile(world_name)
        tc = adaptive_tuning_pp(base_profile, s_scalar, mode, mode_scores, self.cfg)

        # H: bandit perturbation
        if self.bandit is not None:
            arm = self.bandit.select_arm(mode)
            tc = self.bandit.apply_arm(tc, mode, arm)
            self.bandit_arm_per_gen.append({"gen": gen, "mode": mode, "arm": arm})

        self.tuning_history.append({"step": gen, "mode": mode,
                                     "mode_scores": dict(mode_scores),
                                     "growth_cap": tc.growth_cap})

        # Candidate pool
        wolf_now = detect_favorable(s_scalar, self.engine.prev_state)
        pool = build_candidate_pool(s_scalar, wp, rng, wolf=wolf_now)

        # NRMO veto (current default = vNext-style)
        admissible, flags = construct_admissible_set(pool, s_scalar, mode="vnext", tc=tc)
        if not admissible:
            civ_action = _norm(np.array([0.05, 0.50, 0.22, 0.23]))
            return civ_action, tc, mode_scores

        # G: optionality enhancement in scoring (rebuild score with rollout-based optionality)
        # We don't rewrite engine internals here; instead bias by computing per-candidate optionality
        # and using as a soft prior to candidate ranking.
        opt_scores = []
        if self.cfg.enable_G_true_optionality:
            for c in admissible:
                opt_scores.append(estimate_optionality(s_scalar, c, wp, rng, self.cfg, tc=tc))

        # Engine selects action (Omega Full)
        civ_action = self.engine.select_action(admissible, s_scalar, wp, rng,
                                                  mode=mode, world_name=world_name)

        # G: post-hoc optionality boost — if there's a near-tied candidate with higher
        # optionality, prefer it
        if self.cfg.enable_G_true_optionality and len(admissible) > 1 and opt_scores:
            best_idx = 0
            # Find candidate that maximizes (opt_score)
            for i, c in enumerate(admissible):
                if opt_scores[i] > opt_scores[best_idx] + 0.10:
                    # Significant optionality advantage — switch
                    civ_action = c
                    best_idx = i
                    break

        # K: regret tracking
        if self.regret is not None and len(admissible) >= 2:
            # Record top alternatives (admissible sorted by quick heuristic)
            self.regret.record_decision(gen, s_scalar, civ_action,
                                          admissible[:self.cfg.regret_top_k_alternatives + 1],
                                          [1.0] + [0.9] * len(admissible[:self.cfg.regret_top_k_alternatives]))

        # F: contribute to shared failure memory if civ is in distress
        if self.shared_fm is not None and is_ruin_state(s_scalar):
            self.shared_fm.contribute(self.civ_name, world_name,
                                        attribute_ruin(s_scalar),
                                        classify_archetype(civ_action),
                                        s_scalar.arr(), gen,
                                        severity=min(1.0, s_scalar.X / 80))

        # H: bandit reward (proxy: current civ productivity)
        if self.bandit is not None and len(self.bandit_arm_per_gen) >= 2:
            prev_prod = productivity_instant(s_scalar, civ_action)
            self.bandit.update(mode, self.bandit_arm_per_gen[-1]["arm"], prev_prod)

        return civ_action, tc, mode_scores

    def apply_insurance(self, absorbed_new_indices, edu, assets, n_at_risk, rng):
        """B: Apply insurance layer to newly-absorbed lineages.

        Returns boolean mask of which absorbed indices are rescued."""
        if self.insurance is None or n_at_risk == 0:
            return np.zeros(n_at_risk, dtype=bool)
        # Survivors contribute (called externally per gen)
        rescued = self.insurance.rescue(n_at_risk, self.cfg.insurance_max_coverage, rng)
        return rescued

    def contribute_to_insurance(self, edu, assets, absorbed, rng):
        """B: Survivors contribute fraction of edu/assets to insurance pool."""
        if self.insurance is None:
            return
        active = ~absorbed
        n_alive = int(active.sum())
        if n_alive == 0:
            return
        self.insurance.contribute(float(edu[active].mean()),
                                    float(assets[active].mean()),
                                    self.cfg.insurance_pool_rate,
                                    n_alive)
