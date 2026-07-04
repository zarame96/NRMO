# NRMO v7.2 Phase 3 — Combination Optimization

**バージョン**: v7.2 Phase 3
**目的**: 22 機能の最適サブセット探索 (組み合わせ最適化)

---

## Phase 3 で実施したこと

### Implementation

| ファイル | 内容 |
|---|---|
| `evaluator.py` | 機能サブセット → World 別 Pareto 改善スコア計算 |
| `optimizer.py` | Greedy Forward + Backward + Simulated Annealing |
| `visualize.py` | 最適化履歴と最終選定の可視化 |

### 探索手法

```
探索空間: 2^22 = 4,194,304 組み合わせ
→ 全探索不可

採用アルゴリズム:
  Phase A: Greedy Forward Selection (機能を 1 つずつ追加)
  Phase B: Greedy Backward Elimination (削除で改善)
  Phase C: Simulated Annealing (ランダム摂動)

評価関数:
  composite_score = total_improvement - 5*violations 
                  + 0.1*strict_improvements - 0.01*n_active
```

---

## 発見された最適サブセット (Quick Test)

### 採用された 10/22 機能

```
Invariants (1):
  ✓ I8  (推定値補正禁止) — 最重要

HOLD (2):
  ✓ H2  (Vision 明示)
  ✓ H5  (スケール明示)

Gates (7):
  ✓ G1  (単位整合性)
  ✓ G2  (内的一貫性)
  ✓ G3  (物理上限)
  ✓ G6  (不確実性単調性)
  ✓ G7  (反例テスト)
  ✓ G8  (レイヤー越境)
  ✓ G9  (助言性)
```

### 撤回された 12 機能

```
Invariants (4): I9, I10, I11, I12
HOLD (5): H1, H3, H4, H6, H7
Gates (3): G4, G5, G10
```

これらは Phase 2 の「LOO_ONLY」または「LOI_ONLY」カテゴリで、
組み合わせ評価では効果を発揮しなかった。

### 最適化メトリクス (n=80 quick test)

```
Composite score: -2.242
Pareto violations: 1 (Vulnerable で誤差範囲)
Strict improvements: 2 (FastExpansion + Normal)
Total improvement: +2.668 (3 worlds 合計)
Evaluations: 59 / 4,194,304 (0.0014% 探索済)
```

---

## Phase 2 vs Phase 3 の差分

| 機能 | Phase 2 判定 | Phase 3 最終判定 |
|---|---|---|
| I8 | KEEP | ✅ 採用 |
| I11 | KEEP | ❌ 撤回 (Phase 3 で削除しても改善) |
| H2 | KEEP | ✅ 採用 |
| H5 | LOO_ONLY | ✅ 追加採用 |
| G6 | LOO_ONLY | ✅ 追加採用 |
| G1, G2, G3, G7, G8, G9 | KEEP | ✅ 採用 |

Phase 3 で **I11 撤回 + H5/G6 採用** という新しい知見が得られた。

---

## 重要な含意

### 含意 1: I8 が確定的に最重要

両 Phase で一致:
- Phase 2: LOI +0.450 / LOO +0.406 (両指標トップ)
- Phase 3: 最適サブセットに必ず含まれる

→ **「推定値に補正を加えない」が v7.2 の核心**

### 含意 2: 機能間の動的相互作用

```
I11 (レイヤー責任不可侵):
  Phase 2 LOI/LOO 単独評価では KEEP 判定
  Phase 3 組み合わせ評価では撤回
  
理由: 他機能が同等の効果を提供
  (G8 がレイヤー越境を検出するため I11 不要)
```

これは ablation の限界 (単独では分からない相互作用) を示す。

### 含意 3: Gates が主役

採用 10 機能のうち 7 個が Gate:
```
G1, G2, G3, G6, G7, G8, G9 → 採用
G4, G5, G10 → 撤回
```

**Calibration Gate こそが v7.2 の主要な改善ポイント**。

---

## 性能

```
1 evaluation:
  worlds=3, horizons=1, n_runs=80
  → 約 2-3 秒
  
Greedy Forward 15 iterations × ~22 candidates per step:
  最大 330 evaluations
  
Backward 同様

Total evaluations: 59 (early termination で削減)
Total elapsed: 約 3 分

本番 n=100K:
  1 evaluation: 約 30 分
  Greedy 完走: 約 1 週間
```

---

## Phase 3 の限界

### 限界 1: Quick test の noise

```
n=80 では std が大きく、最適点が安定しない
本番 n=100K で確定的な結果が得られる
```

### 限界 2: Greedy の local optimum

```
Greedy は local optimum に陥る可能性
Simulated Annealing で escape を試みる
本番では複数 starting points で並列実行が必要
```

### 限界 3: 評価関数の重み

```
composite = total - 5*violations + 0.1*strict - 0.01*n_active

5 (violation penalty): 厳しすぎるとよい候補も排除
0.1 (strict bonus): 弱すぎる
0.01 (simplicity): 機能数を減らす圧力
  → 重み調整は要 Phase 4
```

---

## 次のステップ (Phase 4 着手判断)

### Phase 4: 全機能統合検証

```
Phase 3 で発見した「最適 10 機能」を:
  本番 n=100K runs × 5 worlds × 4 horizons で完全検証
  
8 つの収束基準を全 cells で実行
合格 → v7.2 採用判定
```

### Phase 5: Long Run 収束検証

```
horizon = 5000 まで延長
plateau 値の比較
attractor 同一性
```

### Phase 6: 最終判定

```
4 条件 (PARETO, STRICT, CONVERGENT, BLUE_OCEAN) チェック
v7.2 採用 or 部分撤回判断
```

---

## 使い方

```bash
cd nrmo_v72_phase1/optimization

# Evaluator 単独テスト
python3 evaluator.py

# 最適化実行 (Quick test, 約 3 分)
python3 optimizer.py

# 結果可視化
python3 visualize.py
```

本番 (Colab Pro+):

```python
from evaluator import CombinationEvaluator
from optimizer import CombinationOptimizer

evaluator = CombinationEvaluator(
    worlds=["Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"],
    horizons=[200, 500, 1000, 2000],
    n_runs=10000,  # 本番は 100,000
    n_workers=8,
)
evaluator.precompute_baseline()

optimizer = CombinationOptimizer(evaluator)
result = optimizer.hybrid(max_iterations_each=30)
```

---

**Phase 3 実装完了 ✅ — Phase 4 着手判断待ち**
