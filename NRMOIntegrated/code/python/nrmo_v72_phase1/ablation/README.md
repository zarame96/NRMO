# NRMO v7.2 Phase 2 — Ablation Matrix

**バージョン**: v7.2 Phase 2
**目的**: 22 機能の個別貢献度を測定し、最適な機能セットを発見

---

## Phase 2 で実施したこと

### Implementation

| ファイル | 内容 |
|---|---|
| `ablation_engine.py` | 機能フラグ付き V72Engine + FeatureFlags |
| `ablation_runner.py` | LOI/LOO の自動実行 (46 conditions × cells) |
| `ablation_analysis.py` | 効果サイズ計算、貢献度ランキング、ヒートマップ |

### 22 機能の ablation

```
Invariants (5): I8, I9, I10, I11, I12
HOLD (7): H1, H2, H3, H4, H5, H6, H7
Gates (10): G1, G2, G3, G4, G5, G6, G7, G8, G9, G10

Conditions:
  BASELINE_v71: All OFF
  FULL_v72: All ON
  LOI_X (22): Feature X のみ ON
  LOO_X (22): Feature X のみ OFF
  
Total: 46 conditions × 5 worlds × 4 horizons = 920 cells (本番)
```

---

## クイックテストの発見 (n=100 runs)

### Vulnerable (H=200) — 最弱点 world

| Category | Features |
|---|---|
| **KEEP (両方プラス)** | I8, I11, H2, G1, G2, G3, G7, G8, G9 (9 機能) |
| **LOO_ONLY** (組み合わせで価値) | I9, H1, H3, H5, H6, G4, G5, G6 |
| **LOI_ONLY** (単独で効くが組み合わせで弱化) | I10, I12, H4, G10 |
| **DROP/NEUTRAL** (要再設計) | H7 |

**最重要機能 (両指標トップ)**:
1. **I8** (補正禁止): LOI +0.450 / LOO +0.406
2. **G3** (物理上限): LOI +0.380 / LOO +0.264
3. **G1** (単位整合性): LOI +0.281 / LOO +0.223
4. **G9** (助言性): LOI +0.274 / LOO +0.154
5. **G2** (内的一貫性): LOI +0.027 / LOO +0.220

### Normal (H=200) — 重要な発見

```
Full (v7.2 全機能 ON) - Baseline (v7.1) = -0.71
```

**v7.2 全機能 ON は Normal world で v7.1 より悪化する**!

これは **機能間の負の相互作用** を示す決定的発見。「全部 ON が最適」ではない。

特に G7 (反例テスト):
- LOI: -3.90 (単独では大悪化)
- LOO: +3.45 (抜くと回復)

→ G7 は単独では効かないが、他機能と組み合わせて意味を成す。

---

## 含意

### 含意 1: Phase 3 (組み合わせ最適化) が本質的に重要

「全 22 機能 ON」は最適でない。
最適な機能サブセットを CMA-ES / GP-BO で探索する必要がある。

### 含意 2: World 別最適機能セット

```
Vulnerable では効く機能 ≠ Normal で効く機能

→ 動的に機能セットを切り替える設計 (機構 E 連続モード) が必要かも
→ または、両方で効く機能のみを選別 (intersection)
```

### 含意 3: I8 (補正禁止) が最重要

これは v7.2 の核心思想を裏付ける:
> 「推定値に safety margin を加えない、Vision レイヤーで適用」

数値検証で最強の機能と判明。

### 含意 4: H7 (類似失敗履歴) は再設計が必要

両指標でマイナス → このシミュレーション環境では効果が出ない。
本番では機構 F (失敗記憶) との統合が必要。

---

## 性能

```
ablation 1 cell (n=100): 約 0.5-1.5 秒
92 cells (2 worlds × 1 horizon): 80 秒
本番予測: 22 features × 2 (LOI/LOO) + 2 base = 46 conditions
         × 5 worlds × 4 horizons = 920 cells

n=1000 runs/cell:
  920 cells × 1000 runs / 500 runs/sec = 1840 sec ≈ 30 分

n=100,000 runs/cell (本番):
  920 cells × 100K / 500 runs/sec = 184,000 sec ≈ 51 時間
  Colab Pro+ 8 並列で: 約 6-12 時間
```

期限なし命令下で実行可能。

---

## 使い方

### クイックテスト

```bash
cd nrmo_v72_phase1/ablation
python3 ablation_engine.py          # FeatureFlags + Engine 動作確認
python3 ablation_runner.py          # 92 cells クイック (80秒)
python3 ablation_analysis.py        # 解析 + 可視化
```

### 本番

```python
from ablation_runner import run_full_ablation

run_full_ablation(
    worlds=["Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"],
    horizons=[200, 500, 1000, 2000],
    n_runs=100000,
    n_workers=8,
    checkpoint_dir="./ablation_results_full",
)
```

---

## Phase 3 への引き継ぎ

Phase 2 で得られた知見:

1. **「KEEP」9 機能** は必須採用候補
2. **「LOO_ONLY」8 機能** は組み合わせで採用
3. **「LOI_ONLY」4 機能** は注意 (組み合わせで弱化)
4. **H7 は撤回 or 再設計**

Phase 3 で:
- CMA-ES or GP-BO で組み合わせ最適化
- 機能サブセットの Pareto front 探索
- World 別最適セットの発見

---

**Phase 2 実装完了 ✅ — Phase 3 着手判断待ち**
