# NRMO + StrongEngine Ω Full — Session Handoff Document
**Date**: March 17, 2026
**Session**: Complete implementation of Adaptive NRMOvNext + StrongEngine Ω Full v5.0

---

## 1. What Was Built

### Final Deliverable
**Adaptive NRMOvNext + StrongEngine Ω Full v5.0**
- ZIP: `NRMO_StrongEngine_OmegaFull_v5.zip`
- Integrated Spec: `NRMO_Integrated_Spec_v2.pdf` (15 pages, 28 sections)
- All source code, smoke results, plots, CSVs included

### Architecture (Immutable)
```
NRMO (governance only)          StrongEngine Ω Full (execution only)
├─ ruin boundary definition     ├─ candidate generation (mutation/synthesis/invention)
├─ admissibility judgment       ├─ candidate search & evaluation
├─ veto (YES/NO/HOLD)          ├─ risk-adjusted scoring
├─ passive ruin detection       ├─ portfolio construction
├─ mode restriction             └─ drift control
└─ execution legitimacy

Formal: A_t = NRMO(X_t), a_t = Ω(A_t), a_t ∈ A_t always holds.
Engine does NOT evaluate RUIN. RUIN = NRMO boundary only.
```

---

## 2. Repository Structure

```
nrmo_omega_full/
├── config/defaults.py          # All parameters (lambda_drift=1.0)
├── core/state.py               # S=(R,E,G,O,K,X), transition
├── core/worlds.py              # 5 world families
├── core/ruin.py                # GOVERNANCE: ruin taxonomy (9 pathways)
├── governance/nrmo_core.py     # GOVERNANCE: veto only, construct_admissible_set()
├── governance/tuning_layer.py  # GOVERNANCE: MetaController (5-mode), adaptive tuning
├── engine/omega_full.py        # EXECUTION: Ω Full (§1-§12 + drift control)
├── engine/strong_engine.py     # EXECUTION: baseline StrongEngine
├── strategies/strategies.py    # 10 strategies including default stack
├── simulation/simulator.py     # Episode runner
├── metrics/metrics.py          # Aggregation + scoring
├── metrics/plots.py            # 8 chart types
├── cli/main.py                 # Entry point
├── drift_sweep.py              # λ_drift optimization script
├── SEPARATION.md               # Governance-execution boundary documentation
├── NRMO_Integrated_Spec_v2.tex # Complete integrated specification
├── NRMO_Integrated_Spec_v2.pdf # 15-page compiled spec
├── design_spec.tex/pdf         # v5.0 engine-focused design spec
└── results_smoke/              # CSVs + PNGs from validation
```

---

## 3. Ω Full Engine — What It Does

### §1 Candidate Population System
- **base** (11 templates) → **mutation** (±0.05, 1-3 variants) → **synthesis** (pairwise avg + ±0.03) → **invention** (state×world analytical) → **pool** (~23-35 candidates)
- Pool passes through governance filter before scoring

### §2-§3 Mutation & Synthesis
- Mutation: local perturbation of each action component
- Synthesis: average of random pairs + noise

### §4-§5 Wolf Pursuit Mode
- Trigger: E≥50, G≥45, O≥45, K≥45, X≤35, dO≥0, dK≥0
- Effect: depth=8, repeats=5, portfolio=(0.75/0.15/0.10), +6 extra candidates

### §6-§7 Edge Survival Guard
- Trigger: fragility>0.65, Vulnerable world, E<40+X rising, G<40+O falling
- Effect: portfolio=(0.45/0.45/0.10), RiskAdj reference injected

### §8 Portfolio Synergy
- Pairwise compatibility matrix for hedge selection

### §9 Dual Objective
- Ruin is NOT in evaluation function (rollout just terminates)
- survived_ratio as multiplicative signal

### Long-Horizon Drift Control (Critical Fix)
```
g_sust = clip(0.15, 0.40, 0.28 + 0.08·E/100 + 0.06·G/100 - 0.10·X/100 - 0.05·env_drag)
drift = max(0, g - g_sust) × env_sensitivity × exposure_factor × gov_buffer
final_score = rollout_score - λ_drift × drift
```
- λ_drift = 1.0 (default, validated)
- Normal world: drift × 1.25
- Portfolio hedge: prefers g ≤ g_sust candidates

---

## 4. Performance Summary

### Overall Score (H200, 20 runs/cell)
| # | Strategy | Score | Surv% |
|---|----------|-------|-------|
| 1 | **Ω Full (default stack)** | **0.50** | **61%** |
| 2 | RiskAdjustedUtility | 0.44 | 59% |
| 3 | NRMOvNext+SE | 0.40 | 55% |
| 4 | Adaptive+SE | 0.34 | 51% |

### Multi-Horizon (Drift Fix)
| Horizon | Ω Full | Risk-Adj | Winner |
|---------|--------|----------|--------|
| 200 | 60% | 60% | TIE |
| 500 | 48% | 46% | Ω WIN |
| 1000 | **40%** | 33% | **Ω WIN** |

### Before Drift Fix (H1000)
Ω=35% vs RA=45% → Ω lost. After fix: Ω=40% vs RA=33% → Ω wins.

### World-Level (H200)
| World | Ω Full | Risk-Adj |
|-------|--------|----------|
| Normal | **100%** | 100% |
| LateStagnation | **100%** | 100% |
| PlanetaryStress | **65%** | 35% |
| FastExpansionRace | 35% | **50%** |
| Vulnerable | 5% | **10%** |

---

## 5. Version History (This Session)

| Version | Score | Key Change | Separation |
|---------|-------|------------|------------|
| Initial Ω Full | 0.34 | 8 modules working | ✓ |
| Portfolio dilution fix | 0.26→0.33 | Decisive pass-through | ✓ |
| P6 + action_risk | **0.55** | World-aware scoring | ✗ (violated) |
| Separation restored | 0.26 | Removed gov thresholds from engine | ✓ |
| §1-§12 Strategy Space Expansion | **0.50** | Mutation/synthesis/invention | ✓ |
| v5.0 + Drift Control | **0.50** + H1000 fix | Sustainable growth estimator | ✓ |

**0.55 was achieved by violating governance-execution separation. It is not legitimate.**
**0.50 is the correct score under constitutional compliance.**

---

## 6. Key Design Decisions & Rationale

### Why Ω Full underperformed initially
1. **Portfolio dilution**: Blending every step destroyed the best candidate's signal
   - Fix: pass-through when score gap > 0.05
2. **Growth bias in scoring**: productivity ∝ g, weight=1.00 dominated other factors
   - Fix: sustainable productivity = prod × min(E/55,1) × min(G/45,1)
3. **Candidate rejection**: Too many invented candidates were vetoed by governance
   - Fix: Over-generate (mutation+synthesis) so filter still leaves diversity
4. **H1000 collapse**: Short rollout (depth 4-8) couldn't detect cumulative E depletion
   - Fix: Drift estimator as cheap long-horizon surrogate

### Why governance-execution separation matters
- Passing governance thresholds (growth_cap, exploration_floor) to engine = violation
- Engine becomes dependent on governance internals → architectural invariant broken
- The 0.55 score required this violation; the 0.50 score does not
- Monograph: "Engine has no independent legitimacy without upstream clearance"

---

## 7. Configuration Defaults

```python
# config/defaults.py
OmegaFullConfig(
    candidate_count=14,
    rollout_depth=4,        # Wolf: 8
    rollout_repeats=3,      # Wolf: 5
    counterfactual_branches=0,  # Disabled for speed in smoke
    lambda_drift=1.0,       # Long-horizon drift penalty
    normal_drift_multiplier=1.25,
    failure_memory_size=64,
    failure_penalty=0.15,
    fragility_prior=0.5,
)
```

Run commands:
```bash
cd nrmo_omega_full
python -m cli.main --mode smoke    # 1,000 episodes (5 worlds × 10 strats × 20 runs)
python drift_sweep.py              # λ_drift optimization
```

---

## 8. Remaining Weaknesses

1. **Vulnerable world**: 5% survival (all strategies struggle here)
2. **FastExpansionRace**: 35% vs Risk-Adj 50% (zero-noise heuristic advantage)
3. **Score 0.75 not reached**: Smoke budget limits statistical power
4. **Full-scale validation pending**: Need 500+ runs/cell, rollouts=16+
5. **Passive ruin 3%**: Not zero, room for improvement
6. **Empirical basis thin**: Synthetic testbed only, no human deployment

---

## 9. Next Steps (Prioritized)

1. **Full-scale validation**: 500+ runs/cell with full engine settings
2. **Vulnerable world fix**: Needs structural approach (world transition model may be too harsh)
3. **FastExpansionRace**: Better rivalry detection in candidate invention
4. **Bayesian parameter tuning**: Systematic optimization of scoring weights
5. **Cox proportional hazard analysis**: Survival statistics
6. **Multi-agent interaction**: Trade/conflict/alliance between civilizations
7. **30-civilization casebook**: Narrative generation for each profile
8. **Human-in-the-loop experiments**: Validate framework with real decisions

---

## 10. Files That Must Not Be Changed

- `governance/nrmo_core.py` — NRMO veto logic
- `governance/tuning_layer.py` — MetaController, adaptive tuning
- `core/ruin.py` — Ruin boundary definition
- `core/state.py` — State transition rules (world physics)
- `core/worlds.py` — World parameter generation

These are governance / world rules. Engine changes go in `engine/omega_full.py` and `strategies/strategies.py` only.

---

## 11. Key Phrases for Future Sessions

- "Adaptive NRMOvNext + StrongEngine Ω Full" = the default stack
- "governance-execution separation" = the invariant that must not be broken
- "Engine does NOT evaluate RUIN" = ruin is NRMO boundary, not scoring penalty
- "λ_drift = 1.0" = long-horizon drift control parameter
- "score 0.50 (constitutional)" vs "score 0.55 (violation)" = the honest comparison
- "Wolf Pursuit" = aggressive search in favorable states
- "Edge Survival Guard" = floor protection in fragile states

---

## 12. Document Inventory

| File | Description |
|------|-------------|
| `NRMO_StrongEngine_OmegaFull_v5.zip` | Complete code + results + specs |
| `NRMO_Integrated_Spec_v2.pdf` | 15-page integrated specification (all original content + engine revision) |
| `NRMO_Integrated_Spec_v2.tex` | LaTeX source |
| `design_spec.pdf` | v5.0 engine-focused design document |
| `drift_lambda_sweep.csv` | λ_drift optimization results |
| `results_smoke/` | All CSVs and PNGs from smoke validation |
| `SEPARATION.md` | Governance-execution boundary documentation |
| `SESSION_HANDOFF.md` | This file |

---

*Session conducted March 17, 2026. All results are smoke-scale (20 runs/cell). Full-scale validation is the primary next action.*
