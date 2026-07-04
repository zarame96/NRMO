# NRMO Complete System v5.5 — Construction Roadmap

**Goal**: Produce a single ~280-300 page LaTeX monograph integrating:
- v5_updated.pdf (v4 monograph, 222p) — preserved core
- arXiv paper (formal theorems T1-T4)
- vNext Design Spec (simulator, 9 strategies)
- Integrated Spec v2.0 (Ω Full, 30 civilisations)
- v2.5 implementation (this codebase)
- Empirical validation (April 2026 results)
- Methodological notes (Option C, statistical lessons)

**Author**: Takashi Ikeya (Zarame)
**Target completion**: 6-8 sessions

---

## Part Structure

```
NRMO Complete System v5.5
├── Frontmatter
│   ├── Abstract (v5.5 unified statement) — 2p
│   ├── ToC, LoF, LoT — auto
│
├── Part 0: Manifest & Context Handoff (rewritten for v5.5) — 5p
│
├── Part I: NRMO Foundational Reference [PRESERVE from v4] — 26p
│   ├── Ch 1: Foundational Reference (DAG & Primordial NRMO)
│   ├── Ch 1.1: Core Mechanisms — Why NRMO Works
│   ├── Ch 1.2: Problem Classes Formalization
│   └── Ch 1.3: Shutdown Architecture
│
├── Part II: NRMO Complete System v2.1 [PRESERVE from v4] — 114p
│   ├── Ch 2: NRMO+Z+PP Secretary Modules (R/W/Z/G/ORIENTATION + ZERO)
│   ├── Ch 3: TTM/PPS — Tactical Training Mode (with 400-pattern catalog)
│   ├── Ch 4: HST-N — Human State Topology
│   ├── Ch 5: A_allowed — Permitted Action Set
│   ├── Ch 6: SOP OS
│   ├── Ch 7: Investment SOP
│   ├── Ch 8: DAG Layer (4 Core Gates)
│   ├── Ch 9: Theoretical Invariants
│   ├── Ch 10: Hare-no-Hi OS Festival Protocol
│   ├── Ch 11: Hare-no-Hi Narrative Random Generator
│   ├── Ch 12: Operational Refinements
│   ├── Ch 13: A_allowed Dictionary
│   ├── Ch 14: A_allowed Concrete Values v1.1
│   ├── Ch 15: APCSO Operational & Applied Guide
│   ├── Ch 16: Parallel OODA — APCSO Trigger Spec
│   ├── Ch 17: Integrated Operation Flow
│   ├── Ch 18: NRMO Life SOP v2.0
│   ├── Ch 19: Limitations and Future Work
│   ├── Ch 20: Strong Engine Architecture — Caged Beast Model
│   ├── Ch 21: NRMO-Engine Separation Principle
│   └── Ch 22-31: Governance Structure (Reflex/Mode/Meta/Time/Situation/NonErgodic)
│
├── Part III: Structural Consistency and Registry [PRESERVE from v4] — 26p
│
├── Part IV: U-DEF-01 Addendum [PRESERVE from v4] — 2p
│
├── Part V: Theoretical Foundation v4 [PRESERVE from v4] — 5p
│   └── Ch 32: NRMO Theoretical Foundation
│
├── Part VI: R1-FIX Patch (Chapters 26-35) [PRESERVE from v4] — 38p
│   └── Ch 33: Revised Chapters 26-35
│   └── Ch 34: Test Suite — 200 Cases + 9 Failure Reproductions
│   └── Ch 35: Appendix A — Minimal Formal Specification
│   └── Ch 36: Appendix C — Illustrative Toy Simulation
│   └── Ch 37: Structural Consistency Statement
│
└── ═══════════ NEW IN v5.5 ═══════════
│
├── Part VII: Mathematical Formalization — 18p
│   ├── Ch 38: Problem Formulation (formal MDP setup)
│   ├── Ch 39: Theorem 1 — Ruin Dilution
│   ├── Ch 40: Theorem 2 — CMDP Separation
│   ├── Ch 41: Theorem 3 — Variational Analysis (Exponential Threshold)
│   ├── Ch 42: Theorem 4 — Polynomial-Time CVaR Tractability
│   └── Ch 43: NRMO Algorithm — Phased Parallel Execution
│
├── Part VIII: vNext Civilisation Simulator — 18p
│   ├── Ch 44: Civilisation State Vector (R,E,G,O,K,X)
│   ├── Ch 45: Five World Families
│   ├── Ch 46: Action Space and State Transition Model
│   ├── Ch 47: Ruin Taxonomy (True / Passive)
│   ├── Ch 48: Adaptive Tuning Layer
│   └── Ch 49: Nine-Strategy Comparison Framework
│
├── Part IX: StrongEngine Ω Full — 22p
│   ├── Ch 50: Candidate Population System (base/mutation/synthesis/invention)
│   ├── Ch 51: Wolf Pursuit Mode
│   ├── Ch 52: Edge Survival Guard
│   ├── Ch 53: Portfolio Synergy
│   ├── Ch 54: Dual Objective Scoring
│   ├── Ch 55: Long-Horizon Drift Control
│   └── Ch 56: 30-Civilisation Casebook Design
│
├── Part X: Engineering Implementation v2.5 — 16p
│   ├── Ch 57: Pipeline Architecture (NRMO + MAPLayer + Shinobi + Norn + Ω Full)
│   ├── Ch 58: Module Structure
│   ├── Ch 59: Mode-Aware Productivity Weight (the v2.5 fix)
│   ├── Ch 60: Pipeline Algorithm with Pseudocode
│   └── Ch 61: Diagnostic Toolchain (bypass_test, trace_deaths, run_chunk)
│
├── Part XI: Empirical Validation 2026 — 20p
│   ├── Ch 62: Validation Methodology (n=50 vs n=500 caveats)
│   ├── Ch 63: Five-World Survival Results
│   ├── Ch 64: v5.2 Baseline Reproduction
│   ├── Ch 65: v2.0 → v2.5 Evolution Trace
│   ├── Ch 66: Statistical Comparison (z-tests, SE bounds)
│   └── Ch 67: Death Cause Analysis
│
├── Part XII: Methodological Notes — 12p
│   ├── Ch 68: Option C Hybrid Experiment (v5.2 adapter via monkey-patch)
│   ├── Ch 69: Five Failed PStress Approaches (env-drag, race_conf, instant-shock, portfolio, rollout-purity)
│   ├── Ch 70: Verification Tools (transition equivalence, RNG wrapper, patch effectiveness)
│   ├── Ch 71: Statistical Discipline (smoke vs 500-run lessons)
│   └── Ch 72: Open Research Questions
│
└── Appendices — 30p
    ├── A: Full Code Listing (engine/omega_full.py and core modules)
    ├── B: World Parameter Specifications
    ├── C: Full 30-Civilisation Roster with Profiles
    └── D: Session Development Log (5 → 8)
```

**Estimated total pages**: ~310 pages (222 preserved + ~88 new)

---

## Session Schedule

### Session A (this session — DESIGN)
- Project skeleton (`.tex` files, Makefile)
- Part 0 (Manifest v5.5) — fully written
- Frontmatter abstract — fully written
- Roadmap document (this file)
- Part VII-XII Chapter abstracts (1 paragraph each)
- Bibliography stub

### Session B (PART I + II.A — ~30p)
- Part I: Foundational Reference (Ch 1) — full LaTeX from PDF text
- Part II Ch 2-5: Secretary Modules + TTM/PPS + HST-N + A_allowed

### Session C (PART II.B — ~40p)
- Part II Ch 6-15: SOP OS through APCSO Operational Guide
- Special focus: tables, action space dictionaries

### Session D (PART II.C + III — ~40p)
- Part II Ch 16-31: OODA through Governance Structure (Reflex/Mode/Meta/Time/Situation/NonErgodic)
- Part III: Structural Consistency and Registry

### Session E (PART IV-VI — ~45p)
- Part IV: U-DEF-01 Addendum
- Part V: Theoretical Foundation v4 (Ch 32)
- Part VI: R1-FIX Patch + Test Suite (Ch 33-37)
- This is heavy because Ch 34 has 200 test cases as tables

### Session F (PART VII-VIII — ~36p — NEW WRITING)
- Part VII: Mathematical Formalization (4 theorems with full proofs)
- Part VIII: vNext Civilisation Simulator
- Source: arXiv paper + vNext Design Spec

### Session G (PART IX-X — ~38p — NEW WRITING)
- Part IX: StrongEngine Ω Full
- Part X: Engineering Implementation v2.5
- Source: Integrated Spec v2 + nrmo_full v2.5 codebase

### Session H (PART XI-XII + APPENDICES — ~62p — NEW WRITING)
- Part XI: Empirical Validation 2026
- Part XII: Methodological Notes
- Appendices A-D
- Final compilation, index, cross-references
- Bibliography full population

---

## Source Material Map

| Section | Primary Source | Method |
|---|---|---|
| Part 0 | New (this session) | Original writing |
| Part I-VI | NRMO_v5_updated.pdf (222p) | Text extract → LaTeX reconstruct |
| Part VII | NRMO_arXiv_Ikeya.pdf (7p) | Direct adaptation |
| Part VIII | NRMO_vNext_Design_Specification_v2.pdf | Direct adaptation |
| Part IX | NRMO_Integrated_Spec_v2.pdf | Direct adaptation |
| Part X | nrmo_full_v2_5_final.zip + SESSION_HANDOFF-8.md | Original writing |
| Part XI | This session's measurements | Original writing |
| Part XII | SESSION_HANDOFFs 5-8 | Original writing |

---

## Compilation

```bash
cd nrmo_v55
pdflatex -shell-escape NRMO_Complete_v5_5.tex
makeindex NRMO_Complete_v5_5.idx
pdflatex -shell-escape NRMO_Complete_v5_5.tex
pdflatex -shell-escape NRMO_Complete_v5_5.tex   # for cross-refs
```

**Tooling note**: This needs LaTeX with `tikz`, `algorithm`, `listings`, `cleveref`, `microtype`, `ltablex`. All standard in TeX Live.

---

## Per-Session Handoff Protocol

At end of every session:
1. Update this roadmap with completed Parts
2. List new `.tex` files created
3. Note open issues / decisions deferred
4. Estimate next session's scope

---

## Decisions Already Made

- **Language**: English throughout (consistent with arXiv paper, publishable)
- **Style**: academic monograph (prose + theorem environments + tables)
- **TeX class**: `report` two-side, A4, 11pt
- **Architecture**: master `.tex` with `\input{}` per Part — keeps individual files manageable
- **Preservation principle**: Part I-VI content preserved verbatim (with light copyedit) from v4; new Parts VII-XII add new content
- **Naming**: "v5.5" not "v5", to indicate this builds on v4 (= v5_updated.pdf labelled v4) with substantial new content but no breaking change to the cognitive system core

## Decisions Deferred

- Bibliography style: BibTeX vs biblatex — defer until Session F
- Index policy: which terms to index — defer until Session H
- Color print vs B&W: monograph likely B&W for production, color for digital — defer

---

## v5.5 → v6.2 Extension (May 2026)

### What was added

The original v5.5 monograph (438 pages) was extended with v5.2--v6.2
World Simulation development:

**Stage 1.1 (v5.1)**: Three orthogonal features — ahistorical event
catalog (20 events), frequency modes (sporadic/frequent/sparse),
encounter mechanism (4 channel × 4 intensity).

**Stage 1.2 (v5.2--v5.4)**: Three-tier Spotlight (individual / family /
civilisation), 3000-year horizon (75 generations), Multi-civ parallel
(4 civs).

**Stage 2 (v5.5)**: Cohort Spotlight expansion to 100+ named individuals
with diversity grid sampling.

**Stage 3 partial (v6.0)**: 9 Cultural Modules (Japan, China, Europe,
Islamic, Indic, SubSaharan, Polynesian, Steppe, IndigenousAmericas) and
18 inter-civ interaction pairs. Scale reached 10⁶ agents (target 10⁷
not achieved due to environment constraints).

**Unified (v6.1)**: Single configurable simulator with 4 scale presets
(small/medium/large/custom).

**Stage 4 partial (v6.2)**: Memetic dynamics, Black Swan event catalog
(9 events), Counterfactual mode (6 scenarios). GPU acceleration not
implemented.

**Calibration (v6.2)**: 9/9 civilisations tuned to historical demography
target ranges (Cook 1998, McEvedy & Jones 1978, Diamond 1997, Reich
2018).

### File layout (v6.2)

```
nrmo_v55/
├── NRMO_Complete_v5_5.pdf         (460 pages, was 438)
├── NRMO_Complete_v5_5.tex
├── chapters/
│   ├── ch_part_xiii_world_simulation_vision.tex   (v5.0--v5.0.1)
│   └── ch_part_xiii_v52_to_v62.tex                (v5.1--v6.2, NEW)
└── world_sim_v50/
    ├── src/                       (21 .py files including v6.1, stage4, calibration)
    └── outputs_v55..v62_demo/     (per-stage validation outputs)
```

### Honest claim

- Stage 3 nominal target (10⁷ agents) not achieved; reached ~3 × 10⁶
- Stage 4 GPU acceleration not implemented (numba/CUDA blocked)
- Counterfactual mode operates only via inter-civ shock modulation,
  not era-fixed `base_failure` override
- Calibration is seed-sensitive: Black Swan-enabled runs may push
  Europe or Polynesian below target range

## v6.4 → v7.0 (NRMO_Collective)

### What was added

**NRMO renaming finalized**:
- `NRMO_Origin`: original 4-rule veto (Part I-II)
- `NRMO`: strengthened operational form (formerly NRMO_vNext)
- `NRMO_Collective`: v7.0 sibling with collective governance layer

**Six collective governance mechanisms (P-U)**:
- P. Multi-tier pooling (family → lineage → civ cascade, rates 0.25/0.15/0.10)
- Q. Quorum coordination (55% threshold, blend toward majority)
- R. Strategy reproduction (0.70 inherit, 0.05 mutate)
- S. Solidarity state (cohesion 0..1, shock multiplier 1.5x..0.55x)
- T. Tradition blending (per-strategy weight, Faith_Communal=0.60)
- U. Ultra-horizon (afterlife/karma → effective gamma → 1)

**Key empirical finding**:
NRMO_Collective vs Faith_Communal gap (catastrophic worlds):
- IndigenousAmericas: +0.539 → -0.085 (NRMO_Collective EXCEEDS Faith_Communal)
- Europe: +0.681 → +0.342 (50% reduction)
- Polynesian: +0.642 → +0.429 (33% reduction)

BUT peaceful worlds degraded: Japan 2.148 → 1.729, Indic 2.017 → 1.532

### Honest claim

NRMO_Collective is NOT a strict improvement over NRMO. It is a principled
trade-off: peacetime efficiency ↔ crisis-time survival. The Faith_Communal
empirical advantage was always this trade-off implicitly; v7.0 makes it
architecturally explicit and tunable.

### File additions
- `chapters/ch_part_xiii_v70_collective.tex`
- `world_sim_v50/src/nrmo_collective_v70.py` (~650 lines, 6 mechanisms)
- `--collective` CLI flag in `world_sim_v6_1_unified.py`

## v7.0 → v7.1 (Collective StrongEngine — Architectural Symmetry Completion)

### What was added

**Structural defect resolved**: v7.0 had collective veto rules (P-U) but
no collective search engine. v7.1 adds the missing Strong Engine for
collective governance, completing the fractal NRMO principle: at every
scale (individual, family, lineage, civ, world), veto and search coexist.

**Six new mechanisms (W-AB)**:
- W. Predictive trigger — forecast next-gen shock, pre-augment pool budgets
- X. Triage optimization — 4-factor rescue priority (knowledge/productivity/diversity/vulnerability)
- Y. Pool reallocation — dynamic surplus redistribution across tiers
- Z. Inter-civ insurance — contractual mutual insurance between civs
- AA. Candidate exploration — mutation/synthesis/invention on collective configs
- AB. Drift control — rescue dependency accumulation tracking

**Four Collective_Core veto rules**:
- Pool depletion veto (safety floor per tier)
- Rescue rate ceiling (moral hazard threshold = 0.30)
- Asymmetric mutual contract veto (asymmetry tolerance = 0.30)
- Drift threshold veto (rescue dependency ceiling = 0.55)

**Architectural invariant**:
At every scale, NRMO Core (veto) and Strong Engine (search) coexist.
Both individual and collective domains now have this symmetry.

### Empirical findings (3-seed avg, scale=small)

NRMO_Collective v7.0 → v7.1 score delta on NRMO_vNext strategy:

| World | v7.0 | v7.1 | Δ | Faith_C gap reduction |
|---|---:|---:|---:|---:|
| Polynesian | 1.156 | 1.207 | +0.052 | gap -0.052 |
| IndigenousAmericas | 0.837 | 0.890 | +0.053 | gap -0.053 |
| Europe | 1.108 | 1.118 | +0.010 | gap -0.010 |
| Indic | 1.532 | 1.555 | +0.023 | (now beats FC) |
| Japan | 1.729 | 1.699 | -0.030 | |
| China | 1.913 | 1.907 | -0.006 | |
| Islamic | 1.395 | 1.372 | -0.023 | |

Engine improves catastrophic worlds (triage + predictive trigger working),
slight peacetime overhead from search complexity.

### File additions
- `chapters/ch_part_xiii_v71_collective_engine.tex`
- `world_sim_v50/src/collective_engine_v71.py` (~970 lines)
- `world_sim_v50/src/collective_v71_wrapper.py` (~180 lines)
- `--collective_engine` CLI flag

### Honest claim
v7.1 is NOT a strict improvement over v7.0 in peaceful worlds. The Engine's
search-driven config has overhead. Improvement is consistent in hostile
worlds (+0.010 ~ +0.053). The collective governance is now architecturally
complete with veto-and-search symmetry at every scale.
