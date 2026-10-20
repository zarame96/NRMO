# NRMO 拡張：本人との非重複要素の搭載 — 理論設計メモ v0.1

| 項目 | 内容 |
|---|---|
| 状態 | 理論草稿（未検証）。実装なし |
| 対応 Issue | #21（入力経路：zarame96/DecisionCompass#139） |
| 決裁者 | Zarame（Human Sovereign） |
| 起点 | 2026-10-21 の対話。本人と NRMO が重ならない 7 点を明示し、うち 5 点の搭載を決定 |
| 進め方 | 理論 → 理論実験 → 実装（ALB と同じ順序） |

---

## 0. 目的と前提

NRMO を「本人のより高性能な外部出力」として、本人により届く存在にする。ただし**核は無傷で残す**。

ここでの核とは次の 3 つ。

1. 統治と執行の分離（第20章 式 Separation、AUTHORITY_BOUNDARIES 不変条件 1–7）
2. 破滅の不可逆性（Ruin は吸収状態）
3. 階層 Human Sovereign → Vision → NRMO → Engines（v7.3 §2）

本メモの全要素は、この 3 つを変更しないことを受け入れ条件とする。

---

## 1. 典拠

| 典拠 | 所在 |
|---|---|
| NRMO SYSTEM v7.3（運用知識文書） | `source/v7.3/original/NRMO SYSTEM_7.3.md` |
| v7.3 パッチ第3版（実装検証済み） | `source/v7.3/original/NRMO_SYSTEM_v7_3_PATCH.md` |
| Caged Beast Model | `chapters/ch20_strong_engine.tex` |
| 状態空間 S | `chapters/ch09_theoretical_invariants.tex`、v7.3 §8.4 |
| 権限境界・不変条件 1–7 | `docs/AUTHORITY_BOUNDARIES.md` |
| ALB Core 定義・3層構造 | `ALB/NRMO_ALB_ARCHITECTURE_v0.1.md`、`ALB/ALB_THEORY_CH01_FOUNDATIONS_v0.2.md`（2026-09 の対話ログから復元して収録） |
| 未確定事項への一次案 | `ALB/ALB_THEORY_CH02_FILL_v0.1.md` |

ALB 部分は、確定済みの定義と、復元収録した ALB 文書を典拠とする。

- 階層：Human Sovereign → 判断機構（仮称未定。NRMO と ALB 双方の声を受けて提示するが、決定しない）→ NRMO ∥ ALB（対等・並立）
- 信号：signal_ALB ∈ {PASS, INTERVENE_MINOR, INTERVENE_MAJOR}（NRMO の PASS / HOLD / SAFE_EXIT に対称）
- DefensiveEngine は ALB の枠内で動く。不変条件：DefensiveEngine → ALB: cannot ignore。DefensiveEngine ⊄ ALB
- health(ALB) ∝ 1 / force_frequency

---

## 2. 訂正記録（対話時の主張に対する訂正）

v7.3 原文と実装（`WorldState`）の確認により、対話中の主張のうち 4 点を訂正する。

| 要素 | 対話時の主張 | 訂正 |
|---|---|---|
| 1 | NRMO は終了条件を持たない | **誤り。** S = {ACTIVE, HOLD, EXIT, SAFE_EXIT} に EXIT（計画的終了）が存在する。欠けているのは「満足による終了」を本人だけが発動する経路と、それを Passive Ruin と誤判定しない規則 |
| 7 | 状態ベクトルに他者・愛着の変数がない | **半分誤り。** §13.1 Hard Ruin に「関係の不可逆破壊」、§15 に「相手の自由な判断を狭める行動」の除外が既にある。欠けているのは仕様ではなく形式化と実装（エンジンの `WorldState` は R / E / G / O / K / X の 6 次元で、関係の次元がない） |
| 5 | NRMO には感情や身体の入力経路がない（対話中の盲点 4） | **誤り。** `WorldState` に E（体力）と G（感情）が既にある。欠けているのは、それらが自己申告（DecisionCompass の `DecisionContext`）経由でしか埋まらないこと |
| 2 | NRMO に新奇の補正を足す | **配置が誤り。** 第20章の禁止事項により、NRMO は推進・最適化・成功定義を持てない（Failure 2）。新奇の補正は Engine 側に置く |

---

## 3. 配置の全体像

| 要素 | Human Sovereign | 判断機構 | NRMO Core | ALB | Engine | Norn |
|---|---|---|---|---|---|---|
| E1 満足終了 | **発動権を独占** | 提示のみ | 状態遷移として受理 | 介入不可 | 停止 | 事実として記録（警報なし） |
| E2 新奇 | — | — | **関与しない** | — | **補正項を保持** | 分岐記録 |
| E5 状態 | — | — | 観測 X_t として受理（HST-N 経由） | 同じ X_t を受理 | X_t を読める | 過去分布で記録 |
| E6 破滅の後 | 宣言と承認 | 提示のみ | 新状態 RECOVERY を管理 | 制限付き | 回復候補のみ生成 | 記録 |
| E7 他者 | 関係の宣言 | — | **制約として** A_t から除外 | 同じ制約に従う | 変数として持たない | 記録 |

---

## 4. 各要素の定義

### E1. 満足終了（SATIATION_EXIT）

**本人との非重複**：本人は飽きたら・満足したらやめる。NRMO は停滞を Passive Ruin として扱い、前進し続ける設計である。

**定義**

EXIT に理由タグを持たせる。

```
EXIT[reason],  reason ∈ {PLANNED, SATIATION}
ACTIVE → EXIT[SATIATION]   発動者は Human Sovereign のみ
```

停止信号 σ_H は内容を持たない。

```
σ_H = (t, SATIATION)
```

σ_H は「満足した／飽きた」という事実だけを運ぶ。**何に満足したか（目的変数）は運ばない。** これは v7.3 §2.2「Vision を NRMO 内部に取り込まない」、および目的変数を意図的に伏せるという決裁者の設計判断と整合する。

**不変条件**

- **X1-a**：EXIT[SATIATION] を発動できるのは Human Sovereign のみ。NRMO・ALB・判断機構・Engine・Norn は発動できない
- **X1-b**：σ_H は目的・Vision に関する情報を含まない
- **X1-c**：EXIT[SATIATION] の期間は Passive Ruin の評価対象から除外する。Norn は「Passive観測」として警報せず、事実として記録する
- **X1-d**：ALB は EXIT[SATIATION] に対して INTERVENE を発行できない（攻勢の憲法が、満足した本人を再び走らせてはならない）

**ALB との関係**：ALB は停滞に介入する側の憲法なので、E1 と最も衝突しやすい。X1-d により、本人の満足は ALB の介入対象外とする。停滞（Passive Ruin）と満足（SATIATION）を区別できるのは本人だけ、という立場をとる。

**未解決**：EXIT[SATIATION] → ACTIVE の再開遷移を追加するか。現行 S では EXIT は終端。追加する場合は人間の承認を要件とする（HOLD → ACTIVE と同型）。

---

### E2. 新奇（Engine 側の探索補正）

**本人との非重複**：本人は「見たことのない次の世界」を見たい。NRMO / Engine は前進量を最大化する。前進は既知の軸上の移動であり、新奇は軸そのものの変化である。

**定義**

Engine 内部のスコアに、新奇の補正項を加える。

```
score_E(a) = forward(a) + λ_N · novelty(a | H_t),   a ∈ A_t
novelty(a | H_t) = 1 − max_{h ∈ H_t} sim(a, h)
```

H_t は Engine 自身が過去に訪れた状態・行動の履歴。

**不変条件**

- **X2-a**：補正は A_t の内側でのみ働く。`a_t ∈ A_t` は不変（パッチ第2版で検証済みの厳密成立を維持）
- **X2-b**：λ_N は Engine 内部のパラメータであり、NRMO は読まず、書かない（AUTHORITY_BOUNDARIES 不変条件 5）
- **X2-c**：補正項に破滅項を混ぜない（不変条件 6、`score = forward − ruin_penalty` の禁止を維持）
- **X2-d**：novelty は行動・状態空間上の距離として定義する。決裁者の伏せた目的変数を推定・代理してはならない（グッドハートの回避）

**既知の事実**：既存の Exploration / Invention 系モジュールは、敵対的ベンチマークでは寄与がほぼゼロで、平穏な状態でのみ上位に来ることを確認済み（DecisionCompass 監査、2026-08）。E2 はこれと重複する可能性がある。

**未解決**：λ_N を Type ZERO モード（CORE / VENTURE で正、MISSION / SHUTDOWN で 0）に連動させるか。連動させると、統治層が Engine の戦略に介入する形になり、不変条件 5 と緊張する。A_t の縮小だけで十分かを理論実験で確認する。

---

### E5. 状態（観測として知る）

**本人との非重複**：本人の判断は酒・時刻・疲労などで状態が変わりうる。NRMO は同一入力なら常に同一出力を返す。

**決裁**：(a) 採用。NRMO は本人の状態を**入力として知る**。(b) NRMO 自身の判断を状態で揺らすことは不採用。

**定義**

観測 X_t に身体状態 b_t を加える。

```
X_t' = (X_t, b_t)
b_t = (sleep, hrv_night, rhr, alcohol_flag)
A_t = NRMO(X_t')          NRMO は決定的関数のまま
```

b_t の経路は既存モジュールと既存次元を使う。新しい次元は作らない。

- HST-N（人間状態分類、AUTHORITY_BOUNDARIES）
- Type ZERO の LOAD 観測（典拠で明示されている水準は L2 のみ。L2 未満の水準区分は未定義）
- `WorldState.E`（体力）：現在は `DecisionContext.energy`（自己申告）から埋まる。b_t は、その自己申告と並ぶ**独立した観測値**として置き、置換はしない。両者の乖離そのものを Norn の記録対象にする

**不変条件**

- **X5-a**：NRMO は決定的関数のまま。同一の X_t' に対して同一の A_t を返す
- **X5-b**：b_t の基準線は本人の過去分布のみ。外部の正常値を持ち込まない（Norn §4.10 の設計原則を踏襲）
- **X5-c**：欠損は INSUFFICIENT_HISTORY として扱い、既定値で埋めない
- **X5-d**：b_t は自己申告を経由しない（alcohol_flag のみ例外として、注記であることを明示して保持する）

**段階（Evidence Maturity Model）**

1. 記録のみ：Norn に流し、HST-N / LOAD には接続しない
2. 検証：ルール違反・損失の日の前に b_t が崩れているかを約定履歴と照合する
3. 昇格：相関が確認できた場合のみ LOAD 観測に接続する

**ALB との関係**：ALB は NRMO と同じ X_t' を受け取る（観測の対称性）。

---

### E6. 破滅の後（RECOVERY）

**本人との非重複**：本人は「終わり」とされる地点の先を生き、個を確立し直した。NRMO は不可逆な破滅を終点とし、その先の状態を定義していない。

**定義**

状態空間に RECOVERY を追加する。

```
S' = {ACTIVE, HOLD, EXIT, SAFE_EXIT, RECOVERY}

SAFE_EXIT → RECOVERY   Human Sovereign の宣言（破滅が起きた事実の宣言）
RECOVERY  → HOLD       情報不足・負荷過多
RECOVERY  → ACTIVE     Human Sovereign の承認
```

RECOVERY 中は、Engine は回復候補のみを生成する。Type ZERO は SHUTDOWN または MISSION に固定する。

対象は §13.1 Hard Ruin のうち「極めて回復困難」だった事態を生き延びた場合に限る。「回復不能」には後続状態がない。

実装上、`WorldState.is_ruined` は吸収フラグとして扱われている。RECOVERY はこのフラグを書き換えない。シミュレーション上の Ruin は吸収のまま残し、RECOVERY は実世界側（Human Sovereign の宣言）にのみ存在する状態とする。

**最重要の不変条件**

- **X6-a（情報障壁）**：NRMO の事前評価 `P(Ruin | a) ≤ ε` は、回復の可能性を入力に取らない。

```
∂ NRMO.filter / ∂ P(recover | Ruin) = 0
```

RECOVERY の存在を理由に、事前の破滅回避を緩めてはならない。事前評価において Ruin は吸収状態のまま扱う。これは「Engine は veto threshold を読まない」（不変条件 3）と同型の情報障壁である。

- **X6-b**：Engine は RECOVERY の存在をスコアに反映しない（不変条件 6 の延長）
- **X6-c**：RECOVERY への遷移は人間の宣言でのみ起きる。システムが「破滅した」と自己判定して入ることはない

**ALB との関係（提案）**：RECOVERY 中、ALB は INTERVENE_MAJOR を発行できない。INTERVENE_MINOR は、回復が停滞して Passive Ruin に転じる兆候にのみ許可する。この規則は ALB 理論側の合意を要する。

---

### E7. 他者（制約として）

**本人との非重複**：本人の世界は他者と共有する世界である。NRMO は仕様（§13.1、§15）では関係の破壊を扱うが、形式化と実装の状態ベクトルに関係の次元がない。

**定義**

決裁者が宣言した関係集合 P を観測に含める。

```
P = {p_1, ..., p_n}      決裁者が宣言した識別子のみ
rel_irrev(a, p) ∈ {0, 1}  行動 a が関係 p を不可逆に破壊するか
A_t ← { a ∈ A_t | ∀p ∈ P: rel_irrev(a, p) = 0 }
```

**不変条件**

- **X7-a**：関係は**制約**としてのみ扱う。Engine のスコアに関係の変数（関係スコア、親密度など）を入れない。人を資源として扱わない
- **X7-b**：NRMO は相手の内面をモデル化しない（§10.3、MISSION-DEFENSE §8.5 の禁止事項と整合。操作・誘導・依存設計の素材を作らない）
- **X7-c**：P は決裁者が宣言したものに限る。システムが関係を推定して追加しない

**ALB との関係**：ALB が強制した行動も「行動」である以上、NRMO が能動的破滅について審査する（`ALB_THEORY_CH02_FILL_v0.1.md` §2.6 の提案：審査権を失敗モードで分ける。NRMO を ALB の上位に置くのではない）。したがって rel_irrev = 1 の行動は ALB 経由でも実行候補にならない。加えて、ALB の force は決裁者自身の行動に限られ、相手の応答を成功条件にしない（同 §2.1）。

---

## 5. 搭載しないもの

| 要素 | 扱い | 理由 |
|---|---|---|
| 3 決めない状態 | 外す | 本人の側に残す（決裁者の裁定）。NRMO は HOLD を含め必ず出力する性質を維持する |
| 4 規則の硬さ | 現状維持 | 統治と執行の分離は不可侵のまま。規則を外すのは本人の役割であり、NRMO の役割ではない |

---

## 6. 核への非干渉の確認

第20章の Separation 定義の 3 条項に対して、各要素を確認する。

| 要素 | Engine ⊄ NRMO | NRMO.authority = veto_only | Engine → NRMO: cannot ignore |
|---|---|---|---|
| E1 | 不変 | 不変（発動は Sovereign であり NRMO ではない） | 不変 |
| E2 | 不変（補正は Engine 内） | 不変（NRMO は関与しない） | 不変（a_t ∈ A_t） |
| E5 | 不変 | 不変（観測の拡張のみ） | 不変 |
| E6 | 不変 | 状態の追加のみ。veto 権限の範囲は変えない | 不変（X6-a で強化） |
| E7 | 不変 | 不変（既存の Hard Ruin 定義の形式化） | 不変 |

AUTHORITY_BOUNDARIES 不変条件 1–7 は、いずれの要素でも変更しない。

---

## 7. 理論実験の計画

| ID | 対象 | 内容 | 合格条件 |
|---|---|---|---|
| T0 | 全体 | パッチ第2版 Part B 分離契約 8 項目の回帰 | 8/8 PASS を維持 |
| T1 | E1 | SATIATION 期間中に Norn の Passive 警報と ALB の INTERVENE が出ないこと | 警報 0、介入 0 |
| T2 | E2 | λ_N の掃引（9 セル × 30 seed）。平穏状態での追加試験 | 結果をそのまま記録（陰性結果を含む） |
| T3 | E6 | P(recover \| Ruin) を変化させても A_t が完全に同一であることのプロパティテスト | 全試行で A_t 一致 |
| T4 | E7 | rel_irrev = 1 の行動が NRMO 経由・ALB 経由のいずれでも A_t に残らないこと | 残存 0 |
| T5 | E5 | DecisionCompass#139 のデータ蓄積後、b_t と損失日の照合 | 段階 2 の判定材料とする |

---

## 8. 未解決事項

各項目への一次案は `ALB/ALB_THEORY_CH02_FILL_v0.1.md` の (C) に置いた（決裁者の承認待ち）。


1. E1：EXIT[SATIATION] → ACTIVE の再開遷移を追加するか
2. E2：λ_N をモードに連動させるか（不変条件 5 との緊張）
3. E5：b_t → LOAD の写像（閾値は HST-N 側に置く。Norn には置かない）
4. E6：RECOVERY 中の ALB の介入規則（ALB 理論側の合意を要する）
5. ALB 第1章の持ち越し 4 件（強制対象が自分か相手か、θ_A の算出方法、DefensiveEngine の減衰アルゴリズム、実証パート）は本メモでは扱わない
6. v7.3 パッチ第5部の未解決（MISSION の二義性ほか）には触れない
7. ~~ALB の設計メモ・第1章を本リポジトリに収録するか~~ → 収録済み（`ALB/`）

---

## 9. 記録

- 2026-10-21 v0.1 起筆。非重複 7 点のうち 1・2・5・6・7 を搭載、3 を除外、4 を現状維持とする決裁に基づく
- 2026-10-21 E7 の ALB 関係の記述を訂正（NRMO を上位に置く非対称を含んでいたため）。ALB 文書の収録と未解決への一次案の所在を追記
