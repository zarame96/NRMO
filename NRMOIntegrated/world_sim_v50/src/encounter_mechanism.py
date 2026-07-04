"""
Unknown-Encounter Mechanism for World Simulation v5.1.

Encounter with a previously-unknown civilization is modeled with 4
distinct effect channels, each with its own intensity:

1. knowledge_transfer: edu/inst boost from new mathematics, astronomy, medicine
2. technology_jump: permanent tech_factor multiplier
3. belief_disruption: religion_strength shock and reshuffling (chaos period)
4. disease_exchange: bidirectional epidemic shock (Columbian-exchange-like)

Encounter intensity evolves over generations:
- gen 0: first_contact (initial recognition)
- gen 1-3: cultural_exchange (active trade and learning)
- gen 4+: colonization OR coexistence (random branching, p=0.4 / 0.6)
"""

# Effect weights per intensity level
INTENSITY_WEIGHTS = {
    "first_contact": {
        "knowledge_transfer": 0.10,
        "technology_jump":    0.05,
        "belief_disruption":  0.40,
        "disease_exchange":   0.85,  # very high; populations have no immunity
    },
    "cultural_exchange": {
        "knowledge_transfer": 0.50,
        "technology_jump":    0.30,
        "belief_disruption":  0.30,
        "disease_exchange":   0.40,
    },
    "colonization": {
        "knowledge_transfer": 0.30,
        "technology_jump":    0.55,
        "belief_disruption":  0.75,  # forced conversion etc.
        "disease_exchange":   0.50,
    },
    "coexistence": {
        "knowledge_transfer": 0.85,
        "technology_jump":    0.75,
        "belief_disruption":  0.10,  # mutual respect
        "disease_exchange":   0.05,  # immunity adapted
    },
}


def initial_intensity():
    return "first_contact"


def evolve_intensity(rng, current, generations_since_contact):
    """Evolve intensity based on time since first contact.

    gen 0:     first_contact
    gen 1-3:   cultural_exchange
    gen 4+:    colonization (p=0.40) or coexistence (p=0.60), then stable
    """
    if generations_since_contact == 0:
        return "first_contact"
    elif generations_since_contact <= 3:
        return "cultural_exchange"
    elif current in ("colonization", "coexistence"):
        # Stable once branched
        return current
    else:
        # Random branching at gen 4
        if rng.random() < 0.40:
            return "colonization"
        else:
            return "coexistence"


def apply_encounter_effects(intensity, base_magnitude,
                             shock_add, tech_factor,
                             religion_strength, rng):
    """Apply per-generation encounter effects to global state.

    Returns updated (shock_add, tech_factor, religion_strength) plus
    per-agent secondary effects dict.
    """
    weights = INTENSITY_WEIGHTS[intensity]

    # Compute combined shock from disease + belief_disruption
    disease_shock = base_magnitude * weights["disease_exchange"] * 0.4
    belief_shock = base_magnitude * weights["belief_disruption"] * 0.15
    shock_add += disease_shock + belief_shock

    # Permanent tech boost (modest per generation)
    tech_boost = base_magnitude * weights["technology_jump"] * 0.10
    tech_factor *= (1 + tech_boost)

    # Belief disruption: religion strength shifts toward chaos
    if weights["belief_disruption"] > 0.30:
        # Strong disruption: random sign large delta
        rs_delta = rng.uniform(-0.30, 0.30) * weights["belief_disruption"]
    else:
        # Weak disruption: slight downward (secularization)
        rs_delta = -0.05 * weights["belief_disruption"]
    religion_strength = max(0.05, min(0.99, religion_strength + rs_delta))

    # Per-agent secondary effects
    secondary = {
        "edu_boost":   base_magnitude * weights["knowledge_transfer"] * 0.05,
        "inst_boost":  base_magnitude * weights["knowledge_transfer"] * 0.04,
        "trade_boost": base_magnitude * weights["technology_jump"] * 0.03,
        # Disease has direct mortality component
        "direct_mortality_p": disease_shock * 0.5,
    }

    return shock_add, tech_factor, religion_strength, secondary


def get_encounter_summary(intensity, generations_since_contact):
    """Return human-readable summary of current encounter state."""
    descriptions = {
        "first_contact":   "Initial recognition, mutual fear, language barrier",
        "cultural_exchange": "Active trade, technology and idea exchange",
        "colonization":    "Power asymmetry, forced conversion, exploitation",
        "coexistence":     "Mutual respect, cultural blending, shared knowledge",
    }
    return f"Gen+{generations_since_contact}: {intensity} ({descriptions[intensity]})"
