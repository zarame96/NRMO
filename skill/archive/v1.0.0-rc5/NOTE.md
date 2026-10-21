# rc5 保存記録

ソースコミット 834ed076c145a10c2f9c64b4b4b67c1b1d0224d9 の SKILL.md、MANIFEST.md、release.json を変更せずに保存した。BUILD_MANIFEST.json は試験前に固定した記録（../../tests/rc5/BUILD_MANIFEST.json）の写し。nrmo.skill は同じコミットから再生成したもので、sha256 は記録値 b27083724a11742f64b861dbe6bb468bc2af72e572be81e9a007a6344c6670fa と一致する。

rc5 の実モデル試験（33件、../../tests/rc5/run-01/、CLI 2.1.306）：PASS 26、FAIL 1（軽度）、T3 判定不能 6（暫定境界 6/6 PASS）。確認された欠陥は2件の実行に2件（T1b_r1、T3b_r3）。総合合格としない。T1b_r1 の欠陥の理由は rc6 作成時に訂正を追記した。rc5 の結果を rc6 の合否に転用しない。
