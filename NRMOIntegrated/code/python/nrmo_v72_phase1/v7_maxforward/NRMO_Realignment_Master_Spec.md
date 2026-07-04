# NRMO 再配置設計原則書 (Realignment Master Spec)
## 「civ-sim 側」とされた全内容を「現実側」へ — 全修整の single source of truth

作成日: 2026-05-29
位置づけ: 全 Python / C++ / LaTeX / PDF / DecisionCompass 修整の唯一の指針
根拠: 設計者による構造訂正 — StrongEngine Ω Full は現実側、MaxForwardEngine が civ-sim 側

---

## 0. 転換の核心 (一文)

```
旧 (誤): NRMO は civ-sim (文明シミュレーション) を中心に最適化する。
         StrongEngine Ω Full は civ-sim 内の engine。

新 (正): NRMO は現実を中心に動く。StrongEngine Ω Full が現実側の主役で、
         あらゆる探索・推論・意思決定を行う (範囲無制限)。
         civ-sim は MaxForwardEngine が StrongEngine Ω Full を模倣し、
         死を恐れず極端を試して最善スコアを算出する "実験場" にすぎない。
```

これまで「civ-sim 側で動く」と記述・実装されてきた component の大半は、
**実際には現実側で動くもの** だった。これを全面的に再配置する。

---

## 1. 全 component 再配置マッピング

| component | 旧位置 (誤) | 新位置 (正) | 根拠 |
|---|---|---|---|
| **StrongEngine Ω Full** (`OmegaFullEngine`, vnext_plus.py) | civ-sim engine | **現実側・主役** | 現実 domain の真の dynamics で最大前進 |
| **Loom layer** (Loom Core / Loom Layer) | civ-sim 補助 | **現実側** | 破滅境界の定義は現実側の governance |
| Wolf Pursuit / Edge Guard | civ-sim 内 | **現実側** | StrongEngine Ω Full の一機能 |
| Mutation / Synthesis / Invention | civ-sim 内 | **現実側** | StrongEngine Ω Full の候補生成 |
| **DomainAdapter** (store/investment/romance) | 現実 | **現実側 (不変)** | もともと現実 domain |
| `world_sim_v50/*` (文明動態) | civ-sim そのもの | **現実 domain の一つ** | 「文明」も StrongEngine が動く現実 domain |
| `collective_engine_v71` / `nrmo_collective_v70` | civ-sim 集団 | **現実側** | 集団動態も現実側の対象 |
| MAPLayer / Norn・Skuld / Shinobi Engine | civ-sim 内 | **現実側** | 履歴管理・task 管理・能動修正は現実側 |
| Thompson Sampling 学習器 | civ-sim 内 | **現実側** | 現実の学習 |
| **MaxForwardEngine** | (未定義/混同) | **civ-sim 側 (唯一)** | StrongEngine を模倣する実験場の engine |

```
要約:
  現実側  = StrongEngine Ω Full + Loom layer + DomainAdapter +
            world_sim(=文明domain) + collective + MAPLayer/Norn/Skuld/Shinobi +
            学習器 … つまり「これまで civ-sim とされた殆ど全て」
  civ-sim 側 = MaxForwardEngine のみ (StrongEngine Ω Full の模倣・極端探索)
```

---

## 2. 接続原則 (双方向)

```
[現実側]                              [civ-sim 側]
StrongEngine Ω Full ──依頼(探索)──→  MaxForwardEngine
  ・現実 domain で最大前進               ・StrongEngine を模倣
  ・破滅は避ける                        ・死/破滅を許容 (フィードバック)
  ・Loom layer が破滅境界を定義          ・極端な慎重は排除
  ・あらゆる domain (範囲無制限)         ・攻撃ピーク/防御ピーク算出
       ↑                                ・最善スコアを算出
       └──────結果(最善・ピーク)────────┘
  双方向: 現実の実行結果 → civ-sim の次探索に蓄積
```

正式実装は `v7_two_layer.py`:
- 現実側 = `StrongEngineOmegaFull`
- civ-sim 側 = `MaxForwardEngine`
- 双方向 bridge = `observe()` / `feedback()`

---

## 3. 修整指針 — 文書 (LaTeX)

各 architecture 章を、本原則に従って書き換える。

| 章 | 現状 | 修整内容 |
|---|---|---|
| `ch20_strong_engine.tex` | StrongEngine を civ-sim engine として記述 | **現実側の主役**として記述。範囲無制限の探索・推論 |
| `ch_part9_omega_full.tex` | Ω Full を civ-sim 最適化器 | 現実 domain で最大前進する engine |
| `ch_part_xiii_v63_vnext_plus.tex` | vnext_plus = civ engine | 現実側 engine の実装詳細 |
| `ch_part_xiii_v70_collective.tex` | collective = civ-sim 集団 | 現実側の集団動態 |
| `ch27_time_horizon.tex` | civ-sim の時間地平 | 現実の意思決定地平 + civ-sim は探索地平 |
| `ch30_success_definitions.tex` | civ-sim スコア | 現実=破滅回避最大前進 / civ-sim=ピーク探索 |
| `ch_part12_methodology.tex` | civ-sim 方法論 | 二層構造の方法論 (現実 ⇄ civ-sim) |

追加すべき新章: **「二層構造 (現実 StrongEngine Ω Full / civ-sim MaxForwardEngine)」**

---

## 4. 修整指針 — コード (Python / C++)

| ファイル群 | 修整内容 |
|---|---|
| `vnext_plus.py` (OmegaFullEngine) | 現実側 StrongEngine として位置づけ。rollout は対象 domain の真の dynamics を使う (内部 civ-sim 固定を排除) — 第4原則 |
| `world_sim_v50/*` | 「文明」を現実 domain の一つとして DomainDynamics 化 |
| `collective_engine_*` / `nrmo_collective_*` | 現実側集団動態として接続 |
| `nrmo_universal_adapter.py` | 現実 DomainAdapter (不変、action_spectrum 追加済み) |
| `v7_two_layer.py` (新・正本) | 二層構造の中核。全 engine はこれに接続 |
| `v7_adapters.py` (新・正本) | 各現実 domain の DomainDynamics |

原則: **engine の rollout は必ず対象の真の dynamics で行う**。
civ-sim 固定 dynamics を内部に持たせない (第4原則)。

---

## 5. 修整指針 — DecisionCompass

```
DecisionCompass は「現実の個人意思決定アプリ」= 完全に現実側。
  ・搭載 engine = StrongEngine Ω Full (現実 domain = 個人の意思決定)
  ・civ-sim (MaxForwardEngine) を内部に持ち、選択肢の極端を試して最善を算出
  ・ユーザーに見せるのは「破滅しない最大前進」の提案
修整: nrmo_core 系を二層構造 (現実 StrongEngine / civ-sim MaxForward) に接続し直す。
```

---

## 6. 段階的実行計画 (正直な進め方)

```
本作業は 151+ Python / 90+ LaTeX / 複数 PDF / DecisionCompass に及び、
1 セッションでの完全修整は物理的に不可能。本原則書を指針に段階実行する。

Phase A [完了] 本再配置原則書 (single source of truth)
Phase B [完了] 中核コード v7_two_layer.py / v7_adapters.py
Phase C        LaTeX architecture 章 (§3 の表) を順次修整
Phase D        world_sim / collective / vnext_plus を §4 に従い再接続
Phase E        DecisionCompass を §5 に従い修整
Phase F        全体を 1 パッケージに統合し PDF 再生成
```

---

## 7. 不変の核 (転換後も変わらないもの)

```
・不可逆破滅 (absorbing ruin) は避ける
・governance と execution の分離 (Loom が境界、StrongEngine が前進)
・最大前進 + 縁での方向転換 (NRMO Constitution v7)
・停滞は ruin として排除
```

転換したのは **engine の配置 (どこが現実でどこが civ-sim か)** であって、
NRMO の価値原則そのものではない。

---

## 8. Phase D 詳細 — collective_engine の二層構造接続設計

collective_engine_v71 / nrmo_collective_v70 は「集団 (多 agent 文明) の動態」であり、
Zarameさん の構造では **現実側**。核心は `CollectiveStrongEngine` (集団版 StrongEngine)。

```
[現実側] CollectiveStrongEngine
  集団全体を最大前進させる。破滅の縁で triage / insurance で方向転換 (止まらない)。
  ・action_spectrum = 集団の攻撃(全体成長) 〜 防御(triage退避) の連続
  ・最大前進 default、停滞 (全体保身) は排除
  ・破滅の縁 (shock 接近) では triage_rescue / MultiTierInsurance で
    「集団を守りながら前進」(止めるのではなく方向転換)

[civ-sim 側] 集団 MaxForwardEngine
  集団の極端 (全攻撃 / 全防御) を死を恐れず試し、集団の最善構成を算出。
  ・invent_configurations で構成を探索
  ・score_collective_candidate で評価
  ・極端な慎重 (過剰 triage) は排除、但し世界が防御最善ならそれを発見 (世界依存性)

[接続]
  forecast_next_shock → 破滅の縁の検出 (detect_edge 相当)
  compute_triage_scores → 縁での方向転換の具体 (誰を守りながら前進するか)
  CollectiveStrongEngine.decide → 集団の最大前進 action

[評価地平]
  文明 domain と同じく長期評価が必須 (短期だと過度な triage = 過度な防御に倒れる)。
```

### 接続手順 (実装時)
```
1. CollectiveEngineState を二層構造の state として扱う
2. 集団 action_spectrum (全体成長率 × triage 強度) を定義
3. civstate ベースでなく集団 dynamics を transition に使う (第4原則)
4. 長期評価地平で civ-sim 探索 → 現実 CollectiveStrongEngine が最善で前進
5. shock 予測を detect_edge に、triage を縁での方向転換に接続
```

注: 実コードの完全接続は段階実行。本節がその指針 (single source of truth)。
