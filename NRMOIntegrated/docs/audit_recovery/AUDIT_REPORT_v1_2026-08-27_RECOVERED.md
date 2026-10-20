<!--
回収記録
  区分    : 原文回収（推定による再構成を含まない）
  対象    : NRMO_DecisionCompass_audit_final_report.md 第1版
  作成時点: 2026-08-27（原本の「作成日」表記）
  回収元  : claude.ai 対話「人間の個の完成」(chat ab0bbb1a-2d46-47c0-941a-8888d5c5f623) turn 323 の create_file 呼び出しの file_text 全文
  回収日  : 2026-10-21
  注意    : これは第1版（77ファイル時点）であり、最終版（第7版、183件）ではない。
            第1版以降は追記・置換が turn 324〜466 にわたり数十回行われており、最終版の状態は未回収。
            回収状況は RECOVERY_STATUS.md を参照。
  本文は回収元のとおり。以下の区切り線より下を一字も変更していない。
-->

# NRMO / DecisionCompass 横断監査 最終報告書

対象: zarame96/NRMO、zarame96/DecisionCompass 両リポジトリ
読了: 77ファイルの精読 + UNCREATED_COMPONENTS.md等の権威ある一次資料
作成日: 2026-08-27

---

## 0. この監査で最も重要な結論(哲学)

**「機能を増やす・洗練させることは、実証的に一貫して報われていない。」**

これは個々のバグより重い、監査全体を貫く発見。3つの独立した経路で
三重に確認された:

1. 旧v7.2(Calibration Gates)のablation研究:
   「全22機能ON」はNormal worldでv7.1より**悪化**した(-0.71)。
   実際に採用すべきは10機能のみ。
2. v8.x系列: Wolf Pursuit、ContextClassifier、MAPLayer、
   ActivePattern等、大量の洗練された機構を実証検証した結果、
   ほぼ全てが「寄与ゼロ」と判明。最終的に「引き算による最終形」
   (V71Engine+EmergencyResourceGuard+SynthesisPathwayのみ)に収束。
3. UnifiedEngine(世界適応的な"賢い"統合エンジン)は、9つの
   世界×難易度セル全てで、一度も最良の成績を残せなかった。
   単純な`recover_fixed`や、世界特化型`v9_minimal`に一貫して劣った。

そして`research/loom100`の提言メモが、この教訓を哲学的に統合する:
**「測れないものは黙って切り捨てられる=目的関数の盲点は暗黙の
価値判断」**。ザラメさん自身を100年企業シムのCEOとしてモデル化
したところ、`ruin_aversion`という物差しがモデルに無かったために、
「平凡な経営者」と誤判定された、という象徴的な発見から導かれた
原則。

---

## 1. バージョン管理の混乱(構造的問題)

- 「v7.2」という名前が、最低3つの異なる内容を指していた
  (今日のTimeHorizonLayer作業/旧Calibration Gates/DecisionCompass
  のphase1)
- v8.0(14層、POMDP/CMDP/Knightian等)→ v8.1-8.2失敗 → v8.4.1
  (単純化、FROZEN)→ v8.4.2-4(MAPLayer実験、大半不採用)→
  v8.5.1(全部乗せ)→ v9-minimal(引き算)→ UnifiedEngine
  (適応統合、しかし最良にならず)という長い変遷が、明確な
  一本の系譜として文書化されていない
- 同名だが別実装のクラス(`StrongEngineOmegaFull`が最低2箇所、
  `WorldTypeDetector`が最低2箇所)が並存

**対策**: `docs/UNCREATED_COMPONENTS.md`のような「権威ある現状台帳」
は既に存在し、機能している。これをバージョン系譜全体に拡張し、
「今、本当に使われているのはどれか」を一元管理すべき。

---

## 2. 具体的なバグ(優先度順)

### 2.1 【高】タイミング攻撃に脆弱なPIN比較
`decisioncompass/app/auth.py::login_with_pin()`
```python
if pin != expected:  # 定数時間比較でない
```
`secrets.compare_digest(pin, expected)`への一行修正で解決可能。

### 2.2 【高】不可逆性チェックのロジック反転疑い
`NRMOIntegrated/.../core/aallowed.py::AallowedRegistry.evaluate()`
`max_irreversibility==0.0`の時だけ不可逆行動をREJECTする分岐があり、
docstringの意図(0.0=不可逆も許可)と矛盾。中間値(0.4/0.5/0.6)の
カテゴリでは不可逆性チェックが実質無効化されている。

### 2.3 【中】型の誤解による無効な"優先"経路
`decisioncompass/nrmo_bridge/full_attach.py::_candidate_from_full()`
`float(strength)`——`strength`は実際には"A"/"B"/"C"という文字列
(world_models.Action.strength)。この「最優先」パスは必ず例外で
except節にフォールバックし、実質一度も成功しない。

### 2.4 【中】PassivePattern/ActivePatternが構造的に無効化
`full_attach.py`のアダプタが`candidates=[]`, `final_action=None`
で`evaluate()`を呼ぶため、内部のスコア計算のほとんどが構造的に
ゼロになる。`nrmo_os_integrator.py`ではPassivePatternはtrace記録
専用(意図通り)だが、その記録自体が無意味な値になっている。
ActivePatternはこのパイプラインから一切呼ばれていない。

### 2.5 【中】防御の層が不揃い
`decisioncompass/app/api.py::add_feedback` / `repository.py`
`record_outcome()`は明示的に多層防御(user_idをWHERE句に含める)
を実装しているが、構造的に似た`add_feedback()`はAPI層のチェック
のみに依存。

### 2.6 【低】断定表現・危機検知キーワードが分散管理
`shutdown_guard.py`の`_HARM`、`secretary_console.py`の
`_RUMINATION`(「消えたい」が両方に重複しつつ別管理)、
`financial_policy.py`の`ASSERTION_BANS`——いずれも固定フレーズの
完全一致のみで、婉曲表現や新しい言い回しに脆弱。一元管理されて
いない。

### 2.7 【低・設計】WorldTypeDetectorの"chaotic"が消去法の既定値
`core/meta_engine.py::WorldTypeDetector.detect_world_type()`は、
"drifting"でも"noisy"でもなければ機械的に"chaotic"と判定する
(積極的な検知条件なし)。UnifiedEngineはこの判定で踏み込んだ
重み調整を行うため、これが発見(1章)の「UnifiedEngineが一貫して
中位」の一因である可能性が高い。

---

## 3. 良かった点(過大に批判しないための記録)

- `finance/`サブシステム: 複式簿記の会計恒等式を毎ステップ検証、
  実モンテカルロ・ロールアウトに基づく敵対的検証。この生態系の
  中でも質の高い部類
- `evidence/collector.py`: リダイレクト経由のSSRFまで考慮した、
  見落とされがちな観点まで対応したセキュリティ設計
- `blind_spots.py`: 「測っていない次元」を明示的にユーザーへ
  開示する、知的に誠実な設計(loom100の中心発見を直接継承)
- `billing.py`: 過去の実際の脆弱性(クライアント埋め込み秘密鍵)を
  発見・修正した記録が残る、健全な開発プロセス
- `Norn`/`drift_reporter.py`: 「遅いズレ=尊重、速い反転=警告」
  という、認識論的に洗練された、判断しない観測層
- `v8_manifest.json`等の検証記録: 失敗を隠さず記録する、誠実な
  文化が一貫している
- `loom_canonical.py`: 「何が正典で何がアーカイブか」を明示する、
  良い実践例
- `UNCREATED_COMPONENTS.md`: 「CREATEDと主張するには実行時トレース
  で効果を示せることが必須」という規律。今回発見した問題群への、
  プロジェクト自身による誠実な対応策

---

## 4. v7.3設計への提言

1. **loom100の8禁忌を、明文化された設計原則として正式採用する**
   (特に禁忌4: 反証不能な複雑さの追加禁止、禁忌8: パラメータの
   不在が価値判断を密輸することへの警戒)
2. **複雑化ではなく、実証済みの単純さを優先する**設計文化を、
   v8.x〜UnifiedEngineの実証結果を根拠として明文化する
3. **バージョン系譜を一本化**し、`UNCREATED_COMPONENTS.md`型の
   「権威ある現状台帳」の運用をNRMO本体側にも拡張する
4. 上記2.1-2.7の具体的バグを優先度順に修正する
5. 危機検知・断定表現のキーワードリストを一元管理する
6. 行動表現(連続ベクトル vs 区分的intent/strength)の不統一を
   解消するか、明示的な変換層を正式に定義する

---

## 5. 監査の限界(正直な申告)

190以上のファイルのうち、77ファイルを精読した。残りは主に:
- v8.x系列の個別エンジンバリアント(v83, v841以外の細部)
- validation/benchmark基盤コードの実装詳細(README等の要約は確認済み)
- 一部の世界モデルバリアント
- research/loom100のscripts/本体コード(README・提言メモは確認済み)

これらは、既に確立した強いパターン(検証基盤の質の高さ、archived
モジュールの存在、決め打ち定数への依存)の周辺である可能性が高いが、
断定はできない。追加で読み進めることで、さらなる発見が出る可能性は
残っている。
