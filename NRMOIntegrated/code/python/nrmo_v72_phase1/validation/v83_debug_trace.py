"""
validation/v83_debug_trace.py

V8.3 の早期破滅原因デバッグ.
1 run を step ごとに記録し、どこで何が起きているかを honest に見る.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT / "core"))
sys.path.insert(0, str(_ROOT / "phase8"))
sys.path.insert(0, str(_ROOT / "phase9"))
sys.path.insert(0, str(_ROOT / "phase10"))
sys.path.insert(0, str(_ROOT / "phase11"))

from chaotic_world import ChaoticWorld, ChaosConfig
from world_models import Action
from engines import V71Engine
from v83_engine import V83Engine
from rng_manager import RNGManager


def debug_v71(seed=42, chaos_level="moderate", horizon=50):
    print("=" * 70)
    print(f"V7.1 trace (chaos={chaos_level}, seed={seed})")
    print("=" * 70)
    
    config = ChaosConfig.from_level(chaos_level)
    world = ChaoticWorld(config, seed=seed)
    engine = V71Engine()
    
    actions_used = []
    for t in range(horizon):
        observed = world.observe()
        action = engine.select_action(observed)
        actions_used.append(f"{action.intent}/{action.strength}")
        
        state_before = (world.state.R, world.state.E, world.state.O, world.state.X)
        reward, done, info = world.step(action)
        engine.update_reward(action, reward)
        
        if t < 15:
            evt = ",".join(info["events"]) if info["events"] else "-"
            print(f"  t={t+1:2d}: {action.intent:7s}/{action.strength} "
                  f"r={reward:+.2f}  "
                  f"R{state_before[0]:.0f}→{world.state.R:.0f} "
                  f"E{state_before[1]:.0f}→{world.state.E:.0f} "
                  f"O{state_before[2]:.0f}→{world.state.O:.0f} "
                  f"X{state_before[3]:.0f}→{world.state.X:.0f}  "
                  f"[{evt[:30]}]")
        
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    from collections import Counter
    act_counter = Counter(actions_used)
    print(f"\n  Total: score={world.state.cumulative_score:.2f}, steps={t+1}")
    print(f"  Action distribution: {act_counter.most_common()}")


def debug_v83(seed=42, chaos_level="moderate", horizon=50):
    print("=" * 70)
    print(f"V8.3 trace (chaos={chaos_level}, seed={seed})")
    print("=" * 70)
    
    config = ChaosConfig.from_level(chaos_level)
    world = ChaoticWorld(config, seed=seed)
    
    rng_mgr = RNGManager(master_seed=seed + 500000)
    engine = V83Engine(rng_manager=rng_mgr, enable_meta_log=False)
    
    actions_used = []
    knightian_count = 0
    shinobi_override_count = 0
    pp_intervention_count = 0
    
    for t in range(horizon):
        observed = world.observe()
        engine.last_state = observed
        
        decision = engine.decide(observed)
        action = decision.action if decision.action else Action(intent="hold", strength="A")
        actions_used.append(f"{action.intent}/{action.strength}")
        
        # trace 解析
        knightian_layer = next((e for e in decision.trace.entries 
                                  if e.layer == "knightian"), None)
        if knightian_layer and knightian_layer.data.get("is_knightian"):
            knightian_count += 1
        
        mf_layer = next((e for e in decision.trace.entries 
                           if e.layer == "multi_framework"), None)
        shinobi_override = mf_layer.data.get("shinobi_override") if mf_layer else False
        if shinobi_override:
            shinobi_override_count += 1
        
        if decision.status == "INTERVENED":
            pp_intervention_count += 1
        
        state_before = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                         "O": world.state.O, "K": world.state.K, "X": world.state.X}
        sb = (world.state.R, world.state.E, world.state.O, world.state.X)
        reward, done, info = world.step(action)
        state_after = {"R": world.state.R, "E": world.state.E, "G": world.state.G,
                        "O": world.state.O, "K": world.state.K, "X": world.state.X}
        engine.update_reward(action, reward, state_before, state_after)
        
        if t < 15:
            evt = ",".join(info["events"]) if info["events"] else "-"
            pp_score = decision.passive_pattern_proposal.score if decision.passive_pattern_proposal else 0
            veto = decision.veto_classification.veto_type.value if decision.veto_classification else "-"
            shinobi_marker = "S" if shinobi_override else " "
            knigt_marker = "K" if knightian_layer and knightian_layer.data.get("is_knightian") else " "
            print(f"  t={t+1:2d}: {action.intent:7s}/{action.strength} "
                  f"r={reward:+.2f}  "
                  f"R{sb[0]:.0f}→{world.state.R:.0f} "
                  f"O{sb[2]:.0f}→{world.state.O:.0f} "
                  f"X{sb[3]:.0f}→{world.state.X:.0f}  "
                  f"PP={pp_score:.2f} V={veto[:4]} {shinobi_marker}{knigt_marker}  "
                  f"[{evt[:25]}]")
        
        if done:
            print(f"  RUINED at step {t+1}")
            break
    
    from collections import Counter
    act_counter = Counter(actions_used)
    print(f"\n  Total: score={world.state.cumulative_score:.2f}, steps={t+1}")
    print(f"  Action distribution: {act_counter.most_common()}")
    print(f"  Knightian fired: {knightian_count}/{t+1}")
    print(f"  Shinobi override: {shinobi_override_count}/{t+1}")
    print(f"  PP intervention: {pp_intervention_count}/{t+1}")
    
    # Decision pipeline 内訳分析: 候補生成と最終 action の差
    candidates_dist = Counter()
    final_dist = act_counter
    
    # 1 step 詳細 (最後の decision)
    if decision.action:
        print(f"\n  Last decision layers:")
        for ent in decision.trace.entries:
            print(f"    [{ent.layer}] {ent.status}")


def compare_v71_v83_same_seed(seed=42, chaos_level="moderate", horizon=30):
    """同じ seed で v7.1 と v8.3 を実行、何が違うか観察"""
    print("=" * 70)
    print(f"v7.1 vs v8.3 SAME SEED ({chaos_level}, seed={seed})")
    print("=" * 70)
    
    # v7.1
    config1 = ChaosConfig.from_level(chaos_level)
    world1 = ChaoticWorld(config1, seed=seed)
    engine1 = V71Engine()
    
    # v8.3
    config2 = ChaosConfig.from_level(chaos_level)
    world2 = ChaoticWorld(config2, seed=seed)
    rng_mgr = RNGManager(master_seed=seed + 500000)
    engine2 = V83Engine(rng_manager=rng_mgr, enable_meta_log=False)
    
    print(f"\n{'step':>4} {'v71_action':>12} {'v71_R':>6} {'v71_X':>6} {'v83_action':>12} {'v83_R':>6} {'v83_X':>6}")
    print("-" * 70)
    
    v71_done = False
    v83_done = False
    
    for t in range(horizon):
        if not v71_done:
            obs1 = world1.observe()
            a1 = engine1.select_action(obs1)
            r1, d1, _ = world1.step(a1)
            engine1.update_reward(a1, r1)
            v71_done = d1
            v71_act = f"{a1.intent}/{a1.strength}"
            v71_R = f"{world1.state.R:.0f}"
            v71_X = f"{world1.state.X:.0f}"
        else:
            v71_act = "RUINED"
            v71_R = "-"
            v71_X = "-"
        
        if not v83_done:
            obs2 = world2.observe()
            engine2.last_state = obs2
            d = engine2.decide(obs2)
            a2 = d.action if d.action else Action(intent="hold", strength="A")
            sb = {"R": world2.state.R, "E": world2.state.E, "G": world2.state.G,
                   "O": world2.state.O, "K": world2.state.K, "X": world2.state.X}
            r2, dn, _ = world2.step(a2)
            sa = {"R": world2.state.R, "E": world2.state.E, "G": world2.state.G,
                   "O": world2.state.O, "K": world2.state.K, "X": world2.state.X}
            engine2.update_reward(a2, r2, sb, sa)
            v83_done = dn
            v83_act = f"{a2.intent}/{a2.strength}"
            v83_R = f"{world2.state.R:.0f}"
            v83_X = f"{world2.state.X:.0f}"
        else:
            v83_act = "RUINED"
            v83_R = "-"
            v83_X = "-"
        
        if v71_done and v83_done:
            break
        
        print(f"{t+1:>4} {v71_act:>12} {v71_R:>6} {v71_X:>6} {v83_act:>12} {v83_R:>6} {v83_X:>6}")
    
    print(f"\nv7.1 score: {world1.state.cumulative_score:.2f}")
    print(f"v8.3 score: {world2.state.cumulative_score:.2f}")


if __name__ == "__main__":
    # Mild chaos で v7.1 と v8.3 を比較
    compare_v71_v83_same_seed(seed=42, chaos_level="mild", horizon=20)
    print()
    debug_v83(seed=42, chaos_level="mild", horizon=15)
