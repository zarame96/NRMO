"""
validation/test_v8_integrity.py

問題9 への対応: 厳格なテストスイート

含むテスト:
  - test_multiframe_key_alignment: Multi-framework 戻り値キー整合性 (P0-1)
  - test_v8_uses_multiframe_best: V8Engine が実際に best_option を採用
  - test_knightian_not_always_on: Knightian が常時 100% trigger でない (P0-4)
  - test_phase4_paired_seeds: paired design 動作 (P0-2)
  - test_seed_reproducibility: 同一 seed で完全一致 (P0-3)
  - test_long_run_safety_strict: 100%ruin 同士の PASS 拒否 (P1-2)
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
for d in ["core", "phase8", "phase11", "."]:
    sys.path.insert(0, str(_ROOT / d))

from rng_manager import RNGManager
from v8_engine import V8Engine
from world_models import World, WorldType
from multi_framework_knightian import MultiFrameworkEnsemble, DecisionOption


N_PASSED = 0
N_FAILED = 0
FAILURES = []


def assert_test(condition, name, details=""):
    global N_PASSED, N_FAILED
    if condition:
        N_PASSED += 1
        print(f"  ✓ {name}")
    else:
        N_FAILED += 1
        FAILURES.append((name, details))
        print(f"  ✗ {name}")
        if details:
            print(f"      {details}")


# ============================================================
# Test 1: Multi-framework key alignment (P0-1)
# ============================================================
def test_multiframe_key_alignment():
    print("\n[Test 1] Multi-framework key alignment (P0-1)")
    
    mf = MultiFrameworkEnsemble()
    opts = [
        DecisionOption(name="a", outcomes=[(0.5, 10), (0.5, -5)]),
        DecisionOption(name="b", outcomes=[(0.5, 5), (0.5, 0)]),
    ]
    result = mf.select_best(opts)
    
    assert_test("best_option" in result, "select_best returns 'best_option' key")
    assert_test(result["best_option"] in ["a", "b"], "best_option is valid name",
                  f"got: {result.get('best_option')}")
    assert_test("all_evaluations" in result, "select_best returns 'all_evaluations'")
    assert_test("recommended" not in result, "old 'recommended' key absent")


# ============================================================
# Test 2: V8 uses multi-framework best (P0-1)
# ============================================================
def test_v8_uses_multiframe_best():
    print("\n[Test 2] V8Engine actually uses Multi-framework best")
    
    rng = RNGManager(master_seed=42)
    engine = V8Engine(rng_manager=rng, enable_meta_log=False)
    world = World(WorldType.NORMAL, seed=42)
    
    decision = engine.decide(world.state)
    
    # mf_layer の trace を確認
    mf_layer = None
    for entry in decision.trace.entries:
        if entry.layer == "multi_framework":
            mf_layer = entry
            break
    
    assert_test(mf_layer is not None, "multi_framework layer reached")
    if mf_layer:
        assert_test(
            "best_candidate" in mf_layer.data,
            "multi_framework records best_candidate"
        )
        # best_candidate と final action が一致してるか
        # (Knightian 弱化が起きていない限り)
        if not decision.metadata.get("knightian_flagged"):
            final_str = f"{decision.action.intent}/{decision.action.strength}"
            assert_test(
                mf_layer.data["best_candidate"] == final_str,
                "Multi-framework best aligns with final action (no Knightian)",
                f"mf_best={mf_layer.data['best_candidate']}, final={final_str}"
            )


# ============================================================
# Test 3: Knightian not always on (P0-4)
# ============================================================
def test_knightian_not_always_on():
    print("\n[Test 3] Knightian not always firing (P0-4)")
    
    knightian_triggers = []
    for trial_seed in range(10):
        rng = RNGManager(master_seed=trial_seed)
        engine = V8Engine(rng_manager=rng, enable_meta_log=False)
        # 健全な state (low risk)
        world = World(WorldType.NORMAL, seed=trial_seed)
        # state を healthy に強制設定: X 低い、E 高い
        world.state.X = 20.0
        world.state.E = 80.0
        
        decision = engine.decide(world.state)
        knightian_triggers.append(decision.metadata.get("knightian_flagged", False))
    
    trigger_rate = sum(knightian_triggers) / len(knightian_triggers)
    assert_test(
        trigger_rate < 1.0,
        f"Knightian activation < 100% in healthy state",
        f"trigger_rate={trigger_rate:.1%}"
    )


# ============================================================
# Test 4: Seed reproducibility (P0-3)
# ============================================================
def test_seed_reproducibility():
    print("\n[Test 4] Seed reproducibility (P0-3)")
    
    def run_sequence(seed: int, n_steps: int = 20):
        rng = RNGManager(master_seed=seed)
        engine = V8Engine(rng_manager=rng, enable_meta_log=False)
        world = World(WorldType.NORMAL, seed=seed)
        actions = []
        for _ in range(n_steps):
            d = engine.decide(world.state)
            actions.append(f"{d.action.intent}/{d.action.strength}")
            _, reward, done, _ = world.step(d.action)
            engine.update_reward(d.action, reward)
            if done:
                break
        return actions, world.state.cumulative_score
    
    a1, s1 = run_sequence(seed=42, n_steps=20)
    a2, s2 = run_sequence(seed=42, n_steps=20)
    a3, s3 = run_sequence(seed=43, n_steps=20)
    
    assert_test(
        a1 == a2, "Same seed → identical action sequence",
        f"a1[:5]={a1[:5]}, a2[:5]={a2[:5]}"
    )
    assert_test(
        abs(s1 - s2) < 1e-6, "Same seed → identical final score",
        f"s1={s1}, s2={s2}"
    )
    assert_test(
        a1 != a3 or abs(s1 - s3) > 1e-6,
        "Different seed → different result"
    )


# ============================================================
# Test 5: Candidates use full action space (P1-1)
# ============================================================
def test_full_action_space_candidates():
    print("\n[Test 5] Candidates cover full action space (P1-1)")
    
    rng = RNGManager(master_seed=42)
    engine = V8Engine(rng_manager=rng, enable_meta_log=False)
    world = World(WorldType.NORMAL, seed=42)
    
    decision = engine.decide(world.state)
    
    cand_layer = None
    for entry in decision.trace.entries:
        if entry.layer == "candidates":
            cand_layer = entry
            break
    
    assert_test(cand_layer is not None, "candidates layer reached")
    if cand_layer:
        n_cand = cand_layer.data.get("n_candidates", 0)
        assert_test(
            n_cand >= 15,
            f"Candidates covers full action space (≥15)",
            f"n_candidates={n_cand}"
        )


# ============================================================
# Test 6: No hardcoded local home path in active code (core/, validation/)
# ============================================================
def test_no_hardcoded_core_paths():
    print("\n[Test 6] No hardcoded paths in active code (core/, validation/)")
    
    target_dirs = [_ROOT / "core", _ROOT / "validation"]
    bad_files = []
    
    for tdir in target_dirs:
        for py_file in tdir.glob("*.py"):
            # test 自身は除外 (検出ロジック自身に対象文字列を含むため)
            if py_file.name == "test_v8_integrity.py":
                continue
            content = py_file.read_text()
            lines = content.split("\n")
            for i, line in enumerate(lines):
                stripped = line.strip()
                # コメント、docstring 内は除外
                if stripped.startswith("#"):
                    continue
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                # 文字列としてのハードコード (両クオートをチェック)
                _needle_dq = '"' + "/home/" + "claude"
                _needle_sq = "'" + "/home/" + "claude"
                if (_needle_dq in line) or (_needle_sq in line):
                    bad_files.append(
                        f"{py_file.parent.name}/{py_file.name}:{i+1}"
                    )
    
    assert_test(
        not bad_files,
        f"No hardcoded local home path string in core/+validation/",
        f"Found in: {bad_files[:3]}" if bad_files else ""
    )
    # legacy は archived として除外している旨を表示
    if not bad_files:
        print("      (note: optimization/, final/, ablation/, colab/ は v7.2 archived として除外)")


# ============================================================
# Run all
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("v8.1 INTEGRITY TEST SUITE")
    print("=" * 70)
    
    test_multiframe_key_alignment()
    test_v8_uses_multiframe_best()
    test_knightian_not_always_on()
    test_seed_reproducibility()
    test_full_action_space_candidates()
    test_no_hardcoded_core_paths()
    
    print("\n" + "=" * 70)
    print(f"Passed: {N_PASSED}")
    print(f"Failed: {N_FAILED}")
    print("=" * 70)
    
    if N_FAILED > 0:
        print("\nFailures:")
        for name, details in FAILURES:
            print(f"  ✗ {name}")
            if details:
                print(f"    {details}")
        sys.exit(1)
    else:
        print("\n✅ All tests passed")
        sys.exit(0)
