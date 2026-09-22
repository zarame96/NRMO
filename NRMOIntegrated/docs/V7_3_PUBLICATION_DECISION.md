# NRMO v7.3 — Publication Decision: PROVISIONAL Status Removed

**Decision date:** 2026-09-22.
**Decision maker:** Human Sovereign (repository owner, `zarame96` /
Takashi Ikeya), recorded in chat directly to this session.
**Decision:** Remove the NRMO Integrated System v7.3 build's overall
PROVISIONAL status.
**New status:** **FINAL — READY FOR MAIN INTEGRATION.**
**Basis:** `NRMOIntegrated/docs/V7_3_PUBLICATION_READINESS.md` (the
2026-09-22 readiness assessment prepared earlier the same day).
**Canon:** `NORMATIVE_CANON.md` — **unchanged by this decision.**
**Repository:** `zarame96/NRMO`, branch `claude/nrmo-version-7-4-piox1y`.
**`main` merge: NOT part of this decision** — see §4 below.

---

**POST-MERGE UPDATE (2026-09-22, same day, separate Human Sovereign
approval):** PR #16 merged. Merge commit
`cb5d2b406d4c302b1e092c619a7cf716973d1e71`. The specification remains
FINAL. Repository integration is now complete: `main` contains this
decision, Part XVI, both immutable original source files, and the full
documentation trail listed in §1. **Current active status: FINAL ---
MAIN INTEGRATED.** This update does not change anything this decision
recorded below — the "New status" field above, and §4's description of
main-merge as a "separate, later decision," describe accurately what
was true and undecided at the moment this record was written, earlier
the same day; they are preserved unedited as history. The merge itself
was a distinct decision, made later that day and recorded in this
session's chat, not by this document.

---

## 1. What this decision is

This record documents a single, narrow decision: removing the v7.3
build's PROVISIONAL marking, wherever that marking appears as an active,
reader-facing status claim (frontmatter notice, Part XVI provenance box,
PDF title page/metadata/running headers, master `.tex` comments).

**This decision does not itself perform any other action.** It does not
adopt Item 5b, does not amend `NORMATIVE_CANON.md`, does not write to
`zarame96/DecisionCompass`, and does not merge this branch into `main`.
Each of those remains separately gated, as detailed below.

## 2. Basis for this decision

`V7_3_PUBLICATION_READINESS.md`, prepared the same day, found all 10 of
its stated `PROVISIONAL_REMOVAL_READY` criteria objectively met:

| Criterion | Status at decision time |
|---|---|
| Original v7.3 source located and authenticity-verified | YES |
| Every prior SOURCE-PENDING item reclassified against the original | YES — 0 terminal SOURCE-PENDING rows |
| No unresolved normative conflict | YES — 0 |
| No authority inversion | YES — 0 |
| No unadopted content presented as normative | YES — 0 |
| `NORMATIVE_CANON.md` unamended | YES — diff vs `main` empty |
| Consistency guards pass | YES — `check_v73_consistency.py`, `check_v73_original_sources.py`, `terminology_audit.py` all PASS |
| Clean PDF build, no new warning classes | YES — 533 pages, 0 errors, 0 "Float too large" |
| DecisionCompass implementation gaps documented (not required closed) | YES — 10.1a, 11.1b tracked, non-blocking |
| Human Sovereign has disposed every item open at branch start | YES — Items 1–4, 6, 5a, 5b all finally disposed |

NRMO v7.3 normative/spec blockers at decision time: **0.**

## 3. What changes and what does not

### Changes (this decision + its implementation pass)

- Active status text in `frontmatter/v73_provisional_notice.tex`, Part XVI
  (`parts/part16_v73_production_contract.tex`), and the master file
  (`NRMO_Integrated_System_v7_3.tex` — `pdftitle`, `pdfsubject`,
  running header, title page, `\date{}`, build comments) updated from
  `PROVISIONAL` to `FINAL --- READY FOR MAIN INTEGRATION`.
- `V7_3_PUBLICATION_READINESS.md`, `V7_3_ADOPTION_PROPOSAL.md`,
  `V7_3_ADOPTION_RECORD.md`, `V7_3_DIFFERENTIAL_TABLE.md` each carry a
  dated update note pointing to this decision record. **None of their
  prior text is deleted or rewritten** — each note is appended,
  preserving the historically-accurate statements of what those earlier
  documents did or did not do at the time they were written.
- The v7.3 PDF is rebuilt to reflect the status-text changes (LOOP G of
  the implementing pass; see the branch's final report for build
  details).

### Explicitly does NOT change

- `NORMATIVE_CANON.md` — untouched (diff vs `main` is empty).
- The two immutable original source files
  (`NRMOIntegrated/source/v7.3/original/NRMO SYSTEM_7.3.md`,
  `NRMO_SYSTEM_v7_3_PATCH.md`) — untouched, SHA-256 unchanged, verified
  by `check_v73_original_sources.py`.
- Item 5b's disposition — remains `DEFERRED / OUT OF v7.3 NORMATIVE
  SCOPE — NOT ADOPTED` (2026-09-22, a separate decision made earlier the
  same day; not reopened or affected by this one).
- Parts I–XV, v7.2 preserved historical material — untouched.
- `zarame96/DecisionCompass` — no file read-write beyond the existing
  read-only conformance evaluation; no Issue opened.
- Repository integration state — `main` is not merged into by this
  decision (see §4).

## 4. Publication status vs. repository integration status

These are two distinct questions, and this decision resolves only the
first:

1. **Publication status of the v7.3 specification content**: was
   PROVISIONAL; is now **FINAL**, as of this decision.
2. **Repository integration status** (has the branch carrying this
   content been merged into `main`): **NOT YET, as of this decision** —
   `main` remains at its pre-existing HEAD, and this branch
   (`claude/nrmo-version-7-4-piox1y`) remains ahead of it, unmerged.
   Merging is a distinct, later Human Sovereign action, requiring its
   own explicit instruction. This decision record's recommended active
   status wording — **FINAL --- READY FOR MAIN INTEGRATION** — is
   deliberately phrased to keep these two facts visibly separate,
   rather than a bare "PUBLISHED" claim that would misstate the second
   fact. **Update: that distinct, later action has since happened** —
   see the POST-MERGE UPDATE note above. As of PR #16's merge, both
   questions resolve to the same answer: **FINAL --- MAIN INTEGRATED.**
   The reasoning above for why the wording separated the two facts
   remains valid and is preserved as written.

## 5. Guardrails (carried from `V7_3_ADOPTION_RECORD.md` /
`NORMATIVE_CANON_ADOPTION.md` precedent)

- No content adopted, rejected, or reclassified by this decision beyond
  the PROVISIONAL/FINAL status label itself.
- No SOURCE-PENDING or PROVISIONAL history is deleted; each is
  superseded-and-cited, with a dated note, per the established
  discipline of this branch's documentation.
- This decision does not merge `claude/nrmo-version-7-4-piox1y` into
  `main`.
- This decision does not write to `zarame96/DecisionCompass`.
- This decision does not change `NORMATIVE_CANON.md`.
- This decision does not adopt Item 5b.

---

*Recorded under the NRMO Founding Charter's authority order
(`Human Sovereign → Vision → NRMO → Engines → Implementations`).*
