"""
NRMO v7.2 FINAL — research reference implementation specification

Phase 1-6 を経て確定された v7.2 の最終仕様。

採用された 10/22 機能:
  Invariants (1): I8 (推定値補正禁止)
  HOLD (2): H2, H5 (Vision明示, スケール明示)
  Gates (7): G1, G2, G3, G6, G7, G8, G9
            (単位, 内的一貫性, 物理上限, 不確実性単調性,
             反例テスト, レイヤー越境, 助言性)

撤回された 12 機能:
  Invariants: I9, I10, I11, I12
  HOLD: H1, H3, H4, H6, H7
  Gates: G4, G5, G10

Phase 5 Long Run で全 5 worlds で plateau 改善確認 (+4.97 total):
  Normal:        13.549 → 16.104  (+2.554)
  FastExpansion:  5.922 →  6.393  (+0.471)
  Vulnerable:     1.371 →  1.578  (+0.207)
  Stagnation:    14.608 → 14.779  (+0.171)
  Race:           7.207 →  8.773  (+1.566)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ablation'))

from ablation_engine import AblatableV72Engine, FeatureFlags, ALL_FEATURES


# Phase 3 で発見、Phase 4-5 で確認された最適機能サブセット
FINAL_V72_FEATURES = ["I8", "H2", "H5", "G1", "G2", "G3", "G6", "G7", "G8", "G9"]

# 撤回された機能のリスト
DROPPED_FEATURES = [f for f in ALL_FEATURES if f not in FINAL_V72_FEATURES]


def build_final_v72_engine(delta: float = 0.01):
    """確定された v7.2 仕様のエンジンを構築"""
    flags = FeatureFlags.all_off()
    for f in FINAL_V72_FEATURES:
        setattr(flags, f, True)
    
    return AblatableV72Engine(flags=flags, delta=delta)


def get_final_specification():
    """最終仕様の構造化情報"""
    return {
        "version": "v7.2_final",
        "based_on": "v7.1",
        "philosophy": "オールパーフェクト・ブルーオーシャン",
        "active_features": FINAL_V72_FEATURES,
        "dropped_features": DROPPED_FEATURES,
        "n_active": len(FINAL_V72_FEATURES),
        "n_dropped": len(DROPPED_FEATURES),
        "feature_breakdown": {
            "invariants": [f for f in FINAL_V72_FEATURES if f.startswith("I")],
            "holds": [f for f in FINAL_V72_FEATURES if f.startswith("H")],
            "gates": [f for f in FINAL_V72_FEATURES if f.startswith("G")],
        },
        "key_insight": (
            "Gates が主役: 採用 10 機能のうち 7 個が Calibration Gate。"
            "I8 (補正禁止) が最重要。"
            "HOLD は最小限 (H2/H5 のみ)。"
            "Invariants は I8 だけで十分。"
        ),
        "long_run_validation": {
            "Normal": {"v71": 13.549, "v72": 16.104, "improvement": 2.554},
            "FastExpansion": {"v71": 5.922, "v72": 6.393, "improvement": 0.471},
            "Vulnerable": {"v71": 1.371, "v72": 1.578, "improvement": 0.207},
            "Stagnation": {"v71": 14.608, "v72": 14.779, "improvement": 0.171},
            "Race": {"v71": 7.207, "v72": 8.773, "improvement": 1.566},
            "total_improvement": 4.969,
            "plateau_violations": 0,
            "ruin_violations": 0,
        },
        "phase_summary": {
            "phase0": "DESIGN: 全体方針、不変条件、HOLD、Gate、検証プロトコル",
            "phase1": "BASELINE: v5.0/v7.1/v7.2 の特性化 (45 cells × 1K runs)",
            "phase2": "ABLATION: 22 機能の個別 LOI/LOO 評価 (92 cells)",
            "phase3": "OPTIMIZATION: Greedy + SA で最適 10 機能発見 (59 evals)",
            "phase4": "VALIDATION: 全 15 cells で完全検証 (11/15 Pareto, 10/15 strict)",
            "phase5": "LONG_RUN: H=2000 で plateau 検証 (5/5 worlds 改善, +4.97)",
            "phase6": "JUDGMENT: 4 条件チェック (C2/C3/C4 pass, C1 要本番検証)",
        },
        "production_readiness": {
            "design_complete": True,
            "implementation_complete": True,
            "quick_test_passed": True,
            "production_run_required": True,
            "production_recommendation": (
                "Phase 5 で全 5 worlds で plateau 改善確認済み。"
                "Phase 4 の n=400 noise で Pareto 11/15 だが、"
                "本番 n=100K で全 cells Pareto pass 見込み。"
                "Colab Pro+ で 6-12 時間の最終検証推奨。"
            ),
        },
    }


def print_final_spec():
    """最終仕様を表示"""
    spec = get_final_specification()
    
    print("=" * 70)
    print(f"NRMO {spec['version'].upper()} — Final Specification")
    print("=" * 70)
    print(f"Based on: {spec['based_on']}")
    print(f"Philosophy: {spec['philosophy']}")
    
    print(f"\nActive features ({spec['n_active']}/22):")
    breakdown = spec["feature_breakdown"]
    print(f"  Invariants ({len(breakdown['invariants'])}): "
            f"{', '.join(breakdown['invariants'])}")
    print(f"  HOLD ({len(breakdown['holds'])}): "
            f"{', '.join(breakdown['holds'])}")
    print(f"  Gates ({len(breakdown['gates'])}): "
            f"{', '.join(breakdown['gates'])}")
    
    print(f"\nDropped features ({spec['n_dropped']}):")
    print(f"  {', '.join(spec['dropped_features'])}")
    
    print(f"\nKey insight:")
    print(f"  {spec['key_insight']}")
    
    print(f"\nLong Run Validation (Phase 5):")
    for world, data in spec["long_run_validation"].items():
        if isinstance(data, dict):
            print(f"  {world:<15}: v7.1={data['v71']:6.3f} → "
                    f"v7.2={data['v72']:6.3f} (+{data['improvement']:.3f})")
    print(f"  {'Total improvement':<15}: "
            f"+{spec['long_run_validation']['total_improvement']:.3f}")
    print(f"  Plateau violations: "
            f"{spec['long_run_validation']['plateau_violations']}")
    print(f"  Ruin violations: "
            f"{spec['long_run_validation']['ruin_violations']}")
    
    print(f"\nProduction Readiness:")
    for k, v in spec["production_readiness"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    # 仕様表示
    print_final_spec()
    
    # 最終 spec を JSON 化
    import json
    spec = get_final_specification()
    
    with open("./FINAL_V72_SPECIFICATION.json", "w") as f:
        json.dump(spec, f, indent=2)
    
    print(f"\nSaved: FINAL_V72_SPECIFICATION.json")
    
    # 実際にエンジンを構築できることを確認
    print(f"\n--- Engine instantiation test ---")
    engine = build_final_v72_engine()
    print(f"Engine created: {type(engine).__name__}")
    print(f"Active features: {len(engine.flags.active_features())}/22")
    print(f"Feature list: {sorted(engine.flags.active_features())}")
