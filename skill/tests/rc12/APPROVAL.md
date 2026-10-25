# nrmo Skill v1.0.0-rc12 — 所有者正式承認

承認日：2026-10-25（JST）  
承認者：所有者（Takashi Ikeya）

## 決定

個人版 nrmo Skill `v1.0.0-rc12` を、通常運用に用いる正式版として承認する。

試験済みパッケージをそのまま正式版とし、承認のために Skill 本体、参照資料、PDF、パッケージを変更・再生成しない。

## 固定対象

| 項目 | 値 |
|---|---|
| ソースコミット | `ef8db358439ed39782153141a341565e02080dc5` |
| パッケージ | `skill/archive/v1.0.0-rc12/nrmo.skill` |
| SHA-256 | `782af0c01a5a069f88c1661b94f08fbf61a486195ae2051cea0116c279b3639c` |
| 構成 | 22メンバー、21参照 |
| v7.3 PDF SHA-256 | `a4f6942369a53981bddf95c65c2cdd73e1751f960b01c7d547201837844f1783` |

## 承認範囲

- v7.3 Canon と Publication of Record に基づく意思決定支援
- NRMOによる破綻境界・可逆性・A_allowedの統治
- StrongEngine Ω FullによるA_allowed内の候補生成
- Canon → RUNTIME_RECONCILIATION → 運用Markdownの参照順
- lifecycle／HOLD、Passive Ruin、Ruin二軸、εのrc12運用規則
- ALB／NPMOを通常判定へ接続しない動作

## 検証根拠

- Claude Code CLI：有効66件が事前基準を達成
- claude.ai アプリ：本文15/15 PASS
- 対象相談のnrmo使用表示：12/12
- 翻訳での非発動：3/3
- アプリA3のメタ発話：0/3
- PDF読み込み表示：あり
- package／provenance CI：成功
- CI成果物：固定パッケージとバイト単位で一致

詳細は `skill/tests/rc12/run-01/` と `skill/tests/rc12/app/` を参照する。

## 受容した制限

- claude.aiではPDFファイルの読み込み表示を確認したが、必読ページ463–474の範囲までは表示から確認できない
- claude.aiの確認はメモリ／過去チャット参照オンで実施
- CLI終了応答で軽度のメタ発話が2件あった。アプリA3では0/3
- 反復試験は有限であり、欠陥が存在しないことの証明ではない

これらは記録を維持するが、通常運用の正式承認を妨げる重大な境界違反とは判断しない。

## 対象外

この承認は次を意味しない。

- ALB／NPMOの採用
- ALB第2章または採用ルールの確定
- Business版への反映
- DecisionCompassの変更
- 上記研究事項の理論的完成

PR #23の取り込みとPR #22からmainへの取り込みは、Gitの統合作業として別途確認する。
