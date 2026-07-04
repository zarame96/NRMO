#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World Simulation v5.0.1 — Faith Two-Sided Implementation

Critical fix vs v5.0:
- Faith is decomposed into 6 sub-theories (Calvinist / Buddhist / Communal /
  Charismatic / Ascetic / Militant) reflecting historical diversity
- Each sub-Faith has BOTH positive AND negative effects, calibrated to
  historical sociology evidence
- religion_strength becomes ENDOGENOUS: rises with shocks, falls with tech
  acceleration, polarises with religious conflict
- No ad-hoc "Faith bonus": every Faith effect is mechanistically grounded
- Religious conflict generates ENDOGENOUS shocks affecting all agents

The previous v5.0 had a "God's Invisible Hand" bias: Faith got a unilateral
failure-reduction buffer with no costs. This is now removed and replaced
with explicit positive-and-negative dynamics.
"""
import argparse, json, time
from pathlib import Path
import numpy as np
import pandas as pd

# ============================================================
# WORLD GENERATOR (essentially same as v5.0 except religion_strength_initial)
# ============================================================

def get_world_config(world_name):
    base = {
        "eras": [
            ("Yayoi_Kofun_Early", 0, 400, 0.14, 0.96),
            ("Kofun_Late_Nara",   400, 800, 0.12, 0.965),
            ("Heian_Estate",      800, 1200, 0.10, 0.97),
            ("Kamakura_Sengoku",  1200, 1600, 0.18, 0.965),
            ("Edo",               1600, 1868, 0.08, 0.98),
            ("Meiji_WW2",         1868, 1945, 0.11, 0.975),
            ("Postwar_Modern",    1945, 2021, 0.04, 0.985),
        ],
        "shocks": [
            ("early_epidemic",       160, 200,  0.05),
            ("ancient_epidemic",     520, 560,  0.03),
            ("nara_epidemic",        720, 760,  0.07),
            ("late_heian_warfare",   1180, 1240, 0.05),
            ("nanbokucho_conflict",  1320, 1400, 0.08),
            ("sengoku_conflict",     1460, 1600, 0.10),
            ("late_edo_famine",      1780, 1840, 0.06),
            ("influenza_industrial", 1880, 1920, 0.05),
            ("war_depression",       1920, 1960, 0.09),
        ],
        "tech_acceleration": 1.0,
        "tech_inflection_year": 1868,
        # Initial religion strength — but this is now ENDOGENOUS
        "religion_strength_initial": 0.5,
        # World-specific Faith sub-distribution
        # (which kinds of Faith exist in this world)
        "faith_subdist": {
            "Faith_Buddhist": 0.30,
            "Faith_Communal": 0.30,
            "Faith_Calvinist": 0.10,
            "Faith_Charismatic": 0.10,
            "Faith_Ascetic": 0.10,
            "Faith_Militant": 0.10,
        },
        "default_strategy_dist": {
            "NRMO_vNext": 0.30,
            "Adaptive_OmegaFull": 0.10,
            "ExpectedValueMax": 0.20,
            "RiskAdjustedUtility": 0.20,
            "Faith": 0.10,  # will be subdivided per faith_subdist
            "Drift": 0.10,
        },
    }

    if world_name == "normal":
        return {**base, "name": "Normal Earth"}

    elif world_name == "science_heavy":
        return {
            **base, "name": "Science-Heavy",
            "tech_acceleration": 1.5, "tech_inflection_year": 1700,
            "religion_strength_initial": 0.2,
            "faith_subdist": {  # secularised distribution
                "Faith_Buddhist": 0.25, "Faith_Communal": 0.25,
                "Faith_Calvinist": 0.30, "Faith_Charismatic": 0.05,
                "Faith_Ascetic": 0.10, "Faith_Militant": 0.05,
            },
            "default_strategy_dist": {
                "NRMO_vNext": 0.40, "Adaptive_OmegaFull": 0.15,
                "ExpectedValueMax": 0.25, "RiskAdjustedUtility": 0.10,
                "Faith": 0.02, "Drift": 0.08,
            },
        }

    elif world_name == "religion_heavy":
        return {
            **base, "name": "Religion-Heavy",
            "tech_acceleration": 0.6, "tech_inflection_year": 2050,
            "religion_strength_initial": 0.9,
            "faith_subdist": {  # militant + ascetic over-represented
                "Faith_Buddhist": 0.20, "Faith_Communal": 0.20,
                "Faith_Calvinist": 0.05, "Faith_Charismatic": 0.10,
                "Faith_Ascetic": 0.20, "Faith_Militant": 0.25,
            },
            "default_strategy_dist": {
                "NRMO_vNext": 0.10, "Adaptive_OmegaFull": 0.05,
                "ExpectedValueMax": 0.10, "RiskAdjustedUtility": 0.10,
                "Faith": 0.40, "Drift": 0.25,
            },
        }

    elif world_name == "mix":
        return {
            **base, "name": "Sci-Religion-Mix",
            "tech_acceleration": 1.2, "tech_inflection_year": 1750,
            "religion_strength_initial": 0.7,
            "default_strategy_dist": {
                "NRMO_vNext": 0.25, "Adaptive_OmegaFull": 0.15,
                "ExpectedValueMax": 0.15, "RiskAdjustedUtility": 0.15,
                "Faith": 0.20, "Drift": 0.10,
            },
        }

    elif world_name == "accelerated_tech":
        # In accelerated tech world, faster industrialisation = earlier
        # environmental and social shocks (pollution, dislocation, war scale)
        cfg_base = {
            **base, "name": "Accelerated-Tech",
            "tech_acceleration": 2.0, "tech_inflection_year": 1500,
            "religion_strength_initial": 0.3,
            "faith_subdist": {
                "Faith_Buddhist": 0.20, "Faith_Communal": 0.20,
                "Faith_Calvinist": 0.40, "Faith_Charismatic": 0.10,
                "Faith_Ascetic": 0.05, "Faith_Militant": 0.05,
            },
            "default_strategy_dist": {
                "NRMO_vNext": 0.35, "Adaptive_OmegaFull": 0.20,
                "ExpectedValueMax": 0.30, "RiskAdjustedUtility": 0.05,
                "Faith": 0.02, "Drift": 0.08,
            },
        }
        cfg = {**cfg_base}
        cfg["shocks"] = base["shocks"] + [
            ("early_industrial_pollution", 1500, 1700, 0.04),
            ("accelerated_warfare", 1700, 1900, 0.07),
            ("early_climate_disruption", 1750, 2021, 0.03),
        ]
        return cfg

    elif world_name == "unknown_encounter":
        cfg = {
            **base, "name": "Unknown-Encounter",
            "tech_acceleration": 1.3, "tech_inflection_year": 1500,
            "religion_strength_initial": 0.6,
            "default_strategy_dist": {
                "NRMO_vNext": 0.30, "Adaptive_OmegaFull": 0.15,
                "ExpectedValueMax": 0.20, "RiskAdjustedUtility": 0.15,
                "Faith": 0.10, "Drift": 0.10,
            },
        }
        cfg["shocks"] = base["shocks"] + [("unknown_encounter", 1480, 1520, 0.15)]
        return cfg

    else:
        raise ValueError(f"Unknown world: {world_name}")


# ============================================================
# RANDOM EVENT CATALOG (same as v5.0)
# ============================================================
RANDOM_EVENTS = [
    ("Volcanic_Tambora",     1815, 1820, 0.30, 0.10, "global_temp_drop"),
    ("Black_Death",          1347, 1353, 0.50, 0.18, "epidemic_severe"),
    ("Spanish_Flu",          1918, 1920, 0.50, 0.06, "epidemic_mild"),
    ("Little_Ice_Age",       1300, 1850, 0.05, 0.04, "agriculture_decline"),
    ("Printing_Press",       1450, 1470, 0.30, 0.08, "knowledge_boost"),
    ("Steam_Engine",         1769, 1800, 0.25, 0.12, "industrial_boost"),
    ("Antibiotics",          1928, 1950, 0.25, 0.15, "health_boost"),
    ("Mongol_Invasion",      1274, 1281, 0.40, 0.12, "war_severe"),
    ("Great_Earthquake",     1854, 1923, 0.02, 0.08, "regional_destruction"),
    ("Tsunami",              0, 2021, 0.005, 0.06, "regional_destruction"),
    ("Religion_Reform",      1517, 1540, 0.20, 0.10, "ideology_shift"),
    ("Population_Boom",      1750, 1850, 0.10, 0.05, "demographic_boost"),
    ("Famine",               1500, 2000, 0.008, 0.07, "agriculture_decline"),
    ("New_World_Discovery",  1490, 1510, 0.40, 0.15, "horizon_expansion"),
    ("World_War",            1914, 1945, 0.20, 0.20, "war_severe"),
]


def sample_random_events(rng, year_start, year_end, world_cfg):
    events = []
    for ev in RANDOM_EVENTS:
        label, ys, ye, prob_per_year, mag, dim = ev
        if ye < year_start or ys > year_end:
            continue
        overlap_start = max(ys, year_start)
        overlap_end = min(ye, year_end)
        years_in_window = overlap_end - overlap_start
        p_occur = 1 - (1 - prob_per_year) ** max(1, years_in_window)
        if rng.random() < p_occur:
            yr = int(rng.uniform(overlap_start, overlap_end))
            events.append({"label": label, "year": yr, "magnitude": mag, "dim": dim})
    return sorted(events, key=lambda e: e["year"])


# ============================================================
# DECISION THEORIES
# ============================================================

def normalize_action(a):
    a = np.maximum(a, 0.05)
    return a / a.sum(axis=-1, keepdims=True)


def state_to_nrmo_norm(fk, edu, inst, trade, assets, urban, shock_add):
    R = assets
    E = np.clip(np.full_like(fk, 1 - shock_add * 5), 0, 1)
    G = inst
    O = 0.5 * fk + 0.5 * edu
    K = edu
    X = np.clip(np.full_like(fk, shock_add * 4) + (1 - inst) * 0.3, 0, 1)
    return R, E, G, O, K, X


def cand_pool_8():
    return np.array([
        [0.28, 0.25, 0.25, 0.22], [0.50, 0.18, 0.17, 0.15],
        [0.12, 0.46, 0.22, 0.20], [0.12, 0.16, 0.50, 0.22],
        [0.08, 0.42, 0.18, 0.32], [0.08, 0.20, 0.18, 0.54],
        [0.44, 0.22, 0.18, 0.16], [0.18, 0.10, 0.48, 0.24],
    ])


SAFE_FALLBACK = np.array([0.10, 0.35, 0.30, 0.25])


# Non-Faith theories (unchanged from v5.0)
def theory_evmax(n, R, E, G, O, K, X, rng, world_cfg):
    return np.tile(np.array([0.55, 0.10, 0.10, 0.25]), (n, 1))


def theory_riskadj(n, R, E, G, O, K, X, rng, world_cfg):
    a = np.zeros((n, 4))
    high_x = X > 0.55
    a[high_x] = [0.15, 0.45, 0.15, 0.25]
    a[~high_x] = [0.40, 0.20, 0.18, 0.22]
    low_e = E < 0.30
    a[low_e] = [0.10, 0.50, 0.20, 0.20]
    return normalize_action(a)


def theory_nrmo_vnext(n, R, E, G, O, K, X, rng, world_cfg):
    cands = cand_pool_8()
    g_c = cands[:, 0][None, :]; s_c = cands[:, 1][None, :]
    l_c = cands[:, 2][None, :]; d_c = cands[:, 3][None, :]
    R_, E_, G_, O_, K_, X_ = R[:, None], E[:, None], G[:, None], O[:, None], K[:, None], X[:, None]
    ok = (g_c <= 0.62) & ~((X_ > 0.55) & (g_c > 0.36)) \
       & ~((E_ < 0.28) & (g_c > 0.30)) & ~((G_ < 0.24) & (d_c < 0.16)) \
       & (l_c >= 0.20) & ~((G_ < 0.30) & (d_c < 0.20)) \
       & ~((E_ < 0.45) & (g_c > 0.38))
    productivity = g_c * R_ * np.minimum(E_ / 0.42, 1) * np.minimum(G_ / 0.35, 1)
    score = productivity + 0.4 * O_ + 0.1 * G_ + 0.05 * E_ - 0.3 * X_
    score = np.where(ok, score, -1e9)
    best_idx = score.argmax(axis=1)
    actions = cands[best_idx]
    none_admissible = ~ok.any(axis=1)
    actions[none_admissible] = SAFE_FALLBACK
    return normalize_action(actions)


def theory_omega_full(n, R, E, G, O, K, X, rng, world_cfg):
    cands = cand_pool_8()
    muts = cands[rng.integers(0, 8, size=4)] + rng.uniform(-0.05, 0.05, size=(4, 4))
    cands = np.vstack([cands, muts])
    cands = normalize_action(cands)
    g_c = cands[:, 0][None, :]; s_c = cands[:, 1][None, :]
    l_c = cands[:, 2][None, :]; d_c = cands[:, 3][None, :]
    R_, E_, G_, O_, K_, X_ = R[:, None], E[:, None], G[:, None], O[:, None], K[:, None], X[:, None]
    ok = (g_c <= 0.62) & ~((X_ > 0.55) & (g_c > 0.36)) \
       & ~((E_ < 0.28) & (g_c > 0.30)) & ~((G_ < 0.24) & (d_c < 0.16)) \
       & (l_c >= 0.20) & ~((G_ < 0.30) & (d_c < 0.20)) \
       & ~((E_ < 0.45) & (g_c > 0.38))
    productivity = g_c * R_ * np.minimum(E_ / 0.42, 1) * np.minimum(G_ / 0.35, 1)
    g_sust = np.clip(0.28 + 0.08 * E_ + 0.06 * G_ - 0.10 * X_, 0.15, 0.40)
    drift = np.maximum(0, g_c - g_sust) * (1 + 0.5 * X_) * (1 - 0.3 * G_)
    score = productivity + 0.4 * O_ + 0.1 * G_ + 0.05 * E_ - 0.3 * X_ - 1.0 * drift
    score = np.where(ok, score, -1e9)
    best_idx = score.argmax(axis=1)
    actions = cands[best_idx]
    none_admissible = ~ok.any(axis=1)
    actions[none_admissible] = SAFE_FALLBACK
    return normalize_action(actions)


def theory_drift(n, R, E, G, O, K, X, rng, world_cfg):
    return np.tile(np.array([0.18, 0.30, 0.22, 0.30]), (n, 1))


# ============================================================
# 6 FAITH SUB-THEORIES
# Each has both POSITIVE and NEGATIVE mechanisms.
# These are returned as actions; the dynamics layer applies the
# specific positive/negative effects based on faith_class.
# ============================================================

# (allocation, faith_class)
# faith_class is used in dynamics to apply the right pos/neg effects.

def theory_faith_buddhist(n, R, E, G, O, K, X, rng, world_cfg):
    """Buddhist/Daoist: 無常・無我・知足. Low growth, high s, modest l, high d."""
    return np.tile(np.array([0.10, 0.45, 0.20, 0.25]), (n, 1))

def theory_faith_communal(n, R, E, G, O, K, X, rng, world_cfg):
    """Communal (Confucian/Islamic-waqf-style/Christian-charity): 共同体重視."""
    return np.tile(np.array([0.18, 0.32, 0.15, 0.35]), (n, 1))

def theory_faith_calvinist(n, R, E, G, O, K, X, rng, world_cfg):
    """Calvinist/prosperity-gospel: 現世での成功 = 救済の徴."""
    return np.tile(np.array([0.45, 0.20, 0.15, 0.20]), (n, 1))

def theory_faith_charismatic(n, R, E, G, O, K, X, rng, world_cfg):
    """Pentecostal/charismatic: 神秘体験・信仰治癒. Volatile."""
    a = np.tile(np.array([0.35, 0.25, 0.10, 0.30]), (n, 1))
    # Volatility: random perturbation each generation
    a += rng.normal(0, 0.05, size=a.shape)
    return normalize_action(a)

def theory_faith_ascetic(n, R, E, G, O, K, X, rng, world_cfg):
    """Ascetic/monastic: 出家・独身. EXTREME negative for direct line."""
    return np.tile(np.array([0.05, 0.50, 0.30, 0.15]), (n, 1))

def theory_faith_militant(n, R, E, G, O, K, X, rng, world_cfg):
    """Militant/crusader: 異教徒排撃・聖戦. Aggressive."""
    return np.tile(np.array([0.40, 0.15, 0.15, 0.30]), (n, 1))


# Strategy registry
THEORIES = {
    "ExpectedValueMax":     (theory_evmax, False, None),
    "RiskAdjustedUtility":  (theory_riskadj, False, None),
    "NRMO_vNext":           (theory_nrmo_vnext, False, None),
    "Adaptive_OmegaFull":   (theory_omega_full, False, None),
    "Faith_Buddhist":       (theory_faith_buddhist, False, "buddhist"),
    "Faith_Communal":       (theory_faith_communal, False, "communal"),
    "Faith_Calvinist":      (theory_faith_calvinist, False, "calvinist"),
    "Faith_Charismatic":    (theory_faith_charismatic, False, "charismatic"),
    "Faith_Ascetic":        (theory_faith_ascetic, False, "ascetic"),
    "Faith_Militant":       (theory_faith_militant, False, "militant"),
    "Drift":                (theory_drift, True, None),
}


# ============================================================
# FAITH POSITIVE/NEGATIVE EFFECTS
# These apply to Faith agents during dynamics, modulated by
# religion_strength (which is endogenous).
# ============================================================

def faith_positive_dfp_modifier(faith_class, religion_strength):
    """Positive: psychological resilience, communal insurance.
    Returns multiplier on direct_failure_probability (< 1.0 = better)."""
    if faith_class == "buddhist":
        # Acceptance of impermanence → low absolute value lost in shock
        # Modest psychological buffer
        return 1 - 0.05 * religion_strength
    elif faith_class == "communal":
        # Strong communal insurance: shocks shared
        return 1 - 0.12 * religion_strength
    elif faith_class == "calvinist":
        # Discipline + work ethic; modest benefit
        return 1 - 0.04 * religion_strength
    elif faith_class == "charismatic":
        # Hope-based resilience; small benefit, but variable (handled
        # in volatility of action itself)
        return 1 - 0.06 * religion_strength
    elif faith_class == "ascetic":
        # Personal resilience but no community help
        return 1 - 0.03 * religion_strength
    elif faith_class == "militant":
        # Group cohesion but no general benefit
        return 1 - 0.04 * religion_strength
    return 1.0


def faith_negative_dfp_modifier(faith_class, religion_strength, era_idx):
    """Negative: persecution risk, sectarian conflict, isolation.
    Returns multiplier on dfp (> 1.0 = worse)."""
    if faith_class == "buddhist":
        # Buddhist clergy purges (Sengoku 一向一揆鎮圧, Meiji 廃仏毀釈)
        if era_idx == 3:  # Sengoku
            return 1 + 0.06 * religion_strength
        if era_idx == 5:  # Meiji
            return 1 + 0.08 * religion_strength
        return 1.0
    elif faith_class == "communal":
        # Generally low negative effects
        return 1.0
    elif faith_class == "calvinist":
        # Religious dissident persecution (in Catholic regimes)
        if era_idx in [3, 4]:
            return 1 + 0.05 * religion_strength
        return 1.0
    elif faith_class == "charismatic":
        # Cult-like behaviour risk: some movements end in mass death
        # (Tail risk: small probability, large impact)
        return 1 + 0.08 * religion_strength
    elif faith_class == "ascetic":
        # MAJOR negative: monastic vow → no direct heir possibility
        # This dominates the trade-off
        return 1 + 0.30  # essentially additive: ascetic vows often = no children
    elif faith_class == "militant":
        # Violent confrontation → high direct failure during conflict eras
        # ALSO: militants always face higher direct mortality from combat
        base_militant = 0.10 * religion_strength  # baseline combat mortality
        if era_idx == 3:  # Sengoku
            return 1 + base_militant + 0.18 * religion_strength
        if era_idx == 5:  # Meiji_WW2 (religious nationalism era)
            return 1 + base_militant + 0.10 * religion_strength
        return 1 + base_militant + 0.04 * religion_strength
    return 1.0


def faith_edu_gain_modifier(faith_class, religion_strength, year):
    """Faith effect on educational gain: some faiths suppress secular
    learning, others promote it."""
    if faith_class == "buddhist":
        # Promotes literacy (sutras, calligraphy) but limits scientific empiricism
        return 1 + 0.05 * religion_strength
    elif faith_class == "communal":
        # Confucian emphasis on study → strong positive
        return 1 + 0.15 * religion_strength
    elif faith_class == "calvinist":
        # Strong literacy push (read scripture directly)
        return 1 + 0.20 * religion_strength
    elif faith_class == "charismatic":
        # Anti-intellectual tendency
        return 1 - 0.15 * religion_strength
    elif faith_class == "ascetic":
        # Theological learning yes, but suppresses worldly knowledge
        return 1 - 0.05 * religion_strength
    elif faith_class == "militant":
        # War-focused, education suppressed
        return 1 - 0.20 * religion_strength
    return 1.0


def faith_collateral_modifier(faith_class, religion_strength):
    """Faith effect on collateral (sub-branch) success rate."""
    if faith_class == "buddhist":
        return 1.0  # neutral
    elif faith_class == "communal":
        return 1 + 0.10 * religion_strength  # strong communal kinship → better collateral
    elif faith_class == "calvinist":
        return 1.0  # neutral
    elif faith_class == "charismatic":
        return 1 - 0.05 * religion_strength  # individualistic experience
    elif faith_class == "ascetic":
        return 1 - 0.20  # ascetic groups don't reproduce; no collateral support
    elif faith_class == "militant":
        return 1 + 0.05 * religion_strength  # warrior brotherhoods help each other
    return 1.0


def faith_shock_loss_modifier(faith_class, religion_strength):
    """Faith effect on asset loss during shocks (communal insurance)."""
    if faith_class == "buddhist":
        return 1 - 0.08 * religion_strength
    elif faith_class == "communal":
        return 1 - 0.15 * religion_strength  # strong waqf/charity support
    elif faith_class == "calvinist":
        return 1 - 0.05 * religion_strength
    elif faith_class == "charismatic":
        return 1 - 0.04 * religion_strength
    elif faith_class == "ascetic":
        return 1 - 0.10 * religion_strength  # monastic protection
    elif faith_class == "militant":
        return 1.0  # no buffer
    return 1.0


def faith_charismatic_tail_event(rng, n_charismatic, religion_strength):
    """Charismatic cults occasionally suffer mass-death events.
    Returns boolean array of agents lost to such events."""
    # Per-generation per-agent probability of cult collapse
    p_cult_disaster = 0.003 * religion_strength
    return rng.random(n_charismatic) < p_cult_disaster


# ============================================================
# ENDOGENOUS RELIGION_STRENGTH DYNAMICS
# ============================================================

def update_religion_strength(current_rs, shock_add, tech_factor,
                              gen_random_events, militant_share,
                              year, world_cfg):
    """
    Religion strength evolves based on:
    - Major shock (epidemic/war) → rises (people seek meaning in crisis)
    - Tech acceleration → falls (secularisation, Inglehart-Welzel)
    - Religious conflict (high militant share) → polarises
    - Religion_Reform event → discontinuous jump
    """
    new_rs = current_rs

    # Shock-driven rise (Black Death → flagellants etc.)
    if shock_add > 0.05:
        new_rs += 0.03 * shock_add  # multiply by shock magnitude

    # Tech-driven decline
    if tech_factor > 1.0 and year >= world_cfg["tech_inflection_year"]:
        new_rs -= 0.008 * (tech_factor - 1)

    # Religious reform shock
    for ev in gen_random_events:
        if ev["dim"] == "ideology_shift":
            # Reformation: temporary rise, then decline
            new_rs += 0.05

    # Polarisation pressure if militant share is large
    if militant_share > 0.15:
        new_rs += 0.01

    # Modern long-run secularisation (constant downward drift after 1900)
    if year >= 1900:
        new_rs -= 0.005

    # Bound to [0.05, 0.99]
    new_rs = np.clip(new_rs, 0.05, 0.99)
    return new_rs


def religious_conflict_shock(rng, militant_share, religion_strength, year, era_idx):
    """When militant Faith share is high in a religious world,
    endogenous shocks are generated (religious wars, persecutions).
    Returns additional shock magnitude affecting EVERYONE (not just Faith)."""
    if militant_share < 0.05 or religion_strength < 0.3:
        return 0.0

    # Probability of religious conflict event
    p_conflict = 0.12 * militant_share * religion_strength
    # Era multiplier (Sengoku = high baseline religious conflict)
    if era_idx == 3:
        p_conflict *= 2.0
    if era_idx == 4:  # Edo, religious suppression era
        p_conflict *= 0.5

    if rng.random() < p_conflict:
        magnitude = 0.04 + 0.10 * militant_share * religion_strength
        return magnitude
    return 0.0


# ============================================================
# CONSTANTS
# ============================================================
REGIONS = ["North_Kyushu", "Kinai", "Setouchi_Kibi", "Tokai_Nobi",
           "Kanto_Inland", "South_Tohoku"]
INIT_REGION_PROBS = np.array([.30, .20, .20, .15, .10, .05])
OCC = ["agrarian", "rural_notable", "temple_estate_clerk", "warrior_auxiliary",
       "craft_trade", "merchant_self", "urban_wage_labor", "industrial_worker",
       "company_skilled_clerical", "education_public_clerical",
       "professional_manager_owner"]
BASE_OCC = np.array([
    [.78, .08, .00, .04, .07, .02, .00, .00, .00, .00, .00],
    [.55, .13, .08, .08, .10, .03, .01, .00, .00, .00, .00],
    [.45, .16, .10, .08, .10, .04, .02, .00, .00, .00, .00],
    [.34, .12, .05, .18, .12, .06, .04, .00, .00, .00, .00],
    [.34, .09, .05, .03, .16, .12, .05, .00, .00, .02, .00],
    [.24, .04, .00, .00, .11, .07, .14, .18, .07, .04, .01],
    [.12, .02, .00, .00, .08, .07, .13, .15, .22, .07, .02]], dtype=float)
EDU_GAIN = np.array([.002, .006, .015, .004, .006, .010, .006, .008, .016, .020, .022])
INST_GAIN = np.array([.002, .012, .018, .006, .006, .012, .004, .006, .012, .018, .018])
TRADE_GAIN = np.array([.002, .006, .004, .005, .014, .020, .006, .008, .010, .005, .014])
ASSET_GAIN = np.array([.004, .010, .006, .004, .010, .014, .004, .006, .008, .007, .012])
URBAN_GAIN = np.array([.001, .003, .004, .003, .008, .010, .014, .015, .014, .010, .014])


def era_idx_for_year(y, eras):
    for i, e in enumerate(eras):
        if e[1] <= y < e[2]:
            return i
    return len(eras) - 1


def shock_for_year(y, shocks):
    add = 0.0; labels = []
    for sh in shocks:
        if sh[1] <= y < sh[2]:
            add += sh[3]; labels.append(sh[0])
    return add, ";".join(labels)


def weighted_choice_rows(prob_mat, rng):
    cs = np.cumsum(prob_mat, axis=1)
    r = rng.random(prob_mat.shape[0])
    return (cs < r[:, None]).sum(axis=1)


def terminal_category_vec(occ, fk, edu, inst, trade, assets, urban, absorbed):
    term = np.full(occ.shape, "rural_farm_part_time_farm", dtype=object)
    term[(occ == 4) | (occ == 5) | (trade > 0.55)] = "craft_trade_self_employed"
    term[(occ == 6) | ((urban > 0.60) & (assets < 0.25))] = "urban_wage_labor"
    term[((occ == 7) | (occ == 8) | ((urban > 0.50) & (edu > 0.40)))] = "company_skilled_clerical"
    term[(occ == 9) | ((edu > 0.58) & (inst > 0.52) & (trade < 0.65))] = "education_public_clerical"
    term[(occ == 10) | ((edu > 0.72) & (inst > 0.60) & (assets > 0.35))] = "professional_manager_owner"
    term[absorbed] = "lineage_absorbed_or_lost"
    return term


# ============================================================
# MAIN SIMULATION
# ============================================================

def run_world(world_cfg, n=100000, seed=20260506, strategy_dist=None,
              spotlight_idx=0, verbose=False):
    rng = np.random.default_rng(seed)
    eras = world_cfg["eras"]
    shocks = world_cfg["shocks"]
    tech_accel = world_cfg["tech_acceleration"]
    tech_inflection = world_cfg["tech_inflection_year"]
    religion_strength = world_cfg["religion_strength_initial"]
    faith_subdist = world_cfg["faith_subdist"]

    events = sample_random_events(rng, 0, 2020, world_cfg)
    if verbose:
        print(f"  World: {world_cfg['name']}")
        print(f"  Initial religion_strength: {religion_strength:.2f}")
        print(f"  Random events: {len(events)}")

    # Strategy distribution: split Faith into sub-faiths
    sd_input = strategy_dist or world_cfg["default_strategy_dist"]
    expanded_dist = {}
    for s, p in sd_input.items():
        if s == "Faith":
            for sub_name, sub_p in faith_subdist.items():
                expanded_dist[sub_name] = p * sub_p
        else:
            expanded_dist[s] = p
    strategy_names = list(expanded_dist.keys())
    strategy_probs = np.array(list(expanded_dist.values()))
    strategy_probs = strategy_probs / strategy_probs.sum()
    agent_strategy = rng.choice(len(strategy_names), size=n, p=strategy_probs)

    # Map strategy idx → faith_class (or None)
    strategy_faith_class = []
    for sname in strategy_names:
        _, _, fc = THEORIES[sname]
        strategy_faith_class.append(fc)

    # Initial state
    initial_region = rng.choice(len(REGIONS), size=n, p=INIT_REGION_PROBS)
    region = initial_region.copy()
    occ = np.zeros(n, dtype=np.int16)
    for ri in range(len(REGIONS)):
        idx = np.where(region == ri)[0]
        if len(idx) == 0:
            continue
        if REGIONS[ri] in ("North_Kyushu", "Setouchi_Kibi", "Kinai"):
            p = np.array([.86, .07, 0, .02, .05, 0, 0, 0, 0, 0, 0])
        else:
            p = np.array([.91, .05, 0, .01, .03, 0, 0, 0, 0, 0, 0])
        occ[idx] = rng.choice(len(OCC), size=len(idx), p=p / p.sum())
    fk = rng.uniform(.04, .16, size=n)
    edu = rng.uniform(.01, .06, size=n)
    inst = rng.uniform(.02, .10, size=n)
    trade = rng.uniform(.02, .12, size=n)
    assets = rng.uniform(.04, .18, size=n)
    urban = rng.uniform(.00, .08, size=n)
    absorbed = np.zeros(n, dtype=bool)
    completed_gen = np.zeros(n, dtype=np.int16)

    spotlight_chronicle = []
    religion_strength_log = []
    endogenous_conflict_log = []
    event_log = []

    for gen in range(1, 51):
        year = (gen - 1) * 40
        ei = era_idx_for_year(year, eras)
        era_name, _, _, base_fail, collat_success = eras[ei]
        shock_add, shock_label = shock_for_year(year, shocks)

        gen_events = [e for e in events if year <= e["year"] < year + 40]
        for ev in gen_events:
            if ev["dim"] in ("epidemic_severe", "epidemic_mild", "war_severe"):
                shock_add += ev["magnitude"]
            elif ev["dim"] in ("agriculture_decline", "regional_destruction"):
                shock_add += ev["magnitude"] * 0.7
            event_log.append(ev)

        # === ENDOGENOUS RELIGIOUS CONFLICT ===
        active_now = ~absorbed
        militant_count = 0
        for s_idx, sname in enumerate(strategy_names):
            if strategy_faith_class[s_idx] == "militant":
                militant_count += int(((agent_strategy == s_idx) & active_now).sum())
        militant_share = militant_count / max(active_now.sum(), 1)
        rel_conflict_shock = religious_conflict_shock(rng, militant_share,
                                                       religion_strength, year, ei)
        if rel_conflict_shock > 0:
            shock_add += rel_conflict_shock
            endogenous_conflict_log.append({
                "year": year, "shock_added": rel_conflict_shock,
                "militant_share": militant_share,
                "religion_strength": religion_strength,
            })

        # === UPDATE RELIGION STRENGTH ===
        tech_factor = tech_accel if year >= tech_inflection else 1.0
        religion_strength = update_religion_strength(
            religion_strength, shock_add, tech_factor, gen_events,
            militant_share, year, world_cfg)
        religion_strength_log.append({"year": year, "rs": religion_strength,
                                       "militant_share": militant_share})

        active = ~absorbed
        idx = np.where(active)[0]
        if len(idx) == 0:
            break

        # Compute actions per strategy
        R_a, E_a, G_a, O_a, K_a, X_a = state_to_nrmo_norm(
            fk[idx], edu[idx], inst[idx], trade[idx], assets[idx], urban[idx], shock_add)
        action = np.zeros((len(idx), 4))
        for s_idx, sname in enumerate(strategy_names):
            mask = agent_strategy[idx] == s_idx
            if not mask.any():
                continue
            theory_fn, bypass, _ = THEORIES[sname]
            sub_action = theory_fn(int(mask.sum()),
                                    R_a[mask], E_a[mask], G_a[mask],
                                    O_a[mask], K_a[mask], X_a[mask],
                                    rng, world_cfg)
            if bypass:
                sub_action = np.zeros_like(sub_action)
            action[mask] = sub_action

        g_a = action[:, 0]; s_a = action[:, 1]
        l_a = action[:, 2]; d_a = action[:, 3]

        # === DFP COMPUTATION ===
        dfp = base_fail + shock_add - .030 * assets[idx] - .025 * inst[idx] - .020 * edu[idx]
        dfp *= (1 - 0.45 * s_a)
        dfp *= (1 - 0.10 * l_a)
        dfp += g_a * shock_add * 0.45

        # === FAITH POSITIVE/NEGATIVE EFFECTS ===
        # Apply per-faith-class modifiers symmetrically
        for s_idx, sname in enumerate(strategy_names):
            fc = strategy_faith_class[s_idx]
            if fc is None:
                continue
            mask = agent_strategy[idx] == s_idx
            if not mask.any():
                continue
            pos_mod = faith_positive_dfp_modifier(fc, religion_strength)
            neg_mod = faith_negative_dfp_modifier(fc, religion_strength, ei)
            net_mod = pos_mod * neg_mod
            dfp[mask] *= net_mod

        # === CHARISMATIC TAIL EVENT (cult disasters) ===
        for s_idx, sname in enumerate(strategy_names):
            if strategy_faith_class[s_idx] == "charismatic":
                mask = agent_strategy[idx] == s_idx
                if not mask.any():
                    continue
                # Sub-population may have catastrophic event
                tail_lost = faith_charismatic_tail_event(rng, int(mask.sum()),
                                                          religion_strength)
                if tail_lost.any():
                    # These agents force-die this gen
                    sub_idx = idx[mask]
                    forced_lost = sub_idx[tail_lost]
                    dfp[np.isin(idx, forced_lost)] = 1.0  # essentially certain death

        dfp = np.clip(dfp, .015, .85)  # max increased to allow Faith negative effects

        direct_success = rng.random(len(idx)) >= dfp
        direct_global = idx[direct_success]
        fail_global = idx[~direct_success]
        collateral_reset_global = np.array([], dtype=int)

        if len(fail_global):
            if gen == 1:
                absorbed[fail_global] = True
            else:
                fail_local_idx = np.where(~direct_success)[0]
                d_fail = d_a[fail_local_idx]
                cprob_base = np.clip(collat_success - shock_add * .10, .88, .995)
                cprob = cprob_base * (1 + 0.20 * d_fail)
                # Apply Faith collateral modifier
                for s_idx, sname in enumerate(strategy_names):
                    fc = strategy_faith_class[s_idx]
                    if fc is None:
                        continue
                    sub_mask = agent_strategy[fail_global] == s_idx
                    if not sub_mask.any():
                        continue
                    cmod = faith_collateral_modifier(fc, religion_strength)
                    cprob[sub_mask] *= cmod
                cprob = np.clip(cprob, 0.0, 0.999)
                csuccess = rng.random(len(fail_global)) <= cprob
                collateral_reset_global = fail_global[csuccess]
                lost = fail_global[~csuccess]
                if len(collateral_reset_global):
                    probs = np.array([.50, .07, 0, .03, .20, .06, .10, .02, .01, .01, 0])
                    occ[collateral_reset_global] = rng.choice(
                        len(OCC), size=len(collateral_reset_global), p=probs / probs.sum())
                if len(lost):
                    absorbed[lost] = True

        survivors = idx[~absorbed[idx]]
        if len(survivors):
            surv_local_idx = np.where(~absorbed[idx])[0]
            g_s = g_a[surv_local_idx]; s_s = s_a[surv_local_idx]
            l_s = l_a[surv_local_idx]; d_s = d_a[surv_local_idx]

            scores = np.tile(BASE_OCC[ei], (len(survivors), 1)).astype(float)
            central = np.isin(region[survivors], [1, 2, 3])
            urban_bias = urban[survivors] + central * .08
            scores[:, 1] += .06 * assets[survivors]
            scores[:, 2] += .12 * edu[survivors] + .08 * inst[survivors]
            if ei == 3:
                scores[:, 3] += .06 * assets[survivors]
            scores[:, 4] += .06 * trade[survivors]
            scores[:, 5] += .10 * trade[survivors] + .04 * assets[survivors]
            scores[:, 6] += .04 * urban_bias
            if ei >= 5:
                scores[:, 7] += .10 * urban_bias
                scores[:, 8] += .14 * edu[survivors] + .05 * inst[survivors]
                scores[:, 10] += .10 * edu[survivors] + .08 * assets[survivors] + .05 * inst[survivors]
            if ei >= 4:
                scores[:, 9] += .11 * edu[survivors] + .06 * inst[survivors]
            scores[np.arange(len(survivors)), occ[survivors]] += .18

            scores[:, 1] += 0.04 * g_s; scores[:, 4] += 0.06 * g_s
            scores[:, 5] += 0.08 * g_s; scores[:, 9] += 0.10 * l_s
            scores[:, 10] += 0.08 * l_s; scores[:, 8] += 0.06 * (l_s + g_s)
            scores[:, 7] += 0.04 * urban_bias * (1 + 0.3 * g_s)

            occ[survivors] = weighted_choice_rows(
                scores / scores.sum(axis=1, keepdims=True), rng)

            o = occ[survivors]
            eg = EDU_GAIN[o].copy() * tech_factor
            ig = INST_GAIN[o].copy() * tech_factor
            tg = TRADE_GAIN[o].copy()
            ag = ASSET_GAIN[o].copy()
            ug = URBAN_GAIN[o].copy()
            if year >= tech_inflection:
                eg += .012 * tech_factor; ug += .010
            if year >= max(1945, tech_inflection):
                eg += .018 * tech_factor
                inst[survivors] = np.clip(inst[survivors] + .005, 0, 1)
            eg += 0.020 * l_s; ig += 0.012 * d_s
            tg += 0.018 * g_s; ag += 0.025 * g_s - 0.005 * (l_s + d_s)
            ug += 0.012 * g_s * (year >= 1600)

            # === Apply Faith edu modifier (per agent) ===
            edu_modifier = np.ones(len(survivors))
            for s_idx, sname in enumerate(strategy_names):
                fc = strategy_faith_class[s_idx]
                if fc is None:
                    continue
                sub_mask = agent_strategy[survivors] == s_idx
                if not sub_mask.any():
                    continue
                edu_modifier[sub_mask] = faith_edu_gain_modifier(fc, religion_strength, year)
            eg = eg * edu_modifier

            edu[survivors] = np.clip(edu[survivors] * .985 + eg + rng.normal(0, .006, size=len(survivors)), 0, 1)
            inst[survivors] = np.clip(inst[survivors] * .990 + ig + rng.normal(0, .005, size=len(survivors)), 0, 1)
            trade[survivors] = np.clip(trade[survivors] * .990 + tg + rng.normal(0, .006, size=len(survivors)), 0, 1)
            assets[survivors] = np.clip(assets[survivors] * .988 + ag + rng.normal(0, .010, size=len(survivors)), 0, 1)
            urban[survivors] = np.clip(urban[survivors] * .990 + ug + rng.normal(0, .006, size=len(survivors)), 0, 1)

            if shock_add > 0:
                shock_buf = (1 - 0.30 * s_s)
                # Apply Faith shock loss modifier
                shock_loss_mod = np.ones(len(survivors))
                for s_idx, sname in enumerate(strategy_names):
                    fc = strategy_faith_class[s_idx]
                    if fc is None:
                        continue
                    sub_mask = agent_strategy[survivors] == s_idx
                    if not sub_mask.any():
                        continue
                    shock_loss_mod[sub_mask] = faith_shock_loss_modifier(fc, religion_strength)
                effective_shock_buf = shock_buf * shock_loss_mod
                assets[survivors] = np.clip(
                    assets[survivors] - rng.uniform(0, shock_add * .6, size=len(survivors)) * effective_shock_buf, 0, 1)
                fk[survivors] = np.clip(
                    fk[survivors] - rng.uniform(0, shock_add * .25, size=len(survivors)) * effective_shock_buf, 0, 1)
        completed_gen[idx] = gen

    term = terminal_category_vec(occ, fk, edu, inst, trade, assets, urban, absorbed)
    n_continued = int((~absorbed).sum())
    p_continued = float((~absorbed).mean())

    per_strategy = {}
    for s_idx, sname in enumerate(strategy_names):
        mask = agent_strategy == s_idx
        if not mask.any():
            continue
        sub_term = term[mask]
        sub_n = int(mask.sum())
        unique, counts = np.unique(sub_term, return_counts=True)
        edist = dict(zip(unique, counts))
        per_strategy[sname] = {
            "n": sub_n,
            "p_continued": 1 - edist.get("lineage_absorbed_or_lost", 0) / sub_n,
            "p_professional": edist.get("professional_manager_owner", 0) / sub_n,
            "p_edu_public": edist.get("education_public_clerical", 0) / sub_n,
            "p_company": edist.get("company_skilled_clerical", 0) / sub_n,
            "p_rural_farm": edist.get("rural_farm_part_time_farm", 0) / sub_n,
            "mean_assets_alive": float(assets[mask & ~absorbed].mean()) if (mask & ~absorbed).any() else 0,
            "mean_edu_alive": float(edu[mask & ~absorbed].mean()) if (mask & ~absorbed).any() else 0,
            "faith_class": strategy_faith_class[s_idx],
        }

    unique, counts = np.unique(term, return_counts=True)
    endpoint_dist = dict(zip(unique, counts))

    return {
        "world_name": world_cfg["name"],
        "n_total": n,
        "p_continued": p_continued,
        "n_continued": n_continued,
        "endpoint_dist": {k: int(v) for k, v in endpoint_dist.items()},
        "per_strategy": per_strategy,
        "events_occurred": event_log,
        "religion_strength_log": religion_strength_log,
        "endogenous_conflict_log": endogenous_conflict_log,
    }


def composite_score(stats):
    return (1.0 * stats["p_continued"]
          + 1.5 * stats["p_professional"]
          + 1.0 * stats["p_edu_public"]
          + 0.4 * stats["p_company"]
          - 0.3 * stats["p_rural_farm"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="normal")
    ap.add_argument("--n", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=20260506)
    ap.add_argument("--all_worlds", action="store_true")
    ap.add_argument("--outdir", default="outputs_v501")
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    if args.all_worlds:
        worlds = ["normal", "science_heavy", "religion_heavy", "mix",
                  "accelerated_tech", "unknown_encounter"]
    else:
        worlds = [args.world]

    all_results = {}
    for w in worlds:
        cfg = get_world_config(w)
        print(f"\n{'='*70}\nRunning: {cfg['name']}  (n={args.n})\n{'='*70}")
        t0 = time.time()
        res = run_world(cfg, n=args.n, seed=args.seed, verbose=True)
        rt = time.time() - t0
        print(f"  Runtime: {rt:.1f}s, continuation rate: {res['p_continued']*100:.2f}%")

        # Religion strength trajectory
        rs_final = res["religion_strength_log"][-1]["rs"]
        rs_init = cfg["religion_strength_initial"]
        n_endo_conflicts = len(res["endogenous_conflict_log"])
        print(f"  Religion strength: {rs_init:.2f} -> {rs_final:.2f}")
        print(f"  Endogenous religious conflicts: {n_endo_conflicts}")

        print(f"\n  Per-Strategy Composite Score Ranking:")
        rows = []
        for sname, stats in res["per_strategy"].items():
            score = composite_score(stats)
            fc = stats["faith_class"] or "secular"
            rows.append((sname, fc, stats["n"], stats["p_continued"]*100,
                        (stats["p_professional"] + stats["p_edu_public"])*100, score))
        rows.sort(key=lambda x: -x[5])
        for r, row in enumerate(rows, 1):
            print(f"    {r:2d}. {row[0]:<22} ({row[1]:<11}) n={row[2]:>5}  cont={row[3]:>5.2f}%  upward={row[4]:>5.2f}%  composite={row[5]:.4f}")

        all_results[w] = res

    with open(out / "all_world_results_v501.json", "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

    if len(worlds) > 1:
        print(f"\n\n{'='*120}")
        print(f"CROSS-WORLD STRATEGY COMPARISON (composite score, v5.0.1 with two-sided Faith)")
        print('='*120)
        all_strategies = set()
        for r in all_results.values():
            all_strategies.update(r["per_strategy"].keys())
        all_strategies = sorted(all_strategies)
        header = f"  {'Strategy':<25}" + "".join(f"{w[:18]:>15}" for w in [all_results[wd]['world_name'] for wd in worlds])
        print(header)
        cross_data = {"strategy": list(all_strategies)}
        for s in all_strategies:
            line = f"  {s:<25}"
            for wd in worlds:
                if s in all_results[wd]["per_strategy"]:
                    sc = composite_score(all_results[wd]["per_strategy"][s])
                    line += f"{sc:>15.4f}"
                    cross_data.setdefault(all_results[wd]['world_name'], []).append(sc)
                else:
                    line += f"{'-':>15}"
                    cross_data.setdefault(all_results[wd]['world_name'], []).append(None)
            print(line)

        df_cross = pd.DataFrame(cross_data)
        df_cross.to_csv(out / "cross_world_comparison_v501.csv", index=False)


if __name__ == "__main__":
    main()
