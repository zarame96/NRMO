#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World Simulation v5.3 — 3000 Years Family Chronicle (Future-Extended)

Extends v5.2 to 75 generations × 40 years = 3000 years.
Adds 2 future eras:
- Future_AI_Era (2021-2500): tech_inflection_2 with AI revolution
- Future_Posthuman (2500-3000): high uncertainty, ahistorical-dominant

Honest caveats:
- Future era parameters are speculative (no historical calibration)
- No historical events after 2021; only ahistorical events
- tech_factor evolves under second inflection at 2050 (AI takeoff)
- religion_strength continues long-run secularisation

Usage:
    python world_sim_v5_3_3000years.py --world normal --n 30000
"""
import sys, json, time, argparse
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

# Import everything we need from v5.2
from world_sim_v5_2_spotlight import (
    REGION_MATS, _make_region_mat,
)
from world_sim_v5_1 import (
    get_world_config as get_world_config_base,
    RANDOM_EVENTS, FREQUENCY_MULTIPLIERS,
    REGIONS, OCC, INIT_REGION_PROBS, BASE_OCC,
    EDU_GAIN, INST_GAIN, TRADE_GAIN, ASSET_GAIN, URBAN_GAIN,
    THEORIES, era_idx_for_year, shock_for_year,
    weighted_choice_rows, terminal_category_vec,
    state_to_nrmo_norm, sample_random_events,
    update_religion_strength, religious_conflict_shock,
    faith_positive_dfp_modifier, faith_negative_dfp_modifier,
    faith_charismatic_tail_event, faith_collateral_modifier,
    faith_edu_gain_modifier, faith_shock_loss_modifier,
    composite_score,
)
from ahistorical_events import (
    sample_ahistorical_events, apply_ahistorical_event_effect,
    get_event_secondary_effects, AHISTORICAL_EVENTS,
)
from encounter_mechanism import (
    initial_intensity, evolve_intensity, apply_encounter_effects,
    get_encounter_summary,
)
from individual_chronicle import (
    record_decision_moment, render_life_chronicle, emotional_arc_summary,
)
from family_lineage import (
    DEFAULT_FAMILY_CONFIG, select_family_branches,
    render_family_chronicle, render_family_tree_ascii,
)
from civilisation_trajectory import (
    record_civilisation_snapshot, render_civilisation_chronicle,
    snapshots_to_dataframe,
)

# ============================================================
# 3000-YEAR ERA EXTENSION
# ============================================================

# Future eras: speculative parameters
FUTURE_ERAS_EXTRA = [
    # (label, year_start, year_end, base_fail, collateral_success)
    ("Future_AI_Era",       2021, 2500, 0.03, 0.985),
    ("Future_Posthuman",    2500, 3001, 0.05, 0.975),  # higher uncertainty
]

# Region matrices for future eras (very high mobility)
FUTURE_REGION_MATS_EXTRA = [
    _make_region_mat(0.65),  # AI era: ultra-mobile
    _make_region_mat(0.55),  # Posthuman: maximally fluid
]

# Future-specific ahistorical events (additional, AI/posthuman flavor)
FUTURE_AHISTORICAL_EVENTS_EXTRA = [
    ("AI_Singularity",       2030, 2500, 0.0010, 0.30, "tech_unknown",
     "Artificial general intelligence transition; profound social disruption"),
    ("Climate_Tipping",      2030, 2200, 0.0020, 0.25, "climate_collapse",
     "Major climate tipping point: ice sheet, AMOC, Amazon dieback"),
    ("Genetic_Engineering",  2050, 2500, 0.0015, 0.18, "biological_break",
     "Human genetic enhancement; biological speciation pressure"),
    ("Space_Colonization",   2080, 3001, 0.0008, 0.15, "horizon_expansion",
     "Off-world colonization viable; resource expansion"),
    ("Consciousness_Upload", 2150, 3001, 0.0005, 0.30, "biological_break",
     "Consciousness substrate transition; biological lineage redefinition"),
    ("Resource_Depletion",   2030, 2300, 0.0015, 0.20, "resource_shock",
     "Critical material exhaustion; civilization-shaking shortage"),
    ("Pandemic_Engineered",  2030, 2500, 0.0012, 0.32, "epidemic_unprecedented",
     "Bioengineered pathogen escape (deliberate or accidental)"),
    ("Quantum_Internet",     2050, 2500, 0.0008, 0.10, "tech_unknown",
     "Quantum communication network; new informational topology"),
    ("Mass_Migration_Climate", 2050, 2300, 0.0020, 0.18, "global_disruption",
     "Climate-driven mass migration; political restructuring"),
    ("Posthuman_Transition", 2400, 3001, 0.0010, 0.40, "biological_break",
     "Definitive split between biological and posthuman lineages"),
]


def get_world_config_3000(world_name):
    """Get world config and extend with future eras."""
    cfg = get_world_config_base(world_name)
    # Extend eras
    cfg["eras"] = list(cfg["eras"]) + FUTURE_ERAS_EXTRA
    # Note: existing shocks list is unchanged (no historical shocks
    # extend beyond 2021); future shocks come from ahistorical events.
    return cfg


def get_extended_region_mats():
    """Return region matrices including future eras."""
    return REGION_MATS + FUTURE_REGION_MATS_EXTRA


def sample_ahistorical_events_3000(rng, year_start, year_end,
                                     frequency_multiplier=1.0, world_cfg=None):
    """Sample ahistorical events including future-specific catalog."""
    # Use base catalog
    events = sample_ahistorical_events(
        rng, year_start, year_end, frequency_multiplier, world_cfg)

    # Add future-specific events
    for ev in FUTURE_AHISTORICAL_EVENTS_EXTRA:
        label, ys, ye, prob_per_year, mag, dim, desc = ev
        if ye < year_start or ys > year_end:
            continue
        overlap_start = max(ys, year_start)
        overlap_end = min(ye, year_end)
        years_in_window = overlap_end - overlap_start
        adjusted_prob = prob_per_year * frequency_multiplier
        p_occur = 1 - (1 - adjusted_prob) ** max(1, years_in_window)
        if rng.random() < p_occur:
            yr = int(rng.uniform(overlap_start, overlap_end))
            events.append({
                "label": label, "year": yr, "magnitude": mag,
                "dim": dim, "description": desc, "type": "ahistorical_future",
            })
    return sorted(events, key=lambda e: e["year"])


def era_idx_for_year_3000(y, eras):
    """Era index lookup, supporting 75-generation eras."""
    for i, e in enumerate(eras):
        if e[1] <= y < e[2]:
            return i
    return len(eras) - 1


def shock_for_year_3000(y, shocks):
    """Historical shocks only fire ≤ 2021. Future shocks come from events."""
    add = 0.0
    labels = []
    for sh in shocks:
        if sh[1] <= y < sh[2]:
            add += sh[3]
            labels.append(sh[0])
    return add, ";".join(labels)


def update_religion_strength_3000(current_rs, shock_add, tech_factor,
                                    gen_random_events, militant_share,
                                    year, world_cfg):
    """Long-run secularisation continues; AI era accelerates it."""
    new_rs = update_religion_strength(current_rs, shock_add, tech_factor,
                                        gen_random_events, militant_share,
                                        year, world_cfg)
    # Additional effect: post-2050 AI era accelerates secularisation
    if year >= 2050:
        new_rs -= 0.008
    if year >= 2400:
        # Posthuman: religion may resurge OR collapse depending on world
        # Random fluctuation
        new_rs += np.random.default_rng(year).uniform(-0.005, 0.005)
    return max(0.05, min(0.99, new_rs))


# ============================================================
# Main 3000-year simulation
# ============================================================

def run_world_3000(world_cfg, n=30000, seed=20260507,
                    frequency_mode="sporadic", enable_ahistorical=True,
                    encounter_year_window=None, family_config=None,
                    n_generations=75, verbose=True):
    """Run a 3000-year (75 gen × 40 yr) world simulation with spotlight."""
    rng = np.random.default_rng(seed)
    eras = world_cfg["eras"]
    shocks = world_cfg["shocks"]
    tech_accel = world_cfg["tech_acceleration"]
    tech_inflection = world_cfg["tech_inflection_year"]
    religion_strength = world_cfg["religion_strength_initial"]
    faith_subdist = world_cfg["faith_subdist"]

    region_mats = get_extended_region_mats()

    freq_mult = FREQUENCY_MULTIPLIERS.get(frequency_mode, 1.0)

    # === Sample events (historical capped at 2021, ahistorical extends to 3000) ===
    # Historical events (only up to 2021)
    events_h = []
    for ev_def in RANDOM_EVENTS:
        label, ys, ye, prob_per_year, mag, dim = ev_def
        # Historical events are capped at 2021
        adj_prob = prob_per_year * freq_mult
        years_in_window = max(1, ye - ys)
        p_occur = 1 - (1 - adj_prob) ** years_in_window
        if rng.random() < p_occur:
            yr = int(rng.uniform(ys, ye))
            events_h.append({"label": label, "year": yr, "magnitude": mag,
                             "dim": dim, "type": "historical"})
    events_h = sorted(events_h, key=lambda e: e["year"])

    # Ahistorical events including future catalog
    events_a = []
    if enable_ahistorical:
        events_a = sample_ahistorical_events_3000(
            rng, 0, 3000, frequency_multiplier=freq_mult, world_cfg=world_cfg)

    all_events = sorted(events_h + events_a, key=lambda e: e["year"])

    encounter_active = False
    encounter_year = None
    encounter_intensity = None
    if encounter_year_window is not None:
        ews, ewe = encounter_year_window
        encounter_year = int(rng.uniform(ews, ewe))
        encounter_active = True
        encounter_intensity = initial_intensity()

    # === Strategy distribution ===
    sd_input = world_cfg["default_strategy_dist"]
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
    strategy_faith_class = []
    for sname in strategy_names:
        _, _, fc = THEORIES[sname]
        strategy_faith_class.append(fc)

    # === Initial state ===
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

    # === SPOTLIGHT setup ===
    nrmo_idx = strategy_names.index("NRMO_vNext") if "NRMO_vNext" in strategy_names else 0
    candidate = np.where(agent_strategy == nrmo_idx)[0]
    spotlight_idx = int(candidate[0]) if len(candidate) > 0 else 0
    individual_chronicle = []

    family_members, family_region = select_family_branches(
        rng, agent_strategy, strategy_names, region, occ,
        n_branches=4, family_config=family_config or DEFAULT_FAMILY_CONFIG)
    family_chronicles = {role: [] for role in family_members.keys()}
    civ_snapshots = []

    if verbose:
        print(f"  World: {world_cfg['name']}")
        print(f"  Frequency: {frequency_mode}")
        print(f"  Generations: {n_generations} ({n_generations * 40} years)")
        print(f"  Eras (incl. future): {[e[0] for e in eras]}")
        print(f"  Spotlight: idx {spotlight_idx} ({strategy_names[agent_strategy[spotlight_idx]]}, "
              f"{REGIONS[region[spotlight_idx]]})")
        print(f"  Family branches: {len(family_members)} in {REGIONS[family_region]}")
        print(f"  Historical events sampled: {len(events_h)}")
        print(f"  Ahistorical events sampled: {len(events_a)} (incl. future catalog)")
        if encounter_active:
            print(f"  Encounter scheduled: year {encounter_year}")

    event_log = []
    encounter_log = []
    religion_strength_log = []

    # === Main loop ===
    for gen in range(1, n_generations + 1):
        year = (gen - 1) * 40
        ei = era_idx_for_year_3000(year, eras)
        era_name, _, _, base_fail, collat_success = eras[ei]
        shock_add, _ = shock_for_year_3000(year, shocks)

        secondary = {
            "edu_multiplier_global": 1.0,
            "asset_random_loss_global": 0.0,
            "inst_random_delta_global": 0.0,
            "direct_mortality_p": 0.0,
            "edu_boost_global": 0.0,
            "inst_boost_global": 0.0,
            "trade_boost_global": 0.0,
        }

        gen_events = [e for e in all_events if year <= e["year"] < year + 40]
        for ev in gen_events:
            ev_type = ev.get("type", "historical")
            if ev_type in ("ahistorical", "ahistorical_future"):
                shock_add, tech_temp, religion_strength = apply_ahistorical_event_effect(
                    ev, shock_add, tech_accel, religion_strength, world_cfg, rng)
                if ev["dim"] in ("tech_collapse", "tech_unknown"):
                    tech_accel = tech_temp
                sec = get_event_secondary_effects(ev)
                if "edu_multiplier" in sec:
                    secondary["edu_multiplier_global"] *= sec["edu_multiplier"]
                if "asset_random_loss" in sec:
                    secondary["asset_random_loss_global"] += sec["asset_random_loss"]
                if "inst_random_delta" in sec:
                    secondary["inst_random_delta_global"] += sec["inst_random_delta"]
                if "direct_mortality_p" in sec:
                    secondary["direct_mortality_p"] = max(
                        secondary["direct_mortality_p"], sec["direct_mortality_p"])
                if "asset_lottery" in sec:
                    secondary["asset_random_loss_global"] += sec["asset_lottery"] * 0.5
            else:
                if ev["dim"] in ("epidemic_severe", "epidemic_mild", "war_severe"):
                    shock_add += ev["magnitude"]
                elif ev["dim"] in ("agriculture_decline", "regional_destruction"):
                    shock_add += ev["magnitude"] * 0.7
            event_log.append(ev)

        # Encounter
        if encounter_active and encounter_year is not None and year >= encounter_year:
            generations_since = (year - encounter_year) // 40
            encounter_intensity = evolve_intensity(rng, encounter_intensity, generations_since)
            shock_add, tech_accel, religion_strength, enc_sec = apply_encounter_effects(
                encounter_intensity, 0.15, shock_add, tech_accel,
                religion_strength, rng)
            secondary["edu_boost_global"] += enc_sec["edu_boost"]
            secondary["inst_boost_global"] += enc_sec["inst_boost"]
            secondary["trade_boost_global"] += enc_sec["trade_boost"]
            secondary["direct_mortality_p"] = max(
                secondary["direct_mortality_p"], enc_sec["direct_mortality_p"])
            encounter_log.append({
                "year": year, "intensity": encounter_intensity,
                "generations_since": generations_since,
            })

        active = ~absorbed
        idx = np.where(active)[0]
        if len(idx) == 0:
            break

        # Religious conflict
        militant_count = 0
        for s_idx, sname in enumerate(strategy_names):
            if strategy_faith_class[s_idx] == "militant":
                militant_count += int(((agent_strategy == s_idx) & active).sum())
        militant_share = militant_count / max(active.sum(), 1)
        rel_conflict = religious_conflict_shock(rng, militant_share,
                                                  religion_strength, year, ei)
        if rel_conflict > 0:
            shock_add += rel_conflict

        # Tech: 2nd inflection at AI era
        if year >= 2050:
            # AI revolution: additional tech acceleration
            tech_factor = tech_accel * 1.5
        elif year >= tech_inflection:
            tech_factor = tech_accel
        else:
            tech_factor = 1.0

        religion_strength = update_religion_strength_3000(
            religion_strength, shock_add, tech_factor, gen_events,
            militant_share, year, world_cfg)
        religion_strength_log.append({"year": year, "rs": religion_strength,
                                       "militant_share": militant_share})

        # Compute actions
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

        # Spotlight pre-state
        prev_individual_state = None
        if not absorbed[spotlight_idx]:
            local_pos = np.where(idx == spotlight_idx)[0]
            if len(local_pos) > 0:
                prev_individual_state = {
                    "occupation": OCC[occ[spotlight_idx]],
                    "region": REGIONS[region[spotlight_idx]],
                    "edu": edu[spotlight_idx],
                    "assets": assets[spotlight_idx],
                    "fk": fk[spotlight_idx],
                    "inst": inst[spotlight_idx],
                    "strategy": strategy_names[agent_strategy[spotlight_idx]],
                }

        # DFP
        dfp = base_fail + shock_add - .030 * assets[idx] - .025 * inst[idx] - .020 * edu[idx]
        dfp *= (1 - 0.45 * s_a)
        dfp *= (1 - 0.10 * l_a)
        dfp += g_a * shock_add * 0.45

        for s_idx, sname in enumerate(strategy_names):
            fc = strategy_faith_class[s_idx]
            if fc is None:
                continue
            mask = agent_strategy[idx] == s_idx
            if not mask.any():
                continue
            pos_mod = faith_positive_dfp_modifier(fc, religion_strength)
            neg_mod = faith_negative_dfp_modifier(fc, religion_strength, ei)
            dfp[mask] *= pos_mod * neg_mod

        for s_idx, sname in enumerate(strategy_names):
            if strategy_faith_class[s_idx] == "charismatic":
                mask = agent_strategy[idx] == s_idx
                if not mask.any():
                    continue
                tail_lost = faith_charismatic_tail_event(rng, int(mask.sum()),
                                                          religion_strength)
                if tail_lost.any():
                    sub_idx = idx[mask]
                    forced_lost = sub_idx[tail_lost]
                    dfp[np.isin(idx, forced_lost)] = 1.0

        dfp = np.clip(dfp, .015, .85)
        if secondary["direct_mortality_p"] > 0:
            dfp = np.clip(dfp + secondary["direct_mortality_p"], .015, .98)

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

        # Survivor state update
        survivors = idx[~absorbed[idx]]
        if len(survivors):
            mat_e = region_mats[ei]
            new_region = region[survivors].copy()
            for ri in range(len(REGIONS)):
                sub = survivors[region[survivors] == ri]
                if len(sub) == 0:
                    continue
                probs = np.tile(mat_e[ri], (len(sub), 1))
                if year >= 1600:
                    mobile = np.isin(occ[sub], [5, 6, 7, 8, 9, 10])
                    if mobile.any():
                        probs[mobile, 4] += .03; probs[mobile, 1] += .02
                        probs[mobile, ri] = np.maximum(0, probs[mobile, ri] - .05)
                        probs[mobile] = probs[mobile] / probs[mobile].sum(axis=1, keepdims=True)
                new_region[region[survivors] == ri] = weighted_choice_rows(probs, rng)
            region[survivors] = new_region

            surv_local_idx = np.where(~absorbed[idx])[0]
            g_s = g_a[surv_local_idx]; s_s = s_a[surv_local_idx]
            l_s = l_a[surv_local_idx]; d_s = d_a[surv_local_idx]

            # Use last era index for occupation scoring (Postwar baseline for future)
            scoring_ei = min(ei, 6)
            scores = np.tile(BASE_OCC[scoring_ei], (len(survivors), 1)).astype(float)
            central = np.isin(region[survivors], [1, 2, 3])
            urban_bias = urban[survivors] + central * .08
            scores[:, 1] += .06 * assets[survivors]
            scores[:, 2] += .12 * edu[survivors] + .08 * inst[survivors] + ((scoring_ei in [1, 2]) * central * .04)
            if scoring_ei == 3:
                scores[:, 3] += .06 * assets[survivors]
            scores[:, 4] += .06 * trade[survivors]
            scores[:, 5] += .10 * trade[survivors] + .04 * assets[survivors]
            scores[:, 6] += .04 * urban_bias
            if scoring_ei >= 5:
                scores[:, 7] += .10 * urban_bias
                scores[:, 8] += .14 * edu[survivors] + .05 * inst[survivors]
                scores[:, 10] += .10 * edu[survivors] + .08 * assets[survivors] + .05 * inst[survivors]
            if scoring_ei >= 4:
                scores[:, 9] += .11 * edu[survivors] + .06 * inst[survivors]
            scores[np.arange(len(survivors)), occ[survivors]] += .18

            scores[:, 1] += 0.04 * g_s; scores[:, 4] += 0.06 * g_s
            scores[:, 5] += 0.08 * g_s; scores[:, 9] += 0.10 * l_s
            scores[:, 10] += 0.08 * l_s; scores[:, 8] += 0.06 * (l_s + g_s)
            scores[:, 7] += 0.04 * urban_bias * (1 + 0.3 * g_s)

            occ[survivors] = weighted_choice_rows(
                scores / scores.sum(axis=1, keepdims=True), rng)

            direct_surv = np.isin(survivors, direct_global)
            collateral_surv = np.isin(survivors, collateral_reset_global) \
                if len(collateral_reset_global) else np.zeros(len(survivors), bool)
            transfer = np.zeros(len(survivors))
            transfer[direct_surv] = np.minimum(
                .30, .10 + .10 * edu[survivors][direct_surv]
                + .06 * inst[survivors][direct_surv]
                + .04 * assets[survivors][direct_surv])
            if collateral_surv.any():
                transfer[collateral_surv] = rng.uniform(.01, .03, size=collateral_surv.sum())

            old_fk = fk[survivors]; new_fk = old_fk.copy()
            new_fk[direct_surv] = np.clip(
                old_fk[direct_surv] * (.70 + transfer[direct_surv] * .25)
                + transfer[direct_surv] * .20, 0, 1)
            new_fk[collateral_surv] = np.clip(
                old_fk[collateral_surv] * .08 + transfer[collateral_surv], 0, 1)
            fk[survivors] = new_fk

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
            # Future era: AI revolution boosts edu/inst more
            if year >= 2050:
                eg += .010
                inst[survivors] = np.clip(inst[survivors] + .003, 0, 1)

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

            eg += 0.020 * l_s; ig += 0.012 * d_s
            tg += 0.018 * g_s; ag += 0.025 * g_s - 0.005 * (l_s + d_s)
            ug += 0.012 * g_s * (year >= 1600)

            if secondary["edu_multiplier_global"] != 1.0:
                edu[survivors] = edu[survivors] * secondary["edu_multiplier_global"]
            if secondary["edu_boost_global"] > 0:
                eg = eg + secondary["edu_boost_global"]
            if secondary["inst_boost_global"] > 0:
                ig = ig + secondary["inst_boost_global"]
            if secondary["trade_boost_global"] > 0:
                tg = tg + secondary["trade_boost_global"]

            edu[survivors] = np.clip(edu[survivors] * .985 + eg + rng.normal(0, .006, size=len(survivors)), 0, 1)
            inst[survivors] = np.clip(inst[survivors] * .990 + ig + rng.normal(0, .005, size=len(survivors)), 0, 1)
            trade[survivors] = np.clip(trade[survivors] * .990 + tg + rng.normal(0, .006, size=len(survivors)), 0, 1)
            assets[survivors] = np.clip(assets[survivors] * .988 + ag + rng.normal(0, .010, size=len(survivors)), 0, 1)
            urban[survivors] = np.clip(urban[survivors] * .990 + ug + rng.normal(0, .006, size=len(survivors)), 0, 1)

            if secondary["asset_random_loss_global"] > 0:
                rand_loss_mag = secondary["asset_random_loss_global"]
                assets[survivors] = np.clip(
                    assets[survivors] - rng.uniform(-rand_loss_mag, rand_loss_mag,
                                                     size=len(survivors)), 0, 1)
            if secondary["inst_random_delta_global"] != 0:
                inst_delta = secondary["inst_random_delta_global"]
                inst[survivors] = np.clip(
                    inst[survivors] + rng.uniform(-inst_delta, inst_delta,
                                                   size=len(survivors)), 0, 1)

            if shock_add > 0:
                shock_buf = (1 - 0.30 * s_s)
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

        # === SPOTLIGHT recording ===
        spotlight_state_now = {
            "occupation": OCC[occ[spotlight_idx]],
            "region": REGIONS[region[spotlight_idx]],
            "edu": edu[spotlight_idx],
            "assets": assets[spotlight_idx],
            "fk": fk[spotlight_idx],
            "inst": inst[spotlight_idx],
            "strategy": strategy_names[agent_strategy[spotlight_idx]],
            "absorbed": bool(absorbed[spotlight_idx]),
        }
        try:
            spotlight_action = (float(g_a[np.where(idx == spotlight_idx)[0][0]]),
                                 float(s_a[np.where(idx == spotlight_idx)[0][0]]),
                                 float(l_a[np.where(idx == spotlight_idx)[0][0]]),
                                 float(d_a[np.where(idx == spotlight_idx)[0][0]]))
        except IndexError:
            spotlight_action = (0.0, 0.0, 0.0, 0.0)

        record_decision_moment(individual_chronicle, gen, year + 40,
                                spotlight_state_now, spotlight_action,
                                prev_individual_state, gen_events,
                                encounter_active and encounter_intensity is not None)

        for role, idx_g in family_members.items():
            prev_fam_state = None
            if family_chronicles[role]:
                prev_fam_state = {
                    "occupation": family_chronicles[role][-1]["occupation"],
                    "region": family_chronicles[role][-1]["region"],
                    "edu": family_chronicles[role][-1]["edu"],
                    "assets": family_chronicles[role][-1]["assets"],
                    "fk": family_chronicles[role][-1]["family_knowledge"],
                    "inst": family_chronicles[role][-1]["inst"],
                    "strategy": family_chronicles[role][-1]["strategy"],
                }
            fam_state = {
                "occupation": OCC[occ[idx_g]],
                "region": REGIONS[region[idx_g]],
                "edu": edu[idx_g],
                "assets": assets[idx_g],
                "fk": fk[idx_g],
                "inst": inst[idx_g],
                "strategy": strategy_names[agent_strategy[idx_g]],
                "absorbed": bool(absorbed[idx_g]),
            }
            try:
                fam_action = (float(g_a[np.where(idx == idx_g)[0][0]]),
                              float(s_a[np.where(idx == idx_g)[0][0]]),
                              float(l_a[np.where(idx == idx_g)[0][0]]),
                              float(d_a[np.where(idx == idx_g)[0][0]]))
            except IndexError:
                fam_action = (0.0, 0.0, 0.0, 0.0)
            record_decision_moment(family_chronicles[role], gen, year + 40,
                                    fam_state, fam_action, prev_fam_state,
                                    gen_events,
                                    encounter_active and encounter_intensity is not None)

        active_count = int((~absorbed).sum())
        if active_count > 0:
            active_mask = ~absorbed
            record_civilisation_snapshot(
                civ_snapshots, gen, year + 40, era_name,
                active_count, n,
                fk[active_mask], edu[active_mask], inst[active_mask],
                trade[active_mask], assets[active_mask], urban[active_mask],
                agent_strategy[active_mask], strategy_names,
                religion_strength, tech_factor,
                shock_add, gen_events,
                encounter_active and encounter_intensity is not None
            )
        else:
            civ_snapshots.append({
                "generation": gen, "year": year + 40, "era": era_name,
                "alive": False, "extinct": True,
            })

    term = terminal_category_vec(occ, fk, edu, inst, trade, assets, urban, absorbed)
    for role, idx_g in family_members.items():
        if family_chronicles[role]:
            family_chronicles[role][-1]["terminal_category"] = term[idx_g]

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
            "faith_class": strategy_faith_class[s_idx],
        }

    return {
        "world_name": world_cfg["name"],
        "n_total": n,
        "n_generations": n_generations,
        "year_horizon": n_generations * 40,
        "p_continued": p_continued,
        "n_continued": n_continued,
        "per_strategy": per_strategy,
        "individual_chronicle": individual_chronicle,
        "family_chronicles": family_chronicles,
        "family_members": {k: int(v) for k, v in family_members.items()},
        "civ_snapshots": civ_snapshots,
        "encounter_log": encounter_log,
        "encounter_year": encounter_year,
        "events_occurred": event_log,
        "ahistorical_events_sampled": events_a,
        "religion_strength_log": religion_strength_log,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default="normal")
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--seed", type=int, default=20260507)
    ap.add_argument("--frequency", default="sporadic",
                    choices=["sporadic", "frequent", "sparse"])
    ap.add_argument("--encounter", action="store_true")
    ap.add_argument("--no_ahistorical", action="store_true")
    ap.add_argument("--n_generations", type=int, default=75,
                    help="Number of generations (75 = 3000 years default)")
    ap.add_argument("--outdir", default="outputs_v53")
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    cfg = get_world_config_3000(args.world)
    encounter_window = (1480, 1520) if (args.encounter or args.world == "unknown_encounter") else None

    print(f"\n{'='*70}\n3000-YEAR Family Chronicle: {cfg['name']}  "
          f"(n={args.n}, freq={args.frequency}, gens={args.n_generations})\n{'='*70}")
    t0 = time.time()
    res = run_world_3000(cfg, n=args.n, seed=args.seed,
                          frequency_mode=args.frequency,
                          enable_ahistorical=not args.no_ahistorical,
                          encounter_year_window=encounter_window,
                          n_generations=args.n_generations,
                          verbose=True)
    rt = time.time() - t0
    print(f"\n  Runtime: {rt:.1f}s, year horizon: {res['year_horizon']}, continuation: {res['p_continued']*100:.2f}%")

    individual_md = render_life_chronicle(
        res["individual_chronicle"], cfg["name"], res["n_total"])
    indiv_path = out / f"spotlight_individual_3000_{args.world}_{args.frequency}.md"
    indiv_path.write_text(individual_md, encoding="utf-8")

    family_md = render_family_chronicle(res["family_chronicles"],
                                          DEFAULT_FAMILY_CONFIG, cfg["name"])
    family_md += "\n\n## Family Tree Visualization\n\n"
    family_md += render_family_tree_ascii(res["family_chronicles"],
                                            DEFAULT_FAMILY_CONFIG)
    fam_path = out / f"spotlight_family_3000_{args.world}_{args.frequency}.md"
    fam_path.write_text(family_md, encoding="utf-8")

    civ_md = render_civilisation_chronicle(
        res["civ_snapshots"], cfg["name"], cfg,
        res["encounter_log"], res["ahistorical_events_sampled"])
    civ_path = out / f"spotlight_civilisation_3000_{args.world}_{args.frequency}.md"
    civ_path.write_text(civ_md, encoding="utf-8")

    df_civ = snapshots_to_dataframe(res["civ_snapshots"])
    csv_path = out / f"civilisation_trajectory_3000_{args.world}_{args.frequency}.csv"
    df_civ.to_csv(csv_path, index=False)

    n_branches_alive = sum(1 for r in res["family_chronicles"].values()
                            if r and r[-1].get("alive", True))
    emo_summary = emotional_arc_summary(res["individual_chronicle"])
    print(f"\n  Family branches surviving 3000 years: {n_branches_alive}/{len(res['family_chronicles'])}")
    print(f"  Individual emotional arc: dominant={emo_summary.get('dominant_emotion', 'n/a')}, "
          f"max intensity={emo_summary.get('max_intensity', 0):.2f}")
    print(f"\n  Outputs saved to: {out}/")


if __name__ == "__main__":
    main()
