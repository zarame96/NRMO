# NRMO v7.3 — Adoption Record

**Status:** ADOPTED (partial) — 5 of 6 items adopted; 1 item deferred.
**Basis:** `NRMOIntegrated/docs/V7_3_ADOPTION_PROPOSAL.md` (the unsigned
proposal this record completes).
**Decision date:** 2026-09-21.
**Decision maker:** Human Sovereign (repository owner, `zarame96` /
Takashi Ikeya), recorded in chat directly to this session.
**Canon:** `NORMATIVE_CANON.md` — **unchanged by this record.**

---

## ⚠️ SUPERSEDED / REINTERPRETED AFTER ORIGINAL SOURCE DISCOVERY (2026-09-21, later same day)

**This entire document below this notice is preserved exactly as
written and decided. Nothing below is deleted, rewritten, or retracted.**
This notice records how to *read* it now, not a change to what it says.

Later on 2026-09-21, the original `NRMO SYSTEM_7.3.md` /
`NRMO_SYSTEM_v7_3_PATCH.md` — which this record and
`V7_3_ADOPTION_PROPOSAL.md` both describe as `ORIGINAL SOURCE NOT
AVAILABLE` — were located, supplied directly by the Human Sovereign, and
authenticity-verified. Full detail:
`NRMOIntegrated/docs/V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md`.

Effect on the six items decided below:

- **Items 1, 2, 3, 4 (rows 3.2, 4.2, 4.4, 5.1)**: the located original
  confirms each at or near verbatim.
  `NRMOIntegrated/docs/V7_3_DIFFERENTIAL_TABLE.md` now classifies these
  `ORIGINAL-CONFIRMED` rather than reading them only through this
  record's "New Explicit Adoption" framing.
- **Item 6 (row 11.1)**: **not reverted to SOURCE-PENDING.** The
  original confirms the response-content fields (now differential-table
  row 11.1a, `ORIGINAL-CONFIRMED`); several persistence/trace-schema
  fields this record adopted (component-version provenance,
  vetoed-candidates-with-reasons, StrongEngine score metadata, persisted
  Human Sovereign accept/modify/reject) have no original precedent at
  all (now row 11.1b, `HUMAN-SOVEREIGN-ADOPTED TRACE EXTENSION`) — this
  record's explicit 2026-09-21 adoption of them **remains the operative
  decision** for those fields specifically, independent of original-text
  status.
- **Item 5 (row 10.1, §4 below)**: the original confirms only a
  presentation-layer default (3 named alternatives, A/B/C) — narrower
  than, and a different architectural layer from, both the deferred
  seven-category text and the Revision 2 addendum this record and
  `V7_3_ADOPTION_PROPOSAL.md` §11 describe. **Neither the seven-category
  text nor Revision 2 is adopted by the original's discovery.** Both
  remain exactly as this record left them: the seven-category text
  DEFERRED/never-adopted, Revision 2 proposed/not-adopted.
  **Further update (2026-09-22, Human Sovereign decision)**: Revision 2
  (row 10.1b) is formally disposed as `DEFERRED / OUT OF v7.3 NORMATIVE
  SCOPE — NOT ADOPTED` — not a rejection, preserved in full as a future/
  independent proposal, and explicitly not a v7.3 publication blocker.
  See `docs/V7_3_PUBLICATION_READINESS.md`.
- **PROVISIONAL status (§5–§6 below)**: on 2026-09-22, separately from
  and later than every item decision recorded here, the Human Sovereign
  removed the v7.3 build's overall PROVISIONAL status on the basis of
  `V7_3_PUBLICATION_READINESS.md`'s readiness assessment. See
  `docs/V7_3_PUBLICATION_DECISION.md`. §6's statement that "[t]his record
  does not remove the v7.3 build's PROVISIONAL status" remains true as a
  description of what *this* record did; it no longer describes the
  build's *current* status, which is now **FINAL — READY FOR MAIN
  INTEGRATION**.

**This record's decisions were made in good faith under incomplete
evidence and are preserved as historically valid** — not superseded
because they were wrong, but recontextualized because stronger evidence
(the original itself) subsequently became available. See
`V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md` for the complete
reclassification and reasoning.

---

## 1. What this record is

This is the completed §10 decision block of
`V7_3_ADOPTION_PROPOSAL.md`, transcribed here as a standalone, permanent
record — following the same pattern as `NORMATIVE_CANON_ADOPTION.md`
(an adoption record separate from the Canon it operates on).

**This is not a claim that the lost "NRMO SYSTEM v7.3" original text has
been recovered, reconstructed, or located.** Per
`V7_3_DIFFERENTIAL_TABLE.md`'s formal finding, that text remains
**ORIGINAL SOURCE NOT AVAILABLE**, and the search for it is closed (Human
Sovereign instruction, 2026-09-20). Every item adopted below is adopted
as **new, explicit, 2026 content**, on the surviving evidence listed in
`V7_3_ADOPTION_PROPOSAL.md` §3 (Canon, v7.2/v7.2.1, DecisionCompass Issue
#120, implementation-scope docs, conformance evidence) — not as a
restoration of anything the original document is confirmed to have said.

## 2. Decision table

| # | Row | Item | Decision | 
|---|---|---|---|
| 1 | 3.2 | Empty `A_allowed` ⇒ `HOLD`, no execution candidate | **ADOPT** |
| 2 | 4.2 | Norn observable-responsibility list | **ADOPT** |
| 3 | 4.4 | Norn drift-classification vocabulary | **ADOPT** |
| 4 | 5.1 | §14 ordered ten-step decision procedure | **ADOPT** |
| 5 | 10.1 | StrongEngine candidate-surface categories | **DEFER** |
| 6 | 11.1 | DecisionRecord / trace schema | **ADOPT** |

## 3. Adopted items (1, 2, 3, 4, 6) — effective 2026-09-21

Each adopted item's text is exactly as proposed in
`V7_3_ADOPTION_PROPOSAL.md` §5 (items 1, 2, 3, 4, 6), reproduced verbatim
in Part XVI (`parts/part16_v73_production_contract.tex`) with its inline
tag updated from `(ADDED / SOURCE-PENDING)` to:

> **`ADOPTED (v7.3, New Explicit Adoption — Human Sovereign, 2026-09-21)`**

This tag is deliberately distinct from `UNCHANGED`/`CLARIFIED` (which
would misrepresent these items as having pre-existing Canon/v7.2
precedent — they do not, individually, as composite/itemized content;
only their sub-components do, as already documented per-item in the
proposal) and distinct from a bare removal of the SOURCE-PENDING marker
(which would erase the provenance history the Canon's version/provenance
rule, §10, requires to stay legible). The tag carries its own adoption
date and cites back to this record and to the proposal's evidence
section, permanently.

**Corresponding changes applied in this pass:**
- `V7_3_DIFFERENTIAL_TABLE.md`: rows 3.2, 4.2, 4.4, 5.1, 11.1
  reclassified from `ADDED / SOURCE-PENDING` to `ADOPTED (v7.3, New
  Explicit Adoption — Human Sovereign, 2026-09-21)`, each with a note
  preserving the original SOURCE-PENDING history rather than deleting it.
- `parts/part16_v73_production_contract.tex`: the 5 corresponding inline
  tags updated in place (text of the adopted paragraphs is unchanged from
  what was already independently Canon-audited in the LOOP A–F external
  audit; only the provenance/status framing sentence changes).
- Summary classification counts in both files updated accordingly.

**Not changed by this adoption:**
- `NORMATIVE_CANON.md` — untouched.
- The PROVISIONAL status of the v7.3 build as a whole (frontmatter
  notice, PDF title page) — **not removed**. The original source text is
  still unavailable; that fact, not the count of adopted items, is what
  the PROVISIONAL marking communicates, and it stands until a separate,
  later decision addresses the build's overall status.
- `NRMO_Integrated_System_v7_3.pdf` — **not rebuilt in this pass.** The
  `.tex` source now differs from the committed PDF's content in these 5
  provenance-framing sentences; a PDF rebuild is a follow-up action, to
  be taken only after this record is reviewed and confirmed, not
  bundled into it.
- Item 5 — remains `ADDED / SOURCE-PENDING`, status DEFERRED (§4 below).

## 4. Deferred item (5) — row 10.1, StrongEngine candidate-surface categories

**Not adopted.** Remains `ADDED / SOURCE-PENDING` in both
`V7_3_DIFFERENTIAL_TABLE.md` and Part XVI, unchanged from its
pre-existing text.

**Reason for deferral (Human Sovereign, 2026-09-21):** the *principle*
that StrongEngine Ω Full must generate sufficiently diverse candidates
within `A_allowed` is accepted. The *specific seven-category closed list*
proposed in `V7_3_ADOPTION_PROPOSAL.md` §5 Item 5 (safe/conservative;
standard; assertive/forward; information-acquisition probe; bounded
sequence/checkpoint; costed HOLD; exit/recovery) is judged insufficiently
evidenced to fix as a closed normative taxonomy (this was already flagged
in the proposal as the weakest-evidenced of the six items), and risks
unnecessarily constraining StrongEngine Ω Full's future search/candidate-
generation capability.

A revised, open-ended formulation has been requested and is prepared as
an **addendum to `V7_3_ADOPTION_PROPOSAL.md` (§11)**, with a diff against
the current Part XVI text and an independent Canon-consistency check.
**That addendum is not adopted by this record.** It awaits a separate
Human Sovereign decision.

## 5. Provenance handling (reaffirmed from proposal §9)

Three provenance categories remain distinguishable per Canon §10, and
this record does not merge them:

1. `v7.2 / v7.2.1 Canon-precedented content` — has direct textual
   precedent (unaffected by this record).
2. `v7.3 Human-Sovereign-Adopted Content (2026, evidence-based, post-hoc)`
   — items 1, 2, 3, 4, 6 as of this record.
3. `v7.3 original specification text` — still `NOT LOCATED`. Should it
   ever surface, every item adopted here must be re-diffed against it
   (proposal §9); this record does not pre-empt that comparison, and does
   not claim these 5 items are what that text said.

## 6. Guardrails (carried from `NORMATIVE_CANON_ADOPTION.md` precedent)

- No item adopted here changes `NORMATIVE_CANON.md`.
- No SOURCE-PENDING history is deleted; it is superseded-and-cited, per
  item, with a dated tag.
- This record does not remove the v7.3 build's PROVISIONAL status.
- This record does not merge `claude/nrmo-version-7-4-piox1y` into `main`.
- Item 5 is not adopted by omission or by association with the other 5;
  it required its own explicit decision, which was DEFER.

---

*Recorded under the NRMO Founding Charter's authority order
(`Human Sovereign → Vision → NRMO → Engines → Implementations`).*
