# NRMO v7.3 — DecisionCompass Conformance Re-Evaluation (post-discovery)

**Status:** NRMO-side conformance note. Read-only against DecisionCompass;
**no file in `zarame96/DecisionCompass` was modified from this branch.**
**Authority direction:** `NRMO source → DecisionCompass implementation →
evidence` — never the reverse. This note does not redefine, infer, or
backfill any NRMO requirement from what DecisionCompass happens to
implement.
**Basis:** `NRMOIntegrated/docs/V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md`
(item classifications) and `NRMOIntegrated/docs/V7_3_DIFFERENTIAL_TABLE.md`
rows 3.2, 4.2, 4.4, 5.1, 10.1a, 10.1b, 11.1a, 11.1b.
**DecisionCompass state checked:** branch
`agent/nrmo-v7-3-canonical-parity`, HEAD
`7ee15a964bce51aba22a997e9bba31a389514ac2` (`docs/nrmo_v7_3_conformance.json`
unchanged since the LOOP F spot-check in the earlier external audit).

## Per-item re-evaluation

| NRMO item | Row | Status | Evidence checked | Notes |
|---|---|---|---|---|
| Empty `A_allowed` ⇒ HOLD | 3.2 | **VERIFIED** | `test_empty_aallowed_returns_hold_without_execution_candidate` (`tests/unit/test_nrmo_v73_procedure_contract.py`, branch HEAD) | Direct, named test for exactly this rule. |
| Norn observable responsibilities | 4.2 | **VERIFIED** | `norn-read-only-audit` (`UNIT_VERIFIED`); spot-checked `tests/unit/test_audit.py` — `test_norn_observe_does_not_mutate_result`, `test_v73_norn_records_branch_upstream_and_passive_facts_only` contain real, non-placeholder assertions. | — |
| Norn drift-classification vocabulary | 4.4 | **VERIFIED** | `test_v73_drift_class_names_are_canonical` (`tests/unit/test_audit.py`) | Confirmed real test, not placeholder (prior spot-check). |
| §14 ten-step procedure | 5.1 | **VERIFIED** | `test_procedure_events_are_runtime_events_in_canonical_order` (`tests/unit/test_nrmo_v73_procedure_contract.py`) — asserts the runtime's `STAGES` list matches the exact 10-stage order (`vision_mission_consistency, ruin_boundary, reversibility, a_allowed, information_sufficiency, execution_candidates, observation, exit_conditions, reevaluation, human_sovereign`) with sequence numbers 1–10. | Independently corroborates the original's §14 order at the implementation level too. |
| 5a — StrongEngine candidates, presentation-layer A/B/C default | 10.1a | **NOT_VERIFIED** (evidence-based, not `NOT_APPLICABLE`) | (1) Searched for `safe`/`standard`/`aggressive` 3-alternative naming, `A`/`B`/`C` alternative structures repo-wide — no matches. (2) Checked whether DecisionCompass even **has** a presentation/UI layer capable of surfacing this, rather than assuming: confirmed it does — `decisioncompass_web/`, `decisioncompass_web_static/`, `decisioncompass/app/`, `android-twa/` are real UI/app surfaces. (3) `decisioncompass_web/src/App.tsx` (lines 530, 792, 1813-1814, 2528) does render a `candidates` list (`nlProp.candidates`, `r.candidates`) as UI tags — a generic, variable-length candidate display, not the specific fixed 3-item safe/standard/aggressive default the original requires. | **Genuinely `NOT_VERIFIED`, not `NOT_APPLICABLE`**: a presentation layer capable of implementing this exists and already renders *some* form of candidate list; whether it specifically implements the 3-named-alternative default is simply unconfirmed, not precluded by architecture. Declaring `NOT_APPLICABLE` would have been an unevidenced assumption; this finding replaces an earlier draft of this note that left the two possibilities open without checking. No requirement ID in `nrmo_v7_3_conformance.json` corresponds to this item at all. |
| 5b — internal candidate-diversity principle | 10.1b | **excluded — not a conformance requirement** | — | Per instruction: unadopted content is never made a conformance requirement. See `V7_3_ITEM5_DECISIONCOMPASS_REQUIREMENT_PROPOSAL.md` for the earlier (still-unadopted) proposed requirement sketch, itself now understood to describe 10.1b specifically, not 10.1a. |
| 6a — original-confirmed response-content fields | 11.1a | **VERIFIED** | `mode-state-separation`, `ruin-separation`, `decision-record` (all `UNIT_VERIFIED`); `test_decision_trace_and_persisted_record_carry_v73_contract` and `test_procedure_events_are_runtime_events_in_canonical_order` both exercise these fields directly. | — |
| 6b — post-hoc trace extension (version provenance, vetoed-with-reasons, score metadata, persisted accept/modify/reject) | 11.1b | **PARTIAL** | `decision-record` (`UNIT_VERIFIED`) covers persistence generally; direct search for `score`, `vetoed...reason`, and a persisted tri-state accept/modify/reject field in `test_nrmo_v73_procedure_contract.py` found only a boolean `human_sovereign` / `final_decision_authority == "human"` flag — narrower than "recorded acceptance, modification, or rejection." `vetoed_actions` as a bare list is present elsewhere (`test_audit.py`), but not confirmed *with reasons* as a persisted field, nor was StrongEngine score metadata confirmed. | Genuine partial gap, not a placeholder-test artifact — the existing tests are real but narrower in scope than the full 11.1b field list. |

## Summary

6 of 8 evaluated sub-items: **VERIFIED**. 1: **PARTIAL** (11.1b — some
but not all extension fields evidenced). 1: **NOT_VERIFIED** (10.1a —
no requirement tracked at all). 10.1b is correctly excluded as
unadopted content, per instruction, not scored.

This is consistent with, and updates, the earlier informational
cross-reference in Part XVI §`sec:v73-decisioncompass-conformance-summary`
(which reports DecisionCompass's own self-reported conformance-matrix
state generally) by breaking it out per NRMO item rather than relying
on the implementation's aggregate self-report. Per
`NORMATIVE_CANON.md` §11, none of this constitutes NRMO theory being
derived from or validated against the implementation — it is solely a
record of the implementation's current evidentiary state relative to
already-established (now `ORIGINAL-CONFIRMED` or
`HUMAN-SOVEREIGN-ADOPTED`) NRMO requirements.

## Gaps recorded (NRMO-side note only — no DecisionCompass action taken)

1. **10.1a (presentation-layer A/B/C default)**: no DecisionCompass
   conformance requirement ID exists. If DecisionCompass's product
   surface is meant to replicate this response convention, a
   requirement (e.g. `strongengine-presentation-default`) and
   corresponding test would need to be added on the DecisionCompass
   side — not done here.
2. **11.1b (trace extension)**: `score metadata`, `vetoed-with-reasons`,
   and persisted `accept/modify/reject` are not confirmed as distinct
   tested fields, only a coarser `human_sovereign` boolean. If full
   11.1b conformance is desired, DecisionCompass's own maintainers
   would need to extend `test_nrmo_v73_procedure_contract.py` or
   equivalent — not done here, and this note does not direct them to.

---

*Prepared read-only, this NRMO branch only. No `zarame96/DecisionCompass`
file was created, modified, or proposed for modification by this note.*
