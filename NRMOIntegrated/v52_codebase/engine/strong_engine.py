"""
engine/strong_engine.py — Baseline StrongEngine
=================================================
Execution layer: candidate generation + MC rollout + baseline scoring.
INVARIANT: operates only on NRMO-admissible candidates.
SOURCE: monograph baseline engine specification.
"""
from __future__ import annotations
import numpy as np
from typing import List
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.state import CivState, transition, productivity_instant, SimConfig
from core.ruin import is_ruin_state
from config.defaults import BaseEngineConfig

MIN_COMP = 0.05

TEMPLATES = {
    "balanced":            np.array([0.27,0.25,0.25,0.23]),
    "high_growth":         np.array([0.48,0.18,0.18,0.16]),
    "safety_heavy":        np.array([0.10,0.48,0.22,0.20]),
    "exploration_heavy":   np.array([0.10,0.14,0.52,0.24]),
    "recovery":            np.array([0.08,0.42,0.18,0.32]),
    "governance_repair":   np.array([0.08,0.18,0.18,0.56]),
    "expansion_race":      np.array([0.44,0.22,0.18,0.16]),
    "stagnation_recovery": np.array([0.16,0.10,0.50,0.24]),
}

def norm_action(a:np.ndarray)->np.ndarray:
    a=np.clip(a, MIN_COMP, None); return a/a.sum()

def generate_base_candidates(s:CivState, rng:np.random.Generator, n:int=12)->List[np.ndarray]:
    cands=[norm_action(t.copy()) for t in TEMPLATES.values()]
    tpls=list(TEMPLATES.values())
    while len(cands)<n:
        b=tpls[rng.integers(len(tpls))]
        cands.append(norm_action(b+rng.normal(0,0.06,4)))
    return cands[:n]

def baseline_rollout_score(s0:CivState, action:np.ndarray, wp:dict,
                           rng:np.random.Generator, ec:BaseEngineConfig,
                           cfg:SimConfig)->float:
    """Single MC rollout with baseline scoring."""
    default=norm_action(np.array([0.24,0.26,0.26,0.24]))
    s=s0.copy()
    s=transition(s,action,wp,rng,cfg)
    if is_ruin_state(s): return -100.0
    for _ in range(ec.rollout_depth-1):
        s=transition(s,default,wp,rng,cfg)
        if is_ruin_state(s): return -50.0
    prod=productivity_instant(s,action)
    return (ec.productivity_weight*prod + ec.optionality_weight*(s.O/130)
            + ec.governance_weight*(s.G/130) + ec.environment_weight*(s.E/130)
            - ec.exposure_penalty*(s.X/130))

def baseline_select(admissible:List[np.ndarray], s:CivState, wp:dict,
                    rng:np.random.Generator, ec:BaseEngineConfig=BaseEngineConfig(),
                    cfg:SimConfig=SimConfig())->np.ndarray:
    if not admissible: return norm_action(np.array([0.05,0.50,0.22,0.23]))
    best_a=admissible[0]; best_sc=-1e9
    for c in admissible:
        total=sum(baseline_rollout_score(s,c,wp,rng,ec,cfg) for _ in range(ec.rollout_repeats))
        avg=total/ec.rollout_repeats
        if avg>best_sc: best_sc=avg; best_a=c
    return best_a

def greedy_score(a:np.ndarray, s:CivState)->float:
    """One-step heuristic score for non-engine strategies."""
    g=a[0]; prod=g*(s.R+s.K)*0.01
    return prod+0.45*(s.O/130+a[2]*0.4)+0.15*(s.G/130+a[3]*0.3)+0.10*(s.E/130+a[1]*0.2)-0.40*(s.X/130+g*0.25)
