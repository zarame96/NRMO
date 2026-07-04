"""
validation/pqr_comprehensive_benchmark.py

PQR 統合 benchmark:
  P: Hard Guard 構造分析 (v8.4.1 を 6 variant に decompose)
  Q: v8.5.1 module ablation in DriftingWorld
  R: 第 3 の world (NoisyObservationWorld) 追加

Worlds: ChaoticWorld, DriftingWorld, NoisyObservationWorld
Levels: mild, moderate, severe
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
# Engine runners
# ============================================================

def _run_hard_guard_variant(args):
    """v8.4.1 decomposed variant runner"""
    world_type, chaos, horizon, seed, variant_name = args
    from v841_decomposed import V841DecomposedEngine, VARIANTS_HARD_GUARD
    from rng_manager import RNGManager
    
    world = _make_world(world_type, chaos, seed)
    eng = V841DecomposedEngine(
        rng_manager=RNGManager(master_seed=seed + 200000),
        **VARIANTS_HARD_GUARD[variant_name]
    )
    ruined = False
    for t in range(horizon):
        sb = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        a = eng.decide(world.state)
        r, done, _ = world.step(a)
        sa = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
              "O": world.state.O, "K": world.state.K, "X": world.state.X}
        eng.update_reward(a, r, sb, sa)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t,
             "eg_triggered": eng.stats["emergency_triggered"],
             "th_triggered": eng.stats["throttle_triggered"]}


def _run_v851_variant(args):
    """v8.5.1 variant runner (DriftingWorld 中心の module ablation)"""
    world_type, chaos, horizon, seed, variant_config = args
    from v851_engine import V851Engine
    from rng_manager import RNGManager
    
    world = _make_world(world_type, chaos, seed)
    eng = V851Engine(
        rng_manager=RNGManager(master_seed=seed + 200000),
        use_active_pattern=True,
        use_strong_engine_full=variant_config.get("strong_engine", True),
        use_contextual_merger=variant_config.get("contextual_merger", True),
        module_config=variant_config.get("module_config", None),
    )
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
             "module_counts": dict(eng.stats["module_selection_counts"]),
             "context_counts": dict(eng.stats["context_counts"])}


def _run_recover_fixed(args):
    world_type, chaos, horizon, seed = args
    world = _make_world(world_type, chaos, seed)
    a = Action("recover", "A")
    ruined = False
    for t in range(horizon):
        r, done, _ = world.step(a)
        if done:
            ruined = True
            break
    return {"final_score": float(world.state.cumulative_score),
             "is_ruined": ruined, "completed_steps": world.state.t}


def compute_metrics(rs: List[Dict], n_runs: int) -> Dict:
    scores = np.array([r["final_score"] for r in rs])
    steps = np.array([r["completed_steps"] for r in rs])
    ruined = np.array([r["is_ruined"] for r in rs])
    sorted_s = np.sort(scores)
    n_bot = max(1, n_runs // 10)
    return {
        "median": float(np.median(scores)),
        "mean": float(np.mean(scores)),
        "std": float(np.std(scores)),
        "p5": float(np.percentile(scores, 5)),
        "cvar": float(np.mean(sorted_s[:n_bot])),
        "ruin_rate": float(np.mean(ruined)),
        "median_steps": float(np.median(steps)),
    }


# ============================================================
# Main runner
# ============================================================

def run_pqr_benchmark(cfg, n_runs=120, horizon=200, seed_offset=5000):
    worlds = ["chaotic", "drifting", "noisy"]
    levels = ["mild", "moderate", "severe"]
    
    HARD_VARIANTS = ["v71_pure", "v71_eg_only", "v71_th_only",
                       "v71_eg_th", "v71_full_no_ap", "v841_full"]
    
    # V8.5.1 ablation: full vs minus-each-module
    V851_ABLATIONS = {
        "v851_full": {"strong_engine": True, "contextual_merger": True},
        "v851_no_aggressive": {"strong_engine": True, "contextual_merger": True,
                                 "module_config": {m: True for m in ["defensive","recovery","exploration","mutation","synthesis","invention"]} | {"aggressive": False}},
        "v851_no_synthesis": {"strong_engine": True, "contextual_merger": True,
                                "module_config": {m: True for m in ["defensive","recovery","exploration","mutation","invention","aggressive"]} | {"synthesis": False}},
        "v851_recovery_only": {"strong_engine": True, "contextual_merger": True,
                                 "module_config": {"defensive": False, "recovery": True,
                                                    "exploration": False, "mutation": False,
                                                    "synthesis": False, "invention": False,
                                                    "aggressive": False}},
        "v851_original_merger": {"strong_engine": True, "contextual_merger": False},
    }
    
    print("=" * 80)
    print("PQR Comprehensive Benchmark")
    print("=" * 80)
    print(f"  n_runs={n_runs}, horizon={horizon}, seed_offset={seed_offset}")
    print(f"  Worlds: {worlds}")
    print(f"  Levels: {levels}")
    print(f"  Hard Guard variants: {HARD_VARIANTS}")
    print(f"  V8.5.1 ablations: {list(V851_ABLATIONS.keys())}")
    
    all_results = {}
    
    for world_type in worlds:
        print(f"\n{'='*60}")
        print(f"  WORLD: {world_type.upper()}")
        print(f"{'='*60}")
        all_results[world_type] = {}
        
        for level in levels:
            print(f"\n[{world_type}/{level}]")
            t0 = time.time()
            args_base = [(world_type, level, horizon, seed_offset + s) for s in range(n_runs)]
            
            # === P: Hard Guard variants ===
            hg_results = {}
            for variant_name in HARD_VARIANTS:
                args = [(world_type, level, horizon, seed_offset + s, variant_name)
                          for s in range(n_runs)]
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(_run_hard_guard_variant, args))
                hg_results[variant_name] = {
                    "metrics": compute_metrics(rs, n_runs),
                    "scores": [r["final_score"] for r in rs],
                    "avg_eg": float(np.mean([r["eg_triggered"] for r in rs])),
                    "avg_th": float(np.mean([r["th_triggered"] for r in rs])),
                }
            
            # === Q: V8.5.1 ablations ===
            v851_results = {}
            for ablation_name, ablation_cfg in V851_ABLATIONS.items():
                args = [(world_type, level, horizon, seed_offset + s, ablation_cfg)
                          for s in range(n_runs)]
                with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                    rs = list(ex.map(_run_v851_variant, args))
                v851_results[ablation_name] = {
                    "metrics": compute_metrics(rs, n_runs),
                    "scores": [r["final_score"] for r in rs],
                }
                # Module counts aggregate
                agg_mod = {}
                for r in rs:
                    for m, c in r.get("module_counts", {}).items():
                        agg_mod[m] = agg_mod.get(m, 0) + c
                v851_results[ablation_name]["module_histogram"] = agg_mod
            
            # === recover_fixed baseline ===
            with ProcessPoolExecutor(max_workers=cfg.n_workers) as ex:
                rec_rs = list(ex.map(_run_recover_fixed, args_base))
            rec_metrics = compute_metrics(rec_rs, n_runs)
            
            elapsed = time.time() - t0
            
            # === Print summary ===
            print(f"  Hard Guard variants:")
            for vname in HARD_VARIANTS:
                m = hg_results[vname]["metrics"]
                print(f"    {vname:<18}: med={m['median']:6.2f} std={m['std']:5.2f} "
                      f"ruin={m['ruin_rate']:.0%} steps={m['median_steps']:.0f}")
            
            print(f"  V8.5.1 ablations:")
            for aname in V851_ABLATIONS.keys():
                m = v851_results[aname]["metrics"]
                print(f"    {aname:<22}: med={m['median']:6.2f} std={m['std']:5.2f} "
                      f"ruin={m['ruin_rate']:.0%}")
            
            print(f"  recover_fixed: med={rec_metrics['median']:6.2f} "
                  f"std={rec_metrics['std']:5.2f} ruin={rec_metrics['ruin_rate']:.0%}")
            print(f"  ({elapsed:.0f}s)")
            
            all_results[world_type][level] = {
                "n_runs": n_runs,
                "hard_guard_variants": {k: {"metrics": v["metrics"],
                                              "avg_eg": v["avg_eg"],
                                              "avg_th": v["avg_th"]}
                                          for k, v in hg_results.items()},
                "v851_ablations": {k: {"metrics": v["metrics"],
                                        "module_histogram": v["module_histogram"]}
                                    for k, v in v851_results.items()},
                "recover_fixed": rec_metrics,
                "elapsed_sec": elapsed,
            }
    
    return all_results


def analyze_findings(results: Dict):
    """honest 分析と要約"""
    print("\n" + "=" * 80)
    print("PQR Comprehensive Findings")
    print("=" * 80)
    
    # P 分析: Hard Guard 構成要素の真の効果
    print("\n[P: Hard Guard Component Analysis]")
    print("各 world × level での 'v841_full' vs 'v71_pure' の差 (full hard guard 効果):")
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            pure = cell["hard_guard_variants"]["v71_pure"]["metrics"]["median"]
            full = cell["hard_guard_variants"]["v841_full"]["metrics"]["median"]
            eg_only = cell["hard_guard_variants"]["v71_eg_only"]["metrics"]["median"]
            th_only = cell["hard_guard_variants"]["v71_th_only"]["metrics"]["median"]
            eg_th = cell["hard_guard_variants"]["v71_eg_th"]["metrics"]["median"]
            no_ap = cell["hard_guard_variants"]["v71_full_no_ap"]["metrics"]["median"]
            
            print(f"  [{world}/{level}]")
            print(f"    pure→eg_only: {eg_only - pure:+.2f}, pure→th_only: {th_only - pure:+.2f}")
            print(f"    eg_th: {eg_th - pure:+.2f}, no_ap: {no_ap - pure:+.2f}, full: {full - pure:+.2f}")
            print(f"    AP contribution: {full - no_ap:+.2f}")
    
    # Q 分析: V8.5.1 module 寄与 (各 world で)
    print("\n[Q: V8.5.1 Module Ablation in 3 Worlds]")
    for world in results.keys():
        print(f"  {world}:")
        for level in results[world].keys():
            cell = results[world][level]
            full = cell["v851_ablations"]["v851_full"]["metrics"]["median"]
            no_agg = cell["v851_ablations"]["v851_no_aggressive"]["metrics"]["median"]
            no_syn = cell["v851_ablations"]["v851_no_synthesis"]["metrics"]["median"]
            rec_only = cell["v851_ablations"]["v851_recovery_only"]["metrics"]["median"]
            orig_merger = cell["v851_ablations"]["v851_original_merger"]["metrics"]["median"]
            
            print(f"    [{level}] full={full:.2f}  "
                  f"-agg:{full-no_agg:+.2f} -syn:{full-no_syn:+.2f} "
                  f"rec_only:{full-rec_only:+.2f} orig_merger:{full-orig_merger:+.2f}")
    
    # R 分析: 第 3 world で何が機能するか
    print("\n[R: NoisyObservationWorld - 真の Knightian uncertainty test]")
    if "noisy" in results:
        for level in results["noisy"].keys():
            cell = results["noisy"][level]
            v841 = cell["hard_guard_variants"]["v841_full"]["metrics"]["median"]
            v851 = cell["v851_ablations"]["v851_full"]["metrics"]["median"]
            v71_pure = cell["hard_guard_variants"]["v71_pure"]["metrics"]["median"]
            rec_fixed = cell["recover_fixed"]["median"]
            print(f"  [noisy/{level}] pure_v71={v71_pure:.2f} v841={v841:.2f} "
                  f"v851={v851:.2f} rec_fixed={rec_fixed:.2f}")
    
    # 全 world 通底パターン
    print("\n[Cross-World Pattern: 何が常に強いか]")
    rankings = {}
    for world in results.keys():
        for level in results[world].keys():
            cell = results[world][level]
            entries = []
            for vname, vdata in cell["hard_guard_variants"].items():
                entries.append((vname, vdata["metrics"]["median"]))
            for vname, vdata in cell["v851_ablations"].items():
                entries.append((vname, vdata["metrics"]["median"]))
            entries.append(("recover_fixed", cell["recover_fixed"]["median"]))
            entries.sort(key=lambda x: -x[1])
            print(f"  [{world}/{level}] Top 3: {entries[0][0]}({entries[0][1]:.1f}), "
                  f"{entries[1][0]}({entries[1][1]:.1f}), {entries[2][0]}({entries[2][1]:.1f})")


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
    results = run_pqr_benchmark(cfg, n_runs=120, horizon=200, seed_offset=5000)
    analyze_findings(results)
    
    summary = {
        "version": "pqr_comprehensive",
        "description": "P: Hard Guard ablation, Q: v8.5.1 ablation, R: 3 worlds",
        "main_results": results,
    }
    
    out = cfg.results_dir / "pqr_comprehensive_results.json"
    with open(out, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")
