# NRMO-vNext + StrongEngine Ω Full — Civilisation Simulation

## Status

| Item | Status |
|------|--------|
| Omega Full architecture | **Documented and implemented** (SOURCE: monograph) |
| 8 Omega Full modules | **All implemented** |
| Smoke validation | **Complete** (1,500 episodes) |
| Full-scale empirical evaluation | **Incomplete** (computational bottleneck) |

**Omega Full exists as a documented final execution-layer architecture.**
**Full-scale empirical superiority is NOT claimed.**

## Architecture

```
World Model
    ↓
Observation
    ↓
Context / Norn Layer
    ↓
Meta-Controller (5 Modes)         ← governance
    ↓
Adaptive Tuning Layer             ← governance
    ↓
NRMO Core (VETO ONLY)            ← governance
    ↓
Admissible Action Set
    ↓
StrongEngine Ω Full               ← execution
    ↓
Portfolio Action
    ↓
State Transition
```

**INVARIANT**: NRMO defines boundaries. Omega Full searches inside them. Never the reverse.

## Omega Full — 8 Modules (SOURCE: monograph)

| # | Module | Role |
|---|--------|------|
| 1 | Strategic Regime Layer | 8 regimes: balanced/recovery/expansion/exploration/eco/governance/stagnation/race |
| 2 | Tactical Candidate Layer | 10 templates with regime-priority ordering |
| 3 | Candidate Invention | 5 pathways: template/perturbation/blend/state-conditioned/world-conditioned |
| 4 | Fragility Detection | 6-factor world fragility score |
| 5 | Failure Memory | Past ruin pattern recording + similarity penalty |
| 6 | Branch Ruin Attribution | Dominant rollout failure pathway classification |
| 7 | Risk-Adjusted Scoring | 10-factor formula with 0.65/0.35 avg/downside blend |
| 8 | Portfolio Planner | A = w1·main + w2·hedge + w3·probe |

## Quick Start

```bash
cd nrmo

# Smoke test: 5 worlds × 10 strategies × 30 runs = 1,500 episodes
python -m cli.main --mode smoke

# Full experiment: 5 worlds × 10 strategies × 500 runs = 25,000 episodes
python -m cli.main --mode full

# Custom engine params
python -m cli.main --mode smoke --omega-rollouts 6 --base-rollouts 5
```

## 10 Comparison Strategies

| # | Strategy | Veto | Engine | Tuning | Meta |
|---|----------|------|--------|--------|------|
| 1 | ExpectedValueMax | — | — | — | — |
| 2 | RiskAdjustedUtility | — | — | — | — |
| 3 | NRMO_Original | Original | Greedy | — | — |
| 4 | NRMO_vNext | vNext | Greedy | Profile | — |
| 5 | UltraConservative | — | — | — | — |
| 6 | AlphaSearch | — | Baseline SE | — | — |
| 7 | NRMO_StrongEngine | Original | Baseline SE | — | — |
| 8 | NRMOvNext_StrongEngine | vNext | Baseline SE | Profile | — |
| 9 | Adaptive_NRMOvNext_SE | vNext | Baseline SE | Adaptive | 5-Mode |
| 10 | **Adaptive_NRMOvNext_OmegaFull** | vNext | **Ω Full** | Adaptive | 5-Mode |

## Repository Structure

```
nrmo/
├── config/defaults.py          # All parameters centralised
├── core/
│   ├── state.py                # S=(R,E,G,O,K,X), transition
│   ├── worlds.py               # 5 world families, per-run draw
│   └── ruin.py                 # Ruin taxonomy, 9 pathway labels
├── governance/
│   ├── nrmo_core.py            # VETO ONLY (original + vNext)
│   └── tuning_layer.py         # Adaptive tuning + meta-controller
├── engine/
│   ├── strong_engine.py        # Baseline StrongEngine
│   └── omega_full.py           # Ω Full (8 modules)
├── strategies/strategies.py    # 10 strategies
├── simulation/simulator.py     # Episode runner
├── metrics/
│   ├── metrics.py              # Aggregation + ruin analysis
│   └── plots.py                # 8 chart types
└── cli/main.py                 # Entry point
```

## Assumptions

Items marked ASSUMPTION are implementation choices where the monograph is silent:

1. **Transition coefficients** — Calibrated for balanced gameplay; exact values not specified in monograph
2. **Mean-reversion terms** — Added to prevent runaway collapse; strength is ASSUMPTION
3. **Shock target selection** — Weighted toward weakest dimension (ASSUMPTION)
4. **Irreversibility heuristic** — Derived from growth allocation + exposure level (ASSUMPTION)
5. **Counterfactual bad policy** — Uses aggressive growth template as pessimistic continuation (ASSUMPTION)
6. **Fragility score weights** — Proportional to drag/probability magnitudes (ASSUMPTION)
7. **Failure memory similarity threshold** — Set to 25.0 state-space distance (ASSUMPTION)

## TODO

1. Full-scale validation (500+ runs per cell with full engine settings)
2. Bayesian optimization for parameter tuning
3. Cox proportional hazard survival analysis
4. Multi-agent civilisation interaction (trade/conflict/alliance)
5. Additional state variables: Social Trust, Information Quality, Systemic Complexity
6. Human-in-the-loop decision experiments
7. 30-civilisation casebook narrative generation

## Dependencies

- Python 3.10+
- numpy, pandas, matplotlib
