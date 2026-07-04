"""
core/state.py — Civilisation state vector and transition dynamics
SOURCE: monograph canonical state model S=(R,E,G,O,K,X)
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.defaults import InitialState, SimConfig

@dataclass
class CivState:
    R:float; E:float; G:float; O:float; K:float; X:float
    step:int=0; alive:bool=True; true_ruin:bool=False; passive_ruin:bool=False
    ruin_type:str="alive"; ruin_step:int=-1
    low_O_streak:int=0; low_K_streak:int=0; compound_streak:int=0
    prev_O:float=54.0; prev_G:float=58.0; prev_K:float=52.0
    cum_prod:float=0.0; peak_prod:float=0.0; peak_X:float=0.0
    growth_accum:float=0.0
    mode:str="Normal"; profile_switch_count:int=0

    @classmethod
    def from_config(cls, c:InitialState)->"CivState":
        return cls(R=c.R,E=c.E,G=c.G,O=c.O,K=c.K,X=c.X,
                   prev_O=c.O,prev_G=c.G,prev_K=c.K)

    def copy(self)->"CivState":
        return CivState(R=self.R,E=self.E,G=self.G,O=self.O,K=self.K,X=self.X,
            step=self.step,alive=self.alive,true_ruin=self.true_ruin,
            passive_ruin=self.passive_ruin,ruin_type=self.ruin_type,ruin_step=self.ruin_step,
            low_O_streak=self.low_O_streak,low_K_streak=self.low_K_streak,
            compound_streak=self.compound_streak,
            prev_O=self.prev_O,prev_G=self.prev_G,prev_K=self.prev_K,
            cum_prod=self.cum_prod,peak_prod=self.peak_prod,peak_X=self.peak_X,
            growth_accum=self.growth_accum,mode=self.mode,
            profile_switch_count=self.profile_switch_count)

    def arr(self)->np.ndarray:
        return np.array([self.R,self.E,self.G,self.O,self.K,self.X])

def transition(s:CivState, action:np.ndarray, wp:dict,
               rng:np.random.Generator, cfg:SimConfig=SimConfig())->CivState:
    """Apply one civilisation step. ASSUMPTION: transition coefficients are
    calibrated for gameplay balance; monograph does not specify exact values."""
    g,sf,lr,di = action
    dR = g*(4.5+0.04*s.K) - wp["environmental_drag"]*s.R*0.18 \
         - g*s.R*0.006*(1+wp["rivalry_level"]) + 0.008*(60-s.R)
    dE = sf*4.2+di*1.4 - g*2.3*(1+wp["rivalry_level"]*0.5) + 0.006*(65-s.E)
    dG = di*4.8+sf*1.8 - wp["governance_drag"]*(1.2+g*1.5) \
         - g*wp["rivalry_level"]*0.5 + 0.005*(55-s.G)
    dO = lr*4.2+0.025*s.K+di*0.9 - (s.X/130)*1.6 \
         - wp["stagnation_drag"]*5.5 + 0.005*(50-s.O)
    dK = lr*4.5*max(0.5,wp["substitutability"]) - wp["stagnation_drag"]*2.2 \
         + 0.012*s.G*lr + 0.004*(50-s.K)
    dX = g*4.8*(1+wp["rivalry_level"]) - sf*5.2-di*1.3 - 0.04*s.X
    sh = np.zeros(6)
    if rng.random() < wp["shock_probability"]:
        mag = rng.exponential(wp["shock_scale"])
        vals = np.array([s.R,s.E,s.G,s.O,s.K])
        p = np.exp(-vals/30); p /= p.sum()
        t = rng.choice(5,p=p); sh[t] -= mag; sh[5] += mag*0.35
    if rng.random() < wp["tail_probability"]:
        tail = rng.exponential(wp["tail_scale"])
        tail *= max(0,1+wp["tail_model_misspecification"]*rng.standard_normal())
        buf = 0.4+0.6*(s.G/130)
        sh[0]-=tail*0.45/buf; sh[1]-=tail*0.35; sh[2]-=tail*0.25
        sh[3]-=tail*0.20; sh[5]+=tail*0.55
    d = np.array([dR,dE,dG,dO,dK,dX])
    nv = np.clip(np.array([s.R,s.E,s.G,s.O,s.K,s.X])+d+sh, cfg.state_min, cfg.state_max)
    s.R,s.E,s.G,s.O,s.K,s.X = nv
    prod = g*(s.R+s.K)*0.01
    s.cum_prod+=prod; s.peak_prod=max(s.peak_prod,prod)
    s.peak_X=max(s.peak_X,s.X); s.growth_accum=s.growth_accum*0.92+g
    s.step+=1
    return s

def productivity_instant(s:CivState, a:np.ndarray)->float:
    return a[0]*(s.R+s.K)*0.01
