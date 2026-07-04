#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World Simulation v5.0 Stage 1 — Multi-World, Multi-Strategy, 100k Agent Prototype

This is the *Reality Track* implementation: what we can actually run on a non-powerful
CPU/GPU machine. The full Vision (1B agents, full multi-civ, full individual layer) is
documented separately in the LaTeX chapter.

Features (Stage 1):
- 5 world types: Normal Earth, Science-Heavy, Religion-Heavy, Mix, Accelerated-Tech
- 100,000 agents
- 6 decision theories pluralistically distributed
- Telescope Architecture (Spotlight + Background)
- Random Event Catalog (15 events)
- Individual life chronicle for spotlight person
- Strategy performance comparison across worlds

Run:
    python world_sim_v5_stage1.py --world normal --n 100000 --seed 20260506
    python world_sim_v5_stage1.py --world religion_heavy --strategy_dist alt
    python world_sim_v5_stage1.py --all_worlds --n 30000
"""
import argparse, json, time, os
from pathlib import Path
import numpy as np
import pandas as pd

# ============================================================
# WORLD GENERATOR
# ============================================================

def get_world_config(world_name):
    """Returns world parameters defining environment dynamics."""
    base = {
        # Era boundaries (year_start, year_end, base_failure, collateral_success)
        "eras": [
            ("Yayoi_Kofun_Early", 0, 400, 0.14, 0.96),
            ("Kofun_Late_Nara",   400, 800, 0.12, 0.965),
            ("Heian_Estate",      800, 1200, 0.10, 0.97),
            ("Kamakura_Sengoku",  1200, 1600, 0.18, 0.965),
            ("Edo",               1600, 1868, 0.08, 0.98),
            ("Meiji_WW2",         1868, 1945, 0.11, 0.975),
            ("Postwar_Modern",    1945, 2021, 0.04, 0.985),
        ],
        # (label, year_start, year_end, shock_magnitude)
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
        # Tech curve modifiers (year → tech_level multiplier)
        "tech_acceleration": 1.0,         # multiplicative on edu/inst gain
        "tech_inflection_year": 1868,     # year when modern tech kicks in
        # Religion strength (affects Faith decision theory effectiveness)
        "religion_strength": 0.5,         # 0=none, 1=very strong
        # Faith provides shock buffer (psychological resilience)
        "faith_shock_buffer": 0.10,
        # Default strategy distribution
        "default_strategy_dist": {
            "NRMO_vNext": 0.30,
            "Adaptive_OmegaFull": 0.10,
            "ExpectedValueMax": 0.20,
            "RiskAdjustedUtility": 0.20,
            "Faith": 0.10,
            "Drift": 0.10,
        },
    }

    if world_name == "normal":
        return {**base, "name": "Normal Earth"}

    elif world_name == "science_heavy":
        # Science develops earlier, faster; religion weaker
        return {
            **base,
            "name": "Science-Heavy",
            "tech_acceleration": 1.5,
            "tech_inflection_year": 1700,  # 168 years earlier
            "religion_strength": 0.2,
            "faith_shock_buffer": 0.04,
            "default_strategy_dist": {
                "NRMO_vNext": 0.40, "Adaptive_OmegaFull": 0.15,
                "ExpectedValueMax": 0.25, "RiskAdjustedUtility": 0.10,
                "Faith": 0.02, "Drift": 0.08,
            },
        }

    elif world_name == "religion_heavy":
        # Religion is dominant, science suppressed
        return {
            **base,
            "name": "Religion-Heavy",
            "tech_acceleration": 0.6,
            "tech_inflection_year": 2050,  # never reaches modern in our window
            "religion_strength": 0.9,
            "faith_shock_buffer": 0.20,
            "default_strategy_dist": {
                "NRMO_vNext": 0.10, "Adaptive_OmegaFull": 0.05,
                "ExpectedValueMax": 0.10, "RiskAdjustedUtility": 0.10,
                "Faith": 0.40, "Drift": 0.25,
            },
        }

    elif world_name == "mix":
        # Both science AND religion strong
        return {
            **base,
            "name": "Sci-Religion-Mix",
            "tech_acceleration": 1.2,
            "tech_inflection_year": 1750,
            "religion_strength": 0.7,
            "faith_shock_buffer": 0.15,
            "default_strategy_dist": {
                "NRMO_vNext": 0.25, "Adaptive_OmegaFull": 0.15,
                "ExpectedValueMax": 0.15, "RiskAdjustedUtility": 0.15,
                "Faith": 0.20, "Drift": 0.10,
            },
        }

    elif world_name == "accelerated_tech":
        # Industrial revolution 300 years earlier
        return {
            **base,
            "name": "Accelerated-Tech",
            "tech_acceleration": 2.0,
            "tech_inflection_year": 1500,
            "religion_strength": 0.3,
            "faith_shock_buffer": 0.05,
            "default_strategy_dist": {
                "NRMO_vNext": 0.35, "Adaptive_OmegaFull": 0.20,
                "ExpectedValueMax": 0.30, "RiskAdjustedUtility": 0.05,
                "Faith": 0.02, "Drift": 0.08,
            },
        }

    elif world_name == "unknown_encounter":
        # Mysterious external contact happens around year 1500
        # Adds tail probability spike + new tech catalyst
        cfg = {
            **base,
            "name": "Unknown-Encounter",
            "tech_acceleration": 1.3,
            "tech_inflection_year": 1500,  # external knowledge transfer
            "religion_strength": 0.6,
            "faith_shock_buffer": 0.12,
            "encounter_year_window": (1480, 1520),
            "encounter_shock": 0.15,
            "default_strategy_dist": {
                "NRMO_vNext": 0.30, "Adaptive_OmegaFull": 0.15,
                "ExpectedValueMax": 0.20, "RiskAdjustedUtility": 0.15,
                "Faith": 0.10, "Drift": 0.10,
            },
        }
        # Add encounter as a shock
        cfg["shocks"] = base["shocks"] + [("unknown_encounter", 1480, 1520, 0.15)]
        return cfg

    else:
        raise ValueError(f"Unknown world: {world_name}")


# ============================================================
# RANDOM EVENT CATALOG
# ============================================================

RANDOM_EVENTS = [
    # (label, year_start, year_end, base_prob_per_year, magnitude, affected_dim)
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
    """Sample which random events occur in this run."""
    events = []
    for ev in RANDOM_EVENTS:
        label, ys, ye, prob_per_year, mag, dim = ev
        if ye < year_start or ys > year_end:
            continue
        # Window overlap with this run
        overlap_start = max(ys, year_start)
        overlap_end = min(ye, year_end)
        years_in_window = overlap_end - overlap_start
        # Probability of occurring at all in window (geometric)
        p_occur = 1 - (1 - prob_per_year) ** max(1, years_in_window)
        if rng.random() < p_occur:
            # Sample year of occurrence within window
            yr = int(rng.uniform(overlap_start, overlap_end))
            events.append({
                "label": label, "year": yr, "magnitude": mag, "dim": dim,
            })
    return sorted(events, key=lambda e: e["year"])


# ============================================================
# DECISION THEORIES (Plugin-style)
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


def theory_faith(n, R, E, G, O, K, X, rng, world_cfg):
    """Faith-based: low growth, high safeguards (trust in providence),
    moderate distribution (community / charity), low learning."""
    a = np.tile(np.array([0.15, 0.45, 0.10, 0.30]), (n, 1))
    return normalize_action(a)


def theory_drift(n, R, E, G, O, K, X, rng, world_cfg):
    """Drift baseline: returns zero action effects (handled by bypass flag)."""
    return np.tile(np.array([0.18, 0.30, 0.22, 0.30]), (n, 1))


THEORIES = {
    "ExpectedValueMax":     (theory_evmax, False),
    "RiskAdjustedUtility":  (theory_riskadj, False),
    "NRMO_vNext":           (theory_nrmo_vnext, False),
    "Adaptive_OmegaFull":   (theory_omega_full, False),
    "Faith":                (theory_faith, False),
    "Drift":                (theory_drift, True),  # bypass agency
}


# ============================================================
# CONSTANTS (from v4.1)
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

TERM_JP = {"lineage_absorbed_or_lost": "lineage_lost",
           "rural_farm_part_time_farm": "rural_farm",
           "craft_trade_self_employed": "craft_trade",
           "company_skilled_clerical": "company_clerical",
           "urban_wage_labor": "urban_wage",
           "education_public_clerical": "education_public",
           "professional_manager_owner": "professional"}


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
    """Run one simulation in a given world with mixed strategy population."""
    rng = np.random.default_rng(seed)
    eras = world_cfg["eras"]
    shocks = world_cfg["shocks"]
    tech_accel = world_cfg["tech_acceleration"]
    tech_inflection = world_cfg["tech_inflection_year"]
    religion_strength = world_cfg["religion_strength"]
    faith_buffer = world_cfg["faith_shock_buffer"]

    # Sample random events for this run
    events = sample_random_events(rng, 0, 2020, world_cfg)
    if verbose:
        print(f"  World: {world_cfg['name']}")
        print(f"  Random events sampled: {len(events)}")
        for e in events:
            print(f"    Year {e['year']}: {e['label']} (mag={e['magnitude']:.2f}, {e['dim']})")

    # Strategy distribution
    sd = strategy_dist or world_cfg["default_strategy_dist"]
    strategy_names = list(sd.keys())
    strategy_probs = np.array(list(sd.values()))
    strategy_probs = strategy_probs / strategy_probs.sum()
    agent_strategy = rng.choice(len(strategy_names), size=n, p=strategy_probs)

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

    # Spotlight: track one specific agent's life
    spotlight_chronicle = [{
        "generation": 0, "year": 0, "alive": True,
        "occupation": OCC[occ[spotlight_idx]],
        "region": REGIONS[region[spotlight_idx]],
        "fk": float(fk[spotlight_idx]), "edu": float(edu[spotlight_idx]),
        "inst": float(inst[spotlight_idx]), "trade": float(trade[spotlight_idx]),
        "assets": float(assets[spotlight_idx]), "urban": float(urban[spotlight_idx]),
        "strategy": strategy_names[agent_strategy[spotlight_idx]],
    }]

    event_log = []  # narrative log

    for gen in range(1, 51):
        year = (gen - 1) * 40
        ei = era_idx_for_year(year, eras)
        era_name, _, _, base_fail, collat_success = eras[ei]
        shock_add, shock_label = shock_for_year(year, shocks)

        # Apply random events impacting this generation's window
        gen_events = [e for e in events if year <= e["year"] < year + 40]
        for ev in gen_events:
            if ev["dim"] in ("epidemic_severe", "epidemic_mild", "war_severe"):
                shock_add += ev["magnitude"]
            elif ev["dim"] in ("agriculture_decline", "regional_destruction"):
                shock_add += ev["magnitude"] * 0.7
            event_log.append(ev)

        active = ~absorbed
        idx = np.where(active)[0]
        if len(idx) == 0:
            break

        # Compute per-agent action by strategy
        R_a, E_a, G_a, O_a, K_a, X_a = state_to_nrmo_norm(
            fk[idx], edu[idx], inst[idx], trade[idx], assets[idx], urban[idx], shock_add)
        action = np.zeros((len(idx), 4))
        for s, sname in enumerate(strategy_names):
            mask = agent_strategy[idx] == s
            if not mask.any():
                continue
            theory_fn, bypass = THEORIES[sname]
            sub_action = theory_fn(int(mask.sum()),
                                    R_a[mask], E_a[mask], G_a[mask],
                                    O_a[mask], K_a[mask], X_a[mask],
                                    rng, world_cfg)
            if bypass:
                sub_action = np.zeros_like(sub_action)
            action[mask] = sub_action

        g_a = action[:, 0]; s_a = action[:, 1]; l_a = action[:, 2]; d_a = action[:, 3]

        # Direct failure probability (with Faith buffer)
        dfp = base_fail + shock_add - .030 * assets[idx] - .025 * inst[idx] - .020 * edu[idx]
        dfp *= (1 - 0.45 * s_a)
        dfp *= (1 - 0.10 * l_a)
        dfp += g_a * shock_add * 0.45
        # Faith provides additional buffer (proportional to religion_strength)
        faith_mask = (agent_strategy[idx] == strategy_names.index("Faith")) \
                     if "Faith" in strategy_names else np.zeros(len(idx), dtype=bool)
        dfp[faith_mask] *= (1 - faith_buffer * religion_strength)
        dfp = np.clip(dfp, .015, .42)

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
                cprob = np.clip(cprob_base * (1 + 0.20 * d_fail), 0.0, 0.999)
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

            # Tech acceleration affects edu/inst gain
            tech_factor = tech_accel if year >= tech_inflection else 1.0
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

            edu[survivors] = np.clip(edu[survivors] * .985 + eg + rng.normal(0, .006, size=len(survivors)), 0, 1)
            inst[survivors] = np.clip(inst[survivors] * .990 + ig + rng.normal(0, .005, size=len(survivors)), 0, 1)
            trade[survivors] = np.clip(trade[survivors] * .990 + tg + rng.normal(0, .006, size=len(survivors)), 0, 1)
            assets[survivors] = np.clip(assets[survivors] * .988 + ag + rng.normal(0, .010, size=len(survivors)), 0, 1)
            urban[survivors] = np.clip(urban[survivors] * .990 + ug + rng.normal(0, .006, size=len(survivors)), 0, 1)
            if shock_add > 0:
                shock_buf = (1 - 0.30 * s_s)
                assets[survivors] = np.clip(
                    assets[survivors] - rng.uniform(0, shock_add * .6, size=len(survivors)) * shock_buf, 0, 1)
                fk[survivors] = np.clip(
                    fk[survivors] - rng.uniform(0, shock_add * .25, size=len(survivors)) * shock_buf, 0, 1)
        completed_gen[idx] = gen

        # Spotlight chronicle (only if alive)
        if not absorbed[spotlight_idx]:
            spotlight_chronicle.append({
                "generation": gen, "year": year + 40,
                "alive": True,
                "occupation": OCC[occ[spotlight_idx]],
                "region": REGIONS[region[spotlight_idx]],
                "fk": float(fk[spotlight_idx]), "edu": float(edu[spotlight_idx]),
                "inst": float(inst[spotlight_idx]), "trade": float(trade[spotlight_idx]),
                "assets": float(assets[spotlight_idx]), "urban": float(urban[spotlight_idx]),
                "strategy": strategy_names[agent_strategy[spotlight_idx]],
                "events_this_gen": [e["label"] for e in gen_events],
            })
        else:
            if not spotlight_chronicle or spotlight_chronicle[-1].get("alive", True):
                spotlight_chronicle.append({
                    "generation": gen, "year": year + 40,
                    "alive": False, "ruin_cause": "absorbed_or_lost",
                })

    # Aggregate results
    term = terminal_category_vec(occ, fk, edu, inst, trade, assets, urban, absorbed)
    n_continued = int((~absorbed).sum())
    p_continued = float((~absorbed).mean())

    # Per-strategy stats (composite ranking within world)
    per_strategy = {}
    for s, sname in enumerate(strategy_names):
        mask = agent_strategy == s
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
        }

    # Endpoint distribution overall
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
        "spotlight_chronicle": spotlight_chronicle,
        "spotlight_strategy": strategy_names[agent_strategy[spotlight_idx]],
        "spotlight_initial_region": REGIONS[initial_region[spotlight_idx]],
    }


def composite_score(per_strategy_stats):
    return (1.0 * per_strategy_stats["p_continued"]
          + 1.5 * per_strategy_stats["p_professional"]
          + 1.0 * per_strategy_stats["p_edu_public"]
          + 0.4 * per_strategy_stats["p_company"]
          - 0.3 * per_strategy_stats["p_rural_farm"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="normal", help="normal, science_heavy, religion_heavy, mix, accelerated_tech, unknown_encounter")
    ap.add_argument("--n", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=20260506)
    ap.add_argument("--all_worlds", action="store_true")
    ap.add_argument("--outdir", default="outputs")
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
        print(f"\n{'='*70}")
        print(f"Running world: {cfg['name']}  (n={args.n})")
        print('='*70)
        t0 = time.time()
        res = run_world(cfg, n=args.n, seed=args.seed, verbose=True)
        rt = time.time() - t0
        print(f"\n  Runtime: {rt:.1f}s, continuation rate: {res['p_continued']*100:.2f}%")

        # Per-strategy ranking within this world
        print(f"\n  Per-Strategy Composite Score Ranking:")
        rows = []
        for sname, stats in res["per_strategy"].items():
            score = composite_score(stats)
            rows.append((sname, stats["n"], stats["p_continued"]*100,
                        (stats["p_professional"] + stats["p_edu_public"])*100, score))
        rows.sort(key=lambda x: -x[4])
        for r, row in enumerate(rows, 1):
            print(f"    {r}. {row[0]:<25} n={row[1]:>6}  cont={row[2]:>5.2f}%  upward={row[3]:>5.2f}%  composite={row[4]:.4f}")

        all_results[w] = res

    # Save
    with open(out / "all_world_results.json", "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

    # Cross-world strategy comparison table
    if len(worlds) > 1:
        print(f"\n\n{'='*100}")
        print(f"CROSS-WORLD STRATEGY COMPARISON (composite score)")
        print('='*100)
        all_strategies = set()
        for r in all_results.values():
            all_strategies.update(r["per_strategy"].keys())
        all_strategies = sorted(all_strategies)
        header = f"  {'Strategy':<25}" + "".join(f"{r[:18]:>20}" for r in [all_results[w]['world_name'] for w in worlds])
        print(header)
        cross_rows = []
        for s in all_strategies:
            scores = []
            for w in worlds:
                if s in all_results[w]["per_strategy"]:
                    scores.append(composite_score(all_results[w]["per_strategy"][s]))
                else:
                    scores.append(None)
            cross_rows.append((s, scores))
            line = f"  {s:<25}"
            for sc in scores:
                line += f"{sc:>20.4f}" if sc is not None else f"{'-':>20}"
            print(line)

        # Save as CSV
        cross_data = {"strategy": [r[0] for r in cross_rows]}
        for i, w in enumerate(worlds):
            cross_data[all_results[w]["world_name"]] = [r[1][i] for r in cross_rows]
        df_cross = pd.DataFrame(cross_data)
        df_cross.to_csv(out / "cross_world_comparison.csv", index=False)

    # Spotlight chronicle (first world only)
    spot = all_results[worlds[0]]["spotlight_chronicle"]
    print(f"\n\n{'='*100}")
    print(f"SPOTLIGHT LIFE CHRONICLE  (Strategy: {all_results[worlds[0]]['spotlight_strategy']})")
    print('='*100)
    for entry in spot:
        if entry.get("alive", True):
            occ_label = entry.get("occupation", "n/a")
            region_label = entry.get("region", "n/a")
            edu_v = entry.get("edu", 0); assets_v = entry.get("assets", 0)
            evts = entry.get("events_this_gen", [])
            print(f"  Gen {entry['generation']:>2} (Year {entry['year']:>4}): {region_label:<15} {occ_label:<25} edu={edu_v:.3f} assets={assets_v:.3f}", end="")
            if evts:
                print(f"  Events: {', '.join(evts)}")
            else:
                print()
        else:
            print(f"  Gen {entry['generation']:>2} (Year {entry['year']:>4}): LINEAGE LOST ({entry.get('ruin_cause', 'unknown')})")
            break


if __name__ == "__main__":
    main()
