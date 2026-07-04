"""
validation/v8_long_run.py

監査指摘 5 (Phase 5 Long Run の ruin 検証が安全性証明になっていない) への対応。

新規指標:
  - time_to_ruin (中央値、四分位)
  - survival_curve (Kaplan-Meier 風)
  - checkpoint_survival_rate
  - 途中破滅後の値を plateau 扱いしない
  - 破滅 run と生存 run の分離統計
"""
from __future__ import annotations
import os
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple, Optional
import numpy as np

# パス設定
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "core"))
sys.path.insert(0, str(_ROOT))

from config import NRMOConfig
from world_models import World, WorldType
from engines import V71Engine


WORLD_TYPE_MAP = {
    "Normal": WorldType.NORMAL,
    "FastExpansion": WorldType.FAST_EXPANSION,
    "Vulnerable": WorldType.VULNERABLE,
    "Stagnation": WorldType.STAGNATION,
    "Race": WorldType.RACE,
}


def _run_one_long(args):
    """1 run の long-horizon 実行
    
    記録するもの:
      - 各 checkpoint での state (生存中のみ)
      - ruin 時刻 (発生したなら)
      - 最終 score
    """
    engine_type, world_name, horizon, seed, checkpoints = args
    
    if engine_type == "v7.1":
        engine = V71Engine()
    elif engine_type == "v8":
        from v8_engine import V8Engine
        from rng_manager import RNGManager
        rng_mgr = RNGManager(master_seed=seed)
        engine = V8Engine(rng_manager=rng_mgr, enable_meta_log=False)
    else:
        raise ValueError(f"Unknown engine: {engine_type}")
    
    world = World(WORLD_TYPE_MAP[world_name], seed=seed)
    
    # 記録
    checkpoint_scores = {}
    ruin_step: Optional[int] = None
    is_ruined = False
    
    for t in range(horizon):
        if engine_type == "v8":
            decision = engine.select_action_v8(world.state) if hasattr(engine, 'select_action_v8') else None
            if decision is None:
                # V8Engine の場合は decide() で
                d = engine.decide(world.state)
                if d.action is None:
                    action = engine.strong_engine.select_action(world.state)
                else:
                    action = d.action
            else:
                action = decision
        else:
            action = engine.select_action(world.state)
        
        _, reward, done, _ = world.step(action)
        if hasattr(engine, 'update_reward'):
            engine.update_reward(action, reward)
        
        if (t + 1) in checkpoints:
            checkpoint_scores[t + 1] = world.state.cumulative_score
        
        if done:
            ruin_step = t + 1
            is_ruined = True
            break
    
    return {
        "engine": engine_type,
        "world": world_name,
        "seed": seed,
        "checkpoint_scores": checkpoint_scores,
        "final_score": world.state.cumulative_score,
        "is_ruined": is_ruined,
        "ruin_step": ruin_step,
        "completed_steps": world.state.t,
    }


def survival_curve(ruin_steps: List[Optional[int]], 
                    max_horizon: int,
                    eval_points: List[int]) -> Dict[int, float]:
    """Kaplan-Meier 風の生存曲線
    
    Returns: {checkpoint: survival_rate}
    """
    n_total = len(ruin_steps)
    if n_total == 0:
        return {p: 0.0 for p in eval_points}
    
    survival = {}
    for point in eval_points:
        # この時点でまだ ruin していない数
        alive = sum(1 for rs in ruin_steps if rs is None or rs > point)
        survival[point] = alive / n_total
    return survival


def time_to_ruin_stats(ruin_steps: List[Optional[int]], 
                        max_horizon: int) -> Dict:
    """破滅までの時間の統計
    
    生存した run は max_horizon として扱う (censored)
    """
    if not ruin_steps:
        return {}
    
    # 実際に ruin した run のみ
    actual_ruins = [rs for rs in ruin_steps if rs is not None]
    n_ruined = len(actual_ruins)
    n_survived = len(ruin_steps) - n_ruined
    
    # All-run (censored at max_horizon)
    all_times = [rs if rs is not None else max_horizon for rs in ruin_steps]
    
    return {
        "n_total": len(ruin_steps),
        "n_ruined": n_ruined,
        "n_survived": n_survived,
        "ruin_rate": n_ruined / len(ruin_steps),
        "survival_rate": n_survived / len(ruin_steps),
        "median_time_to_ruin_among_ruined": (
            float(np.median(actual_ruins)) if actual_ruins else None
        ),
        "p25_time_to_ruin": (
            float(np.percentile(actual_ruins, 25)) if actual_ruins else None
        ),
        "p75_time_to_ruin": (
            float(np.percentile(actual_ruins, 75)) if actual_ruins else None
        ),
        "median_time_all_runs_censored": float(np.median(all_times)),
    }


def survival_separated_stats(results: List[Dict],
                               checkpoints: List[int]) -> Dict:
    """生存 run と破滅 run を分離した checkpoint 統計
    
    監査指摘 5: 「途中破滅後の値を plateau 扱いしない」
    → 生存中の run のみで checkpoint 統計を計算
    """
    stats = {}
    for cp in checkpoints:
        alive_scores = []
        for r in results:
            # この checkpoint まで生きていた run のみ
            if r["ruin_step"] is None or r["ruin_step"] > cp:
                if cp in r["checkpoint_scores"]:
                    alive_scores.append(r["checkpoint_scores"][cp])
        
        if alive_scores:
            stats[cp] = {
                "n_alive": len(alive_scores),
                "median": float(np.median(alive_scores)),
                "mean": float(np.mean(alive_scores)),
                "std": float(np.std(alive_scores)),
                "p25": float(np.percentile(alive_scores, 25)),
                "p75": float(np.percentile(alive_scores, 75)),
            }
        else:
            stats[cp] = {
                "n_alive": 0,
                "median": None,
                "mean": None,
                "std": None,
                "p25": None,
                "p75": None,
            }
    
    return stats


def run_v8_long_run(config: NRMOConfig,
                     worlds: List[str] = None,
                     engines: List[str] = None,
                     max_horizon: int = 2000,
                     checkpoints: List[int] = None,
                     n_runs: int = 100) -> Dict:
    """V8 Long Run 再設計版"""
    worlds = worlds or ["Normal", "Vulnerable", "Stagnation"]
    engines = engines or ["v7.1", "v8"]
    checkpoints = checkpoints or [100, 200, 500, 1000, 1500, 2000]
    checkpoints = [c for c in checkpoints if c <= max_horizon]
    
    print("=" * 70)
    print("V8 Long Run Validation (re-designed)")
    print("=" * 70)
    print(f"Worlds: {worlds}")
    print(f"Engines: {engines}")
    print(f"Max horizon: {max_horizon}")
    print(f"Checkpoints: {checkpoints}")
    print(f"Runs/cell: {n_runs}")
    
    all_results = {}
    start = time.time()
    
    for world in worlds:
        all_results[world] = {}
        for engine_type in engines:
            print(f"\n[{world} / {engine_type}]")
            cell_start = time.time()
            
            args_list = [
                (engine_type, world, max_horizon, seed + 50000, checkpoints)
                for seed in range(n_runs)
            ]
            
            with ProcessPoolExecutor(max_workers=config.n_workers) as executor:
                results = list(executor.map(_run_one_long, args_list))
            
            # 新指標を計算
            ruin_steps = [r["ruin_step"] for r in results]
            
            ttr_stats = time_to_ruin_stats(ruin_steps, max_horizon)
            checkpoint_alive = survival_curve(ruin_steps, max_horizon, checkpoints)
            separated_stats = survival_separated_stats(results, checkpoints)
            
            elapsed = time.time() - cell_start
            
            all_results[world][engine_type] = {
                "time_to_ruin_stats": ttr_stats,
                "checkpoint_survival_rate": checkpoint_alive,
                "separated_checkpoint_stats": separated_stats,
                "n_runs": n_runs,
                "elapsed_sec": elapsed,
            }
            
            # 簡易レポート
            print(f"  ruin_rate: {ttr_stats['ruin_rate']:.1%}")
            print(f"  survival_rate: {ttr_stats['survival_rate']:.1%}")
            if ttr_stats['median_time_to_ruin_among_ruined']:
                print(f"  median_time_to_ruin (ruined only): "
                       f"{ttr_stats['median_time_to_ruin_among_ruined']:.0f}")
            print(f"  checkpoint survival:")
            for cp, rate in checkpoint_alive.items():
                print(f"    t={cp}: {rate:.1%} alive")
            print(f"  ({elapsed:.1f}s)")
    
    total_elapsed = time.time() - start
    print(f"\nTotal elapsed: {total_elapsed:.1f}s")
    
    # 比較サマリー
    print(f"\n{'='*70}")
    print(f"COMPARISON (v8 vs v7.1)")
    print(f"{'='*70}")
    print(f"{'World':<15} {'Metric':<25} {'v7.1':>10} {'v8':>10}")
    print("-" * 70)
    
    for world in worlds:
        v71_stats = all_results[world].get("v7.1", {}).get("time_to_ruin_stats", {})
        v8_stats = all_results[world].get("v8", {}).get("time_to_ruin_stats", {})
        
        # 生存率比較
        s71 = v71_stats.get("survival_rate", 0)
        s8 = v8_stats.get("survival_rate", 0)
        print(f"{world:<15} {'survival_rate':<25} {s71:>10.1%} {s8:>10.1%}")
        
        # Time to ruin
        t71 = v71_stats.get("median_time_to_ruin_among_ruined") or 0
        t8 = v8_stats.get("median_time_to_ruin_among_ruined") or 0
        print(f"{world:<15} {'median_time_to_ruin':<25} {t71:>10.0f} {t8:>10.0f}")
        
        # Checkpoint 1000 alive
        s71_1000 = all_results[world].get("v7.1", {}).get(
            "checkpoint_survival_rate", {}).get(1000, 0)
        s8_1000 = all_results[world].get("v8", {}).get(
            "checkpoint_survival_rate", {}).get(1000, 0)
        print(f"{world:<15} {'alive_at_t1000':<25} {s71_1000:>10.1%} {s8_1000:>10.1%}")
    
    return {
        "phase": "5_v8",
        "max_horizon": max_horizon,
        "checkpoints": checkpoints,
        "n_runs": n_runs,
        "worlds": worlds,
        "engines": engines,
        "results": all_results,
        "total_elapsed_sec": total_elapsed,
    }


def _convert_for_json(obj):
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _convert_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_for_json(v) for v in obj]
    return obj


if __name__ == "__main__":
    cfg = NRMOConfig.from_env(n_workers=4)
    
    # 軽量版で動作確認
    summary = run_v8_long_run(
        cfg,
        worlds=["Normal", "Vulnerable"],
        engines=["v7.1", "v8"],
        max_horizon=500,
        checkpoints=[100, 200, 300, 400, 500],
        n_runs=30,
    )
    
    output_path = cfg.results_dir / "v8_long_run_results.json"
    with open(output_path, "w") as f:
        json.dump(_convert_for_json(summary), f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved: {output_path}")
