# 正式版承認・PR #22 マージ判断の資料（下書き）

**状態：CLI 33/33 PASS、CI success（対象 `de1f668`、成果物は固定ハッシュと一致）、アプリ 15件は NOT_RUN。** アプリ確認の結果を受け取ったら5節を埋めて完成させる。この文書は承認でも main へのマージでもない。

## 1. 判断の対象

| 項目 | 値 |
|---|---|
| 候補版 | nrmo-skill v1.0.0-rc7（候補版として固定済み） |
| ソースコミット | `3c6d7d76f30f9e74f936a9b6b8f6a713dc613f5d` |
| nrmo.skill の sha256 | `ad9db63be6ac3cbf3414246d83b58f5ad5cb4fadfc4341e4344a6f8b3897f426` |
| 通常版の対象範囲（決定済み） | v7.3 正典による支援＋通常の StrongEngine Ω Full。ALB／NPMO は研究草稿として通常運用から除外（`APPROVAL_SCOPE.md`） |

## 2. PR #22 への取り込み（2026-10-21 実施）

- 取り込み前に確認：PR #22 のブランチ `docs/ext-nonoverlap-v0.1` は `e346562`、作業ブランチは `de1f668`。`e346562` は `de1f668` の祖先で、PR 側だけのコミットは 0件。分岐なし
- 早送り（強制なし）で取り込んだ（`e346562..de1f668`）。rc7 は PR #22 のレビュー対象になった
- 試験の生ログは、本人の指示により保持する（削除・履歴の書き換えはしない）
- 取り込み後の CI と成果物の照合は `ci/CI_VERIFICATION.md`。**CI の対象 SHA（`de1f668`）と、実モデル試験の対象 SHA（ソース `3c6d7d7`）は別に記録する**

## 3. 差分（`de1f668` 時点で再集計）

| 比較 | コミット数 | 規模 |
|---|---|---|
| main（`992e16d`）→ PR #22 head | 26 | 1,026 ファイル、117,971 行の追加 |
| rc3（`e346562`）→ PR #22 head（今回取り込んだ分） | 19 | 920 ファイル、95,809 行の追加・59 行の削除 |

本書と CI 記録を加えたコミットで、さらに数ファイル増える。最新の数値は PR #22 の画面で確かめる。

| 区分 | 内容 |
|---|---|
| Skill のソース | `skill/nrmo/SKILL.md`（rc3→rc7 の規則の変更）、`skill/release.json`（版と起点）、`skill/tools/build_package.py`（出力先を版から決めるだけの変更）、`.github/workflows/skill-package.yml`（artifact 名を rc7 に） |
| v7.3 正典・参照資料 | **変更なし**。17参照（正典・PDF・パッチ・ALB 資料を含む）と PDF_CAVEATS.md は、rc3 とバイト単位で同じ。`.tex`、`NRMOIntegrated/`、`ALB/` の変更もなし |
| 版の保存 | `skill/archive/v1.0.0-rc3/`〜`v1.0.0-rc7/`（各版の SKILL.md・MANIFEST・release.json・nrmo.skill・BUILD_MANIFEST・NOTE） |
| 試験記録 | `skill/tests/rc3/`〜`rc7/`（PLAN、BUILD_MANIFEST、run-01 の入力・出力全文・生ログ・採点・報告、追記した再点検と訂正） |
| その他 | `skill/tests/OWNER_APP_TEST.md`（rc7 用）、`skill/tests/T3_ADOPTION_RULE_OPEN.md`（追記）、`skill/MANIFEST.md`（rc7 の対象範囲） |
| 生ログ | 各版の `run-01/raw/` が約 7MB、5版で約 36MB（作業ツリー上）。本人の指示により保持する |

## 4. CLI での検証結果（実モデル試験、各版 11入力×3回＝33件）

| 版 | CLI | PASS | FAIL | 判定不能 | 確認された欠陥（再点検後） | 総合 |
|---|---|---|---|---|---|---|
| rc3 | 2.1.305 | 19 | 8 | 6 | FAIL 8件。ほかに T3b_r1（数値の取り違え）と、rc4 報告に追記した T3b_r3（ε の所在の誤認） | 不合格 |
| rc4 | 2.1.305 | 27 | 0 | 6 | 3件の実行に4件（追記で訂正） | 合格とせず |
| rc5 | 2.1.306 | 26 | 1 | 6 | 2件の実行に2件 | 合格とせず |
| rc6 | 2.1.306 | 27 | 0 | 6 | 1件の実行に1件（追記で訂正） | 合格とせず |
| **rc7** | 2.1.306 | **33** | **0** | 0 | **0** | 基準をすべて満たした（所見2件） |

- rc3〜rc6 の判定不能（T3 の採用ルール）は変更していない。rc7 では対象範囲の変更により、この観点は「対象外」
- 各版の基準は実行前に PLAN に固定した。採点者は Skill の作成者と同じ Claude で、理由を各 GRADES.md に残した
- 限界：各入力3回。欠陥 0件は、この33件で見つからなかったことを示すだけ

## 4b. CI（対象 `de1f668`）

| ワークフロー | イベント | 結果 |
|---|---|---|
| Skill package checks | push / pull_request | success / success |
| Validate NRMO provenance | pull_request | success |

- 成果物の内包 `nrmo.skill`：sha256 `ad9db63be6ac3cbf3414246d83b58f5ad5cb4fadfc4341e4344a6f8b3897f426`。試験済み rc7 の固定ハッシュと一致し、archive の固定版とバイト単位で同一
- 収録19ファイル：試験時の BUILD_MANIFEST と 19/19 一致。BUILD_MANIFEST の違いは `source_commit` だけ（CI＝`de1f668`、試験＝`3c6d7d7`）
- 詳細は `ci/CI_VERIFICATION.md`

## 5. アプリ確認の結果（未記入）

| 区分 | 件数 |
|---|---|
| 実施 | — / 15 |
| PASS | — |
| FAIL | — |
| 無効 | — |
| 確認された欠陥 | — |

記録表：`app/RECORD.md`。手引き：`app/QUICKSTART.md`。現在は全件 NOT_RUN。

## 6. 残る判断（アプリ確認の後）

1. 正式版として承認するか（アプリ確認の結果を踏まえて）
2. PR #22 を main へマージするか（作業ブランチの取り込みと、生ログの保持は済み）

ALB の採用、Business 版への反映は、この判断に含めない。
