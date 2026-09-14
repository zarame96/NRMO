# NRMO Historical Provenance Register

Status: Supporting provenance record for Normative Canon repair  
Parent issue: #6  
Authority: Subordinate to `NORMATIVE_CANON.md`

## Purpose

NRMO preserves historical specification text rather than silently rewriting or deleting it. This register identifies known cross-generation terminology that remains in the monograph/source tree and states how it must be interpreted under the current Normative Canon.

A historical occurrence is not controlling merely because the literal term remains searchable in the repository.

## Canonical interpretation rules

- Current Operational Modes: `NORMAL / VENTURE / MISSION / SAFE`.
- Historical `CORE` -> canonical `NORMAL` where it means ordinary/standard operation.
- Historical goal-constrained `MISSION` -> canonical `MISSION`.
- Historical defensive `MISSION` -> canonical `SAFE` and/or `MISSION-DEFENSE`, according to actual behavior.
- Historical peer-mode `SHUTDOWN` -> `SAFE` only where the behavior is defensive narrowing; true terminal/halt semantics remain `SHUTDOWN`.
- `MISSION-DEFENSE` is an action-space / `A_allowed` defensive extension or override, not a peer Operational Mode.
- `HOLD` is a governance/lifecycle state/result or data-reliability signal, not a peer Operational Mode.
- `HARE` and `TRAINING` are Context Overrides; `A-F / E+` is Training Grade.

## Source classification

### Inline-supersession applied in Phase B

1. `chapters/ch02c_type_zero_modes.tex`
   - Preserves the historical `CORE / VENTURE / MISSION / SHUTDOWN` table.
   - Explicitly marked superseded for current Operational Mode semantics.

2. `chapters/ch02d_action_space.tex`
   - Preserves the historical mode-selection step.
   - Explicit canonical translation is required before operational use.

3. `chapters/ch06_sop_os.tex`
   - Preserves historical mode and permission tables.
   - Historical `MISSION = only A` is explicitly non-controlling and classified as the old defensive MISSION profile.

4. `chapters/ch10_hare_no_hi.tex`
   - Historical `Context Override Mode` wording is superseded.
   - HARE is typed as a Context Override, not an additional Operational Mode.

5. `chapters/ch02e_logic_gates.tex`
   - Historical `Hold Mode` heading is retained only as provenance.
   - HST-N Hold is typed as a data-reliability state/signal.

6. `chapters/ch04_hst_n.tex`
   - Same Hold correction applied to the standalone HST-N reference.

### Preserved historical / non-controlling source material

The following files may continue to contain literal old-generation terminology. Their presence is intentional and does not override the Canon.

- `chapters/ch01c_foundations_paper.tex`
  - Peer-review/foundations draft reconstructed from earlier monograph generations.
  - Old `Core / Venture / Mission / Shutdown` formalizations are historical model descriptions unless separately re-adopted by the Canon.

- `chapters/ch02b_defensive_offense_carryback.tex`
  - Preserved carryback/training architecture text.
  - Old mode labels are historical integration vocabulary.

- `chapters/ch02g_mission_defense.tex`
  - Preserves the evolution of the MISSION-DEFENSE extension.
  - Interpret `MISSION-DEFENSE` canonically as an `A_allowed` action-space extension/override, never as a fifth Operational Mode.
  - Where the file contains a later `NORMAL / VENTURE / MISSION / SAFE` profile, that profile is the current-generation taxonomy.

- `chapters/ch05_a_allowed.tex`
  - `MISSION-DEFENSE` references describe a defensive action-space extension.
  - They do not alter the canonical definition of MISSION as goal-constrained execution.

- Any archive, validation snapshot, generated output, or versioned codebase under `archive/`, `v52_codebase/`, or equivalent historical directories.
  - Treat as implementation/version evidence, not current normative authority.

## Search rule

Mechanical scans for `CORE`, `MISSION`, `SHUTDOWN`, `Hold Mode`, `Context Override Mode`, or similar legacy terms must classify each hit before treating it as a defect:

1. current normative text;
2. explicitly superseded historical text;
3. historical implementation snapshot;
4. archive/generated artifact;
5. current Canon-conformant usage.

A search hit in categories 2-4 is not by itself a specification conflict.

## No-blind-rewrite rule

Do not globally replace legacy terminology. Preserve historical lineage and add provenance/supersession notes where ambiguity affects current interpretation.
