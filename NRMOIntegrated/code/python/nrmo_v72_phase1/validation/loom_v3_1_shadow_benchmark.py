"""
validation/loom_v3_1_shadow_benchmark.py

最終確認 benchmark — 案 B 確定.

Per Zarameさん 指示:
  - Loom v3.1 を凍結 (行動主体)
  - Sociable Detection 4 層を Shadow Layer として追加 (観測のみ)
  - 行動介入 default OFF
  
Success criteria:
  - score は v3.1 と同等
  - Top3 count は v3.1 と同等
  - best-per-cell loss は悪化しない
  - Sociable metrics が trace に出る
  - 行動選択は v3.1 と一致 (ほぼ同等の paired diff)
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


def _make_world(world_type, chaos, seed):
    cfg = ChaosConfig.from_level(chaos)
    if world_type == "chaotic":
        return ChaoticWorld(cfg, seed=seed)
    elif world_type == "drifting":
        return DriftingWorld(cfg, seed=seed)
    elif world_type == "noisy":
        return NoisyObservationWorld(cfg, seed=seed)


def _run_v841(args):
    world_type, chaos, horizon, seed = args
    from v841_engine import V841Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V841Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v851(args):
    world_type, chaos, horizon, seed = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V851Engine(rng_manager=RNGManager(master_seed=seed + 200000),
                       use_active_pattern=True, use_strong_engine_full=True,
                       use_contextual_merger=True, enable_sociable_essence=False)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        a = d.action if d.action else Action("hold", "A")
        r, done, _ = world.step(a)
        eng.update_reward(a, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_v9(args):
    world_type, chaos, horizon, seed = args
    from v9_minimal_engine import V9MinimalEngine
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = V9MinimalEngine(rng_manager=RNGManager(master_seed=seed + 200000),
                            use_synthesis=True, use_emergency_guard=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_loom_v3_1(args):
    world_type, chaos, horizon, seed = args
    from loom_v3_1 import LoomV31
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomV31(rng_manager=RNGManager(master_seed=seed + 200000),
                     use_qs_essence=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done: ruined = True; break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def _run_loom_v3_1_shadow(args):
    """Loom v3.1 + Sociable Shadow Layer"""
    world_type, chaos, horizon, seed = args
    from loom_v3_1_shadow import LoomV31Shadow
    from rng_manager import RNGManager
    world = _make_world(world_type, chaos, seed)
    eng = LoomV31Shadow(rng_manager=RNGManager(master_seed=seed + 200000),
                           use_qs_essence=True)
    ruined = False
    for t in range(horizon):
        d = eng.decide(world.observe())
        r, done, _ = world.step(d.action)
        eng.update_reward(d.action, r)
        if done: ruined = True; break
    shadow_sum = eng.get_shadow_summary()
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "shadow_records": shadow_sum.get("total_records", 0),
             "shadow_drift_lik_avg": shadow_sum.get("drift_likelihood_avg", 0),
             "shadow_chaotic_lik_avg": shadow_sum.get("chaotic_likelihood_avg", 0),
             "shadow_noisy_lik_avg": shadow_sum.get("noisy_likelihood_avg", 0),
             "shadow_canonical_states": shadow_sum.get("canonical_stats", {}).get("canonical_states", 0),
             "shadow_dominant_faces": shadow_sum.get("dominant_failure_faces", {})}


def _run_recover(args):
    world_type, chaos, horizon, seed = args
    world = _make_world(world_type, chaos, seed)
    ruined = False
    a = Action("recover", "A")
    for t in range(horizon):
        r, done, _ = world.step(a)
        if done: ruined = True; break
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
    }


def run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=17000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "moderate", "severe"]
    
    print("=" * 80)
    print("Loom v3.1 Shadow Final Benchmark (案 B 確定)")
    print("=" * 80)
    print(f"  Per Zarameさん 仕様: v3.1 凍結 + Sociable Detection Shadow Layer")
    
    all_results = {}
    
    for world_type in worlds:
        print(f"\n{'='*60}\n  WORLD: {world_type.upper()}\n{'='*60}")
        all_results[world_type] = {}
        
        for level in levels:
            print(f"\n[{world_type}/{level}]")
            args = [(world_type, level, horizon, seed_offset + s) for s in range(n_runs)]
            
            t0 = time.time()
            engines = {
                "v8.4.1": _run_v841,
                "v8.5.1": _run_v851,
                "v9_minimal": _run_v9,
                "Loom_v3.1": _run_loom_v3_1,
                "Loom_v3.1_Shadow": _run_loom_v3_1_shadow,
                "recover": _run_recover,
            }
            
            results = {}
            for name, runner in engines.items():
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(runner, args))
                results[name] = {"metrics": compute_metrics(rs, n_runs),
                                  "scores": [r["final_score"] for r in rs]}
                if name == "Loom_v3.1_Shadow":
                    agg = {"shadow_records_total": 0,
                            "shadow_drift_lik_list": [],
                            "shadow_chaotic_lik_list": [],
                            "shadow_noisy_lik_list": [],
                            "shadow_canonical_states_total": 0,
                            "shadow_dominant_faces": {}}
                    for r in rs:
                        agg["shadow_records_total"] += r.get("shadow_records", 0)
                        agg["shadow_drift_lik_list"].append(r.get("shadow_drift_lik_avg", 0))
                        agg["shadow_chaotic_lik_list"].append(r.get("shadow_chaotic_lik_avg", 0))
                        agg["shadow_noisy_lik_list"].append(r.get("shadow_noisy_lik_avg", 0))
                        agg["shadow_canonical_states_total"] += r.get("shadow_canonical_states", 0)
                        for f, c in r.get("shadow_dominant_faces", {}).items():
                            agg["shadow_dominant_faces"][f] = agg["shadow_dominant_faces"].get(f, 0) + c
                    results[name]["shadow_extras"] = agg
            
            elapsed = time.time() - t0
            
            # Ranking
            ranking = [(name, data["metrics"]["median"]) for name, data in results.items()]
            ranking.sort(key=lambda x: -x[1])
            print(f"  Ranking (median):")
            for i, (name, med) in enumerate(ranking):
                marker = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else "  "))
                m = results[name]["metrics"]
                print(f"    {marker} {name:<22}: med={med:6.2f} std={m['std']:5.2f} "
                      f"p5={m['p5']:6.2f}")
            
            # Shadow stats
            se = results["Loom_v3.1_Shadow"].get("shadow_extras", {})
            drift_lik_avg = float(np.mean(se.get("shadow_drift_lik_list", [0])))
            chaotic_lik_avg = float(np.mean(se.get("shadow_chaotic_lik_list", [0])))
            noisy_lik_avg = float(np.mean(se.get("shadow_noisy_lik_list", [0])))
            print(f"  Shadow stats:")
            print(f"    records={se.get('shadow_records_total', 0)}, "
                  f"canonical_states={se.get('shadow_canonical_states_total', 0)}")
            print(f"    drift_lik_avg={drift_lik_avg:.3f}, "
                  f"chaotic_lik_avg={chaotic_lik_avg:.3f}, "
                  f"noisy_lik_avg={noisy_lik_avg:.3f}")
            print(f"    dominant_faces: {se.get('shadow_dominant_faces', {})}")
            
            # Critical: paired diff v3.1 vs v3.1_Shadow
            v31 = np.array(results["Loom_v3.1"]["scores"])
            v31s = np.array(results["Loom_v3.1_Shadow"]["scores"])
            paired_diff = float(np.median(v31s - v31))
            wilcoxon_p = "n/a"
            try:
                from scipy.stats import wilcoxon
                if not all(d == 0 for d in (v31s - v31)):
                    _, p = wilcoxon(v31s - v31, alternative="two-sided")
                    wilcoxon_p = f"{p:.4f}"
                else:
                    wilcoxon_p = "all_zero"
            except Exception:
                pass
            print(f"  v3.1 vs v3.1_Shadow paired diff: {paired_diff:+.4f}, p={wilcoxon_p}")
            
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "engines": {k: {"metrics": v["metrics"]} for k, v in results.items()},
                "shadow_extras": {
                    "records": se.get("shadow_records_total", 0),
                    "canonical_states": se.get("shadow_canonical_states_total", 0),
                    "drift_lik_avg": drift_lik_avg,
                    "chaotic_lik_avg": chaotic_lik_avg,
                    "noisy_lik_avg": noisy_lik_avg,
                    "dominant_faces": se.get("shadow_dominant_faces", {}),
                },
                "paired_diff_v31_vs_shadow": paired_diff,
                "elapsed_sec": elapsed,
            }
    
    return all_results


def analyze(results):
    print("\n" + "=" * 80)
    print("案 B 確定 Final Analysis")
    print("=" * 80)
    
    # Top 3 count
    top3_counts = {}
    v31_top3 = []
    v31s_top3 = []
    
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = [(name, data["metrics"]["median"])
                        for name, data in cell["engines"].items()]
            entries.sort(key=lambda x: -x[1])
            for i, (name, _) in enumerate(entries[:3]):
                top3_counts[name] = top3_counts.get(name, 0) + 1
                if name == "Loom_v3.1":
                    v31_top3.append(f"{world}/{level}({i+1}位)")
                if name == "Loom_v3.1_Shadow":
                    v31s_top3.append(f"{world}/{level}({i+1}位)")
    
    print("\n[Top 3 入りカウント]")
    for name, count in sorted(top3_counts.items(), key=lambda x: -x[1]):
        marker = "★" if name.startswith("Loom") else " "
        print(f"  {marker} {name:<22}: {count}/9 cells")
    
    print(f"\n[Loom_v3.1 Top3]: {v31_top3}")
    print(f"[Loom_v3.1_Shadow Top3]: {v31s_top3}")
    
    # Success criteria
    v31_count = top3_counts.get("Loom_v3.1", 0)
    v31s_count = top3_counts.get("Loom_v3.1_Shadow", 0)
    
    # paired diff total
    total_paired_diff = 0.0
    for world in results.keys():
        for level in results[world].keys():
            total_paired_diff += results[world][level]["paired_diff_v31_vs_shadow"]
    
    print(f"\n[成功条件 Check]")
    mark = "✅" if v31s_count >= v31_count - 1 else "❌"
    print(f"  {mark} 1. Top3 count v3.1 と同等: v3.1={v31_count}/9, v3.1_Shadow={v31s_count}/9")
    
    mark = "✅" if abs(total_paired_diff) < 5.0 else "❌"
    print(f"  {mark} 2. paired diff total < 5.0: 実績 {total_paired_diff:.2f}")
    
    # Best-per-cell loss
    v31_loss = 0.0
    v31s_loss = 0.0
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            v31_med = cell["engines"]["Loom_v3.1"]["metrics"]["median"]
            v31s_med = cell["engines"]["Loom_v3.1_Shadow"]["metrics"]["median"]
            others = [(n, d["metrics"]["median"]) for n, d in cell["engines"].items()
                       if not n.startswith("Loom")]
            best = max(others, key=lambda x: x[1])
            v31_loss += min(0, v31_med - best[1])
            v31s_loss += min(0, v31s_med - best[1])
    
    mark = "✅" if abs(v31s_loss - v31_loss) < 3.0 else "❌"
    print(f"  {mark} 3. best-per-cell loss 悪化なし: v3.1={v31_loss:.2f}, Shadow={v31s_loss:.2f}")
    
    # Shadow trace
    total_records = sum(results[w][l]["shadow_extras"]["records"]
                          for w in results.keys() for l in results[w].keys())
    mark = "✅" if total_records > 0 else "❌"
    print(f"  {mark} 4. Sociable metrics traced: {total_records} records")
    
    # Per-cell shadow drift_lik
    print(f"\n[Shadow detection metrics per cell]")
    for world in results.keys():
        for level in results[world].keys():
            se = results[world][level]["shadow_extras"]
            print(f"  {world}/{level}: drift={se['drift_lik_avg']:.2f} "
                  f"chaotic={se['chaotic_lik_avg']:.2f} "
                  f"noisy={se['noisy_lik_avg']:.2f}  "
                  f"faces={list(se['dominant_faces'].keys())[:3]}")


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
    results = run_benchmark(cfg, n_runs=100, horizon=200, seed_offset=17000)
    analyze(results)
    
    summary = {
        "version": "loom_v3_1_shadow_final",
        "description": "Loom v3.1 凍結 + Sociable Shadow Layer (案 B 確定)",
        "main_results": results,
    }
    out = cfg.results_dir / "loom_v3_1_shadow_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
