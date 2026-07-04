#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World Simulation v5.5 — Stage 2: 100+ Subjects Life Chronicle

Extends v5.3 (3000 year simulation) with cohort spotlight: 100+ named
individuals tracked simultaneously with full life chronicles.

This is the ladder step Stage 1 (v5.0, 1 spotlight) → Stage 2 (v5.5,
100+ spotlights). The next step is Stage 3 (v6.0, multi-civ + 10⁷ agents).

Output:
- Per-individual chronicle (compact, 100+ files)
- Cohort summary statistics
- Highlight reports (most successful, most resilient, etc.)
- Civilisation trajectory (same as v5.3)

Usage:
    python world_sim_v5_5_cohort.py --world normal --n 30000 --cohort_size 100
    python world_sim_v5_5_cohort.py --world unknown_encounter --frequency frequent
"""
import sys, json, time, argparse
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from world_sim_v5_3_3000years import (
    get_world_config_3000, get_extended_region_mats,
    sample_ahistorical_events_3000,
    era_idx_for_year_3000, shock_for_year_3000,
    update_religion_strength_3000,
    FUTURE_AHISTORICAL_EVENTS_EXTRA,
)
from world_sim_v5_1 import (
    RANDOM_EVENTS, FREQUENCY_MULTIPLIERS,
    REGIONS, OCC, INIT_REGION_PROBS, BASE_OCC,
    EDU_GAIN, INST_GAIN, TRADE_GAIN, ASSET_GAIN, URBAN_GAIN,
    THEORIES, weighted_choice_rows, terminal_category_vec,
    state_to_nrmo_norm, sample_random_events,
    update_religion_strength, religious_conflict_shock,
    faith_positive_dfp_modifier, faith_negative_dfp_modifier,
    faith_charismatic_tail_event, faith_collateral_modifier,
    faith_edu_gain_modifier, faith_shock_loss_modifier,
    composite_score,
)
from ahistorical_events import (
    sample_ahistorical_events, apply_ahistorical_event_effect,
    get_event_secondary_effects,
)
from encounter_mechanism import (
    initial_intensity, evolve_intensity, apply_encounter_effects,
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
from spotlight_cohort import (
    select_cohort, create_cohort_chronicles,
    cohort_summary_stats, find_highlight_lives,
    render_cohort_summary_report, render_cohort_compact_chronicles,
)


def run_world_cohort(world_cfg, n=30000, seed=20260507,
                      frequency_mode="sporadic", enable_ahistorical=True,
                      encounter_year_window=None, family_config=None,
                      n_generations=75, cohort_size=100,
                      cohort_diversity="grid", verbose=True):
    """Run a 3000-year world simulation with cohort spotlight (100+ subjects)."""
    rng = np.random.default_rng(seed)
    eras = world_cfg["eras"]
    shocks = world_cfg["shocks"]
    tech_accel = world_cfg["tech_acceleration"]
    tech_inflection = world_cfg["tech_inflection_year"]
    religion_strength = world_cfg["religion_strength_initial"]
    faith_subdist = world_cfg["faith_subdist"]

    region_mats = get_extended_region_mats()
    freq_mult = FREQUENCY_MULTIPLIERS.get(frequency_mode, 1.0)

    # Sample events
    events_h = []
    for ev_def in RANDOM_EVENTS:
        label, ys, ye, prob_per_year, mag, dim = ev_def
        adj_prob = prob_per_year * freq_mult
        years_in_window = max(1, ye - ys)
        p_occur = 1 - (1 - adj_prob) ** years_in_window
        if rng.random() < p_occur:
            yr = int(rng.uniform(ys, ye))
            events_h.append({"label": label, "year": yr, "magnitude": mag,
                             "dim": dim, "type": "historical"})
    events_h = sorted(events_h, key=lambda e: e["year"])

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

    # Strategy distribution
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

    # === COHORT SETUP (NEW IN v5.5) ===
    cohort_indices, cohort_meta = select_cohort(
        rng, agent_strategy, strategy_names, region, occ, absorbed,
        n_cohort=cohort_size, diversity_strategy=cohort_diversity)
    cohort_chronicles = create_cohort_chronicles(cohort_indices)
    cohort_set = set(cohort_indices)  # for fast lookup

    # Family for the FIRST cohort member (representative)
    family_members, family_region = select_family_branches(
        rng, agent_strategy, strategy_names, region, occ,
        n_branches=4, family_config=family_config or DEFAULT_FAMILY_CONFIG)
    family_chronicles = {role: [] for role in family_members.keys()}
    civ_snapshots = []

    if verbose:
        print(f"  World: {world_cfg['name']}")
        print(f"  Frequency: {frequency_mode}")
        print(f"  Generations: {n_generations} ({n_generations * 40} years)")
        print(f"  Cohort size: {cohort_size} (diversity strategy: {cohort_diversity})")
        if "n_cells_filled" in cohort_meta:
            print(f"  Diversity grid filled: {cohort_meta['n_cells_filled']}/{cohort_meta['n_cells_total']} cells")
        print(f"  Family branches: {len(family_members)} in {REGIONS[family_region]}")
        print(f"  Historical events: {len(events_h)}, Ahistorical events: {len(events_a)}")
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

        militant_count = 0
        for s_idx, sname in enumerate(strategy_names):
            if strategy_faith_class[s_idx] == "militant":
                militant_count += int(((agent_strategy == s_idx) & active).sum())
        militant_share = militant_count / max(active.sum(), 1)
        rel_conflict = religious_conflict_shock(rng, militant_share,
                                                  religion_strength, year, ei)
        if rel_conflict > 0:
            shock_add += rel_conflict

        if year >= 2050:
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

        # === COHORT pre-state capture ===
        prev_cohort_states = {}
        for c_idx in cohort_indices:
            if not absorbed[c_idx]:
                prev_cohort_states[c_idx] = {
                    "occupation": OCC[occ[c_idx]],
                    "region": REGIONS[region[c_idx]],
                    "edu": edu[c_idx],
                    "assets": assets[c_idx],
                    "fk": fk[c_idx],
                    "inst": inst[c_idx],
                    "strategy": strategy_names[agent_strategy[c_idx]],
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

        # State update
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

            scoring_ei = min(ei, 6)
            scores = np.tile(BASE_OCC[scoring_ei], (len(survivors), 1)).astype(float)
            central = np.isin(region[survivors], [1, 2, 3])
            urban_bias = urban[survivors] + central * .08
            scores[:, 1] += .06 * assets[survivors]
            scores[:, 2] += .12 * edu[survivors] + .08 * inst[survivors]
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

        # === COHORT recording (NEW IN v5.5) ===
        for c_idx in cohort_indices:
            cohort_state = {
                "occupation": OCC[occ[c_idx]],
                "region": REGIONS[region[c_idx]],
                "edu": edu[c_idx],
                "assets": assets[c_idx],
                "fk": fk[c_idx],
                "inst": inst[c_idx],
                "strategy": strategy_names[agent_strategy[c_idx]],
                "absorbed": bool(absorbed[c_idx]),
            }
            try:
                cohort_action = (float(g_a[np.where(idx == c_idx)[0][0]]),
                                  float(s_a[np.where(idx == c_idx)[0][0]]),
                                  float(l_a[np.where(idx == c_idx)[0][0]]),
                                  float(d_a[np.where(idx == c_idx)[0][0]]))
            except IndexError:
                cohort_action = (0.0, 0.0, 0.0, 0.0)

            prev_state = prev_cohort_states.get(c_idx)
            record_decision_moment(
                cohort_chronicles[c_idx], gen, year + 40,
                cohort_state, cohort_action,
                prev_state, gen_events,
                encounter_active and encounter_intensity is not None)

        # Family chronicle (representative family)
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

        # Civilisation snapshot
        active_count = int((~absorbed).sum())
        if active_count > 0:
            active_mask = ~absorbed
            record_civilisation_snapshot(
                civ_snapshots, gen, year + 40, era_name,
                active_count, n,
                fk[active_mask], edu[active_mask], inst[active_mask],
                trade[active_mask], assets[active_mask], urban[active_mask],
                agent_strategy[active_mask], strategy_names,
                religion_strength, tech_accel,
                shock_add, gen_events,
                encounter_active and encounter_intensity is not None
            )
        else:
            civ_snapshots.append({
                "generation": gen, "year": year + 40, "era": era_name,
                "alive": False, "extinct": True,
            })

    # Terminal categorization
    term = terminal_category_vec(occ, fk, edu, inst, trade, assets, urban, absorbed)
    for role, idx_g in family_members.items():
        if family_chronicles[role]:
            family_chronicles[role][-1]["terminal_category"] = term[idx_g]
    for c_idx in cohort_indices:
        if cohort_chronicles[c_idx]:
            cohort_chronicles[c_idx][-1]["terminal_category"] = term[c_idx]

    n_continued = int((~absorbed).sum())
    p_continued = float((~absorbed).mean())

    return {
        "world_name": world_cfg["name"],
        "n_total": n,
        "n_generations": n_generations,
        "year_horizon": n_generations * 40,
        "p_continued": p_continued,
        "n_continued": n_continued,
        "cohort_indices": cohort_indices,
        "cohort_meta": cohort_meta,
        "cohort_chronicles": cohort_chronicles,
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
    ap = argparse.ArgumentParser(description="World Sim v5.5 — Stage 2 Cohort Spotlight")
    ap.add_argument("--world", default="normal")
    ap.add_argument("--n", type=int, default=30000, help="Total agent count")
    ap.add_argument("--cohort_size", type=int, default=100,
                    help="Number of named individuals to chronicle")
    ap.add_argument("--cohort_diversity", default="grid",
                    choices=["grid", "random", "strategy_balanced"])
    ap.add_argument("--seed", type=int, default=20260507)
    ap.add_argument("--frequency", default="sporadic",
                    choices=["sporadic", "frequent", "sparse"])
    ap.add_argument("--encounter", action="store_true")
    ap.add_argument("--no_ahistorical", action="store_true")
    ap.add_argument("--n_generations", type=int, default=75)
    ap.add_argument("--outdir", default="outputs_v55")
    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    cfg = get_world_config_3000(args.world)
    encounter_window = (1480, 1520) if (args.encounter or args.world == "unknown_encounter") else None

    print(f"\n{'='*70}\nWorld Sim v5.5 — Stage 2 Cohort: {cfg['name']}")
    print(f"  n={args.n}, cohort={args.cohort_size}, freq={args.frequency}, "
          f"gens={args.n_generations}\n{'='*70}")
    t0 = time.time()
    res = run_world_cohort(cfg, n=args.n, seed=args.seed,
                            frequency_mode=args.frequency,
                            enable_ahistorical=not args.no_ahistorical,
                            encounter_year_window=encounter_window,
                            n_generations=args.n_generations,
                            cohort_size=args.cohort_size,
                            cohort_diversity=args.cohort_diversity,
                            verbose=True)
    rt = time.time() - t0
    print(f"\n  Runtime: {rt:.1f}s")
    print(f"  Year horizon: {res['year_horizon']}")
    print(f"  Civilization continuation: {res['p_continued']*100:.2f}%")

    # Cohort statistics
    stats = cohort_summary_stats(res["cohort_chronicles"])
    print(f"\n  COHORT STATS:")
    print(f"    Cohort size: {stats['n_total']}")
    print(f"    Survival rate: {stats['p_survival']*100:.1f}%")
    print(f"    Total crises across cohort: {stats['n_crises_total']}")
    print(f"    Total career transitions: {stats['n_career_transitions_total']}")
    print(f"    Total ahistorical events: {stats['n_ahistorical_total']}")

    # Render outputs
    highlights = find_highlight_lives(res["cohort_chronicles"])

    cohort_summary_md = render_cohort_summary_report(
        res["cohort_chronicles"], cfg["name"], highlights, res["cohort_meta"])
    summary_path = out / f"cohort_summary_{args.world}_{args.frequency}.md"
    summary_path.write_text(cohort_summary_md, encoding="utf-8")

    sample_chronicles_md = render_cohort_compact_chronicles(
        res["cohort_chronicles"], max_individuals=10)
    sample_path = out / f"cohort_sample_chronicles_{args.world}_{args.frequency}.md"
    sample_path.write_text(sample_chronicles_md, encoding="utf-8")

    # Save full chronicle JSON
    full_data = {
        "world": cfg["name"],
        "n_generations": res["n_generations"],
        "cohort_indices": res["cohort_indices"],
        "cohort_meta": res["cohort_meta"],
        "stats": stats,
        "highlights": {
            cat: [(idx, score) for idx, score, _ in items[:5]]
            for cat, items in highlights.items()
        },
        # Compact per-individual: only key milestones
        "chronicles_compact": {
            str(idx): [
                {
                    "gen": r["generation"],
                    "year": r["year_at_end_of_gen"],
                    "occupation": r["occupation"],
                    "region": r["region"],
                    "edu": round(r["edu"], 3),
                    "assets": round(r["assets"], 3),
                    "decision_type": r["decision_type"],
                    "emotion": r["emotion"],
                    "alive": r["alive"],
                }
                for r in chronicle
                if r.get("decision_type") in ("founder", "crisis_response",
                                                "encounter", "ahistorical",
                                                "career_transition", "absorption")
            ]
            for idx, chronicle in res["cohort_chronicles"].items()
        },
    }
    json_path = out / f"cohort_data_{args.world}_{args.frequency}.json"
    json_path.write_text(json.dumps(full_data, ensure_ascii=False, indent=2, default=str),
                          encoding="utf-8")

    # Civ trajectory CSV
    df_civ = snapshots_to_dataframe(res["civ_snapshots"])
    csv_path = out / f"civilisation_trajectory_{args.world}_{args.frequency}.csv"
    df_civ.to_csv(csv_path, index=False)

    print(f"\n  Outputs saved to: {out}/")
    print(f"    Cohort summary:        {summary_path.name}")
    print(f"    Sample chronicles:     {sample_path.name}")
    print(f"    Full chronicle JSON:   {json_path.name}")
    print(f"    Civ trajectory CSV:    {csv_path.name}")


if __name__ == "__main__":
    main()
