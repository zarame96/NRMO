"""
validation/v85_full_benchmark.py

V8.5 = v8.4.1 + StrongEngineΩfull (with AggressiveEngine submodule).

Ablation:
  v7.1
  v8.4.1 (frozen baseline)
  v8.5 with StrongEngineΩfull ON
  v8.5 with StrongEngineΩfull OFF (= v8.4.1 effectively)
"""
from __future__ import annotations
import os, sys, json, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List
import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "core"))

from config import NRMOConfig
from chaotic_world import ChaoticWorld, ChaosConfig
from world_models import Action


def _run_v71(args):
    chaos, horizon, seed = args
    from engines import V71Engine
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
    eng = V71Engine(rng=np.random.default_rng(seed + 100000))
    ruined = False
    for t in range(horizon):
        a = eng.select_action(world.observe())
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v841(args):
    chaos, horizon, seed = args
    from v841_engine import V841Engine
    from rng_manager import RNGManager
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
    eng = V841Engine(rng_manager=RNGManager(master_seed=seed + 200000), 
                       use_active_pattern=True)
    ruined = False
    for t in range(horizon):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(world.state)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v85_on(args):
    chaos, horizon, seed = args
    from v85_engine import V85Engine
    from rng_manager import RNGManager
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
    eng = V85Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                      use_active_pattern=True,
                      use_strong_engine_full=True)
    ruined = False
    for t in range(horizon):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(world.state)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "aggressive_activated_count": eng.stats["aggressive_activated_count"],
             "aggressive_mode_counts": eng.stats["aggressive_mode_counts"],
             "emergency_triggered": eng.stats["emergency_triggered"],
             "throttle_triggered": eng.stats["throttle_triggered"],
             "ap_intervened": eng.stats["ap_intervened"],
             "strong_engine_selected": eng.stats["strong_engine_selected"]}


def _run_v85_off(args):
    chaos, horizon, seed = args
    from v85_engine import V85Engine
    from rng_manager import RNGManager
    cfg = ChaosConfig.from_level(chaos)
    world = ChaoticWorld(cfg, seed=seed)
    eng = V85Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                      use_active_pattern=True,
                      use_strong_engine_full=False)  # OFF
    ruined = False
    for t in range(horizon):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        d = eng.decide(world.state)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def run(config, n_runs=200, horizon=200, seed_offset=900):
    levels = ["mild", "moderate", "severe", "extreme", "total"]
    print("=" * 80)
    print("V8.5 Full Benchmark — StrongEngineΩfull (with AggressiveEngine submodule)")
    print("=" * 80)
    print(f"  n_runs={n_runs}, seeds {seed_offset}-{seed_offset+n_runs-1}")
    
    all_results = {}
    for level in levels:
        print(f"\n[{level.upper()}]")
        args = [(level, horizon, seed_offset + s) for s in range(n_runs)]
        
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
            v71_r = list(ex.map(_run_v71, args))
        with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
            v841_r = list(ex.map(_run_v841, args))
        with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
            v85_on_r = list(ex.map(_run_v85_on, args))
        with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
            v85_off_r = list(ex.map(_run_v85_off, args))
        elapsed = time.time() - t0
        
        def stats(rs):
            s = np.array([r["final_score"] for r in rs])
            return {"median": float(np.median(s)), "mean": float(np.mean(s)),
                     "std": float(np.std(s)),
                     "ruin_rate": float(np.mean([r["is_ruined"] for r in rs])),
                     "median_steps": float(np.median([r["completed_steps"] for r in rs]))}
        
        v71_s = stats(v71_r)
        v841_s = stats(v841_r)
        v85_on_s = stats(v85_on_r)
        v85_off_s = stats(v85_off_r)
        
        diffs_vs_841 = np.array([v85_on_r[i]["final_score"] - v841_r[i]["final_score"]
                                   for i in range(n_runs)])
        se_effect = np.array([v85_on_r[i]["final_score"] - v85_off_r[i]["final_score"]
                               for i in range(n_runs)])
        
        from scipy.stats import wilcoxon
        try:
            _, p_85 = wilcoxon(diffs_vs_841, alternative="two-sided")
        except Exception:
            p_85 = None
        try:
            _, p_se = wilcoxon(se_effect, alternative="two-sided")
        except Exception:
            p_se = None
        
        agg_avg = np.mean([r["aggressive_activated_count"] for r in v85_on_r])
        mode_totals = {}
        for r in v85_on_r:
            for m, c in r["aggressive_mode_counts"].items():
                mode_totals[m] = mode_totals.get(m, 0) + c
        
        cell = {
            "v71": v71_s, "v841": v841_s,
            "v85_se_on": v85_on_s, "v85_se_off": v85_off_s,
            "paired_v85_vs_v841": {
                "median": float(np.median(diffs_vs_841)),
                "mean": float(np.mean(diffs_vs_841)),
                "n_85_better": int(np.sum(diffs_vs_841 > 0)),
                "wilcoxon_p": p_85,
            },
            "se_pure_effect": {
                "median": float(np.median(se_effect)),
                "mean": float(np.mean(se_effect)),
                "n_on_better": int(np.sum(se_effect > 0)),
                "wilcoxon_p": p_se,
            },
            "variance_change": {
                "v841_std": v841_s["std"], "v85_std": v85_on_s["std"],
                "std_delta": v85_on_s["std"] - v841_s["std"],
            },
            "aggressive_activated_avg_per_run": float(agg_avg),
            "aggressive_mode_totals": mode_totals,
            "elapsed_sec": elapsed,
        }
        
        print(f"  v7.1:           median={v71_s['median']:7.2f}  std={v71_s['std']:5.2f}")
        print(f"  v8.4.1:         median={v841_s['median']:7.2f}  std={v841_s['std']:5.2f}")
        print(f"  v8.5 SE-ON:     median={v85_on_s['median']:7.2f}  std={v85_on_s['std']:5.2f}")
        print(f"  v8.5 SE-OFF:    median={v85_off_s['median']:7.2f}  std={v85_off_s['std']:5.2f}")
        
        d = cell["paired_v85_vs_v841"]["median"]
        sign = "+" if d >= 0 else ""
        w = cell["paired_v85_vs_v841"]["n_85_better"]
        p_str = f"{p_85:.4f}" if p_85 else "n/a"
        print(f"  v85 vs v841: diff={sign}{d:.2f}, 85 wins {w}/{n_runs}, p={p_str}")
        
        se_d = cell["se_pure_effect"]["median"]
        sign_se = "+" if se_d >= 0 else ""
        se_w = cell["se_pure_effect"]["n_on_better"]
        p_se_str = f"{p_se:.4f}" if p_se else "n/a"
        print(f"  SE effect (ON-OFF): {sign_se}{se_d:.2f}, ON wins {se_w}/{n_runs}, p={p_se_str}")
        
        print(f"  Std delta: {cell['variance_change']['std_delta']:+.2f}")
        print(f"  Aggressive: {agg_avg:.2f}/run, modes={mode_totals}")
        print(f"  ({elapsed:.0f}s)")
        
        all_results[level] = cell
    
    return all_results


def _convert(obj):
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert(v) for v in obj]
    return obj


if __name__ == "__main__":
    cfg = NRMOConfig.from_env(n_workers=4)
    results = run(cfg, n_runs=200, horizon=200, seed_offset=900)
    
    out = cfg.results_dir / "v85_full_results.json"
    with open(out, "w") as f:
        json.dump(_convert({"version": "v8.5", "main_results": results}),
                   f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
