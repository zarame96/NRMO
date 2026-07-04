"""
loom_vnext_hybrid.py

統合 controller: 「高い数値を出すが、破綻しない NRMO」

Per Zarameさん 指示:
  vNext の高出力を Loom Core / Loom Layer で制御し、
  Safety Floor で破綻を防ぎ、
  Sociable Shadow で検出・正規化する構造へ統合.

Architecture:
  vNext Ω Full      → 高出力候補生成 (build_candidate_pool + OmegaFullEngine)
  Loom Control Layer → world detection + risk proximity + Sparse mode
  Safety Floor      → v8.4.1 風 throttle/guard (civ action level)
  Sociable Shadow   → 観測・正規化 (trace のみ, 行動非介入)
"""
from __future__ import annotations
import os, sys
import numpy as np

LOOM_CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"nrmo_v72_phase1","core")
import os as _os
WORLDSIM = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "world_sim_v50", "src")
sys.path.insert(0, LOOM_CORE)
sys.path.insert(0, WORLDSIM)

from world_models import WorldState as LoomWorldState
from rng_manager import RNGManager
from enhanced_world_detector import EnhancedWorldDetector
from sociable_detection_layer import SociableDetectionSystem
from world_models import Action as LoomAction

from vnext_plus import (
    CivState, RolloutConfig, civstate_transition, is_ruin_state,
    MetaController, HysteresisTracker, adaptive_tuning,
    build_candidate_pool, construct_admissible_set,
    OmegaFullEngine, OmegaFullConfig, get_world_profile,
    detect_favorable,
)
from loom_worldsim_runner import LoomCivAdapter


def _norm(a):
    a = np.maximum(a, 0.0)
    s = a.sum()
    return a / s if s > 1e-9 else np.array([0.25, 0.25, 0.25, 0.25])


class LoomVNextHybrid:
    """高出力 (vNext) × 破綻回避 (Loom Safety Floor) 統合 controller."""
    
    # Safety Floor thresholds (v8.4.1 風, civ-sim 適用)
    RISK_PROXIMITY_EMERGENCY = 0.45   # 早期介入 (元 0.65)
    R_FLOOR_SOFT = 42.0          # R がこれ以下で throttle (元 30, 早期化)
    X_CEILING_SOFT = 58.0        # X がこれ以上で throttle (元 70, 早期化)
    GROWTH_THROTTLE_FACTOR = 0.55  # emergency 時の growth 抑制率
    
    def __init__(self, world_name: str, seed: int,
                  enable_safety_floor: bool = True,
                  enable_sociable_shadow: bool = True):
        self.world_name = world_name
        self.enable_safety_floor = enable_safety_floor
        self.enable_sociable_shadow = enable_sociable_shadow
        
        # vNext Ω Full (高出力候補生成)
        self.meta = MetaController()
        self.ht = HysteresisTracker()
        self.engine = OmegaFullEngine(OmegaFullConfig(), enable_archetype_classifier=True)
        self.base_profile = get_world_profile(world_name)
        
        # Loom Control Layer
        self.world_detector = EnhancedWorldDetector()
        self.adapter = LoomCivAdapter()
        
        # Sociable Shadow (観測のみ)
        self.sociable_shadow = SociableDetectionSystem() if enable_sociable_shadow else None
        
        # Stats
        self.stats = {
            "total_steps": 0,
            "safety_floor_applied": 0,
            "emergency_throttle": 0,
            "vnext_passthrough": 0,
            "world_detections": {},
            "shadow_records": 0,
        }
        self._last_civ_action = None
    
    def _compute_risk_proximity(self, cs: CivState) -> float:
        r_part = max(0, (35 - cs.R) / 35.0) * 0.5
        x_part = max(0, (cs.X - 60) / 40.0) * 0.5
        return min(1.0, r_part + x_part)
    
    def decide(self, cs: CivState, wp: dict, rng) -> np.ndarray:
        self.stats["total_steps"] += 1
        cfg_dummy = None
        
        # === 1. Loom Control Layer: world detection ===
        loom_state = self.adapter.civ_to_loom(cs)
        self.world_detector.update(loom_state)
        world_type, world_conf = self.world_detector.detect_world_type()
        risk_prox = self._compute_risk_proximity(cs)
        self.stats["world_detections"][world_type] = \
            self.stats["world_detections"].get(world_type, 0) + 1
        
        # === 2. vNext Ω Full: 高出力候補生成 ===
        mode = self.meta.update(cs, wp)
        cs.mode = mode
        tc = adaptive_tuning(self.base_profile, cs, mode, self.ht)
        wolf_now = detect_favorable(cs, self.engine.prev_state)
        pool = build_candidate_pool(cs, wp, rng, wolf=wolf_now)
        admissible, flags = construct_admissible_set(pool, cs, mode="vnext", tc=tc)
        
        if not admissible:
            vnext_action = np.array([0.05, 0.50, 0.22, 0.23])
        else:
            vnext_action = self.engine.select_action(
                admissible, cs, wp, rng, mode=mode, world_name=self.world_name)
        
        # === 3. Safety Floor: 破綻防止制御 ===
        final_action = vnext_action.copy()
        floor_applied = False
        
        if self.enable_safety_floor:
            emergency = (risk_prox >= self.RISK_PROXIMITY_EMERGENCY
                          or cs.R <= self.R_FLOOR_SOFT
                          or cs.X >= self.X_CEILING_SOFT)
            
            if emergency:
                # Emergency: v8.4.1 recover-first.
                # growth を抑制しつつ、governance repair (di) を主軸に R/G/E 回復.
                # 単純な growth 抑制は R-floor collapse を招くため、
                # di (distribution/governance) を大幅増強して回復投資を確保する.
                g, sf, lr, di = vnext_action
                # 危機度に応じて recover を強める
                severity = min(1.0, max(
                    (self.R_FLOOR_SOFT - cs.R) / self.R_FLOOR_SOFT if cs.R < self.R_FLOOR_SOFT else 0,
                    (cs.X - self.X_CEILING_SOFT) / (100 - self.X_CEILING_SOFT) if cs.X > self.X_CEILING_SOFT else 0,
                ))
                g_throttled = g * (self.GROWTH_THROTTLE_FACTOR * (1 - 0.5 * severity))
                sf_boosted = sf + 0.15 + 0.10 * severity
                di_boosted = di + 0.25 + 0.20 * severity  # governance repair 主軸
                lr_reduced = lr * (1 - 0.4 * severity)
                final_action = _norm(np.array([g_throttled, sf_boosted, lr_reduced, di_boosted]))
                floor_applied = True
                self.stats["safety_floor_applied"] += 1
                self.stats["emergency_throttle"] += 1
            else:
                # Normal: vNext 高出力をそのまま通過 (soft cap のみ)
                self.stats["vnext_passthrough"] += 1
        else:
            self.stats["vnext_passthrough"] += 1
        
        self._last_civ_action = final_action
        return final_action
    
    def observe_shadow(self, cs: CivState, cs_next: CivState, reward: float):
        """Sociable Shadow 観測 (行動非介入)"""
        if self.sociable_shadow is None:
            return
        # Loom action proxy (civ action → intent 推定)
        ca = self._last_civ_action
        if ca is None:
            return
        g, sf, lr, di = ca
        # 最大成分から intent 推定
        idx = int(np.argmax([g, sf, lr, di]))
        intent = ["invest", "defend", "explore", "recover"][idx]
        strength = "C" if g > 0.5 else ("B" if g > 0.3 else "A")
        loom_action = LoomAction(intent, strength)
        
        self.sociable_shadow.update(
            step=cs.step,
            state=self.adapter.civ_to_loom(cs),
            action=loom_action,
            module="HybridVNext",
            context_name=cs.mode,
            world_type=max(self.stats["world_detections"],
                            key=self.stats["world_detections"].get),
            reward=reward,
            guard_intervention=(self._last_civ_action is not None and 
                                  self.stats["emergency_throttle"] > 0),
        )
        self.stats["shadow_records"] += 1


def run_hybrid_civ(world_name: str, wp: dict, horizon: int, seed: int,
                     enable_safety_floor: bool = True) -> dict:
    """Hybrid controller で single-civ rollout."""
    rng = np.random.default_rng(seed)
    cfg = RolloutConfig(horizon=horizon, seed=seed)
    
    ctrl = LoomVNextHybrid(world_name, seed,
                             enable_safety_floor=enable_safety_floor,
                             enable_sociable_shadow=True)
    cs = CivState()
    ruin_step = -1
    
    for step in range(horizon):
        cs.step = step
        civ_action = ctrl.decide(cs, wp, rng)
        cs_next = civstate_transition(cs, civ_action, wp, rng, cfg)
        reward = (cs_next.cum_prod - cs.cum_prod) / 10.0
        ctrl.observe_shadow(cs, cs_next, reward)
        cs = cs_next
        if is_ruin_state(cs):
            ruin_step = step
            break
    
    return {
        "final_cum_prod": float(cs.cum_prod),
        "survived_steps": cs.step + 1,
        "is_ruined": ruin_step >= 0,
        "final_R": float(cs.R), "final_X": float(cs.X),
        "safety_floor_applied": ctrl.stats["safety_floor_applied"],
        "vnext_passthrough": ctrl.stats["vnext_passthrough"],
        "world_detections": dict(ctrl.stats["world_detections"]),
        "shadow_records": ctrl.stats["shadow_records"],
    }


if __name__ == "__main__":
    print("=" * 70)
    print("Loom-vNext Hybrid 統合 controller — 動作確認")
    print("=" * 70)
    
    wp = {"rivalry_level": 0.12, "shock_freq": 0.06}
    for seed in [42, 123]:
        r = run_hybrid_civ("Normal", wp, horizon=150, seed=seed)
        print(f"\n  seed={seed}: cum_prod={r['final_cum_prod']:.1f}, "
              f"survived={r['survived_steps']}, ruined={r['is_ruined']}")
        print(f"    final R={r['final_R']:.0f} X={r['final_X']:.0f}")
        print(f"    safety_floor_applied={r['safety_floor_applied']}, "
              f"vnext_passthrough={r['vnext_passthrough']}")
        print(f"    world_detections={r['world_detections']}")
        print(f"    shadow_records={r['shadow_records']}")
    
    print("\n[Hybrid 動作確認 ✅]")
