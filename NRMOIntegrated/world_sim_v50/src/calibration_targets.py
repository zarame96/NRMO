"""
Calibration targets from historical demography literature.

Per-civilization expected continuation rate (2000 BCE → 2021 CE).
These are coarse Y-DNA / ethnographic estimates from population genetics
studies. Used as soft anchors for v6.1.1 calibration.

References (illustrative, not exhaustive):
- Cook 1998, "Born to Die" — Mesoamerica 90% population loss 1492-1620
- McEvedy & Jones 1978, "Atlas of World Population History"
- Diamond 1997, "Guns, Germs, and Steel"
- Cavalli-Sforza 2000, "Genes, Peoples, and Languages"
- Reich 2018, "Who We Are and How We Got Here"
"""

CALIBRATION_TARGETS = {
    # Civilization: (lower, target_central, upper) for 2000-year continuation
    # rate of family lines (proxy: % of descendants whose direct paternal line
    # of named ancestor 2000 yr ago survives in Y-DNA today, multiplied by
    # an ad-hoc factor for "named lineage" coherence).
    "Japan": (0.78, 0.85, 0.92),
    # Tokugawa-era genealogies show ~80-90% continuation; simulation 86.9% ✅

    "China": (0.78, 0.84, 0.90),
    # Major lineages (e.g. Confucius) traceable; warlord eras caused breaks;
    # simulation 84.0% ✅

    "Europe": (0.40, 0.55, 0.70),
    # Migration period + Black Death + religious wars + WWI/WWII =
    # high attrition. Simulation 29% may be too low.

    "Islamic": (0.70, 0.80, 0.88),
    # Mongol invasion + colonial fragmentation; simulation 83.9% ✅

    "Indic": (0.75, 0.83, 0.90),
    # Caste system + joint family preserves lineage; simulation 87.8% ✅

    "SubSaharan": (0.55, 0.70, 0.82),
    # Slave trade + colonial disruption + civil wars;
    # simulation 85.5% likely too high.

    "Polynesian": (0.40, 0.55, 0.72),
    # Contact-era catastrophe (Cook to ~1900): 70-90% population loss
    # in Marquesas / Hawaii; simulation 84.1% likely too high.

    "Steppe": (0.50, 0.65, 0.78),
    # Mongol/Russian/Qing expansions + 20C sedentarization;
    # simulation 77.4% upper edge.

    "IndigenousAmericas": (0.05, 0.12, 0.25),
    # Contact catastrophe 90% loss + colonial era + reservations;
    # simulation 79.5% MASSIVELY off (need calibration).
}


def calibration_status(simulated_p, target):
    """Return 'in_range' / 'low' / 'high' classification."""
    lower, central, upper = target
    if simulated_p < lower:
        return "low", abs(simulated_p - central)
    if simulated_p > upper:
        return "high", abs(simulated_p - central)
    return "in_range", abs(simulated_p - central)


def render_calibration_report(per_civ_p_continued):
    """Compare simulated vs target continuation rates."""
    lines = []
    lines.append("# Calibration Report — Civilization Continuation Rates")
    lines.append("")
    lines.append("Comparison of simulated 2000-year continuation rates to")
    lines.append("target ranges from historical demography literature.")
    lines.append("")
    lines.append("| Civilization | Target Range | Simulated | Status |")
    lines.append("|---|---:|---:|:---:|")

    issues = []
    for civ, (lower, central, upper) in CALIBRATION_TARGETS.items():
        sim = per_civ_p_continued.get(civ)
        if sim is None:
            continue
        status, dev = calibration_status(sim, (lower, central, upper))
        if status == "in_range":
            badge = "✅"
        elif status == "low":
            badge = "⬇️"
            issues.append(f"{civ}: simulated {sim:.2f} below target {central:.2f}")
        else:
            badge = "⬆️"
            issues.append(f"{civ}: simulated {sim:.2f} above target {central:.2f}")
        lines.append(f"| {civ} | {lower:.2f}-{upper:.2f} ({central:.2f}) | "
                     f"{sim:.2f} | {badge} |")

    lines.append("")
    if issues:
        lines.append("## Calibration Issues")
        lines.append("")
        for iss in issues:
            lines.append(f"- {iss}")
        lines.append("")
    else:
        lines.append("All civilizations within target ranges. ✅")
        lines.append("")

    return "\n".join(lines)
