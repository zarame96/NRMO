"""
simulation/simulator.py — Episode runner with ruin attribution
"""
from __future__ import annotations
import numpy as np, time
from dataclasses import dataclass
from typing import List, Callable
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.state import CivState, transition
from core.ruin import check_true_ruin, update_passive_ruin, detect_overshoot, OVERSHOOT_COLLAPSE, ALIVE
from core.worlds import draw_world
from config.defaults import InitialState, RuinThresholds, SimConfig

@dataclass
class EpisodeResult:
    world_name:str; strategy_name:str; run_id:int; seed:int
    lifespan:int; alive:bool; true_ruin:bool; passive_ruin:bool
    ruin_type:str; ruin_step:int
    final_R:float; final_E:float; final_G:float
    final_O:float; final_K:float; final_X:float
    cum_prod:float; peak_prod:float; peak_X:float; mean_prod:float
    selected_profile:str; profile_switch_count:int

def run_episode(strategy, world_name, run_id, seed,
                sim_cfg=SimConfig(), init=InitialState(),
                ruin_th=RuinThresholds())->EpisodeResult:
    rng=np.random.default_rng(seed)
    w=draw_world(world_name,rng); wp=w.as_dict()
    s=CivState.from_config(init)
    for step in range(sim_cfg.horizon):
        a=strategy(s,wp,rng,step,world_name=world_name)
        s=transition(s,a,wp,rng,sim_cfg)
        rc=check_true_ruin(s,ruin_th)
        if rc:
            if detect_overshoot(s): rc=OVERSHOOT_COLLAPSE
            s.alive=False; s.true_ruin=True; s.ruin_type=rc; s.ruin_step=s.step; break
        pr=update_passive_ruin(s,ruin_th)
        if pr and not s.passive_ruin:
            s.passive_ruin=True; s.ruin_type=pr; s.ruin_step=s.step
    mp=s.cum_prod/max(s.step,1)
    return EpisodeResult(world_name,getattr(strategy,"name","?"),run_id,seed,
        s.step,s.alive,s.true_ruin,s.passive_ruin,s.ruin_type,s.ruin_step,
        s.R,s.E,s.G,s.O,s.K,s.X,s.cum_prod,s.peak_prod,s.peak_X,mp,
        s.mode,s.profile_switch_count)

def run_experiment(strategies, worlds, runs, sim_cfg=SimConfig(),
                   base_seed=42, verbose=True)->List[EpisodeResult]:
    results=[]; total=len(worlds)*len(strategies)*runs; done=0; t0=time.time()
    for wi,wn in enumerate(worlds):
        for si,st in enumerate(strategies):
            sn=getattr(st,"name",f"s{si}")
            for r in range(runs):
                seed=base_seed+wi*100000+si*10000+r
                results.append(run_episode(st,wn,r,seed,sim_cfg))
                done+=1
            if verbose:
                el=time.time()-t0; pct=done/total*100; eps=done/el if el>0 else 0
                print(f"  [{pct:5.1f}%] {wn:20s} × {sn:35s} ({runs}r) {eps:.0f}ep/s",flush=True)
    if verbose: el=time.time()-t0; print(f"\nDone: {total} episodes in {el:.1f}s ({total/el:.0f}ep/s)")
    return results
