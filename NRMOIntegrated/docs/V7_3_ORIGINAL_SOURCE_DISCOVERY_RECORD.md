# NRMO v7.3 — Original Source Discovery Record

**Status:** Discovery record. Read-only reclassification of the 6
previously-SOURCE-PENDING items against the located original text.
**Does not:** modify `NORMATIVE_CANON.md`; adopt or apply Item 5
Revision 2; rebuild `NRMO_Integrated_System_v7_3.pdf`; change
publication/PROVISIONAL status; merge to `main`; delete or alter
`V7_3_ADOPTION_RECORD.md` or `V7_3_ADOPTION_PROPOSAL.md`.

---

## 1. Discovery

**Date discovered:** 2026-09-21 JST (2026-09-20 UTC) — uploaded to this
Claude Code session as file attachments and hash-verified the same day.
Recorded in JST to match this project's existing adoption-record
convention (`V7_3_ADOPTION_RECORD.md`, `V7_3_ADOPTION_PROPOSAL.md` §11
Revision 2, both dated 2026-09-21 JST); the session's own clock runs UTC,
hence the dual notation here.

**Files:**

| File | SHA-256 | Size |
|---|---|---|
| `NRMO SYSTEM_7.3.md` | `474b635063830d12ec4065e6a13d77ab455af4bfef70e10e917a07948e85c712` | 25,013 bytes |
| `NRMO_SYSTEM_v7_3_PATCH.md` | `dbb79f8aeb4455031f598da7666608374fc7cbfcd0c8220629972b4b1705825d` | 12,800 bytes |

These are exactly the two filenames DecisionCompass Issue #120 named as
"supplied 2026-09-15" and which `V7_3_DIFFERENTIAL_TABLE.md`'s
source-authenticity note (and the entire LOOP C search protocol) had
been unable to locate. Both files are currently held, unmodified, at
this session's scratchpad (`original_v73_source/`) as preservation
copies; they have **not** been committed into this repository, edited,
or otherwise processed. Committing the raw originals into the repository
is a separate decision not made by this record.

## 2. Authenticity assessment (external, objective corroboration)

Performed by cross-checking specific, falsifiable technical claims in
`NRMO_SYSTEM_v7_3_PATCH.md` against the actual `zarame96/DecisionCompass`
codebase (read-only clone, this session):

| Claim in PATCH.md | Verified against actual code |
|---|---|
| `core/mode_selector.py` returns `NORMAL/VENTURE/MISSION/SAFE` + `TRAINING/HARE` | ✅ Exact match, including comment wording |
| `HOLD = "EXIT_HOLD"` in `v7_maxforward/separation_engine.py` | ✅ Exact match, including the sentinel comment |
| `decisioncompass/audit/norn.py` is 125 lines | ✅ Exact (`wc -l` = 125) |
| `engine/` directory does not exist | ✅ Confirmed, repo-wide |
| `engine/norn.py`, `engine/omega_v52_adapter.py` do not exist | ✅ Confirmed |
| `NornTaskManager`/`SkuldTaskManager` rename "not yet executed" as of 2026-09-15, still active | ⚠️ Partially superseded: PR #118 ("separate Shinobi router names from canonical Norn") merged 2026-09-14, renaming these to `PECoreTaskRouter`/`FallbackTaskRouter` (line numbers 135/194, close to the patch's cited 132/190). The patch's claim was accurate as of its own analysis snapshot but one day stale relative to `main` by its stated verification date — consistent with an analysis performed against a checkout slightly behind the merge, not with fabrication. |
| `DECISIONCOMPASS_AUDIT_PERSIST` env var gates persistence | ✅ Confirmed present (in `audit/norn.py`; the patch's attribution to `audit_store.py` is a minor, immaterial mis-attribution) |

**Assessment: high-confidence genuine.** The density and specificity of
independently-verifiable technical detail (exact line counts, exact
sentinel strings, exact env var names, a same-week PR merge) is not
readily explained by fabrication.

## 3. Original document's self-definition (corrected)

`NRMO SYSTEM_7.3.md` explicitly defines itself as:

> Version: v7.3 / **Status: Operational Knowledge Document** / Scope:
> Personal Decision Support / Governance / Execution Boundary / Risk
> Control / Strategic Candidate Generation

and, in §1 Role Definition:

> あなたは「**NRMO v7.3 Governance Kernel**」です。... あなたは以下では
> **ありません**：思想家 / 教祖 / 価値体系 / **人格AI** / 最終判断者 /
> ユーザーの代替意思決定者。

**Correction to this session's earlier characterization**: this document
should **not** be described as a "personality/persona operational
document" (人格運用文書). Its own self-definition is **Operational
Knowledge Document / Governance Kernel / Decision Support
Specification** — and it explicitly, textually **prohibits** being
treated as a personality-AI (`人格AI`) or a final decision-maker. It is
an LLM/GEM-targeted *operational specification*, not a persona script;
that distinction matters and this record adopts the corrected framing
throughout.

## 4. Authority relationship to v7.2

§1 states directly:

> あなたの役割は、**NRMO Integrated System v7.2** を権威参照として、
> ユーザーの意思決定を支援することです。

Self-declared subordinate to the v7.2 Integrated System / Canon —
consistent with, not competing against, the authority order already
established in `NORMATIVE_CANON.md` §11 (Conformance Rule) and the
Founding Charter (`Human Sovereign → Vision → NRMO → Engines`, restated
verbatim in this document's own §2). This document does not claim to
amend or override v7.2/Canon anywhere; no occurrence of `NORMATIVE_CANON`
or an amendment claim was found in either original file (checked by
full-text search).

**Methodological note — normative content vs. point-in-time observation
(per Human Sovereign instruction):** `NRMO_SYSTEM_v7_3_PATCH.md` mixes
two different kinds of content that must be read separately:

- **Prescriptive/normative sections** (第1–3部: mode hierarchy, the §8
  replacement text, §4.10 Norn addition) — written as durable operational
  rules, the actual source for items 1–4 below.
- **Point-in-time implementation observations** (第4部 "実装で確定した
  事実", 第5部 "残る未解決", e.g. the `NornTaskManager` rename status,
  `engine/norn.py` non-existence) — explicitly dated verification notes
  as of 2026-09-15 against a specific codebase snapshot. These describe
  what was true of the implementation *then*; they are not normative
  claims about NRMO theory and are not treated as such here (confirmed
  above: one of them, the rename status, was already one day stale at
  time of writing — exactly the kind of drift a point-in-time
  observation is expected to accumulate, and exactly why it must not be
  read as a permanent rule).

## 5. Supersession of the "ORIGINAL SOURCE NOT AVAILABLE" finding

`V7_3_DIFFERENTIAL_TABLE.md`'s finding — and the identical finding
recorded in `V7_3_ADOPTION_PROPOSAL.md` and `V7_3_ADOPTION_RECORD.md` —
stated that the original text was **not located** in a specific,
enumerated set of searched locations: `zarame96/NRMO` (all refs,
reflog, stash, dangling objects, filesystem, session scratch),
`zarame96/DecisionCompass` (all branches reachable at the time), and the
restore bundle/patch files used earlier in this session. That finding
was accurate **as a statement about those specific searched locations**
at the time it was made — it was not, and could not have been, a claim
that the files did not exist anywhere at all (e.g. on the Human
Sovereign's own local Drive/device, which was never a location this
session had access to search).

**This record supersedes that finding going forward**: the original
files have now been supplied directly by the Human Sovereign and
authenticity-verified (§2). The prior finding is **not deleted** —
`V7_3_ADOPTION_RECORD.md` and `V7_3_ADOPTION_PROPOSAL.md` remain exactly
as committed, preserved as the historical record of the good-faith,
evidence-based reconstruction effort undertaken while the originals were
genuinely unlocated by this session. That effort's outcome (items 1, 2,
3, 4 independently converging on content nearly identical to the real
original, before the original was known to this session) is itself
notable and is preserved, not erased, alongside the superseding
reclassification below.

## 6. Six-item reclassification (initial pass)

| # | Row | Item | New classification | Basis |
|---|---|---|---|---|
| 1 | 3.2 | Empty `A_allowed` ⇒ `HOLD`, no execution candidate | **ORIGINAL-CONFIRMED** | §8.4: "許容行動集合が空のとき、実行層は HOLD を返し、候補生成を行わない。" / §15 restates the same rule. Near-verbatim match. |
| 2 | 4.2 | Norn observable-responsibility list | **ORIGINAL-CONFIRMED** | §4.10 "主務" 1–4 (分岐記録/手続き監査/ドリフト検知/Passive観測) + "二面の配置" (upstream/downstream, one-way). Near-verbatim structural and content match. |
| 3 | 4.4 | Norn drift-classification vocabulary | **ORIGINAL-CONFIRMED** | §4.10 "変化の扱い" table: `DRIFT / SIGNAL / WITHIN_OWN_RANGE / INSUFFICIENT_HISTORY` — exact label match. |
| 4 | 5.1 | §14 ordered ten-step decision procedure | **ORIGINAL-CONFIRMED** | §14 Decision Logic, steps 1–10, identical order and content to what was adopted — including the section number (`§14`) itself matching. |
| 5a | 10.1 | StrongEngine candidates, presentation layer | **ORIGINAL-CONFIRMED** (narrowly — see §7) | §6 "Strong Engine候補" / §7 "PP_Deliver Format": a default A/B/C (safe / standard / aggressive-forward) response format. Confirmed as an **output-presentation default**, not as a statement about internal candidate-generation architecture. |
| 5b | 10.1 | StrongEngine internal candidate-diversity principle | **POST-HOC / UNRESOLVED EXTENSION** | Revision 2's "must not collapse to a single risk posture" is **not stated, in any form, anywhere in either original file.** It is this session's own post-hoc extension, proposed as a separate, deeper-layer principle. Relationship to 5a is unresolved (§7) — not adopted. |
| 6 | 11.1 | DecisionRecord / trace schema | **ORIGINAL-PARTIAL + POST-HOC TRACE EXTENSION** | Split required (§7a) — some fields confirmed in original §6, others are this session's post-hoc additions with no original precedent at all. |

## 7. Item 5 — two-layer split (5a / 5b), per Human Sovereign correction

Two things must not be conflated: (a) the original's §6/§7
**output-presentation content** (what the GEM shows the user in a chat
response), and (b) **StrongEngine Ω Full's internal candidate-generation
architecture** (the theory-layer subject `V7_3_DIFFERENTIAL_TABLE.md`
row 10.1 and Part XVI's "StrongEngine Candidate Surface" section
actually address, citing `ch20_strong_engine.tex` /
`ch_part9_omega_full.tex`).

**What the original says, verbatim — nothing more, nothing less:**

> ## 6. Strong Engine候補 — 以下の3案で出す。A案：安全寄り、B案：標準、
> C案：攻め。ただし、すべて NRMO の許容行動集合内に収める。

This appears under **"6. Standard Output Format"**, itself introduced as
通常は以下の形式で回答する ("**normally** respond in the following
format" — §6's own heading concedes this is a default, not stated as an
unconditional absolute), and is echoed in **"7. PP_Deliver Format"**
("3 alternatives: A / B / C") as an alternate response template.

### 5a. `ORIGINAL-CONFIRMED` — presentation-layer default A/B/C format

The original confirms, narrowly and exactly: a **default** response
format presenting three named alternatives — A: safe-leaning
(安全寄り), B: standard (標準), C: aggressive/forward (攻め) — all
constrained within `A_allowed`. That is the full extent of what is
confirmed. **This record previously stated the requirement in stronger
terms ("always show ≥3 differentiated alternatives," "never fewer,"
"never all-safe") — those phrasings do not appear verbatim in the
original and have been removed as overreach.** §6's own wording ("通常
は" / "normally") does not support reading this as an absolute,
unconditional requirement either; it is the original's stated *default*,
no stronger claim is made here.

The original text nowhere states that StrongEngine Ω Full's *internal*
search/candidate generation is itself limited to, or defined by, exactly
three named postures — §6/§7 are response-formatting sections, and
appear separately from "2. Top-Level Hierarchy" / "4. Module Separation"
where the document defines StrongEngine's actual internal role.

### 5b. `POST-HOC / UNRESOLVED EXTENSION` — internal candidate-diversity principle

Revision 2's principle ("StrongEngine Ω Full must not collapse candidate
generation to a single risk posture when materially distinct admissible
alternatives exist") **does not appear, in any form, anywhere in either
original file.** It was authored entirely by this session, before the
originals were located, as a proposed internal-architecture principle.
It is not confirmed, not contradicted, and **not adopted** by the
original text — it simply is not addressed by it at all.

### Relationship between 5a and 5b — genuinely unresolved, not decided here

Whether 5b is a reasonable elaboration compatible with 5a (StrongEngine
could search a broader internal candidate space while the response layer
still defaults to presenting the 3 named postures from 5a), or whether it
is redundant with, or in tension with, 5a's specific fixed format, is
**not resolved by this record**. Revision 2 remains **not adopted**. Any
future decision on Item 5 should treat 5a and 5b as two separate
questions — one already `ORIGINAL-CONFIRMED` at the presentation layer,
one still an open, admittedly post-hoc, non-original proposal at the
internal-architecture layer — rather than one merged item.

## 7a. Item 6 — `ORIGINAL-PARTIAL + POST-HOC TRACE EXTENSION`, fields split

**Confirmed in original §6 (Standard Output Format), directly:**
mode/state display (Operational Mode / Context Override / Type ZERO
Mode / lifecycle state / MISSION-DEFENSE flag); ruin boundary (Hard/
Soft/Active/Passive Ruin, irreversibility); reversibility classification
(戻せる/戻しにくい/戻せない); `A_allowed` (今やってよい/保留/禁止);
candidates (§6's A/B/C, §5a above); a recommendation
(recommend/hold/reject); execution steps (今日やること/次に確認する
こと/記録すべきこと); exit conditions and reevaluation date/conditions.

**Not present in either original file — this session's post-hoc trace
extension, with no original precedent:** an explicit
authority/spec-version field (`nrmo_spec_version` itself *is* in the
original's DecisionCompass-side evidence, but the broader
"component versions" framing is not in either original file); vetoed
candidates *with reasons* as a persisted field (the original's §6 shows
only the selected recommendation, not a persisted admissible/vetoed-
with-reasons ledger); StrongEngine "score metadata" (no scoring/ranking
metadata concept appears in either original); and Human Sovereign's
recorded accept/modify/reject as a persisted, auditable field (the
original describes a live chat response, not a persistence/audit
record of the user's subsequent decision).

**Conclusion:** Item 6 is confirmed at the *content-field* level for
everything §6 already covers, but the *persistence/audit trace schema*
framing — and several of its specific fields — has no original
precedent and must be labeled a post-hoc extension, not restated as if
original.

## 8. Disposition of prior records (updated — see follow-up LOOP note below)

- `V7_3_ADOPTION_RECORD.md` — **existing decision content preserved
  unedited**; a `SUPERSEDED / REINTERPRETED AFTER ORIGINAL SOURCE
  DISCOVERY` notice was subsequently added (LOOP B) immediately after
  the header, pointing here. Nothing in the original decision text was
  deleted or rewritten.
- `V7_3_ADOPTION_PROPOSAL.md` — same treatment, same reasoning.
- `V7_3_DIFFERENTIAL_TABLE.md`, `parts/part16_v73_production_contract.tex`
  — **updated** (LOOP A / LOOP C, same overall pass): rows 3.2, 4.2, 4.4,
  5.1, 10.1a, 11.1a reclassified `ORIGINAL-CONFIRMED`; row 10.1 split
  into 10.1a/10.1b; row 11.1 split into 11.1a/11.1b
  (`HUMAN-SOVEREIGN-ADOPTED TRACE EXTENSION`); Part XVI's provenance box,
  per-item tags, StrongEngine Candidate Surface section, and Trace
  Schema chapter updated to match. Prior "ORIGINAL SOURCE NOT AVAILABLE"
  / post-hoc-adoption framing in both files is preserved inline as
  explicitly marked historical/superseded text, not deleted.
- `frontmatter/v73_provisional_notice.tex`,
  `NRMO_Integrated_System_v7_3.tex` — **updated** (LOOP D stale-provenance
  audit): both contained active, reader-facing claims that the original
  "could not be located" / "not located" (including the PDF title-page
  `\date{}` line) — corrected to reflect the 2026-09-21 discovery.
  `PROVISIONAL` status wording itself is unchanged in both.
- `NRMO_Integrated_System_v7_3.pdf` — not yet rebuilt as of this specific
  record's original text (LOOP G, later in the same overall pass, once
  source-text updates are finalized).
- `NORMATIVE_CANON.md` — unaffected throughout; not read as requiring
  any change by anything found in the original v7.3 text.

---

*Prepared as a read-only reclassification record. Item 5 remains
unresolved and Revision 2 remains unadopted pending further analysis.
No file other than this new record was modified in this pass.*
