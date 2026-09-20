# NRMO v7.3 — Adoption Proposal for Remaining SOURCE-PENDING Content

**Status:** PROPOSAL ONLY — NOT ADOPTED. No signature below means no decision
has been made. This document changes nothing by itself.
**Scope:** The 6 rows marked `ADDED / SOURCE-PENDING` in
`NRMOIntegrated/docs/V7_3_DIFFERENTIAL_TABLE.md` and correspondingly marked
`(ADDED / SOURCE-PENDING)` in `NRMOIntegrated/parts/part16_v73_production_contract.tex`.
**Does not touch:** `NORMATIVE_CANON.md` (unchanged, not proposed for
change), `NRMO_Integrated_System_v7_3.pdf`/`.tex`, Part XVI, or the
differential table's existing classifications. This proposal is a decision
record awaiting signature, not an edit to any of those files.
**Prepared by:** Claude (external post-restore audit session), at Human
Sovereign's request, following LOOP A–F audit approval.
**Date prepared:** 2026-09-20.

---

## 1. Fact of source loss

The original **"NRMO SYSTEM v7.3"** specification text — the two files
named in DecisionCompass Issue #120 as supplied 2026-09-15,
`NRMO SYSTEM_7.3.md` and `NRMO_SYSTEM_v7_3_PATCH.md` — **could not be
located**, after an exhaustive search covering:

- `zarame96/NRMO`: full `git log --all`, `git reflog --all`, `git stash
  list`, `git fsck --full --unreachable --dangling` (all empty of
  results), the working filesystem, and session scratch space;
- `zarame96/DecisionCompass`: all branches reachable from a depth-1000
  fetch of `agent/nrmo-v7-3-canonical-parity` (HEAD
  `7ee15a964bce51aba22a997e9bba31a389514ac2`);
- the Git bundle and patch files used to restore this work into the
  current session.

This is recorded as a formal finding: **ORIGINAL SOURCE NOT AVAILABLE**.
This proposal does not reopen that search. Per Human Sovereign instruction
(2026-09-20), original-source search is closed as of this document.

## 2. What this proposal is **not**

**This is not a claim that the original text has been recovered,
reconstructed, or reverse-engineered.** No content below is presented as
"what NRMO SYSTEM v7.3 actually said." Nothing in this document, if
signed, retroactively becomes "the original v7.3 spec, restored." It is a
**new, explicit adoption decision**, made in 2026 with the original text
admittedly and permanently unavailable, grounded only in the surviving
evidence listed in §3. If the original text is ever located, every item
adopted here must be re-diffed against it (§9) — adoption here does not
pre-empt or foreclose that comparison.

## 3. Surviving evidence considered

In descending order of authority, as already established by
`V7_3_DIFFERENTIAL_TABLE.md`'s evidence hierarchy:

1. **Founding Charter** (repository root) — Human Sovereignty, unaffected
   by anything below.
2. **`NORMATIVE_CANON.md`** — frozen; not modified by this proposal or by
   any possible adoption of it. Every item in §5 below has already been
   checked against it (§6).
3. **v7.2 / v7.2.1** (`NRMO_Complete_v5_5.tex`, preserved chapters,
   `docs/v72_1_validation_record.md`, `docs/v72_implementation_integration_map.md`)
   — used for the Canon-grounding of individual sub-steps where it exists
   (e.g. ruin boundary, reversibility, `A_allowed` chapters); does not
   itself contain the composite items below.
4. **DecisionCompass Issue #120** (`zarame96/DecisionCompass#120`,
   `author_association: OWNER`, created 2026-09-15 by the repository
   owner directly — i.e. by the Human Sovereign, not by an agent or a
   secondary implementation document). Identified during the LOOP C
   external audit as containing near-verbatim restatements of nearly
   every item in §4/§5. This is the single strongest surviving evidence
   for this proposal, precisely because it is owner-authored text, not
   third-party inference — but it is still not confirmed to be a
   transcription of the lost original, and is not treated as such here.
5. **DecisionCompass v7.3 implementation-scope documents**
   (`docs/NRMO_V7_3_IMPLEMENTATION_SCOPE.md`,
   `docs/NRMO_V7_3_GAP_MATRIX.md`, branch
   `agent/nrmo-v7-3-canonical-parity`) — secondary, AI/agent-authored
   documents written to conform to Canon/v7.2; used as corroborating,
   not primary, evidence.
6. **DecisionCompass conformance evidence**
   (`docs/nrmo_v7_3_conformance.json` and its cited test files, e.g.
   `tests/unit/test_nrmo_v73_mode_state_contract.py`,
   `tests/unit/test_audit.py`, `tests/unit/test_nrmo_v73_procedure_contract.py`)
   — spot-verified during the LOOP F external audit to contain real,
   substantive assertions, not placeholders. Per `NORMATIVE_CANON.md`
   §11, this is implementation evidence of what has already been *built*,
   not a source of theory; it is listed here only because an
   implementation existing in conformity with an item is one data point
   among several, never sufficient by itself (§6, §8).
7. **`NRMOIntegrated/docs/V7_3_DIFFERENTIAL_TABLE.md`** — the
   row-by-row reconciliation this proposal draws its item list and
   classifications from, including the external LOOP A–F audit addendum.

## 4. The 6 SOURCE-PENDING items

Row numbers refer to `V7_3_DIFFERENTIAL_TABLE.md`.

| # | Row | Item |
|---|---|---|
| 1 | 3.2 | Empty `A_allowed` ⇒ `HOLD`, no execution candidate generated |
| 2 | 4.2 | Norn detailed observable-responsibility list |
| 3 | 4.4 | Norn drift-classification vocabulary |
| 4 | 5.1 | §14 ordered ten-step decision procedure |
| 5 | 10.1 | StrongEngine candidate-surface category checklist |
| 6 | 11.1 | DecisionRecord / decision-trace schema field list |

## 5. Proposed adoption text (verbatim, per item)

Each block below is the **exact text that would become normative for
NRMO v7.3** if this item is signed for adoption. It is reproduced from
Part XVI (already independently audited for Canon-consistency, LOOP A/E)
with its authority framing corrected from "SOURCE-PENDING, offered as a
working assumption" to "adopted by explicit 2026 Human Sovereign
decision."

### Item 1 (row 3.2) — Empty admissible set

> If `A_allowed` (equivalently `A_t`) is empty, the execution layer
> returns `HOLD` and generates no execution candidate.

**Evidence for this item:** entailed by Canon §8 ("execution may never
expand `A_t` on its own authority") — if governance has narrowed `A_t` to
`∅`, no admissible candidate can exist by construction. Independently
stated, near-verbatim, in Issue #120 §B ("If `A_allowed` is empty,
execution returns `HOLD` and generates no candidate"). DecisionCompass
`lifecycle-human-gate` conformance evidence (`UNIT_VERIFIED`) is
consistent with it, but is not itself offered as proof of the rule.

### Item 2 (row 4.2) — Norn observable responsibilities

> Required Observable Responsibilities: branch record (proposed /
> admissible / selected / rejected alternatives); procedure audit
> (whether the ordered evaluation of Item 4 was actually followed by the
> runtime, including detection of missing or reordered steps);
> conceptual-drift observation (descriptive only — see Item 3; no
> Norn-owned decision threshold is permitted); passive observation
> (stagnation, opportunity loss, adaptation delay); post-decision,
> one-way observation that cannot alter the decision already made;
> upstream observation immediately after normalized World Model /
> Observation, where the runtime makes this feasible.

**Evidence for this item:** consistent elaboration of Canon §7.1
("interpretive governance perspective... not the sovereign, not the
final decision maker, not StrongEngine, not an execution engine"), which
states Norn's role generally but does not itemize it. Near-verbatim match
to Issue #120 §C. DecisionCompass `norn-read-only-audit` conformance
evidence spot-verified (`test_norn_observe_does_not_mutate_result`,
`test_v73_norn_records_branch_upstream_and_passive_facts_only`) to
contain real, non-placeholder assertions of this behavior.

### Item 3 (row 4.4) — Norn drift-classification vocabulary

> Descriptive change classes: `DRIFT | SIGNAL | WITHIN_OWN_RANGE |
> INSUFFICIENT_HISTORY`. Descriptive only; no Norn-owned decision
> threshold is permitted ("audit has no scale").

**Evidence for this item:** no Canon or v7.2/v7.2.1 chapter precedent
located (this vocabulary is unrelated to the quantitative "Long-Horizon
Drift Control" metric in the StrongEngine Ω Full chapter, which is a
different concept under the same English word). Verbatim match to Issue
#120 §C. DecisionCompass `test_v73_drift_class_names_are_canonical` spot-
verified as a real test, not a placeholder.

### Item 4 (row 5.1) — §14 ordered ten-step decision procedure

> 1. Vision / Mission alignment. 2. Ruin boundary check. 3. Reversibility
> check. 4. `A_allowed` narrowing. 5. Information sufficiency check.
> 6. Execution candidate generation. 7. Observation indicator recording
> (Norn). 8. Exit condition statement. 9. Reevaluation condition/date
> statement. 10. Return final authority to Human Sovereign.

**Evidence for this item:** every individual step already has independent
Canon or chapter grounding (cited inline in Part XVI §`sec:v73-decision-
procedure`); the *composite, ordered packaging* of these ten steps as one
traceable procedure has no single-document Canon/v7.2 precedent.
Verbatim match, in the same order, to Issue #120 §D. DecisionCompass
`procedure-events` conformance evidence (`UNIT_VERIFIED`,
`tests/unit/test_nrmo_v73_procedure_contract.py`) implements this order
but is implementation evidence, not proof of normative status (§6 of
`NORMATIVE_CANON.md`).

### Item 5 (row 10.1) — StrongEngine candidate-surface categories

> Preserve safe/conservative; standard; assertive/forward;
> information-acquisition probe; bounded sequence/checkpoint plan;
> costed HOLD (where `A_allowed` admits it); exit/recovery (where
> required) as the minimum candidate-category surface inside
> `A_allowed`. Invariant (already Canon, unaffected): no advisory or
> presentation layer may substitute an inadmissible action for
> StrongEngine's selection.

**Evidence for this item — weaker than Items 1–4, stated plainly:**
Chapters `ch20_strong_engine.tex` and the Ω Full chapter describe
candidate generation generally but list no such category checklist.
**Issue #120 does not state this exact category list either** — its
"existing baseline" section names overlapping but non-identical
DecisionCompass features (`costed HOLD`, `minimum-forward`,
`option decay`, `information gain`) without presenting them as a closed
taxonomy. This item's category list appears to originate from the
AI-authored `docs/NRMO_V7_3_IMPLEMENTATION_SCOPE.md` rather than from
Issue #120 itself. **This is the single weakest-evidenced item of the
six** and is flagged as such for the Human Sovereign's judgment — the
underlying principle (StrongEngine may not select outside `A_allowed`) is
already Canon; only the specific seven-category enumeration is genuinely
proposed-new.

### Item 6 (row 11.1) — DecisionRecord / trace schema

> Persist: authority/spec version and component versions; operational
> mode / context override / Type ZERO internal gate (qualified per the
> Type-ZERO disambiguation) / lifecycle state / MISSION-DEFENSE flag;
> Vision/Mission reference where supplied; `ruin_severity` and
> `ruin_origin` as two separate fields; reversibility classification;
> admissible and vetoed candidates with reasons; selected action and
> StrongEngine score metadata; observation indicators (Norn); exit
> conditions; reevaluation conditions/date; Norn branch/procedure/drift
> observations; Human Sovereign's recorded acceptance, modification, or
> rejection, where captured.

**Evidence for this item:** Canon §10 requires publication/baseline/
component/implementation-snapshot version distinguishability in general
but does not enumerate a decision-trace schema. Near-verbatim match to
Issue #120 §I. DecisionCompass `decision-record` conformance evidence
(`UNIT_VERIFIED`) is consistent with it.

## 6. Canon-conflict check

**No item in §5 conflicts with `NORMATIVE_CANON.md`.** This was verified
during the LOOP A–F external audit, independently of this proposal:

- No item asserts `HOLD` or `MISSION-DEFENSE` as an Operational Mode.
- No item describes StrongEngine as redefining the ruin boundary.
- No item grants Norn veto, execution, or threshold authority — Item 2
  and Item 3 are explicitly descriptive/audit-only, consistent with
  Canon §7.1 and §8.
- No item equates `SHUTDOWN` with `SAFE`.
- No item lets `TRAINING` mutate real-world state or `HARE` disable ruin
  avoidance (neither is addressed by these 6 items).
- No item redefines Passive Ruin as mere inactivity (not addressed by
  these 6 items; the Passive Ruin window definition is a separate,
  already-`CLARIFIED`, non-SOURCE-PENDING row).
- No item negates or omits `a_t ∈ A_t` (Item 1 restates it; Item 5's
  invariant clause restates it).
- No item claims to amend `NORMATIVE_CANON.md`.
- No item references v7.4 scope.
- No item names any actor other than Human Sovereign as holding final
  authority (Item 4, step 10, explicitly returns final authority to
  Human Sovereign).
- No item describes Vision as NRMO-owned or NRMO-generated.
- No item flattens Type ZERO gating labels and Operational Mode into one
  enum, or Hard/Soft-Ruin and Active/Passive-Ruin into one 4-value enum
  (neither axis is addressed by these 6 items).

This check was performed with `NRMOIntegrated/tools/check_v73_consistency.py`
(14-guard version, LOOP D) against the Part XVI text these items are
drawn from, in addition to manual Canon-section cross-reading (LOOP A).
**`NORMATIVE_CANON.md` requires no change for any of the 6 items to be
adopted.**

## 7. If adopted: what changes and to what

Adoption is **per-item**, not all-or-nothing (see §10 — six independent
decisions). For each item signed "ADOPT":

- Its classification in `V7_3_DIFFERENTIAL_TABLE.md` changes from
  `ADDED / SOURCE-PENDING` to a new, distinct tag:
  **`ADOPTED (v7.3, New Explicit Adoption — Human Sovereign, <date>)`**.
  This tag is deliberately **not** `UNCHANGED` or `CLARIFIED` (which
  would misrepresent it as having always had Canon/v7.2 precedent) and
  **not** a bare removal of the SOURCE-PENDING marker (which would erase
  the provenance history). It carries the adoption date and remains
  permanently traceable to this proposal document and to §3's evidence
  list.
- Part XVI's inline `(ADDED / SOURCE-PENDING)` tag for that item's
  paragraph is replaced with a citation to this proposal and its
  adoption date, and the paragraph's hedging language ("offered as the
  current best-evidence working assumption... subject to revision if the
  original v7.3 text is later located") is replaced with adoption
  language that still preserves the §9 re-diff obligation.
- The provisional-build framing (frontmatter notice, PDF title page
  "PROVISIONAL BUILD") is **not** automatically removed by adopting some
  or all of these 6 items — that framing exists because the *original
  source itself* remains unavailable (§1), which adoption of surviving-
  evidence content does not change. A separate, later decision would be
  needed to change the PROVISIONAL status of the whole build.

**None of the above edits are made by this proposal document itself.**
They are the described consequence of a future signature, to be executed
as a separate, subsequent commit after signature, following this
proposal's exact terms.

## 8. If not adopted (per item)

An item left unsigned, or explicitly marked "DEFER" or "DECLINE" (§10):

- Remains `ADDED / SOURCE-PENDING` in the differential table, unchanged.
- Its text remains in Part XVI exactly as currently written (provisional,
  hedged), or — at the Human Sovereign's separate future instruction —
  may be removed from Part XVI entirely if declined outright. This
  proposal does not remove any content; a decline does not, by itself,
  trigger deletion.
- Is not treated as rejected-forever: per the "preserve, do not erase"
  guardrail already established in `NORMATIVE_CANON_ADOPTION.md`, a
  declined or deferred item may be revisited if new evidence (including,
  but not limited to, the original source text) surfaces later.
- Does not block adoption of the other 5 items; each is independent.

## 9. Provenance handling

- This proposal, and any resulting per-item adoption, is recorded as
  **`v7.3 Human-Sovereign-Adopted Content (2026, evidence-based, post-
  hoc)`** — a distinct provenance category from `v7.3 original
  specification text` (still `NOT LOCATED`) and from `v7.2 / v7.2.1
  Canon-precedented content` (has direct textual precedent). Per Canon
  §10, these three categories must remain distinguishable and must not
  be silently merged.
- Should the original `NRMO SYSTEM_7.3.md` / `NRMO_SYSTEM_v7_3_PATCH.md`
  ever be located after some or all items here are adopted, each adopted
  item must be **re-diffed against the recovered original**, not assumed
  equivalent to it. Three outcomes are possible per item at that time:
  confirmed match (no further action), minor drift (correction with an
  explicit correction note, per the LOOP 6 self-audit precedent already
  used in this table), or substantive conflict (the recovered original
  would then need its own Human Sovereign adoption decision, superseding
  this one — this proposal does not pre-bind that future decision).
- This document itself is dated and version-controlled (git-tracked);
  its authority is scoped to exactly the 6 items in §4 and lapses in
  scope (though not in historical record) if superseded by a located
  original text per the paragraph above.

## 10. Human Sovereign decision

Nothing in this document is adopted until this section is completed and
signed. Mark each item independently.

| # | Item | Decision (ADOPT / DEFER / DECLINE) | Notes |
|---|---|---|---|
| 1 | Empty `A_allowed` ⇒ `HOLD` (row 3.2) | _______________ | |
| 2 | Norn observable responsibilities (row 4.2) | _______________ | |
| 3 | Norn drift-classification vocabulary (row 4.4) | _______________ | |
| 4 | §14 ordered ten-step procedure (row 5.1) | _______________ | |
| 5 | StrongEngine candidate-surface categories (row 10.1) | _______________ | weakest-evidenced item, see §5 |
| 6 | DecisionRecord / trace schema (row 11.1) | _______________ | |

**Human Sovereign (name):** _______________________________

**Signature:** _______________________________

**Adoption date:** _______________________________

**Scope statement (optional, free text — e.g. conditions attached to any
ADOPT decision above):**

_______________________________________________________________________

_______________________________________________________________________

---

*This document was prepared under the NRMO Founding Charter's authority
order (`Human Sovereign → Vision → NRMO → Engines → Implementations`). It
proposes; it does not decide. No entity other than the Human Sovereign may
complete §10.*
