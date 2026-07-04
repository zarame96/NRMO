#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
World Simulation v6.1 — Unified Integrated Simulator (Stage 2+3 + scale presets)

Combines all features from v5.0 → v6.0 into a single configurable simulator:
- Stage 1: 5 worlds + ahistorical + frequency + encounter mechanism (v5.1)
- Stage 1: Two-sided Faith with 6 sub-theories + endogenous religion (v5.0.1)
- Stage 1: 3-tier individual/family/civ Spotlight (v5.2)
- Stage 1: 3000 year horizon (v5.3)
- Stage 1: Multi-civ parallel (v5.4)
- Stage 2: Cohort 100+ named individuals (v5.5)
- Stage 3: 9 Cultural Modules + 18 interaction pairs (v6.0)

Configurable scale presets:
    --scale small   : 9 civs × 5,000  =   45K agents,   50 cohort, ~5s,  <0.5GB
    --scale medium  : 9 civs × 50,000 =  450K agents,  100 cohort, ~60s, ~1GB  [DEFAULT]
    --scale large   : 9 civs × 200,000 = 1.8M agents,  200 cohort, ~4min, ~3GB
    --scale custom  : use --n_per_civ and --cohort_size

Civilization selection:
    --civs Japan,China,Europe,Islamic,Indic,SubSaharan,Polynesian,Steppe,IndigenousAmericas
        (any subset; default is all 9)

Time horizon:
    --n_generations 75  (75 = 3000 years; 50 = 2000 years)

Output structure:
    outputs_v61/
        per_civ_chronicles/<civ>_cohort_summary.md       (per civ cohort report)
        per_civ_chronicles/<civ>_family_chronicle.md     (per civ family tree)
        civ_trajectories/<civ>.csv                       (per civ time series)
        cross_civ_strategy.csv                           (matrix)
        interaction_summary.md                           (inter-civ events)
        v61_overall_report.md                            (executive summary)
        full_data.json                                   (everything)

Usage:
    python world_sim_v6_1_unified.py                          # medium default
    python world_sim_v6_1_unified.py --scale small            # small preset
    python world_sim_v6_1_unified.py --civs Japan,China,Europe --scale large
    python world_sim_v6_1_unified.py --n_per_civ 30000 --cohort_size 50
"""
import sys, json, time, argparse
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from world_sim_v5_3_3000years import sample_ahistorical_events_3000
from world_sim_v5_1 import (
    RANDOM_EVENTS, FREQUENCY_MULTIPLIERS,
    OCC, BASE_OCC, EDU_GAIN, INST_GAIN, TRADE_GAIN, ASSET_GAIN, URBAN_GAIN,
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
from cultural_modules import CULTURAL_MODULES, get_cultural_module, list_cultural_modules
from inter_civ_interaction import (
    sample_interactions_for_year, apply_interaction_effects,
    empty_civ_state, render_interaction_summary,
)
from stage4_features import (
    evolve_strategy_distribution, apply_memetic_drift,
    sample_black_swan_events, apply_black_swan_to_civ,
    CounterfactualOverrides, COUNTERFACTUAL_SCENARIOS,
    build_counterfactual, render_counterfactual_summary,
)
from calibration_targets import render_calibration_report
from vnext_plus import (
    VNextPlusCivController, project_action_to_agents,
    OmegaFullConfig,
)
from vnext_pp_v64 import (
    NRMOController, VNextPPConfig, SharedFailureMemory,
    project_action_to_agents_pp, cultural_distance_fn,
)
from nrmo_collective_v70 import (
    CollectiveCivController, CollectiveConfig,
    apply_quorum, apply_tradition_blend, apply_ultra_horizon_boost,
    compute_tradition_action, apply_strategy_reproduction,
)
from collective_engine_v71 import (
    CollectiveStrongEngine, CollectiveEngineConfig,
    triage_rescue_selection,
)
from collective_v71_wrapper import CollectiveCivControllerV71


# ============================================================
# Scale Presets
# ============================================================

SCALE_PRESETS = {
    "small": {
        "n_per_civ": 5_000,
        "cohort_size": 50,
        "expected_runtime_s": 5,
        "expected_ram_mb": 300,
        "description": "Quick test (5K/civ × 9 civs = 45K agents, 50 cohort/civ)",
    },
    "medium": {
        "n_per_civ": 50_000,
        "cohort_size": 100,
        "expected_runtime_s": 60,
        "expected_ram_mb": 1_000,
        "description": "Default (50K/civ × 9 = 450K agents, 100 cohort/civ)",
    },
    "large": {
        "n_per_civ": 200_000,
        "cohort_size": 200,
        "expected_runtime_s": 240,
        "expected_ram_mb": 3_000,
        "description": "Heavy (200K/civ × 9 = 1.8M agents, 200 cohort/civ) — RAM ~3GB",
    },
}


# ============================================================
# Per-civ population init
# ============================================================

def init_civ_pop(civ_module, n, rng):
    """Initialize agent population for one civilization."""
    region_init_probs = civ_module.region_init_probs
    n_regions = civ_module.n_regions

    sd_input = civ_module.base_strategy_dist
    expanded_dist = {}
    for s, p in sd_input.items():
        if s == "Faith":
            for sub_name, sub_p in civ_module.faith_subdist.items():
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

    region = rng.choice(n_regions, size=n, p=region_init_probs)
    p_init_occ = np.array([.85, .07, 0, .02, .04, 0, 0, 0, 0, 0, 0])
    occ = rng.choice(len(OCC), size=n, p=p_init_occ / p_init_occ.sum())
    fk = rng.uniform(.04, .16, size=n)
    edu = rng.uniform(.01, .06, size=n)
    inst = rng.uniform(.02, .10, size=n)
    trade = rng.uniform(.02, .12, size=n)
    assets = rng.uniform(.04, .18, size=n)
    urban = rng.uniform(.00, .08, size=n)
    absorbed = np.zeros(n, dtype=bool)

    return {
        "civ_module": civ_module,
        "n": n,
        "region": region, "occ": occ,
        "fk": fk, "edu": edu, "inst": inst, "trade": trade,
        "assets": assets, "urban": urban, "absorbed": absorbed,
        "agent_strategy": agent_strategy,
        "strategy_names": strategy_names,
        "strategy_faith_class": strategy_faith_class,
        "religion_strength": civ_module.religion_strength_initial,
        "tech_accel": civ_module.tech_acceleration,
        "tech_inflection": civ_module.tech_inflection_year,
    }


def era_idx_for_civ(year, civ_eras):
    for i, e in enumerate(civ_eras):
        if e[1] <= year < e[2]:
            return i
    return len(civ_eras) - 1


# ============================================================
# Step civ one generation (with cohort + family tracking)
# ============================================================

def step_civ_one_gen(civ_state, gen, year, gen_events, interaction_state,
                       secondary, cohort_indices, cohort_chronicles,
                       family_members, family_chronicles, encounter_active,
                       encounter_intensity, rng,
                       vnext_plus_ctrl=None,
                       nrmo_pp_ctrl=None,
                       collective_ctrl=None,
                       family_assignment=None):
    """One generation step for one civilization with cohort+family chronicling.

    Controller tiers (mutually exclusive, in priority order):
    - None: use original per-agent theory functions (v6.0 baseline)
    - vnext_plus_ctrl (v6.3): full Adaptive NRMOvNext + Ω Full pipeline
    - nrmo_pp_ctrl (v6.4): vNext++ with all 13 enhancements (A-M)
    Only one of vnext_plus_ctrl / nrmo_pp_ctrl should be non-None.

    Additional layer:
    - collective_ctrl (v7.0): NRMO Collective extension (P-U mechanisms)
      Operates ON TOP of nrmo_pp_ctrl. Applies Q (quorum), T (tradition),
      U (ultra-horizon), S (solidarity), P (multi-tier insurance).
    """
    civ_module = civ_state["civ_module"]
    eras = civ_module.eras
    n = civ_state["n"]

    region = civ_state["region"]
    occ = civ_state["occ"]
    fk = civ_state["fk"]; edu = civ_state["edu"]; inst = civ_state["inst"]
    trade = civ_state["trade"]; assets = civ_state["assets"]; urban = civ_state["urban"]
    absorbed = civ_state["absorbed"]
    agent_strategy = civ_state["agent_strategy"]
    strategy_names = civ_state["strategy_names"]
    strategy_faith_class = civ_state["strategy_faith_class"]
    religion_strength = civ_state["religion_strength"]
    tech_accel = civ_state["tech_accel"]
    tech_inflection = civ_state["tech_inflection"]

    ei = era_idx_for_civ(year, eras)
    era_name, _, _, base_fail, collat_success = eras[ei]
    shock_add = interaction_state["shock_add"]

    # v7.0: S - Solidarity shock absorption
    if collective_ctrl is not None and collective_ctrl.solidarity is not None:
        shock_add = collective_ctrl.apply_shock_modifiers(shock_add)

    active = ~absorbed
    idx = np.where(active)[0]
    if len(idx) == 0:
        return None

    # Religious conflict
    militant_count = 0
    for s_idx in range(len(strategy_names)):
        if strategy_faith_class[s_idx] == "militant":
            militant_count += int(((agent_strategy == s_idx) & active).sum())
    militant_share = militant_count / max(active.sum(), 1)
    rel_conflict = religious_conflict_shock(rng, militant_share,
                                              religion_strength, year, ei)
    if rel_conflict > 0:
        shock_add += rel_conflict

    # Tech factor (with AI inflection at 2050)
    if year >= 2050 and year >= tech_inflection:
        tech_factor = tech_accel * 1.5
    elif year >= tech_inflection:
        tech_factor = tech_accel
    else:
        tech_factor = 1.0

    religion_strength = update_religion_strength(
        religion_strength, shock_add, tech_factor, gen_events,
        militant_share, year, {"tech_inflection_year": tech_inflection})

    # Compute actions
    R_a, E_a, G_a, O_a, K_a, X_a = state_to_nrmo_norm(
        fk[idx], edu[idx], inst[idx], trade[idx], assets[idx], urban[idx], shock_add)
    action = np.zeros((len(idx), 4))

    # === vNext+ / vNext++ pipeline (if controller provided) ===
    # Run civ-level Ω Full once per generation per civ; project to agents.
    civ_action_vnext = None
    civ_tc = None
    nrmo_pp_used = False
    if nrmo_pp_ctrl is not None:
        try:
            civ_action_vnext, civ_tc, _mode_scores = nrmo_pp_ctrl.step(
                rng, fk, edu, inst, trade, assets, urban, civ_state["absorbed"],
                religion_strength, shock_add, ei,
                world_name="Normal", gen=gen)
            nrmo_pp_used = True
        except Exception as e:
            print(f"  Warning: nrmo_pp_ctrl step failed for {civ_module.name}: {e}")
            civ_action_vnext = None
    elif vnext_plus_ctrl is not None:
        try:
            civ_action_vnext, civ_tc = vnext_plus_ctrl.step(
                rng, fk, edu, inst, trade, assets, urban, civ_state["absorbed"],
                religion_strength, shock_add, ei,
                world_name="Normal", gen=gen)
        except Exception as e:
            print(f"  Warning: vnext_plus step failed for {civ_module.name}: {e}")
            civ_action_vnext = None

    for s_idx, sname in enumerate(strategy_names):
        mask = agent_strategy[idx] == s_idx
        if not mask.any():
            continue
        # ENHANCEMENT: project civ_action for NRMO-family strategies
        if (civ_action_vnext is not None and
            sname in ("NRMO_vNext", "Adaptive_OmegaFull", "NRMO")):
            n_sub = int(mask.sum())
            sigma = 0.03 if sname in ("NRMO_vNext", "NRMO") else 0.04
            if nrmo_pp_used and nrmo_pp_ctrl is not None and nrmo_pp_ctrl.cfg.enable_D_state_conditioned_sigma:
                # D: state-conditioned sigma
                sub_edu_active = edu[idx][mask]
                sub_ass_active = assets[idx][mask]
                prosperity = sub_edu_active + sub_ass_active
                severity = np.clip(1 - prosperity / 2, 0, 1) * 0.6 + np.clip(shock_add, 0, 0.5) * 0.4
                sigma_scaled = sigma * (1 - severity * 0.7)
                sub_action = np.tile(civ_action_vnext, (n_sub, 1)) + \
                              rng.normal(0, 1.0, size=(n_sub, 4)) * sigma_scaled[:, None]
            else:
                sub_action = np.tile(civ_action_vnext, (n_sub, 1)) + \
                              rng.normal(0, sigma, size=(n_sub, 4))
            sub_action = np.clip(sub_action, 0.05, None)
            sub_action = sub_action / sub_action.sum(axis=1, keepdims=True)
        else:
            theory_fn, bypass, _ = THEORIES[sname]
            sub_action = theory_fn(int(mask.sum()),
                                    R_a[mask], E_a[mask], G_a[mask],
                                    O_a[mask], K_a[mask], X_a[mask],
                                    rng, {"tech_acceleration": tech_accel,
                                           "tech_inflection_year": tech_inflection})
            if bypass:
                sub_action = np.zeros_like(sub_action)
        action[mask] = sub_action

    # v7.0: Q (quorum) + T (tradition) on top of base projection
    if collective_ctrl is not None:
        # Tradition action: weighted mean of all strategies' actions
        tradition_act = compute_tradition_action(action, agent_strategy[idx],
                                                    strategy_names,
                                                    np.zeros(len(idx), dtype=bool),
                                                    collective_ctrl.cfg)
        # Blend each strategy toward tradition with strategy-specific weight
        action = apply_tradition_blend(action, agent_strategy[idx],
                                         strategy_names, tradition_act,
                                         collective_ctrl.cfg)
        # Quorum coordination within each strategy
        action = apply_quorum(action, agent_strategy[idx],
                                strategy_names, collective_ctrl.cfg, rng)

    g_a = action[:, 0]; s_a = action[:, 1]
    l_a = action[:, 2]; d_a = action[:, 3]

    # === Cohort/family pre-state capture ===
    prev_cohort_states = {}
    for c_idx in cohort_indices:
        if not absorbed[c_idx]:
            prev_cohort_states[c_idx] = {
                "occupation": OCC[occ[c_idx]],
                "region": _region_name(civ_module, region[c_idx]),
                "edu": float(edu[c_idx]), "assets": float(assets[c_idx]),
                "fk": float(fk[c_idx]), "inst": float(inst[c_idx]),
                "strategy": strategy_names[agent_strategy[c_idx]],
            }

    prev_family_states = {}
    for role, idx_g in family_members.items():
        if not absorbed[idx_g] and family_chronicles[role]:
            last = family_chronicles[role][-1]
            prev_family_states[role] = {
                "occupation": last["occupation"],
                "region": last["region"], "edu": last["edu"],
                "assets": last["assets"], "fk": last["family_knowledge"],
                "inst": last["inst"], "strategy": last["strategy"],
            }

    # DFP
    dfp = base_fail + shock_add - .030 * assets[idx] - .025 * inst[idx] - .020 * edu[idx]
    dfp *= (1 - 0.45 * s_a)
    dfp *= (1 - 0.10 * l_a)
    dfp += g_a * shock_add * 0.45

    for s_idx in range(len(strategy_names)):
        fc = strategy_faith_class[s_idx]
        if fc is None:
            continue
        mask = agent_strategy[idx] == s_idx
        if not mask.any():
            continue
        pos_mod = faith_positive_dfp_modifier(fc, religion_strength)
        neg_mod = faith_negative_dfp_modifier(fc, religion_strength, ei)
        dfp[mask] *= pos_mod * neg_mod

    for s_idx in range(len(strategy_names)):
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

    # v7.0: U - ultra-horizon dfp reduction
    if collective_ctrl is not None:
        dfp = collective_ctrl.apply_dfp_modifiers(dfp, agent_strategy[idx],
                                                     strategy_names)

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
            cprob = cprob_base * (1 + 0.20 * d_fail) * civ_module.distribution_boost
            for s_idx in range(len(strategy_names)):
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

            # v7.0: P - multi-tier insurance rescue cascade for lost lineages
            if (collective_ctrl is not None and collective_ctrl.insurance is not None
                and len(lost) > 0 and family_assignment is not None):
                rescued_mask = collective_ctrl.attempt_rescue_cascade(
                    lost, family_assignment, agent_strategy,
                    strategy_names, rng)
                truly_lost = lost[~rescued_mask]
                rescued_lineages = lost[rescued_mask]
                if len(rescued_lineages):
                    # Reset rescued lineages similar to collateral
                    probs = np.array([.40, .10, 0, .03, .20, .08, .10, .03, .02, .03, .01])
                    occ[rescued_lineages] = rng.choice(
                        len(OCC), size=len(rescued_lineages), p=probs / probs.sum())
                if len(truly_lost):
                    absorbed[truly_lost] = True
            else:
                if len(lost):
                    absorbed[lost] = True

    # State update
    survivors = idx[~absorbed[idx]]
    if len(survivors):
        # Region transition (use civ's stability curve)
        n_eras = len(civ_module.region_stability_curve)
        stability = civ_module.region_stability_curve[min(ei, n_eras - 1)]
        n_reg = civ_module.n_regions
        mat_e = np.full((n_reg, n_reg), (1 - stability) / max(n_reg - 1, 1))
        np.fill_diagonal(mat_e, stability)
        new_region = region[survivors].copy()
        for ri in range(n_reg):
            sub = survivors[region[survivors] == ri]
            if len(sub) == 0:
                continue
            probs = np.tile(mat_e[ri], (len(sub), 1))
            new_region[region[survivors] == ri] = weighted_choice_rows(probs, rng)
        region[survivors] = new_region

        surv_local_idx = np.where(~absorbed[idx])[0]
        g_s = g_a[surv_local_idx]; s_s = s_a[surv_local_idx]
        l_s = l_a[surv_local_idx]; d_s = d_a[surv_local_idx]

        scoring_ei = min(ei, 6)
        scores = np.tile(BASE_OCC[scoring_ei], (len(survivors), 1)).astype(float)
        urban_bias = urban[survivors]
        scores[:, 1] += .06 * assets[survivors]
        scores[:, 4] += .06 * trade[survivors]
        scores[:, 5] += .10 * trade[survivors] + .04 * assets[survivors]
        if scoring_ei >= 5:
            scores[:, 7] += .10 * urban_bias
            scores[:, 8] += .14 * edu[survivors] + .05 * inst[survivors]
            scores[:, 10] += .10 * edu[survivors] + .08 * assets[survivors]
        if scoring_ei >= 4:
            scores[:, 9] += .11 * edu[survivors] + .06 * inst[survivors]
        scores[np.arange(len(survivors)), occ[survivors]] += .18

        scores[:, 5] += 0.08 * g_s; scores[:, 9] += 0.10 * l_s
        scores[:, 10] += 0.08 * l_s; scores[:, 8] += 0.06 * (l_s + g_s)

        occ[survivors] = weighted_choice_rows(
            scores / scores.sum(axis=1, keepdims=True), rng)

        # State updates
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

        edu_modifier = np.ones(len(survivors))
        for s_idx in range(len(strategy_names)):
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

        # Inter-civ interaction effects
        eg += interaction_state["edu_boost"]
        ig += interaction_state["inst_boost"]
        tg += interaction_state["trade_boost"]
        ag += interaction_state["asset_boost"]

        # Ahistorical secondary
        if secondary["edu_multiplier_global"] != 1.0:
            edu[survivors] = edu[survivors] * secondary["edu_multiplier_global"]
        if secondary["edu_boost_global"] > 0:
            eg = eg + secondary["edu_boost_global"]
        if secondary["trade_boost_global"] > 0:
            tg = tg + secondary["trade_boost_global"]

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

    # === Cohort/family chronicle recording ===
    # Build O(1) lookup: c_idx -> position in idx (only for cohort+family members)
    # avoids O(n) np.where calls
    idx_pos_lookup = {}
    if len(cohort_indices) > 0 or len(family_members) > 0:
        track_set = set(cohort_indices) | set(family_members.values())
        for pos, gi in enumerate(idx):
            if int(gi) in track_set:
                idx_pos_lookup[int(gi)] = pos

    for c_idx in cohort_indices:
        cohort_state = {
            "occupation": OCC[occ[c_idx]],
            "region": _region_name(civ_module, region[c_idx]),
            "edu": float(edu[c_idx]), "assets": float(assets[c_idx]),
            "fk": float(fk[c_idx]), "inst": float(inst[c_idx]),
            "strategy": strategy_names[agent_strategy[c_idx]],
            "absorbed": bool(absorbed[c_idx]),
        }
        local_pos = idx_pos_lookup.get(int(c_idx))
        if local_pos is not None:
            cohort_action = (float(g_a[local_pos]), float(s_a[local_pos]),
                              float(l_a[local_pos]), float(d_a[local_pos]))
        else:
            cohort_action = (0.0, 0.0, 0.0, 0.0)
        prev = prev_cohort_states.get(c_idx)
        record_decision_moment(
            cohort_chronicles[c_idx], gen, year + 40,
            cohort_state, cohort_action, prev, gen_events,
            encounter_active and encounter_intensity is not None)

    for role, idx_g in family_members.items():
        fam_state = {
            "occupation": OCC[occ[idx_g]],
            "region": _region_name(civ_module, region[idx_g]),
            "edu": float(edu[idx_g]), "assets": float(assets[idx_g]),
            "fk": float(fk[idx_g]), "inst": float(inst[idx_g]),
            "strategy": strategy_names[agent_strategy[idx_g]],
            "absorbed": bool(absorbed[idx_g]),
        }
        local_pos = idx_pos_lookup.get(int(idx_g))
        if local_pos is not None:
            fam_action = (float(g_a[local_pos]), float(s_a[local_pos]),
                           float(l_a[local_pos]), float(d_a[local_pos]))
        else:
            fam_action = (0.0, 0.0, 0.0, 0.0)
        prev = prev_family_states.get(role)
        record_decision_moment(
            family_chronicles[role], gen, year + 40,
            fam_state, fam_action, prev, gen_events,
            encounter_active and encounter_intensity is not None)

    civ_state["religion_strength"] = religion_strength
    civ_state["tech_accel"] = tech_accel

    return {
        "active_count": int((~absorbed).sum()),
        "shock_received": shock_add,
        "religion_strength": religion_strength,
        "tech_factor": tech_factor,
    }


def _region_name(civ_module, region_idx):
    if region_idx < len(civ_module.region_names):
        return civ_module.region_names[region_idx]
    return f"region_{region_idx}"


# ============================================================
# Main simulation
# ============================================================

def run_unified(civ_names, n_per_civ, cohort_size, n_generations, seed,
                  frequency_mode, enable_ahistorical, encounter_civ,
                  cohort_diversity="grid",
                  enable_memetic=False, memetic_drift_rate=0.05,
                  enable_black_swan=False, black_swan_intensity=1.0,
                  counterfactual_scenarios=None,
                  enable_vnext_plus=False,
                  enable_nrmo_pp=False,
                  enable_collective=False,
                  enable_collective_engine=False,
                  nrmo_pp_config=None,
                  collective_config=None,
                  collective_engine_config=None,
                  enable_archetype_classifier=True,
                  verbose=True):
    """Run unified multi-civ simulation.

    Controller tiers (in priority order):
    - enable_collective_engine: v7.1 NRMO Collective + Strong Engine (implies --collective)
    - enable_collective: v7.0 NRMO Collective (requires nrmo_pp as base)
    - enable_nrmo_pp: v6.4 NRMO++ with all A-M enhancements
    - enable_vnext_plus: v6.3 Adaptive NRMOvNext + Ω Full
    - neither: v6.0 per-agent theory baseline

    v7.1 (collective_engine) extends v7.0 by adding the Collective Strong
    Engine: a search process over CollectiveConfiguration objects that
    selects optimal P-U parameters each generation, instead of using v7.0's
    fixed values.
    """
    rng = np.random.default_rng(seed)

    cf = None
    if counterfactual_scenarios:
        cf = build_counterfactual(counterfactual_scenarios)

    black_swans = []
    if enable_black_swan:
        black_swans = sample_black_swan_events(
            rng, 0, n_generations * 40, black_swan_intensity)

    # v6.3 vNext+ controllers (one per civ)
    vnext_plus_controllers = {}
    if enable_vnext_plus and not enable_nrmo_pp:
        pass  # initialized below in civ loop

    # v6.4 NRMO controllers (one per civ; vNext++)
    nrmo_pp_controllers = {}
    shared_failure_memory = None
    if enable_nrmo_pp or enable_collective:
        pp_cfg = nrmo_pp_config or VNextPPConfig()
        if pp_cfg.enable_F_shared_failure_memory:
            shared_failure_memory = SharedFailureMemory()

    # v7.0 NRMO Collective controllers (one per civ)
    collective_controllers = {}
    # Family assignment: each agent gets a family bucket (0..3) for P
    civ_family_assignment = {}

    # Initialize civ populations
    civ_states = {}
    for cn in civ_names:
        cm = get_cultural_module(cn)
        civ_states[cn] = init_civ_pop(cm, n_per_civ, rng)
        # v6.4 NRMO controller (vNext++) takes priority over v6.3
        if enable_nrmo_pp or enable_collective:
            nrmo_pp_controllers[cn] = NRMOController(
                cn, cm, nrmo_pp_config or VNextPPConfig(),
                shared_failure_memory=shared_failure_memory)
        elif enable_vnext_plus:
            vnext_plus_controllers[cn] = VNextPlusCivController(
                cn, cm, enable_archetype_classifier=enable_archetype_classifier)

        # v7.0 Collective controller + family assignment
        # v7.1 uses CollectiveCivControllerV71 (wrapper) instead
        if enable_collective_engine:
            strategy_names = civ_states[cn]["strategy_names"]
            collective_controllers[cn] = CollectiveCivControllerV71(
                cn, cm,
                v70_cfg=collective_config or CollectiveConfig(),
                v71_cfg=collective_engine_config or CollectiveEngineConfig(),
                strategy_names=strategy_names, n_families=4)
            civ_family_assignment[cn] = rng.integers(0, 4, size=n_per_civ)
        elif enable_collective:
            strategy_names = civ_states[cn]["strategy_names"]
            collective_controllers[cn] = CollectiveCivController(
                cn, cm, collective_config or CollectiveConfig(),
                strategy_names=strategy_names, n_families=4)
            civ_family_assignment[cn] = rng.integers(0, 4, size=n_per_civ)

    # Initialize per-civ cohort + family + chronicles
    civ_cohorts = {}
    civ_cohort_chronicles = {}
    civ_family_members = {}
    civ_family_chronicles = {}
    civ_snapshots = {cn: [] for cn in civ_names}

    for cn in civ_names:
        cs = civ_states[cn]
        cohort_idx, cohort_meta = select_cohort(
            rng, cs["agent_strategy"], cs["strategy_names"],
            cs["region"], cs["occ"], cs["absorbed"],
            n_cohort=cohort_size, diversity_strategy=cohort_diversity)
        civ_cohorts[cn] = (cohort_idx, cohort_meta)
        civ_cohort_chronicles[cn] = create_cohort_chronicles(cohort_idx)

        fam_members, _ = select_family_branches(
            rng, cs["agent_strategy"], cs["strategy_names"],
            cs["region"], cs["occ"], n_branches=4)
        civ_family_members[cn] = fam_members
        civ_family_chronicles[cn] = {role: [] for role in fam_members.keys()}

    # Encounter setup
    encounter_civ_state = None
    encounter_year = None
    encounter_intensity = None
    if encounter_civ and encounter_civ in civ_names:
        encounter_year = int(rng.uniform(1480, 1520))
        encounter_intensity = initial_intensity()
        encounter_civ_state = encounter_civ

    freq_mult = FREQUENCY_MULTIPLIERS.get(frequency_mode, 1.0)
    events_global = []
    if enable_ahistorical:
        events_global = sample_ahistorical_events_3000(
            rng, 0, n_generations * 40, frequency_multiplier=freq_mult)

    if verbose:
        print(f"\n{'='*72}")
        print(f"v6.1 Unified Simulation")
        print(f"  Civilizations: {', '.join(civ_names)} ({len(civ_names)} civs)")
        print(f"  Per-civ agents: {n_per_civ:,}")
        print(f"  Per-civ cohort: {cohort_size}")
        print(f"  Total agents: {n_per_civ * len(civ_names):,}")
        print(f"  Total chronicled individuals: {(cohort_size + 4) * len(civ_names)}")
        print(f"  Generations: {n_generations} ({n_generations*40} years)")
        print(f"  Frequency: {frequency_mode}")
        print(f"  Ahistorical events: {len(events_global)}")
        if encounter_civ_state:
            print(f"  Encounter civilization: {encounter_civ_state} (year {encounter_year})")
        if enable_memetic:
            print(f"  Memetic dynamics: ON (drift_rate={memetic_drift_rate})")
        if enable_black_swan:
            print(f"  Black Swan events: {len(black_swans)} sampled (intensity {black_swan_intensity})")
        if cf:
            print(f"  Counterfactuals: {counterfactual_scenarios} ({len(cf.overrides)} overrides)")
        print(f"{'='*72}\n")

    interaction_log = []
    encounter_log = []
    black_swan_log = []
    memetic_log = []

    for gen in range(1, n_generations + 1):
        year = (gen - 1) * 40

        # === Counterfactual: forced extinctions ===
        if cf:
            for cn in civ_names:
                if cf.force_extinction(cn, year):
                    civ_states[cn]["absorbed"][:] = True

        # === Black Swan events for this gen ===
        gen_black_swans = []
        if enable_black_swan:
            gen_black_swans = [bs for bs in black_swans if year <= bs["year"] < year + 40]

        # Inter-civ interactions
        active_civs = [cn for cn in civ_names if (~civ_states[cn]["absorbed"]).any()]
        interactions = sample_interactions_for_year(year, 40, rng, active_civs)

        # Apply counterfactual: filter interactions
        if cf:
            interactions = cf.filter_interactions(interactions, year)

        civ_interaction_states = {cn: empty_civ_state() for cn in civ_names}
        for itc in interactions:
            apply_interaction_effects(itc, civ_interaction_states)
            interaction_log.append(itc)

        # Apply Black Swan to all civs (or specific scope)
        for bs in gen_black_swans:
            black_swan_log.append(bs)
            if bs["scope"] == "global":
                for cn in civ_names:
                    civ_interaction_states[cn]["shock_add"] += bs["shock_magnitude"]
            elif bs["scope"] == "regional":
                # Random subset of civs
                affected = rng.choice(civ_names, size=min(3, len(civ_names)), replace=False)
                for cn in affected:
                    civ_interaction_states[cn]["shock_add"] += bs["shock_magnitude"]
            elif bs["scope"] == "civ_pair":
                # 2 random civs hit
                if len(civ_names) >= 2:
                    pair = rng.choice(civ_names, size=2, replace=False)
                    for cn in pair:
                        civ_interaction_states[cn]["shock_add"] += bs["shock_magnitude"]

        # Ahistorical events for this gen
        gen_events = [e for e in events_global if year <= e["year"] < year + 40]
        # Counterfactual: filter out suppressed events
        if cf:
            gen_events = cf.filter_events(gen_events, year)
        # Counterfactual: shock reduction per civ
        if cf:
            for cn in civ_names:
                mod = cf.civ_shock_modifier(cn, year)
                if mod < 1.0:
                    civ_interaction_states[cn]["shock_add"] *= mod
        secondary = {
            "edu_multiplier_global": 1.0, "asset_random_loss_global": 0.0,
            "inst_random_delta_global": 0.0, "direct_mortality_p": 0.0,
            "edu_boost_global": 0.0, "inst_boost_global": 0.0, "trade_boost_global": 0.0,
        }
        for ev in gen_events:
            sec = get_event_secondary_effects(ev)
            if "edu_multiplier" in sec:
                secondary["edu_multiplier_global"] *= sec["edu_multiplier"]
            if "direct_mortality_p" in sec:
                secondary["direct_mortality_p"] = max(
                    secondary["direct_mortality_p"], sec["direct_mortality_p"])
            for cn in civ_names:
                dummy_world_cfg = {"tech_acceleration": civ_states[cn]["tech_accel"]}
                add_shock, _, _ = apply_ahistorical_event_effect(
                    ev, civ_interaction_states[cn]["shock_add"],
                    civ_states[cn]["tech_accel"], civ_states[cn]["religion_strength"],
                    dummy_world_cfg, rng)
                civ_interaction_states[cn]["shock_add"] = add_shock

        # Encounter on specific civ
        if encounter_civ_state and year >= encounter_year:
            generations_since = (year - encounter_year) // 40
            encounter_intensity = evolve_intensity(rng, encounter_intensity, generations_since)
            new_shock, _, new_rs, enc_sec = apply_encounter_effects(
                encounter_intensity, 0.15,
                civ_interaction_states[encounter_civ_state]["shock_add"],
                civ_states[encounter_civ_state]["tech_accel"],
                civ_states[encounter_civ_state]["religion_strength"], rng)
            civ_interaction_states[encounter_civ_state]["shock_add"] = new_shock
            civ_interaction_states[encounter_civ_state]["edu_boost"] += enc_sec["edu_boost"]
            civ_interaction_states[encounter_civ_state]["inst_boost"] += enc_sec["inst_boost"]
            civ_interaction_states[encounter_civ_state]["trade_boost"] += enc_sec["trade_boost"]
            civ_states[encounter_civ_state]["religion_strength"] = new_rs
            encounter_log.append({
                "year": year, "civ": encounter_civ_state,
                "intensity": encounter_intensity,
                "generations_since": generations_since,
            })

        # Step each civ
        for cn in civ_names:
            cohort_idx, _ = civ_cohorts[cn]
            ctrl = vnext_plus_controllers.get(cn) if enable_vnext_plus and not enable_nrmo_pp and not enable_collective and not enable_collective_engine else None
            pp_ctrl = nrmo_pp_controllers.get(cn) if (enable_nrmo_pp or enable_collective or enable_collective_engine) else None
            coll_ctrl = collective_controllers.get(cn) if (enable_collective or enable_collective_engine) else None
            fam_assign = civ_family_assignment.get(cn) if (enable_collective or enable_collective_engine) else None

            # v7.1: Engine selects collective configuration BEFORE step
            if enable_collective_engine and coll_ctrl is not None and isinstance(coll_ctrl, CollectiveCivControllerV71):
                cs = civ_states[cn]
                from vnext_plus import aggregate_to_civstate as _agg
                cs_scalar = _agg(cs["fk"], cs["edu"], cs["inst"], cs["trade"],
                                  cs["assets"], cs["urban"], cs["absorbed"],
                                  cs["religion_strength"],
                                  civ_interaction_states[cn]["shock_add"],
                                  None, step=gen)
                # World params
                ei_now = era_idx_for_civ(year, civ_state["civ_module"].eras) if False else 0
                # use module eras
                eras_now = cs["civ_module"].eras
                ei_now = next((i for i, e in enumerate(eras_now)
                                if e[1] <= year < e[2]), len(eras_now) - 1)
                from vnext_plus import derive_world_params
                wp = derive_world_params(cs["civ_module"], ei_now, cs["religion_strength"])
                # Partner balances and states (simplified: empty for now;
                # full inter-civ contracts handled separately)
                partner_civs = [c for c in civ_names if c != cn]
                partner_balances = {p: 0.0 for p in partner_civs}
                partner_states = {p: None for p in partner_civs}
                rivalry_pairs = {(cn, p): 0.20 for p in partner_civs}
                # Inequality proxy
                active = ~cs["absorbed"]
                if active.any():
                    inequality = float(np.var(cs["edu"][active] + cs["assets"][active]))
                else:
                    inequality = 0.0
                coll_ctrl.run_engine_select(
                    civstate_scalar=cs_scalar, world_params=wp,
                    partner_civs=partner_civs, partner_balances=partner_balances,
                    partner_states=partner_states,
                    rivalry_pairs=rivalry_pairs, inequality=inequality, rng=rng)

            result = step_civ_one_gen(
                civ_states[cn], gen, year, gen_events,
                civ_interaction_states[cn], secondary,
                cohort_idx, civ_cohort_chronicles[cn],
                civ_family_members[cn], civ_family_chronicles[cn],
                encounter_civ_state == cn, encounter_intensity, rng,
                vnext_plus_ctrl=ctrl, nrmo_pp_ctrl=pp_ctrl,
                collective_ctrl=coll_ctrl, family_assignment=fam_assign)

            # B: Insurance contribution after each gen (vNext++)
            if pp_ctrl is not None and pp_ctrl.cfg.enable_B_insurance_layer:
                cs = civ_states[cn]
                pp_ctrl.contribute_to_insurance(cs["edu"], cs["assets"], cs["absorbed"], rng)

            # v7.0/v7.1: collective end-of-gen processing
            if coll_ctrl is not None:
                cs = civ_states[cn]
                crisis_flag = civ_interaction_states[cn]["shock_add"] > 0.15
                coll_ctrl.step_end_of_generation(
                    cs["edu"], cs["assets"], cs["absorbed"],
                    cs["agent_strategy"], cs["strategy_names"],
                    fam_assign, crisis_flag, rng)

            cs = civ_states[cn]

            # === Memetic dynamics: replicator update at end of gen ===
            if enable_memetic and gen >= 2:  # Skip gen 1 (no fitness data)
                n_strategies = len(cs["strategy_names"])
                new_dist, fitness = evolve_strategy_distribution(
                    cs["agent_strategy"], cs["absorbed"],
                    cs["edu"], cs["assets"],
                    n_strategies, drift_rate=memetic_drift_rate, rng=rng)
                # Apply to recently-reset agents (those who got new occupation this gen)
                # Identify them: they were in fail_global ∩ collateral_reset
                # Approximation: random subset of survivors
                survivors_active = np.where(~cs["absorbed"])[0]
                if len(survivors_active) > 0:
                    n_drift = int(len(survivors_active) * memetic_drift_rate * 0.5)
                    if n_drift > 0:
                        drift_idx = rng.choice(survivors_active, size=n_drift, replace=False)
                        cs["agent_strategy"] = apply_memetic_drift(
                            cs["agent_strategy"], drift_idx, new_dist, rng)
                if gen % 10 == 0:  # Log every 10 gens
                    memetic_log.append({
                        "civ": cn, "gen": gen, "year": year,
                        "fitness_top": int(fitness.argmax()),
                        "fitness_max": float(fitness.max()),
                    })

            ac = int((~cs["absorbed"]).sum())
            if ac > 0:
                cm = cs["civ_module"]
                ei = era_idx_for_civ(year, cm.eras)
                era_name = cm.eras[ei][0]
                am = ~cs["absorbed"]
                record_civilisation_snapshot(
                    civ_snapshots[cn], gen, year + 40, era_name,
                    ac, cs["n"],
                    cs["fk"][am], cs["edu"][am], cs["inst"][am],
                    cs["trade"][am], cs["assets"][am], cs["urban"][am],
                    cs["agent_strategy"][am], cs["strategy_names"],
                    cs["religion_strength"],
                    result["tech_factor"] if result else cs["tech_accel"],
                    civ_interaction_states[cn]["shock_add"], gen_events,
                    encounter_civ_state == cn)
            else:
                civ_snapshots[cn].append({
                    "generation": gen, "year": year + 40,
                    "alive": False, "extinct": True,
                })

    # Aggregate
    civ_results = {}
    for cn in civ_names:
        cs = civ_states[cn]
        n = cs["n"]
        absorbed = cs["absorbed"]
        term = terminal_category_vec(cs["occ"], cs["fk"], cs["edu"],
                                       cs["inst"], cs["trade"], cs["assets"],
                                       cs["urban"], absorbed)

        # Add terminal to family
        for role, idx_g in civ_family_members[cn].items():
            if civ_family_chronicles[cn][role]:
                civ_family_chronicles[cn][role][-1]["terminal_category"] = term[idx_g]
        for c_idx in civ_cohorts[cn][0]:
            if civ_cohort_chronicles[cn][c_idx]:
                civ_cohort_chronicles[cn][c_idx][-1]["terminal_category"] = term[c_idx]

        n_continued = int((~absorbed).sum())
        p_continued = float((~absorbed).mean())
        unique, counts = np.unique(term, return_counts=True)
        endpoint_dist = dict(zip(unique, counts))

        per_strategy = {}
        for s_idx, sname in enumerate(cs["strategy_names"]):
            mask = cs["agent_strategy"] == s_idx
            if not mask.any():
                continue
            sub_term = term[mask]
            sub_n = int(mask.sum())
            uq, ct = np.unique(sub_term, return_counts=True)
            edist = dict(zip(uq, ct))
            per_strategy[sname] = {
                "n": sub_n,
                "p_continued": 1 - edist.get("lineage_absorbed_or_lost", 0) / sub_n,
                "p_professional": edist.get("professional_manager_owner", 0) / sub_n,
                "p_edu_public": edist.get("education_public_clerical", 0) / sub_n,
                "p_company": edist.get("company_skilled_clerical", 0) / sub_n,
                "p_rural_farm": edist.get("rural_farm_part_time_farm", 0) / sub_n,
                "faith_class": cs["strategy_faith_class"][s_idx],
            }

        civ_results[cn] = {
            "name": cn,
            "label_jp": cs["civ_module"].label_jp,
            "n_total": n,
            "p_continued": p_continued,
            "n_continued": n_continued,
            "endpoint_dist": {k: int(v) for k, v in endpoint_dist.items()},
            "per_strategy": per_strategy,
            "religion_strength_final": cs["religion_strength"],
            "snapshots": civ_snapshots[cn],
            "cohort_chronicles": civ_cohort_chronicles[cn],
            "cohort_indices": civ_cohorts[cn][0],
            "family_chronicles": civ_family_chronicles[cn],
            "family_members": {k: int(v) for k, v in civ_family_members[cn].items()},
        }

    return {
        "civ_results": civ_results,
        "interaction_log": interaction_log,
        "encounter_log": encounter_log,
        "encounter_year": encounter_year,
        "encounter_civ": encounter_civ_state,
        "ahistorical_events": events_global,
        "black_swan_log": black_swan_log,
        "memetic_log": memetic_log,
        "counterfactual_scenarios": counterfactual_scenarios or [],
        "n_generations": n_generations,
        "year_horizon": n_generations * 40,
    }


def main():
    ap = argparse.ArgumentParser(
        description="World Simulation v6.1 — Unified Stage 2+3 with scale presets",
        formatter_class=argparse.RawTextHelpFormatter)

    # Civilization selection
    ap.add_argument("--civs",
                    default="Japan,China,Europe,Islamic,Indic,SubSaharan,Polynesian,Steppe,IndigenousAmericas",
                    help="Comma-separated civilizations (default: all 9)")

    # Scale preset
    scale_help = "\n".join([
        f"Scale preset (default: medium):",
        *[f"  {k:<8}: {v['description']} (RAM ~{v['expected_ram_mb']}MB, ~{v['expected_runtime_s']}s)"
          for k, v in SCALE_PRESETS.items()],
        f"  custom  : use --n_per_civ and --cohort_size",
    ])
    ap.add_argument("--scale", default="medium",
                    choices=list(SCALE_PRESETS.keys()) + ["custom"],
                    help=scale_help)

    # Custom scale
    ap.add_argument("--n_per_civ", type=int, default=None,
                    help="Agents per civilization (overrides preset)")
    ap.add_argument("--cohort_size", type=int, default=None,
                    help="Cohort size per civilization (overrides preset)")

    # Other
    ap.add_argument("--n_generations", type=int, default=75,
                    help="Number of generations (75 = 3000 years default)")
    ap.add_argument("--frequency", default="sporadic",
                    choices=["sporadic", "frequent", "sparse"])
    ap.add_argument("--encounter_civ", default=None,
                    help="Force encounter mechanism on a specific civilization")
    ap.add_argument("--no_ahistorical", action="store_true")
    ap.add_argument("--cohort_diversity", default="grid",
                    choices=["grid", "random", "strategy_balanced"])
    ap.add_argument("--seed", type=int, default=20260507)
    ap.add_argument("--outdir", default="outputs_v61")

    # Stage 4 features
    ap.add_argument("--memetic", action="store_true",
                    help="Enable memetic dynamics (replicator update of strategy distribution)")
    ap.add_argument("--memetic_drift", type=float, default=0.05,
                    help="Memetic drift rate (default 0.05)")
    ap.add_argument("--black_swan", action="store_true",
                    help="Enable Black Swan events (ultra-rare catastrophes)")
    ap.add_argument("--black_swan_intensity", type=float, default=1.0,
                    help="Black Swan intensity multiplier (default 1.0)")
    ap.add_argument("--counterfactual", default=None,
                    help="Comma-separated counterfactual scenarios "
                         f"(available: {','.join(COUNTERFACTUAL_SCENARIOS.keys())})")

    # vNext+ (v6.3) — Full Adaptive NRMOvNext + StrongEngine Ω Full
    ap.add_argument("--vnext_plus", action="store_true",
                    help="Enable full Adaptive NRMOvNext + StrongEngine Ω Full "
                         "(per-civ Tuning Layer + Ω Full pipeline; ~50%+ slower)")
    ap.add_argument("--no_archetype_classifier", action="store_true",
                    help="Disable Ω Full's world archetype classifier (default: enabled)")

    # vNext++ / NRMO v6.4 — All 13 enhancements (A-M)
    ap.add_argument("--nrmo_pp", action="store_true",
                    help="Enable v6.4 NRMO (vNext++) with all 13 enhancements (A-M): "
                         "asymmetric hysteresis, insurance layer, distributional state, "
                         "state-conditioned sigma, continuous mode, shared failure memory, "
                         "true optionality, online bandit tuning, synergy learning, "
                         "cumulative drift, counterfactual regret, hierarchical optionality, "
                         "early passive ruin detection. Supersedes --vnext_plus.")

    # NRMO Collective v7.0 — Collective governance extension (P-U)
    ap.add_argument("--collective", action="store_true",
                    help="Enable v7.0 NRMO Collective (P-U mechanisms on top of NRMO++): "
                         "multi-tier pooling, quorum coordination, strategy reproduction, "
                         "solidarity state, tradition blending, ultra-horizon. "
                         "Implies --nrmo_pp.")

    # NRMO Collective Engine v7.1 — Search engine for collective configurations
    ap.add_argument("--collective_engine", action="store_true",
                    help="Enable v7.1 Collective Strong Engine (W-AB mechanisms): "
                         "predictive trigger, triage optimization, pool reallocation, "
                         "inter-civ insurance, candidate exploration, drift control. "
                         "Implies --collective.")

    args = ap.parse_args()

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "per_civ_chronicles").mkdir(exist_ok=True)
    (out / "civ_trajectories").mkdir(exist_ok=True)

    # Parse civs
    civ_names = [c.strip() for c in args.civs.split(",")]
    available = list_cultural_modules()
    for cn in civ_names:
        if cn not in available:
            print(f"Error: civilization '{cn}' not found. Available: {available}")
            return

    # Determine scale
    if args.scale == "custom":
        if args.n_per_civ is None or args.cohort_size is None:
            print("Error: --scale custom requires --n_per_civ and --cohort_size")
            return
        n_per_civ = args.n_per_civ
        cohort_size = args.cohort_size
    else:
        preset = SCALE_PRESETS[args.scale]
        n_per_civ = args.n_per_civ if args.n_per_civ is not None else preset["n_per_civ"]
        cohort_size = args.cohort_size if args.cohort_size is not None else preset["cohort_size"]
        print(f"Scale preset: {args.scale}")
        print(f"  {preset['description']}")
        print(f"  Expected runtime: ~{preset['expected_runtime_s']}s, RAM: ~{preset['expected_ram_mb']}MB")

    # Counterfactual parsing
    cf_scenarios = None
    if args.counterfactual:
        cf_scenarios = [s.strip() for s in args.counterfactual.split(",")]

    # Run
    t0 = time.time()
    res = run_unified(
        civ_names=civ_names,
        n_per_civ=n_per_civ,
        cohort_size=cohort_size,
        n_generations=args.n_generations,
        seed=args.seed,
        frequency_mode=args.frequency,
        enable_ahistorical=not args.no_ahistorical,
        encounter_civ=args.encounter_civ,
        cohort_diversity=args.cohort_diversity,
        enable_memetic=args.memetic,
        memetic_drift_rate=args.memetic_drift,
        enable_black_swan=args.black_swan,
        black_swan_intensity=args.black_swan_intensity,
        counterfactual_scenarios=cf_scenarios,
        enable_vnext_plus=args.vnext_plus,
        enable_nrmo_pp=args.nrmo_pp or args.collective or args.collective_engine,
        enable_collective=args.collective or args.collective_engine,
        enable_collective_engine=args.collective_engine,
        enable_archetype_classifier=not args.no_archetype_classifier,
        verbose=True)
    rt = time.time() - t0

    print(f"\n{'='*72}")
    print(f"COMPLETE — Runtime: {rt:.1f}s")
    print(f"  Year horizon: {res['year_horizon']}")
    print(f"  Total agents: {len(civ_names) * n_per_civ:,}")
    total_chronicled = (cohort_size + 4) * len(civ_names)
    print(f"  Total chronicled individuals: {total_chronicled}")
    print(f"  Total inter-civ interactions: {len(res['interaction_log'])}")

    # === Save outputs ===
    # Per-civ outputs
    for cn, cr in res["civ_results"].items():
        # Per-civ cohort summary
        highlights = find_highlight_lives(cr["cohort_chronicles"])
        cohort_md = render_cohort_summary_report(
            cr["cohort_chronicles"], f"{cr['label_jp']} ({cn})",
            highlights, {"strategy": "grid"})
        (out / "per_civ_chronicles" / f"{cn}_cohort_summary.md").write_text(
            cohort_md, encoding="utf-8")

        # Per-civ family chronicle
        fam_md = render_family_chronicle(cr["family_chronicles"],
                                            DEFAULT_FAMILY_CONFIG,
                                            f"{cr['label_jp']} ({cn})")
        fam_md += "\n\n" + render_family_tree_ascii(cr["family_chronicles"],
                                                       DEFAULT_FAMILY_CONFIG)
        (out / "per_civ_chronicles" / f"{cn}_family_chronicle.md").write_text(
            fam_md, encoding="utf-8")

        # Per-civ trajectory CSV
        df = snapshots_to_dataframe(cr["snapshots"])
        df.to_csv(out / "civ_trajectories" / f"{cn}.csv", index=False)

    # Cross-civ strategy comparison
    rows_compare = []
    all_strategies = set()
    for cn, cr in res["civ_results"].items():
        all_strategies.update(cr["per_strategy"].keys())
    for sname in sorted(all_strategies):
        row = {"strategy": sname}
        for cn, cr in res["civ_results"].items():
            if sname in cr["per_strategy"]:
                row[cn] = composite_score(cr["per_strategy"][sname])
            else:
                row[cn] = None
        rows_compare.append(row)
    df_compare = pd.DataFrame(rows_compare)
    df_compare.to_csv(out / "cross_civ_strategy.csv", index=False)

    # Interaction summary
    interaction_md = render_interaction_summary(res["interaction_log"], args.n_generations)
    (out / "interaction_summary.md").write_text(interaction_md, encoding="utf-8")

    # Overall report
    overall_md = render_overall_report(res, civ_names, n_per_civ, cohort_size,
                                          args, rt, total_chronicled)
    (out / "v61_overall_report.md").write_text(overall_md, encoding="utf-8")

    # Full data JSON (light version)
    full_data = {
        "config": {
            "civs": civ_names, "scale": args.scale,
            "n_per_civ": n_per_civ, "cohort_size": cohort_size,
            "n_generations": args.n_generations,
            "frequency": args.frequency,
            "encounter_civ": args.encounter_civ,
        },
        "runtime_seconds": rt,
        "year_horizon": res["year_horizon"],
        "civ_summary": {
            cn: {
                "label_jp": cr["label_jp"],
                "p_continued": cr["p_continued"],
                "religion_strength_final": cr["religion_strength_final"],
                "endpoint_dist": cr["endpoint_dist"],
                "cohort_size": len(cr["cohort_chronicles"]),
                "cohort_stats": cohort_summary_stats(cr["cohort_chronicles"]),
            }
            for cn, cr in res["civ_results"].items()
        },
        "interactions": {
            "total": len(res["interaction_log"]),
            "by_channel": {ch: sum(1 for x in res["interaction_log"] if x["channel"] == ch)
                           for ch in ["trade", "war", "knowledge_diffusion", "disease_exchange"]},
        },
        "ahistorical_events": [{"year": e["year"], "label": e["label"]} for e in res["ahistorical_events"]],
    }
    (out / "full_data.json").write_text(
        json.dumps(full_data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")

    print(f"\nOutputs saved to: {out}/")
    print(f"  Per-civ cohort summaries:  per_civ_chronicles/<civ>_cohort_summary.md")
    print(f"  Per-civ family chronicles: per_civ_chronicles/<civ>_family_chronicle.md")
    print(f"  Per-civ trajectories:      civ_trajectories/<civ>.csv")
    print(f"  Cross-civ strategy:        cross_civ_strategy.csv")
    print(f"  Interaction summary:       interaction_summary.md")
    print(f"  Overall report:            v61_overall_report.md")
    print(f"  Full data JSON:            full_data.json")


def render_overall_report(res, civ_names, n_per_civ, cohort_size, args, rt, total_chronicled):
    """Render the overall executive summary."""
    lines = []
    lines.append(f"# World Simulation v6.1 — Unified Run Report")
    lines.append(f"")
    lines.append(f"## Configuration")
    lines.append(f"")
    lines.append(f"- **Civilizations**: {len(civ_names)} ({', '.join(civ_names)})")
    lines.append(f"- **Scale**: {args.scale}")
    lines.append(f"- **Per-civ agents**: {n_per_civ:,}")
    lines.append(f"- **Total agents**: {len(civ_names) * n_per_civ:,}")
    lines.append(f"- **Per-civ cohort**: {cohort_size}")
    lines.append(f"- **Total chronicled individuals**: {total_chronicled}")
    lines.append(f"- **Generations**: {args.n_generations} ({args.n_generations*40} years)")
    lines.append(f"- **Frequency mode**: {args.frequency}")
    lines.append(f"- **Encounter civilization**: {args.encounter_civ or 'none'}")
    lines.append(f"- **Runtime**: {rt:.1f} seconds")
    lines.append(f"")

    lines.append(f"## Per-Civilization Summary")
    lines.append(f"")
    lines.append(f"| Civ | Continuation | Religion Final | Top Strategy | Cohort Survival |")
    lines.append(f"|---|---:|---:|---|---:|")
    for cn, cr in res["civ_results"].items():
        rows = [(sname, composite_score(stats))
                for sname, stats in cr["per_strategy"].items()]
        rows.sort(key=lambda x: -x[1])
        top_strat = rows[0][0] if rows else "?"
        cohort_stats = cohort_summary_stats(cr["cohort_chronicles"])
        cohort_surv = cohort_stats.get("p_survival", 0)
        lines.append(f"| {cr['label_jp']} ({cn}) | {cr['p_continued']*100:.1f}% | "
                     f"{cr['religion_strength_final']:.2f} | {top_strat} | "
                     f"{cohort_surv*100:.1f}% |")
    lines.append(f"")

    lines.append(f"## Inter-Civilization Interactions")
    lines.append(f"")
    by_channel = {}
    for ev in res["interaction_log"]:
        by_channel[ev["channel"]] = by_channel.get(ev["channel"], 0) + 1
    for ch in ["trade", "war", "knowledge_diffusion", "disease_exchange"]:
        c = by_channel.get(ch, 0)
        lines.append(f"- {ch}: {c}")
    lines.append(f"- **Total**: {len(res['interaction_log'])}")
    lines.append(f"")

    if res["encounter_civ"]:
        lines.append(f"## Encounter Event")
        lines.append(f"- **Civilization**: {res['encounter_civ']}")
        lines.append(f"- **Year**: {res['encounter_year']}")
        lines.append(f"- **Generations affected**: {len(res['encounter_log'])}")
        lines.append(f"")

    if res.get("black_swan_log"):
        lines.append(f"## Black Swan Events ({len(res['black_swan_log'])})")
        for bs in res["black_swan_log"]:
            lines.append(f"- Year {bs['year']}: **{bs['label']}** "
                         f"(scope {bs['scope']}, shock {bs['shock_magnitude']:.2f}, "
                         f"mortality {bs['mortality_p']:.2f})")
        lines.append(f"")

    if res.get("memetic_log"):
        lines.append(f"## Memetic Dynamics Log ({len(res['memetic_log'])} samples)")
        lines.append(f"Strategy fitness evolved over generations.")
        lines.append(f"")

    if res.get("counterfactual_scenarios"):
        lines.append(f"## Counterfactual Mode")
        for s in res["counterfactual_scenarios"]:
            if s in COUNTERFACTUAL_SCENARIOS:
                lines.append(f"- **{s}**: {COUNTERFACTUAL_SCENARIOS[s]['description']}")
        lines.append(f"")

    if res["ahistorical_events"]:
        lines.append(f"## Ahistorical Events ({len(res['ahistorical_events'])})")
        for ev in res["ahistorical_events"][:10]:
            lines.append(f"- Year {ev['year']}: {ev['label']} ({ev.get('dim', '?')})")
        if len(res["ahistorical_events"]) > 10:
            lines.append(f"- ... and {len(res['ahistorical_events']) - 10} more")
        lines.append(f"")

    # Calibration check
    sim_p = {cn: cr["p_continued"] for cn, cr in res["civ_results"].items()}
    lines.append(render_calibration_report(sim_p))

    return "\n".join(lines)


if __name__ == "__main__":
    main()
