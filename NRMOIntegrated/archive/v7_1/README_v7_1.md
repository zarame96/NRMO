> **ARCHIVED (v7.1).** 正式状態は PACKAGE_MANIFEST.md / IMPLEMENTATION_STATUS.md / VALIDATION_STATUS.md を参照。

# NRMO Integrated System v7.1

**Status**: Final Build (defensive side complete)
**Date**: 2026-05-14
**Author**: Takashi Ikeya

This package contains the integrated NRMO system as of v7.1, representing
the architectural completion of the defensive side of the NRMO research
programme.

---

## What this is

NRMO (Non-Ruin Maximizing Objective) is a decision-theoretic framework
for long-horizon decision-making under absorbing failure risk. It is
operationalised across both individual and collective scales with
strict governance-execution separation.

This v7.1 build provides:

- **NRMO_Origin** — foundational 4-rule veto (Parts I-II)
- **NRMO** — strengthened operational form with 13 enhancements + Ω Full
- **NRMO_Collective** — sibling theory with collective governance
  (P-U mechanisms) + Collective Strong Engine (W-AB mechanisms)
- **World Simulation** — 9-civilisation × 75-generation multi-agent
  validation framework
- **v52_codebase** — original single-civilisation research code

---

## What this is not

- NOT a doctrine, ideology, or value system
- NOT a replacement for human judgement
- NOT a motivational engine

NRMO is a decision aid. The user remains sovereign.

---

## Architecture

```
Human Sovereign
  ↓
Vision (held by Human, NOT by NRMO)
  ↓
NRMO Core (admissibility + veto)
  ↓
Strong Engine (search within admissibility)
  ├─ Ω Full (individual)
  └─ Collective Ω Full (collective)
```

At every scale (individual, family, lineage, civilisation), the same
veto + search structure applies. This is the "fractal NRMO" principle.

---

## Empirical position

3-seed averaged comparison (small scale: 9 civilisations × 5000 agents
× 75 generations, NRMO_vNext strategy score):

| World | Baseline (v6.0) | NRMO (v6.4) | NRMO_Collective (v7.1) | Faith_Communal |
|---|---:|---:|---:|---:|
| Japan | 2.148 | **2.170** | 1.699 | 1.997 |
| China | 2.109 | **2.182** | 1.907 | 2.146 |
| Europe | 0.769 | 0.835 | **1.118** | 1.450 |
| Islamic | 1.544 | **1.616** | 1.372 | 1.431 |
| Indic | 2.017 | **2.074** | 1.555 | 1.770 |
| Polynesian | 0.943 | 1.012 | **1.207** | 1.585 |
| IndigenousAmericas | 0.213 | 0.195 | **0.890** | 0.752 |

- **NRMO (v6.4)** wins in peaceful worlds (5 out of 7)
- **NRMO_Collective (v7.1)** wins in catastrophic worlds (Europe,
  Polynesian, IndigenousAmericas)
- In IndigenousAmericas, NRMO_Collective **exceeds Faith_Communal**
  (0.890 vs 0.752) — first empirical case of non-religious framework
  outperforming Faith-based collective survival

---

## Package contents

```
NRMO_Integrated_System_v7_1/
├── NRMO_Integrated_System_v7_1.pdf    (478 pages, complete reference)
├── NRMO_Complete_v5_5.tex              (LaTeX master, kept original filename)
├── chapters/                           (Part XIII development chapters)
├── parts/                              (Parts I-XII canonical content)
├── appendices/                         (Code listings, world params)
├── frontmatter/                        (Abstract, version manifest, final build statement)
├── world_sim_v50/src/                  (World Simulation v6.1 unified)
│   ├── vnext_plus.py                   (v6.3 bridge module)
│   ├── vnext_pp_v64.py                 (v6.4 NRMO 13 enhancements)
│   ├── nrmo_collective_v70.py          (v7.0 collective P-U layer)
│   ├── collective_engine_v71.py        (v7.1 collective Strong Engine)
│   ├── collective_v71_wrapper.py       (v7.1 integration wrapper)
│   └── world_sim_v6_1_unified.py       (top-level simulator)
├── v52_codebase/                       (original single-civ research code)
└── ROADMAP.md, RECONSTRUCTION_TRACKER.md, this README
```

---

## Usage

```bash
# v7.1 with collective Strong Engine (full)
python world_sim_v6_1_unified.py --scale medium --collective_engine

# v6.4 NRMO with 13 enhancements only
python world_sim_v6_1_unified.py --scale medium --nrmo_pp

# baseline (v6.0)
python world_sim_v6_1_unified.py --scale small
```

CLI flags supported:
- `--vnext_plus`: v6.3 Adaptive NRMOvNext + Ω Full
- `--nrmo_pp`: v6.4 with all A-M enhancements
- `--collective`: v7.0 collective governance layer
- `--collective_engine`: v7.1 with Collective Strong Engine
- `--memetic`, `--black_swan`, `--counterfactual`: Stage 4 features

---

## Future work (out of v7.1 scope)

- **NPMO** (Non-Passivity Maximizing Objective): offensive theory
  complementing NRMO. Together to be unified under a Holdings layer
  at user-sovereign level. Reserved for separate volume.
- **Vision integration**: deliberately not implemented. Vision belongs
  to the user, not to NRMO. See Final Build Statement in PDF.
- **Statistical validation**: 30+ seed validation with formal t-test
  for publication-grade empirical claims.
- **Ablation study**: per-enhancement contribution measurement
  (currently 13 A-M + 6 P-U + 6 W-AB combined effects only).

---

## Reading order

For first-time readers:
1. Final Build Statement (this volume's positioning)
2. Abstract
3. Per-Part Version Manifest
4. Part I (NRMO_Origin foundational reference)
5. Part XIII (development chronology, v5.0 → v7.1)

For implementers:
1. Final Build Statement
2. Part IX (Ω Full specification)
3. Part XIII v6.4, v7.0, v7.1 chapters
4. `world_sim_v50/src/` code with inline documentation

For researchers tracing the development:
1. RECONSTRUCTION_TRACKER.md
2. ROADMAP.md
3. v52_codebase/ as historical reference

---

## v7.2 rev2 追加 (Part XV + code/)

### Part XV: Universal Adapter Framework
NRMO/Loom を domain 非依存にする adapter 構造を追加.
- 6D state (R,E,G,O,K,X) を domain 横断の共通言語とする
- DomainAdapter (4 必須メソッド + Hybrid 用 propose_high_output)
- Hybrid controller (高出力 engine × Loom Safety Floor)
- 4 domain 実証 (civilisation / 金融 / 店舗 / 健康)

### code/ ディレクトリ (実行可能プログラム同梱)
```
code/
├─ python/    汎用 framework + 4 adapter + Loom v3.1 core (完全動作)
│   └─ nrmo_universal_adapter.py  (python3 で直接実行可)
├─ cpp/       header-only C++ core + 店舗 demo + Makefile
│   └─ make run  でビルド・実行
└─ frontend/  index.html (ブラウザで開くだけ, offline, プログラミング不要)
```

実証済み Hybrid 効果 (vs Loom 単体):
| Domain | Ruin | Hybrid 効果 |
|--------|------|------------|
| civilisation | resource/exposure collapse | cum_prod 高出力の 98%, ruin 0% |
| 金融 portfolio | drawdown > 40% | max drawdown 18.6%→1.1% |
| 店舗運営 | cash < 15 | survival 35→85-108 step |
| 健康管理 | disease_risk > 80 | score 973→1134 |

最終 identity:
  NRMO = Hybrid(高出力 engine, Loom v3.1) + Sociable Shadow + DomainAdapter
