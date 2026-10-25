# NRMO v7.3 Runtime Reconciliation

**Status:** Runtime reconciliation for the all-employee Work Skill. This document adds no theory and does not amend the preserved sources. Employee-specific authority, privacy, consultation, and reporting controls are defined in WORKPLACE_BOUNDARIES.md and may narrow action, but may not override this reconciliation or the Canon.

## 1. Authority and reading order

Use the following order when sources differ:

1. Explicit Human Sovereign adoption decisions, within the authority structure defined by the Canon
2. `NORMATIVE_CANON.md`
3. Adopted or clarified statements in `NRMO_Integrated_System_v7_3.pdf`, especially Part XVI
4. The applicable authoritative chapter or foundation source
5. `nrmo_system_v7_3.md`, as the preserved LLM/GEM-targeted operational specification
6. Patches, implementation observations, evidence reports, and research drafts within their stated scope

For workplace use, Human Sovereignty is not transferred to an employer, manager, model, or work rule. An employee acts within verified role authority and retains personal rights. An employee may prepare, ask, document, pause unsafe work within applicable authority, consult, or report through available routes; the Skill does not create approval power, waive consent, or determine another person's employment outcome. Unknown authority remains unknown.

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
| `Pr(τ_F ≤ T | s,a) ≤ ε` | Chapter 3, and Chapter 22 "Caged Beast Model" | Chapter 3: file pages 59-82 (expressions mainly 61-71). Chapter 22: file pages 211-216; the bundled text source is `foundations/ch20_caged_beast.tex`. Read both contexts before using the expression. PDF Chapter 20 is "NRMO Life SOP" and does not contain the expression; do not call this context "PDF Chapter 20" |

For an ordinary decision consultation, read this file, `NORMATIVE_CANON.md`, and `nrmo_system_v7_3.md`. Before producing an output that uses any row above, also read the corresponding PDF section. If the PDF cannot be read, say which required source was unavailable and do not replace its rule with an inference from the operational Markdown.

**Standard decision response.** The standard output format (`nrmo_system_v7_3.md` §6) always contains the mode and state, the ruin boundary, `A_allowed`, and StrongEngine candidates. Therefore, before composing any standard decision response, read PDF file pages 463-474 in a single Read call with one continuous range (`pages: "463-474"`). Do not pass comma-separated page lists. This one range covers §60.3, §63.1, §63.2, §64.1, and §64.2. Add the Chapter 3 and Chapter 22 contexts when the ruin-probability row applies.

**Closing-only response.** When the user only asks to end or pause the conversation and does not ask for an assessment, do not produce a standard decision response. Do not output a lifecycle state, governance result, Ruin label, mode, or review date, and do not write anything that reads as a state history or a new record. No PDF reading is required on this path because no determination is made.

**Evidence of reading.** Do not state that a source was read, checked, or used as a basis unless it was actually opened in this response.

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
