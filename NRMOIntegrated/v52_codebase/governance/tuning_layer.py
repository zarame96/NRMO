"""
governance/tuning_layer.py — Adaptive tuning + meta-controller
SOURCE: monograph adaptive tuning and meta-controller specification.
"""
from __future__ import annotations
import copy
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.state import CivState
from config.defaults import TuningConfig, get_world_profile

MODE_NORMAL="Normal"; MODE_HIGHSTAKES="HighStakes"; MODE_RECOVERY="Recovery"
MODE_STAGNATION="StagnationEscape"; MODE_RACE="Race"

class MetaController:
    """5-mode meta-controller with hysteresis.
    SOURCE: monograph meta-controller modes."""
    def __init__(self, enter_th=2, exit_th=3):
        self.mode=MODE_NORMAL; self.enter_th=enter_th; self.exit_th=exit_th
        self.triggers={m:0 for m in [MODE_HIGHSTAKES,MODE_RECOVERY,MODE_STAGNATION,MODE_RACE]}
        self.stable=0

    def update(self, s:CivState, wp:dict)->str:
        triggered=set()
        if s.X>55 or s.E<28: triggered.add(MODE_HIGHSTAKES)
        if s.R<25 or s.G<25: triggered.add(MODE_RECOVERY)
        if s.O<30 or s.K<28: triggered.add(MODE_STAGNATION)
        if wp.get("rivalry_level",0)>0.35: triggered.add(MODE_RACE)
        for m in self.triggers:
            if m in triggered: self.triggers[m]+=1
            else: self.triggers[m]=max(0,self.triggers[m]-1)
        new=MODE_NORMAL
        for m in [MODE_HIGHSTAKES,MODE_RECOVERY,MODE_STAGNATION,MODE_RACE]:
            if self.triggers[m]>=self.enter_th: new=m; break
        if new==MODE_NORMAL and self.mode!=MODE_NORMAL:
            self.stable+=1
            if self.stable<self.exit_th: return self.mode
        else: self.stable=0
        self.mode=new; return self.mode

class HysteresisTracker:
    def __init__(self, cooldown=6): self.cooldown=cooldown; self.t={}
    def trigger(self,p,step): self.t[p]=step
    def locked(self,p,step): return p in self.t and (step-self.t[p])<self.cooldown

def adaptive_tuning(base:TuningConfig, s:CivState, mode:str,
                    ht:HysteresisTracker=None)->TuningConfig:
    """SOURCE: monograph state-responsive adaptation rules."""
    tc=copy.deepcopy(base)
    if mode==MODE_HIGHSTAKES:
        tc.growth_cap=min(tc.growth_cap,0.30); tc.exposure_penalty_weight=max(tc.exposure_penalty_weight,0.55)
    elif mode==MODE_RECOVERY:
        tc.growth_cap=min(tc.growth_cap,0.25); tc.governance_repair_floor=max(tc.governance_repair_floor,0.24)
    elif mode==MODE_STAGNATION:
        tc.exploration_floor=max(tc.exploration_floor,0.28); tc.knowledge_weight=max(tc.knowledge_weight,0.26)
    elif mode==MODE_RACE:
        tc.growth_cap=min(tc.growth_cap+0.04,0.54)
    step=s.step
    if s.X>48:
        ex=(s.X-48)/82; tc.growth_cap=max(0.22,tc.growth_cap-ex*0.22)
        tc.exposure_penalty_weight=min(0.65,tc.exposure_penalty_weight+ex*0.22)
    if s.O<38:
        d=(38-s.O)/38; tc.exploration_floor=min(0.34,tc.exploration_floor+d*0.12)
        tc.optionality_weight=min(0.62,tc.optionality_weight+d*0.16)
    if s.G<34:
        d=(34-s.G)/34; tc.growth_cap=max(0.22,tc.growth_cap-d*0.16)
        tc.governance_repair_floor=min(0.30,tc.governance_repair_floor+d*0.10)
    if s.E<38:
        d=(38-s.E)/38; tc.eco_growth_cap=max(0.20,tc.eco_growth_cap-d*0.10)
    if s.K<34:
        d=(34-s.K)/34; tc.exploration_floor=min(0.32,tc.exploration_floor+d*0.08)
        tc.knowledge_weight=min(0.28,tc.knowledge_weight+d*0.12)
    return tc

def get_tuning(mode_str:str, base:TuningConfig, state:CivState=None,
               world_name:str=None, meta_mode:str=MODE_NORMAL,
               ht:HysteresisTracker=None)->TuningConfig:
    if mode_str=="manual": return copy.deepcopy(base)
    if mode_str=="scenario": return get_world_profile(world_name or "Normal")
    if mode_str=="adaptive":
        bp=get_world_profile(world_name) if world_name else base
        return adaptive_tuning(bp,state,meta_mode,ht) if state else bp
    raise ValueError(mode_str)
