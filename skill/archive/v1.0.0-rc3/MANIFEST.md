# nrmo Skill — 個人版候補の固定記録

| 項目 | 値 |
|---|---|
| 版 | **nrmo-skill v1.0.0-rc3**（候補版・実動作試験未実施） |
| 起点 | da4027075a7b4625b4e98c3d7004defe1e0652b1（rc2） |
| 前版 | archive/v1.0.0-rc2/ に元のパッケージ・MANIFEST・SKILL.md を保存 |
| 現行ソース | nrmo/。版と不変参照の sha256 は release.json |
| 現行パッケージ | Skill package checks の artifact 内の nrmo.skill。旧パッケージを新版と誤認しないよう、ルートの旧 nrmo.skill は archive へ移動 |
| 固定記録 | 同じ artifact の BUILD_MANIFEST.json に対象コミット、パッケージ sha256、ツリーハッシュ、全ファイル sha256、検証項目を収録 |
| モデル試験 | NOT_RUN。実行計画は tests/rc3/PLAN.md |
| claude.ai 保存版 | 最後に確認されたのは rc1。rc3 との一致・アプリ動作は未確認 |

## rc2 からの変更

許容行動の番号と意味を全候補・推奨・実行ステップに照合する。対象・行為者・費用・期間・確約・権限・組合せの制約を広げない。日常語の保留を正式 HOLD とみなさない。本人の相談終了権を保つ。専用非発動切替は本人の要件変更で対象外とし、過去の T4 記録は保存する。

個人版の Vision を維持する。PDF_CAVEATS.md を版と実装根拠の注意として追加し、従来の正典・PDF・パッチ・ALB を含む17参照は rc2 とバイト単位で維持する。実行時に release.json の SHA-256 と照合し、不一致ならパッケージ検証を失敗させる。

## 再現方法

リポジトリの対象コミットをクリーンに checkout して次を実行する。Python 標準ライブラリのみを使う。

```sh
python3 skill/tools/build_package.py
```

dist/nrmo-rc3/ に nrmo.skill と BUILD_MANIFEST.json を出力する。同梱パス、重複、CRC、全内容のソース一致、同一実行環境内での決定性、内容不一致の拒否を確認する。ZIPの圧縮ライブラリが異なる環境間で同一ハッシュになる保証とは区別する。CI の artifact は保存期限があるため、期限後は対象コミットから生成し直せる。

## 判断の分離

Skill の実動作試験・正式版承認、ALB 第2章の採用、T3 の採用ルール、PR #22 のマージは別判断。パッケージ検証はこれらの承認や成功を代替しない。監査最終版の未回収箇所は未回収のまま。
