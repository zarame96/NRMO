"""
validation/final_3world_benchmark.py

XZW 統合 benchmark:
  X: observe() 経由で engine 呼び出し (true state ではなく観測 state)
  Z: V9 minimal engine (EG + Synthesis のみ) を含める
  W: 3 worlds × 5 engines × 3 levels で並行検証

This benchmark uses world.observe() for the engine input,
so NoisyObservationWorld's observation noise actually affects the engines.
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
from drifting_world import DriftingWorld
from noisy_world import NoisyObservationWorld
from world_models import Action


def _make_world(world_type: str, chaos_level: str, seed: int):
    cfg = ChaosConfig.from_level(chaos_level)
    if world_type == "chaotic":
        return ChaoticWorld(cfg, seed=seed)
    elif world_type == "drifting":
        return DriftingWorld(cfg, seed=seed)
    elif world_type == "noisy":
        return NoisyObservationWorld(cfg, seed=seed)
    raise ValueError(f"Unknown world: {world_type}")


# ============================================================
# Engine runners (observe() 経由)
# ============================================================

def _run_v71(args):
    world_type, chaos, horizon, seed = args
    from engines import V71Engine
    world = _make_world(world_type, chaos, seed)
    eng = V71Engine(rng=np.random.default_rng(seed + 100000))
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        a = eng.select_action(observed)
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v841(args):
    world_type, chaos, horizon, seed = args
    from v841_engine import V841Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V841Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True)
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        sb = {"R": observed.R, "E": observed.E, "G": observed.G,
              "O": observed.O, "K": observed.K, "X": observed.X}
        d = eng.decide(observed)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        observed_after = world.observe()
        sa = {"R": observed_after.R, "E": observed_after.E, "G": observed_after.G,
              "O": observed_after.O, "K": observed_after.K, "X": observed_after.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v851(args):
    world_type, chaos, horizon, seed = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V851Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True,
                       use_strong_engine_full=True,
                       use_contextual_merger=True)
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        sb = {"R": observed.R, "E": observed.E, "G": observed.G,
              "O": observed.O, "K": observed.K, "X": observed.X}
        d = eng.decide(observed)
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        observed_after = world.observe()
        sa = {"R": observed_after.R, "E": observed_after.E, "G": observed_after.G,
              "O": observed_after.O, "K": observed_after.K, "X": observed_after.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "module_counts": dict(eng.stats["module_selection_counts"])}


def _run_v9(args):
    world_type, chaos, horizon, seed = args
    from v9_minimal_engine import V9MinimalEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V9MinimalEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                            use_synthesis=True,
                            use_emergency_guard=True)
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        sb = {"R": observed.R, "E": observed.E, "G": observed.G,
              "O": observed.O, "K": observed.K, "X": observed.X}
        d = eng.decide(observed)
        r, done, _ = world.step(d.action)
        sa = {"R": observed.R, "E": observed.E, "G": observed.G,
              "O": observed.O, "K": observed.K, "X": observed.X}
        eng.update_reward(d.action, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "synthesis_selected": eng.stats["synthesis_selected"],
             "emergency_triggered": eng.stats["emergency_triggered"]}


def _run_v9_no_synthesis(args):
    """V9 ablation: EG only (no synthesis)"""
    world_type, chaos, horizon, seed = args
    from v9_minimal_engine import V9MinimalEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V9MinimalEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                            use_synthesis=False,  # ★ Synthesis OFF
                            use_emergency_guard=True)
    ruined = False
    for t in range(horizon):
        observed = world.observe()
        d = eng.decide(observed)
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_recover_fixed(args):
    world_type, chaos, horizon, seed = args
    world = _make_world(world_type, chaos, seed)
    ruined = False
    a = Action("recover", "A")
    for t in range(horizon):
        r, done, _ = world.step(a)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def compute_metrics(rs, n_runs):
    scores = np.array([r["final_score"] for r in rs])
    sorted_s = np.sort(scores)
    n_bot = max(1, n_runs // 10)
    return {
        "median": float(np.median(scores)),
        "mean": float(np.mean(scores)),
        "std": float(np.std(scores)),
        "p5": float(np.percentile(scores, 5)),
        "cvar": float(np.mean(sorted_s[:n_bot])),
        "ruin_rate": float(np.mean([r["is_ruined"] for r in rs])),
        "median_steps": float(np.median([r["completed_steps"] for r in rs])),
    }


def run_benchmark(cfg, n_runs=150, horizon=200, seed_offset=6000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "moderate", "severe"]
    
    print("=" * 80)
    print("Final 3-World Benchmark (XZW: observe() 経由, V9 統合)")
    print("=" * 80)
    print(f"  n_runs={n_runs}, horizon={horizon}, seeds {seed_offset}-{seed_offset+n_runs-1}")
    print(f"  Engines: v71_pure, v8.4.1, v8.5.1, v9_minimal, v9_no_synthesis, recover_fixed")
    print(f"  ★ All engines use world.observe() (NoisyWorld の noise が真に効く)")
    
    all_results = {}
    
    for world_type in worlds:
        print(f"\n{'='*60}")
        print(f"  WORLD: {world_type.upper()}")
        print(f"{'='*60}")
        all_results[world_type] = {}
        
        for level in levels:
            print(f"\n[{world_type}/{level}]")
            args = [(world_type, level, horizon, seed_offset + s) for s in range(n_runs)]
            
            t0 = time.time()
            
            engines = {
                "v71_pure": _run_v71,
                "v8.4.1": _run_v841,
                "v8.5.1": _run_v851,
                "v9_minimal": _run_v9,
                "v9_no_synthesis": _run_v9_no_synthesis,
                "recover_fixed": _run_recover_fixed,
            }
            
            results_by_engine = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results_by_engine[name] = {
                    "metrics": compute_metrics(rs, n_runs),
                    "scores": [r["final_score"] for r in rs],
                }
                if name == "v8.5.1":
                    agg = {}
                    for r in rs:
                        for m, c in r.get("module_counts", {}).items():
                            agg[m] = agg.get(m, 0) + c
                    results_by_engine[name]["module_histogram"] = agg
                elif name == "v9_minimal":
                    syn_total = sum(r.get("synthesis_selected", 0) for r in rs)
                    eg_total = sum(r.get("emergency_triggered", 0) for r in rs)
                    results_by_engine[name]["synthesis_total"] = syn_total
                    results_by_engine[name]["eg_total"] = eg_total
            
            elapsed = time.time() - t0
            
            # Paired
            v841_scores = np.array(results_by_engine["v8.4.1"]["scores"])
            v9_scores = np.array(results_by_engine["v9_minimal"]["scores"])
            v851_scores = np.array(results_by_engine["v8.5.1"]["scores"])
            
            from scipy.stats import wilcoxon
            try:
                _, p_v9_vs_841 = wilcoxon(v9_scores - v841_scores, alternative="two-sided")
                _, p_v9_vs_851 = wilcoxon(v9_scores - v851_scores, alternative="two-sided")
            except Exception:
                p_v9_vs_841 = p_v9_vs_851 = None
            
            # Print
            for name in engines.keys():
                m = results_by_engine[name]["metrics"]
                extra = ""
                if name == "v9_minimal":
                    extra = f" syn={results_by_engine[name]['synthesis_total']}, EG={results_by_engine[name]['eg_total']}"
                print(f"  {name:<18}: med={m['median']:6.2f} std={m['std']:5.2f} "
                      f"p5={m['p5']:6.2f} ruin={m['ruin_rate']:.0%}{extra}")
            
            v9_vs_841_diff = float(np.median(v9_scores - v841_scores))
            v9_vs_851_diff = float(np.median(v9_scores - v851_scores))
            print(f"  v9 vs v841: diff={v9_vs_841_diff:+.2f}, "
                  f"p={p_v9_vs_841:.4f}" if p_v9_vs_841 else f"  v9 vs v841: diff={v9_vs_841_diff:+.2f}")
            print(f"  v9 vs v851: diff={v9_vs_851_diff:+.2f}, "
                  f"p={p_v9_vs_851:.4f}" if p_v9_vs_851 else f"  v9 vs v851: diff={v9_vs_851_diff:+.2f}")
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "n_runs": n_runs,
                "engines": {k: {"metrics": v["metrics"]} 
                             for k, v in results_by_engine.items()},
                "v851_module_histogram": results_by_engine["v8.5.1"].get("module_histogram", {}),
                "v9_synthesis_total": results_by_engine["v9_minimal"].get("synthesis_total", 0),
                "v9_eg_total": results_by_engine["v9_minimal"].get("eg_total", 0),
                "paired_v9_vs_v841": {"median_diff": v9_vs_841_diff, "wilcoxon_p": p_v9_vs_841},
                "paired_v9_vs_v851": {"median_diff": v9_vs_851_diff, "wilcoxon_p": p_v9_vs_851},
                "elapsed_sec": elapsed,
            }
    
    return all_results


def analyze(results):
    print("\n" + "=" * 80)
    print("Final 3-World Analysis")
    print("=" * 80)
    
    # Engine ranking across all worlds/levels
    print("\n[Engine Cross-World Ranking]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = [(name, data["metrics"]["median"]) 
                        for name, data in cell["engines"].items()]
            entries.sort(key=lambda x: -x[1])
            print(f"  [{world}/{level}] Top: " + 
                  ", ".join(f"{name}({med:.1f})" for name, med in entries[:3]))
    
    # Hard Guard + Synthesis effect summary
    print("\n[V9 (EG+Synthesis) vs V8.4.1 (Hard Guard) — 引き算 vs 大規模]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            v841 = cell["engines"]["v8.4.1"]["metrics"]["median"]
            v9 = cell["engines"]["v9_minimal"]["metrics"]["median"]
            v9_no_syn = cell["engines"]["v9_no_synthesis"]["metrics"]["median"]
            v851 = cell["engines"]["v8.5.1"]["metrics"]["median"]
            print(f"  [{world}/{level}] v841={v841:.2f}  v9={v9:.2f} (diff {v9-v841:+.2f})  "
                  f"v9_no_syn={v9_no_syn:.2f}  v851={v851:.2f}")
    
    # Synthesis contribution
    print("\n[Synthesis contribution in V9 (V9 - V9_no_synthesis)]")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            v9 = cell["engines"]["v9_minimal"]["metrics"]["median"]
            v9_no = cell["engines"]["v9_no_synthesis"]["metrics"]["median"]
            print(f"  [{world}/{level}] synthesis_contribution: {v9 - v9_no:+.2f}")
    
    # NoisyWorld 真の検証
    print("\n[NoisyObservationWorld: observe() 経由での真の結果]")
    if "noisy" in results:
        for level in results["noisy"].keys():
            cell = results["noisy"][level]
            print(f"  [noisy/{level}]")
            for name, data in cell["engines"].items():
                print(f"    {name:<18}: med={data['metrics']['median']:6.2f} "
                      f"std={data['metrics']['std']:5.2f}")


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
    results = run_benchmark(cfg, n_runs=150, horizon=200, seed_offset=6000)
    analyze(results)
    
    summary = {
        "version": "final_3world_xzw",
        "description": "observe() 経由 + V9 (EG+Synthesis) を含む 3 world 検証",
        "main_results": results,
    }
    
    out = cfg.results_dir / "final_3world_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
