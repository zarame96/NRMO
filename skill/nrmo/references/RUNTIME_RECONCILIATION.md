# NRMO v7.3 Runtime Reconciliation

**Status:** Runtime reconciliation for the personal Skill. This document adds no theory and does not amend the preserved sources.

## 1. Authority and reading order

Use the following order when sources differ:

1. Explicit Human Sovereign adoption decisions, within the authority structure defined by the Canon
2. `NORMATIVE_CANON.md`
3. Adopted or clarified statements in `NRMO_Integrated_System_v7_3.pdf`, especially Part XVI
4. The applicable authoritative chapter or foundation source
5. `nrmo_system_v7_3.md`, as the preserved LLM/GEM-targeted operational specification
6. Patches, implementation observations, evidence reports, and research drafts within their stated scope

`nrmo_system_v7_3.md` is not a complete reproduction of the Publication of Record. The bundled `SOURCE_MANIFEST.md` classifies it as an operational specification subordinate to the v7.2 Integrated System and records no amendment of the Normative Canon. Use it for the standard response shape and operational summary, but do not let it override items 1-4.

## 2. Mandatory PDF routing

The PDF has 537 file pages. Printed page numbers differ from file-page numbers. Read the named section, not only a remembered page number.

| Question or output element | Required PDF section | Location |
|---|---|---|
| Authority, mode, lifecycle | Chapter 60 | printed pp.423-425; file pages 463-465 |
| Entering or leaving HOLD | §60.3 HOLD State Machine | printed p.425; file page 465 |
| Hard/Soft and Active/Passive | §63.1 Ruin Taxonomy | printed p.431; file page 471 |
| Passive Ruin | §63.2 Avoidability-Window Definition | printed p.432; file page 472 |
| `A_allowed` classification | §64.1 Admissibility Refinement | printed p.433; file page 473 |
| StrongEngine candidate surface | §64.2 StrongEngine Candidate Surface | printed pp.433-434; file pages 473-474 |
| `Pr(τ_F ≤ T | s,a) ≤ ε` | Chapter 3 and Chapter 20 | read both contexts before using the expression |

For an ordinary decision consultation, read this file, `NORMATIVE_CANON.md`, and `nrmo_system_v7_3.md`. Before producing an output that uses any row above, also read the corresponding PDF section. If the PDF cannot be read, say which required source was unavailable and do not replace its rule with an inference from the operational Markdown.

## 3. HOLD reconciliation

Keep three claims separate:

1. **Observed current lifecycle state:** state only what the input or a trusted state record establishes. Otherwise write `current recorded state: unknown`.
2. **Governance result for this assessment:** NRMO may return `HOLD` when human intervention is required, including an empty `A_allowed` or materially insufficient information for a major or irreversible candidate. No human action is needed to enter HOLD.
3. **Resumption:** `HOLD → ACTIVE` requires explicit Human Sovereign approval.

Everyday language such as “保留している” does not by itself prove a previously recorded lifecycle transition. This evidence rule does not prevent NRMO from returning a new HOLD governance signal when the formal trigger is satisfied. Write `governance result: HOLD` separately from the observed historical state.

## 4. Ruin reconciliation

Record two independent axes:

- `ruin_severity ∈ {Hard, Soft}` is the severity axis for the Investment domain. Use `N/A` outside that domain unless a later adopted source explicitly extends it.
- `ruin_origin ∈ {Active, Passive}` is a domain-general causal-origin axis.

Do not flatten them into a four-member enum. Outside the Investment domain, describe an irreversible-loss boundary or recoverable degradation without assigning the formal Hard/Soft severity label.

### Passive Ruin

Do not infer Passive Ruin from inactivity, elapsed time, caution, or delay alone. The primary test is an observed avoidability-window closure:

1. an avoidability window was open immediately before the choice;
2. the candidate action closes that window;
3. the comparison against the do-nothing or relevant alternative baseline supports the closure; and
4. optionality is thereby eroded through avoidance, rigidity, or adaptation failure.

An inactivity streak is a secondary, lagging diagnostic. If the closure is not established, report `Passive Ruin: not established` and describe any observed delay or risk separately.

## 5. Operational Markdown preservation

Keep `nrmo_system_v7_3.md` byte-for-byte unchanged as a preserved original. Resolve conflicts in this file and in `SKILL.md`; do not silently rewrite the original. Cite the operational section and the controlling Canon/PDF section when a reconciliation changes the literal reading of the operational Markdown.
