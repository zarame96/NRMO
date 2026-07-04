"""
v7.1 wrapper for CollectiveCivController.

Combines:
- v7.0 CollectiveCivController (P-U mechanisms, fixed parameters)
- v7.1 CollectiveStrongEngine (W-AB mechanisms, search-driven parameters)

The Engine generates a CollectiveConfiguration each generation, which
overwrites v7.0's fixed P-U parameters before the rescue cascade runs.

This wrapping preserves NRMO's architectural principles:
- v7.0 layer = veto-like rules (the P-U fixed mechanisms)
- v7.1 layer = search (the Engine that explores Configurations)
- v7.0 mechanisms execute with Engine-provided parameters
"""
import numpy as np
import copy
from typing import Optional, Dict, List

from nrmo_collective_v70 import CollectiveCivController, CollectiveConfig
from collective_engine_v71 import (
    CollectiveStrongEngine, CollectiveEngineConfig, CollectiveConfiguration,
    triage_rescue_selection, compute_lineage_features,
)


class CollectiveCivControllerV71:
    """v7.1 controller: combines v7.0 P-U layer + v7.1 search Engine.

    Each generation:
    1. Engine selects optimal CollectiveConfiguration c* (search)
    2. c* parameters overwrite v7.0 controller's P-U parameters
    3. v7.0 controller executes with the new parameters
    4. Engine state updates from observed rescue outcomes
    """

    def __init__(self, civ_name: str, civ_module,
                  v70_cfg: Optional[CollectiveConfig] = None,
                  v71_cfg: Optional[CollectiveEngineConfig] = None,
                  strategy_names: Optional[List[str]] = None,
                  n_families: int = 4):
        self.civ_name = civ_name
        self.civ_module = civ_module
        # v7.0 layer (P-U execution)
        self.v70 = CollectiveCivController(
            civ_name, civ_module, v70_cfg or CollectiveConfig(),
            strategy_names=strategy_names, n_families=n_families)
        # v7.1 layer (Engine)
        self.engine = CollectiveStrongEngine(civ_name, v71_cfg or CollectiveEngineConfig())
        self.strategy_names = strategy_names or []
        self.last_config: Optional[CollectiveConfiguration] = None
        self.last_diagnostics: Optional[dict] = None
        # Cross-gen tracking
        self.engine_log = []

    # --- Pass-through accessors ---
    @property
    def insurance(self):
        return self.v70.insurance

    @property
    def solidarity(self):
        return self.v70.solidarity

    @property
    def cfg(self):
        # Used by step_civ_one_gen for D-sigma reading
        return self.v70.cfg

    @property
    def gen_rescues(self):
        return self.v70.gen_rescues

    @gen_rescues.setter
    def gen_rescues(self, v):
        self.v70.gen_rescues = v

    # --- Engine-driven main entry ---
    def run_engine_select(self, civstate_scalar, world_params,
                            partner_civs: List[str],
                            partner_balances: Dict[str, float],
                            partner_states: Dict,
                            rivalry_pairs: Dict,
                            inequality: float, rng) -> CollectiveConfiguration:
        """Step 1: Engine selects CollectiveConfiguration this generation.

        Returns the chosen configuration AND applies it to v70 parameters.
        """
        # Current pool levels (normalised by initial budget approximation)
        if self.v70.insurance is not None:
            pool_family = sum(p.accumulated_edu + p.accumulated_assets
                              for p in self.v70.insurance.family_pools) / max(1, len(self.v70.insurance.family_pools))
            pool_lineage = sum(p.accumulated_edu + p.accumulated_assets
                                for p in self.v70.insurance.lineage_pools.values()) / max(1, len(self.v70.insurance.lineage_pools))
            pool_civ = self.v70.insurance.civ_pool.accumulated_edu + self.v70.insurance.civ_pool.accumulated_assets
            # Normalize roughly (assumes pool sizes in [0, 100])
            pool_levels = {
                "family": min(1.0, pool_family / 50),
                "lineage": min(1.0, pool_lineage / 50),
                "civ": min(1.0, pool_civ / 50),
                "cohesion": self.v70.solidarity.cohesion if self.v70.solidarity else 0.5,
            }
        else:
            pool_levels = {"family": 1.0, "lineage": 1.0, "civ": 1.0, "cohesion": 0.5}

        # Pressure indicators (how much each tier was used recently)
        pressure_indicators = {
            "family": self.v70.gen_rescues / 100,  # crude proxy
            "lineage": self.v70.gen_rescues / 100,
            "civ": self.v70.gen_rescues / 100,
        }

        config, diag = self.engine.select_configuration(
            civ_state=civstate_scalar,
            world_params=world_params,
            pool_levels=pool_levels,
            pressure_indicators=pressure_indicators,
            partner_civs=partner_civs,
            partner_balances=partner_balances,
            partner_states=partner_states,
            rivalry_pairs=rivalry_pairs,
            inequality=inequality,
            rng=rng)

        # Apply config to v70 parameters
        self._apply_config_to_v70(config)

        self.last_config = config
        self.last_diagnostics = diag
        self.engine_log.append({"gen": len(self.engine_log), "config": config,
                                  "diag": diag})
        return config

    def _apply_config_to_v70(self, config: CollectiveConfiguration):
        """Overwrite v7.0 fixed parameters with Engine-selected values."""
        c70 = self.v70.cfg
        c70.p_family_pool_rate = config.family_pool_rate
        c70.p_lineage_pool_rate = config.lineage_pool_rate
        c70.p_civ_pool_rate = config.civ_pool_rate
        c70.p_family_coverage = config.family_coverage
        c70.p_lineage_coverage = config.lineage_coverage
        c70.p_civ_coverage = config.civ_coverage

    # --- Per-gen / end-of-gen pass-through ---
    def apply_shock_modifiers(self, shock_add):
        return self.v70.apply_shock_modifiers(shock_add)

    def apply_dfp_modifiers(self, dfp, agent_strategy, strategy_names):
        return self.v70.apply_dfp_modifiers(dfp, agent_strategy, strategy_names)

    def project_actions_with_collective_layer(self, *args, **kwargs):
        return self.v70.project_actions_with_collective_layer(*args, **kwargs)

    def attempt_rescue_cascade(self, at_risk_indices, family_assignment,
                                 agent_strategy, strategy_names, rng,
                                 edu=None, assets=None, inst=None, urban=None,
                                 all_active=None, use_triage=True):
        """Triage-augmented rescue cascade (v7.1 enhancement).

        If features arrays provided AND use_triage, applies v7.1 triage
        ordering instead of v7.0 random rescue.
        """
        if self.v70.insurance is None or len(at_risk_indices) == 0:
            return np.zeros(len(at_risk_indices), dtype=bool)

        # X: triage selection if features provided
        if use_triage and edu is not None and assets is not None:
            # Determine total rescue budget across tiers
            cost = 0.5
            n_fam = int(min(self.v70.insurance.family_pools[0].accumulated_edu,
                              self.v70.insurance.family_pools[0].accumulated_assets) / cost)
            # Use engine triage weights
            triage_w = self.engine.state.triage_weights
            n_can_rescue = min(len(at_risk_indices),
                                 int(len(at_risk_indices) * self.v70.cfg.p_family_coverage))
            if n_can_rescue > 0:
                rescued = triage_rescue_selection(
                    at_risk_indices, agent_strategy, strategy_names,
                    edu, assets, inst, urban, all_active,
                    n_can_rescue=n_can_rescue, triage_weights=triage_w)
                # Now actually pay from cascading pools
                n_rescued = int(rescued.sum())
                # Approximation: deduct from family pool first
                if n_rescued > 0:
                    for fp in self.v70.insurance.family_pools:
                        afford = min(fp.accumulated_edu, fp.accumulated_assets) / cost
                        take = min(n_rescued, int(afford))
                        if take > 0:
                            fp.accumulated_edu -= take * cost
                            fp.accumulated_assets -= take * cost
                            fp.rescued_total += take
                            n_rescued -= take
                        if n_rescued == 0:
                            break
                self.v70.gen_rescues += int(rescued.sum())
                return rescued

        # Fall back to v7.0 cascade
        return self.v70.attempt_rescue_cascade(
            at_risk_indices, family_assignment, agent_strategy,
            strategy_names, rng)

    def step_end_of_generation(self, edu, assets, absorbed, agent_strategy,
                                 strategy_names, family_assignment,
                                 crisis_flag, rng):
        """End-of-gen: v70 contributions + v71 engine state update."""
        # v70 handles contributions and solidarity update
        self.v70.step_end_of_generation(edu, assets, absorbed, agent_strategy,
                                          strategy_names, family_assignment,
                                          crisis_flag, rng)
        # v71 engine state: dependency tracking
        active = ~absorbed
        n_total = int(active.sum())
        n_rescues_this_gen = self.v70.gen_rescues
        self.engine.update_after_gen(n_rescues_this_gen, n_total)
