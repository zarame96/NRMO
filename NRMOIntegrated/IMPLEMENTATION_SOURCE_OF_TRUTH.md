# NRMO Runtime Implementation Source of Truth

Status: **Controlling implementation-provenance record**  
Parent: Issue #11 / Issue #6 Phase E  
Specification repository: `zarame96/NRMO`

## Repository responsibility split

NRMO and its executable implementation intentionally have different source-of-truth repositories.

- **`zarame96/NRMO`** — normative specification, monograph, research/provenance records, historical/reference implementation material.
- **`zarame96/DecisionCompass`** — current executable NRMO/StrongEngine integration and product runtime.

This split is consistent with the repository `.gitignore`, which excludes `NRMOIntegrated/code/` and states that the executable engine implementation is managed in DecisionCompass.

A path mentioned in an older NRMO package document does not prove that the corresponding runtime file is bundled in the NRMO repository.

## Phase E audited implementation snapshot

The implementation-conformance audit opened under Issue #6 is pinned to:

- repository: `zarame96/DecisionCompass`
- commit: `ae00f9fd23760a6b4dd078723a1eed74ef7bffc9`
- implementation root: `NRMOIntegrated/code/python/nrmo_v72_phase1/`
- audit date: 2026-09-14

This SHA is a **conformance snapshot**, not a floating alias. Future DecisionCompass changes do not silently update the evidence for this audit. A later conformance pass must record a new exact commit.

## Current conformance findings at the pinned snapshot

PASS / structurally conformant:

- Aallowed narrows candidate space and does not override NRMO veto.
- The production pipeline orders candidate generation -> Aallowed -> NRMO hard filter -> StrongEngine selection.
- StrongEngine receives the admitted set for final ranking/selection and asserts selected-action membership.
- Passive Ruin v7.2.1 narrows the admitted set; it does not enlarge it.
- HOLD and terminal Shutdown control are distinct in the audited pipeline.
- MISSION selection is goal/mission driven rather than the historical defensive-only MISSION profile.

Open implementation deltas are tracked separately in DecisionCompass:

- #113 — separate TRAINING/HARE Context Overrides from Operational Mode typing.
- #114 — implement the Canon-defined Type ZERO action-space/mode gating contract.
- #115 — remove the overloaded Norn/Skuld task-manager naming collision.

## Validation rule

The NRMO repository must not claim a self-contained FULL runtime validation when the runtime tree is intentionally not present.

Runtime validation is valid only when:

1. the DecisionCompass repository is checked out explicitly;
2. the exact intended commit is known;
3. the validator is pointed at that checkout;
4. the checked-out SHA is recorded in the resulting evidence.

The NRMO-side `validate_nrmo_integrated_v72.py` is therefore a provenance-aware delegator/checker. With no runtime checkout supplied, it may validate repository provenance but must not report runtime FULL PASS.

## Evidence priority

For implementation behavior/existence claims:

1. checked-in DecisionCompass files at the stated commit;
2. validation/test output generated from that same commit;
3. ref-bound implementation documentation;
4. historical/reference code snapshots preserved in NRMO;
5. generated/copied listings.

For normative architecture and terminology, `NORMATIVE_CANON.md` remains controlling.

## No-duplication rule

Do not copy the current DecisionCompass runtime back into NRMO merely to make an old package manifest appear self-contained. Two writable runtime copies would create silent drift and destroy the source-of-truth boundary this record establishes.
