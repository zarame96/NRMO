# World Simulation v5.0 — Design Document

## 二層フレーム

このプロジェクトは **2 つの並行する開発線** を持つ:

### Reality Track (v5.0 Stage 1 — 動くコード)
**目標**: CPU/GPU 1枚 (非力環境) で動く 10万人プロトタイプ
**実装**: Python + numpy ベクトル化
**期待実行時間**: 1 simulation = 数分以内
**目的**: Telescope Architecture の正しさ検証 + 動く demo

### Vision Track (LaTeX 章として記載)
**目標**: 10 億 agent + 全機能 (multi-world, individual layer, cultural modules,
inter-civilisation interaction, theory pluralism, random events, counterfactual)
**実装**: 「本来こうあるべき」を LaTeX/PDF に明文化
**目的**: 将来の自分・他者がこの研究の野心を理解できる、設計的志向の永久保存

両者を**意図的に分離**することで、現実に動かせる範囲と理想形が混同されない。
これは Zarame さんの一貫した "honest claim regimen" の延長。

## v5.0 Stage 1 の機能範囲

### IN scope (実装する)
- World Generator: 5 world types (Normal Earth, Science-Heavy, Religion-Heavy, Mix, Accelerated-Tech)
- 10万人 agent (vectorised numpy)
- 8 strategies (v4.1 そのまま流用)
- Telescope Architecture (Spotlight + Background)
- Individual layer (主役 1 人の人生 chronicle)
- Strategy distribution sweep (世界によりどの理論が支配的か)
- Random Event Catalog (15-20 events)

### OUT of scope (Vision のみ)
- 10 億 agent (1000x scale)
- Cultural modules (Japan のみ実装、他は spec 化)
- Inter-civilisation interaction (single civ のみ)
- 反事実史モード (Vision で記述、Stage 1 では実装簡略)
- Belief / Ideology layer (Stage 1 では theory 多様性で代用)
- Memetic dynamics (Vision のみ)

### MINI scope (Stage 1 で簡易実装)
- Multi-civ: 1 civilisation の中で「文化的差異のあるサブグループ」として扱う
- Individual life events: 主役のみ詳細、他は family-level summary
- Decision theory pluralism: 8 戦略を agent に分布で割り当て (簡易 pluralism)

## 計算量目標

| Item | 目標 |
|---|---:|
| Total agents | 100,000 |
| Time horizon | 50 generations |
| Vectorisation | numpy fully |
| Single run | < 10 minutes on CPU |
| Memory | < 4 GB |

## アーキテクチャ概観

```
World Generator
  ├─ Normal Earth          (基準: v4.1 の Japan parameters)
  ├─ Science-Heavy         (technology curve 加速、religion 効果弱化)
  ├─ Religion-Heavy        (faith ベース shock buffer 強化、science 抑制)
  ├─ Mix                   (科学+宗教 両方強)
  └─ Accelerated-Tech      (産業革命 1500年に前倒し)

Agent Population (100k)
  ├─ Spotlight (1 person)         — Individual layer detailed
  ├─ Family of spotlight (~20)    — Family-level full
  ├─ Active circle (~1,000)       — Mid-detail
  └─ Background (~99,000)         — Cohort-aggregated

Random Event Catalog
  ├─ Natural   (volcano, earthquake, drought, plague)
  ├─ Tech      (printing, steam, electricity, antibiotics)
  ├─ Political (revolution, dynasty change, war)
  └─ Cultural  (religion arrival, ideology spread)

Strategy Distribution
  各 agent は確率分布で戦略を割り当てられる
  Default: NRMO 30% / EVMax 20% / RA 20% / Faith 10% / Drift 10% / Imitation 10%
  World により分布変動 (Religion-Heavy では Faith 30%, NRMO 15%)
```

## Stage 1 → 将来 Stage への ladder

| Stage | Agent 数 | 機能 | Memory | 時間 |
|---|---:|---|---:|---:|
| **Stage 1 (v5.0)** | **100k** | **Vector ops** | 4 GB | 10 min |
| Stage 2 (v5.5) | 1M | + Individual layer 拡張 | 16 GB | 30 min |
| Stage 3 (v6.0) | 10M | + Cultural modules + Inter-civ | 64 GB | 2 hr |
| Stage 4 (v7.0) | 100M | + GPU CUDA 加速 | 128 GB | 4 hr |
| Stage 5 (v∞) | **1B** | **Full Telescope + 全機能** | 256 GB | 12 hr |

## 評価指標

各 simulation 後に出力する:

1. **主役の人生 chronicle** (1 人物 80 年 day-by-day)
2. **主役家系図** (本家+分家+養子先 50世代)
3. **文明 trajectory** (R, E, G, O, K, X over time)
4. **Strategy performance heatmap** (世界 × 戦略)
5. **Random event log** (この世界線で起きたこと)
6. **反事実比較** (この事件がなかったら主役の運命はどう変わったか)

## Honest Claims (再掲)

- このシミュレーションは **モデル内確率** であり、歴史実証データではない
- 数値の絶対値ではなく **戦略間の相対比較・世界間の相対比較** を解釈の主軸
- Spotlight 人物の "人生" は架空であり、特定の歴史人物を再現するものではない
- "Vision" 部分は実装されておらず、設計的志向の記録である
