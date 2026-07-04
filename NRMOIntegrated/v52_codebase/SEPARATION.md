# Governance–Execution Separation

## The Rule

NRMO is governance only. Engine is execution only.

This is not a suggestion. It is the architectural invariant.

## Where Governance Ends and Execution Begins

```
GOVERNANCE                           EXECUTION
─────────────────────────────────    ─────────────────────────────────
core/ruin.py                         engine/strong_engine.py
  check_true_ruin()                    generate_base_candidates()
  update_passive_ruin()                baseline_rollout_score()
  is_ruin_state()                      baseline_select()

governance/nrmo_core.py              engine/omega_full.py
  nrmo_veto()                          Module 1: select_regime()
  nrmo_vnext_veto()                    Module 2: TACTICAL_TEMPLATES
  construct_admissible_set()           Module 3: invent_candidates()
                                       Module 4: compute_fragility()
governance/tuning_layer.py             Module 5: FailureMemory
  MetaController.update()              Module 6: attribute_ruin_branch()
  adaptive_tuning()                    Module 7: risk_adjusted_score()
  HysteresisTracker                    Module 8: build_portfolio()
                                       OmegaFullEngine.select_action()
```

## Formal Contract

```
A_t = NRMO(X_t)        ← governance defines admissibility
a_t = Engine(A_t)       ← execution searches within admissibility
```

## Verified By Audit

The following checks pass on this codebase:

- [x] invent_candidates() has no governance parameters (growth_cap, exploration_floor, etc.)
- [x] strategies.py does not pass governance thresholds to engine
- [x] Flow order: invention → governance filter → engine scoring
- [x] omega_full.py delegates ruin checks to core.ruin.is_ruin_state()
- [x] nrmo_core.py contains no scoring functions
- [x] Mode determination is upstream of engine search

## What Engine May NOT Do

- Redefine ruin
- Redraw the admissibility boundary
- Override NRMO veto
- Score first, filter later
- Absorb governance logic into search logic
- Contain growth_cap, exploration_floor, or other governance parameters

## What Governance May NOT Do

- Rank candidates
- Score candidates
- Select final action
- Optimise
- Advise (governance issues YES/NO/HOLD only)
