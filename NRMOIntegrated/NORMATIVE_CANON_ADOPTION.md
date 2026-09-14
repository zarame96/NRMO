# NRMO Normative Canon — Adoption Record

**Status:** Adopted for specification repair  
**Parent issue:** #6 — Establish Normative Canon and resolve cross-generation specification conflicts  
**Canon:** `NORMATIVE_CANON.md`

## Decision

The Normative Canon is adopted as the active consistency ruling for repair of the NRMO Integrated v7.2 monograph.

This adoption does **not** declare the current PDF internally consistent. It establishes the authority needed to repair it deterministically.

The repository Founding Charter remains controlling at repository level:

`Human Sovereign → Vision → NRMO → Engines → Implementations`

The Canon operationalizes that hierarchy by distinguishing:

- Human Sovereign — final sovereign decision authority;
- NRMO — final governance/admissibility/veto authority;
- StrongEngine Ω Full — search/selection inside the admissible set;
- implementations — subordinate realizations of the specification.

## Frozen rulings

The following rulings are frozen for the repair pass unless explicit contradictory evidence requires reopening #6:

1. Operational Modes: `NORMAL / VENTURE / MISSION / SAFE`.
2. `MISSION = Goal-Constrained Execution`.
3. `TRAINING` and `HARE` are Context Overrides; `A–F / E+` is Training Grade.
4. `HOLD` is a lifecycle/governance state/result, not an Operational Mode.
5. `SHUTDOWN` is exceptional/terminal defensive control, not an ordinary peer Operational Mode.
6. `MISSION-DEFENSE` is an action-space/A_allowed defensive extension or override, not a mode.
7. `/#vision` is context/orientation, not an Operational Mode or execution authority.
8. Type ZERO is an action-space/mode **gating** controller, not an actuator authority.
9. Canonical Norn is an interpretive governance perspective; historical task-manager Norn is a naming-overloaded implementation artifact.
10. Strict governance/execution separation remains normative: `A_t = NRMO(X_t)`, `a_t = Ω(A_t)`, `a_t ∈ A_t`.

## Repair sequence

### Phase A — Normative text
Patch the integrated monograph so its current normative layer explicitly matches the Canon:

- authority wording;
- operational mode taxonomy;
- MISSION definition;
- context override vs training-grade typing;
- Type ZERO role wording.

### Phase B — Preserved historical specifications
Do not erase historical material. Add explicit provenance/supersession notes where old material conflicts with the Canon, especially:

- `CORE / VENTURE / MISSION / SHUTDOWN` mode tables;
- defensive MISSION definitions;
- SOP permission tables tied to defensive MISSION;
- “Hold Mode” headings that are actually state/signal semantics.

### Phase C — Implementation provenance
Label concrete module/file descriptions by implementation status. In particular, historical Norn/Skuld task-manager code and stale module trees must not be mistaken for current normative architecture.

### Phase D — Mechanical consistency audit
After edits, scan the complete monograph for at least:

`MISSION`, `CORE`, `NORMAL`, `SAFE`, `SHUTDOWN`, `HOLD`, `Norn`, `Type ZERO`, `TRAINING`, `HARE`, `A_allowed`, `Aallowed`, `final decision authority`, `final judgement`, `execution controller`.

Every remaining occurrence must be either canon-conformant or explicitly historical/non-normative.

### Phase E — Implementation conformance
Only after the specification repair is frozen, compare DecisionCompass/current reference implementation against the repaired specification and create separate implementation issues for genuine behavioral deltas.

## Guardrails

- No blind global rename of `CORE`, `SHUTDOWN`, or `MISSION`.
- No deletion of negative results or historical research merely because terminology is superseded.
- No implementation change justified solely by stale historical prose.
- No change to the Canon merely to make current code appear conformant.
- Any true theory change discovered during repair must be separately reviewed rather than hidden inside editorial cleanup.

## Exit criteria for #6

Issue #6 can be closed only when:

1. Canon is present and linked from the integrated package entry point.
2. The monograph's current normative sections conform to it.
3. Conflicting preserved sections carry explicit historical/superseded provenance.
4. HOLD, MISSION, SAFE/SHUTDOWN, Norn, Type ZERO, and authority terminology pass full-text consistency review.
5. Publication/baseline/implementation version provenance is unambiguous.
6. A post-repair audit records remaining implementation deltas separately.
