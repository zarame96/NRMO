# NRMO v8.4.1 FROZEN BASELINE

**Status**: FROZEN as controlled minimal guard baseline  
**Date**: 2026-05-23  
**Classification**: Safety baseline, NOT final NRMO v8

---

## 1. Conceptual Baselines

### v8.4.1-HG (True Minimal Safety Baseline)
```
V71Engine (with rng injection)
  + EmergencyResourceGuard
  + ActionIntensityThrottle
  + Revalidation (Emergency-based)
  + CumulativeRiskTracker
```

Files:
- `core/engines.py` (V71Engine with rng)
- `core/emergency_guards.py` (EG + Throttle)
- `core/cumulative_risk_tracker.py`
- `core/veto_classification.py`

Toggle in `V841Engine.__init__()`:
```python
engine = V841Engine(rng_manager=mgr, use_active_pattern=False)
```

### v8.4.1-AP (Future Aggressive-Engine Safety Harness)
```
v8.4.1-HG
  + ActivePatternProxy (threshold=0.35 fixed)
```

Toggle:
```python
engine = V841Engine(rng_manager=mgr, use_active_pattern=True)
```

---

## 2. Frozen File Inventory

| File | Purpose | Frozen Hash |
|---|---|---|
| `core/engines.py` | V71Engine with rng | (do not modify) |
| `core/emergency_guards.py` | EG + Throttle + unit tests | (do not modify) |
| `core/cumulative_risk_tracker.py` | Cumulative breach detector | (do not modify) |
| `core/active_pattern_proxy.py` | AP (threshold=0.35 fixed) | (do not modify) |
| `core/veto_classification.py` | NRMO Core veto types | (do not modify) |
| `core/v841_engine.py` | V841Engine integration | (do not modify) |
| `validation/v841_full_benchmark.py` | n=200 benchmark + aggressive test | (do not modify) |
| `results/v841_full_results.json` | Frozen result data | (do not modify) |

---

## 3. Honest Evaluation (per handoff doc § 2)

### Accepted findings
- v8.4.1 shows statistically significant improvement over v7.1 in **mild/moderate/severe** chaos (Wilcoxon p<0.001, paired diff +2.21 to +3.95)
- v8.4.1 remains in same performance band as v7.1 in **extreme/total** chaos
- Aggressive synthetic crash mitigated: time_to_ruin extended by +10-14 steps
- Main improvement source: **EmergencyResourceGuard + ActionIntensityThrottle** (hard guard)

### Claims NOT made
- v8.4.1 does NOT fully surpass v7.1 (extreme/total are equivalent only)
- v8.4.1 does NOT prove non-ruin (100% ruin rate still observed in long-run)
- ActivePattern is NOT the primary improvement source (pure effect ≈ 0 on v7.1 base)
- StrongEngineΩfull is NOT validated
- AggressiveEngine is NOT validated as independent engine

### Audit acceptance criteria (handoff doc § 3)
1. ✅ Deterministic RNG in V71Engine, V841Engine
2. ✅ EmergencyResourceGuard implemented
3. ✅ ActionIntensityThrottle implemented
4. ✅ R-critical hard rules pass unit tests (14/14)
5. ✅ R-critical B/C actions prohibited
6. ✅ ActivePattern ON/OFF ablation performed
7. ✅ Revalidation implemented
8. ✅ CumulativeRiskTracker integrated
9. ✅ Aggressive synthetic crash mitigated (+12.2 step avg)

### Remaining limitations (handoff doc § 3)
1. Ruin rate still 100% in long-run settings
2. Extreme/total chaos not yet significantly improved
3. ActivePattern pure effect ≈ 0 on v7.1 baseline
4. v8.4.1 is NOT final architecture; it is frozen safety baseline

---

## 4. AggressiveEngine Definition (locked, per handoff doc § 6-8)

```
AggressiveEngine is NOT an independent engine.

It is an internal auxiliary submodule of StrongEngineΩfull.
Its role: bounded, reversible, condition-aware offensive candidate generation.

It has NO authority to:
  - decide final actions
  - override NRMO vetoes
  - modify ruin boundaries
  - expand risk budgets
  - bypass EmergencyResourceGuard, ActionIntensityThrottle, 
    Calibration, or NRMO Revalidation
```

StrongEngineΩfull internal structure (future, not yet implemented):
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

---

## 5. Next Step (locked, per handoff doc § 5)

```
v8.4.2 = v8.4.1 + MAPLayer only
```

Strictly isolated: PassivePattern, StrongEngineΩfull, Shinobi, or other modules
must NOT be added in the same step.

v8.4.2 acceptance criteria (handoff doc § 5):
1. Does not degrade v8.4.1 in mild/moderate/severe
2. Improves or stabilizes extreme/total
3. MAPLayer ON/OFF ablation shows measurable benefit
4. Deterministic RNG remains intact
5. Intervention traces remain explainable
6. No additional early-ruin mechanism appears
7. No uncontrolled candidate amplification occurs

If MAPLayer fails any criterion, it must NOT be retained in mainline.

---

## 6. Priority Order After v8.4.1 (locked)

1. ✅ Freeze and document v8.4.1 (this manifest)
2. → Add MAPLayer only as v8.4.2
3. Validate MAPLayer with ON/OFF ablation
4. Only after MAPLayer validation, rebuild StrongEngineΩfull
5. Integrate AggressiveEngine only as StrongEngineΩfull submodule
6. Test StrongEngineΩfull against frozen v8.4.1 baseline
