# NRMO v8.4.1 (FROZEN) + v8.4.2 (MAPLayer Trial) — Honest Report

**Date**: 2026-05-23  
**Status**: v8.4.1 frozen as safety baseline; v8.4.2 MAPLayer trial → NOT retained in mainline  
**Audit reference**: NRMO_v8_4_1_to_v8_4_2_Claude_handoff.md

---

## 1. Executive Summary

```
v8.4.1: FROZEN as controlled minimal guard baseline.
  Main improvement source = EmergencyResourceGuard + ActionIntensityThrottle.
  ActivePattern pure effect ≈ 0 on v7.1 baseline.
  Statistically significant improvement over v7.1 in mild/moderate/severe (p<0.001).
  Same performance band as v7.1 in extreme/total.

v8.4.2 = v8.4.1 + MAPLayer only:
  Acceptance criteria 5/7 PASS (1, 4, 5, 6, 7).
  Acceptance criteria 2/7 FAIL: criteria 2 and 3.
    - extreme/total: no improvement, no variance reduction (std delta -0.01)
    - MAPLayer ON/OFF ablation: pure effect = 0.00 across all chaos levels
  Per handoff doc § 5: "If MAPLayer does not improve extreme/total or 
                         variance, it should not be retained in the mainline."
  → MAPLayer NOT retained in mainline (in adaptive-tightening form).

AggressiveEngine:
  Definition LOCKED as StrongEngineΩfull internal auxiliary submodule.
  No final-action authority. Must emit safe_variant + reversible_variant + 
  stop_conditions. Must pass Guard / Throttle / Calibration / Revalidation.
```

---

## 2. v8.4.1 Frozen Baseline

### 2.1 Architecture

```
NRMO v8.4.1 =
  V71Engine (with deterministic RNG injection)
    + EmergencyResourceGuard      ← hard rule (R/E/X thresholds)
    + ActionIntensityThrottle      ← rolling drawdown + consecutive limit
    + ActivePatternProxy           ← threshold=0.35, retained as safety harness
    + Revalidation                  ← all proposed_action re-checked by EG
    + CumulativeRiskTracker        ← projected breach detection
```

### 2.2 Conceptual Baselines

| Variant | Components | Purpose |
|---|---|---|
| v8.4.1-HG | V71+rng + EG + Throttle + Reval + CumRisk | True minimal safety baseline |
| v8.4.1-AP | v8.4.1-HG + ActivePattern | Future aggressive-engine safety harness |

### 2.3 Audit Compliance (handoff doc § 3)

| # | Criterion | Status |
|---|---|---|
| 1 | Deterministic RNG | ✅ V71Engine + V841Engine rng injection |
| 2 | EmergencyResourceGuard | ✅ implemented |
| 3 | ActionIntensityThrottle | ✅ implemented |
| 4 | R-critical hard rules unit-tested | ✅ 14/14 PASS |
| 5 | R-critical B/C actions prohibited | ✅ hard rule |
| 6 | ActivePattern ON/OFF ablation | ✅ performed |
| 7 | Revalidation | ✅ implemented |
| 8 | CumulativeRiskTracker integrated | ✅ integrated |
| 9 | Aggressive synthetic crash mitigated | ✅ +12.2 step avg |

### 2.4 Main Benchmark Results (n=200, seed 100-299, horizon 200)

| Level | v7.1 | v8.4.1 | paired Δ | Wilcoxon p | AP pure effect |
|---|---:|---:|---:|---:|---:|
| mild | 12.28 | 16.38 | +3.95 | **<0.0001** ✓ | +0.00 |
| moderate | 11.42 | 14.95 | +3.48 | **<0.0001** ✓ | +0.00 |
| severe | 9.96 | 12.13 | +2.21 | **0.0008** ✓ | +0.00 |
| extreme | 7.05 | 5.83 | +0.67 | 0.1425 | +0.00 |
| total | 3.49 | 4.04 | +0.04 | 0.3698 | +0.00 |

**Honest interpretation**:
- mild/moderate/severe: statistically significant improvement
- extreme/total: same performance band (not significantly different)
- ActivePattern pure effect ≈ 0 (v7.1 base does not produce aggressive C-actions)
- Improvement source: hard guard (EmergencyResourceGuard + Throttle)

### 2.5 Aggressive Synthetic Test (v8.3 crash 再現)

| Level | Aggressive baseline | + Guard stack | Time-to-ruin gain |
|---|---:|---:|---:|
| mild | 2.56 (6 step) | 8.17 (20 step) | **+14.0 step** |
| moderate | 2.17 (6 step) | 5.92 (16 step) | **+10.5 step** |

```
Across 60 runs:
  EmergencyResourceGuard triggered: 645
  ActionIntensityThrottle triggered: 189
  ActivePattern intervened: 10
```

ActivePattern intervenes 10/60 runs in aggressive setting — validates retention as safety harness for future aggressive engines.

---

## 3. v8.4.2 MAPLayer Experiment

### 3.1 Design

```
v8.4.2 = v8.4.1 + MAPLayer only.

MAPLayer integration: adaptive guard tightening
  - near_ruin history >= 3 → r_warning ↑ (25 → 30)
  - obs_noise > 0.30 → consecutive_large_limit ↓ (2 → 1)
  - obs_noise > 0.50 → r_drawdown_threshold ↓ (0.20 → 0.15)
  - L2 state trends (R declining or X rising) → r_warning ↑

MAPLayer does NOT generate candidates or directly select actions.
```

### 3.2 Results (n=200, seed 300-499, 4-way comparison)

| Level | v7.1 | v8.4.1 | v8.4.2 ML-ON | v8.4.2 ML-OFF | MAPLayer pure effect |
|---|---:|---:|---:|---:|---:|
| severe | 10.38 | 12.15 | 12.15 | 12.15 | **+0.00** |
| extreme | 7.42 | 6.43 | 6.43 | 6.43 | **+0.00** |
| total | 4.78 | 5.03 | 5.03 | 5.03 | -0.01 |

```
adaptive_tightening fires: severe 21.6/run, extreme 16.9/run, total 13.4/run
near_ruin events observed: severe 8.9/run, extreme 6.2/run, total 3.9/run

MAPLayer signal is active. But its action on guard thresholds 
produces NO measurable change in outcomes.
```

### 3.3 Acceptance Criteria Result

| # | Criterion | Status |
|---|---|---|
| 1 | Does not degrade v8.4.1 in mild/moderate/severe | ✅ (Δ=0) |
| 2 | Improves or stabilizes extreme/total | ❌ (Δ=0, std delta=-0.01) |
| 3 | MAPLayer ON/OFF ablation shows measurable benefit | ❌ (pure effect=0) |
| 4 | Deterministic RNG remains intact | ✅ |
| 5 | Intervention traces remain explainable | ✅ |
| 6 | No additional early-ruin mechanism | ✅ |
| 7 | No uncontrolled candidate amplification | ✅ |

**5/7 PASS. Criteria 2 and 3 FAIL.**

### 3.4 Honest Decision

Per handoff doc § 5: *"If MAPLayer does not improve extreme/total or variance, it should not be retained in the mainline."*

→ **MAPLayer (in adaptive_guard_tightening form) is NOT retained in mainline.**

### 3.5 Root Cause Analysis

```
Why MAPLayer adaptive_tightening produced no effect:

  Base guard config in v8.4.1 (r_emergency=10, r_critical=15, r_warning=25)
  is already sufficiently strict for the chaos levels tested.
  
  Adaptive tightening (r_warning 25 → 28 → 33) does not change guard 
  firing timing because the same trajectory hits the same thresholds 
  in the same order.
  
  near_ruin events are detected (severe 8.9/run), but the response 
  (further tightening) does not alter outcomes when EG already fires.
  
  This does NOT prove MAPLayer is useless. It proves that the 
  adaptive_tightening pathway is the wrong way to use MAPLayer.
```

### 3.6 Possible Future Uses of MAPLayer (NOT implemented yet)

```
A) Candidate predictor for AggressiveEngine
   - L2 trend signal → predict whether opportunity window persists
   - feed into AggressiveEngine's required_conditions

B) Observation-noise-aware Knightian
   - L3 episodic memory → identify rare regime shifts
   - augment NRMO Core's veto classification (uncertainty_driven flag)

C) Stop-condition trigger source
   - L2 trends → real-time stop_conditions for AggressiveEngine candidates
   
These are out of scope for v8.4.x; explore only when StrongEngineΩfull is rebuilt.
```

---

## 4. AggressiveEngine Definition (LOCKED, per handoff doc § 6-15)

### 4.1 Core Definition

```
AggressiveEngine is NOT an independent engine.

It is an internal auxiliary submodule of StrongEngineΩfull.

Role: Generate bounded, reversible, condition-aware offensive candidates 
that may expand future reachable states under NRMO constraints.

Authority:
  ❌ Decide final actions
  ❌ Override NRMO vetoes
  ❌ Modify ruin boundaries
  ❌ Expand risk budgets
  ❌ Bypass EmergencyResourceGuard, Throttle, Calibration, Revalidation

  ✅ Generate offensive candidates with full schema
  ✅ Propose Wolf Pursuit / Small Reversible / Anti-Stagnation / Momentum
```

### 4.2 StrongEngineΩfull Internal Structure (future, not yet implemented)

```
StrongEngineΩfull
  ├─ DefensiveCandidateModule
  ├─ RecoveryCandidateModule
  ├─ ExplorationCandidateModule
  ├─ MutationPathway
  ├─ SynthesisPathway
  ├─ InventionPathway
  ├─ AggressiveEngine Submodule
  │    ├─ Wolf Pursuit Mode
  │    ├─ Small Reversible Attack Mode
  │    ├─ Anti-Stagnation Attack Mode
  │    └─ Momentum Exploitation Mode
  └─ CandidateMerger
```

### 4.3 Required Output Schema per AggressiveEngine candidate

```json
{
  "module": "AggressiveEngine",
  "mode": "small_reversible_attack",
  "attack_candidate": "invest/B",
  "safe_variant": "invest/A",
  "minimum_reversible_variant": "explore/A",
  "expected_upside": 0.72,
  "estimated_downside": 0.24,
  "reversibility": 0.81,
  "required_conditions": {
    "R_min": 40, "E_min": 0.45, "X_max": 0.60,
    "O_confidence_min": 0.65,
    "no_recent_drawdown": true, "no_true_veto": true
  },
  "stop_conditions": {
    "R_below": 25, "X_above": 0.75,
    "two_failed_attempts": true,
    "opportunity_signal_decay": true
  },
  "reason": "..."
}
```

### 4.4 Activation Conditions

| Condition | Threshold |
|---|---|
| R | >= 40 |
| E | >= 0.45 |
| X | <= 0.60 |
| O_signal_confidence | >= 0.65 |
| recent_resource_drawdown | == false |
| true_veto | == false |
| small_reversible_variant_available | == true |

### 4.5 Suppression Conditions

| Condition | Action |
|---|---|
| R <= 25 | C action candidate generation prohibited |
| R <= 15 | B/C action candidate generation prohibited |
| R <= 10 | AggressiveEngine inactive, recover/A prioritized |
| X >= 0.75 | C action prohibited |
| X >= 0.90 | true_veto candidate, all aggressive generation stopped |
| recent_R_drawdown >= threshold | next action max size A |
| consecutive_large_actions >= 2 | cooldown mode |

---

## 5. Pipeline Diagram (Locked)

### 5.1 Current v8.4.1 Pipeline

```
v7.1 base
  ↓
EmergencyResourceGuard
  ↓
ActionIntensityThrottle
  ↓
ActivePattern (proposal only)
  ↓
Revalidation (Emergency Guard re-check)
  ↓
Final Action
```

### 5.2 Future StrongEngineΩfull Pipeline (with AggressiveEngine submodule)

```
NRMO Core
  ↓
Allowed Action Set
  ↓
StrongEngineΩfull
  ├─ Defensive / Recovery / Exploration / Mutation / Synthesis / Invention
  └─ AggressiveEngine Submodule (Wolf / SmallReversible / AntiStagnation / Momentum)
  ↓
CandidateMerger
  ↓
EmergencyResourceGuard
  ↓
ActionIntensityThrottle
  ↓
Calibration
  ↓
NRMO Revalidation
  ↓
Final Action
```

---

## 6. Next Steps (Locked Priority Order, handoff doc § 18)

```
1. ✅ Freeze and document v8.4.1                    (this report)
2. ✅ Add MAPLayer only as v8.4.2                   (this report)
3. ✅ Validate MAPLayer with ON/OFF ablation         (this report — failed criteria 2,3)
4. → Decision: MAPLayer not retained in mainline    (this report)
5. → Rebuild StrongEngineΩfull (full structure per § 4.2)
6. → Integrate AggressiveEngine as StrongEngineΩfull submodule
7. → Test against frozen v8.4.1 baseline
```

---

## 7. Conclusion

```
v8.4.1 is the first stable baseline since v8.3 aggressive overextension failure.
It is FROZEN. Modifications must use new version numbers.

v8.4.2 = v8.4.1 + MAPLayer (adaptive_tightening) — does not work.
MAPLayer is retained in code repository but NOT in active pipeline.

Next: rebuild StrongEngineΩfull with AggressiveEngine submodule integration.
AggressiveEngine submodule MUST follow lock specification:
  - bounded, reversible, condition-aware candidates only
  - no final-action authority
  - all outputs pass Guard / Throttle / Calibration / Revalidation
```
