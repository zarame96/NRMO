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
| rc9のClaude Code試験 | skill/tests/rc9/（主試験33件と補助12件を別に報告） |
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
