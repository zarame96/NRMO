#!/usr/bin/env python3
"""check_v73_consistency.py — negative-state guards for Part XVI
(NRMO v7.3 Production Contract Integration).

Scans NRMOIntegrated/parts/part16_v73_production_contract.tex for
textual patterns that would indicate one of the known governance
violations this Part must never assert. This is a text-level guard
(this Part is prose/LaTeX, not executable code), analogous in spirit
to tools/terminology_audit.py.

Exit 0 = all guards pass. Exit 1 = a guard fired (potential
normative-consistency regression).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "parts" / "part16_v73_production_contract.tex"


def fail(msg):
    print(f"  FAIL: {msg}")


def main():
    if not TARGET.exists():
        print(f"[V7.3 CONSISTENCY GUARD] SKIP: {TARGET} not present")
        return 0

    text = TARGET.read_text(encoding="utf-8")
    # Strip LaTeX comments for pattern matching (keep line structure).
    stripped_lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("%"):
            stripped_lines.append("")
        else:
            stripped_lines.append(line)
    body = "\n".join(stripped_lines)

    failures = []

    # 1. HOLD or MISSION-DEFENSE must never be asserted as an
    #    Operational Mode (Canon §3.4, §3.6).
    if re.search(r"HOLD\s+is\s+an?\s+Operational Mode", body, re.I):
        failures.append("HOLD asserted as an Operational Mode")
    if re.search(r"MISSION-DEFENSE\s+is\s+an?\s+Operational Mode", body, re.I):
        failures.append("MISSION-DEFENSE asserted as an Operational Mode")

    # 2. StrongEngine must never be described as changing/redefining
    #    the ruin boundary or admissible set on its own authority.
    if re.search(
        r"StrongEngine[^.]{0,80}(redefine|change|expand)s?\s+the\s+ruin",
        body, re.I,
    ):
        failures.append("StrongEngine described as changing the ruin boundary")

    # 3. Norn must never be described as holding veto/execute/threshold
    #    authority in an affirmative (non-prohibition) sentence. We
    #    check for the prohibition phrasing existing at least once,
    #    and flag any affirmative "Norn may veto" / "Norn executes"
    #    style construction.
    if not re.search(r"Norn\s+\\textbf\{must not\}", body):
        failures.append(
            "expected explicit 'Norn must not' prohibition sentence not found"
        )
    if re.search(r"Norn\s+(may|can|is permitted to)\s+veto", body, re.I):
        failures.append("Norn described as permitted to veto")
    if re.search(r"Norn\s+executes?\b", body, re.I):
        failures.append("Norn described as executing")

    # 4. SHUTDOWN must never be silently equated with SAFE.
    if re.search(r"SHUTDOWN\s+is\s+(the\s+same\s+as|equivalent\s+to)\s+SAFE\b", body, re.I):
        failures.append("SHUTDOWN silently equated with SAFE")

    # 5. TRAINING must never be described as feeding real-world/
    #    authoritative execution state.
    if re.search(r"TRAINING[^.]{0,80}(execute|mutate)[^.]{0,40}real", body, re.I):
        failures.append("TRAINING described as mutating/executing real-world state")

    # 6. HARE must never be described as disabling ruin avoidance.
    if re.search(r"HARE[^.]{0,80}ruin avoidance[^.]{0,40}(disab|suspend|remov)", body, re.I):
        failures.append("HARE described as disabling ruin avoidance")

    # 7. Passive Ruin must not be reduced to mere inactivity as a
    #    positive definition (the Part must state the prohibition,
    #    not violate it).
    if not re.search(r"Passive Ruin must not be redefined as mere inactivity", body):
        failures.append(
            "expected explicit Passive-Ruin-is-not-mere-inactivity statement not found"
        )

    # 8. a_t in A_t invariant must be present and never negated.
    if "a_t \\in A_t" not in body:
        failures.append("expected admissibility invariant a_t in A_t not found")
    if re.search(r"a_t\s*\\notin\s*A_t", body):
        failures.append("admissibility invariant explicitly negated (a_t not in A_t)")

    # 9. No content in this Part should claim to amend/modify
    #    NORMATIVE_CANON.md. Skip sentences that explicitly negate
    #    this ("No ... amends ...", "does not amend ...") — those are
    #    the required disclaimer, not a violation.
    for m in re.finditer(
        r"(amends?|modifies?|changes?)\s+\\texttt\{NORMATIVE\\_CANON\.md\}",
        body, re.I,
    ):
        window_start = max(0, m.start() - 60)
        preceding = body[window_start:m.start()]
        if re.search(r"\b(no|not|never|does not|doesn't)\b", preceding, re.I):
            continue  # negated — this is the required disclaimer
        failures.append(
            f"Part XVI text appears to claim it amends NORMATIVE_CANON.md "
            f"(near: ...{body[max(0, m.start()-40):m.end()+10]!r}...)"
        )

    # 10. No v7.4 content should be present in this v7.3 Part.
    if re.search(r"\bv7\.4\b", body):
        failures.append("v7.4 reference found in v7.3 Part (scope violation)")

    print("[V7.3 CONSISTENCY GUARD]")
    if failures:
        for f in failures:
            fail(f)
        print(f"FOUND {len(failures)} guard violation(s)")
        return 1
    print("OK: no known governance-violation patterns found in Part XVI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
