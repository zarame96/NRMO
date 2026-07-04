"""
Ahistorical Event Catalog for World Simulation v5.1.

These events are deliberately "ahistorical" — they did not occur in our
recorded history but are physically/biologically plausible (or
imaginatively useful) and can be triggered in alternative-world
simulations.

Each event has:
- label: identifier
- year_start, year_end: window of possible occurrence
- base_prob_per_year: probability per year (independent)
- magnitude: shock magnitude (0-1 scale)
- dim: impact dimension (determines which mechanism applies)
- description: human-readable

Frequency mode multiplies base_prob_per_year:
- sporadic: 1.0
- frequent: 3.0
- sparse: 0.3
"""

AHISTORICAL_EVENTS = [
    # (label, year_start, year_end, base_prob_per_year, magnitude, dim, description)

    # === COSMIC / GLOBAL ===
    ("Asteroid_Strike",
     0, 2021, 0.00005, 0.40, "global_extinction",
     "Regional-to-global asteroid impact; 40-80% population loss, 15-year impact winter"),

    ("Solar_Flare_Carrington_Plus",
     1850, 2021, 0.00080, 0.25, "tech_collapse",
     "Massive solar flare frying electronic civilization; agrarian societies survive"),

    ("Geomagnetic_Reversal",
     0, 2021, 0.00000300, 0.30, "global_disruption",
     "Pole reversal disrupting navigation, electronics, biological migration; mass mortality"),

    ("Atmospheric_Composition_Shift",
     0, 2021, 0.00010, 0.25, "biological_break",
     "Sudden shift in atmospheric oxygen/CO2; respiratory crisis, agricultural collapse"),

    # === BIOLOGICAL / MEDICAL ===
    ("Mutation_Plague_Novel",
     0, 2021, 0.00015, 0.35, "epidemic_unprecedented",
     "Unprecedented pathogen with 30-50% case fatality and high transmissibility"),

    ("Sense_Awakening",
     0, 2021, 0.00005, 0.15, "biological_break",
     "Sudden emergence of new sensory organ (magnetic, electric); social restructuring"),

    ("Animal_Uprising_Coordinated",
     0, 2021, 0.00008, 0.15, "biological_break",
     "Coordinated animal behavior disrupting agriculture and transport"),

    # === PSYCHOLOGICAL / SOCIAL ===
    ("Mass_Insanity_Wave",
     0, 2021, 0.00010, 0.20, "psychological",
     "Inexplicable wave of collective psychosis; neither religion nor science explains"),

    ("Universal_Telepathy_Brief",
     0, 2021, 0.00003, 0.30, "psychological",
     "Brief (days-weeks) period of universal telepathy; profound social and religious upheaval"),

    ("Mass_Memory_Loss",
     0, 2021, 0.00008, 0.18, "knowledge_collapse",
     "Region-wide memory loss; knowledge transmission interrupted"),

    ("Linguistic_Bifurcation",
     0, 2021, 0.00008, 0.12, "communication_break",
     "Sudden language fissure across age cohorts; intergenerational communication broken"),

    # === IDEOLOGICAL / DISCOVERY ===
    ("Chthonic_Discovery",
     0, 2021, 0.00005, 0.18, "ideological_break",
     "Discovery of subterranean ancient civilization artifacts; civilizational history overturned"),

    ("Underground_Civilization_Contact",
     0, 2021, 0.00005, 0.20, "ideological_break",
     "Contact with previously unknown subterranean/oceanic human-class civilization"),

    ("Mass_Religious_Vision_Shared",
     0, 2021, 0.00015, 0.18, "ideological_break",
     "All humans simultaneously share an identical religious vision"),

    ("Spontaneous_Empire",
     0, 2021, 0.00010, 0.20, "political_break",
     "Inexplicable political movement spreading globally in a few years"),

    # === ENERGY / TECHNOLOGY ===
    ("Unknown_Energy_Source",
     1500, 2021, 0.00080, 0.20, "tech_unknown",
     "Sudden discovery of inexhaustible non-fossil energy source; economic order overturned"),

    ("Resource_Materialization",
     0, 2021, 0.00008, 0.10, "resource_shock",
     "Sudden appearance of precious-metal deposits; economic order disrupted"),

    # === PHYSICAL / ANOMALOUS ===
    ("Time_Anomaly_Region",
     0, 2021, 0.00003, 0.25, "physical_anomaly",
     "Local-region time-flow anomaly; small but verified physical effect"),

    ("Reality_Rule_Shift_Local",
     0, 2021, 0.00002, 0.40, "physical_anomaly",
     "Local micro-shift in physical laws; effects unpredictable"),

    # === CLIMATE / OCEANIC ===
    ("Ocean_Current_Stop",
     1700, 2021, 0.00080, 0.22, "climate_collapse",
     "Sudden cessation of oceanic conveyor; northern hemisphere climate violently shifts"),
]


def sample_ahistorical_events(rng, year_start, year_end, frequency_multiplier=1.0,
                                world_cfg=None):
    """Sample which ahistorical events occur in this run.

    Returns list of dicts: [{label, year, magnitude, dim, type='ahistorical'}, ...]
    sorted by year.
    """
    events = []
    for ev in AHISTORICAL_EVENTS:
        label, ys, ye, prob_per_year, mag, dim, desc = ev
        if ye < year_start or ys > year_end:
            continue
        overlap_start = max(ys, year_start)
        overlap_end = min(ye, year_end)
        years_in_window = overlap_end - overlap_start

        # Apply frequency multiplier
        adjusted_prob = prob_per_year * frequency_multiplier

        # Geometric: probability of at least one occurrence
        p_occur = 1 - (1 - adjusted_prob) ** max(1, years_in_window)
        if rng.random() < p_occur:
            yr = int(rng.uniform(overlap_start, overlap_end))
            events.append({
                "label": label,
                "year": yr,
                "magnitude": mag,
                "dim": dim,
                "description": desc,
                "type": "ahistorical",
            })
    return sorted(events, key=lambda e: e["year"])


def apply_ahistorical_event_effect(event, shock_add, tech_factor,
                                     religion_strength, world_cfg, rng):
    """Apply event effect to global state. Returns updated values.

    Effects are world-context-dependent: e.g., Solar_Flare devastates
    tech-dependent worlds but barely affects agrarian ones.
    """
    dim = event["dim"]
    mag = event["magnitude"]
    new_shock = shock_add
    new_tech_factor = tech_factor
    new_rs = religion_strength

    if dim == "global_extinction":
        new_shock += mag * 2.0
    elif dim == "tech_collapse":
        # World-context: only tech-heavy worlds suffer
        if world_cfg.get("tech_acceleration", 1.0) >= 1.2:
            new_shock += mag * 1.5
            new_tech_factor /= (1 + mag * 2)
        else:
            new_shock += mag * 0.3  # agrarian society barely affected
    elif dim == "epidemic_unprecedented":
        new_shock += mag * 2.0
    elif dim == "psychological":
        new_shock += mag * 0.8
        # Religion strength jumps unpredictably
        new_rs += rng.uniform(-0.15, 0.15) * mag
    elif dim == "tech_unknown":
        new_shock += mag * 0.4  # transient disruption
        new_tech_factor *= (1 + mag)  # permanent boost
    elif dim == "global_disruption":
        new_shock += mag
    elif dim == "ideological_break":
        new_shock += mag * 0.6
        # Religion gets reshuffled (we model as random delta)
        new_rs += rng.uniform(-0.3, 0.3) * mag
    elif dim == "climate_collapse":
        new_shock += mag * 1.2
    elif dim == "communication_break":
        new_shock += mag * 0.5
    elif dim == "biological_break":
        new_shock += mag
    elif dim == "knowledge_collapse":
        new_shock += mag * 0.8
        # Caller must apply edu *= 0.5 separately
    elif dim == "physical_anomaly":
        new_shock += mag * 0.7
    elif dim == "political_break":
        new_shock += mag * 0.6
    elif dim == "resource_shock":
        new_shock += mag * 0.3
        # Caller must apply asset perturbation separately

    # Bound religion strength
    new_rs = max(0.05, min(0.99, new_rs))
    return new_shock, new_tech_factor, new_rs


def get_event_secondary_effects(event):
    """Return dict of secondary per-agent effects (applied by caller).

    Some events require per-agent state mutation, not just global shock.
    """
    dim = event["dim"]
    mag = event["magnitude"]
    effects = {}

    if dim == "knowledge_collapse":
        # Each agent: edu *= (1 - mag * 0.5)
        effects["edu_multiplier"] = 1 - mag * 0.5
    if dim == "resource_shock":
        # Half agents lose, half gain
        effects["asset_lottery"] = mag * 0.3
    if dim == "physical_anomaly":
        # Random asset loss
        effects["asset_random_loss"] = mag * 0.2
    if dim == "political_break":
        # Governance redistribution
        effects["inst_random_delta"] = mag * 0.15
    if dim == "biological_break":
        # Population direct mortality (independent of dfp)
        effects["direct_mortality_p"] = mag * 0.4

    return effects
