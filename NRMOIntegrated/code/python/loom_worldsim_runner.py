"""
loom_worldsim_runner.py

Loom v3.1 (frozen Behavioral Core) で Integrated の civilisation
simulation (world_sim_v50) を回す adapter + runner.

CivState (R,E,G,O,K,X) は Loom の WorldState と同じ 6 次元.
Loom Action (intent, strength) を civ action (g, sf, lr, di) に変換する.
"""
from __future__ import annotations
import os, sys
import numpy as np
from pathlib import Path

# Loom v3.1 core path
LOOM_CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"nrmo_v72_phase1","core")
sys.path.insert(0, LOOM_CORE)

# world_sim path
import os as _os
WORLDSIM = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "world_sim_v50", "src")
sys.path.insert(0, WORLDSIM)

from world_models import WorldState as LoomWorldState, Action as LoomAction
from rng_manager import RNGManager
from loom_v3_1 import LoomV31

from vnext_plus import (
    CivState, RolloutConfig, civstate_transition,
    check_true_ruin, is_ruin_state,
)


# ============================================================
# Adapter
# ============================================================

class LoomCivAdapter:
    """CivState <-> Loom WorldState, Loom Action -> civ action (g,sf,lr,di)."""
    
    @staticmethod
    def civ_to_loom(cs: CivState) -> LoomWorldState:
        """CivState (R,E,G,O,K,X) → Loom WorldState (同じ 6D)"""
        return LoomWorldState(
            t=cs.step,
            R=float(cs.R), E=float(cs.E), G=float(cs.G),
            O=float(cs.O), K=float(cs.K), X=float(cs.X),
            cumulative_score=float(cs.cum_prod),
            is_ruined=bool(cs.true_ruin or cs.passive_ruin),
        )
    
    @staticmethod
    def loom_action_to_civ(action: LoomAction) -> np.ndarray:
        """Loom Action (intent, strength) → civ action np.array([g, sf, lr, di]).
        
        g  = growth pressure
        sf = safety / defensive allocation
        lr = learning / exploration rate
        di = distribution / governance repair
        """
        # Strength magnitude
        mag = {"A": 0.5, "B": 1.0, "C": 1.6}.get(action.strength, 1.0)
        
        # Intent → base (g, sf, lr, di) profile
        profiles = {
            "invest":  np.array([0.55, 0.15, 0.15, 0.20]),  # growth-heavy
            "defend":  np.array([0.10, 0.55, 0.10, 0.25]),  # safety-heavy
            "explore": np.array([0.20, 0.15, 0.50, 0.15]),  # learning-heavy
            "recover": np.array([0.15, 0.30, 0.15, 0.40]),  # governance repair
            "hold":    np.array([0.10, 0.30, 0.15, 0.45]),  # conservative
        }
        base = profiles.get(action.intent, profiles["hold"])
        
        # Scale growth by magnitude; keep di (distribution) as exploration floor
        g  = float(base[0] * mag)
        sf = float(base[1])
        lr = float(max(base[2], 0.12))   # exploration floor
        di = float(max(base[3], 0.15))   # governance repair floor
        
        return np.array([g, sf, lr, di])


# ============================================================
# Single-civ runner
# ============================================================

def run_single_civ(loom_engine, world_params: dict,
                     horizon: int = 200, seed: int = 42,
                     init_state: CivState = None) -> dict:
    """1 civilisation を Loom v3.1 で回す single-civ rollout."""
    rng = np.random.default_rng(seed)
    cfg = RolloutConfig(horizon=horizon, seed=seed)
    adapter = LoomCivAdapter()
    
    cs = init_state or CivState()
    
    trajectory = []
    ruin_step = -1
    
    for step in range(horizon):
        cs.step = step
        
        # 1. CivState → Loom WorldState
        loom_state = adapter.civ_to_loom(cs)
        
        # 2. Loom v3.1 decide
        decision = loom_engine.decide(loom_state)
        loom_action = decision.action
        
        # 3. Loom action → civ action (g, sf, lr, di)
        civ_action = adapter.loom_action_to_civ(loom_action)
        
        # 4. Civ state transition
        cs_next = civstate_transition(cs, civ_action, world_params, rng, cfg)
        
        # 5. Reward (productivity delta) を Loom に feedback
        reward = (cs_next.cum_prod - cs.cum_prod) / 10.0  # normalize
        sb = {"R": cs.R, "E": cs.E, "G": cs.G, "O": cs.O, "K": cs.K, "X": cs.X}
        sa = {"R": cs_next.R, "E": cs_next.E, "G": cs_next.G,
              "O": cs_next.O, "K": cs_next.K, "X": cs_next.X}
        loom_engine.update_reward(loom_action, reward, sb, sa)
        
        trajectory.append({
            "step": step,
            "R": cs_next.R, "E": cs_next.E, "G": cs_next.G,
            "O": cs_next.O, "K": cs_next.K, "X": cs_next.X,
            "cum_prod": cs_next.cum_prod,
            "mode": decision.primary_mode,
            "action": f"{loom_action.intent}/{loom_action.strength}",
        })
        
        cs = cs_next
        
        # Ruin check
        if is_ruin_state(cs):
            ruin_step = step
            cs.true_ruin = True
            break
    
    return {
        "final_cum_prod": float(cs.cum_prod),
        "peak_prod": float(cs.peak_prod),
        "survived_steps": cs.step + 1,
        "ruin_step": ruin_step,
        "is_ruined": ruin_step >= 0,
        "final_state": {"R": cs.R, "E": cs.E, "G": cs.G,
                          "O": cs.O, "K": cs.K, "X": cs.X},
        "trajectory": trajectory,
        "mode_counts": dict(loom_engine.stats["mode_counts"]),
    }


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Loom v3.1 で Civilisation Simulation (world_sim_v50) を回す")
    print("=" * 70)
    
    # World parameters (different civilisation environments)
    world_configs = {
        "stable":     {"rivalry_level": 0.10, "shock_freq": 0.05},
        "competitive": {"rivalry_level": 0.30, "shock_freq": 0.10},
        "volatile":   {"rivalry_level": 0.20, "shock_freq": 0.25},
    }
    
    for world_name, wp in world_configs.items():
        print(f"\n--- World: {world_name} (rivalry={wp['rivalry_level']}, "
              f"shock={wp['shock_freq']}) ---")
        results = []
        for seed in [42, 123, 777, 2024, 9999]:
            loom = LoomV31(rng_manager=RNGManager(master_seed=seed + 500000),
                              use_qs_essence=True)
            r = run_single_civ(loom, wp, horizon=300, seed=seed)
            results.append(r)
            print(f"  seed={seed}: cum_prod={r['final_cum_prod']:.1f}, "
                  f"survived={r['survived_steps']}/300, "
                  f"ruined={r['is_ruined']}, "
                  f"final R={r['final_state']['R']:.0f} X={r['final_state']['X']:.0f}")
        
        avg_prod = np.mean([r["final_cum_prod"] for r in results])
        avg_survived = np.mean([r["survived_steps"] for r in results])
        ruin_rate = np.mean([r["is_ruined"] for r in results])
        print(f"  AVG: cum_prod={avg_prod:.1f}, survived={avg_survived:.0f}, "
              f"ruin_rate={ruin_rate:.0%}")
        # Mode usage (last run)
        print(f"  Modes (last run): {results[-1]['mode_counts']}")
    
    print("\n[Loom v3.1 で civilisation simulation 動作確認 ✅]")
