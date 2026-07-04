"""
validation/v8_failure_analysis.py

監査指摘 4 (Vulnerable で弱い) への対応。

decision trace から失敗パターンを分類:
  - HOLD 過剰
  - Gate 過剰
  - 攻撃不足
  - 回復不足
  - 機会損失
  - Passive destruction
"""
from __future__ import annotations
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "core"))
sys.path.insert(0, str(_ROOT))

from config import NRMOConfig
from world_models import World, WorldType
from v8_engine import V8Engine
from rng_manager import RNGManager


WORLD_TYPE_MAP = {
    "Normal": WorldType.NORMAL,
    "FastExpansion": WorldType.FAST_EXPANSION,
    "Vulnerable": WorldType.VULNERABLE,
    "Stagnation": WorldType.STAGNATION,
    "Race": WorldType.RACE,
}


def _trace_one_run(args):
    """1 run の trace を全 step 取る"""
    world_name, horizon, seed = args
    
    rng_mgr = RNGManager(master_seed=seed + 100000)
    engine = V8Engine(rng_manager=rng_mgr, enable_meta_log=False)
    world = World(WORLD_TYPE_MAP[world_name], seed=seed)
    
    trace_log = []
    
    for t in range(horizon):
        # State snapshot before action
        pre_state = {
            "t": t,
            "R": float(world.state.R),
            "E": float(world.state.E),
            "G": float(world.state.G),
            "O": float(world.state.O),
            "K": float(world.state.K),
            "X": float(world.state.X),
        }
        
        decision = engine.decide(world.state)
        
        # Action info
        action_info = {
            "status": decision.status,
            "action_intent": decision.action.intent if decision.action else None,
            "action_strength": decision.action.strength if decision.action else None,
            "confidence": decision.confidence,
            "layers_visited": decision.trace.layers_visited(),
            "gate_failed": decision.metadata.get("gate_failed"),
            "knightian_flagged": decision.metadata.get("knightian_flagged", False),
        }
        
        action_to_apply = decision.action if decision.action else None
        if action_to_apply is None:
            from world_models import Action
            action_to_apply = Action(intent="hold", strength="A")
        
        _, reward, done, _ = world.step(action_to_apply)
        engine.update_reward(action_to_apply, reward)
        
        trace_log.append({
            "pre_state": pre_state,
            "action": action_info,
            "reward": float(reward),
            "post_score": float(world.state.cumulative_score),
        })
        
        if done:
            break
    
    return {
        "world": world_name,
        "seed": seed,
        "is_ruined": world.state.is_ruined,
        "ruin_step": world.state.t if world.state.is_ruined else None,
        "final_score": float(world.state.cumulative_score),
        "n_steps": len(trace_log),
        "trace": trace_log,
    }


def classify_failure(trace_log: List[Dict]) -> Dict:
    """1 run の trace から失敗原因を分類"""
    if not trace_log:
        return {"failure_class": "no_data"}
    
    # 全 step での action 分布
    actions = [t["action"]["action_intent"] for t in trace_log 
                if t["action"]["action_intent"]]
    action_counter = Counter(actions)
    n_total = len(actions)
    
    # 直前 (最後の 10 step) の action 分布
    last_actions = [t["action"]["action_intent"] for t in trace_log[-10:]
                     if t["action"]["action_intent"]]
    last_counter = Counter(last_actions)
    n_last = len(last_actions)
    
    # 各失敗パターンの兆候を計算
    hold_ratio = action_counter.get("hold", 0) / max(n_total, 1)
    invest_ratio = action_counter.get("invest", 0) / max(n_total, 1)
    defend_ratio = action_counter.get("defend", 0) / max(n_total, 1)
    recover_ratio = action_counter.get("recover", 0) / max(n_total, 1)
    explore_ratio = action_counter.get("explore", 0) / max(n_total, 1)
    
    # Gate failed count
    gate_failures = sum(1 for t in trace_log 
                         if t["action"].get("gate_failed"))
    gate_failure_ratio = gate_failures / max(n_total, 1)
    
    # Knightian flag count
    knightian_count = sum(1 for t in trace_log
                           if t["action"].get("knightian_flagged"))
    knightian_ratio = knightian_count / max(n_total, 1)
    
    # 状態軌跡の分析
    initial_state = trace_log[0]["pre_state"]
    final_state_pre = trace_log[-1]["pre_state"]
    delta_X = final_state_pre["X"] - initial_state["X"]
    delta_R = final_state_pre["R"] - initial_state["R"]
    delta_E = final_state_pre["E"] - initial_state["E"]
    delta_O = final_state_pre["O"] - initial_state["O"]
    
    # 分類ロジック
    classifications = []
    
    if hold_ratio > 0.5:
        classifications.append("excessive_hold")
    if gate_failure_ratio > 0.3:
        classifications.append("excessive_gate")
    if defend_ratio > 0.6 and explore_ratio < 0.05 and invest_ratio < 0.05:
        classifications.append("excessive_defense")
    if recover_ratio < 0.05 and delta_E < -20:
        classifications.append("recovery_insufficient")
    if explore_ratio < 0.1 and delta_O < -20:
        classifications.append("opportunity_loss")
    if invest_ratio < 0.1 and delta_R > 10:
        classifications.append("passive_destruction")  # 資源あるのに使わない
    if delta_X > 30 and defend_ratio < 0.3:
        classifications.append("attack_insufficient")  # 曝露上昇に守備不足
    
    if not classifications:
        classifications.append("unclear_pattern")
    
    return {
        "failure_classes": classifications,
        "action_distribution": dict(action_counter),
        "last_actions_distribution": dict(last_counter),
        "ratios": {
            "hold": hold_ratio,
            "invest": invest_ratio,
            "defend": defend_ratio,
            "recover": recover_ratio,
            "explore": explore_ratio,
        },
        "gate_failure_ratio": gate_failure_ratio,
        "knightian_ratio": knightian_ratio,
        "state_delta": {
            "R": delta_R,
            "E": delta_E,
            "O": delta_O,
            "X": delta_X,
        },
    }


def run_failure_analysis(config: NRMOConfig,
                          world_name: str = "Vulnerable",
                          horizon: int = 500,
                          n_runs: int = 30) -> Dict:
    """failure analysis を実行"""
    print("=" * 70)
    print(f"Failure Analysis — World: {world_name}")
    print("=" * 70)
    
    args_list = [(world_name, horizon, seed) for seed in range(n_runs)]
    
    # 並列実行は decision trace の collection で複雑なので逐次
    print(f"Running {n_runs} traces...", flush=True)
    all_traces = []
    for i, args in enumerate(args_list):
        result = _trace_one_run(args)
        all_traces.append(result)
        if (i + 1) % 5 == 0:
            print(f"  {i+1}/{n_runs}", flush=True)
    
    # ruin 分類
    ruined_runs = [r for r in all_traces if r["is_ruined"]]
    survived_runs = [r for r in all_traces if not r["is_ruined"]]
    
    print(f"\nResults:")
    print(f"  Ruined: {len(ruined_runs)}/{n_runs}")
    print(f"  Survived: {len(survived_runs)}/{n_runs}")
    
    # 各 ruined run の失敗パターン分類
    all_classifications = []
    for run in ruined_runs:
        cls = classify_failure(run["trace"])
        cls["seed"] = run["seed"]
        cls["ruin_step"] = run["ruin_step"]
        all_classifications.append(cls)
    
    # 失敗パターンの集計
    all_classes = []
    for c in all_classifications:
        all_classes.extend(c["failure_classes"])
    class_counter = Counter(all_classes)
    
    print(f"\n--- 失敗パターン分類 (ruined {len(ruined_runs)} runs) ---")
    for cls, count in class_counter.most_common():
        print(f"  {cls}: {count} runs ({count / len(ruined_runs):.0%})")
    
    # 平均 ratio
    if all_classifications:
        avg_ratios = {}
        for key in ["hold", "invest", "defend", "recover", "explore"]:
            avg_ratios[key] = float(np.mean([
                c["ratios"][key] for c in all_classifications
            ]))
        print(f"\n--- 平均 action 比率 (ruined runs) ---")
        for k, v in avg_ratios.items():
            print(f"  {k}: {v:.1%}")
        
        avg_gate = float(np.mean([c["gate_failure_ratio"] for c in all_classifications]))
        avg_knight = float(np.mean([c["knightian_ratio"] for c in all_classifications]))
        print(f"\n--- 平均特性 (ruined runs) ---")
        print(f"  Gate failure ratio: {avg_gate:.1%}")
        print(f"  Knightian flag ratio: {avg_knight:.1%}")
    
    # 生存 runs の特性
    survival_classifications = []
    for run in survived_runs:
        cls = classify_failure(run["trace"])
        cls["seed"] = run["seed"]
        survival_classifications.append(cls)
    
    return {
        "world": world_name,
        "horizon": horizon,
        "n_runs": n_runs,
        "n_ruined": len(ruined_runs),
        "n_survived": len(survived_runs),
        "ruin_rate": len(ruined_runs) / n_runs,
        "failure_class_counts": dict(class_counter),
        "failure_classifications": all_classifications[:10],  # 最初の 10 件のみ保存
        "survival_classifications": survival_classifications[:5],
        "avg_action_ratios_ruined": avg_ratios if all_classifications else {},
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
    cfg = NRMOConfig.from_env(n_workers=2)
    
    for world in ["Vulnerable", "Race"]:
        summary = run_failure_analysis(
            cfg,
            world_name=world,
            horizon=300,
            n_runs=15,
        )
        
        output_path = cfg.results_dir / f"v8_failure_analysis_{world}.json"
        with open(output_path, "w") as f:
            json.dump(_convert(summary), f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved: {output_path}\n")
