# rc7 固定記録（試験済み・アプリ確認用の提出物）

| 項目 | 値 |
|---|---|
| 版 | nrmo-skill v1.0.0-rc7 |
| ソースコミット | `3c6d7d76f30f9e74f936a9b6b8f6a713dc613f5d` |
| nrmo.skill の sha256 | `ad9db63be6ac3cbf3414246d83b58f5ad5cb4fadfc4341e4344a6f8b3897f426` |
| ツリーハッシュ | `c9eb69d1352b2e243629ed523acdb0d336cb113f53524cf1a317ba7b5900e376` |
| BUILD_MANIFEST.json の sha256 | `ee0f5ae3b7c795bc92236d4370c933198c32a193d0a2c2673bcb7b1695e00347`（試験前に固定した ../../tests/rc7/BUILD_MANIFEST.json と同一） |
| 試験前の固定コミット | `8385ffa` |
| 試験結果 | ../../tests/rc7/run-01/ |

この nrmo.skill は、試験前に対象コミットから生成したパッケージそのもので、CLI 試験ではこれを展開した19ファイルを読み込ませた（試験前後とも 19/19 一致）。ZIP の19メンバーは BUILD_MANIFEST と一致する。SKILL.md・MANIFEST.md・release.json はソースコミットのまま保存した。

試験結果の要約：33件すべて PASS、確認された欠陥 0件、所見 2件。T3 は rc7 の期待（ALB を採用・適用しない、選択待ちで止めない、正典と Strong Engine で支援、数値と ε を区別）で採点した。rc3〜rc6 の判定不能は変更していない。claude.ai アプリ試験は NOT_RUN。

## 候補版としての固定（2026-10-21、本人の指示）

rc7 を候補版として固定した。現時点で rc8 は作らない。固定の対象は上の表のソースコミット・パッケージ・BUILD_MANIFEST で、以後のアプリ確認はこの nrmo.skill を使う。

- 通常版の対象範囲は、本人の決定により「v7.3 正典による支援＋通常の StrongEngine Ω Full」。ALB／NPMO は研究草稿として通常運用から除外する。この対象範囲は決定済みで、判断待ちにしない。正式版の承認とは別の事項である
- CLI 試験 33件（tests/rc7/run-01/）と、アプリ確認 15件（tests/rc7/app/RECORD.md、現在 NOT_RUN）は別々に記録する
- 所見2件（T1a_r3、T5e_r1）は記録として保持する。T5e_r1 は、事前基準が「無関係な翻訳へ判定形式を強制しない」であるため、発動したことだけを理由に不合格へ変更しない
