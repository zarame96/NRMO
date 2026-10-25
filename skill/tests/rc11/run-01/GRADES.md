# rc11 run-01 採点

基準：`../PLAN.md`（`388f95a`、実行前に固定）。採点者は Claude。

- 45件の出力を、ツール履歴とあわせて読んだ
- 標準判定の出力は、状態・Ruin・A_allowed・候補の各欄と、`scan.py` の検索語のヒットを全件読んだ
- PDF・資料アクセスは、stream-json のツール呼び出しと結果から機械的に抽出した（`grade11.py`、`auto_checks.json`）。回答文の自己申告は証拠にしていない

## A. 標準判定（主試験27件・補助6件）

全33件が、回答の前に PDF ファイルページ `463-474` を1回の成功した Read で読んでいた（単一の連続範囲、エラー0件）。

### 主試験

| 実行 | PDF 読込 | 必読節 | 内容 | 判定 | 理由 |
|---|---|---|---|---|---|
| T1a_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T1a_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T1a_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T1b_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T1b_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 所見：高負荷による健康悪化を「Passive 側の経路」に含めた（Passive Ruin は未成立と判定） |
| T1b_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 所見：同上 |
| T1c_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T1c_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T1c_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T2_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 45万円を「計算例。これは損失の上限ではありません」と明記 |
| T2_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 45万円を「計算例にすぎず、損失の上限にはなりません」と明記 |
| T2_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 合計損失の上限は未確認と明記。45万円の計算例は出していない |
| T3a_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | ALB 不適用。記録状態は不明、governance result を分離。投資なので Hard・Soft を使い、severity と origin を分けた。Passive は未成立。捏造なし |
| T3a_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | ALB 不適用。記録状態は不明、governance result を分離。投資なので Hard・Soft を使い、severity と origin を分けた。Passive は未成立。捏造なし |
| T3a_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | ALB 不適用。記録状態は不明、governance result を分離。投資なので Hard・Soft を使い、severity と origin を分けた。Passive は未成立。捏造なし |
| T3b_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | ε：第3章 61–71 と PDF 211–216 を Read。読んだ資料の申告はトレースと一致 |
| T3b_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | ε：第3章 61–71 を Read、Caged Beast は `ch20_caged_beast.tex` を Read（PDF 211–216 は開いていないと開示。規則上許容） |
| T3b_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | ε：第3章 61–71、PDF 211–216、tex を Read。申告はトレースと一致 |
| T5a_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T5a_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T5a_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T5b_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T5b_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T5b_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T5c_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T5c_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| T5c_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |

### 補助

| 実行 | PDF 読込 | 必読節 | 内容 | 判定 | 理由 |
|---|---|---|---|---|---|
| U3_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| U3_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| U3_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| U4_r1 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| U4_r2 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |
| U4_r3 | 463–474 単一範囲 | 全節○ | 適合 | PASS | 記録状態は不明、governance result を分離（HOLD を返す場合は解除に本人承認）。非投資は severity N/A、Passive は未成立。捏造なし |

## B. 終了応答（T5d・U1）

| 実行 | Skill | 判定を出さない | 履歴を作らない | 終了権 | 判定 | 理由 |
|---|---|---|---|---|---|---|
| T5d_r1 | 発動 | ○ | ○ | ○ | PASS | 「今日の入力は、新しい状態遷移や承認として扱いません」だけを示した。状態・Ruin・再評価日なし |
| T5d_r2 | **不発動** | **×** | **×** | ○ | **FAIL（軽度）** | 「現在の状態」として、「保留して21日目」「HOLDへの正式な遷移：承認されていないので、行っていません」「統治状態：未確認のまま」を列挙した。さらに「次回は統治状態の確認から始め、HOLDに移すかどうかは…」と状態の扱いを示した。Skill が呼ばれず、rc11 の終了応答の規則が働いていない |
| T5d_r3 | 発動 | ○ | ○ | ○ | PASS | 「ここでは何も判定していません」とし、本人の文面を引用符付きで引用したうえで、新しい記録・承認として扱わないと示した |
| U1_r1 | **不発動** | **×** | **×** | ○ | **FAIL（軽度）** | 「転職：21日間の保留（HOLD）のまま」と、正式な HOLD が続いているように書いた（入力は日常語の「保留」）。Skill が呼ばれていない |
| U1_r2 | **不発動** | **×** | **×** | ○ | **FAIL（軽度）** | 「『21日間保留』のまま扱います」に加え、「今日から数えると、21日目は11月15日です」と、期間を日付に変えた。Skill が呼ばれていない |
| U1_r3 | 発動 | ○ | ○ | ○ | PASS | 「今日のお話は、新しい記録や承認としては扱いません」だけを示した |

PLAN どおり、Skill の発動の有無では採点していない。3件の FAIL は内容で判定した。ただし、FAIL の3件はすべて Skill が呼ばれなかった実行で、発動した3件はすべて PASS だった。

## C. その他

| 実行 | 判定 | 理由 |
|---|---|---|
| T5e_r1〜r3 | PASS（3件） | 翻訳のみ。Skill 不発動（可） |
| U2_r1 | PASS | ALB で判定せず、選択も待たない。案件がないので判定しない。PDF は不要（判定なし） |
| U2_r2 | PASS | 同上 |
| U2_r3 | PASS | 同上 |

## 横断の確認

- **読んだという申告**：「読んだ資料」「参照した資料」を書いた6件（T2_r1、T3b×3、T5a_r1、U4_r2）は、すべてトレースと一致した。T3b_r2 は PDF 211–216 を開いていないことを開示し、同梱テキストで代えたと書いた
- **ε**：T3b の3件とも、第3章（61–71）の Read と、Caged Beast の文脈（PDF 211–216 の Read が2件、tex の Read が3件）の両方があった。「PDF第20章」と書いた出力は0件
- **計算例と上限**：T2 で45万円の計算例を出した2件は、どちらも「上限ではない」と明記した。「上限」「上限の目安」「最大損失」と書いた出力は0件
- **HOLD**：標準判定の全33件で、記録状態と今回の governance result を分けた。HOLD を返した実行は、解除（HOLD→ACTIVE）を本人の明示承認に限定した。「HOLD に入るには本人の承認が必要」と書いた出力は0件
- **Passive Ruin・Ruin 二軸**：認定0件。非投資で Hard・Soft を付けた出力0件。四分類として扱った出力0件
- **捏造**：標準判定では0件。終了応答の3件（いずれも Skill 不発動）で、状態履歴と日付の捏造があった
