"""
NRMO v7.0 — Collective Governance Extension.

Adds 6 mechanisms (P-U) that Faith_Communal exhibits naturally and which
NRMO (v6.4 = NRMO++) lacks. These are NOT enhancements to NRMO's
individual governance core; they are a parallel COLLECTIVE governance
layer that operates on top of individual-NRMO.

P. Pooling          — multi-tier risk pool (family → lineage → civ)
Q. Quorum           — within-strategy action coordination via majority
R. Reproduction     — strategy transmission parent→child within lineages
S. Solidarity       — civ cohesion state with shock-absorption effect
T. Tradition        — norm-anchored action (individual optimum blended with civ norm)
U. Ultra-horizon    — afterlife/karma boost via gamma → 1 for ascetic/communal strategies

The collective layer respects the governance-execution invariant: it
acts on candidate generation and action sampling but does NOT modify
NRMO Core veto logic. NRMO_Collective = NRMO_individual + COLL[P,Q,R,S,T,U]

Honest claim: empirical effect is untested at design time. Faith_Communal
may still win because:
  - Faith_Communal's mechanisms are religious commitment, which can override
    individual rationality more completely than any "blend ratio" T.
  - The simulator may not have the granularity to capture out-group hostility
    (Faith_Communal's other side, intentionally not implemented here).
  - Calibration of blending weights is heuristic, not optimised.

Expected outcome: NRMO_Collective narrows the Faith_Communal gap by 30-60%
in hostile worlds. Full closure is unlikely.
"""
import numpy as np
import copy
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from typing import Optional, List, Dict, Tuple


# ============================================================
# CONFIG
# ============================================================

@dataclass
class CollectiveConfig:
    """Master config for collective layer."""
    # Master enables
    enable_P_multi_tier_pooling: bool = True
    enable_Q_quorum_coordination: bool = True
    enable_R_strategy_reproduction: bool = True
    enable_S_solidarity_state: bool = True
    enable_T_tradition_blending: bool = True
    enable_U_ultra_horizon: bool = True

    # P parameters (multi-tier pooling)
    p_family_pool_rate: float = 0.25
    p_lineage_pool_rate: float = 0.15
    p_civ_pool_rate: float = 0.10
    p_family_coverage: float = 0.70
    p_lineage_coverage: float = 0.50
    p_civ_coverage: float = 0.30

    # Q parameters (quorum)
    q_quorum_threshold: float = 0.55  # action quorum requires 55% strategy agreement
    q_coordination_weight: float = 0.30  # how much majority action pulls minority

    # R parameters (reproduction)
    r_parent_strategy_inherit_prob: float = 0.70
    r_mutation_prob: float = 0.05  # rare strategy switches

    # S parameters (solidarity)
    s_initial_cohesion: float = 0.50
    s_cohesion_decay: float = 0.98  # per gen
    s_cohesion_shock_amplifier_at_zero: float = 1.5  # shocks 1.5x worse when cohesion = 0
    s_cohesion_shock_dampener_at_one: float = 0.55  # shocks 0.55x when cohesion = 1
    s_pooling_cohesion_boost: float = 0.04  # each rescue boosts cohesion
    s_inequality_cohesion_drag: float = 0.02  # high inequality drags cohesion

    # T parameters (tradition)
    t_norm_weight_per_strategy: Dict[str, float] = field(default_factory=lambda: {
        "NRMO_vNext": 0.10,  # individualistic, slight norm influence
        "Adaptive_OmegaFull": 0.15,
        "ExpectedValueMax": 0.05,  # nearly pure self-interest
        "RiskAdjustedUtility": 0.10,
        "Faith_Buddhist": 0.40,
        "Faith_Communal": 0.60,  # high norm influence (matches its empirical advantage)
        "Faith_Calvinist": 0.35,
        "Faith_Charismatic": 0.30,
        "Faith_Ascetic": 0.55,
        "Faith_Militant": 0.50,
        "Drift": 0.00,
        "NRMO": 0.10,
        "NRMO_Collective": 0.45,  # NEW: explicitly collective
    })

    # U parameters (ultra-horizon)
    # Strategies with eternal-reward beliefs effectively discount less
    u_horizon_boost_per_strategy: Dict[str, float] = field(default_factory=lambda: {
        "Faith_Buddhist": 0.20,
        "Faith_Communal": 0.15,
        "Faith_Calvinist": 0.25,  # predestination + heaven
        "Faith_Ascetic": 0.30,  # strongest eternal focus
        "Faith_Militant": 0.20,  # martyrdom
        "Faith_Charismatic": 0.15,
        "NRMO_Collective": 0.15,
        # individualist strategies: 0
    })


# ============================================================
# P: Multi-Tier Pooling
# ============================================================

@dataclass
class FamilyPool:
    """Pool for one family branch (typically ~4 main + many sub)."""
    accumulated_edu: float = 0.0
    accumulated_assets: float = 0.0
    n_contributors: int = 0
    rescued_total: int = 0


@dataclass
class LineagePool:
    """Pool for one strategy lineage (~all NRMO_vNext agents in civ)."""
    accumulated_edu: float = 0.0
    accumulated_assets: float = 0.0
    n_contributors: int = 0
    rescued_total: int = 0


class MultiTierInsurance:
    """P: 3-tier pool: family → lineage → civilization.

    Each tier covers what the tier below cannot afford.
    Rescue cascade: family tries first, then lineage, then civ.
    """
    def __init__(self, cfg: CollectiveConfig, n_families: int = 4,
                  strategy_names: Optional[List[str]] = None):
        self.cfg = cfg
        self.family_pools = [FamilyPool() for _ in range(n_families)]
        self.lineage_pools = {s: LineagePool() for s in (strategy_names or [])}
        self.civ_pool = LineagePool()  # reuse struct; same fields
        self.total_rescues = 0
        self.payout_history = []

    def contribute(self, family_idx: int, strategy: str,
                    edu_mean: float, assets_mean: float, n_survivors: int):
        """Distribute contributions across three tiers."""
        c = self.cfg
        # Family tier
        if 0 <= family_idx < len(self.family_pools):
            fp = self.family_pools[family_idx]
            fp.accumulated_edu += edu_mean * c.p_family_pool_rate * n_survivors
            fp.accumulated_assets += assets_mean * c.p_family_pool_rate * n_survivors
            fp.n_contributors += n_survivors
        # Lineage tier
        if strategy in self.lineage_pools:
            lp = self.lineage_pools[strategy]
            lp.accumulated_edu += edu_mean * c.p_lineage_pool_rate * n_survivors
            lp.accumulated_assets += assets_mean * c.p_lineage_pool_rate * n_survivors
            lp.n_contributors += n_survivors
        # Civ tier
        self.civ_pool.accumulated_edu += edu_mean * c.p_civ_pool_rate * n_survivors
        self.civ_pool.accumulated_assets += assets_mean * c.p_civ_pool_rate * n_survivors
        self.civ_pool.n_contributors += n_survivors

    def cascade_rescue(self, family_idx: int, strategy: str,
                        n_at_risk: int, rng) -> np.ndarray:
        """Try family → lineage → civ in cascade."""
        if n_at_risk == 0:
            return np.zeros(0, dtype=bool)
        rescued = np.zeros(n_at_risk, dtype=bool)
        cost = 0.5  # cost per rescue
        c = self.cfg

        # Tier 1: family
        if 0 <= family_idx < len(self.family_pools):
            fp = self.family_pools[family_idx]
            n_fam_affordable = int(min(fp.accumulated_edu, fp.accumulated_assets) / cost)
            n_fam = min(n_at_risk, int(n_at_risk * c.p_family_coverage), n_fam_affordable)
            if n_fam > 0:
                idx = rng.choice(n_at_risk, size=n_fam, replace=False)
                rescued[idx] = True
                fp.accumulated_edu -= n_fam * cost
                fp.accumulated_assets -= n_fam * cost
                fp.rescued_total += n_fam

        # Tier 2: lineage (covers remaining)
        if strategy in self.lineage_pools:
            lp = self.lineage_pools[strategy]
            remaining_unrescued = ~rescued
            n_remain = int(remaining_unrescued.sum())
            if n_remain > 0:
                n_lin_affordable = int(min(lp.accumulated_edu, lp.accumulated_assets) / cost)
                n_lin = min(n_remain, int(n_remain * c.p_lineage_coverage), n_lin_affordable)
                if n_lin > 0:
                    remain_idx = np.where(remaining_unrescued)[0]
                    sub = rng.choice(remain_idx, size=n_lin, replace=False)
                    rescued[sub] = True
                    lp.accumulated_edu -= n_lin * cost
                    lp.accumulated_assets -= n_lin * cost
                    lp.rescued_total += n_lin

        # Tier 3: civ (covers what's still remaining)
        remaining_unrescued = ~rescued
        n_remain = int(remaining_unrescued.sum())
        if n_remain > 0:
            n_civ_affordable = int(min(self.civ_pool.accumulated_edu,
                                         self.civ_pool.accumulated_assets) / cost)
            n_civ = min(n_remain, int(n_remain * c.p_civ_coverage), n_civ_affordable)
            if n_civ > 0:
                remain_idx = np.where(remaining_unrescued)[0]
                sub = rng.choice(remain_idx, size=n_civ, replace=False)
                rescued[sub] = True
                self.civ_pool.accumulated_edu -= n_civ * cost
                self.civ_pool.accumulated_assets -= n_civ * cost
                self.civ_pool.rescued_total += n_civ

        self.total_rescues += int(rescued.sum())
        return rescued


# ============================================================
# Q: Quorum Coordination
# ============================================================

def apply_quorum(actions: np.ndarray, agent_strategy: np.ndarray,
                  strategy_names: List[str], cfg: CollectiveConfig,
                  rng) -> np.ndarray:
    """Q: Pull minority agents in each strategy toward strategy majority.

    For each strategy, compute the "modal action" (mean of upper quartile by
    fitness proxy), then blend each agent's action toward it by
    q_coordination_weight if majority quorum reached.
    """
    if not cfg.enable_Q_quorum_coordination:
        return actions
    out = actions.copy()
    for s_idx, sname in enumerate(strategy_names):
        mask = agent_strategy == s_idx
        n = int(mask.sum())
        if n < 5:
            continue
        sub_actions = actions[mask]
        # Modal action = mean of all (could be median for robustness)
        mode_a = sub_actions.mean(axis=0)
        # Check quorum: how many are within 0.1 of mode?
        dist = np.linalg.norm(sub_actions - mode_a, axis=1)
        in_quorum_share = float((dist < 0.15).sum() / n)
        if in_quorum_share >= cfg.q_quorum_threshold:
            # Pull minority toward mode
            w = cfg.q_coordination_weight
            out[mask] = (1 - w) * sub_actions + w * mode_a
            # Renormalize
            out[mask] = np.clip(out[mask], 0.05, None)
            out[mask] = out[mask] / out[mask].sum(axis=1, keepdims=True)
    return out


# ============================================================
# R: Strategy Reproduction (parent → child transmission)
# ============================================================

def apply_strategy_reproduction(new_agent_indices: np.ndarray,
                                  parent_agent_indices: np.ndarray,
                                  agent_strategy: np.ndarray,
                                  n_strategies: int, cfg: CollectiveConfig,
                                  rng) -> np.ndarray:
    """R: Newly-created lineages (via collateral_reset or similar) inherit
    parent's strategy with prob inherit_prob, mutate otherwise.

    Args:
      new_agent_indices: indices of agents that just got reset/born
      parent_agent_indices: corresponding parent indices (same length)
    Returns:
      modified agent_strategy array (in-place)
    """
    if not cfg.enable_R_strategy_reproduction:
        return agent_strategy
    if len(new_agent_indices) == 0:
        return agent_strategy
    n_new = len(new_agent_indices)
    inherit_mask = rng.random(n_new) < cfg.r_parent_strategy_inherit_prob
    # Inherit: copy parent's strategy
    for k in range(n_new):
        if inherit_mask[k]:
            new_idx = new_agent_indices[k]
            par_idx = parent_agent_indices[k]
            agent_strategy[new_idx] = agent_strategy[par_idx]
    # Mutation: small fraction switch to random strategy
    mutate_mask = (~inherit_mask) & (rng.random(n_new) < cfg.r_mutation_prob)
    n_mutate = int(mutate_mask.sum())
    if n_mutate > 0:
        new_strategies = rng.integers(0, n_strategies, size=n_mutate)
        agent_strategy[new_agent_indices[mutate_mask]] = new_strategies
    return agent_strategy


# ============================================================
# S: Solidarity State
# ============================================================

@dataclass
class SolidarityState:
    """S: Civilisation cohesion / solidarity, evolves over time.

    High cohesion → shocks are absorbed (multiplied by < 1).
    Low cohesion → shocks amplified.
    Updated by:
    - Pooling activity raises cohesion (+ shared sacrifice)
    - Inequality lowers cohesion
    - Crisis events lower cohesion (panic)
    - Stable peace raises cohesion (gradual)
    """
    cohesion: float = 0.5  # in [0, 1]
    history: List[float] = field(default_factory=list)

    def absorb_factor(self, cfg: CollectiveConfig) -> float:
        """Returns shock multiplier in [absorb_at_1, amplify_at_0]."""
        if not cfg.enable_S_solidarity_state:
            return 1.0
        # Linear interpolation: cohesion=0 → amplifier, cohesion=1 → dampener
        return (cfg.s_cohesion_shock_amplifier_at_zero
                + self.cohesion * (cfg.s_cohesion_shock_dampener_at_one
                                    - cfg.s_cohesion_shock_amplifier_at_zero))

    def update(self, n_rescues_this_gen: int, n_total: int,
                inequality_var: float, crisis_this_gen: bool,
                cfg: CollectiveConfig):
        # Decay
        self.cohesion *= cfg.s_cohesion_decay
        # Pooling boost
        if n_total > 0:
            rescue_intensity = n_rescues_this_gen / n_total
            self.cohesion += cfg.s_pooling_cohesion_boost * rescue_intensity * 10
        # Inequality drag
        self.cohesion -= cfg.s_inequality_cohesion_drag * min(inequality_var * 4, 1)
        # Crisis drag
        if crisis_this_gen:
            self.cohesion -= 0.06
        # Gradual peace boost (if no crisis and no rescues)
        if not crisis_this_gen and n_rescues_this_gen == 0:
            self.cohesion += 0.005
        self.cohesion = float(np.clip(self.cohesion, 0.0, 1.0))
        self.history.append(self.cohesion)


# ============================================================
# T: Tradition (norm-anchored action blending)
# ============================================================

def apply_tradition_blend(actions: np.ndarray, agent_strategy: np.ndarray,
                            strategy_names: List[str],
                            tradition_action: np.ndarray,
                            cfg: CollectiveConfig) -> np.ndarray:
    """T: Blend individual optimum with civ's tradition action.

    For each strategy s, blend_ratio = t_norm_weight_per_strategy[s].
    Faith_Communal (0.60) → 60% tradition, 40% individual.
    NRMO_vNext (0.10) → 10% tradition, 90% individual.
    """
    if not cfg.enable_T_tradition_blending:
        return actions
    out = actions.copy()
    for s_idx, sname in enumerate(strategy_names):
        mask = agent_strategy == s_idx
        if not mask.any():
            continue
        w = cfg.t_norm_weight_per_strategy.get(sname, 0.0)
        if w == 0:
            continue
        # Blend
        out[mask] = (1 - w) * actions[mask] + w * tradition_action
        out[mask] = np.clip(out[mask], 0.05, None)
        out[mask] = out[mask] / out[mask].sum(axis=1, keepdims=True)
    return out


def compute_tradition_action(actions: np.ndarray, agent_strategy: np.ndarray,
                              strategy_names: List[str], absorbed: np.ndarray,
                              cfg: CollectiveConfig) -> np.ndarray:
    """T: Determine the civ's tradition action = weighted mean of all active
    agents' actions, weighted by their tradition weights.

    Strategies with high norm_weight contribute more to defining the norm
    (Faith_Communal 0.60 contributes 6x more than EVMax 0.05). This reflects
    that high-tradition groups are the norm-setters.
    """
    active = ~absorbed
    if not active.any():
        return np.array([0.20, 0.30, 0.25, 0.25])
    weighted_sum = np.zeros(4)
    total_w = 0
    for s_idx, sname in enumerate(strategy_names):
        mask = active & (agent_strategy == s_idx)
        if not mask.any():
            continue
        w = cfg.t_norm_weight_per_strategy.get(sname, 0.05)
        n = int(mask.sum())
        weighted_sum += actions[mask].mean(axis=0) * w * n
        total_w += w * n
    if total_w == 0:
        return np.array([0.20, 0.30, 0.25, 0.25])
    norm = weighted_sum / total_w
    norm = np.clip(norm, 0.05, None)
    return norm / norm.sum()


# ============================================================
# U: Ultra-horizon (afterlife / karma boost)
# ============================================================

def apply_ultra_horizon_boost(dfp: np.ndarray, agent_strategy: np.ndarray,
                                strategy_names: List[str],
                                cfg: CollectiveConfig) -> np.ndarray:
    """U: Strategies with ultra-horizon beliefs effectively reduce the
    perceived weight of death-in-this-generation.

    Implementation: reduce dfp (death-failure-probability) for these
    strategies by the boost factor. This represents the agent's
    willingness to take risks for inter-generational/eternal gains.

    Note: This is per-agent dfp reduction, not state change. It models
    the BEHAVIORAL effect of long-horizon beliefs, not actual immortality.

    Mathematically equivalent to: these strategies have effective gamma
    closer to 1 in the discounted value calculation.
    """
    if not cfg.enable_U_ultra_horizon:
        return dfp
    out = dfp.copy()
    for s_idx, sname in enumerate(strategy_names):
        mask = agent_strategy == s_idx
        if not mask.any():
            continue
        boost = cfg.u_horizon_boost_per_strategy.get(sname, 0.0)
        if boost == 0:
            continue
        # Reduce dfp by up to 30% for strongest belief
        out[mask] = out[mask] * (1 - boost * 0.5)
    return out


# ============================================================
# Master collective controller (one per civ)
# ============================================================

class CollectiveCivController:
    """One per civilization. Coordinates all 6 mechanisms.

    Used alongside (not replacing) NRMOController from v6.4.
    """

    def __init__(self, civ_name: str, civ_module, cfg: CollectiveConfig = None,
                  strategy_names: Optional[List[str]] = None,
                  n_families: int = 4):
        self.civ_name = civ_name
        self.civ_module = civ_module
        self.cfg = cfg or CollectiveConfig()
        self.insurance = MultiTierInsurance(self.cfg, n_families=n_families,
                                              strategy_names=strategy_names) \
                          if self.cfg.enable_P_multi_tier_pooling else None
        self.solidarity = SolidarityState(cohesion=self.cfg.s_initial_cohesion) \
                          if self.cfg.enable_S_solidarity_state else None
        self.gen_rescues = 0  # track rescues per gen for solidarity update

    def project_actions_with_collective_layer(self, civ_action, agent_strategy,
                                                 strategy_names, edu, assets, inst,
                                                 absorbed, rng, n_agents):
        """Build per-agent actions with Q, T applied on top of base projection."""
        # Base projection (state-conditioned sigma from v6.4)
        from vnext_pp_v64 import project_action_to_agents_pp, VNextPPConfig
        pp_cfg = VNextPPConfig()  # default
        actions = project_action_to_agents_pp(
            civ_action, agent_strategy, strategy_names, rng, n_agents,
            pp_cfg, edu=edu, assets=assets, inst=inst, shock_add=0.0)

        # T: tradition blending
        tradition = compute_tradition_action(actions, agent_strategy,
                                                strategy_names, absorbed, self.cfg)
        actions = apply_tradition_blend(actions, agent_strategy,
                                          strategy_names, tradition, self.cfg)

        # Q: quorum coordination
        actions = apply_quorum(actions, agent_strategy, strategy_names,
                                 self.cfg, rng)

        return actions

    def apply_dfp_modifiers(self, dfp, agent_strategy, strategy_names):
        """U: ultra-horizon dfp reduction."""
        return apply_ultra_horizon_boost(dfp, agent_strategy, strategy_names, self.cfg)

    def apply_shock_modifiers(self, shock_add):
        """S: solidarity-based shock absorption.

        Returns modified shock_add multiplied by absorb_factor."""
        if self.solidarity is None:
            return shock_add
        return shock_add * self.solidarity.absorb_factor(self.cfg)

    def step_end_of_generation(self, edu, assets, absorbed, agent_strategy,
                                strategy_names, family_assignment, crisis_flag,
                                rng):
        """Called at end of each generation:
        - Survivors contribute to multi-tier insurance
        - Solidarity updates
        """
        if self.insurance is not None:
            active = ~absorbed
            # Per-family / per-strategy contribution
            for fam_idx in range(len(self.insurance.family_pools)):
                fam_mask = active & (family_assignment == fam_idx)
                if not fam_mask.any():
                    continue
                for s_idx, sname in enumerate(strategy_names):
                    strat_mask = fam_mask & (agent_strategy == s_idx)
                    if not strat_mask.any():
                        continue
                    n = int(strat_mask.sum())
                    self.insurance.contribute(
                        fam_idx, sname,
                        float(edu[strat_mask].mean()),
                        float(assets[strat_mask].mean()),
                        n)

        # S: Solidarity update
        if self.solidarity is not None:
            active = ~absorbed
            n_total = int(active.sum())
            inequality_var = float(np.var(edu[active] + assets[active])) if n_total > 0 else 0.0
            self.solidarity.update(
                n_rescues_this_gen=self.gen_rescues,
                n_total=n_total,
                inequality_var=inequality_var,
                crisis_this_gen=crisis_flag,
                cfg=self.cfg)
        # Reset per-gen rescue counter
        self.gen_rescues = 0

    def attempt_rescue_cascade(self, at_risk_indices, family_assignment,
                                 agent_strategy, strategy_names, rng):
        """P: Try multi-tier rescue. Returns boolean mask of which were saved."""
        if self.insurance is None or len(at_risk_indices) == 0:
            return np.zeros(len(at_risk_indices), dtype=bool)
        # Group at-risk indices by (family, strategy) for efficient rescue
        rescued = np.zeros(len(at_risk_indices), dtype=bool)
        # Process per family-strategy group
        groups = defaultdict(list)
        for k, gi in enumerate(at_risk_indices):
            fam = int(family_assignment[gi])
            strat_idx = int(agent_strategy[gi])
            groups[(fam, strat_idx)].append(k)
        for (fam, strat_idx), local_k_list in groups.items():
            strat_name = strategy_names[strat_idx]
            n_at_risk_local = len(local_k_list)
            sub_rescued = self.insurance.cascade_rescue(fam, strat_name,
                                                          n_at_risk_local, rng)
            for k_local, was_rescued in zip(local_k_list, sub_rescued):
                if was_rescued:
                    rescued[k_local] = True
        self.gen_rescues += int(rescued.sum())
        return rescued
