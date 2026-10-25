# NRMO SYSTEM v7.3 パッチ（第3版・実装検証済み）

適用先: `NRMO SYSTEM_7.2.md`
典拠: `NRMO_Integrated_System_v7_2.pdf`（511p）＋ 実装 `nrmo_v72_phase1`
検証日: 2026-09-15
裁定者: Zarame

---

# 第0部：撤回

## 撤回1（第1版）

`v52_codebase` を Integrated 本体の実装として扱った。誤り。
`v52_codebase` は PDF が「v5.2 baseline reference」と呼ぶ**旧ベースライン**である。

## 撤回2（第2版）

以下の3点は、旧ベースラインの挙動を本体の仕様と誤認したものである。**全て撤回する。**

| 誤報 | 実測（本体） |
|---|---|
| 「HOLD は実装に存在しない」 | **存在する。** `HOLD = "EXIT_HOLD"`。許容集合が空なら Engine が HOLD を返し、候補生成も行わない |
| 「成立しているのは `a_t ∈ conv(A_t)`」 | **`a_t ∈ A_t` が厳密に成立。** 要素一致を assert で検証済み |
| 「`engine/norn.py` の所属が未確定」 | **そのファイルは存在しない。** 争点ごと消滅 |

## 検証の根拠

統合ツリー（公開リポジトリの文書 ＋ DecisionCompass の `code/`）で実行。

```
公式検証エントリ  必須8項目 ALL PASS / スキップなし（6.9s）
Part A 本物サブシステム駆動   10/10 PASS
Part B NRMO 分離契約          8/8 PASS
```

Part B の内訳に以下が含まれる。

- `engine_never_reads_veto_thresholds`
- `selected_action_always_in_admissible`
- `vetoed_action_unreachable`
- `empty_admissible_returns_hold`
- `no_NRMO_boundary_mutation_by_engine`

統治と実行の分離は、本体実装において**構造的に**担保されている。

---

# 第1部：モード階層の確定

## PDF の定義

### §2.3 Operational Modes（実行姿勢）

| モード | 定義 |
|---|---|
| NORMAL | 標準運用 |
| SAFE | リスク最小化実行 |
| VENTURE | 定められた制限下での探索 |
| MISSION | 目的制約下の実行 |

### §2.4 Context Override Modes（文脈上書き）

| モード | 定義 |
|---|---|
| TRAINING（A–F, E+） | ロールプレイ／シミュレーション、失敗再現、防御的理解のための隔離文脈。実世界の判断に直接影響してはならない。出力は Passive Pattern または Observe/Orient 段にのみ接続可 |
| HARE（晴れの日） | 表現・情緒の制約を緩める。ただし破綻回避原則は停止しない |
| /#vision | **運用モードではない。** 長期方向性と価値の参照文脈。命令も判断も発しない |

### §4.7 Type ZERO Modes（統治層が観測状態から自動割当）

モードは制約ではなく、**将来の自由度を保つためのギア**である。
CORE / VENTURE は自由度を広げ、MISSION / SHUTDOWN は不可逆境界を避ける。

| モード | 目的 | 遷移トリガ |
|---|---|---|
| CORE | 通常運用（自由度最大化） | IRREV=I1 かつ VOL≥V1 → MISSION |
| VENTURE | 探索・拡張 | LOAD=L2 または VOL=V2 → CORE |
| MISSION | 境界接近時の制御 | IRREV=I0 かつ VOL≤V1 → CORE |
| SHUTDOWN | 停止（安全着陸） | IRREV=I1 かつ VOL=V2 かつ LOAD=L2 → 即時 |

Appendix A の形式仕様も同一: `m_t ∈ {Core, Venture, Mission, Shutdown}`

### §11.1.2 状態空間（理論的不変条件）

```
S = {ACTIVE, HOLD, EXIT, SAFE_EXIT}

ACTIVE → HOLD      人間の介入が必要
ACTIVE → EXIT      計画的終了
ACTIVE → SAFE_EXIT 緊急終了
HOLD   → ACTIVE    人間の承認
HOLD   → SAFE_EXIT エスカレーション
```

### §4.11 / §7.8 A_allowed v1.2 — MISSION-DEFENSE Extension

**モードではない。許容行動集合の拡張である。**
発動条件（交渉不可）、非交渉的制限、追加カテゴリ、MISSION caps 拡張、
5段階の運用手順、専用の出力形式を持つ。

## 実装の実測

`core/mode_selector.py` の `ModeSelector` が返す値:

```
TRAINING / SAFE / HARE / MISSION / VENTURE / NORMAL
```

**PDF §2.3（4種）＋ §2.4（TRAINING, HARE）と完全一致する。**

HOLD は `v7_maxforward/separation_engine.py:35` に
`HOLD = "EXIT_HOLD"` として定義される sentinel であり、
モード列挙には含まれない。§11.1.2 の状態空間に対応する。

## 現行 md の誤り

| md のモード | 判定 |
|---|---|
| NORMAL | 正しい（Operational Mode） |
| SAFE | 正しい（Operational Mode） |
| VENTURE | 正しい（Operational / Type ZERO 両方に存在） |
| MISSION | 正しい。ただし二義性あり（下記） |
| MISSION-DEFENSE | **誤り。** モードではなく A_allowed 拡張 |
| HOLD | **誤り。** モードではなく状態 |
| （欠落） | **TRAINING と HARE が抜けている** |

## MISSION の二義性 — 記録のみ

- §2.3: 目的制約下の実行（前進のための制約）
- §4.7: 境界接近時の制御（不可逆方向を避ける防御）

方向が逆を向いている。PDF 側の未整理であり、本パッチでは解決しない。

---

# 第2部：§8 の置換（確定）

現行 md の §8 を、以下で全面置換する。

```
## 8. モードと状態

モードは制約ではない。将来の自由度を保つためのギアである。

### 8.1 Operational Modes（実行姿勢）

NORMAL   標準運用
SAFE     リスク最小化実行
VENTURE  定められた制限下での探索
MISSION  目的制約下の実行

### 8.2 Context Override Modes（文脈上書き）

TRAINING（A-F, E+）
          ロールプレイ／シミュレーション、失敗再現、防御的理解のための隔離文脈。
          実世界の判断に直接影響してはならない。
          出力は Passive Pattern または Observe/Orient 段にのみ接続する。
HARE      表現・情緒の制約を緩める。破綻回避原則は停止しない。
/#vision  運用モードではない。長期方向性と価値の参照文脈。
          命令も判断も発しない。

### 8.3 Type ZERO Modes（統治層が観測状態から自動割当）

CORE      通常運用。自由度最大化。不可逆境界のみ監視
VENTURE   探索・拡張。小さく試し、可逆範囲内でのみ拡大
MISSION   境界接近時の制御。行動空間を整理し、
          不可逆方向の行動を避けつつ自由度を維持
SHUTDOWN  停止（安全着陸）。一時停止、延期、休息、第三者確認

CORE / VENTURE は自由度を広げる。
MISSION / SHUTDOWN は不可逆境界を避ける。

### 8.4 状態（理論的不変条件）

S = {ACTIVE, HOLD, EXIT, SAFE_EXIT}

HOLD はモードではない。
ACTIVE → HOLD は人間の介入を要し、HOLD → ACTIVE は人間の承認を要する。
許容行動集合が空のとき、実行層は HOLD を返し、候補生成を行わない。

### 8.5 A_allowed 拡張

MISSION-DEFENSE（v1.2）
モードではない。圧力・誘導・関係悪化・不可逆化・心理的負荷がある場面で
発動する許容行動集合の拡張。発動条件は §4.11 に従う。
```

## §6 出力形式への追加

応答時に次を示す。

```
Operational Mode：
Type ZERO Mode：
状態：ACTIVE / HOLD / EXIT / SAFE_EXIT
MISSION-DEFENSE 拡張：発動 / 非発動
```

---

# 第3部：§4.10 Norn の追加（確定）

裁定（2026-09-15）: 上流・下流の二役を持つ。ただし性質は Operator（操舵係）。

```
### 4.10 Norn（Operator / 操舵係）

Norn は NRMO Integrated の Operator である。
大きな船の操舵係であり、決裁者の意志に沿って舵を取る支援者である。

操舵係は舵を取るが、針路を決めない。針路は決裁者が定める。
Norn の仕事は、定められた針路を保ち、逸れたときに報せることである。

#### 性質

意思決定主体ではない。実行エンジンでもない。
構造的一貫性を保持する解釈的パースペクティブである。

#### 主務

監視と報告。

1. 分岐記録     どの選択肢が挙がり、どれが残り、どれが選ばれたかを記録する
2. 手続き監査   評価順序（§14）が実際に踏まれたかを記録する
3. ドリフト検知 概念的ドリフト、および憲法的ロジックが日和見的な
                短期推論に置換されていないかを検知し、報せる
4. Passive観測  動いていない状態、機会損失、適応遅れを観測する

#### 二面の配置

上流: World Model / Observation の直後。状況の特徴を整理し、
      決裁者が定めた針路からの逸れを検知する。
下流: 決裁の後。結果を観測し記録する。決裁結果を変更しない（片方向）。

いずれの位置でも Norn は判断しない。
上流の整理は保針であり、評価ではない。

#### 禁止

VETO しない / 実行しない / 結論を出さない / 針路を決めない
人格を持たない（§3-9、§3-10、§11-12）

#### 設計原則

監査は秤を持たない。観測層に閾値を置いてはならない。
閾値を置けば、Norn は第四の意思決定者になる。

上流で文脈を整理する際も、基準は Norn に属さない。
基準は決裁者が定めた Vision / Mission と、決裁者自身の過去分布である。

#### 変化の扱い

「前と違う」を変化の速度で見分ける。

DRIFT               長期の緩やかな移動。成長または環境変化の可能性。敬意をもって扱う
SIGNAL              同日内の急反転。異常の可能性。知らせる
WITHIN_OWN_RANGE    過去の範囲内。事実として置く
INSUFFICIENT_HISTORY 履歴不足。報告しない

#### 問診

7日経過後にランダムに立てる。
毎回同じ間隔にすると馴化し、回答が汚染される。

#### Norn / Skuld（実行層の同名モジュール — 別物）

ShinobiEngine 内の NornTaskManager（主タスク管理者）と
SkuldTaskManager（バックアップ、Norn が unavailable な時の fallback）は、
12ユニットへの重み配分を行う実行層のモジュールであり、
本節の Operator としての Norn とは別の対象である。混同してはならない。
```

---

# 第4部：実装で確定した事実

| 項目 | 実測 |
|---|---|
| Operator としての Norn | `decisioncompass/audit/norn.py`（125行）。`audit/` パッケージ、決裁の**後**に片方向で観測 |
| 配線 | `api.py:278`。`create_decision` の戻り値確定後に `get_norn().observe()` |
| 永続化 | `audit_store.py`（150行、SQLite）。`DECISIONCOMPASS_AUDIT_PERSIST=0` でメモリのみ |
| 併存モジュール | `calibration.py`、`user_drift.py`、`audit_observer.py`（296行）、`drift_reporter.py`（304行） |
| 実行層の Norn | `core/shinobi_engine.py:132` `NornTaskManager`（Norse: Past） |
| Skuld | `core/shinobi_engine.py:190` `SkuldTaskManager`（Norse: Future）。Norn の fallback |
| `engine/norn.py` | **存在しない。** リポジトリ全体に `engine/` ディレクトリなし |
| `engine/omega_v52_adapter.py` | **存在しない** |

---

# 第5部：残る未解決

## 5-1. PDF §43.6 が実在しない構成を記述している

§43.6 は「Engine Auxiliary Modules」として以下を挙げるが、いずれも実在しない。

- `engine/shinobi.py`（実在は `core/shinobi_engine.py`）
- `engine/norn.py`（265行 — **実在しない**）
- `engine/map_layer.py`（実在は `core/map_layer.py`）
- `engine/omega_v52_adapter.py`（**実在しない**）

PDF 側の訂正作業を要する。

## 5-2. NornTaskManager の改名が未実行

2026-06-14 に「実態名へ改名してよい」と裁定されたが、実行されていない。
検証 `norn_task_manager_used` が PASS しており、現役で稼働している。

結果、「Norn」が実装内に2つ、文書内に2つ（うち1つは実在しない）存在する。

改名するか、第3部の注記で併存を許容するかの判断を要する。
本パッチは後者を暫定採用している。

## 5-3. MISSION の二義性（§2.3 と §4.7）

記録済み。未解決。

## 5-4. v8.3

`core/v83_engine.py` に「NRMO v8.3 Integrated Engine — 正典 pipeline」が実装されている。
**2026-09-15 時点で正式採用されていない。** 本パッチの対象外。

---

# 適用手順

1. 現行 md の §8 を、第2部の内容で全面置換
2. §6 の出力形式に、第2部末尾の4項目を追加
3. §4 の末尾に、第3部の §4.10 を挿入
4. バージョン表記を v7.3 に更新
5. Drive の `NRMO SYSTEM_7.2.md` を差し替え
6. Gemini GEM と会社 Claude の Project Knowledge を両方更新
