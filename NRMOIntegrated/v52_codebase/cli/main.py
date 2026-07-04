#!/usr/bin/env python3
"""
cli/main.py — NRMO-vNext + StrongEngine Omega Full Simulation
===============================================================
Usage:
    python -m cli.main --mode smoke
    python -m cli.main --mode full
    python -m cli.main --mode sweep --sweep-world Normal
"""
from __future__ import annotations
import argparse, time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np, pandas as pd
from pathlib import Path
from config.defaults import SimConfig, BaseEngineConfig, OmegaFullConfig, ScoreWeights
from core.worlds import list_world_families
from strategies.strategies import build_all_strategies
from simulation.simulator import run_experiment
from metrics.metrics import results_to_df, aggregate_world, aggregate_overall, add_scores, export_all
from metrics.plots import generate_all_plots

def parse_args():
    p=argparse.ArgumentParser(description="NRMO + Omega Full Civilisation Simulation")
    p.add_argument("--mode",choices=["smoke","full","sweep"],default="smoke")
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--horizon",type=int,default=200)
    p.add_argument("--base-rollouts",type=int,default=None)
    p.add_argument("--omega-rollouts",type=int,default=None)
    p.add_argument("--output-dir",type=str,default=None)
    p.add_argument("--sweep-world",type=str,default="Normal")
    return p.parse_args()

def main():
    args=parse_args(); smoke=args.mode=="smoke"
    runs=30 if smoke else 500
    scfg=SimConfig(horizon=args.horizon,seed=args.seed)
    bec=BaseEngineConfig(
        candidate_count=8 if smoke else 12,
        rollout_depth=3 if smoke else 5,
        rollout_repeats=args.base_rollouts or (3 if smoke else 6),
    )
    # Omega Full: stronger settings — this is the DEFAULT STACK
    # SOURCE: monograph specifies Omega Full as the completed execution layer
    ofc=OmegaFullConfig(
        candidate_count=12 if smoke else 14,
        rollout_depth=4 if smoke else 6,
        rollout_repeats=args.omega_rollouts or (4 if smoke else 6),
        counterfactual_branches=1 if smoke else 2,
    )
    od=args.output_dir or f"results_{'smoke' if smoke else 'full'}"
    Path(od).mkdir(parents=True,exist_ok=True)
    ws=list_world_families()
    ss=build_all_strategies(base_ec=bec,omega_oc=ofc)
    total=len(ws)*len(ss)*runs
    print("="*74)
    print("NRMO-vNext + StrongEngine Omega Full — Civilisation Simulation")
    print("="*74)
    print(f"Mode: {args.mode}  Worlds: {ws}")
    print(f"Strategies ({len(ss)}): {[s.name for s in ss]}")
    print(f"Runs/cell: {runs}  Horizon: {scfg.horizon}  Total: {total}")
    print(f"Base engine: depth={bec.rollout_depth} cands={bec.candidate_count} rolls={bec.rollout_repeats}")
    print(f"Omega Full:  depth={ofc.rollout_depth} cands={ofc.candidate_count} rolls={ofc.rollout_repeats} cf={ofc.counterfactual_branches}")
    print(f"Output: {od}/")
    print("="*74,"\n")
    t0=time.time()
    results=run_experiment(ss,ws,runs,scfg,args.seed)
    wall=time.time()-t0
    print("\nComputing metrics...")
    raw=results_to_df(results)
    wa=add_scores(aggregate_world(raw)); ov=add_scores(aggregate_overall(raw))
    export_all(raw,wa,ov,od)
    generate_all_plots(raw,wa,ov,od)
    print("\n"+"="*74)
    print("OVERALL RANKING")
    print("="*74)
    cols=["strategy","survival_rate","true_ruin_rate","passive_ruin_rate","mean_lifespan","mean_final_O","mean_final_X","score"]
    s=ov[cols].sort_values("score",ascending=False).copy()
    s.columns=["Strategy","Surv%","TRuin%","PRuin%","Life","Opt","Exp","Score"]
    for c in ["Surv%","TRuin%","PRuin%"]: s[c]=(s[c]*100).round(1)
    for c in ["Life","Opt","Exp","Score"]: s[c]=s[c].round(2)
    print(s.to_string(index=False))
    print(f"\nWall: {wall:.1f}s  Results: {od}/")

if __name__=="__main__": main()
