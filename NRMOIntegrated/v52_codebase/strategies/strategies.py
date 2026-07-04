"""
strategies/strategies.py — 10 comparison strategies
=====================================================
ARCHITECTURAL FLOW (enforced):
  1. Engine generates candidates (execution domain)
  2. Governance constructs admissible set (governance domain)
  3. Engine scores/selects within admissible set (execution domain)

  Formal: A_t = NRMO(X_t)   ... governance
          a_t = Engine(A_t)  ... execution

  Engine NEVER receives governance thresholds.
  Governance NEVER receives engine scores.
"""
from __future__ import annotations
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.state import CivState
from governance.nrmo_core import construct_admissible_set, NRMOCoreConfig
from governance.tuning_layer import (
    get_tuning, MetaController, HysteresisTracker, MODE_NORMAL,
)
from engine.strong_engine import (
    generate_base_candidates, baseline_select, greedy_score,
    norm_action, BaseEngineConfig,
)
from engine.omega_full import (
    OmegaFullEngine, build_candidate_pool, compute_fragility,
    detect_favorable,
    OmegaFullConfig,
)
from config.defaults import TuningConfig, SimConfig, get_world_profile

# ───────────────────────────────
# Helper
# ───────────────────────────────

def _best_greedy(c, s):
    b, sc = c[0], -1e9
    for x in c:
        v = greedy_score(x, s)
        if v > sc: sc = v; b = x
    return b

# ───────────────────────────────
# 1. ExpectedValueMax
# ───────────────────────────────

class ExpectedValueMax:
    name = "ExpectedValueMax"
    def __call__(self, s, wp, rng, step, **kw):
        g = rng.uniform(0.42, 0.58)
        r = rng.dirichlet([1, 1, 1]) * (1 - g)
        return norm_action(np.array([g, r[0], r[1], r[2]]))

# ───────────────────────────────
# 2. RiskAdjustedUtility
# ───────────────────────────────

class RiskAdjustedUtility:
    name = "RiskAdjustedUtility"
    def __call__(self, s, wp, rng, step, **kw):
        g = max(0.08, min(0.48, 0.36 - 0.18 * (s.X / 130)))
        sf = 0.26 + 0.16 * (s.X / 130); lr = 0.20
        return norm_action(np.array([g, sf, lr, max(0.05, 1 - g - sf - lr)]))

# ───────────────────────────────
# 3. NRMO_Original
# ───────────────────────────────

class NRMO_Original:
    name = "NRMO_Original"
    def __init__(self, nc=NRMOCoreConfig()): self.nc = nc
    def __call__(self, s, wp, rng, step, **kw):
        # EXECUTION: generate candidates
        candidates = generate_base_candidates(s, rng, 12)
        # GOVERNANCE: construct admissible set
        admissible, _ = construct_admissible_set(candidates, s, "nrmo", nc=self.nc)
        # EXECUTION: select from admissible set
        return _best_greedy(admissible, s) if admissible else norm_action(np.array([0.05, 0.42, 0.23, 0.30]))

# ───────────────────────────────
# 4. NRMO_vNext
# ───────────────────────────────

class NRMO_vNext:
    name = "NRMO_vNext"
    def __init__(self, nc=NRMOCoreConfig()): self.nc = nc
    def __call__(self, s, wp, rng, step, **kw):
        tc = get_world_profile(kw.get("world_name", "Normal"))
        candidates = generate_base_candidates(s, rng, 14)
        admissible, _ = construct_admissible_set(candidates, s, "vnext", nc=self.nc, tc=tc)
        return _best_greedy(admissible, s) if admissible else norm_action(np.array([0.05, 0.32, 0.33, 0.30]))

# ───────────────────────────────
# 5. UltraConservative
# ───────────────────────────────

class UltraConservative:
    name = "UltraConservative"
    def __call__(self, s, wp, rng, step, **kw):
        return norm_action(np.array([0.07, 0.48, 0.13, 0.32]))

# ───────────────────────────────
# 6. AlphaSearch (no veto)
# ───────────────────────────────

class AlphaSearch:
    name = "AlphaSearch"
    def __init__(self, ec=BaseEngineConfig()): self.ec = ec
    def __call__(self, s, wp, rng, step, **kw):
        candidates = generate_base_candidates(s, rng, self.ec.candidate_count)
        # NO governance — candidates pass directly to engine
        return baseline_select(candidates, s, wp, rng, self.ec)

# ───────────────────────────────
# 7. NRMO_StrongEngine
# ───────────────────────────────

class NRMO_StrongEngine:
    name = "NRMO_StrongEngine"
    def __init__(self, nc=NRMOCoreConfig(), ec=BaseEngineConfig()):
        self.nc = nc; self.ec = ec
    def __call__(self, s, wp, rng, step, **kw):
        candidates = generate_base_candidates(s, rng, self.ec.candidate_count)
        admissible, _ = construct_admissible_set(candidates, s, "nrmo", nc=self.nc)
        return baseline_select(admissible, s, wp, rng, self.ec)

# ───────────────────────────────
# 8. NRMOvNext_StrongEngine
# ───────────────────────────────

class NRMOvNext_StrongEngine:
    name = "NRMOvNext_StrongEngine"
    def __init__(self, nc=NRMOCoreConfig(), ec=BaseEngineConfig()):
        self.nc = nc; self.ec = ec
    def __call__(self, s, wp, rng, step, **kw):
        tc = get_world_profile(kw.get("world_name", "Normal"))
        candidates = generate_base_candidates(s, rng, self.ec.candidate_count)
        admissible, _ = construct_admissible_set(candidates, s, "vnext", nc=self.nc, tc=tc)
        return baseline_select(admissible, s, wp, rng, self.ec)

# ───────────────────────────────
# 9. Adaptive_NRMOvNext_SE
# ───────────────────────────────

class Adaptive_NRMOvNext_SE:
    name = "Adaptive_NRMOvNext_SE"
    def __init__(self, nc=NRMOCoreConfig(), ec=BaseEngineConfig()):
        self.nc = nc; self.ec = ec
        self.meta = MetaController(); self.ht = HysteresisTracker()
    def __call__(self, s, wp, rng, step, **kw):
        wn = kw.get("world_name", "Normal")
        # GOVERNANCE: mode determination (upstream of execution)
        mm = self.meta.update(s, wp)
        old = s.mode; s.mode = mm
        if mm != old: s.profile_switch_count += 1
        # GOVERNANCE: adaptive tuning
        tc = get_tuning("adaptive", TuningConfig(), s, wn, mm, self.ht)
        # EXECUTION: candidate generation (engine domain, no governance params)
        candidates = generate_base_candidates(s, rng, self.ec.candidate_count)
        # GOVERNANCE: construct admissible set
        admissible, _ = construct_admissible_set(candidates, s, "vnext", nc=self.nc, tc=tc)
        # EXECUTION: score and select within admissible set
        return baseline_select(admissible, s, wp, rng, self.ec)

# ───────────────────────────────
# 10. Adaptive NRMOvNext + StrongEngine Omega Full
#     = THE DEFAULT STACK
# ───────────────────────────────

class Adaptive_NRMOvNext_OmegaFull:
    """Default stack: Adaptive NRMOvNext + StrongEngine Omega Full.

    Flow (enforced separation):
      GOVERNANCE: meta-controller → adaptive tuning → admissible boundary
      EXECUTION:  Omega candidate invention → [governance filter] → Omega scoring → portfolio

    Engine does NOT know governance thresholds.
    Governance does NOT know engine scores.
    """
    name = "Adaptive_NRMOvNext_OmegaFull"
    def __init__(self, nc=NRMOCoreConfig(), oc=OmegaFullConfig()):
        self.nc = nc; self.oc = oc
        self.engine = OmegaFullEngine(oc)
        self.meta = MetaController(); self.ht = HysteresisTracker()

    def __call__(self, s, wp, rng, step, **kw):
        wn = kw.get("world_name", "Normal")

        # ═══ GOVERNANCE ═══
        mm = self.meta.update(s, wp)
        old = s.mode; s.mode = mm
        if mm != old: s.profile_switch_count += 1
        tc = get_tuning("adaptive", TuningConfig(), s, wn, mm, self.ht)

        # ═══ EXECUTION: §1 Candidate Population System ═══
        # §4: detect favorable for Wolf Pursuit
        wolf = detect_favorable(s, self.engine.prev_state)
        # §1: base → mutation → synthesis → invention → pool
        c_raw = build_candidate_pool(s, wp, rng, wolf=wolf)

        # ═══ GOVERNANCE: Admissibility Boundary ═══
        admissible, _ = construct_admissible_set(c_raw, s, "vnext", nc=self.nc, tc=tc)

        # ═══ EXECUTION: Score + Portfolio ═══
        return self.engine.select_action(admissible, s, wp, rng, mm, wn)


# ───────────────────────────────
# Registry
# ───────────────────────────────

def build_all_strategies(base_ec=None, omega_oc=None) -> list:
    ec = base_ec or BaseEngineConfig()
    oc = omega_oc or OmegaFullConfig()
    return [
        ExpectedValueMax(), RiskAdjustedUtility(),
        NRMO_Original(), NRMO_vNext(), UltraConservative(),
        AlphaSearch(ec=ec),
        NRMO_StrongEngine(ec=ec), NRMOvNext_StrongEngine(ec=ec),
        Adaptive_NRMOvNext_SE(ec=ec),
        Adaptive_NRMOvNext_OmegaFull(oc=oc),
    ]
