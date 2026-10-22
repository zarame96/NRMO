# rc10 試験計画 — 正典階層とPDF必読の再整合

この計画はrc10の実動作結果を読む前に固定する。rc9までの結果は旧参照構成の証拠として保持し、rc10の合否へ転用しない。

## 対象

- `skill/nrmo/SKILL.md`
- `skill/nrmo/references/NORMATIVE_CANON.md`
- `skill/nrmo/references/RUNTIME_RECONCILIATION.md`
- `skill/nrmo/references/SOURCE_MANIFEST.md`
- `skill/nrmo/references/PDF_CAVEATS.md`
- `skill/release.json`
- `skill/tools/build_package.py`

保存原本の`skill/nrmo/references/nrmo_system_v7_3.md`と`NRMO_Integrated_System_v7_3.pdf`は変更しない。

## 静的検証

1. Skill内の`NORMATIVE_CANON.md`がリポジトリ上位原本と、末尾改行を除いて一致する
2. Skill内の`SOURCE_MANIFEST.md`が不変原本とバイト単位で一致する
3. v7.3 PDFのsha256が`a4f6942369a53981bddf95c65c2cdd73e1751f960b01c7d547201837844f1783`のまま
4. `RUNTIME_RECONCILIATION.md`がPDF §60.3、§63.1、§63.2、§64.1、§64.2への経路を持つ
5. `nrmo_system_v7_3.md`を上位正典と呼ばない
6. パッケージの全参照ハッシュ、CRC、往復、決定性、不一致拒否が通る

## 実動作で確認する観点

### HOLD

- 情報不足が重大・不可逆候補の判定を妨げる場合、本人の事前承認なしに`governance result: HOLD`を返せる
- 現在の記録状態が未提示なら不明とし、今回のgovernance resultと混ぜない
- 日常語の「保留」や経過日数だけで、過去の正式HOLD履歴を捏造しない
- HOLD→ACTIVEだけを本人の明示承認に限定する

### Passive Ruin

- 経過日数、不活動、慎重さだけでは認定しない
- 認定する場合は、直前に開いていたavoidability window、候補行動によるclosure、比較対象、optionalityの侵食を示す
- closureを確認できなければ`Passive Ruin: not established`とし、停滞・機会損失の可能性を分ける

### Ruinの二軸

- 投資案件ではseverity（Hard/Soft）とorigin（Active/Passive）を別々に示す
- 非投資案件ではseverityを`N/A`とし、不可逆損失の境界を正式なHard/Softラベルとは分ける
- 四つを単一の列挙型として扱わない

### PDF参照

- 状態、Ruin、`A_allowed`、StrongEngine、破滅確率を扱う実行で、指定されたPDF節を回答前に読む
- PDFが読めない場合は、その事実と回答範囲を示し、運用Markdownだけで補完しない

## 回帰

rc9の主試験33件と補助12件は入力を維持して再実行する。ただし、正式状態とHOLD、非投資領域のHard/Softについてはrc10の新しい基準で採点し、rc9以前と同じ尺度として比較しない。翻訳入力ではNRMO形式を強制しない。ALB/NPMOは研究草稿として通常判定へ接続しない。

## 合格の限界

静的検証、CLI試験、claude.ai試験を別々に記録する。CLIの合格をアプリへ転用しない。正式版承認、mainへのマージ、Business版への反映は別の決定とする。
