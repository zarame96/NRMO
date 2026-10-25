# rc4 保存記録

ソースコミット 2b3fef34ae245d684ee93a784be72527c3697c5d の SKILL.md、MANIFEST.md、release.json を変更せずに保存した。BUILD_MANIFEST.json は試験前に固定した記録（../../tests/rc4/BUILD_MANIFEST.json）の写し。nrmo.skill は同じコミットから再生成したもので、sha256 は記録値 e65b735057143497100c3a66df7150f3072acfcbe9d765523c3f66703418b0e3 と一致する。

rc4 の実モデル試験（33件、../../tests/rc4/run-01/）：T3 以外 PASS 27/27、T3 暫定境界 PASS 6/6、T3 採用ルール 判定不能 6/6。T3 で確認された欠陥は3件の実行に4件（うち T3b_r1 の2件は rc5 作成時の再点検で追記）。総合合格としない。rc4 の結果を rc5 の合否に転用しない。
