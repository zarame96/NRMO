"""
v5.5 Stage 2: Spotlight Cohort — 100+ Named Individuals.

Extends v5.2's single Spotlight individual to a population of 100+
named individuals tracked simultaneously, with full life chronicles
for each.

Selection strategy: stratified sampling across:
- decision strategy (NRMO_vNext, Faith_Buddhist, EVMax, Drift, etc.)
- initial region (6 regions)
- founding occupation tier (rural agrarian, rural notable, craft trade, etc.)
- birth generation (gen 1, 5, 10, 20, 30, 50)

This ensures diversity of trajectories rather than 100 NRMO farmers.

Output:
- Per-individual full life chronicle (same format as v5.2's single subject)
- Aggregated cohort statistics (emotion distributions, decision moments,
  career transitions across the cohort)
- Highlight reports (most successful, most tragic, most unusual lives)
"""
import numpy as np
from collections import defaultdict


def select_cohort(rng, agent_strategy, strategy_names, region, occ,
                   absorbed, n_cohort=100, diversity_strategy="grid"):
    """Select a diverse cohort of n_cohort agents to spotlight.

    diversity_strategy:
    - "grid": stratified across (strategy × region × occupation_tier)
    - "random": purely random selection
    - "strategy_balanced": equal counts per strategy

    Returns: list of agent indices (global), with metadata dict.
    """
    n_total = len(agent_strategy)
    active = ~absorbed
    active_indices = np.where(active)[0]

    if len(active_indices) < n_cohort:
        # Just return all active ones if can't reach n_cohort
        return active_indices.tolist(), {"strategy": "all_active"}

    if diversity_strategy == "random":
        chosen = rng.choice(active_indices, size=n_cohort, replace=False)
        return chosen.tolist(), {"strategy": "random"}

    if diversity_strategy == "strategy_balanced":
        per_strategy = max(1, n_cohort // len(strategy_names))
        chosen = []
        for s_idx, sname in enumerate(strategy_names):
            mask = (agent_strategy == s_idx) & active
            candidates = np.where(mask)[0]
            if len(candidates) == 0:
                continue
            n_pick = min(per_strategy, len(candidates))
            picks = rng.choice(candidates, size=n_pick, replace=False)
            chosen.extend(picks.tolist())
        return chosen[:n_cohort], {"strategy": "strategy_balanced"}

    # Grid: try to populate 3D grid (strategy × region × occupation_tier)
    n_strategies = len(strategy_names)
    n_regions = int(region.max()) + 1

    # Occupation tier (0-3): agrarian, notable, craft, urban
    def occ_tier(o):
        if o in [0]:           # agrarian
            return 0
        elif o in [1, 2, 3]:   # notable, temple, warrior
            return 1
        elif o in [4, 5]:      # craft, merchant
            return 2
        else:                  # urban_wage, industrial, company, edu, prof
            return 3

    occ_tiers = np.array([occ_tier(int(o)) for o in occ])
    n_tiers = 4

    # Compute target per-cell count
    n_cells = n_strategies * n_regions * n_tiers
    per_cell = max(1, n_cohort // n_cells)

    chosen = []
    cell_counts = defaultdict(int)
    for s_idx in range(n_strategies):
        for r_idx in range(n_regions):
            for t_idx in range(n_tiers):
                mask = ((agent_strategy == s_idx)
                        & (region == r_idx)
                        & (occ_tiers == t_idx)
                        & active)
                candidates = np.where(mask)[0]
                if len(candidates) == 0:
                    continue
                n_pick = min(per_cell, len(candidates))
                picks = rng.choice(candidates, size=n_pick, replace=False)
                for p in picks:
                    chosen.append(int(p))
                    cell_counts[(s_idx, r_idx, t_idx)] += 1
                    if len(chosen) >= n_cohort:
                        break
                if len(chosen) >= n_cohort:
                    break
            if len(chosen) >= n_cohort:
                break
        if len(chosen) >= n_cohort:
            break

    # If still under n_cohort, fill with random
    if len(chosen) < n_cohort:
        already = set(chosen)
        remaining = [i for i in active_indices.tolist() if i not in already]
        n_more = n_cohort - len(chosen)
        if remaining:
            extra = rng.choice(remaining, size=min(n_more, len(remaining)), replace=False)
            chosen.extend([int(x) for x in extra])

    return chosen[:n_cohort], {
        "strategy": "grid",
        "n_cells_filled": len(cell_counts),
        "n_cells_total": n_cells,
    }


def create_cohort_chronicles(cohort_indices):
    """Initialize empty chronicle storage for cohort."""
    return {idx: [] for idx in cohort_indices}


def cohort_summary_stats(cohort_chronicles):
    """Compute aggregate statistics across cohort."""
    n_total = len(cohort_chronicles)
    if n_total == 0:
        return {}

    n_alive_final = 0
    emotion_counts = defaultdict(int)
    n_crises_total = 0
    n_career_transitions_total = 0
    n_encounters_total = 0
    n_ahistorical_total = 0
    final_education = []
    final_assets = []

    for idx, chronicle in cohort_chronicles.items():
        if not chronicle:
            continue
        last = chronicle[-1]
        if last.get("alive", True):
            n_alive_final += 1
            final_education.append(last.get("edu", 0))
            final_assets.append(last.get("assets", 0))

        for record in chronicle:
            emotion_counts[record.get("emotion", "unknown")] += 1
            if record.get("decision_type") == "crisis_response":
                n_crises_total += 1
            if record.get("occupation_changed"):
                n_career_transitions_total += 1
            if record.get("decision_type") == "encounter":
                n_encounters_total += 1
            if record.get("decision_type") == "ahistorical":
                n_ahistorical_total += 1

    return {
        "n_total": n_total,
        "n_alive_final": n_alive_final,
        "p_survival": n_alive_final / n_total if n_total else 0,
        "emotion_distribution": dict(emotion_counts),
        "n_crises_total": n_crises_total,
        "n_career_transitions_total": n_career_transitions_total,
        "n_encounters_total": n_encounters_total,
        "n_ahistorical_total": n_ahistorical_total,
        "mean_final_edu": float(np.mean(final_education)) if final_education else 0,
        "mean_final_assets": float(np.mean(final_assets)) if final_assets else 0,
    }


def find_highlight_lives(cohort_chronicles, n_highlights=5):
    """Find notable individuals: most successful, most tragic, most unusual."""
    if not cohort_chronicles:
        return {}

    rankings = {
        "most_successful": [],   # highest final education + assets
        "most_resilient": [],    # most crises survived
        "most_dynamic": [],      # most career transitions
        "tragic_loss": [],       # ended absorbed
        "stayed_humble": [],     # ended rural farm
    }

    for idx, chronicle in cohort_chronicles.items():
        if not chronicle:
            continue
        last = chronicle[-1]
        is_alive = last.get("alive", True)

        # Successful
        if is_alive:
            success_score = last.get("edu", 0) + last.get("assets", 0)
            rankings["most_successful"].append((idx, success_score, chronicle))

        # Resilient
        n_crises = sum(1 for r in chronicle if r.get("decision_type") == "crisis_response")
        if is_alive and n_crises > 0:
            rankings["most_resilient"].append((idx, n_crises, chronicle))

        # Dynamic
        n_transitions = sum(1 for r in chronicle if r.get("occupation_changed"))
        rankings["most_dynamic"].append((idx, n_transitions, chronicle))

        # Tragic
        if not is_alive:
            n_recorded = len(chronicle)
            rankings["tragic_loss"].append((idx, n_recorded, chronicle))

        # Humble
        if is_alive and "agrarian" in str(last.get("occupation", "")).lower():
            rankings["stayed_humble"].append((idx, last.get("edu", 0), chronicle))

    highlights = {}
    for category, items in rankings.items():
        # Sort: most_successful etc. = descending; tragic_loss = descending (longer life worse)
        items.sort(key=lambda x: -x[1])
        highlights[category] = items[:n_highlights]
    return highlights


def render_cohort_summary_report(cohort_chronicles, world_name, highlights,
                                    cohort_meta):
    """Render an aggregated cohort report (markdown)."""
    stats = cohort_summary_stats(cohort_chronicles)
    lines = []
    lines.append(f"# Cohort Life Chronicle Report — {world_name}")
    lines.append(f"")
    lines.append(f"## Cohort Overview")
    lines.append(f"")
    lines.append(f"- **Cohort size**: {stats['n_total']} individuals")
    lines.append(f"- **Selection strategy**: {cohort_meta.get('strategy', 'grid')}")
    if "n_cells_filled" in cohort_meta:
        lines.append(f"- **Diversity grid**: {cohort_meta['n_cells_filled']}/{cohort_meta['n_cells_total']} cells filled")
    lines.append(f"- **Survival rate**: {stats['p_survival']*100:.1f}% ({stats['n_alive_final']}/{stats['n_total']})")
    lines.append(f"- **Mean final education**: {stats['mean_final_edu']:.3f}")
    lines.append(f"- **Mean final assets**: {stats['mean_final_assets']:.3f}")
    lines.append(f"")

    lines.append(f"## Aggregated Life Events")
    lines.append(f"")
    lines.append(f"- Total crises encountered: {stats['n_crises_total']}")
    lines.append(f"- Total career transitions: {stats['n_career_transitions_total']}")
    lines.append(f"- Total encounters with unknowns: {stats['n_encounters_total']}")
    lines.append(f"- Total ahistorical events witnessed: {stats['n_ahistorical_total']}")
    lines.append(f"")

    lines.append(f"## Emotional Arc Distribution (cohort-wide)")
    lines.append(f"")
    total_records = sum(stats['emotion_distribution'].values())
    for emo, count in sorted(stats['emotion_distribution'].items(), key=lambda x: -x[1]):
        pct = count / total_records * 100 if total_records else 0
        lines.append(f"- {emo}: {count} ({pct:.1f}%)")
    lines.append(f"")

    lines.append(f"## Highlight Lives")
    lines.append(f"")

    for category, items in highlights.items():
        if not items:
            continue
        lines.append(f"### {category.replace('_', ' ').title()}")
        lines.append(f"")
        for idx, score, chronicle in items[:3]:
            if not chronicle:
                continue
            first = chronicle[0]
            last = chronicle[-1]
            n_gens = len(chronicle)
            lines.append(f"- **Individual #{idx}** ({first.get('strategy', '?')}, "
                         f"founder year {first.get('year_at_end_of_gen', '?')-40} in {first.get('region', '?')}):")
            lines.append(f"  - Score: {score:.3f}, Generations recorded: {n_gens}")
            if last.get("alive", True):
                lines.append(f"  - Final: {last.get('occupation', '?')} in {last.get('region', '?')}, "
                             f"edu {last.get('edu', 0):.2f}, assets {last.get('assets', 0):.2f}")
            else:
                lines.append(f"  - **Lineage absorbed** at year {last.get('year_at_end_of_gen', '?')}")
        lines.append(f"")

    return "\n".join(lines)


def render_cohort_compact_chronicles(cohort_chronicles, max_individuals=10):
    """Compact chronicle view for first N individuals (sample)."""
    lines = []
    lines.append(f"# Sample Individual Chronicles (first {max_individuals})")
    lines.append(f"")

    sample_indices = list(cohort_chronicles.keys())[:max_individuals]
    for idx in sample_indices:
        chronicle = cohort_chronicles[idx]
        if not chronicle:
            continue
        first = chronicle[0]
        last = chronicle[-1]
        n_gens = len(chronicle)

        lines.append(f"## Individual #{idx}")
        lines.append(f"- Founder: {first.get('strategy', '?')} in {first.get('region', '?')}")
        lines.append(f"- Founding occupation: {first.get('occupation', '?')}")

        # Crisis count
        n_crises = sum(1 for r in chronicle if r.get("decision_type") == "crisis_response")
        n_transitions = sum(1 for r in chronicle if r.get("occupation_changed"))

        if last.get("alive", True):
            lines.append(f"- **Survived** {n_gens} generations to year {last.get('year_at_end_of_gen', '?')}")
            lines.append(f"  - Final occupation: {last.get('occupation', '?')}")
            lines.append(f"  - Final edu: {last.get('edu', 0):.3f}, assets: {last.get('assets', 0):.3f}")
        else:
            lines.append(f"- Lineage lost at generation {last.get('generation', '?')} "
                         f"(year {last.get('year_at_end_of_gen', '?')})")

        lines.append(f"  - Crises encountered: {n_crises}")
        lines.append(f"  - Career transitions: {n_transitions}")

        # Top 3 emotions
        from collections import Counter
        emotions = [r.get("emotion", "?") for r in chronicle]
        top = Counter(emotions).most_common(3)
        emo_str = ", ".join(f"{e}({c})" for e, c in top)
        lines.append(f"  - Top emotions: {emo_str}")
        lines.append(f"")

    return "\n".join(lines)
