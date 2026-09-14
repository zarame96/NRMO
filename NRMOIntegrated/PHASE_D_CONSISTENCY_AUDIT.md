# Phase D Mechanical Consistency Audit

Parent issue: #6  
Branch: `fix/issue-6-phase-d-consistency-audit`  
Base: `18c437021b3fbb6b4774196c26ec90a8ce202088`  
Scope: monograph/specification consistency and publication provenance; no runtime behavior changes

## Method

Repository code search on the Phase D base was used to discover occurrences of the required audit vocabulary, followed by source inspection and branch-local repair where a hit could still be read as current controlling semantics.

Required vocabulary from the adoption plan:

`MISSION`, `CORE`, `NORMAL`, `SAFE`, `SHUTDOWN`, `HOLD`, `Norn`, `Type ZERO`, `TRAINING`, `HARE`, `A_allowed`, `Aallowed`, `final decision authority`, `final judgement`, `execution controller`.

Search hits were classified as:

- **C — Current / Canon-conformant**
- **H — Historical or preserved baseline with explicit non-controlling precedence**
- **I — Implementation identifier/evidence; conformance deferred to Phase E**
- **F — Conflict found and fixed in Phase D**

## Scan matrix

| Term / pattern | Classification after Phase D | Result |
|---|---|---|
| `MISSION` | C / H | Current MISSION remains Goal-Constrained Execution. Old defensive MISSION is explicitly historical and maps to SAFE and/or MISSION-DEFENSE by behavior. |
| historical `CORE` mode | H | Superseded as current mode taxonomy; maps to NORMAL where it means ordinary operation. `NRMO Core` as a component name is a separate, valid usage. |
| `NORMAL` | C | Canonical Operational Mode. |
| `SAFE` | C / H | Canonical Operational Mode; old defensive mode semantics are translated through the historical mapping. |
| peer-mode `SHUTDOWN` | H | Historical peer-mode use is non-controlling. True terminal/halt SHUTDOWN remains valid exceptional control. |
| `HOLD` | C / H | Canonical state/governance result. HST-N Hold is a data-reliability signal. HOLD subtypes are implementation-level state refinements, not peer Operational Modes. |
| `Norn` | C / H / I | Canonical Norn is the interpretive governance perspective. Historical task-manager Norn/Skuld is provenance-labelled. Current implementation-name usage remains a Phase E conformance/naming check. |
| `Type ZERO` | C / H / I | Current specification: action-space/mode gating controller with no independent actuator authority. Preserved older wording is covered by Canon precedence; runtime conformance remains Phase E. |
| `TRAINING` | C / H | TRAINING is a Context Override; A–F/E+ is Training Grade. Older “Training Mode” language is preserved baseline terminology. |
| `HARE` | C / H | HARE is a Context Override, not a peer Operational Mode. Older “Context Override Mode” wording is explicitly provenance-labelled. |
| `A_allowed` | C | Canonical permitted/admissible action-space notation/profile concept. |
| `Aallowed` | I | Implementation/module identifier spelling. It does not create separate authority; runtime filter behavior is checked in Phase E. |
| `final decision authority` | C / F | Canon requires Human/User final sovereign decision authority. Residual HST-N/SOP authority wording was fixed in Phase D. |
| `final judgement` | C / H / F | Human final judgement is valid. Historical `DECISION_SURVIVAL_ENGINE` “final judgement engine” wording was classified and corrected so it cannot acquire sovereignty. |
| `Final authority` | C / F | APCSO table was repaired to separate Human Sovereign final authority from NRMO admissibility/veto authority. |
| `execution controller` | C / H | Current Type ZERO wording is gating controller/no actuator authority. Preserved “execution controller” semantics are controlled by the Canon interpretation rule. |
| `NRMO decides` | F | Residual HST-N wording was replaced with explicit governance/admissibility/veto vs Human sovereign decision separation. |
| `HOLD = shutdown` | F | Residual High-Speed text was corrected: HOLD is a lifecycle/governance state and is not synonymous with SHUTDOWN. |

## Structural precedence repair

A mechanical scan cannot safely be solved by blind global replacement because Parts I–VI intentionally preserve older generations. Phase D therefore adds explicit source-visible/PDF-visible precedence at the Part boundary:

- Part I: mixed-provenance notice — current Canon + repaired Operational Specification control; preserved foundational/foundations-paper wording is non-controlling where conflicting.
- Parts II–VI: shared preserved-baseline notice — current Canon controls conflicting terminology, authority, mode/state typing, Norn, and Type ZERO semantics.

This converts remaining literal legacy hits inside preserved Parts from ambiguous to explicitly historical/non-normative without deleting research lineage.

## High-risk inline repairs

### `chapters/ch02f_state_labels.tex`

Fixed residual statements that could assign final decision authority to SOP/NRMO/Type ZERO. Current reading is now:

- HST-N = classification only;
- SOP = procedural/action-space structure;
- Type ZERO = action-space/mode gating;
- NRMO = final governance/admissibility/veto authority;
- Human/User = final sovereign adoption/execution decision.

### `chapters/ch16_parallel_ooda.tex`

Separated the former `Human / Governance` row into Human Sovereign selection semantics and explicit NRMO admissibility/veto authority.

### `chapters/ch19_limitations.tex`

- corrected `HOLD` so it is not described as shutdown;
- changed the flow label from generic “veto judgment” to veto/admissibility;
- classified the historical `DECISION_SURVIVAL_ENGINE` “final judgement engine” description as non-sovereign survival/irreversibility evaluation/gating.

## Publication/version provenance audit

Phase D found that the previous manifest did not list Part XV and still said Parts I–XIII carried forward unchanged, despite the current master containing Part XV and Issue #6 source repairs.

Current publication interpretation is now explicit:

- publication family/version = **NRMO Integrated System v7.2**;
- current integrated source revision = **v7.2 rev2**;
- `NRMO_Complete_v5_5.tex` = legacy build-root/source-lineage filename, not publication version;
- Part/source baseline versions, normative Canon status, and implementation/experiment versions are separate dimensions;
- Part XIV = v7.2 Loom v3.1/Sociable Shadow culmination;
- Part XV = v7.2 rev2 Universal Adapter Framework;
- Issue #6 repairs are a consistency/provenance overlay on preserved baselines, so “unchanged” may describe lineage but not literal current source bytes.

The PDF build now includes a publication/provenance note and a corrected per-Part manifest.

## Remaining implementation deltas — deferred to Phase E

These are not Phase D specification blockers, but must be checked against the frozen Canon before Issue #6 closes:

1. **Norn/Skuld implementation naming and semantics** — implementation/status documents still use `Norn-Skuld`; verify that no current implementation component assumes canonical Norn authority or task-manager semantics under the same conceptual name.
2. **Aallowed runtime authority** — verify it filters/categories action space and cannot override NRMO veto or Human sovereignty.
3. **Type ZERO runtime authority** — verify gating-only behavior and absence of independent actuator authority.
4. **ModeSelector taxonomy** — verify current implementation maps to canonical `NORMAL / VENTURE / MISSION / SAFE`, with TRAINING/HARE as overrides and HOLD as state, not mode.
5. **MISSION semantics** — verify runtime MISSION is goal-constrained execution, not the old defensive-only profile.
6. **SHUTDOWN/HOLD separation** — verify terminal halt vs lifecycle hold is preserved in code paths.
7. **StrongEngine boundary** — verify candidate generation/search/selection cannot enlarge or bypass the NRMO-admitted set.
8. **DecisionCompass conformance** — separately compare application implementation to the frozen NRMO Canon after NRMO-side implementation audit.

## Phase D conclusion

After the Phase D branch repairs, no known monograph/specification occurrence in the required scan vocabulary remains both (a) conflicting with the Canon and (b) unclassified as current, historical/non-normative, or implementation evidence.

Phase D therefore freezes the specification text for transition to Phase E implementation conformance, subject to PR diff review and merge.
