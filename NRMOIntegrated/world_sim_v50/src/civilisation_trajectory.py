"""
Phase 10C: Civilisation Trajectory Tracking.

Records the entire civilisation-level trajectory generation by generation:
- Aggregate state (R, E, G, O, K, X) over time
- Strategy distribution evolution (memetic dynamics)
- Population dynamics (alive count, birth/death/branching)
- Major events impact summary
- Religion strength trajectory
- Tech level trajectory
- Phase/era summary

Output: civilisation history chronicle + plot-ready CSV.
"""
import numpy as np


def record_civilisation_snapshot(snapshots, gen, year, era_name,
                                  active_count, total_count,
                                  fk, edu, inst, trade, assets, urban,
                                  agent_strategy, strategy_names,
                                  religion_strength, tech_factor,
                                  shock_add, gen_events, encounter_active):
    """Record a per-generation snapshot of the civilisation state.

    Aggregate state across all surviving agents.
    """
    if active_count == 0:
        snapshots.append({
            "generation": gen,
            "year": year,
            "era": era_name,
            "alive": False,
            "extinct": True,
        })
        return

    # Aggregate state
    snapshot = {
        "generation": gen,
        "year": year,
        "era": era_name,
        "alive": True,
        "active_count": int(active_count),
        "total_count": int(total_count),
        "p_alive": float(active_count / max(total_count, 1)),

        # 6-dim aggregate state
        "mean_assets_R": float(assets.mean()),
        "mean_environ_E": float(np.clip(1 - shock_add * 5, 0, 1)),  # peace_buffer
        "mean_govern_G": float(inst.mean()),
        "mean_optional_O": float((0.5 * fk + 0.5 * edu).mean()),
        "mean_knowl_K": float(edu.mean()),
        "mean_exposure_X": float(np.clip(shock_add * 4 + (1 - inst.mean()) * 0.3, 0, 1)),

        # Tech and religion
        "religion_strength": float(religion_strength),
        "tech_factor": float(tech_factor),
        "shock_this_gen": float(shock_add),

        # Strategy distribution (proportion of active agents per strategy)
        "strategy_dist": {},

        # Events
        "events_this_gen": [e.get("label", "?") for e in (gen_events or [])],
        "n_events": len(gen_events or []),
        "encounter_active": bool(encounter_active),
    }

    # Per-strategy active counts
    for s_idx, sname in enumerate(strategy_names):
        snapshot["strategy_dist"][sname] = float(
            (agent_strategy == s_idx).sum() / max(active_count, 1)
        )

    snapshots.append(snapshot)


def detect_phases(snapshots):
    """Detect major phases in civilisation trajectory.

    A phase is a contiguous span of generations with similar state
    characteristics. Returns list of phase descriptors.
    """
    if not snapshots or len(snapshots) < 2:
        return []

    phases = []
    current_phase = None

    for snap in snapshots:
        if not snap.get("alive", True):
            continue
        # Define phase characteristics
        if snap["mean_exposure_X"] > 0.55:
            phase_label = "crisis"
        elif snap["mean_assets_R"] > 0.45:
            phase_label = "prosperity"
        elif snap["mean_knowl_K"] > 0.35:
            phase_label = "enlightenment"
        elif snap["mean_govern_G"] > 0.40:
            phase_label = "stable_governance"
        else:
            phase_label = "developing"

        if current_phase is None or current_phase["label"] != phase_label:
            if current_phase:
                phases.append(current_phase)
            current_phase = {
                "label": phase_label,
                "start_year": snap["year"],
                "start_gen": snap["generation"],
                "end_year": snap["year"],
                "end_gen": snap["generation"],
                "mean_X": snap["mean_exposure_X"],
                "mean_K": snap["mean_knowl_K"],
            }
        else:
            current_phase["end_year"] = snap["year"]
            current_phase["end_gen"] = snap["generation"]

    if current_phase:
        phases.append(current_phase)
    return phases


def detect_strategy_shifts(snapshots, threshold=0.05):
    """Detect generations where the dominant strategy shifted significantly.

    Returns list of {generation, year, from_strategy, to_strategy}.
    """
    shifts = []
    if len(snapshots) < 2:
        return shifts

    prev_dominant = None
    for snap in snapshots:
        if not snap.get("alive", True) or "strategy_dist" not in snap:
            continue
        dist = snap["strategy_dist"]
        if not dist:
            continue
        cur_dominant = max(dist, key=dist.get)
        if prev_dominant and cur_dominant != prev_dominant:
            shifts.append({
                "generation": snap["generation"],
                "year": snap["year"],
                "from_strategy": prev_dominant,
                "to_strategy": cur_dominant,
                "shift_size": dist.get(cur_dominant, 0) - dist.get(prev_dominant, 0),
            })
        prev_dominant = cur_dominant
    return shifts


def render_civilisation_chronicle(snapshots, world_name, world_cfg,
                                    encounter_log, ahistorical_events):
    """Render the civilisation history as human-readable text."""
    lines = []
    lines.append(f"# Civilisation Chronicle — {world_name}")
    lines.append(f"")
    lines.append(f"Initial religion strength: {world_cfg['religion_strength_initial']:.2f}")
    lines.append(f"Tech inflection year: {world_cfg['tech_inflection_year']}")
    lines.append(f"Tech acceleration: {world_cfg['tech_acceleration']:.2f}×")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    if not snapshots:
        lines.append("No civilisation data recorded.")
        return "\n".join(lines)

    # Lifecycle
    first = snapshots[0]
    last = snapshots[-1]
    extinct = not last.get("alive", True)

    lines.append(f"## Civilisation Lifecycle")
    lines.append(f"- Generations: {first['generation']} → {last['generation']}")
    lines.append(f"- Years: {first['year']} → {last['year']}")
    if extinct:
        lines.append(f"- **CIVILISATION COLLAPSED** at year {last['year']}")
    else:
        lines.append(f"- Civilisation survived to year {last['year']}")
        lines.append(f"- Final population alive: {last['active_count']:,} of {last['total_count']:,} "
                     f"({last['p_alive']*100:.1f}%)")
    lines.append("")

    # State trajectory summary
    if snapshots:
        living = [s for s in snapshots if s.get("alive", True)]
        if living:
            initial = living[0]
            final = living[-1]
            lines.append(f"## State Trajectory (R, E, G, O, K, X)")
            lines.append(f"| Dimension | Initial | Final | Change |")
            lines.append(f"|---|---:|---:|---:|")
            for dim, key, label in [
                ("R", "mean_assets_R", "Resources"),
                ("E", "mean_environ_E", "Environment"),
                ("G", "mean_govern_G", "Governance"),
                ("O", "mean_optional_O", "Optionality"),
                ("K", "mean_knowl_K", "Knowledge"),
                ("X", "mean_exposure_X", "Exposure"),
            ]:
                init_v = initial[key]
                fin_v = final[key]
                delta = fin_v - init_v
                lines.append(f"| **{dim}** ({label}) | {init_v:.3f} | {fin_v:.3f} | {delta:+.3f} |")
            lines.append("")
            lines.append(f"Religion strength trajectory: "
                         f"{initial['religion_strength']:.3f} → {final['religion_strength']:.3f}")
            lines.append(f"Tech factor trajectory: "
                         f"{initial['tech_factor']:.3f} → {final['tech_factor']:.3f}")
            lines.append("")

    # Phases
    phases = detect_phases(snapshots)
    if phases:
        lines.append(f"## Civilisational Phases")
        for p in phases:
            duration = p["end_year"] - p["start_year"] + 40
            lines.append(f"- **{p['label']}** (year {p['start_year']}–{p['end_year']}, "
                         f"~{duration} years)")
        lines.append("")

    # Strategy shifts
    shifts = detect_strategy_shifts(snapshots)
    if shifts:
        lines.append(f"## Memetic Dynamics — Dominant Strategy Shifts ({len(shifts)})")
        for sh in shifts[:8]:
            lines.append(f"- Year {sh['year']}: dominant strategy "
                         f"**{sh['from_strategy']}** → **{sh['to_strategy']}**")
        if len(shifts) > 8:
            lines.append(f"- ... and {len(shifts) - 8} more shifts")
        lines.append("")

    # Major events
    all_events = []
    for s in snapshots:
        if s.get("alive", True) and s.get("events_this_gen"):
            for ev in s["events_this_gen"]:
                all_events.append((s["year"], ev))
    if all_events:
        lines.append(f"## Major Events Witnessed ({len(all_events)})")
        # Show first 12
        for year, ev_label in all_events[:12]:
            lines.append(f"- Year {year}: {ev_label}")
        if len(all_events) > 12:
            lines.append(f"- ... and {len(all_events) - 12} more events")
        lines.append("")

    # Ahistorical events
    if ahistorical_events:
        lines.append(f"## Ahistorical Events ({len(ahistorical_events)})")
        for ev in ahistorical_events:
            lines.append(f"- Year {ev['year']}: **{ev['label']}** "
                         f"({ev['dim']}, magnitude {ev['magnitude']:.2f})")
        lines.append("")

    # Encounter
    if encounter_log:
        lines.append(f"## Unknown Civilisation Encounter")
        lines.append(f"- Total generations affected: {len(encounter_log)}")
        intensities_seen = {}
        for e in encounter_log:
            intensities_seen[e["intensity"]] = intensities_seen.get(e["intensity"], 0) + 1
        for intensity, count in intensities_seen.items():
            lines.append(f"  - {intensity}: {count} generations")
        lines.append("")

    return "\n".join(lines)


def snapshots_to_dataframe(snapshots):
    """Convert snapshots to a flat DataFrame-friendly list."""
    import pandas as pd
    rows = []
    for s in snapshots:
        if not s.get("alive", True):
            rows.append({"generation": s["generation"], "year": s["year"],
                         "alive": False})
            continue
        row = {
            "generation": s["generation"],
            "year": s["year"],
            "era": s.get("era", "?"),
            "alive": True,
            "active_count": s["active_count"],
            "p_alive": s["p_alive"],
            "R": s["mean_assets_R"],
            "E": s["mean_environ_E"],
            "G": s["mean_govern_G"],
            "O": s["mean_optional_O"],
            "K": s["mean_knowl_K"],
            "X": s["mean_exposure_X"],
            "religion_strength": s["religion_strength"],
            "tech_factor": s["tech_factor"],
            "n_events": s["n_events"],
            "encounter_active": s["encounter_active"],
        }
        for sname, prop in s.get("strategy_dist", {}).items():
            row[f"strat_{sname}"] = prop
        rows.append(row)
    return pd.DataFrame(rows)
