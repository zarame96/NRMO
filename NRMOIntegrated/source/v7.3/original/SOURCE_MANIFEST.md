# NRMO v7.3 — Original Source Manifest

**Status:** Immutable original source. Read `docs/V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md`
first for the authenticity assessment and reclassification this
manifest supports.

## Immutable-original policy

**The two files in this directory must never be edited, reformatted,
translated, or otherwise modified.** Any correction, annotation,
disambiguation, or extension belongs in a *separate* document that
references these files — never in these files themselves. If a
byte-identical copy is ever needed elsewhere in this repository, copy
it verbatim and verify the SHA-256 below matches; do not re-type or
re-encode it. This directory exists specifically so that "source
package supplied" (as DecisionCompass Issue #120 phrased it) is never
again true only of an external issue-tracker reference with no
corresponding file in this repository — the incident this manifest is
a direct response to.

## Files

### `NRMO SYSTEM_7.3.md`

| Field | Value |
|---|---|
| SHA-256 | `474b635063830d12ec4065e6a13d77ab455af4bfef70e10e917a07948e85c712` |
| Size | 25,013 bytes |
| Supplied date (per DecisionCompass Issue #120) | 2026-09-15 |
| Rediscovered/provided date (this repository) | 2026-09-21 JST (2026-09-20 UTC) |
| Authority role | NRMO v7.3 operational knowledge document / Governance Kernel / Decision Support Specification, for an LLM/GEM assistant persona. Self-declared **Status: Operational Knowledge Document**; explicitly prohibits being read as a personality-AI (`人格AI`) or as a final decision-maker (§1). |
| Relationship to v7.2 Integrated System | **Subordinate.** §1: "あなたの役割は、NRMO Integrated System v7.2 を権威参照として、ユーザーの意思決定を支援することです" (your role is to support the user's decisions using NRMO Integrated System v7.2 as the authoritative reference). Restates the Founding Charter authority order (`Human Sovereign → Vision → NRMO → Engines`) verbatim in its own §2. No occurrence of `NORMATIVE_CANON` or any Canon-amendment claim anywhere in the file. |

### `NRMO_SYSTEM_v7_3_PATCH.md`

| Field | Value |
|---|---|
| SHA-256 | `dbb79f8aeb4455031f598da7666608374fc7cbfcd0c8220629972b4b1705825d` |
| Size | 12,800 bytes |
| Supplied date (per DecisionCompass Issue #120) | 2026-09-15 |
| Rediscovered/provided date (this repository) | 2026-09-21 JST (2026-09-20 UTC) |
| Authority role | A patch/verification record against `NRMO SYSTEM_7.2.md`, citing `NRMO_Integrated_System_v7_2.pdf` (511p) and the `nrmo_v72_phase1` implementation as its own authorities. Self-labeled "第3版・実装検証済み" (3rd edition, implementation-verified), dated 2026-09-15, adjudicated by "Zarame" (the repository owner). **Mixes two content types that must be read separately** (see `V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md` §4): prescriptive/normative sections (第1–3部, the actual source of items 1–4/6 in the discovery record) and dated, point-in-time implementation observations (第4–5部) that describe the `nrmo_v72_phase1`/DecisionCompass codebase state as of 2026-09-15 specifically and must not be read as permanent normative claims. |
| Relationship to v7.2 Integrated System | **Subordinate / corrective.** Presents itself as reconciling the operational knowledge document against the v7.2 PDF and implementation, explicitly retracting (第0部「撤回」) its own two prior editions' misreadings of the codebase. Does not claim to amend `NORMATIVE_CANON.md` (no occurrence found). |

## Authenticity summary

See `docs/V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md` §2 for the full
assessment. Summary: 6 independently falsifiable technical claims in
`NRMO_SYSTEM_v7_3_PATCH.md` were checked against the actual
`zarame96/DecisionCompass` codebase; all were confirmed exactly, except
one (a Shinobi-router rename claimed "not yet executed") which was
found one day stale relative to the patch's own stated verification
date — consistent with ordinary analysis-to-write-up time skew, not
with fabrication. Assessed as high-confidence genuine.

## Verifying integrity of these copies

```
sha256sum "NRMO SYSTEM_7.3.md" "NRMO_SYSTEM_v7_3_PATCH.md"
```

Expected output must match the SHA-256 values in the tables above
exactly. If it does not, do not use the file — the copy has been
altered or corrupted; restore from git history or request the original
again.

## Referencing documents

- `NRMOIntegrated/docs/V7_3_ORIGINAL_SOURCE_DISCOVERY_RECORD.md` — full
  discovery record, authenticity assessment, and item-by-item
  reclassification.
- `NRMOIntegrated/docs/V7_3_DIFFERENTIAL_TABLE.md` — not yet updated to
  reflect this discovery (as of this manifest's commit); still reflects
  the pre-discovery state.
- `NRMOIntegrated/docs/V7_3_ADOPTION_PROPOSAL.md`,
  `NRMOIntegrated/docs/V7_3_ADOPTION_RECORD.md` — preserved unmodified,
  historical record of the evidence-based reconstruction effort made
  before these originals were located.
- `NRMOIntegrated/parts/part16_v73_production_contract.tex` — not yet
  updated to reflect this discovery.
