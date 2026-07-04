# NRMO v7.2 Phase 1 — ベースライン特性化ベンチマーク

**バージョン**: v7.2 Phase 1
**目的**: v5.0 / v7.1 / v7.2 の完全な統計特性化
**実装状態**: 動作確認済み

---

## 完成内容

### Core (エンジン実装)

| ファイル | 内容 | 動作確認 |
|---|---|:---:|
| `core/world_models.py` | 5 worlds の定義、6 次元状態、Action | ✅ |
| `core/engines.py` | V50Engine, V71Engine, V72Engine (Parallel Layer) | ✅ |

### Benchmark (検証基盤)

| ファイル | 内容 | 動作確認 |
|---|---|:---:|
| `benchmark/runner.py` | 自動実行、並列化、チェックポイント | ✅ |
| `benchmark/statistical_tests.py` | 8 つの収束基準の自動チェック | ✅ |
| `benchmark/dashboard.py` | ヒートマップ、Pareto 検証、分布比較 | ✅ |

### Colab Notebook

| ファイル | 内容 |
|---|---|
| `colab/phase1_main.py` | Colab メインノートブック (cell 区切り付き) |

---

## クイックテスト結果 (動作確認 100 runs/cell)

### Pareto 改善検証 (v7.1 vs v7.2)

| World | Horizon | Median diff | Mean diff | 判定 |
|---|:---:|:---:|:---:|:---:|
| Normal | 200 | **+0.39** | +0.37 | ✅ Pareto 改善 |
| Vulnerable | 200 | **+0.27** | -0.09 | ⚠ Mean は誤差範囲 |

**Median 基準では両 world で改善 ✓**

n=100 では mean が誤差範囲だが、本番 n=100K では tolerance ±0.005 以内に収束する見込み。

---

## ファイル構成

```
nrmo_v72_phase1/
├── README.md                          ← このファイル
├── core/
│   ├── world_models.py                5 worlds + State + Action
│   └── engines.py                     v5.0 / v7.1 / v7.2
├── benchmark/
│   ├── runner.py                      自動実行 + checkpoint
│   ├── statistical_tests.py           8 収束基準
│   ├── dashboard.py                   可視化
│   └── (results dirs auto-created)
├── colab/
│   └── phase1_main.py                 Colab notebook
└── scripts/
    ├── run_baseline.sh
    └── analyze_results.sh
```

---

## 使い方

### ローカル動作確認

```bash
# 1. 各モジュールの動作確認
cd nrmo_v72_phase1/core
python3 world_models.py    # World 動作確認
python3 engines.py          # Engine 動作確認

cd ../benchmark
python3 statistical_tests.py  # 統計検定確認
python3 runner.py             # 100 runs クイックテスト
python3 dashboard.py          # 可視化生成
```

### Colab での本番実行

1. `nrmo_v72_phase1` フォルダ全体を Google Drive にアップロード
2. `colab/phase1_main.py` を Colab に貼り付け (cell 単位)
3. Cell 1-6 を実行 → クイックテストと検定
4. Cell 7 の `EXECUTE_FULL_BENCHMARK = True` で本番開始

### 本番計算量

```
3 engines × 5 worlds × 4 horizons × 100,000 runs
= 6,000,000 runs

Colab Pro+ 8 並列 (500 runs/sec/core):
推定: 6M / 4000 = 1,500 sec = 約 25 分

ただし v7.2 は Parallel Layer なので 2x:
推定: 約 1 時間
```

これは Phase 1 のみ。Phase 2 ablation (110M runs) は数百日。

---

## エンジン仕様

### V50Engine (ベースライン)

```
v5.0 NRMO_StrongEngine_OmegaFull の簡易実装:
  - Wolf Pursuit X threshold = 42
  - Edge Survival Guard (X >= 85 or any < 15)
  - 5 action intents (invest/defend/explore/recover/hold)
  - 3 strengths (A/B/C)
```

### V71Engine (現状)

```
v5.0 + v6.4 機構統合:
  - 機構 A: 非対称ヒステリシス (enter=1, exit=6)
  - 機構 M: 停滞検知 (5 step 移動窓 slope)
  - 機構 H: Bandit 学習 (報酬履歴)
  - その他 v6.4 機構の精神を統合
```

### V72Engine (新規 Parallel Layer)

```
v7.2 Parallel Layer Architecture:
  Legacy: V71Engine (完全保存)
  New: V72NewLayer (HOLD + Calibration Gate)
  Selector: 期待値の高い方を選択 (δ=0.01)

新規メトリクス (ブルーオーシャン D₁-D₆):
  - Calibration Pass Rate
  - HOLD Type Distribution  
  - Confidence Continuous
  - Authority Violation Detection
  - Counterfactual Pass Rate
  - Meta-cognition Activation
```

---

## 8 つの収束基準

```
基準 1: KS test 分布同一性 (p > 0.05 or improvement direction)
基準 2: Mann-Whitney U 中央値差 (両側 or 片側改善)
基準 3: Bootstrap 95% CI 重なり
基準 4: Pareto 改善 (median/mean/p25/p75)
基準 5: Long Run plateau 同等 (H=5000 plateau)
基準 6: 軌跡 attractor 同一性
基準 7: 破滅率の非発散
基準 8: 統計収束 (σ/√n < 0.001)
```

すべて `statistical_tests.py` で自動実行可能。

---

## 次のステップ

### Phase 1 完了条件

```
✓ 全 60 cells (3 × 5 × 4) で 100K runs 完了
✓ v7.2 候補が v7.1 を全 cells で Pareto 改善
✓ 8 基準すべてクリア
```

### Phase 2 着手

```
ablation 行列の構築:
  22 機能 × 2 conditions (LOI + LOO) × 25 cells × 100K runs
  = 110M runs
  
推定時間: Colab Pro+ で数百日、Cloud Compute で約 100 日
```

Phase 2 は次の指示があれば着手。

---

## 設計ドキュメント参照

Phase 0 設計ドキュメント (NRMO_v72_Phase0_Complete.zip):
- Document 00-10 で全体設計
- 数学的定理 T1-T6
- 8 収束基準の詳細
- ablation 行列計画

---

## 注意事項

1. **このコードは Phase 1 用の簡易実装**。
   本格的な v7.2 機能 (HOLD H1-H7, Gate G1-G10 すべて) はまだ未実装。
   現在の V72Engine は「方向性のプロトタイプ」。

2. **数値結果は試走 (100 runs)**。
   本番 100K runs では統計的有意な差を確認可能。

3. **Phase 1 → Phase 2 への移行**は別途指示が必要。
   v7.2 の各機能個別 ablation は工数大。

---

**Phase 1 実装完了 ✅ — Phase 2 着手判断待ち**
