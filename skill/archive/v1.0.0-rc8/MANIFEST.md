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
