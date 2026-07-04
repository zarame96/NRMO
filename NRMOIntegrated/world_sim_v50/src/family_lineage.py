"""
Phase 10B: Family Lineage Portfolio (Multi-Branch).

Re-implements v4.1's Multi-Branch Portfolio in the world simulation context.
A spotlight 'family' is a collection of branches (本家・分家・養子先) that
share an origin but diverge in strategy and trajectory.

Each family has:
- A founder branch (本家): primary heir, conservative strategy by default
- 1-3 cadet branches (分家): differentiated strategies
- 0-2 adopted-into branches (養子先): linked through marriage/adoption

The family survives if AT LEAST ONE branch survives. The final state of
the family is the BEST surviving branch's terminal category.

Output: family tree visualization + branch-by-branch chronicle.
"""
import numpy as np


# Default family configuration
DEFAULT_FAMILY_CONFIG = {
    "honke": {       # 本家 (main heir)
        "label": "本家 (main lineage)",
        "weight": 0.40,
        "strategy_preference": "Faith_Communal",   # most distribution-heavy
    },
    "bunke_1": {     # 分家 1
        "label": "分家 (first cadet branch)",
        "weight": 0.25,
        "strategy_preference": "NRMO_vNext",
    },
    "bunke_2": {     # 分家 2
        "label": "分家 (second cadet branch)",
        "weight": 0.20,
        "strategy_preference": "ExpectedValueMax",
    },
    "yoshi": {       # 養子先
        "label": "養子先 (adopted-into branch)",
        "weight": 0.15,
        "strategy_preference": "Adaptive_OmegaFull",
    },
}


def select_family_branches(rng, agent_strategy, strategy_names, region, occ,
                            n_branches=4, family_config=None):
    """Select a coherent family from the agent population.

    A 'family' here = one agent per branch role, located in the same
    starting region, with strategies matching the family preferences.

    Returns: dict {branch_role: agent_global_idx}
    """
    family_config = family_config or DEFAULT_FAMILY_CONFIG
    branch_roles = list(family_config.keys())[:n_branches]

    # Find agents matching each branch's preferred strategy
    family_members = {}
    used_indices = set()

    # Pick a starting region (whatever has lots of agents)
    region_counts = np.bincount(region, minlength=int(region.max()) + 1)
    primary_region = int(region_counts.argmax())

    for role in branch_roles:
        cfg = family_config[role]
        pref_strategy = cfg["strategy_preference"]
        if pref_strategy not in strategy_names:
            # Fallback: any strategy
            pref_strategy = strategy_names[0]
        s_idx = strategy_names.index(pref_strategy)

        candidates = np.where(
            (agent_strategy == s_idx)
            & (region == primary_region)
        )[0]
        # Exclude already-used
        candidates = [c for c in candidates if c not in used_indices]
        if not candidates:
            # Loosen region constraint
            candidates = [c for c in np.where(agent_strategy == s_idx)[0] if c not in used_indices]
        if not candidates:
            continue
        chosen = int(rng.choice(candidates))
        family_members[role] = chosen
        used_indices.add(chosen)

    return family_members, primary_region


def render_family_chronicle(family_records, family_config, world_name):
    """Render the family chronicle as human-readable text."""
    lines = []
    lines.append(f"# Family Lineage Chronicle — {world_name}")
    lines.append(f"")
    lines.append(f"Branches tracked: {len(family_records)}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    family_config = family_config or DEFAULT_FAMILY_CONFIG

    # Branch summaries
    for role, records in family_records.items():
        cfg = family_config.get(role, {})
        lines.append(f"## {cfg.get('label', role)}")
        if not records:
            lines.append("- No records (branch not founded).")
            continue
        first = records[0]
        last = records[-1]
        survived = last.get('alive', True)
        lines.append(f"- Strategy: **{first['strategy']}**")
        lines.append(f"- Founding region: {first['region']}")
        lines.append(f"- Founding occupation: {first['occupation']}")
        if survived:
            lines.append(f"- **Survived** to generation {last['generation']} (year {last['year_at_end_of_gen']})")
            lines.append(f"  - Final occupation: **{last['occupation']}**")
            lines.append(f"  - Final region: **{last['region']}**")
            lines.append(f"  - Final education: {last['edu']:.3f}, assets: {last['assets']:.3f}")
        else:
            lines.append(f"- **Absorbed** at generation {last['generation']} (year {last['year_at_end_of_gen']})")
            if len(records) >= 2:
                lines.append(f"  - Last occupation before loss: {records[-2]['occupation']}")

        # Crises
        crises = [r for r in records if r['decision_type'] == 'crisis_response']
        if crises:
            lines.append(f"  - Crises encountered: {len(crises)}")

        # Career changes
        transitions = [r for r in records if r['occupation_changed']]
        if transitions:
            lines.append(f"  - Career transitions: {len(transitions)}")

        # Emotional arc
        emotions = [r['emotion'] for r in records]
        if emotions:
            from collections import Counter
            top_emotions = Counter(emotions).most_common(3)
            emo_str = ", ".join(f"{e}({c})" for e, c in top_emotions)
            lines.append(f"  - Dominant emotions: {emo_str}")
        lines.append("")

    # Family-level summary
    n_survived = sum(1 for r in family_records.values()
                      if r and r[-1].get('alive', True))
    n_total = len(family_records)
    lines.append(f"## Family Survival Summary")
    lines.append(f"- Branches founded: {n_total}")
    lines.append(f"- Branches surviving: **{n_survived}**")
    lines.append(f"- Family continuity: {'YES' if n_survived > 0 else 'NO'}")

    # Best terminal among surviving branches
    rank_order = ["lineage_absorbed_or_lost", "rural_farm_part_time_farm",
                  "urban_wage_labor", "craft_trade_self_employed",
                  "company_skilled_clerical", "education_public_clerical",
                  "professional_manager_owner"]
    best_term = "lineage_absorbed_or_lost"
    best_role = None
    for role, records in family_records.items():
        if records and records[-1].get('alive', True):
            term = records[-1].get('terminal_category', 'unknown')
            if term in rank_order:
                if rank_order.index(term) > rank_order.index(best_term):
                    best_term = term
                    best_role = role
    if best_role:
        lines.append(f"- Best terminal outcome: **{best_term}** (via {family_config[best_role]['label']})")

    lines.append("")
    return "\n".join(lines)


def render_family_tree_ascii(family_records, family_config):
    """Render an ASCII family tree showing branches and their fates."""
    lines = []
    family_config = family_config or DEFAULT_FAMILY_CONFIG
    lines.append("```")
    lines.append("FOUNDER")
    lines.append("│")

    roles = list(family_records.keys())
    for i, role in enumerate(roles):
        is_last = (i == len(roles) - 1)
        prefix = "└─" if is_last else "├─"
        cont_prefix = "  " if is_last else "│ "
        cfg = family_config.get(role, {})
        records = family_records[role]
        if not records:
            lines.append(f"{prefix} {cfg.get('label', role)}: NOT FOUNDED")
            continue
        last = records[-1]
        survived = last.get('alive', True)
        status = "SURVIVED" if survived else "LOST"
        terminal = last.get('terminal_category', '?') if survived else '—'
        lines.append(f"{prefix} {cfg.get('label', role)}")
        lines.append(f"{cont_prefix}   Strategy: {records[0]['strategy']}")
        lines.append(f"{cont_prefix}   Status: {status}")
        if survived:
            lines.append(f"{cont_prefix}   Terminal: {terminal}")
            lines.append(f"{cont_prefix}   Final occupation: {last['occupation']}")
        else:
            gen_lost = last['generation']
            lines.append(f"{cont_prefix}   Lost at generation {gen_lost}")
    lines.append("```")
    return "\n".join(lines)
