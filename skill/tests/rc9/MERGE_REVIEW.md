# 正式版承認・PR #22 マージ判断の資料（rc9、下書き）

**状態：Claude Code 主試験 33/33 PASS（確認された欠陥0件）、補助12件は PASS 10・FAIL（発動）2、パッケージ検証 PASS、claude.ai アプリ15件は NOT_RUN。** この文書は承認でも main へのマージでもない。

## 1. 判断の対象

| 項目 | 値 |
|---|---|
| 候補版 | nrmo-skill v1.0.0-rc9 |
| ソースコミット（実モデル試験の対象） | `440fa65b843a381c2a2f6e7e09035e951c3f0d08` |
| nrmo.skill の sha256 | `ff73850eafbc6f41855393aa30770465c4fb1b0ef79939b1ee8d3a07137382cb`（`skill/archive/v1.0.0-rc9/`） |
| description | 147文字（上限200をビルドで検証） |
| 通常版の対象範囲（決定済み） | v7.3 正典による支援＋通常の StrongEngine Ω Full。ALB／NPMO は研究草稿として通常運用から除外 |

## 2. rc8 から rc9 への経緯

1. 元 rc8（`f6b90797…`）は claude.ai へのアップロードに失敗した（原因は断定していない）
2. description だけを短くした rc8-upload1（`0c2cbab1…`）でアプリ15件の応答を受領し、Codex が本文をレビューした：PASS 7、FAIL（軽度）8。環境・読込版は未確認
3. 欠陥の型（未申告の補完、状態の決めつけ、無料の断定、期間の日付化）と所見（回復可能性、二重計上）を、共通規則として SKILL.md に加えた。description を200文字以下にし、ビルドで検証するようにした
4. 同じ型を rc3〜rc8 の CLI 記録で再点検し、rc8 の「33/33 PASS」を「PASS 26、FAIL（軽度）7」に訂正した（`RECHECK_PAST_CLI.md`）

## 3. 検証結果

| 確認 | 結果 |
|---|---|
| パッケージ検証（19メンバー、17参照ハッシュ、往復、CRC、決定性、不一致拒否、description 200文字以下） | PASS |
| Claude Code 主試験33件（CLI 2.1.308） | **33/33 PASS、欠陥0件、所見1件**（`run-01/REPORT.md`） |
| Claude Code 補助12件（アプリの A3・A4 の原文と、費用・回復可能性を狙う入力） | PASS 10、**FAIL（発動）2**（U1_r3・U3_r2 で Skill が呼ばれなかった）。本文の欠陥0件 |
| claude.ai アプリ15件 | **NOT_RUN**（`app/QUICKSTART.md`、`app/RECORD.md`） |

各版の CLI 主試験（再点検後）：

| 版 | PASS | FAIL | 判定不能 |
|---|---|---|---|
| rc3 | 15 | 12 | 6 |
| rc4 | 20 | 7 | 6 |
| rc5 | 20 | 7 | 6 |
| rc6 | 24 | 3 | 6 |
| rc7 | 25 | 8 | 0 |
| rc8 | 26 | 7 | 0 |
| **rc9** | **33** | **0** | 0 |

限界：各入力3回。採点者は Claude で、rc3〜rc8 では同じ型を見落とした実績がある。基準は実行前に固定し、理由を GRADES.md に残した。

## 4. 差分

v7.3 正典、17参照、ALB 資料の本文、`.tex` は変更していない。Skill のソースの変更は `skill/nrmo/SKILL.md`・`skill/release.json`・`skill/tools/build_package.py`（description の上限の検証）・ワークフローの artifact 名に限られる。rc8・rc8-upload1 の成果物と過去の原記録は保持している。

## 5. 残る判断

1. rc9 のアプリ確認15件の実施（Skill の使用表示も記録する。補助試験で発動しない回があったため）
2. 結果を受けた正式版の承認
3. PR #22 の main へのマージ

ALB の採用、Business 版への反映は含めない。
