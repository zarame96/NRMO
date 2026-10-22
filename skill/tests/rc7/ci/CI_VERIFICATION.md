# rc7 の CI 確認（PR #22 への取り込み後）

**CI の対象 SHA と、実モデル試験の対象 SHA は別のものとして記録する。**

| 区分 | 対象 SHA | 内容 |
|---|---|---|
| 実モデル試験（CLI 33件） | `3c6d7d76f30f9e74f936a9b6b8f6a713dc613f5d`（ソース） | パッケージの固定は `8385ffa`。試験時の `../BUILD_MANIFEST.json` はそのまま保持（source_commit＝3c6d7d7） |
| CI（取り込み直後） | `de1f6681b24ff52b2a8b4d7c63453b76abcd82ed`（PR #22 の head） | `3c6d7d7` 以後、`skill/nrmo`・`skill/release.json`・`skill/tools` は変更なし |

## 取り込み

- 取り込み前：PR #22 のブランチ `docs/ext-nonoverlap-v0.1` は `e34656262569751b2037d544eb6c8d1cada4cd11`、作業ブランチ `claude/rc3-production-test-33-fsj4v0` は `de1f6681b24ff52b2a8b4d7c63453b76abcd82ed`
- 祖先関係：`e346562` は `de1f668` の祖先。PR 側にだけあるコミットは 0件、作業ブランチ側は 19件。分岐なし
- 早送り（強制なし）で取り込んだ：`e346562..de1f668`

## CI の結果（対象 `de1f668`、2026-10-21）

| ワークフロー | イベント | run | 結果 |
|---|---|---|---|
| Skill package checks | push | [39608368308](https://github.com/zarame96/NRMO/actions/runs/39608368308) | success |
| Skill package checks | pull_request | [39608375614](https://github.com/zarame96/NRMO/actions/runs/39608375614) | success |
| Validate NRMO provenance | pull_request | [39608375645](https://github.com/zarame96/NRMO/actions/runs/39608375645) | success |

## 成果物の照合（pull_request の run 39608375614、artifact 12348822071）

| 項目 | 結果 |
|---|---|
| artifact 名 | `nrmo-rc7-de1f6681b24ff52b2a8b4d7c63453b76abcd82ed` |
| 外側の artifact ZIP の sha256 | `dc279f62032a51bcb58cc8bda79edd2e638528be1dee9c435ba2690cf694b712`（push の run の artifact 12349352031 も同じ digest）。内包の nrmo.skill のハッシュとは別 |
| 内包 `nrmo.skill` の sha256 | `ad9db63be6ac3cbf3414246d83b58f5ad5cb4fadfc4341e4344a6f8b3897f426` — **試験済み rc7 の固定ハッシュと一致** |
| `skill/archive/v1.0.0-rc7/nrmo.skill` との比較 | バイト単位で同一 |
| 収録ファイル | 19メンバー。試験時の BUILD_MANIFEST の `file_sha256` と **19/19 一致** |
| CI の BUILD_MANIFEST（`BUILD_MANIFEST.ci-de1f668.json`） | 試験時のものとの違いは `source_commit` だけ（CI＝`de1f668`、試験＝`3c6d7d7`）。package_sha256・tree_sha256・file_sha256・checks は同じ |
| CI の checks | unchanged_references 17、archive_members 19、round_trip・same_runtime_reproducible・mismatch_rejection いずれも true |

CI は、パッケージの形式・参照ハッシュ・再現性を検証するもので、Skill の実動作を検証するものではない。実動作は CLI 33件（`../run-01/`）とアプリ確認（`../app/`、NOT_RUN）で別に記録する。
