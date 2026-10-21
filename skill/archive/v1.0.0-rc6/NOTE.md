# rc6 固定記録（試験済み・アプリ確認用の提出物）

rc6 は CLI で実モデル試験を行った版として、ここに固定する。rc7 は作っていない（本人の指示）。

| 項目 | 値 |
|---|---|
| 版 | nrmo-skill v1.0.0-rc6 |
| ソースコミット | `e46019da1c5a58f70adcf890db1670b328c97631` |
| nrmo.skill の sha256 | `5ed57a3b84eb2ace82a5aa757df189fd39b28435c8468343e3ec5e0a33f8b006` |
| ツリーハッシュ | `e71822031d1dfdff5f825758335dcb2ea9624d3d1f60bc9687a1304d727ed402` |
| BUILD_MANIFEST.json の sha256 | `4ec877e5e4d30a92565d2a68e0cedd086f680714fc9796615733fee3366773f6` |
| 試験前の固定コミット | `54160ba`（../../tests/rc6/BUILD_MANIFEST.json） |
| 試験結果 | ../../tests/rc6/run-01/（結果コミット `51a5bff`。T3b_r2 の再点検は同じ報告の末尾に追記） |

## 一致の確認

- この nrmo.skill は、ソースコミットから `python3 skill/tools/build_package.py` で再生成したもの。sha256 は試験前の記録値と一致する
- 同時に生成された BUILD_MANIFEST.json は、試験前に固定した `../../tests/rc6/BUILD_MANIFEST.json` とバイト単位で同じ
- ZIP の19メンバーは、BUILD_MANIFEST の `file_sha256` と 19/19 一致する
- CLI 試験（tests/rc6/run-01/）では、このパッケージを展開した19ファイルを読み込ませた。試験前後とも 19/19 一致
- この時点のリポジトリの `skill/nrmo/SKILL.md` は、ソースコミットの SKILL.md と同一

## 試験結果の要約（詳細は tests/rc6/run-01/REPORT.md）

T3 以外は PASS 27/27。T3 は暫定境界 PASS 6/6、採用ルール 判定不能 6/6。確認された欠陥は、再点検後で1件の実行に1件（T3b_r2）。総合合格としない。claude.ai アプリ試験は NOT_RUN（../../tests/OWNER_APP_TEST.md）。
