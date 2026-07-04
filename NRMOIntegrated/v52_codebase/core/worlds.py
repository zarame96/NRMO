"""
core/worlds.py — World families and per-run instantiation
SOURCE: monograph world family specifications
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, fields
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.defaults import WorldRange, WORLD_FAMILIES

@dataclass
class WorldInstance:
    name:str; shock_probability:float; shock_scale:float
    tail_probability:float; tail_scale:float
    environmental_drag:float; governance_drag:float; stagnation_drag:float
    rivalry_level:float; innovation_noise:float; coordination_cost:float
    substitutability:float; tail_model_misspecification:float
    def as_dict(self)->dict:
        return {f.name:getattr(self,f.name) for f in fields(self) if f.name!="name"}

def draw_world(family:str, rng:np.random.Generator)->WorldInstance:
    wr=WORLD_FAMILIES[family]; p={}
    for f in fields(wr):
        lo,hi=getattr(wr,f.name); p[f.name]=rng.uniform(lo,hi)
    return WorldInstance(name=family,**p)

def list_world_families()->list: return list(WORLD_FAMILIES.keys())
