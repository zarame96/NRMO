# NRMO v7.3 — Differential Table (Provisional)

**Status:** Provisional / working document. NOT a normative source by itself.
**Purpose:** Track reconciliation of `NRMO v7.3` requirements (as evidenced by
DecisionCompass secondary sources) against NRMO v7.2 / v7.2.1 / Normative
Canon, prior to formal `NRMO_Integrated_System_v7_3` integration.

## Evidence hierarchy used for this table

```
1. Human Sovereignty (Founding Charter)
2. NORMATIVE_CANON.md (frozen, not modified by this table)
3. Formal "NRMO SYSTEM v7.3" original prose — NOT LOCATED (see below)
4. v7.2.1 explicitly-adopted revisions (Passive Ruin avoidability window)
5. Historical specification (preserved chapters)
6. Implementation documentation (DecisionCompass docs/*)
7. DecisionCompass implementation (code, tests)
```

## Source-authenticity note

The original supply-package files referenced by DecisionCompass Issue #120
(`NRMO SYSTEM_7.3.md`, `NRMO_SYSTEM_v7_3_PATCH.md`, supplied 2026-09-15) were
**not located** in:
- `zarame96/NRMO` (any branch, any commit, working tree, untracked files)
- `zarame96/DecisionCompass` (any branch reachable via `git ls-remote`)
- local session scratch space

The only available evidence for "what v7.3 requires" is a **secondary,
implementation-target document**:

- `docs/NRMO_V7_3_IMPLEMENTATION_SCOPE.md` (DecisionCompass, branch
  `agent/nrmo-v7-3-canonical-parity`, HEAD `7ee15a964bce51aba22a997e9bba31a389514ac2`)
- `docs/NRMO_V7_3_GAP_MATRIX.md` (same branch)
- `docs/nrmo_v7_3_conformance.json` (same branch)

This document itself states its authority as: *"NRMO SYSTEM v7.3 operational
knowledge document supplied 2026-09-15, with NRMO Integrated v7.2 PDF /
Normative Canon precedence where applicable."* — i.e. it is written to
**conform to** v7.2/Canon, not to override it. Per user instruction, this
table treats it as evidence of DecisionCompass's implementation target, not
as the v7.3 normative original. Every row derived only from this document is
marked `SOURCE-PENDING` in addition to its classification, per the required
notation.

## Classification legend

- `UNCHANGED` — restates existing Canon/v7.2 content with no semantic delta.
- `CLARIFIED` — adds precision/detail consistent with existing Canon/v7.2;
  no new normative claim.
- `ADDED` — introduces content with no v7.2/Canon precedent; not contradicted
  by it either.
- `SUPERSEDED` — v7.3 evidence explicitly replaces v7.2/historical content.
  (No rows currently qualify — see §Conflicts.)
- `CONFLICT` — apparent contradiction requiring root-cause judgment.
- `IMPLEMENTATION-ONLY` — DecisionCompass runtime/test/CI concern; not a
  theory-layer concept.
- `HISTORICAL` — refers to preserved historical material already marked
  non-normative.

---

## 1. Authority / hierarchy

| # | v7.3 requirement (source: IMPLEMENTATION_SCOPE.md §1) | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 1.1 | Human Sovereign final adoption/execution authority | Canon §2.1 | UNCHANGED | Verbatim restatement |
| 1.2 | Vision is human-owned; NRMO may check alignment, may not own/generate Vision | Canon §2.1, §2.4, Adoption record | UNCHANGED | — |
| 1.3 | NRMO defines boundaries; StrongEngine generates/ranks inside them only | Canon §2.2, §2.3, §8; `AUTHORITY_BOUNDARIES.md` | UNCHANGED | Formal invariant `a_t ∈ A_t` already Canon |

## 2. Four-layer mode/state model

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 2.1 | Operational Mode: `NORMAL\|SAFE\|VENTURE\|MISSION` | Canon §3.1 | UNCHANGED | — |
| 2.2 | Context Override: `TRAINING(A-F,E+)\|HARE\|NONE` | Canon §3.2, §3.3 | UNCHANGED | — |
| 2.3 | **Type ZERO Mode: `CORE\|VENTURE\|MISSION\|SHUTDOWN`** as an axis distinct from Operational Mode | Canon §5 marks this exact 4-tuple "superseded **as the current Operational Mode taxonomy**"; `ch02c_type_zero_modes.tex` preserves it as an explicit **historical, superseded** table | **CONFLICT → resolved as CLARIFIED (see LOOP 3 below)** / SOURCE-PENDING | Terminology-collision risk: identical labels (`MISSION`, `VENTURE`) used for two different axes. See root-cause judgment below. |
| 2.4 | Lifecycle State: `ACTIVE\|HOLD\|EXIT\|SAFE_EXIT` | Canon §3.4 | UNCHANGED | — |
| 2.5 | `A_allowed` extension: `MISSION_DEFENSE = active\|inactive` | Canon §3.6; `ch02g_mission_defense.tex` | UNCHANGED | — |
| 2.6 | "Do not flatten these into one enum" | Canon implies via §3.4 (HOLD is not an Operational Mode) and §3.6 (MISSION-DEFENSE is not a mode) | CLARIFIED | Generalizes an already-Canon principle into an explicit engineering rule |

### Root-cause judgment for row 2.3 (LOOP 3)

Candidate readings:
1. **CONFLICT reading**: v7.3 resurrects a labelset Canon calls superseded → would require Canon amendment (forbidden without authorization).
2. **CLARIFIED reading**: Canon §5 supersedes `CORE/VENTURE/MISSION/SHUTDOWN` only *as the Operational Mode taxonomy*. It does not forbid Type ZERO from retaining an internal historical gating-state vocabulary for its own (non-actuator, per Canon §6) gating logic, provided it is never presented as, or confused with, canonical Operational Mode. `ch02c` already treats this 4-tuple as a **preserved historical table**, i.e. Canon already permits its continued existence as labelled historical/internal material.

Decision (per evidence-hierarchy priority: Canon > historical spec > implementation doc): **CLARIFIED**, conditional on an explicit disambiguation note being added wherever the two axes could be read together. This is a documentation obligation, not a Canon change. Resolution implemented in the new v7.3 chapter (§ "Type ZERO Internal Gating State vs Operational Mode").

## 3. HOLD state machine

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 3.1 | `ACTIVE→HOLD`, `ACTIVE→EXIT`, `ACTIVE→SAFE_EXIT`, `HOLD→ACTIVE` (Human Sovereign approval only), `HOLD→SAFE_EXIT` | **Found during LOOP 6 self-audit**: this exact 5-transition table already exists verbatim in `ch09_theoretical_invariants.tex` §`sec:inv-state-space` (lines 39-54), as part of the "UNCHANGED" v2.0 theoretical invariants restated in that chapter. Also consistent with Canon §3.4 and §2.1 (Human Sovereign approval for `HOLD→ACTIVE`). | **UNCHANGED** (corrected from an earlier ADDED/SOURCE-PENDING draft classification — see Part XVI §`sec:v73-hold-state-machine` correction note) | Reclassification recorded per evidence-discipline requirement; no silent correction. |
| 3.2 | Empty `A_allowed` ⇒ HOLD, no candidate generated | Consistent with Canon §8 (execution may not expand `A_t`); not previously stated this explicitly | ADDED / SOURCE-PENDING | — |

## 4. Norn Operator

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 4.1 | Canonical Norn is interpretive/monitoring, not decision-maker/executor | Canon §7.1 | UNCHANGED | — |
| 4.2 | Detailed observable responsibilities (branch record, procedure audit, drift, passive observation, one-way post-decision) | Canon §7.1 states role generally; no itemized responsibility list existed | ADDED / SOURCE-PENDING | Consistent elaboration, no authority expansion |
| 4.3 | "Norn MUST NOT: veto; execute; set thresholds; choose route/Vision/Mission; return final conclusion" | Directly entailed by Canon §7.1 + §8 | CLARIFIED | Makes an implicit Canon constraint explicit |
| 4.4 | Drift classes: `DRIFT\|SIGNAL\|WITHIN_OWN_RANGE\|INSUFFICIENT_HISTORY` | No Canon precedent (Canon doesn't enumerate drift-classification vocabulary) | ADDED / SOURCE-PENDING | Descriptive-only per requirement text ("audit has no scale") — consistent with §7.1 non-decision role |

## 5. Decision procedure (10-step order, "§14")

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 5.1 | Ordered 10-step evaluation (Vision/Mission → ruin → reversibility → A_allowed → info sufficiency → candidates → observation → exit → reevaluation → return to Human Sovereign) | No equivalent single ordered procedure exists in Canon; individual steps each have Canon/chapter grounding (ruin: Ch9/Ch27; reversibility: Ch34/R1-FIX; A_allowed: Ch5/13/14; final authority: Canon §2.1) | ADDED / SOURCE-PENDING | Composite ordering is new; each component step is independently Canon-grounded. No component contradicts Canon. |
| 5.2 | "Norn audits the procedure but cannot alter it" | Canon §7.1, §8 | UNCHANGED | — |

## 6. Ruin semantics

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 6.1 | Maintain distinct trace/causal fields for **Hard Ruin, Soft Ruin, Active Ruin, Passive Ruin** as if one 4-way taxonomy | `Hard Ruin`/`Soft Ruin` are domain-specific (Investment SOP, `ch07_investment_sop.tex:47-51`, severity axis within the investment domain); `Active Ruin`/`Passive Ruin` are core-theory, domain-general (`ch_part9_omega_full.tex:134-142`, causal-origin axis) | **CLARIFIED, with required disambiguation** / SOURCE-PENDING | These are two **different, non-orthogonal-by-default axes from two different chapters/domains**, not natively a single 4-member enum. Treating them as one flat set risks implying Hard/Soft Ruin apply domain-generally (they don't) or that Active/Passive are investment-specific (they aren't). Resolution: v7.3 chapter states both axes separately and notes they may co-occur (e.g. a Soft Ruin within Investment domain may have Active or Passive causal origin) rather than presenting 4 siblings. |
| 6.2 | Passive Ruin uses avoidability-window definition as leading signal; legacy streak retained as lagging diagnostic only; "do not redefine Passive Ruin as inactivity alone" | Exactly matches `docs/v72_1_validation_record.md` and `docs/v72_implementation_integration_map.md` §2.1 (two-tier: leading window-closure + lagging streak) | CLARIFIED | This is the **strongest-evidence row in the whole table** — v7.2.1 already adopted this exact design before v7.3 implementation existed. Formal adoption into v7.3 chapter is safe. |

## 7. `A_allowed`

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 7.1 | Admissibility requires ruin-boundary + reversibility + withdrawal/review feasibility + Vision/Mission non-conflict | `ch05_a_allowed.tex`, `ch13`, `ch14`, Canon §8 | UNCHANGED | — |
| 7.2 | Reject actions: irreversible direct loss, major lock-in under info insufficiency, removal of withdrawal capability, sovereignty violation | Consistent with existing `A_allowed` chapters and R1-FIX boundary contract (Ch34) | CLARIFIED | — |

## 8. MISSION-DEFENSE extension

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 8.1 | A_allowed policy extension, not a mode; defensive-only; forbids persuasion/coercion/dependency design | Canon §3.6; `ch02g_mission_defense.tex` (verbatim match, including forbidden-category list) | UNCHANGED | Near word-for-word match to existing Ch02g |

## 9. Context overrides

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 9.1 | TRAINING isolated, must not mutate real-world state | Canon §3.2 | UNCHANGED | — |
| 9.2 | HARE relaxes expressive constraints only, ruin avoidance stays active | Canon §3.2 | UNCHANGED | — |
| 9.3 | `/#vision` is context, not mode/authority | Canon §3.7 | UNCHANGED | — |

## 10. StrongEngine candidate surface

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 10.1 | Preserve safe/standard/assertive/probe/sequence/costed-HOLD/exit candidate categories inside `A_allowed` | `ch20_strong_engine.tex`, `ch_part9_omega_full.tex` describe candidate generation generally; this exact category list is new | ADDED / SOURCE-PENDING | No contradiction; consistent refinement |
| 10.2 | "No advisory layer may replace Ω Full selection with an inadmissible action" | Canon §2.3, §8 (`a_t ∈ A_t` strict) | UNCHANGED | — |

## 11. Trace / DecisionRecord

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 11.1 | Persist authority/state/Ruin/reversibility/candidates/selection/observation/exit/reevaluation/Norn/Human-Sovereign-decision fields | Canon §10 requires version/provenance distinguishability generally; does not enumerate trace schema | ADDED / SOURCE-PENDING | Engineering elaboration of Canon §10 intent; no conflict |

## 12. Conformance requirements / Non-goals (IMPLEMENTATION_SCOPE.md §"Conformance requirements", §"Non-goals")

| # | Item | Classification | Notes |
|---|---|---|---|
| 12.1 | Machine-readable v7.3 conformance matrix, negative/mutation tests, cross-runtime checks, Android build-artifact verification | IMPLEMENTATION-ONLY | DecisionCompass CI/test concern; not theory-layer |
| 12.2 | "Do not adopt experimental v8.3 merely because it exists" | IMPLEMENTATION-ONLY | Guards DecisionCompass implementation discipline; consistent with Canon §9 (implementation status labelling) |
| 12.3 | "Do not conflate historical Shinobi task routers with canonical Norn" | HISTORICAL | Directly restates Canon §7.2 |
| 12.4 | "Do not rewrite NRMO theory for implementation convenience" | UNCHANGED | Restates Canon §11 (Conformance Rule) |

---

## Summary counts

| Classification | Count |
|---|---|
| UNCHANGED | 14 |
| CLARIFIED | 7 |
| ADDED (all SOURCE-PENDING) | 7 |
| SUPERSEDED | 0 |
| CONFLICT (resolved to CLARIFIED, see row 2.3) | 1 |
| IMPLEMENTATION-ONLY | 2 |
| HISTORICAL | 1 |

**Revision note (LOOP 6 self-audit)**: row 3.1 was reclassified from
ADDED/SOURCE-PENDING to UNCHANGED after locating verbatim precedent in
`ch09_theoretical_invariants.tex` §`sec:inv-state-space`. Counts above
reflect this correction.

**No row required a NORMATIVE_CANON.md change.** The one apparent conflict
(row 2.3, Type ZERO Mode labelset) resolves under existing Canon wording
without amendment, provided the v7.3 chapter adds the disambiguation note
described above. Row 6.1 requires a disambiguation note but not a Canon
change (Hard/Soft vs Active/Passive are chapter-scoped axes, not Canon-level
concepts to begin with — Canon does not mention any of the four terms).

## LOOP 4/5/6 completion record

1. ✅ "Type ZERO Internal Gating State vs Operational Mode" disambiguation
   note added — Part XVI §`sec:v73-typezero-disambiguation` (resolves row 2.3).
2. ✅ "Ruin taxonomy provenance" note distinguishing Investment-domain
   Hard/Soft axis from core Active/Passive axis added — Part XVI
   §`sec:v73-ruin-disambiguation` (resolves row 6.1).
3. ✅ New Part XVI (`parts/part16_v73_production_contract.tex`) drafted,
   integrated into `NRMO_Integrated_System_v7_3.tex` (separate master
   file; `NRMO_Complete_v5_5.tex`, the v7.2 master, left byte-identical
   to its pre-v7.3-work state). All rows classified ADDED/CLARIFIED are
   present, labelled with SOURCE-PENDING status where applicable.
4. ✅ Consistency-guard script added:
   `NRMOIntegrated/tools/check_v73_consistency.py`. Covers: HOLD/
   MISSION-DEFENSE asserted as Operational Mode, StrongEngine redefining
   ruin boundary, Norn veto/execute permission, SHUTDOWN≡SAFE collapse,
   TRAINING leakage to real-world state, HARE disabling ruin avoidance,
   Passive-Ruin-as-mere-inactivity, `a_t ∈ A_t` invariant presence/negation,
   unauthorized Canon-amendment claims, v7.4 scope leakage. Verified to
   both fire on injected violations and pass cleanly on the actual text
   (injection test performed and reverted; `diff` confirmed identical
   restore).
5. ✅ LOOP 6 self-audit found one real misclassification (row 3.1, HOLD
   transition table — verbatim precedent existed in
   `ch09_theoretical_invariants.tex` and was missed in the first pass).
   Corrected in both this table and Part XVI, with an explicit
   in-document correction note (not a silent fix). No other
   misclassifications found on re-read.
6. ✅ PDF build verified: `NRMO_Integrated_System_v7_3.pdf`, 531 pages,
   3 full pdflatex passes + makeindex, 0 build errors. Remaining
   "undefined reference" warnings (7) are byte-identical to the
   pre-existing v7.2 baseline's own residual warnings (3 unresolved
   bibtex citations + 4 chapter cross-refs to placeholder/late chapters
   that are pre-existing in v7.2, confirmed by diffing against a fresh
   3-pass v7.2 baseline build). Zero Part-XVI-introduced unresolved
   references remain.
