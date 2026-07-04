"""
validation/v83_chaotic_benchmark.py

V7.1 vs V8.3 を ChaoticWorld で比較.

検証項目:
  A) anti-fragile 検証: chaos level が上がるほど v8.3 が v7.1 に近づく/逆転するか
  C) PassivePatternScore の分布分析: 各 chaos level でどう振る舞うか

V8.3 vs V7.1 vs V8.0(参考):
  - V7.1: legacy Bandit
  - V8.3: 全 7 部品統合 (StrongEngine Ω, Shinobi, MAPLayer, PassivePattern, TypeZero, VetoClass, CumRisk)
"""
from __future__ import annotations
import os
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List
import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "core"))
sys.path.insert(0, str(_ROOT / "phase8"))
sys.path.insert(0, str(_ROOT / "phase9"))
sys.path.insert(0, str(_ROOT / "phase10"))
sys.path.insert(0, str(_ROOT / "phase11"))

from config import NRMOConfig
from chaotic_world import ChaoticWorld, ChaosConfig
from world_models import Action
from engines import V71Engine


def _run_v71(args):
    chaos_level, horizon, seed = args
    config = ChaosConfig.from_level(chaos_level)
    world = ChaoticWorld(config, seed=seed)
    engine = V71Engine()
    
    ruined = False
    ruin_step = None
    for t in range(horizon):
        observed = world.observe()
        action = engine.select_action(observed)
        reward, done, info = world.step(action)
        engine.update_reward(action, reward)
        if done:
            ruined = True
            ruin_step = t + 1
            break
    
    return {
        "engine": "v7.1",
        "chaos_level": chaos_level,
        "seed": seed,
        "final_score": float(world.state.cumulative_score),
        "is_ruined": ruined,
        "ruin_step": ruin_step,
        "completed_steps": world.state.t,
    }


def _run_v83(args):
    chaos_level, horizon, seed = args
    config = ChaosConfig.from_level(chaos_level)
    world = ChaoticWorld(config, seed=seed)
    
    from v83_engine import V83Engine
    from rng_manager import RNGManager
    rng_mgr = RNGManager(master_seed=seed + 500000)
    engine = V83Engine(rng_manager=rng_mgr, enable_meta_log=False)
    
    ruined = False
    ruin_step = None
    
    # PassivePattern 分布収集
    pp_scores = []
    pp_levels_count = {"none": 0, "mild": 0, "active": 0, "severe": 0}
    pp_interventions = 0
    veto_types = {"no_veto": 0, "soft_veto": 0, "true_veto": 0}
    
    for t in range(horizon):
        observed = world.observe()
        engine.last_state = observed
        
        try:
            decision = engine.decide(observed)
        except Exception as e:
            # 万一エラー → hold/A で fallback
            decision = None
        
        if decision is None or decision.action is None:
            action = Action(intent="hold", strength="A")
        else:
            action = decision.action
            # PP データ収集
            if decision.passive_pattern_proposal is not None:
                pp_scores.append(decision.passive_pattern_proposal.score)
                level = decision.passive_pattern_proposal.level
                pp_levels_count[level] = pp_levels_count.get(level, 0) + 1
                if decision.status == "INTERVENED":
                    pp_interventions += 1
            if decision.veto_classification is not None:
                veto_type = decision.veto_classification.veto_type.value
                veto_types[veto_type] = veto_types.get(veto_type, 0) + 1
        
        state_before = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                          "O": world.state.O, "K": world.state.K, "X": world.state.X}
        reward, done, info = world.step(action)
        state_after = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                         "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.update_reward(action, reward, state_before, state_after)
        
        if done:
            ruined = True
            ruin_step = t + 1
            break
    
    return {
        "engine": "v8.3",
        "chaos_level": chaos_level,
        "seed": seed,
        "final_score": float(world.state.cumulative_score),
        "is_ruined": ruined,
        "ruin_step": ruin_step,
        "completed_steps": world.state.t,
        # PP 分布データ
        "pp_score_median": float(np.median(pp_scores)) if pp_scores else 0.0,
        "pp_score_mean": float(np.mean(pp_scores)) if pp_scores else 0.0,
        "pp_score_max": float(np.max(pp_scores)) if pp_scores else 0.0,
        "pp_levels_count": pp_levels_count,
        "pp_interventions": pp_interventions,
        "veto_types": veto_types,
    }


def run_v83_chaotic(config: NRMOConfig,
                      chaos_levels: List[str] = None,
                      horizon: int = 300,
                      n_runs: int = 50) -> Dict:
    chaos_levels = chaos_levels or ["mild", "moderate", "severe", "extreme", "total"]
    
    print("=" * 70)
    print("V7.1 vs V8.3 in ChaoticWorld + PP Distribution Analysis")
    print("=" * 70)
    print(f"Chaos levels: {chaos_levels}")
    print(f"Horizon: {horizon}, n_runs: {n_runs}")
    
    all_results = {}
    start = time.time()
    
    for level in chaos_levels:
        print(f"\n[{level.upper()}]")
        cell_start = time.time()
        
        args = [(level, horizon, seed) for seed in range(n_runs)]
        
        # v7.1
        with ProcessPoolExecutor(max_workers=config.n_workers) as ex:
            v71_results = list(ex.map(_run_v71, args))
        
        # v8.3 (sequential で安全に — v83 は init コスト高い)
        v83_results = []
        for i, arg in enumerate(args):
            if i % 10 == 0:
                print(f"  v8.3 progress: {i}/{n_runs} ...")
            try:
                v83_results.append(_run_v83(arg))
            except Exception as e:
                print(f"  v8.3 seed={arg[2]} failed: {e}")
                v83_results.append({
                    "engine": "v8.3", "chaos_level": level, "seed": arg[2],
                    "final_score": 0.0, "is_ruined": True, "ruin_step": 1,
                    "completed_steps": 1, "pp_score_median": 0.0,
                    "pp_score_mean": 0.0, "pp_score_max": 0.0,
                    "pp_levels_count": {}, "pp_interventions": 0,
                    "veto_types": {},
                })
        
        # 集計
        v71_scores = np.array([r["final_score"] for r in v71_results])
        v83_scores = np.array([r["final_score"] for r in v83_results])
        v71_steps = np.array([r["completed_steps"] for r in v71_results])
        v83_steps = np.array([r["completed_steps"] for r in v83_results])
        v71_ruin = np.mean([r["is_ruined"] for r in v71_results])
        v83_ruin = np.mean([r["is_ruined"] for r in v83_results])
        
        diffs = v83_scores - v71_scores
        n_v83_better = int(np.sum(diffs > 0))
        n_v71_better = int(np.sum(diffs < 0))
        
        # PP 分布集計
        all_pp_scores = [r["pp_score_mean"] for r in v83_results]
        pp_score_overall = float(np.mean(all_pp_scores)) if all_pp_scores else 0.0
        
        # PP level 集計
        total_pp_levels = {"none": 0, "mild": 0, "active": 0, "severe": 0}
        for r in v83_results:
            for level_name, count in r["pp_levels_count"].items():
                total_pp_levels[level_name] = total_pp_levels.get(level_name, 0) + count
        
        # PP 介入回数
        total_interventions = sum(r["pp_interventions"] for r in v83_results)
        
        # Veto type 集計
        total_veto_types = {"no_veto": 0, "soft_veto": 0, "true_veto": 0}
        for r in v83_results:
            for vt, count in r["veto_types"].items():
                total_veto_types[vt] = total_veto_types.get(vt, 0) + count
        
        cell = {
            "chaos_level": level,
            "n_runs": n_runs,
            "v71": {
                "median_score": float(np.median(v71_scores)),
                "mean_score": float(np.mean(v71_scores)),
                "ruin_rate": float(v71_ruin),
                "median_steps": float(np.median(v71_steps)),
            },
            "v83": {
                "median_score": float(np.median(v83_scores)),
                "mean_score": float(np.mean(v83_scores)),
                "ruin_rate": float(v83_ruin),
                "median_steps": float(np.median(v83_steps)),
            },
            "paired": {
                "median_diff": float(np.median(diffs)),
                "mean_diff": float(np.mean(diffs)),
                "n_v83_better": n_v83_better,
                "n_v71_better": n_v71_better,
            },
            "pp_distribution": {
                "score_mean_across_runs": pp_score_overall,
                "level_counts_total": total_pp_levels,
                "intervention_count_total": total_interventions,
                "veto_type_counts": total_veto_types,
            },
            "elapsed_sec": time.time() - cell_start,
        }
        
        print(f"  v7.1:    median={cell['v71']['median_score']:.2f} "
                f"ruin={cell['v71']['ruin_rate']:.1%} steps={cell['v71']['median_steps']:.0f}")
        print(f"  v8.3:    median={cell['v83']['median_score']:.2f} "
                f"ruin={cell['v83']['ruin_rate']:.1%} steps={cell['v83']['median_steps']:.0f}")
        sign = "+" if cell["paired"]["median_diff"] >= 0 else ""
        print(f"  diff:    {sign}{cell['paired']['median_diff']:.2f} "
                f"(v8.3 wins {n_v83_better}/{n_runs})")
        print(f"  PP:      score_avg={pp_score_overall:.3f}, "
                f"interventions={total_interventions}")
        print(f"  PP lvls: {total_pp_levels}")
        print(f"  Veto:    {total_veto_types}")
        print(f"  ({cell['elapsed_sec']:.0f}s)")
        
        all_results[level] = cell
    
    total_elapsed = time.time() - start
    
    # サマリーテーブル
    print(f"\n{'='*70}")
    print(f"V8.3 vs V7.1 ChaoticWorld Summary")
    print(f"{'='*70}")
    print(f"{'Level':<10} {'v7.1':>10} {'v8.3':>10} {'diff':>10} {'wins':>8} "
            f"{'pp':>8} {'interv':>8}")
    print("-" * 75)
    for level in chaos_levels:
        c = all_results[level]
        d = c["paired"]["median_diff"]
        sign = "+" if d >= 0 else ""
        diff_str = f"{sign}{d:.2f}"
        wins = f"{c['paired']['n_v83_better']}/{n_runs}"
        pp_avg = c["pp_distribution"]["score_mean_across_runs"]
        interv = c["pp_distribution"]["intervention_count_total"]
        print(f"{level:<10} {c['v71']['median_score']:>10.2f} "
                f"{c['v83']['median_score']:>10.2f} "
                f"{diff_str:>10} {wins:>8} {pp_avg:>8.3f} {interv:>8}")
    
    return {
        "phase": "v83_chaotic_benchmark",
        "chaos_levels": chaos_levels,
        "horizon": horizon,
        "n_runs": n_runs,
        "results": all_results,
        "total_elapsed_sec": total_elapsed,
    }


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
    
    summary = run_v83_chaotic(
        cfg,
        chaos_levels=["mild", "moderate", "severe", "extreme", "total"],
        horizon=200,
        n_runs=30,
    )
    
    output_path = cfg.results_dir / "v83_chaotic_results.json"
    with open(output_path, "w") as f:
        json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {output_path}")
