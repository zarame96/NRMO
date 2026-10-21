# nrmo Skill — 個人版候補の固定記録

| 項目 | 値 |
|---|---|
| 版 | **nrmo-skill v1.0.0-rc5**（候補版・実動作試験は tests/rc5/ で実施） |
| 起点 | 2b3fef34ae245d684ee93a784be72527c3697c5d（rc4） |
| 前版 | archive/v1.0.0-rc4/、archive/v1.0.0-rc3/ に SKILL.md・MANIFEST.md・release.json・パッケージを保存。rc3 は総合不合格（tests/rc3/run-01/）。rc4 は総合合格とせず（tests/rc4/run-01/。再点検の追記あり） |
| 現行ソース | nrmo/。版と不変参照の sha256 は release.json |
| 現行パッケージ | `python3 skill/tools/build_package.py` が dist/nrmo-rc5/ に出力する nrmo.skill。試験に使った固定値は tests/rc5/BUILD_MANIFEST.json |
| モデル試験 | 計画・期待する応答・合格基準は tests/rc5/PLAN.md（実行前に記録） |
| claude.ai 保存版 | 最後に確認されたのは rc1。rc3〜rc5 との一致・アプリ動作は未確認 |

## rc4 からの変更（SKILL.md のみ。正典の適用範囲は広げない）

1. 典拠の所在：`P(Ruin | a) ≤ ε` は第20章（ch20_caged_beast.tex）と v7.3 PDF 第3章（評価期間 T 付き）にもあり、草稿にもある。`nrmo_system_v7_3.md` には同じ式が無い。資料内の不存在は、確かめた範囲を限って述べる。
2. 判定式の扱い：式の説明と本人宣言値による仮定計算は可。不等式の成立だけから NRMO 全体の PASS・拒否なし・A_allowed への採用・実行推奨を導かない。破滅の定義・評価期間・推定の根拠・他の制約との整合を分け、未確認は未確認とする。
3. 経過時間と破滅：経過時間だけで Soft / Passive Ruin を認定しない。停滞・悪化の標識・破滅への到達を区別する。ALB の採用未決を、正典で可能な支援まで止める理由にしない。

rc3→rc4 の変更（安全案内の照合、本人が限定した範囲、観測の対象・時点・条件、数値の意味）は維持する。正典・PDF・パッチ・ALB を含む17参照と PDF_CAVEATS.md は rc3・rc4 とバイト単位で同じ。

## 再現方法

リポジトリの対象コミットをクリーンに checkout して次を実行する。Python 標準ライブラリのみを使う。

```sh
python3 skill/tools/build_package.py
```

dist/nrmo-rc5/ に nrmo.skill と BUILD_MANIFEST.json を出力する。同梱パス、重複、CRC、全内容のソース一致、同一実行環境内での決定性、内容不一致の拒否を確認する。ZIPの圧縮ライブラリが異なる環境間で同一ハッシュになる保証とは区別する。

## 判断の分離

Skill の実動作試験・正式版承認、ALB 第2章の採用、T3 の採用ルール、PR #22 のマージは別判断。パッケージ検証はこれらの承認や成功を代替しない。監査最終版の未回収箇所は未回収のまま。
