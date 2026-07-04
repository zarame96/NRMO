"""
Stage 4 (v7.0) Features — Memetic dynamics, Black Swan, Counterfactual mode.

These extend the v6.1 unified simulator to:
1. Memetic dynamics: strategy distributions evolve over generations based on
   relative success (replicator dynamics)
2. Black Swan events: ultra-rare (~10⁻⁴/year) catastrophic events with
   massive shock magnitudes
3. Counterfactual mode: override specific historical decision points to
   compare "what if" trajectories

This is a partial Stage 4 — full Stage 4 also requires GPU acceleration to
reach 10⁸ agents, which is blocked by the current environment.
"""
import numpy as np


# ============================================================
# 1. MEMETIC DYNAMICS — Strategy distribution evolution
# ============================================================

def compute_strategy_fitness(agent_strategy, absorbed, edu, assets, n_strategies):
    """Compute per-strategy fitness based on survival × prosperity.

    Returns array of shape (n_strategies,) with normalized fitness scores.
    """
    fitness = np.zeros(n_strategies)
    counts = np.zeros(n_strategies)
    for s in range(n_strategies):
        mask = agent_strategy == s
        if not mask.any():
            continue
        n_total = int(mask.sum())
        n_alive = int((mask & ~absorbed).sum())
        if n_total == 0:
            continue
        survival = n_alive / n_total
        # Mean education + assets among alive
        if n_alive > 0:
            alive_mask = mask & ~absorbed
            mean_prosperity = (edu[alive_mask].mean() + assets[alive_mask].mean()) / 2
        else:
            mean_prosperity = 0
        # Fitness = survival × prosperity (multiplicative)
        fitness[s] = survival * (0.5 + mean_prosperity)
        counts[s] = n_total

    # Normalize to sum to 1
    if fitness.sum() > 0:
        fitness = fitness / fitness.sum()
    else:
        fitness = np.ones(n_strategies) / n_strategies
    return fitness, counts


def evolve_strategy_distribution(agent_strategy, absorbed, edu, assets,
                                    n_strategies, drift_rate=0.05,
                                    rng=None):
    """Apply memetic replication: strategies that did well get more agents.

    Uses replicator dynamics: new_share[s] = old_share[s] * fitness[s] / mean_fitness
    Then a fraction `drift_rate` of newly-absorbed lineages adopt the new
    distribution (for new collateral_reset agents).

    Returns: new strategy distribution (probabilities for resampling).
    """
    fitness, counts = compute_strategy_fitness(
        agent_strategy, absorbed, edu, assets, n_strategies)

    # Old share
    old_share = counts / max(counts.sum(), 1)

    # Replicator step: new_share ∝ old_share × fitness
    new_share = old_share * (1 + fitness)
    new_share = new_share / new_share.sum()

    # Smooth drift toward new
    final_dist = (1 - drift_rate) * old_share + drift_rate * new_share
    final_dist = final_dist / final_dist.sum()
    return final_dist, fitness


def apply_memetic_drift(agent_strategy, collateral_reset_indices,
                         new_dist, rng):
    """Reassign strategies of newly-reset (collateral_reset) lineages
    according to new_dist. This represents memetic adoption."""
    if len(collateral_reset_indices) == 0:
        return agent_strategy
    n_strategies = len(new_dist)
    new_assigns = rng.choice(n_strategies, size=len(collateral_reset_indices),
                              p=new_dist)
    agent_strategy[collateral_reset_indices] = new_assigns
    return agent_strategy


# ============================================================
# 2. BLACK SWAN EVENTS — Ultra-rare catastrophic events
# ============================================================

BLACK_SWAN_CATALOG = [
    # (label, year_start, year_end, p_per_year, shock_magnitude, mortality_p, scope)
    ("Volcanic_Winter_Year",    0, 3000, 1e-4, 0.50, 0.10, "global"),
    # 1815 Tambora-class: -3°C global, crops fail; 0.01% chance per year
    ("Megaplague_Pandemic",     0, 3000, 8e-5, 0.40, 0.20, "regional"),
    # Black Death+: 30%+ mortality; ~50% the rate of Justinian/Black Death/H1N1
    ("Great_Solar_Flare_Carrington", 1850, 3000, 5e-5, 0.30, 0.05, "global"),
    # Carrington-class CME hitting modern grid; 0.005% per year post-electric
    ("Asteroid_Regional_Impact", 0, 3000, 2e-5, 0.70, 0.30, "regional"),
    # Tunguska-class hitting populated area
    ("Multi_Empire_Collapse",   0, 2021, 3e-5, 0.55, 0.15, "civ_pair"),
    # Bronze Age collapse / Roman+Han simultaneous fall
    ("Climate_Tipping_Cascade", 2050, 3000, 8e-5, 0.45, 0.10, "global"),
    # AMOC + Amazon dieback + permafrost release
    ("AI_Misalignment_Crisis",  2050, 3000, 4e-5, 0.60, 0.05, "global"),
    # AGI safety failure scenario
    ("Antibiotic_Apocalypse",   2030, 3000, 5e-5, 0.35, 0.18, "global"),
    # Pan-resistant pathogens emerge
    ("Posthuman_Schism",        2500, 3000, 1.5e-4, 0.50, 0.05, "global"),
    # Enhanced/baseline humans diverge violently
]


def sample_black_swan_events(rng, year_start, year_end, intensity_multiplier=1.0):
    """Sample which Black Swan events fire across the simulation horizon."""
    events = []
    for label, ys, ye, p_per_year, shock_mag, mortality, scope in BLACK_SWAN_CATALOG:
        eff_start = max(ys, year_start)
        eff_end = min(ye, year_end)
        if eff_end <= eff_start:
            continue
        years = eff_end - eff_start
        # Probability of at least one occurrence in window
        p_at_least_one = 1 - (1 - p_per_year * intensity_multiplier) ** years
        if rng.random() < p_at_least_one:
            yr = int(rng.uniform(eff_start, eff_end))
            events.append({
                "label": label,
                "year": yr,
                "shock_magnitude": shock_mag,
                "mortality_p": mortality,
                "scope": scope,
                "type": "black_swan",
            })
    return sorted(events, key=lambda e: e["year"])


def apply_black_swan_to_civ(event, civ_state_shock, rng):
    """Apply a Black Swan event to a single civilization's shock state."""
    return civ_state_shock + event["shock_magnitude"], event["mortality_p"]


# ============================================================
# 3. COUNTERFACTUAL MODE — Override decision points
# ============================================================

class CounterfactualOverrides:
    """Container for counterfactual interventions.

    Each override specifies a year and a transformation to apply at that year.
    Examples:
    - Suppress Black Death (1347-1353)
    - Prevent Conquest (1521-1700, IndigenousAmericas survives)
    - No WWI
    - No Cook contact (Polynesia stays isolated)
    """

    def __init__(self):
        self.overrides = []

    def add_event_suppression(self, label, year_range):
        """Suppress all events with given label in year range."""
        self.overrides.append({
            "type": "suppress_event",
            "label": label,
            "year_range": year_range,
        })

    def add_civ_protection(self, civ_name, year_range, shock_reduction=1.0):
        """Reduce all incoming shocks to a civilization in year range.

        shock_reduction=1.0 = full elimination, 0.5 = halve."""
        self.overrides.append({
            "type": "civ_protection",
            "civ": civ_name,
            "year_range": year_range,
            "shock_reduction": shock_reduction,
        })

    def add_civ_extinction(self, civ_name, year):
        """Force a civilization to go extinct at a year."""
        self.overrides.append({
            "type": "civ_extinction",
            "civ": civ_name,
            "year": year,
        })

    def add_interaction_suppression(self, civ_pair, year_range):
        """Prevent inter-civ interactions in year range."""
        self.overrides.append({
            "type": "suppress_interaction",
            "pair": civ_pair,
            "year_range": year_range,
        })

    def filter_events(self, events, year):
        """Filter events through suppression rules at a given year."""
        suppressed_labels = set()
        for ov in self.overrides:
            if ov["type"] == "suppress_event":
                ys, ye = ov["year_range"]
                if ys <= year < ye:
                    suppressed_labels.add(ov["label"])
        return [e for e in events if e.get("label") not in suppressed_labels]

    def filter_interactions(self, interactions, year):
        """Filter interactions through suppression rules."""
        result = []
        for it in interactions:
            suppressed = False
            for ov in self.overrides:
                if ov["type"] != "suppress_interaction":
                    continue
                ys, ye = ov["year_range"]
                if not (ys <= year < ye):
                    continue
                pair_a, pair_b = ov["pair"]
                if (it["pair"][0] == pair_a and it["pair"][1] == pair_b) or \
                   (it["pair"][0] == pair_b and it["pair"][1] == pair_a):
                    suppressed = True
                    break
            if not suppressed:
                result.append(it)
        return result

    def civ_shock_modifier(self, civ_name, year):
        """Get shock multiplier for a civilization at a year (1.0 = no change)."""
        mod = 1.0
        for ov in self.overrides:
            if ov["type"] != "civ_protection":
                continue
            if ov["civ"] != civ_name:
                continue
            ys, ye = ov["year_range"]
            if ys <= year < ye:
                mod *= (1.0 - ov["shock_reduction"])
        return mod

    def force_extinction(self, civ_name, year):
        """Check if a civ should be forced extinct at a given year."""
        for ov in self.overrides:
            if ov["type"] != "civ_extinction":
                continue
            if ov["civ"] != civ_name:
                continue
            if ov["year"] <= year:
                return True
        return False


# Pre-built counterfactual scenarios
COUNTERFACTUAL_SCENARIOS = {
    "no_black_death": {
        "description": "Suppress Black Death pandemic 1347-1353",
        "build": lambda cf: cf.add_event_suppression("Megaplague_Pandemic", (1300, 1400)),
    },
    "no_conquest": {
        "description": "IndigenousAmericas not conquered (1492 contact peaceful)",
        "build": lambda cf: (
            cf.add_civ_protection("IndigenousAmericas", (1492, 1700), 0.95),
            cf.add_interaction_suppression(("Europe", "IndigenousAmericas"), (1492, 1700)),
        ),
    },
    "no_cook": {
        "description": "Polynesia stays isolated (no European contact)",
        "build": lambda cf: cf.add_interaction_suppression(
            ("Europe", "Polynesian"), (1769, 2021)),
    },
    "no_mongol": {
        "description": "No Mongol Empire (1200-1400 conquests prevented)",
        "build": lambda cf: cf.add_interaction_suppression(
            ("China", "Steppe"), (1200, 1400)),
    },
    "no_industrial": {
        "description": "Industrial Revolution suppressed (Europe stays agrarian)",
        "build": lambda cf: cf.add_civ_protection(
            "Europe", (1700, 2021), 0.0),  # No protection but signal
    },
    "early_islam": {
        "description": "Islamic civilization rises 200 years earlier",
        "build": lambda cf: cf.add_event_suppression("Roman_Era", (400, 622)),
    },
}


def build_counterfactual(scenario_names):
    """Build a CounterfactualOverrides from named scenarios."""
    cf = CounterfactualOverrides()
    for name in scenario_names:
        if name not in COUNTERFACTUAL_SCENARIOS:
            print(f"Warning: unknown scenario '{name}'")
            continue
        builder = COUNTERFACTUAL_SCENARIOS[name]["build"]
        builder(cf)
    return cf


def render_counterfactual_summary(cf, scenario_names):
    """Render description of active counterfactuals."""
    if not scenario_names:
        return ""
    lines = ["## Counterfactual Mode Active", ""]
    for name in scenario_names:
        if name in COUNTERFACTUAL_SCENARIOS:
            lines.append(f"- **{name}**: {COUNTERFACTUAL_SCENARIOS[name]['description']}")
    lines.append(f"")
    lines.append(f"Total overrides: {len(cf.overrides)}")
    lines.append("")
    return "\n".join(lines)
