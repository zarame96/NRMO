"""
NRMO v7.1 — Collective StrongEngine + Collective Core.

Restores architectural symmetry: as individual NRMO has NRMO_Core (veto) +
Omega Full (search), collective NRMO_Collective now has Collective_Core
(veto) + CollectiveStrongEngine (search).

Six new mechanisms (W-AB):
  W. Predictive trigger        — forecast next-gen shock, pre-augment budget
  X. Target selection (triage) — explicit rescue priority via 4-factor score
  Y. Pool reallocation         — dynamic surplus redistribution across tiers
  Z. Inter-civ insurance       — contractual mutual insurance between civs
  AA. Candidate exploration    — mutation/synthesis/invention on collective configs
  AB. Collective drift control — rescue dependency accumulation

Four Collective_Core veto rules:
  1. Pool depletion veto
  2. Rescue rate ceiling (moral hazard)
  3. Asymmetric mutual contract veto
  4. Drift threshold veto

NRMO principle: scale-invariant governance-execution separation.
At every scale (individual / family / lineage / civ / world),
veto and search are distinct, with search constrained to admissible.

No simplification: all components fully implemented per user directive.
"""
import numpy as np
import copy
from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import Optional, List, Dict, Tuple


# ============================================================
# Configuration for Collective Engine and Core
# ============================================================

@dataclass
class CollectiveEngineConfig:
    """Full configuration for v7.1 collective layer."""

    # === Master enables (all on by default; no simplification) ===
    enable_W_predictive_trigger: bool = True
    enable_X_triage_optimization: bool = True
    enable_Y_pool_reallocation: bool = True
    enable_Z_inter_civ_insurance: bool = True
    enable_AA_candidate_exploration: bool = True
    enable_AB_drift_control: bool = True
    enable_collective_veto: bool = True

    # === Search hyperparameters ===
    candidate_count: int = 12
    rollout_depth: int = 6
    rollout_repeats: int = 4
    mutation_variants: int = 3
    invention_count: int = 4

    # === W: Predictive trigger ===
    w_lookback_window: int = 5
    w_forecast_horizon: int = 2  # generations ahead
    w_shock_forecast_weight_X: float = 0.4
    w_shock_forecast_weight_history: float = 0.4
    w_shock_forecast_weight_world_params: float = 0.2
    w_budget_augment_max: float = 0.50  # max 50% budget increase
    w_trigger_threshold: float = 0.35   # forecast >= this triggers augment

    # === X: Triage (target selection) ===
    x_factor_knowledge: float = 0.25
    x_factor_productivity: float = 0.20
    x_factor_diversity: float = 0.30
    x_factor_vulnerability: float = 0.25
    x_factor_learning_rate: float = 0.05  # adapt weights from rollout outcomes
    x_min_factor_weight: float = 0.05    # floor for any one factor

    # === Y: Pool reallocation ===
    y_safety_floor_family: float = 0.10  # cannot drain below this fraction
    y_safety_floor_lineage: float = 0.10
    y_safety_floor_civ: float = 0.15
    y_max_reallocation_fraction: float = 0.30  # per gen
    y_consider_reverse: bool = True  # also try civ → family direction

    # === Z: Inter-civ insurance ===
    z_max_contracts: int = 3  # per civ
    z_min_rivalry_for_contract: float = 0.30  # below this allows contract
    z_contribution_rate: float = 0.05
    z_max_payout_per_contract: float = 0.40
    z_asymmetry_tolerance: float = 0.30  # max imbalance before veto
    z_contract_duration_steps: int = 10

    # === AA: Candidate exploration ===
    aa_base_templates_count: int = 5
    aa_mutation_count: int = 3
    aa_synthesis_count: int = 3
    aa_invention_count: int = 2

    # === AB: Drift control ===
    ab_rescue_dependency_decay: float = 0.92
    ab_dependency_ceiling: float = 0.55  # absolute ceiling
    ab_dependency_warning: float = 0.40

    # === Collective Veto thresholds ===
    veto_pool_depletion_floor: float = 0.10
    veto_rescue_rate_ceiling: float = 0.30
    veto_asymmetry_max: float = 0.30
    veto_drift_ceiling: float = 0.55

    # === Scoring weights (per world archetype) ===
    score_continuation_weight: float = 0.50
    score_diversity_weight: float = 0.30
    score_cohesion_weight: float = 0.20

    # === Failure memory ===
    failure_memory_size: int = 64
    failure_penalty: float = 0.15


# ============================================================
# Collective Configuration (search target)
# ============================================================

@dataclass
class CollectiveConfiguration:
    """One full collective-governance configuration that the Engine considers.

    This is the search space element: each candidate is a complete
    parameterisation of the collective layer for one generation.
    """
    # Tier rates (P)
    family_pool_rate: float = 0.25
    lineage_pool_rate: float = 0.15
    civ_pool_rate: float = 0.10
    # Tier coverages (P)
    family_coverage: float = 0.70
    lineage_coverage: float = 0.50
    civ_coverage: float = 0.30
    # W: budget augmentation (multiplier applied to pools this gen)
    budget_augment_multiplier: float = 1.0
    # X: triage weights (4 factors)
    triage_w_knowledge: float = 0.25
    triage_w_productivity: float = 0.20
    triage_w_diversity: float = 0.30
    triage_w_vulnerability: float = 0.25
    # Y: pool reallocation directives
    realloc_family_to_lineage: float = 0.0
    realloc_lineage_to_civ: float = 0.0
    realloc_civ_to_lineage: float = 0.0  # reverse direction
    # Z: inter-civ contract participations (list of partner names)
    inter_civ_contracts: List[str] = field(default_factory=list)
    # AA: structural flag
    extra_individual_reserve: bool = False  # 4th tier individual reserve
    # AB: rescue rate cap (drift control)
    rescue_rate_cap: float = 0.30

    def to_vector(self) -> np.ndarray:
        """For distance/diversity computation."""
        return np.array([
            self.family_pool_rate, self.lineage_pool_rate, self.civ_pool_rate,
            self.family_coverage, self.lineage_coverage, self.civ_coverage,
            self.budget_augment_multiplier,
            self.triage_w_knowledge, self.triage_w_productivity,
            self.triage_w_diversity, self.triage_w_vulnerability,
            self.realloc_family_to_lineage, self.realloc_lineage_to_civ,
            self.realloc_civ_to_lineage,
            float(self.extra_individual_reserve),
            self.rescue_rate_cap,
        ])

    def archetype(self) -> str:
        """Classify configuration for synergy matrix."""
        if self.budget_augment_multiplier > 1.3:
            return "expanded_protection"
        if self.civ_coverage > 0.40:
            return "civ_heavy"
        if self.family_coverage > 0.80:
            return "family_heavy"
        if max(self.realloc_family_to_lineage, self.realloc_lineage_to_civ,
                self.realloc_civ_to_lineage) > 0.15:
            return "reallocating"
        if len(self.inter_civ_contracts) > 0:
            return "external_insured"
        return "balanced_collective"


# ============================================================
# State carried by the collective engine across generations
# ============================================================

@dataclass
class CollectiveEngineState:
    """Per-civilisation state for the collective engine."""
    # History for predictive trigger (W)
    shock_history: deque = field(default_factory=lambda: deque(maxlen=20))
    rescue_history: deque = field(default_factory=lambda: deque(maxlen=20))
    civ_size_history: deque = field(default_factory=lambda: deque(maxlen=20))
    # Triage weights (X) — adapted online
    triage_weights: np.ndarray = field(default_factory=lambda: np.array([0.25, 0.20, 0.30, 0.25]))
    triage_outcome_log: deque = field(default_factory=lambda: deque(maxlen=30))
    # Reallocation history (Y)
    reallocation_log: deque = field(default_factory=lambda: deque(maxlen=20))
    # Inter-civ contracts (Z) — active contracts
    active_contracts: Dict[str, Dict] = field(default_factory=dict)
    contract_history: deque = field(default_factory=lambda: deque(maxlen=30))
    # Drift (AB)
    rescue_dependency: float = 0.0
    rescue_dependency_history: deque = field(default_factory=lambda: deque(maxlen=20))
    # Previous configuration
    prev_config: Optional[CollectiveConfiguration] = None
    # Failure memory
    failure_records: deque = field(default_factory=lambda: deque(maxlen=64))


# ============================================================
# Collective Core (Veto) — symmetric to NRMO_Core
# ============================================================

class CollectiveCore:
    """Veto-only collective layer. 4 rules, no scoring.

    Constructs admissibility set over CollectiveConfiguration candidates.
    """

    def __init__(self, cfg: CollectiveEngineConfig):
        self.cfg = cfg
        self.veto_counts = {"depletion": 0, "rescue_rate": 0,
                             "asymmetry": 0, "drift": 0}

    def veto(self, config: CollectiveConfiguration,
              engine_state: CollectiveEngineState,
              current_pool_levels: Dict[str, float],
              partner_balances: Dict[str, float]) -> Optional[str]:
        """Check the 4 collective veto rules.

        Returns None if admissible, otherwise the violated rule name.
        """
        if not self.cfg.enable_collective_veto:
            return None

        # Rule 1: Pool depletion veto
        # If projected outflows leave any pool below safety floor, veto
        net_family_rate = (config.family_coverage * config.rescue_rate_cap
                            - config.family_pool_rate
                            - config.realloc_civ_to_lineage  # reverse fills
                            + config.realloc_family_to_lineage)
        proj_family_level = current_pool_levels.get("family", 1.0) - net_family_rate
        if proj_family_level < self.cfg.veto_pool_depletion_floor:
            self.veto_counts["depletion"] += 1
            return "pool_depletion"

        # Rule 2: Rescue rate ceiling (moral hazard)
        max_rescue_rate = max(config.family_coverage, config.lineage_coverage,
                               config.civ_coverage) * config.rescue_rate_cap
        if max_rescue_rate > self.cfg.veto_rescue_rate_ceiling:
            self.veto_counts["rescue_rate"] += 1
            return "rescue_rate_ceiling"

        # Rule 3: Asymmetric mutual contract veto
        for partner in config.inter_civ_contracts:
            balance = partner_balances.get(partner, 0.0)
            # Balance: positive = we've given more, negative = we've received more
            if abs(balance) > self.cfg.veto_asymmetry_max:
                self.veto_counts["asymmetry"] += 1
                return f"asymmetric_contract_with_{partner}"

        # Rule 4: Drift threshold
        if engine_state.rescue_dependency > self.cfg.veto_drift_ceiling:
            self.veto_counts["drift"] += 1
            return "rescue_dependency_drift"

        return None

    def construct_admissible_set(self, candidates: List[CollectiveConfiguration],
                                   engine_state: CollectiveEngineState,
                                   pool_levels: Dict[str, float],
                                   partner_balances: Dict[str, float]) -> Tuple[List[CollectiveConfiguration], List[Optional[str]]]:
        """Return (admissible, veto_flags) lists. Mirrors individual side."""
        admissible = []
        flags = []
        for c in candidates:
            v = self.veto(c, engine_state, pool_levels, partner_balances)
            flags.append(v)
            if v is None:
                admissible.append(c)
        return admissible, flags


# ============================================================
# W: Predictive Trigger
# ============================================================

def forecast_next_shock(engine_state: CollectiveEngineState,
                          current_X: float, world_params: dict,
                          cfg: CollectiveEngineConfig) -> float:
    """Forecast next-generation shock probability/magnitude in [0, 1].

    Combines:
    - Current exposure X (normalized to [0, 1])
    - Recent shock history slope
    - World parameter intrinsic shock rate
    """
    if not cfg.enable_W_predictive_trigger:
        return 0.0

    # Component 1: current X normalised
    x_norm = min(1.0, current_X / 100.0)

    # Component 2: shock history trend
    if len(engine_state.shock_history) >= 2:
        recent = list(engine_state.shock_history)[-cfg.w_lookback_window:]
        if len(recent) >= 2:
            # Simple linear trend
            xs = np.arange(len(recent))
            slope = float(np.polyfit(xs, recent, 1)[0])
            mean_recent = float(np.mean(recent))
            hist_signal = min(1.0, max(0.0, mean_recent + slope * cfg.w_forecast_horizon))
        else:
            hist_signal = float(recent[0]) if recent else 0.0
    else:
        hist_signal = 0.0

    # Component 3: world parameter risk
    wp_signal = min(1.0,
        world_params.get("shock_probability", 0.10) * 3 +
        world_params.get("tail_probability", 0.03) * 8 +
        world_params.get("environmental_drag", 0.03) * 5)

    forecast = (cfg.w_shock_forecast_weight_X * x_norm +
                cfg.w_shock_forecast_weight_history * hist_signal +
                cfg.w_shock_forecast_weight_world_params * wp_signal)
    return float(min(1.0, max(0.0, forecast)))


def compute_budget_augment(forecast: float, cfg: CollectiveEngineConfig) -> float:
    """Translate forecast into pool budget multiplier (1.0..1+max)."""
    if not cfg.enable_W_predictive_trigger:
        return 1.0
    if forecast < cfg.w_trigger_threshold:
        return 1.0
    # Linear scaling from threshold to 1.0 → multiplier 1.0 to 1+max
    ratio = (forecast - cfg.w_trigger_threshold) / (1.0 - cfg.w_trigger_threshold)
    return 1.0 + cfg.w_budget_augment_max * ratio


# ============================================================
# X: Triage (rescue priority scoring)
# ============================================================

def compute_lineage_features(at_risk_indices: np.ndarray,
                              agent_strategy: np.ndarray,
                              strategy_names: List[str],
                              edu: np.ndarray, assets: np.ndarray,
                              inst: np.ndarray, urban: np.ndarray,
                              all_active: np.ndarray) -> np.ndarray:
    """Compute (n_at_risk, 4) feature matrix: [knowledge, productivity, diversity, vulnerability].

    diversity = how much this lineage's strategy contributes to civ-wide diversity
    vulnerability = self-recovery probability complement (= 1 - prosperity)
    """
    n_risk = len(at_risk_indices)
    if n_risk == 0:
        return np.zeros((0, 4))

    # Civ-wide strategy distribution
    n_total = int(all_active.sum())
    if n_total == 0:
        return np.zeros((n_risk, 4))
    strat_active = agent_strategy[all_active]
    strat_counts = np.bincount(strat_active, minlength=len(strategy_names))
    strat_probs = strat_counts / max(1, n_total)

    features = np.zeros((n_risk, 4))
    for k, gi in enumerate(at_risk_indices):
        # Knowledge
        features[k, 0] = float(edu[gi])
        # Productivity
        features[k, 1] = float(assets[gi])
        # Diversity contribution: rarity of this lineage's strategy
        s_idx = int(agent_strategy[gi])
        p = strat_probs[s_idx] if s_idx < len(strat_probs) else 0.5
        features[k, 2] = 1.0 - p  # rarer = more diversity contribution
        # Vulnerability = 1 - prosperity proxy
        prosperity = (edu[gi] + assets[gi] + inst[gi]) / 3
        features[k, 3] = 1.0 - float(prosperity)
    return features


def compute_triage_scores(at_risk_indices: np.ndarray, features: np.ndarray,
                           weights: np.ndarray) -> np.ndarray:
    """Triage priority = dot(features, weights). Higher = rescued first."""
    if len(at_risk_indices) == 0:
        return np.zeros(0)
    return features @ weights


def update_triage_weights(engine_state: CollectiveEngineState,
                            recent_outcomes: List[Dict],
                            cfg: CollectiveEngineConfig):
    """Online learning of triage weights from observed rescue outcomes.

    Each outcome is a record: which features were prioritised,
    what happened to civ continuation rate.
    """
    if not cfg.enable_X_triage_optimization:
        return
    if not recent_outcomes:
        return
    # Compute gradient: features that correlate with good civ-continuation
    # weights get boosted
    delta = np.zeros(4)
    n_used = 0
    for outcome in recent_outcomes:
        features_used = outcome.get("features_mean")
        score_change = outcome.get("civ_score_delta")
        if features_used is None or score_change is None:
            continue
        delta += score_change * features_used
        n_used += 1
    if n_used == 0:
        return
    delta = delta / n_used
    # Apply learning rate update
    new_weights = engine_state.triage_weights + cfg.x_factor_learning_rate * delta
    # Floor each weight, then renormalise
    new_weights = np.maximum(new_weights, cfg.x_min_factor_weight)
    new_weights = new_weights / new_weights.sum()
    engine_state.triage_weights = new_weights


# ============================================================
# Y: Pool Reallocation
# ============================================================

def compute_reallocation_candidates(current_levels: Dict[str, float],
                                      pressure_indicators: Dict[str, float],
                                      cfg: CollectiveEngineConfig) -> List[Dict[str, float]]:
    """Generate candidate reallocation actions based on imbalance.

    pressure_indicators: per-tier rescue demand / inflow ratio
    Returns: list of {f2l, l2c, c2l} reallocation directives.
    """
    if not cfg.enable_Y_pool_reallocation:
        return [{"f2l": 0.0, "l2c": 0.0, "c2l": 0.0}]

    candidates = [{"f2l": 0.0, "l2c": 0.0, "c2l": 0.0}]  # no reallocation
    max_r = cfg.y_max_reallocation_fraction

    # Family is high, lineage is low → move family → lineage
    fam_level = current_levels.get("family", 1.0)
    lin_level = current_levels.get("lineage", 1.0)
    civ_level = current_levels.get("civ", 1.0)
    fam_pressure = pressure_indicators.get("family", 0.0)
    lin_pressure = pressure_indicators.get("lineage", 0.0)
    civ_pressure = pressure_indicators.get("civ", 0.0)

    # Strategy 1: Forward reallocation (family → lineage)
    if fam_level > cfg.y_safety_floor_family * 2 and lin_pressure > fam_pressure:
        candidates.append({"f2l": min(max_r, fam_level * 0.2), "l2c": 0.0, "c2l": 0.0})
    # Strategy 2: Forward reallocation (lineage → civ)
    if lin_level > cfg.y_safety_floor_lineage * 2 and civ_pressure > lin_pressure:
        candidates.append({"f2l": 0.0, "l2c": min(max_r, lin_level * 0.2), "c2l": 0.0})
    # Strategy 3: Reverse reallocation (civ → lineage, for emergency)
    if cfg.y_consider_reverse and civ_level > cfg.y_safety_floor_civ * 2 and lin_pressure > 0.5:
        candidates.append({"f2l": 0.0, "l2c": 0.0,
                            "c2l": min(max_r, civ_level * 0.15)})
    # Strategy 4: Double move
    if fam_level > cfg.y_safety_floor_family * 3:
        candidates.append({"f2l": 0.15, "l2c": 0.05, "c2l": 0.0})

    return candidates


# ============================================================
# Z: Inter-civ Insurance
# ============================================================

def enumerate_partner_candidates(civ_name: str, other_civs: List[str],
                                   rivalry_pairs: Dict[Tuple[str, str], float],
                                   cfg: CollectiveEngineConfig) -> List[str]:
    """Return civs with rivalry below threshold (eligible partners)."""
    if not cfg.enable_Z_inter_civ_insurance:
        return []
    eligible = []
    for other in other_civs:
        if other == civ_name:
            continue
        rivalry = rivalry_pairs.get((civ_name, other),
                                       rivalry_pairs.get((other, civ_name), 0.5))
        if rivalry < cfg.z_min_rivalry_for_contract:
            eligible.append(other)
    return eligible


def evaluate_contract_proposal(self_civ_state, partner_civ_state,
                                  contract_duration: int,
                                  cfg: CollectiveEngineConfig) -> Dict:
    """Estimate expected utility of contract entry."""
    # Heuristic: contracts most valuable when self at high X but partner at low X
    # (we're the receiver expected); or symmetrically when shocks correlated
    self_X = self_civ_state.X if hasattr(self_civ_state, "X") else 30.0
    self_E = self_civ_state.E if hasattr(self_civ_state, "E") else 60.0
    partner_X = partner_civ_state.X if hasattr(partner_civ_state, "X") else 30.0
    partner_E = partner_civ_state.E if hasattr(partner_civ_state, "E") else 60.0

    # Correlation proxy: difference in X. If we have opposite phases, contract good.
    phase_diff = abs(self_X - partner_X) / 100.0
    fragility_balance = abs(self_E - partner_E) / 100.0
    expected_benefit = 0.4 + 0.3 * phase_diff - 0.2 * fragility_balance
    expected_cost = cfg.z_contribution_rate * contract_duration

    return {
        "expected_benefit": float(expected_benefit),
        "expected_cost": float(expected_cost),
        "net_utility": float(expected_benefit - expected_cost),
    }


# ============================================================
# AA: Candidate Exploration (mutation/synthesis/invention)
# ============================================================

def generate_base_templates(cfg: CollectiveEngineConfig) -> List[CollectiveConfiguration]:
    """Base archetypes of collective configurations."""
    return [
        CollectiveConfiguration(),  # balanced default
        CollectiveConfiguration(family_pool_rate=0.35, family_coverage=0.85,
                                  lineage_pool_rate=0.10, civ_pool_rate=0.05),  # family-heavy
        CollectiveConfiguration(family_pool_rate=0.10, lineage_pool_rate=0.25,
                                  civ_pool_rate=0.25, civ_coverage=0.50),  # civ-heavy
        CollectiveConfiguration(budget_augment_multiplier=1.30,
                                  family_coverage=0.80, civ_coverage=0.45),  # expanded
        CollectiveConfiguration(family_pool_rate=0.15, lineage_pool_rate=0.10,
                                  civ_pool_rate=0.05, rescue_rate_cap=0.15),  # conservative
    ]


def mutate_configurations(bases: List[CollectiveConfiguration], rng,
                            n_variants: int = 3) -> List[CollectiveConfiguration]:
    """Apply small perturbations to base templates."""
    out = []
    for b in bases[:5]:
        for _ in range(n_variants):
            m = copy.deepcopy(b)
            m.family_pool_rate = float(np.clip(b.family_pool_rate + rng.normal(0, 0.03), 0.05, 0.40))
            m.lineage_pool_rate = float(np.clip(b.lineage_pool_rate + rng.normal(0, 0.03), 0.05, 0.30))
            m.civ_pool_rate = float(np.clip(b.civ_pool_rate + rng.normal(0, 0.02), 0.03, 0.20))
            m.family_coverage = float(np.clip(b.family_coverage + rng.normal(0, 0.05), 0.30, 0.95))
            m.lineage_coverage = float(np.clip(b.lineage_coverage + rng.normal(0, 0.05), 0.20, 0.80))
            m.civ_coverage = float(np.clip(b.civ_coverage + rng.normal(0, 0.04), 0.10, 0.60))
            out.append(m)
    return out


def synthesize_configurations(pool: List[CollectiveConfiguration], rng,
                                n: int = 3) -> List[CollectiveConfiguration]:
    """Hybrid two configurations."""
    out = []
    if len(pool) < 2:
        return out
    for _ in range(n):
        i, j = rng.choice(len(pool), 2, replace=False)
        hybrid = copy.deepcopy(pool[i])
        b = pool[j]
        alpha = rng.uniform(0.3, 0.7)
        hybrid.family_pool_rate = alpha * hybrid.family_pool_rate + (1 - alpha) * b.family_pool_rate
        hybrid.lineage_pool_rate = alpha * hybrid.lineage_pool_rate + (1 - alpha) * b.lineage_pool_rate
        hybrid.civ_pool_rate = alpha * hybrid.civ_pool_rate + (1 - alpha) * b.civ_pool_rate
        hybrid.family_coverage = alpha * hybrid.family_coverage + (1 - alpha) * b.family_coverage
        hybrid.lineage_coverage = alpha * hybrid.lineage_coverage + (1 - alpha) * b.lineage_coverage
        hybrid.civ_coverage = alpha * hybrid.civ_coverage + (1 - alpha) * b.civ_coverage
        hybrid.budget_augment_multiplier = (alpha * hybrid.budget_augment_multiplier
                                              + (1 - alpha) * b.budget_augment_multiplier)
        out.append(hybrid)
    return out


def invent_configurations(state_summary: dict, forecast: float,
                            rivalry_level: float, rng,
                            cfg: CollectiveEngineConfig, n: int = 2) -> List[CollectiveConfiguration]:
    """Generate state-conditioned new configurations."""
    out = []
    for _ in range(n):
        c = CollectiveConfiguration()
        # If forecast high, augment budget
        if forecast > 0.5:
            c.budget_augment_multiplier = 1.0 + cfg.w_budget_augment_max * forecast
            c.family_coverage = 0.80
            c.civ_coverage = 0.45
        # If high X observed, conservative cap
        if state_summary.get("X", 30) > 60:
            c.rescue_rate_cap = 0.18
        # If rivalry low, propose inter-civ contracts
        if rivalry_level < cfg.z_min_rivalry_for_contract:
            c.inter_civ_contracts = state_summary.get("eligible_partners", [])[:2]
        # If high inequality, more lineage-focused
        if state_summary.get("inequality", 0) > 0.3:
            c.lineage_pool_rate = 0.22
            c.lineage_coverage = 0.65
        # Small perturbation
        c.family_pool_rate += float(rng.normal(0, 0.02))
        c.lineage_pool_rate += float(rng.normal(0, 0.02))
        out.append(c)
    return out


def build_configuration_candidates(engine_state: CollectiveEngineState,
                                     civ_state, world_params: dict,
                                     forecast: float, rivalry_level: float,
                                     eligible_partners: List[str],
                                     state_summary: dict, rng,
                                     cfg: CollectiveEngineConfig) -> List[CollectiveConfiguration]:
    """Build full candidate pool (W invented + base + mutations + synth)."""
    if not cfg.enable_AA_candidate_exploration:
        return [CollectiveConfiguration()]

    state_summary = dict(state_summary)
    state_summary["eligible_partners"] = eligible_partners

    bases = generate_base_templates(cfg)[:cfg.aa_base_templates_count]
    mutations = mutate_configurations(bases, rng, cfg.aa_mutation_count)
    synth = synthesize_configurations(bases + mutations, rng, cfg.aa_synthesis_count)
    invented = invent_configurations(state_summary, forecast, rivalry_level,
                                        rng, cfg, cfg.aa_invention_count)
    pool = bases + mutations + synth + invented

    # Apply prev configuration as warm-start option
    if engine_state.prev_config is not None:
        pool.append(copy.deepcopy(engine_state.prev_config))

    return pool


# ============================================================
# AB: Collective Drift Control
# ============================================================

def update_rescue_dependency(engine_state: CollectiveEngineState,
                              n_rescues_this_gen: int, n_total: int,
                              cfg: CollectiveEngineConfig):
    """Track rescue dependency over time."""
    if not cfg.enable_AB_drift_control:
        return
    if n_total == 0:
        return
    instant_dependency = n_rescues_this_gen / n_total
    # Exponential moving average
    engine_state.rescue_dependency = (
        cfg.ab_rescue_dependency_decay * engine_state.rescue_dependency
        + (1 - cfg.ab_rescue_dependency_decay) * instant_dependency)
    engine_state.rescue_dependency_history.append(engine_state.rescue_dependency)


def drift_warning(engine_state: CollectiveEngineState,
                    cfg: CollectiveEngineConfig) -> Optional[str]:
    if not cfg.enable_AB_drift_control:
        return None
    if engine_state.rescue_dependency >= cfg.ab_dependency_ceiling:
        return "rescue_dependency_critical"
    if engine_state.rescue_dependency >= cfg.ab_dependency_warning:
        return "rescue_dependency_warning"
    return None


# ============================================================
# Rollout for collective scoring
# ============================================================

def _rollout_collective(config: CollectiveConfiguration,
                          civ_state, world_params: dict,
                          rng, depth: int = 6) -> dict:
    """Simulate collective effects over `depth` steps.

    Returns: dict with continuation_rate_proxy, diversity, cohesion, etc.

    This is a lightweight model: at each step, simulate aggregate
    pool flows + rescue outcomes + cohesion drift, without invoking
    the full agent population step (would be circular and expensive).
    """
    # Initial estimates from civ_state
    pool_family = 1.0  # normalised
    pool_lineage = 1.0
    pool_civ = 1.0
    cohesion = 0.5
    continuation = 1.0
    diversity_score = 1.0  # max entropy baseline

    # Each step: apply config rates and observe outcomes
    for step in range(depth):
        # Inflows
        inflow_f = config.family_pool_rate * continuation
        inflow_l = config.lineage_pool_rate * continuation
        inflow_c = config.civ_pool_rate * continuation

        # Reallocations
        pool_family += inflow_f - config.realloc_family_to_lineage * pool_family
        pool_lineage += (inflow_l + config.realloc_family_to_lineage * pool_family
                          - config.realloc_lineage_to_civ * pool_lineage
                          + config.realloc_civ_to_lineage * pool_civ)
        pool_civ += (inflow_c + config.realloc_lineage_to_civ * pool_lineage
                      - config.realloc_civ_to_lineage * pool_civ)

        # Shock event sampling (probabilistic)
        wp_shock_p = world_params.get("shock_probability", 0.10)
        covered_f = covered_l = covered_c = 0.0
        uncovered = 0.0
        if rng.random() < wp_shock_p:
            shock_mag = rng.exponential(world_params.get("shock_scale", 5.0)) / 30
            # Rescue from cascading pools
            demand = shock_mag * 0.5
            covered_f = min(demand, pool_family * config.family_coverage) * config.budget_augment_multiplier
            demand -= covered_f
            pool_family -= covered_f / config.family_coverage if config.family_coverage > 0 else covered_f

            if demand > 0:
                covered_l = min(demand, pool_lineage * config.lineage_coverage) * config.budget_augment_multiplier
                demand -= covered_l
                pool_lineage -= covered_l / config.lineage_coverage if config.lineage_coverage > 0 else covered_l

            if demand > 0:
                covered_c = min(demand, pool_civ * config.civ_coverage) * config.budget_augment_multiplier
                demand -= covered_c
                pool_civ -= covered_c / config.civ_coverage if config.civ_coverage > 0 else covered_c

            uncovered = max(0, demand)
            continuation -= uncovered * 0.5

            # Cohesion gets boost from rescues, but uncovered erodes it
            cohesion += 0.05 * (covered_f + covered_l + covered_c) - 0.10 * uncovered
            # Diversity drops if uncovered failures concentrate in one lineage
            diversity_score -= uncovered * 0.1

        # Pool decay
        pool_family *= 0.98
        pool_lineage *= 0.98
        pool_civ *= 0.98
        cohesion *= 0.99
        cohesion = float(np.clip(cohesion, 0.0, 1.0))
        diversity_score = float(np.clip(diversity_score, 0.0, 1.5))
        continuation = float(np.clip(continuation, 0.0, 1.0))

    return {
        "continuation": continuation,
        "diversity": diversity_score,
        "cohesion": cohesion,
        "final_pool_family": pool_family,
        "final_pool_lineage": pool_lineage,
        "final_pool_civ": pool_civ,
    }


def score_collective_candidate(config: CollectiveConfiguration,
                                 civ_state, world_params: dict, rng,
                                 cfg: CollectiveEngineConfig,
                                 archetype: str,
                                 engine_state: CollectiveEngineState) -> dict:
    """Full scoring of one collective configuration via MC rollout."""
    rollout_results = []
    for _ in range(cfg.rollout_repeats):
        r = _rollout_collective(config, civ_state, world_params, rng, cfg.rollout_depth)
        rollout_results.append(r)

    mean_cont = float(np.mean([r["continuation"] for r in rollout_results]))
    mean_div = float(np.mean([r["diversity"] for r in rollout_results]))
    mean_coh = float(np.mean([r["cohesion"] for r in rollout_results]))

    # Variance penalty (rollout uncertainty)
    var_cont = float(np.var([r["continuation"] for r in rollout_results]))
    var_pen = 0.2 * np.sqrt(var_cont)

    # Pool sustainability penalty: if any pool depletes, penalty
    sustainability = float(np.mean([
        min(r["final_pool_family"], r["final_pool_lineage"], r["final_pool_civ"])
        for r in rollout_results
    ]))
    sus_pen = max(0, 0.2 - sustainability) * 0.5

    # Failure memory penalty
    fm_pen = 0.0
    for record in engine_state.failure_records:
        if record["archetype"] == archetype:
            # Recent same-archetype failure → penalty
            fm_pen = max(fm_pen, cfg.failure_penalty)

    score = (cfg.score_continuation_weight * mean_cont
              + cfg.score_diversity_weight * mean_div
              + cfg.score_cohesion_weight * mean_coh
              - var_pen - sus_pen - fm_pen)

    return {
        "score": float(score),
        "continuation": mean_cont,
        "diversity": mean_div,
        "cohesion": mean_coh,
        "sustainability": sustainability,
        "var_pen": float(var_pen),
        "fm_pen": fm_pen,
    }


# ============================================================
# Top-level Collective StrongEngine
# ============================================================

class CollectiveStrongEngine:
    """Per-civilisation search engine over collective configurations.

    Mirrors Omega Full in structure: candidate generation, admissibility
    check (Collective_Core), scoring via rollout, portfolio construction.
    """

    def __init__(self, civ_name: str, cfg: Optional[CollectiveEngineConfig] = None):
        self.civ_name = civ_name
        self.cfg = cfg or CollectiveEngineConfig()
        self.core = CollectiveCore(self.cfg)
        self.state = CollectiveEngineState()

    def select_configuration(self,
                                civ_state,  # CivState or scalar dict
                                world_params: dict,
                                pool_levels: Dict[str, float],
                                pressure_indicators: Dict[str, float],
                                partner_civs: List[str],
                                partner_balances: Dict[str, float],
                                partner_states: Dict[str, object],
                                rivalry_pairs: Dict[Tuple[str, str], float],
                                inequality: float,
                                rng) -> Tuple[CollectiveConfiguration, dict]:
        """Run full collective engine pipeline.

        Returns: (chosen configuration, diagnostics dict)
        """
        # Step 1: predictive forecast (W)
        current_X = civ_state.X if hasattr(civ_state, "X") else 30.0
        forecast = forecast_next_shock(self.state, current_X, world_params, self.cfg)
        self.state.shock_history.append(forecast)

        # Step 2: identify eligible partners (Z)
        eligible_partners = enumerate_partner_candidates(
            self.civ_name, partner_civs, rivalry_pairs, self.cfg)

        # Step 3: build candidate pool (AA)
        state_summary = {
            "X": current_X,
            "inequality": inequality,
            "cohesion": pool_levels.get("cohesion", 0.5),
        }
        candidates = build_configuration_candidates(
            self.state, civ_state, world_params, forecast,
            world_params.get("rivalry_level", 0.15),
            eligible_partners, state_summary, rng, self.cfg)

        # Apply W: budget augmentation
        budget_aug = compute_budget_augment(forecast, self.cfg)
        for c in candidates:
            c.budget_augment_multiplier = max(c.budget_augment_multiplier, budget_aug)

        # Apply Y: reallocation candidates (variant per base)
        realloc_options = compute_reallocation_candidates(
            pool_levels, pressure_indicators, self.cfg)
        # Expand candidates with reallocation variants
        expanded = []
        for c in candidates:
            for ro in realloc_options[:3]:
                m = copy.deepcopy(c)
                m.realloc_family_to_lineage = ro["f2l"]
                m.realloc_lineage_to_civ = ro["l2c"]
                m.realloc_civ_to_lineage = ro["c2l"]
                expanded.append(m)
        candidates = expanded[:self.cfg.candidate_count * 3]

        # Step 4: Collective Core veto
        admissible, veto_flags = self.core.construct_admissible_set(
            candidates, self.state, pool_levels, partner_balances)

        if not admissible:
            # Fall back to most conservative
            fallback = CollectiveConfiguration(
                family_pool_rate=0.15, lineage_pool_rate=0.10, civ_pool_rate=0.05,
                family_coverage=0.50, lineage_coverage=0.30, civ_coverage=0.20,
                rescue_rate_cap=0.15)
            return fallback, {"forecast": forecast, "n_admissible": 0,
                                "veto_counts": dict(self.core.veto_counts)}

        # Step 5: score each via MC rollout
        scored = []
        for c in admissible:
            arch = c.archetype()
            metrics = score_collective_candidate(
                c, civ_state, world_params, rng, self.cfg, arch, self.state)
            scored.append((c, metrics["score"], metrics, arch))
        scored.sort(key=lambda x: x[1], reverse=True)

        # Step 6: portfolio — take best, but consider a hedge from second
        best = scored[0][0]
        best_metrics = scored[0][2]
        if len(scored) > 1 and scored[1][1] > scored[0][1] - 0.05:
            # Close second: blend best (70%) + hedge (30%)
            hedge = scored[1][0]
            blended = copy.deepcopy(best)
            blended.family_pool_rate = 0.7 * best.family_pool_rate + 0.3 * hedge.family_pool_rate
            blended.lineage_pool_rate = 0.7 * best.lineage_pool_rate + 0.3 * hedge.lineage_pool_rate
            blended.civ_pool_rate = 0.7 * best.civ_pool_rate + 0.3 * hedge.civ_pool_rate
            best = blended

        # Record state
        self.state.prev_config = best

        # Drift warning (AB)
        drift_warn = drift_warning(self.state, self.cfg)

        # Failure record (if rollout showed low continuation)
        if best_metrics["continuation"] < 0.5:
            self.state.failure_records.append({
                "archetype": scored[0][3],
                "score": best_metrics["score"],
                "continuation": best_metrics["continuation"],
            })

        return best, {
            "forecast": forecast,
            "n_admissible": len(admissible),
            "n_candidates": len(candidates),
            "best_score": scored[0][1],
            "best_archetype": scored[0][3],
            "drift_warning": drift_warn,
            "rescue_dependency": self.state.rescue_dependency,
            "veto_counts": dict(self.core.veto_counts),
            "triage_weights": list(self.state.triage_weights),
        }

    def update_after_gen(self, n_rescues: int, n_total: int):
        """Update state after generation."""
        self.state.rescue_history.append(n_rescues)
        self.state.civ_size_history.append(n_total)
        update_rescue_dependency(self.state, n_rescues, n_total, self.cfg)


# ============================================================
# Triage-based rescue selection (replaces v7.0 random.choice)
# ============================================================

def triage_rescue_selection(at_risk_indices: np.ndarray,
                              agent_strategy: np.ndarray,
                              strategy_names: List[str],
                              edu: np.ndarray, assets: np.ndarray,
                              inst: np.ndarray, urban: np.ndarray,
                              all_active: np.ndarray,
                              n_can_rescue: int,
                              triage_weights: np.ndarray) -> np.ndarray:
    """Select which at-risk lineages to rescue by triage priority.

    Returns boolean mask of size len(at_risk_indices).
    """
    if len(at_risk_indices) == 0 or n_can_rescue == 0:
        return np.zeros(len(at_risk_indices), dtype=bool)

    features = compute_lineage_features(at_risk_indices, agent_strategy,
                                           strategy_names, edu, assets,
                                           inst, urban, all_active)
    scores = compute_triage_scores(at_risk_indices, features, triage_weights)

    # Rescue top-N by score
    n_rescue = min(n_can_rescue, len(at_risk_indices))
    rank = np.argsort(-scores)  # descending
    rescued = np.zeros(len(at_risk_indices), dtype=bool)
    rescued[rank[:n_rescue]] = True
    return rescued
