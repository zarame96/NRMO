# NRMO Complete System v5.5 — Executive Overview

**Author**: Takashi Ikeya (Zarame)
**Version**: 5.5 (April 2026)
**Status**: Complete monograph, research reference implementation
**Format**: 12 Parts + 4 Appendices, ~441 pages PDF, fully compilable LaTeX

---

## What is NRMO?

**Non-Ruin Maximization Objective (NRMO)** is a governance-first
decision-making framework for environments with absorbing failure states
(states from which recovery is structurally impossible). NRMO treats ruin
avoidance as a *hard constraint* — not a soft penalty — and maximises
long-horizon optionality, learning, and durable growth within that
constraint.

**Core principle**: *It no longer says only "do not die." It says: "do not
close the future."*

---

## Architectural Invariants

The framework rests on four non-negotiable invariants:

1. **Governance–Execution Separation**: NRMO defines admissibility
   `A_t = NRMO(X_t)`; the execution engine (StrongEngine Ω Full) searches
   within `A_t`: `a_t = Ω(A_t)`, and `a_t ∈ A_t` always holds.
2. **True Ruin as Hard Constraint**: irreversible failure states are
   excluded from admissibility regardless of expected reward.
3. **Optionality is the Long-Horizon Objective**: maximise future
   manoeuvrability inside the non-ruin domain.
4. **Intelligence is not Authority**: execution / search / strategy
   generation must be downstream of governance constraints.

---

## What This Monograph Contains (12 Parts + 4 Appendices)

**Parts I–VI (v4 Constitutional Edition, ~260 pages)**:
Foundational reference, Complete System v2.1 (Secretary Modules + 200
TTM/PPS catalogue), Structural Consistency Registry, U-DEF-01 conflict
resolution, Theoretical Foundation v4 (4 theorems with full proofs),
R1-FIX patch, **Test Suite of 200 main cases + 9 failure reproductions**.

**Parts VII–XII (v5.5 Extensions, ~86 pages)**:
- **VII**: Mathematical formalisation as arXiv preprint (T1 Ruin Dilution,
  T2 CMDP Separation, T3 Variational analysis, T4 CVaR tractability —
  full proofs).
- **VIII**: vNext Civilisation Simulator design specification (20
  sections, 6-dimensional state vector, 5 world families, 9 strategies).
- **IX**: StrongEngine Ω Full + 30-civilisation casebook (24 sections + 4
  appendices, Wolf Pursuit, Edge Survival Guard, Long-Horizon Drift
  Control).
- **X**: Engineering implementation v2.5 with full source listings of
  governance kernel, state dynamics, and Ω Full execution engine.
- **XI**: Empirical validation from 1,500 smoke episodes (per-strategy +
  per-world tables, ruin cause distribution, drift-λ ablation).
- **XII**: Methodological notes from two engineering session-handoff
  records (March 2026 v5.0 + April 2026 v2.5).

**Appendices A–D (~58 pages)**:
A: 12-module Python source listings (~2300 lines).
B: World parameter reference tables.
C: Full narratives for all 30 civilisations.
D: Project session log compendium.

---

## Headline Empirical Results

**v2.5 production stack** (Adaptive NRMOvNext + StrongEngine Ω Full),
1,500-episode smoke validation across 5 world families:

| Strategy | Survival | True Ruin | Score |
|---|---|---|---|
| **Adaptive NRMOvNext + Ω Full** | **61%** | 39% | **0.50** |
| RiskAdjustedUtility (baseline) | 59% | 41% | 0.44 |
| NRMOvNext + StrongEngine | 55% | 45% | 0.40 |
| ExpectedValueMax (textbook) | 5% | 95% | −0.50 |

**Key findings**:
- Ω Full beats RiskAdjustedUtility across all horizons (200 / 500 / 1000)
  while maintaining governance–execution separation.
- A v2.5 single-line PROBE-mode penalty (`prod_w = 0.92`) raised
  FastExpansionRace survival by +10 points with no measurable downsides.
- Score 0.55 was *rejected* because it required violating the separation
  invariant; score 0.50 is the legitimate constitutional result.
- Known weaknesses honestly reported: Vulnerable world (5%),
  FastExpansionRace world (35% vs 50% RiskAdj), small-n statistical
  significance.

---

## Source Material Provenance

Every chapter is derived from explicitly uploaded primary sources:

- `NRMO_v5.tex` (v4 monograph original LaTeX, 4722 lines)
- `NRMO_arXiv_Ikeya.pdf` (Part VII source)
- `NRMO_vNext_Design_Specification_v2.pdf` (Part VIII)
- `NRMO_Integrated_Spec_v2.pdf` (Part IX)
- `nrmo_full_v2_5_final.zip` + `NRMO_v5_2_FINAL.zip` (Part X codebases)
- `results_smoke/*.csv` (Part XI empirical data)
- `SESSION_HANDOFF.md` + `SESSION_HANDOFF-8.md` (Part XII)
- 3 supplementary HTML files (Japanese-language original specs)

All originals are archived in `v4_source/` for OCR-loss-free preservation.

---

## How to Read This Monograph

- **Practitioner**: Start with Parts II (operational) and X (engineering
  implementation).
- **Researcher / theorist**: Start with Part VII (mathematical
  formalisation) and Part V (theoretical foundation v4).
- **Engineering team**: Read SEPARATION.md audit (Part X §2) first, then
  Parts VIII–XI for design / validation flow.
- **Decision-maker**: Read this overview, then Part IX §1 (Executive
  Summary) and Part XI §6 (empirical-claim status).

---

## Files in This Distribution

| File | Purpose |
|---|---|
| `NRMO_Complete_v5_5_FINAL.pdf` | Compiled monograph (441 pages) |
| `nrmo_v55_LaTeX_only.zip` | LaTeX sources + primary-source archive (OCR-loss-free) |
| `nrmo_v55_full_project.zip` | Complete project: LaTeX + PDF + assets |
| `RECONSTRUCTION_TRACKER.md` | Reconstruction provenance and status |
| `NRMO_v5_5_OVERVIEW.md` | This document |

---

*NRMO Complete System v5.5 — Unified Specification: Mathematical
Foundations, Cognitive Architecture, and Empirical Validation. Takashi
Ikeya, 2026.*
