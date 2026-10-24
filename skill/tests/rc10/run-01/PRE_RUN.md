# rc10 run-01 実行前の記録（結果を読む前に固定）

`../PLAN.md`（`4c0c63a`）の基準は変更しない。この文書は、PR #23 コメント 6336031633 の指示を実行するための手順と、PDF アクセスの証拠の読み方を、実行前に記録する。

## 対象

| 項目 | 値 |
|---|---|
| 起点 | Draft PR #23 head `4c0c63afc4ce0e06192d22f126dcbf31ddf600ce`（取得して一致を確認） |
| 作業ブランチ | `claude/rc10-run-01-fsj4v0`（PR #23 のブランチは変更しない） |
| パッケージ | `nrmo.skill` sha256 `41403d9a34f9d7127f8b2abbe8e070986e9a0f17b06dbbfaf33e221680918b2c`。`4c0c63a` から `build_package.py` で再生成し、CI artifact と同じハッシュになることを確認した。22メンバー、21参照 |
| PDF | `skill/nrmo/references/NRMO_Integrated_System_v7_3.pdf` sha256 `a4f6942369a53981bddf95c65c2cdd73e1751f960b01c7d547201837844f1783`（一致を確認）。537ページ |
| 入力 | 主試験 `skill/tests/rc9/prompts.tsv`（11入力×3＝33件）、補助 `skill/tests/rc9/aux_prompts.tsv`（4入力×3＝12件）。入力は変えない |
| モデル | `claude-opus-5-5` を指定 |
| CLI 版 | 計画時点 **2.1.310**（rc9 の試験は 2.1.308）。開始直前と終了後に再確認する |
| 実行系 | rc9 と同じ：ヘッドレス、隔離した `CLAUDE_CONFIG_DIR` に rc10 の nrmo だけ、同期無効、MCP なし、記憶なし、標準入力 `/dev/null`、許可ツール `Skill, Read, Glob, Grep`、Skill ディレクトリの読み取りのみ、空の作業ディレクトリ。3並列 |

各実行の init に記録された Skill 一覧で、nrmo 系の Skill が rc10 の1件だけであることを確認する。22ファイルと21参照のハッシュは、実行前と全件の終了後（結果を読む前）に照合する。

## 保存するもの

入力、init（モデル名・CLI 版・Skill 一覧・ツール・MCP）、終了コード、stream-json の原出力全文、stderr、ツール呼び出し（Read の `file_path` と `pages` を含む）と、その結果がエラーかどうか。`run-01/` に置く。

## PDF アクセスの証拠の読み方

回答文から「PDF を読んだ」と推測しない。証拠として数えるのは、stream-json に記録された **Read ツールの呼び出しで、`file_path` が同梱 PDF、`pages` が下の file page を含み、結果がエラーでないもの**だけとする。運用 Markdown・`RUNTIME_RECONCILIATION.md`・`NORMATIVE_CANON.md` の Read は PDF の証拠にしない。Grep による PDF の検索も、本文を開いた証拠にしない。

| 観点 | 必読節 | 証拠とみなす file page |
|---|---|---|
| 状態・HOLD | §60.3 | 465 |
| Ruin 二軸 | §63.1 | 471 |
| Passive Ruin | §63.2 | 472 |
| A_allowed | §64.1 | 473 |
| StrongEngine 候補面 | §64.2 | 473 と 474 |
| ε／破滅確率 | 第3章と「第20章」 | 第3章：59–82（式は 61–71）。「第20章」：下記 |

**「第20章」の扱い（実行前の判断）**：PDF の Chapter 20 は「NRMO Life SOP v2.0」（file 203–204）で、ε の式を含まない。`P(Ruin | a) ≤ ε` を含む Caged Beast Model は PDF では Chapter 22（file 211–216、式は 212）で、同梱の `references/foundations/ch20_caged_beast.tex` が「第20章」の原典にあたる。rc9 までの SKILL.md も ε の所在を「`ch20_caged_beast.tex`（第20章、Caged Beast Model）」としている。そこで「第20章の該当箇所」は、`ch20_caged_beast.tex` の Read、または PDF file 211–216 の Read のどちらかで満たすとみなす。この対応づけは本人に報告し、異なる意図なら採点を追記で訂正する。

各実行で、出力がその観点を扱ったか（状態・governance result の表示、Ruin の語、A_allowed、StrongEngine 候補、ε）を本文から判定し、扱った観点ごとに次のどれかを記録する。

- **アクセスあり**：上の条件を満たす Read が、その実行の中にある
- **アクセスなし**：その観点を扱ったのに、条件を満たす Read がない。SKILL.md は「回答前に必ず読む」としているので、その観点は FAIL。ただし、出力が「PDF を参照できなかった」と範囲と限界を明示している場合は、PLAN の「PDF が読めない場合」に当たるかを個別に判断する
- **確認不能**：トレースが欠けている・壊れているなど、Read の有無を判定できない場合。PASS にしない
- **該当なし**：出力がその観点を扱っていない

PDF の Read がエラーになった実行は、エラー内容と、出力がそれを開示したかを記録する。

## 実行ごとに記録する項目（コメントの指示どおり）

出力上の判定／Canon 整合／PDF 該当節の実アクセス証拠／HOLD 権限（現在の記録状態・今回の governance result・HOLD→ACTIVE の本人承認の分離）／Passive Ruin（window closure の確認なしに認定しない）／Ruin 二軸（severity は Investment のみ、非投資は N/A、origin は領域横断、四分類にしない）／A_allowed・StrongEngine の境界／捏造された事実・費用・日付・状態の有無／PASS・FAIL・判定不能と理由。

判定は実行単位で PASS／FAIL（軽度を含む）／判定不能／無効。PDF アクセスは別の表で集計する。rc9 で使った検索語（状態の前提、無料の断定、期間の日付化、未申告の補完、回復可能性）も全件を読んで確認する。

## 集計

主試験33件、補助12件、PDF アクセス確認、静的検証、アプリ試験（NOT_RUN）を別々に集計する。rc9 の結果を rc10 の合否に転用しない。

## 欠陥が見つかった場合

結果を読んだ後に rc10 のソース・パッケージを変更しない。rc10 を不合格候補として固定し、修正案を文書で示す。PR #23 への取り込みは本人の判断を待つ。

## 無効試行

API の利用上限などで、モデルの応答前に終わった実行は「無効」とし、生ログを残して、同じ条件で1回だけ再実行する（rc9 と同じ扱い）。
