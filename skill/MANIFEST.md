# NRMO Business — 管理職共通版 v1.0.0-business-rc1

| 項目 | 値 |
|---|---|
| 基準 | 正式承認済み個人版 nrmo v1.0.0-rc12 |
| 現行ソース | skill/nrmo-business/ |
| 対象 | 管理職共通。稟議・契約・投資・人事・プロジェクト・事故対応・撤退・監査 |
| Business固有参照 | references/BUSINESS_GOVERNANCE.md |
| 除外 | ALB/NPMO、非重複拡張草稿、会社固有規程の推測 |
| 計画 | skill/tests/business-rc1/PLAN.md |
| 生成 | python3 skill/tools/build_business_package.py → dist/nrmo-business-rc1/ |
| 固定ソース | 4d883f2b724eb20ab1bb94cb44242bc8fc2c5201 |
| 固定パッケージ | CI成果物 nrmo-business-rc1-<source SHA>/nrmo-business.skill |
| SHA-256 | 819f6b5e56638411e3e5efddff4b599095ed171116e5c14f024fe8f874a0226a |
| 状態 | 静的検証PASS。モデル試験・所有者アプリ試験はNOT_RUN |

個人版rc12のCanon、Publication of Record、保存原本、共有参照はバイト単位で維持する。Business版は個人版を置き換えず、別名・別パッケージで提供する。

---

# nrmo Skill — rc12 状態を含む終了場面の発動補強候補

| 項目 | 値 |
|---|---|
| 版 | nrmo-skill v1.0.0-rc12（未承認・未実動作試験） |
| 起点 | PR #23 head `8fbe4a48407c1b81d6666dccb2f649768bef9809`（rc11 と rc11 run-01 の記録） |
| 現行ソース | `skill/nrmo/`。21参照のsha256は`skill/release.json`（rc11 から不変） |
| 計画 | `skill/tests/rc12/PLAN.md`（実行前に固定） |
| 生成 | `python3 skill/tools/build_package.py` → `dist/nrmo-rc12/` |

## rc11からの変更（PR #23 コメント 6395006095 の判断に基づく）

- `SKILL.md` の description に「正式状態・HOLD・保留期間を含む区切りや終了の確認にも使う。」を加えた（147→178文字、上限200）。終了一般・あいさつ・翻訳は発動対象に加えていない
- SKILL.md 本文は版名の行だけを変更。終了経路を含む規則は rc11 のまま
- 21参照（Canon、保存原本、v7.3 PDF、RUNTIME_RECONCILIATION.md を含む）は rc11 からバイト単位で不変

rc11 は「内容・PDF参照は合格、発動境界に軽度欠陥3件が残った不合格候補」として固定する。

---

# nrmo Skill — rc11 PDF必読手順の固定候補

| 項目 | 値 |
|---|---|
| 版 | nrmo-skill v1.0.0-rc11（未承認・未実動作試験） |
| 起点 | PR #23 head `6f4f2727732186165a29e027eef756b38abd5462`（rc10 と rc10 run-01 の記録） |
| 現行ソース | `skill/nrmo/`。21参照のsha256は`skill/release.json` |
| 計画 | `skill/tests/rc11/PLAN.md`（実行前に固定） |
| 生成 | `python3 skill/tools/build_package.py` → `dist/nrmo-rc11/` |

## rc10からの変更（PR #23 コメント 6394494345 の判断に基づく）

- 標準の意思決定判定では、回答の組み立て前に PDF ファイルページ 463〜474 を1回の Read で、連続した1つの範囲として読む（SKILL.md、RUNTIME_RECONCILIATION.md）
- 会話の終了だけを求められた場合の終了応答を、標準判定から分ける。状態・Ruin・governance result・再評価日を出さず、状態履歴を作る表現を禁止する。この経路では PDF を開かない
- ε の参照先を、PDF 第3章（ファイルページ 59〜82）と、PDF Chapter 22「Caged Beast Model」（ファイルページ 211〜216）／同梱 `foundations/ch20_caged_beast.tex` に訂正する。「PDF第20章」とは書かない
- 初期費用＋仮定上の月次赤字の計算例（45万円など）を「上限」「上限の目安」「最大損失」と書かない
- 実際に開いていない資料を「確認した」「根拠は〜」と書かない
- ビルド検証に、連続範囲 `"463-474"`、Chapter 22（211-216）の経路、「Chapter 3 and Chapter 20」の不在、SKILL.md と照合ファイルの経路の一致を追加
- 変更したのは `SKILL.md` と `RUNTIME_RECONCILIATION.md` だけ。Canon、保存原本、v7.3 PDF、他の19参照は変更しない。Business版、ALB/NPMO、DecisionCompassは対象外

rc10 は不合格候補として固定し、原出力・採点・計画を変更しない。

---

# nrmo Skill — rc10 正典階層再整合候補

| 項目 | 値 |
|---|---|
| 版 | nrmo-skill v1.0.0-rc10（未承認・未実動作試験） |
| 起点 | Claude作業ブランチ `c104b930c9c5c1e7d40c891795e4670d6975de55`（rc9実行中の記録まで） |
| 現行ソース | `skill/nrmo/`。21参照のsha256は`skill/release.json` |
| 計画 | `skill/tests/rc10/PLAN.md` |
| 生成 | `python3 skill/tools/build_package.py` → `dist/nrmo-rc10/` |
| 状態 | 静的検証PASS。Claude Code・claude.aiの挙動はNOT_RUN |

## rc9からの変更

- 保存原本の`nrmo_system_v7_3.md`を単独の正典として扱わない。上位の`NORMATIVE_CANON.md`と原本の`SOURCE_MANIFEST.md`をSkillへ収録し、運用MarkdownをLLM/GEM向け従属仕様として位置づける
- `RUNTIME_RECONCILIATION.md`を追加し、Canon、Publication of Record、運用Markdownの参照順と、PDFの必読節を固定する
- HOLDを「現在の記録状態」「今回のgovernance result」「HOLD→ACTIVEの本人承認」に分ける。ACTIVE→HOLDには本人操作・承認を要求しない
- Passive Ruinの主要条件をavoidability-window closureとし、不活動期間を二次的な標識に限定する
- Hard/Softのseverity軸（Investment domain）とActive/Passiveのorigin軸（domain-general）を分離する
- 保存原本の運用Markdown、v7.3 PDF、従来の17参照は変更しない。Business版、ALB/NPMO、DecisionCompassは対象外

rc9までの試験結果は旧参照構成の記録として保持する。rc10の正典適合や挙動の証拠には転用しない。

---

# nrmo Skill — rc9 個人版候補の固定記録

| 項目 | 値 |
|---|---|
| 版 | nrmo-skill v1.0.0-rc9（未承認候補） |
| 起点 | PR #22 head e15fb46bd6f0bb4369593d2bae545170cd4e7b06（rc8、rc8-upload1） |
| 現行ソース | skill/nrmo/。版と17参照のsha256はskill/release.json |
| 計画 | skill/tests/rc9/PLAN.md（実行前に固定） |
| 生成 | python3 skill/tools/build_package.py → dist/nrmo-rc9/（descriptionは1〜200文字でなければ失敗する） |
| 過去版 | archive/v1.0.0-rc8/・v1.0.0-rc8-upload1/までの固定パッケージと、各版のCLI試験を保持 |
| 修正の動機 | rc8-upload1のアプリ応答15件の本文レビュー（PASS 7、FAIL（軽度）8、環境未確認）。原応答は公開変更に含めない |
| rc9のClaude Code試験 | 主試験33/33 PASS（欠陥0）、補助12件はPASS 10・FAIL（発動）2（skill/tests/rc9/run-01/REPORT.md） |
| rc9のclaude.ai試験 | NOT_RUN |

## rc8からの変更

descriptionを147文字（rc8-upload1と同じ文言）にし、Skill本文に「書かれていない事実・費用・日付を補わない」（未申告は不明、現在の状態を決めつけない、無料を断定しない、期間を日付に変えない、回復可能性を一般論で断定しない）と、初期費用の二重計上の防止を共通規則として追加する。

v7.3正典・17参照とPDF_CAVEATS.mdは不変。ALB／NPMOは研究草稿として通常運用から除外。Business版は変更しない。

---

以下はrc8時点の記録（原文のまま保持）。

# nrmo Skill — rc8 個人版候補の固定記録

| 項目 | 値 |
|---|---|
| 版 | nrmo-skill v1.0.0-rc8（未承認候補） |
| 起点 | PR #22 head 63d27fff9c5920e8f0cdb3d57c865321a52364de（rc7） |
| 現行ソース | skill/nrmo/。版と17参照のsha256はskill/release.json |
| 計画 | skill/tests/rc8/PLAN.md（新版の補助試験・Claude試験前に記録） |
| 生成 | python3 skill/tools/build_package.py → dist/nrmo-rc8/ |
| 過去版 | archive/v1.0.0-rc7/までの固定パッケージと、各版のCLI試験を保持 |
| 修正の動機 | アプリ応答の本文確認。原応答・個人の環境記録は公開変更に含めない |
| rc8の実Claude試験 | NOT_RUN（この環境にはClaude Code CLIがない）。Codex補助試験と混同しない |
| rc8のclaude.ai試験 | NOT_RUN |

## rc7からの変更

Skill本文だけに、個別案件の破綻認定と禁止の根拠、初期費用と合計損失上限の区別、費用と損益・二重計上の確認、本人宣言の意味と追加提案の分離を追加する。分類と数値の確認を、モード理由から撤退条件まで同じ意味で適用する。

v7.3正典・17参照とPDF_CAVEATS.mdは不変。ALB／NPMOは研究草稿として通常運用から除外。人間（Vision・最終判断）／NRMO（境界・許容集合）／StrongEngine Ω Full（許容集合内の前進候補）を維持する。Business版は変更しない。

パッケージの形式・CRC・19メンバー・参照ハッシュ・同一環境での決定性・不一致拒否は生成スクリプトで検証する。形式検証や補助試験だけで実モデル試験・アプリ試験・正式版承認・マージの合格を宣言しない。
