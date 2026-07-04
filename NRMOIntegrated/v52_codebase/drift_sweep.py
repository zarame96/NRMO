#!/usr/bin/env python3
"""
drift_sweep.py — λ_drift optimization sweep
Runs Ω Full vs RiskAdjusted at horizons 200/500/1000 for each λ_drift value.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import numpy as np, pandas as pd
from config.defaults import *
from core.worlds import list_world_families
from strategies.strategies import Adaptive_NRMOvNext_OmegaFull, RiskAdjustedUtility
from simulation.simulator import run_episode
from metrics.metrics import results_to_df

LAMBDA_VALUES = [0.8, 1.0, 1.2, 1.6]
HORIZONS = [200, 500, 1000]
RUNS_PER_CELL = 2  # per world per strategy per horizon
WORLDS = list_world_families()

def compute_score(df):
    surv = df["alive"].mean(); truin = df["true_ruin"].mean()
    pruin = df["passive_ruin"].mean(); opt = df["final_O"].mean()
    prod = df["cum_prod"].mean(); exp_x = df["final_X"].mean()
    return 1.0*surv - 0.70*truin - 0.40*pruin + 0.18*(opt/130) + 0.08*(prod/200) - 0.10*(exp_x/130)

def run_pair(lam, horizon, runs):
    """Run Ω Full (with λ_drift=lam) vs RiskAdj at given horizon."""
    cfg = SimConfig(horizon=horizon)
    ofc = OmegaFullConfig(candidate_count=14, rollout_depth=4, rollout_repeats=3,
                          counterfactual_branches=0, lambda_drift=lam)
    omega = Adaptive_NRMOvNext_OmegaFull(oc=ofc)
    ra = RiskAdjustedUtility()
    results = []
    for wn in WORLDS:
        for st in [omega, ra]:
            for r in range(runs):
                seed = 42 + hash(wn) % 9999 + hash(st.name) % 9999 + r
                results.append(run_episode(st, wn, r, seed, cfg))
    return results_to_df(results)

def main():
    t0 = time.time()
    records = []

    # Run RiskAdj once per horizon (it's identical across λ)
    ra_cache = {}
    print("Computing RiskAdj baselines...")
    for h in HORIZONS:
        cfg = SimConfig(horizon=h)
        ra = RiskAdjustedUtility()
        res = []
        for wn in WORLDS:
            for r in range(RUNS_PER_CELL):
                seed = 42 + hash(wn) % 9999 + hash("RiskAdjustedUtility") % 9999 + r
                res.append(run_episode(ra, wn, r, seed, cfg))
        df = results_to_df(res)
        ra_cache[h] = {"score": compute_score(df), "surv": df["alive"].mean(), "df": df}
        print(f"  H={h}: RA score={ra_cache[h]['score']:.3f} surv={ra_cache[h]['surv']:.0%}")

    print(f"\nSweeping λ_drift: {LAMBDA_VALUES}")
    for lam in LAMBDA_VALUES:
        rec = {"lambda_drift": lam}
        for h in HORIZONS:
            cfg = SimConfig(horizon=h)
            ofc = OmegaFullConfig(candidate_count=14, rollout_depth=4, rollout_repeats=2,
                                  counterfactual_branches=0, lambda_drift=lam)
            omega = Adaptive_NRMOvNext_OmegaFull(oc=ofc)
            res = []
            for wn in WORLDS:
                for r in range(RUNS_PER_CELL):
                    seed = 42 + hash(wn) % 9999 + hash("Adaptive_NRMOvNext_OmegaFull") % 9999 + r
                    res.append(run_episode(omega, wn, r, seed, cfg))
            df = results_to_df(res)
            sc = compute_score(df); sv = df["alive"].mean()
            rec[f"score_{h}"] = round(sc, 4)
            rec[f"survival_{h}"] = round(sv, 3)
            rec[f"riskadj_score_{h}"] = round(ra_cache[h]["score"], 4)
            rec[f"riskadj_survival_{h}"] = round(ra_cache[h]["surv"], 3)
            rec[f"delta_{h}"] = round(sc - ra_cache[h]["score"], 4)

            # Per-world survival at H1000
            if h == 1000:
                for wn in WORLDS:
                    wsub = df[(df["strategy"] == "Adaptive_NRMOvNext_OmegaFull") & (df["world"] == wn)]
                    rec[f"{wn.lower()}_surv_1000"] = round(wsub["alive"].mean(), 3) if not wsub.empty else 0.0

        records.append(rec)
        print(f"  λ={lam:.1f}  "
              f"H200={rec['score_200']:.3f}(Δ{rec['delta_200']:+.3f})  "
              f"H500={rec['score_500']:.3f}(Δ{rec['delta_500']:+.3f})  "
              f"H1000={rec['score_1000']:.3f}(Δ{rec['delta_1000']:+.3f})")

    # Save CSV
    pdf = pd.DataFrame(records)
    pdf.to_csv("drift_lambda_sweep.csv", index=False)
    print(f"\n→ drift_lambda_sweep.csv")

    # §8: Selection rule
    print("\n" + "="*74)
    print("λ_drift SELECTION")
    print("="*74)

    best_lam = None; best_obj = -1e9
    for _, row in pdf.iterrows():
        lam = row["lambda_drift"]
        A = row["delta_200"]; B = row["delta_500"]; C = row["delta_1000"]
        # Reject if H1000 materially inferior
        if C < -0.05:
            print(f"  λ={lam:.1f} REJECTED: H1000 delta={C:+.3f} < -0.05")
            continue
        if row["survival_1000"] < ra_cache[1000]["surv"] - 0.10:
            print(f"  λ={lam:.1f} REJECTED: H1000 survival {row['survival_1000']:.0%} << RA {ra_cache[1000]['surv']:.0%}")
            continue
        obj = 0.30*A + 0.30*B + 0.40*C
        status = "✓"
        if C >= 0: status = "★"
        print(f"  λ={lam:.1f} {status} obj={obj:+.4f}  H200 Δ{A:+.3f}  H500 Δ{B:+.3f}  H1000 Δ{C:+.3f}")
        if obj > best_obj:
            best_obj = obj; best_lam = lam

    print(f"\n  ★ BEST λ_drift = {best_lam}")
    br = pdf[pdf["lambda_drift"]==best_lam].iloc[0]
    print(f"    H200:  Ω={br['score_200']:.3f} vs RA={br['riskadj_score_200']:.3f}  {'WIN' if br['delta_200']>0 else 'LOSS'}")
    print(f"    H500:  Ω={br['score_500']:.3f} vs RA={br['riskadj_score_500']:.3f}  {'WIN' if br['delta_500']>0 else 'LOSS'}")
    print(f"    H1000: Ω={br['score_1000']:.3f} vs RA={br['riskadj_score_1000']:.3f}  {'WIN' if br['delta_1000']>=0 else 'NON-INF' if br['delta_1000']>-0.03 else 'LOSS'}")
    print(f"\n    Wall: {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
