"""
config/defaults.py — Central configuration registry
SOURCE: NRMO Civilization Research Monograph
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, Tuple
import json

@dataclass
class WorldRange:
    shock_probability: Tuple[float,float]=(0.08,0.18)
    shock_scale: Tuple[float,float]=(3.0,8.0)
    tail_probability: Tuple[float,float]=(0.02,0.06)
    tail_scale: Tuple[float,float]=(12.0,25.0)
    environmental_drag: Tuple[float,float]=(0.01,0.04)
    governance_drag: Tuple[float,float]=(0.01,0.03)
    stagnation_drag: Tuple[float,float]=(0.005,0.02)
    rivalry_level: Tuple[float,float]=(0.0,0.3)
    innovation_noise: Tuple[float,float]=(0.5,1.5)
    coordination_cost: Tuple[float,float]=(0.02,0.08)
    substitutability: Tuple[float,float]=(0.3,0.7)
    tail_model_misspecification: Tuple[float,float]=(0.0,0.15)

WORLD_FAMILIES: Dict[str,WorldRange] = {
    "Normal": WorldRange(shock_probability=(0.08,0.15),shock_scale=(3,7),tail_probability=(0.02,0.04),tail_scale=(12,20),environmental_drag=(0.01,0.03),governance_drag=(0.01,0.02),stagnation_drag=(0.005,0.015),rivalry_level=(0.05,0.20),innovation_noise=(0.6,1.2),coordination_cost=(0.02,0.06),substitutability=(0.4,0.6),tail_model_misspecification=(0,0.08)),
    "Vulnerable": WorldRange(shock_probability=(0.15,0.28),shock_scale=(5,12),tail_probability=(0.04,0.10),tail_scale=(18,35),environmental_drag=(0.03,0.07),governance_drag=(0.02,0.05),stagnation_drag=(0.01,0.03),rivalry_level=(0.15,0.40),innovation_noise=(0.8,1.8),coordination_cost=(0.04,0.10),substitutability=(0.25,0.50),tail_model_misspecification=(0.05,0.25)),
    "PlanetaryStress": WorldRange(shock_probability=(0.12,0.22),shock_scale=(4,10),tail_probability=(0.03,0.08),tail_scale=(15,30),environmental_drag=(0.05,0.12),governance_drag=(0.03,0.06),stagnation_drag=(0.008,0.025),rivalry_level=(0.10,0.35),innovation_noise=(0.7,1.5),coordination_cost=(0.05,0.12),substitutability=(0.30,0.55),tail_model_misspecification=(0.05,0.20)),
    "LateStagnation": WorldRange(shock_probability=(0.05,0.12),shock_scale=(2,5),tail_probability=(0.01,0.03),tail_scale=(8,16),environmental_drag=(0.02,0.04),governance_drag=(0.02,0.05),stagnation_drag=(0.03,0.08),rivalry_level=(0.05,0.15),innovation_noise=(0.3,0.8),coordination_cost=(0.03,0.08),substitutability=(0.5,0.8),tail_model_misspecification=(0.02,0.12)),
    "FastExpansionRace": WorldRange(shock_probability=(0.10,0.20),shock_scale=(4,9),tail_probability=(0.04,0.09),tail_scale=(14,28),environmental_drag=(0.02,0.05),governance_drag=(0.01,0.04),stagnation_drag=(0.003,0.01),rivalry_level=(0.25,0.55),innovation_noise=(1.0,2.2),coordination_cost=(0.03,0.07),substitutability=(0.35,0.60),tail_model_misspecification=(0.08,0.25)),
}

@dataclass
class InitialState:
    R:float=62.0; E:float=66.0; G:float=58.0; O:float=54.0; K:float=52.0; X:float=18.0

@dataclass
class RuinThresholds:
    R_floor:float=8.0; E_floor:float=8.0; G_floor:float=8.0; O_floor:float=6.0; X_ceiling:float=92.0
    passive_O_threshold:float=18.0; passive_O_streak:int=14
    passive_K_threshold:float=20.0; passive_K_streak:int=18
    compound_streak:int=12

@dataclass
class NRMOCoreConfig:
    growth_hard_cap:float=0.62; high_exposure_growth_cap:float=0.36; high_exposure_threshold:float=55.0
    low_env_growth_cap:float=0.30; low_env_threshold:float=28.0
    low_gov_dist_floor:float=0.16; low_gov_threshold:float=24.0

@dataclass
class TuningConfig:
    exploration_floor:float=0.20; growth_cap:float=0.44; eco_growth_cap:float=0.32
    high_stakes_trigger_exposure:float=52.0; high_stakes_trigger_environment:float=30.0
    high_stakes_trigger_governance:float=26.0
    passive_ruin_optionality_threshold:float=22.0; passive_ruin_knowledge_threshold:float=22.0
    governance_repair_floor:float=0.18; exposure_penalty_weight:float=0.40
    optionality_weight:float=0.45; knowledge_weight:float=0.20; hysteresis_steps:int=6

def _pN(): return TuningConfig(exploration_floor=0.20,growth_cap=0.44,high_stakes_trigger_exposure=52.0,governance_repair_floor=0.18)
def _pV(): return TuningConfig(exploration_floor=0.20,growth_cap=0.36,high_stakes_trigger_exposure=45.0,high_stakes_trigger_environment=35.0,governance_repair_floor=0.22,exposure_penalty_weight=0.48,optionality_weight=0.48)
def _pP(): return TuningConfig(exploration_floor=0.18,growth_cap=0.38,eco_growth_cap=0.32,high_stakes_trigger_environment=40.0,exposure_penalty_weight=0.42,optionality_weight=0.46)
def _pL(): return TuningConfig(exploration_floor=0.23,growth_cap=0.40,passive_ruin_knowledge_threshold=24.0,knowledge_weight=0.28,passive_ruin_optionality_threshold=26.0)
def _pF(): return TuningConfig(exploration_floor=0.18,growth_cap=0.48,high_stakes_trigger_exposure=50.0,exposure_penalty_weight=0.32)
_PROFILES={"Normal":_pN,"Vulnerable":_pV,"PlanetaryStress":_pP,"LateStagnation":_pL,"FastExpansionRace":_pF}
def get_world_profile(n:str)->TuningConfig: return _PROFILES.get(n,_pN)()

@dataclass
class BaseEngineConfig:
    candidate_count:int=12; rollout_depth:int=5; rollout_repeats:int=6
    productivity_weight:float=1.0; optionality_weight:float=0.4; governance_weight:float=0.1
    environment_weight:float=0.05; exposure_penalty:float=0.3

@dataclass
class OmegaScoring:
    """SOURCE: monograph Omega Full scoring specification."""
    reward:float=1.00; optionality:float=0.45; knowledge:float=0.20
    governance:float=0.15; environment:float=0.10; exposure:float=-0.40
    drawdown_risk:float=-0.24; tail_risk:float=-0.22
    irreversibility_risk:float=-0.14; stagnation_risk:float=-0.10
    average_weight:float=0.65; downside_weight:float=0.35

PORTFOLIO_WEIGHTS={"Normal":(0.70,0.20,0.10),"HighStakes":(0.60,0.35,0.05),"Recovery":(0.50,0.45,0.05),"StagnationEscape":(0.60,0.20,0.20),"Race":(0.75,0.20,0.05)}

@dataclass
class OmegaFullConfig:
    candidate_count:int=14; rollout_depth:int=6; rollout_repeats:int=6
    counterfactual_branches:int=2; scoring:OmegaScoring=field(default_factory=OmegaScoring)
    exploration_allowance:float=0.06; irreversibility_sensitivity:float=0.14
    fragility_prior:float=0.5; portfolio_hedge_bias:float=0.20
    rollout_depth_bias:float=1.3; candidate_diversity_bias:float=0.05
    failure_memory_size:int=64; failure_penalty:float=0.15
    # Long-horizon drift control
    lambda_drift:float=1.0
    normal_drift_multiplier:float=1.25

@dataclass
class SimConfig:
    horizon:int=200; seed:int=42; state_min:float=0.0; state_max:float=130.0

@dataclass
class ScoreWeights:
    survival_rate:float=1.0; true_ruin_rate:float=-0.50; passive_ruin_rate:float=-0.50
    optionality:float=0.22; productivity:float=0.08; exposure:float=-0.12

@dataclass
class SweepRanges:
    exploration_floor:Tuple[float,float]=(0.12,0.28); growth_cap:Tuple[float,float]=(0.32,0.60)
    rollout_depth:Tuple[int,int]=(3,12); candidate_count:Tuple[int,int]=(8,24); n_samples:int=20
