# NRMO v7.3 — Differential Table (Provisional)

**Status:** Provisional / working document. NOT a normative source by itself.
**Purpose:** Track reconciliation of `NRMO v7.3` requirements — as of
2026-09-21, evidenced primarily by the **located v7.3 operational
originals** (`NRMOIntegrated/source/v7.3/original/`; see
`docs/V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md`), with DecisionCompass
documentation as corroborating/conformance evidence only (not a v7.3
requirements source) — against NRMO v7.2 / v7.2.1 / Normative Canon,
within `NRMO_Integrated_System_v7_3` integration (Part XVI). Prior to
2026-09-21, this table's sole evidence for "what v7.3 requires" was
DecisionCompass secondary documentation; that phase is preserved as
history below (see each section's superseded-notice).

## Evidence hierarchy used for this table

**⚠️ SUPERSEDED 2026-09-21 — see "Evidence hierarchy, current" immediately
below.** The block directly below this notice is preserved verbatim as
the historical record of the evidence hierarchy used while the original
v7.3 text was genuinely unlocated. It is `HISTORICAL_AND_MARKED_SUPERSEDED`,
not `ACTIVE_AND_CORRECT` — do not cite line 3 below as current status.

```
1. Human Sovereignty (Founding Charter)
2. NORMATIVE_CANON.md (frozen, not modified by this table)
3. Formal "NRMO SYSTEM v7.3" original prose — NOT LOCATED (see below)
4. v7.2.1 explicitly-adopted revisions (Passive Ruin avoidability window)
5. Historical specification (preserved chapters)
6. Implementation documentation (DecisionCompass docs/*)
7. DecisionCompass implementation (code, tests)
```

### Evidence hierarchy, current (2026-09-21, post-discovery)

```
1. Human Sovereignty (Founding Charter)
2. NORMATIVE_CANON.md (frozen, not modified by this table)
3. Formal "NRMO SYSTEM v7.3" original prose — LOCATED 2026-09-21 JST.
   Stored, byte-for-byte unmodified, at
   NRMOIntegrated/source/v7.3/original/ (SHA-256 in SOURCE_MANIFEST.md).
   See NRMOIntegrated/docs/V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md for
   the full authenticity assessment and item-by-item reclassification.
4. v7.2.1 explicitly-adopted revisions (Passive Ruin avoidability window)
5. Historical specification (preserved chapters)
6. DecisionCompass Issue #120 (owner-authored requirements text,
   2026-09-15) and implementation-scope documentation (DecisionCompass
   docs/*) — corroborating, not primary, now that tier 3 is located
7. DecisionCompass implementation (code, tests) — conformance evidence
   only, per Canon §11; never a source of NRMO theory
```

Authority direction is fixed and does not change with this update:
`Human Sovereign → Canon/v7.2 → located v7.3 operational source →
integrated specification → DecisionCompass → conformance evidence`.
NRMO theory is never derived from DecisionCompass's implementation.

## Source-authenticity note

**⚠️ SUPERSEDED 2026-09-21 — see "Source status, current" immediately
below.** This note is preserved verbatim as the historical record of the
search performed while the original text was genuinely unlocated by this
session; it remains an accurate description of *that search*, not of the
current state.

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

### Source status, current (2026-09-21, post-discovery)

Both original files were supplied directly by the Human Sovereign and
authenticity-verified (see
`NRMOIntegrated/docs/V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md` §2 for
the full assessment: 6 independently falsifiable technical claims
checked against the actual DecisionCompass codebase, all confirmed).
Stored at `NRMOIntegrated/source/v7.3/original/` with SHA-256 in
`SOURCE_MANIFEST.md`. **The search recorded above is not reopened** —
it correctly describes what was and was not found in the locations this
session had access to search, and remains valid history.

## Classification legend

- `UNCHANGED` — restates existing Canon/v7.2 content with no semantic delta.
- `CLARIFIED` — adds precision/detail consistent with existing Canon/v7.2;
  no new normative claim.
- `ADDED` — introduces content with no v7.2/Canon precedent; not contradicted
  by it either.
- `ORIGINAL-CONFIRMED` — confirmed present, at or near verbatim, in the
  located original v7.3 source text (`NRMOIntegrated/source/v7.3/original/`).
- `ORIGINAL-PARTIAL` — some but not all content confirmed in the located
  original; remainder is a later, separately-labeled extension.
- `DEFERRED / OUT OF v7.3 NORMATIVE SCOPE` — proposed by this session
  before the original was located; absent from the original; explicitly
  placed outside v7.3 normative scope by Human Sovereign decision
  (2026-09-22); **not adopted, not rejected, not deleted** — an open
  proposal for a future version or independent track, and not a
  publication blocker for v7.3.
- `HUMAN-SOVEREIGN-ADOPTED TRACE EXTENSION` — content with no original-text
  precedent that the Human Sovereign explicitly adopted as new v7.3
  content on 2026-09-21, independent of original-text status.
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
| 2.3 | **Type ZERO Mode: `CORE\|VENTURE\|MISSION\|SHUTDOWN`** as an axis distinct from Operational Mode | Canon §5 marks this exact 4-tuple "superseded **as the current Operational Mode taxonomy**"; `ch02c_type_zero_modes.tex` preserves it as an explicit **historical, superseded** table; **located original confirms this axis directly**: §6 response format lists `Type ZERO Mode: CORE / VENTURE / MISSION / SHUTDOWN` as a line item separate from `Operational Mode: NORMAL / SAFE / VENTURE / MISSION`, and §8.3 gives it a dedicated definition with its own transition triggers (`IRREV`/`VOL`/`LOAD`) | **ORIGINAL-CONFIRMED + CLARIFIED** (updated 2026-09-21; was `CONFLICT → resolved as CLARIFIED` / `SOURCE-PENDING` pre-discovery — see root-cause judgment below, now updated) | Terminology-collision risk: identical labels (`MISSION`, `VENTURE`) used for two different axes remains real and is resolved the same way (qualify by axis). The original's own §6 output format already lists both axes as separate lines, directly corroborating the disambiguation. No longer `SOURCE-PENDING`. |
| 2.4 | Lifecycle State: `ACTIVE\|HOLD\|EXIT\|SAFE_EXIT` | Canon §3.4 | UNCHANGED | — |
| 2.5 | `A_allowed` extension: `MISSION_DEFENSE = active\|inactive` | Canon §3.6; `ch02g_mission_defense.tex` | UNCHANGED | — |
| 2.6 | "Do not flatten these into one enum" | Canon implies via §3.4 (HOLD is not an Operational Mode) and §3.6 (MISSION-DEFENSE is not a mode) | CLARIFIED | Generalizes an already-Canon principle into an explicit engineering rule |

### Root-cause judgment for row 2.3 (LOOP 3)

Candidate readings:
1. **CONFLICT reading**: v7.3 resurrects a labelset Canon calls superseded → would require Canon amendment (forbidden without authorization).
2. **CLARIFIED reading**: Canon §5 supersedes `CORE/VENTURE/MISSION/SHUTDOWN` only *as the Operational Mode taxonomy*. It does not forbid Type ZERO from retaining an internal historical gating-state vocabulary for its own (non-actuator, per Canon §6) gating logic, provided it is never presented as, or confused with, canonical Operational Mode. `ch02c` already treats this 4-tuple as a **preserved historical table**, i.e. Canon already permits its continued existence as labelled historical/internal material.

Decision (per evidence-hierarchy priority: Canon > historical spec > implementation doc): **CLARIFIED**, conditional on an explicit disambiguation note being added wherever the two axes could be read together. This is a documentation obligation, not a Canon change. Resolution implemented in the new v7.3 chapter (§ "Type ZERO Internal Gating State vs Operational Mode").

**Update (2026-09-21, post-discovery):** the located original independently
confirms the Type ZERO Mode axis directly (§6 output format, §8.3
definition with its own transition triggers), reached this reading
(reading 2 above) without stating it as a terminology-collision risk
requiring resolution — the original simply lists both axes side by
side. This upgrades the row to `ORIGINAL-CONFIRMED` for the axis's
existence, while the disambiguation obligation (never presenting a bare
`MISSION`/`VENTURE` without stating which axis) remains `CLARIFIED`
engineering discipline, not itself stated verbatim in the original.

## 3. HOLD state machine

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 3.1 | `ACTIVE→HOLD`, `ACTIVE→EXIT`, `ACTIVE→SAFE_EXIT`, `HOLD→ACTIVE` (Human Sovereign approval only), `HOLD→SAFE_EXIT` | **Found during LOOP 6 self-audit**: this exact 5-transition table already exists verbatim in `ch09_theoretical_invariants.tex` §`sec:inv-state-space` (lines 39-54), as part of the "UNCHANGED" v2.0 theoretical invariants restated in that chapter. Also consistent with Canon §3.4 and §2.1 (Human Sovereign approval for `HOLD→ACTIVE`). | **UNCHANGED** (corrected from an earlier ADDED/SOURCE-PENDING draft classification — see Part XVI §`sec:v73-hold-state-machine` correction note) | Reclassification recorded per evidence-discipline requirement; no silent correction. |
| 3.2 | Empty `A_allowed` ⇒ HOLD, no candidate generated | Consistent with Canon §8 (execution may not expand `A_t`) | **ORIGINAL-CONFIRMED** *(history: ADDED/SOURCE-PENDING 2026-09-20 → ADOPTED as New Explicit Adoption, Human Sovereign, 2026-09-21 → original text located same day, confirming near-verbatim match; see `V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md` §6 item 1)* | Original §8.4: "許容行動集合が空のとき、実行層は HOLD を返し、候補生成を行わない。" The 2026-09-21 adoption decision was made independently, before the original was known to this session, and is preserved as historically valid evidence-based reconstruction — not superseded by being "wrong," but confirmed by the subsequently located original. |

## 4. Norn Operator

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 4.1 | Canonical Norn is interpretive/monitoring, not decision-maker/executor | Canon §7.1 | UNCHANGED | — |
| 4.2 | Detailed observable responsibilities (branch record, procedure audit, drift, passive observation, one-way post-decision) | Canon §7.1 states role generally; no itemized responsibility list existed | **ORIGINAL-CONFIRMED** *(history: as row 3.2 above; see Discovery Record §6 item 2)* | Original §4.10 "主務" 1–4 (分岐記録/手続き監査/ドリフト検知/Passive観測) + "二面の配置" (upstream/downstream, one-way) — near-verbatim structural and content match. |
| 4.3 | "Norn MUST NOT: veto; execute; set thresholds; choose route/Vision/Mission; return final conclusion" | Directly entailed by Canon §7.1 + §8 | CLARIFIED | Makes an implicit Canon constraint explicit. Also directly confirmed in original §4.10 "禁止" list (VETOしない/実行しない/結論を出さない/針路を決めない). |
| 4.4 | Drift classes: `DRIFT\|SIGNAL\|WITHIN_OWN_RANGE\|INSUFFICIENT_HISTORY` | No Canon precedent (Canon doesn't enumerate drift-classification vocabulary) | **ORIGINAL-CONFIRMED** *(history: as row 3.2 above; see Discovery Record §6 item 3)* | Original §4.10 "変化の扱い" table: exact same four English labels. |

## 5. Decision procedure (10-step order, "§14")

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 5.1 | Ordered 10-step evaluation (Vision/Mission → ruin → reversibility → A_allowed → info sufficiency → candidates → observation → exit → reevaluation → return to Human Sovereign) | No equivalent single ordered procedure exists in Canon; individual steps each have Canon/chapter grounding (ruin: Ch9/Ch27; reversibility: Ch34/R1-FIX; A_allowed: Ch5/13/14; final authority: Canon §2.1) | **ORIGINAL-CONFIRMED** *(history: as row 3.2 above; see Discovery Record §6 item 4)* | Original §14 "Decision Logic," steps 1–10, identical order and content — **including the section number `§14` itself matching.** Each component step remains independently Canon-grounded as well. |
| 5.2 | "Norn audits the procedure but cannot alter it" | Canon §7.1, §8 | UNCHANGED | — |

## 6. Ruin semantics

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 6.1 | Maintain distinct trace/causal fields for **Hard Ruin, Soft Ruin, Active Ruin, Passive Ruin** | Located original, §4.1 (NRMO Core role list) presents them as **two separate bullet items**: "Hard Ruin / Soft Ruin identification" and "Active Ruin / Passive Ruin identification" — not one merged list; §13.1–13.4 defines all four individually; `ch07_investment_sop.tex:47-51` (Hard/Soft, severity axis) and `ch_part9_omega_full.tex:134-142` (Active/Passive, causal-origin axis) independently corroborate the same two-axis structure | **ORIGINAL-CONFIRMED + CLARIFIED (axis semantics / disambiguation required)** | **That all four concepts must be tracked** is `ORIGINAL-CONFIRMED` (original §4.1, §13.1–13.4, §6/Standard-Output-Format §3 all require it; no `SOURCE-PENDING` status remains). **That they must never be flattened into one undifferentiated 4-way enum** is `CLARIFIED`: the original's own §4.1 phrasing (two separate bullets, not "Hard/Soft/Active/Passive Ruin の識別" as a single list) already supports reading them as two axes, and this is independently corroborated by the Canon-adjacent chapter split (severity axis, domain-specific, Investment SOP; causal-origin axis, domain-general, StrongEngine Ω Full). They may co-occur (e.g. a Soft Ruin within the Investment domain may have Active or Passive causal origin) rather than being 4 mutually exclusive siblings. See Part XVI §`sec:v73-ruin-disambiguation`. |
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
| 10.1a | StrongEngine candidates, **presentation layer**: default response shows 3 named alternatives (A: safe-leaning, B: standard, C: aggressive/forward), all within `A_allowed` | Original §6 "Strong Engine候補" / §7 "PP_Deliver Format" | **ORIGINAL-CONFIRMED** (narrowly) | Confirmed exactly as a **default output-presentation format** — §6 itself says "通常は" (normally), not an unconditional absolute. **Not** a statement about StrongEngine's internal candidate-generation architecture; the original does not address that separately. See Discovery Record §7. |
| 10.1b | StrongEngine candidates, **internal generation**: "must not collapse candidate generation to a single risk posture when materially distinct admissible alternatives exist" (Revision 2 principle) | No Canon precedent; **not present in either original v7.3 file, in any form** | **DEFERRED / OUT OF v7.3 NORMATIVE SCOPE — NOT ADOPTED** (Human Sovereign decision, 2026-09-22) | Authored by this session before the originals were located, as a proposed internal-architecture principle distinct from 10.1a's output-format requirement. **Disposition (2026-09-22): not adopted into v7.3 normative scope** — located v7.3 does not contain it, 5a's presentation-layer A/B/C default is already original-confirmed and sufficient for v7.3 completeness, and 5b is not needed to restore/finalize v7.3. **This is not a rejection or deletion of Revision 2**: the proposal text is preserved in full (`V7_3_ADOPTION_PROPOSAL.md` §11) as an open candidate for a future version or an independent proposal track, outside v7.3's normative scope. **Not a v7.3 publication blocker** (see `V7_3_PUBLICATION_READINESS.md`). The original 7-category "safe/standard/assertive/probe/sequence/costed-HOLD/exit" text (proposed 2026-09-20, deferred 2026-09-21) remains `DEFERRED`, never adopted, and is not restored by this reclassification — see `V7_3_ADOPTION_RECORD.md` §4 (preserved, historical). |
| 10.2 | "No advisory layer may replace Ω Full selection with an inadmissible action" | Canon §2.3, §8 (`a_t ∈ A_t` strict) | UNCHANGED | Also consistent with original §2.4: `a_t ∈ A_t` formal invariant restated verbatim in the original. |

## 11. Trace / DecisionRecord

| # | v7.3 requirement | Canon/v7.2 baseline | Classification | Notes |
|---|---|---|---|---|
| 11.1a | Original-confirmed response-content fields: mode/state, ruin boundary, reversibility, `A_allowed`, candidates (10.1a), recommendation, execution steps, exit/reevaluation | Original §6 Standard Output Format, sections 2–9, directly | **ORIGINAL-CONFIRMED** | Every field here is directly present in the original's response format. See Discovery Record §7a. |
| 11.1b | Post-hoc persisted trace/audit fields: authority/component-version provenance, vetoed candidates *with reasons* as a persisted field, StrongEngine score metadata, persisted Human Sovereign accept/modify/reject | Canon §10 requires version/provenance distinguishability generally; does not enumerate a persistence/audit trace schema | **HUMAN-SOVEREIGN-ADOPTED TRACE EXTENSION** *(history: ADDED/SOURCE-PENDING 2026-09-20 → ADOPTED, Human Sovereign, 2026-09-21 — see `V7_3_ADOPTION_RECORD.md` item 6)* | **Not present in either original file** — confirmed absent, not merely unconfirmed (see Discovery Record §7a). Because the Human Sovereign explicitly adopted this content on 2026-09-21, it is **not** reverted to SOURCE-PENDING merely because the original doesn't contain it: this is original content (11.1a) **plus** a later, separately-labeled, explicitly-adopted normative extension (11.1b) — the two must stay distinguishable, never merged into one "11.1 confirmed" claim. |

## 12. Conformance requirements / Non-goals (IMPLEMENTATION_SCOPE.md §"Conformance requirements", §"Non-goals")

| # | Item | Classification | Notes |
|---|---|---|---|
| 12.1 | Machine-readable v7.3 conformance matrix, negative/mutation tests, cross-runtime checks, Android build-artifact verification | IMPLEMENTATION-ONLY | DecisionCompass CI/test concern; not theory-layer |
| 12.2 | "Do not adopt experimental v8.3 merely because it exists" | IMPLEMENTATION-ONLY | Guards DecisionCompass implementation discipline; consistent with Canon §9 (implementation status labelling) |
| 12.3 | "Do not conflate historical Shinobi task routers with canonical Norn" | HISTORICAL | Directly restates Canon §7.2 |
| 12.4 | "Do not rewrite NRMO theory for implementation convenience" | UNCHANGED | Restates Canon §11 (Conformance Rule) |

---

## Summary counts (recomputed 2026-09-21, post-discovery)

| Classification | Count | Rows |
|---|---|---|
| UNCHANGED | 17 | 1.1,1.2,1.3,2.1,2.2,2.4,2.5,3.1,4.1,5.2,7.1,8.1,9.1,9.2,9.3,10.2,12.4 |
| CLARIFIED | 4 | 2.6,4.3,6.2,7.2 |
| **ORIGINAL-CONFIRMED + CLARIFIED** (axis semantics disambiguation required) | 2 | 2.3,6.1 |
| CONFLICT (fully resolved, none remaining) | 0 | — |
| **ORIGINAL-CONFIRMED** | **6** | 3.2,4.2,4.4,5.1,10.1a,11.1a |
| **DEFERRED / OUT OF v7.3 NORMATIVE SCOPE** | 1 | 10.1b |
| **HUMAN-SOVEREIGN-ADOPTED TRACE EXTENSION** | 1 | 11.1b |
| SUPERSEDED | 0 | — |
| IMPLEMENTATION-ONLY | 2 | 12.1,12.2 |
| HISTORICAL | 1 | 12.3 |
| **Total rows** | **34** | |

**Zero rows remain `ADDED / SOURCE-PENDING` or `SOURCE-PENDING` as an
unresolved terminal state as of this pass** (row 6.1's prior
`SOURCE-PENDING` tag is resolved: the original confirms the four-concept
requirement outright; only the axis-semantics disambiguation remains a
`CLARIFIED`-type documentation obligation, not an unresolved evidentiary
gap). The former 7-category text for row 10.1 (now split into
10.1a/10.1b) remains `DEFERRED`/never-adopted per
`V7_3_ADOPTION_RECORD.md` §4, preserved as history, not reinstated.

**Revision note (LOOP 6 self-audit)**: row 3.1 was reclassified from
ADDED/SOURCE-PENDING to UNCHANGED after locating verbatim precedent in
`ch09_theoretical_invariants.tex` §`sec:inv-state-space`. Counts above
reflect this correction.

**Revision note (2026-09-21 adoption record — `HISTORICAL_AND_MARKED_SUPERSEDED`,
preserved verbatim for record purposes)**: rows 3.2, 4.2, 4.4, 5.1, and
11.1 — 5 of the 6 rows formerly counted as "ADDED (all SOURCE-PENDING)"
— were reclassified to `ADOPTED (v7.3, New Explicit Adoption — Human
Sovereign, 2026-09-21)` per `V7_3_ADOPTION_RECORD.md`. ~~This is an
explicit 2026 adoption decision on surviving evidence, not a claim that
the lost v7.3 original text has been located or restored (that finding,
ORIGINAL SOURCE NOT AVAILABLE, is unchanged — see the External audit
record above).~~ **The struck-through sentence is stale — see the
discovery note immediately below.** Row 10.1 (StrongEngine
candidate-surface categories) was deliberately left `ADDED /
SOURCE-PENDING` and marked DEFERRED; see `V7_3_ADOPTION_RECORD.md` §4 and
`V7_3_ADOPTION_PROPOSAL.md` §11 for its pending open-ended revision. No
row in this table required, or received, a `NORMATIVE_CANON.md` change
as part of this adoption.

**Revision note (2026-09-21, second pass — original source discovery,
`ACTIVE_AND_CORRECT`)**: later the same day, the original
`NRMO SYSTEM_7.3.md` / `NRMO_SYSTEM_v7_3_PATCH.md` were located, supplied
directly by the Human Sovereign, and authenticity-verified — see
`NRMOIntegrated/docs/V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md`. This
supersedes the "ORIGINAL SOURCE NOT AVAILABLE" finding referenced
immediately above (that finding is preserved as accurate history of the
specific search performed at the time, not deleted — see the External
audit record below, now itself annotated). Rows 3.2, 4.2, 4.4, 5.1,
10.1a, and 11.1a were reclassified a second time, from `ADOPTED (New
Explicit Adoption)` to `ORIGINAL-CONFIRMED`, because the located
original text confirms them at or near verbatim. **This is not a claim
that the 2026-09-21 adoption decision was wrong or is being discarded**
— it remains preserved, unedited, in `V7_3_ADOPTION_RECORD.md` as a
historically valid decision made under incomplete evidence, whose
outcome happened to match the subsequently-located original closely.
Row 10.1 was split into 10.1a (`ORIGINAL-CONFIRMED`, narrowly — the
presentation-layer A/B/C default only) and 10.1b (at this point still
under review as an unresolved extension; **2026-09-22 update**: formally
disposed as `DEFERRED / OUT OF v7.3 NORMATIVE SCOPE — NOT ADOPTED`, see
the 2026-09-22 revision note below — the internal-generation diversity
principle, absent from the original, not needed for v7.3 completeness,
preserved as an open future/independent proposal). Row 11.1 was split
into 11.1a (`ORIGINAL-CONFIRMED`) and 11.1b (`HUMAN-SOVEREIGN-ADOPTED
TRACE EXTENSION` — retained as adopted, per Human Sovereign instruction,
precisely because it was an explicit 2026-09-21 normative decision
independent of original-text status, not an unconfirmed guess that
should revert to SOURCE-PENDING merely because the original lacks it).

**No row required a NORMATIVE_CANON.md change.** The one apparent conflict
(row 2.3, Type ZERO Mode labelset) resolves under existing Canon wording
without amendment, provided the v7.3 chapter adds the disambiguation note
described above. Row 6.1 requires a disambiguation note but not a Canon
change (Hard/Soft vs Active/Passive are chapter-scoped axes, not Canon-level
concepts to begin with — Canon does not mention any of the four terms).

**Revision note (2026-09-22, Item 5b disposition, `ACTIVE_AND_CORRECT`)**:
the Human Sovereign reviewed row 10.1b (the internal-generation
candidate-diversity principle, "Revision 2") and decided: **DEFERRED /
OUT OF v7.3 NORMATIVE SCOPE. NOT ADOPTED.** Reasoning: (1) the located
v7.3 original does not contain it, in any form; (2) row 10.1a
(presentation-layer A/B/C default) is already `ORIGINAL-CONFIRMED` and
is sufficient, by itself, for v7.3 normative completeness on the
StrongEngine-candidates topic; (3) 5b is a later-generation, internal-
architecture proposal that is not required to restore or finalize v7.3.
**This is explicitly not a rejection or deletion**: the Revision 2 text
remains preserved in full (`V7_3_ADOPTION_PROPOSAL.md` §11) as an open
proposal for a future NRMO version or an independent track. **Row 10.1b
is not, and must not be treated as, a v7.3 publication blocker** — see
`docs/V7_3_PUBLICATION_READINESS.md`. No prior "UNRESOLVED" framing on
this row should be read as blocking v7.3 completeness; it described an
open architectural question, not a gap in the v7.3 specification
itself (which needs only 10.1a).

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

## External audit record (post-restore session, independent of the LOOP 1–6 self-audit above)

Performed against the restored commits `df171b4`/`449c1c7`/`992bfe8` in a
separate session, with fresh `git clone`-level scrutiny and an independently
installed LaTeX toolchain. Findings:

1. **3-commit content audit**: confirmed no commit modifies
   `NRMO_Complete_v5_5.tex`, `NORMATIVE_CANON.md`, or any file under
   `chapters/` (`git diff --stat` between pre-v7.3 `main` and this branch
   over those paths is empty). Confirmed Part XVI's Canon §-citations
   (§2.1, §2.3, §3.1–3.7, §5, §7.1, §7.2, §8, §9, §10, §11) accurately
   reflect the actual `NORMATIVE_CANON.md` text. Confirmed the row-3.1
   HOLD-transition "verbatim precedent" claim against
   `ch09_theoretical_invariants.tex` §`sec:inv-state-space` — precedent is
   real, not overstated. Confirmed the row-8.1 MISSION-DEFENSE
   "near-verbatim match" claim against `ch02g_mission_defense.tex` —
   accurate. Confirmed the row-6.2 Passive Ruin avoidability-window claim
   against `docs/v72_implementation_integration_map.md` §2–3 (the
   `window_open()`/`closes_window()`/leading-lagging-indicator design is
   real, not overstated; it is not in `v72_1_validation_record.md` alone —
   that file documents a separate but related diff-in-diff detection-
   sensitivity fix). No fabricated or misrepresented citation found.
2. **SOURCE-PENDING re-verification**: independently grepped the full
   `NRMOIntegrated/` corpus (chapters, parts, docs, Canon) for precedent of
   all 6 ADDED/SOURCE-PENDING rows (3.2, 4.2, 4.4, 5.1, 10.1, 11.1). No
   precedent found for any; SOURCE-PENDING status correctly retained on
   textual-search grounds, not merely because a DecisionCompass
   implementation exists.
3. **New provenance finding** (`HISTORICAL_AND_MARKED_SUPERSEDED` —
   accurate as a description of the search performed at the time;
   superseded by the 2026-09-21 discovery, see
   `V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md`; not deleted): the original
   `NRMO SYSTEM_7.3.md` / `NRMO_SYSTEM_v7_3_PATCH.md` files remain **NOT
   LOCATED** after a full pass over: this repo's entire git history/reflog/stash/dangling-object
   set (`git fsck --unreachable --dangling`: empty), the working
   filesystem, session scratch space, the restore bundle/patch files
   themselves, and `zarame96/DecisionCompass` (all branches reachable from
   a depth-1000 fetch of `agent/nrmo-v7-3-canonical-parity`, HEAD
   `7ee15a964bce51aba22a997e9bba31a389514ac2`). **Formal finding:
   ORIGINAL SOURCE NOT AVAILABLE**, per the LOOP-C search protocol.
   However, **DecisionCompass Issue #120** (`zarame96/DecisionCompass#120`,
   authored directly by the repository owner/Human Sovereign, 2026-09-15,
   `author_association: OWNER`) contains near-verbatim restatements of
   nearly every ADDED/SOURCE-PENDING item in this table and in Part XVI —
   including the exact §14 ten-step order, the exact Norn responsibility
   list (branch record / procedure audit / conceptual-drift observation /
   passive observation / downstream one-way / upstream read-only), the
   exact drift-class vocabulary (`DRIFT/SIGNAL/WITHIN_OWN_RANGE/
   INSUFFICIENT_HISTORY`), and the empty-`A_allowed`⇒HOLD rule. This is
   **not** the missing original spec text (Issue #120 does not claim to be
   a transcription of it, and may be the owner's own implementation
   synthesis rather than a copy), so it does not lift any SOURCE-PENDING
   tag by itself. It does materially strengthen the evidentiary basis for
   those rows from "AI-authored secondary implementation-scope document"
   to "directly owner-authored requirements text, predating and seeding
   DecisionCompass's own scope docs." Recommendation: cite Issue #120
   alongside `docs/NRMO_V7_3_IMPLEMENTATION_SCOPE.md` in the evidence
   hierarchy on any future revision of this table; SOURCE-PENDING tags are
   left unchanged here per the "implementation existence alone does not
   lift SOURCE-PENDING" rule and because Issue #120 is not confirmed to be
   the original spec text itself.
4. **PDF rebuild verification**: rebuilt `NRMO_Integrated_System_v7_3.pdf`
   from source (fresh `pdflatex` ×3 + `makeindex`) in this session's
   environment. Page count matches exactly (531). File size matches
   exactly (2,297,926 bytes.) Content is not byte-identical to the
   committed PDF (differs from offset 2,255,258; this is expected —
   PDF `/ID`/timestamp metadata varies by build environment even for
   otherwise-identical content). **One discrepancy from the commit's
   self-verification claim**: a fresh v7.2-baseline rebuild in this same
   environment shows 7 undefined-reference warnings (3 citations + 4
   cross-refs), but the v7.3 rebuild shows 8 (3 citations + 5 cross-refs)
   — one extra: `Reference 'sec:foundations-mech-b-constraint' on page
   114 undefined`. Root-caused to a pre-existing label/ref prefix
   mismatch in `ch07_investment_sop.tex:217` (`\ref{sec:foundations-mech-
   b-constraint}`) vs. the actual label in `ch01c_foundations_paper.tex:106`
   (`\label{eq:foundations-mech-b-constraint}`) — an `eq:`/`sec:` prefix
   typo. Both files are byte-identical between the v7.2 and v7.3 builds
   (confirmed via `git diff`), so **this is a pre-existing latent defect,
   not something Part XVI introduced**; it appears to surface
   inconsistently depending on page/section-count-driven multi-pass label
   resolution. The commit message's claim that the warning sets are
   "byte-identical" between the two baselines is therefore not exactly
   reproduced (off by one warning) in an independent rebuild — a minor,
   non-normative inaccuracy in that self-verification claim, logged here
   rather than silently corrected in the original commit message.
5. **Consistency-guard coverage gap closed**: `check_v73_consistency.py`
   covered 11 of the governance-violation classes required by the restart
   instructions but was missing checks for (a) Norn holding threshold-
   setting authority (only veto/execute were checked), (b) any actor other
   than Human Sovereign being described as holding final authority, (c)
   Vision being described as NRMO-owned/generated, (d) Type ZERO gating
   labels and Operational Mode being flattened into one enum, and (e)
   Hard/Soft-Ruin and Active/Passive-Ruin being flattened into one
   4-valued enum. All five added as new regex guards; verified 4/4 on
   injection (guard (a) reuses the existing Norn-prohibition pattern
   family and was exercised together with the veto/execute checks
   previously). Clean pass confirmed on the actual Part XVI text both
   before and after the addition; injected text fully reverted and
   confirmed via empty `git diff` after each test.
6. **DecisionCompass conformance spot-check**: fetched
   `agent/nrmo-v7-3-canonical-parity` directly (HEAD confirmed
   `7ee15a964bce51aba22a997e9bba31a389514ac2`, matching this table's
   citation) and read `docs/nrmo_v7_3_conformance.json` directly rather
   than relying on Part XVI's summary of it — the summary is accurate (12
   of 13 tracked requirements `UNIT_VERIFIED`/`SCENARIO_VERIFIED`/
   `CI_VERIFIED`, 1 `NOT_RUN_NO_CONNECTED_DEVICE`). Spot-read two evidence
   files directly (`tests/unit/test_nrmo_v73_mode_state_contract.py`,
   `tests/unit/test_audit.py`) and confirmed they contain real,
   substantive assertions matching their claimed requirement IDs (e.g.
   `test_lifecycle_hold_resume_requires_explicit_human_sovereign_approval`,
   `test_norn_observe_does_not_mutate_result`), not placeholder/vacuous
   tests. Per Canon §11, this remains implementation evidence only and
   does not make DecisionCompass a source of NRMO theory.
