"""
Phase 10A: Individual Life Chronicle.

Tracks a single 'spotlight' agent at full per-generation resolution,
recording:
- Decision moments (career transition, inheritance, migration)
- Subjective experience (emotional valence at key events)
- State trajectory (occupation, region, education, assets, family knowledge)
- Events that affected this individual personally

Each generation in the simulation = ~40 years of one person's life
(or one family generation; in this model these are conflated).

Output: human-readable life chronicle + structured JSON.
"""
import numpy as np


# Decision moment types
DECISION_TYPES = {
    "founder":          "First-generation: establishing the lineage",
    "career_transition": "Significant occupation change",
    "regional_move":     "Migration between regions",
    "inheritance":       "Receiving family wealth/position",
    "branching":         "Generation establishing a cadet branch",
    "crisis_response":   "Response to major shock event",
    "encounter":         "Encounter with unknown civilization",
    "ahistorical":       "Response to ahistorical event",
    "absorption":        "Lineage end (this agent's line lost)",
}


def emotion_for_event(occupation_change, region_change, shock_severity,
                       prosperity_change, is_terminal):
    """Classify subjective emotion based on state transitions.

    Returns dominant emotion label and intensity (0-1).
    """
    if is_terminal:
        return ("loss", 0.95)
    if shock_severity > 0.15:
        return ("fear", min(0.95, 0.5 + shock_severity * 2))
    if shock_severity > 0.08 and prosperity_change < -0.05:
        return ("grief", min(0.85, 0.4 + shock_severity * 2))
    if prosperity_change > 0.10:
        return ("pride", min(0.85, 0.4 + prosperity_change * 3))
    if occupation_change and prosperity_change > 0:
        return ("hope", 0.65)
    if region_change:
        return ("disorientation", 0.55)
    if shock_severity > 0.04:
        return ("anxiety", 0.50)
    return ("equanimity", 0.30)


def record_decision_moment(chronicle, gen, year, agent_state, action_chosen,
                             prev_state=None, gen_events=None,
                             encounter_active=False):
    """Append a Decision Moment record to the chronicle."""
    g, s, l, d = action_chosen
    occupation = agent_state["occupation"]
    region = agent_state["region"]
    edu = agent_state["edu"]
    assets = agent_state["assets"]
    fk = agent_state["fk"]
    inst = agent_state["inst"]
    strategy = agent_state["strategy"]

    occ_change = (prev_state and prev_state["occupation"] != occupation) if prev_state else False
    region_change = (prev_state and prev_state["region"] != region) if prev_state else False
    prosperity_change = (assets - prev_state["assets"]) if prev_state else 0.0

    shock_severity = 0.0
    if gen_events:
        for e in gen_events:
            shock_severity = max(shock_severity, e.get("magnitude", 0))

    is_terminal = agent_state.get("absorbed", False)

    emotion, intensity = emotion_for_event(occ_change, region_change,
                                             shock_severity, prosperity_change,
                                             is_terminal)

    decision_type = "career_transition" if occ_change else (
        "regional_move" if region_change else "ongoing")
    if gen == 1:
        decision_type = "founder"
    if shock_severity > 0.10:
        decision_type = "crisis_response"
    if encounter_active:
        decision_type = "encounter"
    if gen_events and any(e.get("type") == "ahistorical" for e in gen_events):
        decision_type = "ahistorical"
    if is_terminal:
        decision_type = "absorption"

    record = {
        "generation": gen,
        "year_at_end_of_gen": year,
        "occupation": occupation,
        "region": region,
        "strategy": strategy,
        "edu": float(edu),
        "assets": float(assets),
        "family_knowledge": float(fk),
        "inst": float(inst),
        "action_g": float(g),
        "action_s": float(s),
        "action_l": float(l),
        "action_d": float(d),
        "decision_type": decision_type,
        "decision_meaning": DECISION_TYPES.get(decision_type, "ongoing"),
        "events_this_gen": [e.get("label", "?") for e in (gen_events or [])],
        "shock_severity": float(shock_severity),
        "occupation_changed": bool(occ_change),
        "region_changed": bool(region_change),
        "prosperity_change": float(prosperity_change),
        "emotion": emotion,
        "emotion_intensity": float(intensity),
        "alive": not is_terminal,
    }
    chronicle.append(record)


def render_life_chronicle(chronicle, world_name, n_world_total):
    """Render the individual chronicle as human-readable narrative."""
    lines = []
    lines.append(f"# Individual Life Chronicle — Spotlight in {world_name}")
    lines.append(f"")
    lines.append(f"Total agents in this world: {n_world_total:,}")
    lines.append(f"Generations recorded: {len(chronicle)}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    if not chronicle:
        lines.append("No chronicle data available.")
        return "\n".join(lines)

    # Founder
    first = chronicle[0]
    lines.append(f"## Founder (Generation 1, year ~{first['year_at_end_of_gen']})")
    lines.append(f"- Region: **{first['region']}**")
    lines.append(f"- Occupation: **{first['occupation']}**")
    lines.append(f"- Decision strategy: **{first['strategy']}**")
    lines.append(f"- Initial state: education {first['edu']:.3f}, "
                 f"assets {first['assets']:.3f}, "
                 f"institutional access {first['inst']:.3f}")
    lines.append("")

    # Mid-life
    mid_gen = len(chronicle) // 2
    if mid_gen > 0 and mid_gen < len(chronicle):
        mid = chronicle[mid_gen]
        lines.append(f"## Mid-life (Generation {mid['generation']}, "
                     f"year {mid['year_at_end_of_gen']})")
        lines.append(f"- {mid['region']} / {mid['occupation']}")
        lines.append(f"- Education: {mid['edu']:.3f}, Assets: {mid['assets']:.3f}")
        if mid['events_this_gen']:
            lines.append(f"- World events affecting this generation: "
                         f"{', '.join(mid['events_this_gen'])}")
        lines.append(f"- Dominant emotion: *{mid['emotion']}* "
                     f"(intensity {mid['emotion_intensity']:.2f})")
        lines.append("")

    # Crisis moments
    crises = [c for c in chronicle if c['decision_type'] == 'crisis_response']
    if crises:
        lines.append(f"## Crises Survived ({len(crises)})")
        for c in crises:
            lines.append(f"- Gen {c['generation']} (year {c['year_at_end_of_gen']}): "
                         f"{c['emotion']} during {', '.join(c['events_this_gen'])} — "
                         f"prosperity {c['prosperity_change']:+.3f}")
        lines.append("")

    # Career transitions
    transitions = [c for c in chronicle if c['occupation_changed']]
    if transitions:
        lines.append(f"## Career Transitions ({len(transitions)})")
        for t in transitions[:5]:
            lines.append(f"- Gen {t['generation']}: → {t['occupation']} "
                         f"(emotion: {t['emotion']})")
        if len(transitions) > 5:
            lines.append(f"- ... and {len(transitions) - 5} more transitions")
        lines.append("")

    # Encounter or ahistorical
    encounters = [c for c in chronicle if c['decision_type'] in ('encounter', 'ahistorical')]
    if encounters:
        lines.append(f"## Extraordinary Events Witnessed ({len(encounters)})")
        for e in encounters:
            lines.append(f"- Gen {e['generation']} (year {e['year_at_end_of_gen']}): "
                         f"{e['decision_meaning']} — {', '.join(e['events_this_gen'])}")
        lines.append("")

    # End state
    last = chronicle[-1]
    if last['alive']:
        lines.append(f"## Final State (Generation {last['generation']}, "
                     f"year {last['year_at_end_of_gen']})")
        lines.append(f"- Region: **{last['region']}**")
        lines.append(f"- Occupation: **{last['occupation']}**")
        lines.append(f"- Education: {last['edu']:.3f}")
        lines.append(f"- Assets: {last['assets']:.3f}")
        lines.append(f"- Lineage continued.")
    else:
        lines.append(f"## Lineage Lost (Generation {last['generation']})")
        lines.append(f"- Final occupation: {chronicle[-2]['occupation'] if len(chronicle) >= 2 else 'unknown'}")
        lines.append(f"- Lineage absorbed at year ~{last['year_at_end_of_gen']}.")

    return "\n".join(lines)


def emotional_arc_summary(chronicle):
    """Return summary statistics on the emotional arc."""
    emotions = [c['emotion'] for c in chronicle]
    intensities = [c['emotion_intensity'] for c in chronicle]
    if not emotions:
        return {}
    counts = {}
    for e in emotions:
        counts[e] = counts.get(e, 0) + 1
    return {
        "dominant_emotion": max(counts, key=counts.get),
        "emotion_distribution": counts,
        "mean_intensity": float(np.mean(intensities)),
        "max_intensity": float(np.max(intensities)),
        "n_high_intensity_moments": sum(1 for i in intensities if i > 0.7),
    }
