"""
validate_part_b_subprocess.py — Part B 専用 (subprocess 分離)。
NRMO/Engine 分離契約だけを見る。Part A の状態を持ち越さない別プロセス。

必須:
  engine_never_reads_veto_thresholds
  selected_action_always_in_admissible
  vetoed_action_unreachable
  empty_admissible_returns_hold
  domain_rollout_uses_domain_dynamics
  memory_changes_future_candidate_distribution
  no_NRMO_boundary_mutation_by_engine
  all_domain_examples_reproduce_light   (steps<=50, seeds<=2, horizon<=8)
"""
from __future__ import annotations
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "core"))

import numpy as np
import run_all_validations as R   # 7 個の高速分離テスト + helpers を再利用


def t_all_domain_examples_reproduce_light():
    """正式入口用の軽量再現テスト (steps<=50, seeds<=2, horizon<=8)。"""
    def run(seed):
        eng = R._engine(horizon=8); dyn = R.DemoDomain()
        goal = R.GoalInterpreter(); gov = R.DemoNRMO()
        rng = np.random.default_rng(seed); s = R.fresh_state()
        f0 = dyn.forward_value(s); ruined = False
        for _ in range(50):
            a, _ = eng.step(gov, dyn, s, goal, rng)
            if a is R.HOLD:
                safe = np.array([0.10, 0.55, 0.20, 0.30])
                if gov.filter([safe], s):
                    s = dyn.transition(s, safe, rng)
                continue
            s = dyn.transition(s, a, rng)
            if dyn.is_ruin(s):
                ruined = True; break
        return ruined, dyn.forward_value(s) - f0
    r1 = run(11); r2 = run(11)
    assert r1 == r2, "not reproducible (light)"
    for sd in (11, 12):
        ru, gn = run(sd)
        assert not ru, f"seed {sd}: ruin in light run"
    return True


# 7 個の高速テスト + 軽量再現
TESTS = [
    ("engine_never_reads_veto_thresholds", R.t_engine_never_reads_veto_thresholds),
    ("selected_action_always_in_admissible", R.t_selected_action_always_in_admissible),
    ("vetoed_action_unreachable", R.t_vetoed_action_unreachable),
    ("empty_admissible_returns_hold", R.t_empty_admissible_returns_hold),
    ("domain_rollout_uses_domain_dynamics", R.t_domain_rollout_uses_domain_dynamics),
    ("memory_changes_future_candidate_distribution", R.t_memory_changes_future_candidate_distribution),
    ("no_NRMO_boundary_mutation_by_engine", R.t_no_NRMO_boundary_mutation_by_engine),
    ("all_domain_examples_reproduce_light", t_all_domain_examples_reproduce_light),
]


def main():
    print("[PART B] NRMO 分離契約 (propose→filter→select, ruin_penalty 排除)")
    fails = 0
    for name, fn in TESTS:
        try:
            fn(); print(f"  PASS: {name}")
        except Exception as e:
            fails += 1; print(f"  FAIL: {name}  -- {e}")
    print("-" * 50)
    if fails == 0:
        print("NRMO SEPARATION CONTRACT: ALL PASS")
        sys.exit(0)
    print(f"NRMO SEPARATION CONTRACT: {fails} FAILED")
    sys.exit(1)


if __name__ == "__main__":
    main()
