# rc8 claude.ai アップロード互換版

rc8本体・参照資料・過去の試験記録は変更しない。rc8-upload1 は同じrc8パッケージから、SKILL.md冒頭のYAML descriptionだけを235文字から147文字へ短縮した別成果物。

- 元パッケージ SHA-256：`f6b90797f696044a32aecf05a400db5c468c2a8cb0e4fdb34e0518f1faa5d9c4`
- 互換版 SHA-256：`0c2cbab1f0cab12ae308d52309c5eaaf2608c324b70725238e7865031fe35b7c`
- 元ソース：`e168af2acdce4f5f8a045a7740b61a197b519ced`
- 再生成：`python3 skill/tools/build_upload_variant.py`

## 根拠と限界

2026-10-22確認のclaude.ai公式手引きはdescriptionを200文字以下としている。一方、APIのAgent Skills資料は1024文字以下としており、製品ごとの記載が異なる。ここではclaude.aiの短い方に合わせる。

- https://support.claude.com/en/articles/12512198-how-to-create-custom-skills
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

画面の一般的な「アップロードに失敗」表示だけから、説明文が原因だったとは断定しない。元rc8はZIPのCRC・19メンバー・固定ハッシュに異常なし。短縮後の説明文も、意思決定相談での使用、各理論の照会、ALBを研究理論の質問に限る対象範囲を示す。

Skill本文はバイト単位で同じ。18参照もすべてバイト単位で同じ。Skill名・内部ルートはnrmoのまま。説明文は発動判定に使われるため、互換版の発動とアプリ応答は未検証。元rc8のClaude Code 33件の記録はそのまま保持し、互換版の実動作試験結果へ読み替えない。

## 登録と試験

このフォルダーの`nrmo.skill`を使って再度登録する。失敗表示だけを理由に既存の正常なSkillを削除しない。登録できたら有効なnrmoを1件にし、新規チャットで確認する。アプリ15件の入力と採点基準は`../../tests/rc8/app/QUICKSTART.md`を使い、記録には必ず`rc8-upload1`と上記のハッシュを書く。互換版の応答を元rc8の記録と混ぜない。

現時点：互換版のアップロードNOT_RUN、モデル実動作NOT_RUN。正式版承認・mainへのマージ・Business版更新は行わない。
