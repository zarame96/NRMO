# Phase F 完了報告 — 全体統合 + NRMO Integrated PDF 再生成

作成日: 2026-05-30
指針: NRMO_Realignment_Master_Spec.md §6 / SESSION_HANDOFF §4
成果物: `NRMO_Integrated_System_v7_2_rev2_EN.pdf` (511ページ, 英語のみ・CJKエラー0)
source: `NRMO_Integrated_System_v7_2_rev2_source.zip` → `integrated_v72/`
master: `NRMO_Complete_v5_5.tex` (title = "NRMO Integrated System v7.1", pdflatex)

---

## 1. 何をしたか

1. v7.2-rev2 LaTeX source を展開。master は `NRMO_Complete_v5_5.tex`
   (Makefile: `pdflatex -shell-escape` 3パス + bibtex + makeindex)。
2. **latex_patches の 7 章を chapters/ に上書き** (v7 Realignment セクション挿入済み):
   ch20_strong_engine, ch27_time_horizon, ch30_success_definitions,
   ch_part12_methodology, ch_part9_omega_full,
   ch_part_xiii_v63_vnext_plus, ch_part_xiii_v70_collective。
3. **Phase D/E の成果を本文に統合** (英語節を追記):
   - Phase D → `ch_part_xiii_v70_collective.tex` 末尾に
     「v7 Phase D: Collective Two-Layer Connection and Validation」
   - Phase E → `ch20_strong_engine.tex` 末尾に
     「v7 Phase E: DecisionCompass Two-Layer with Real Governance」
4. pdflatex で再生成 (多パス, 相互参照解決)。

---

## 2. 結果

| 項目 | 値 |
|---|---|
| ページ数 | **511** (元 v7.1 PDF=478, 未修整 v7.2-rev2=482, +realignment/PhaseD/E) |
| v7 Realignment 節 (本文) | 8 箇所 |
| Two-Layer / Real-Side / MaxForward 言及 | 15 箇所 |
| Phase D/E 節 | 反映済 (本文 + 目次) |
| 新規致命エラー (patch 由来) | **なし** |

---

## 3. 英語のみ化 (English-only cleanup)

本書は英語論文 (Integrated) であり日本語本文は意図されていない。当初 pdflatex が
CJK Unicode エラーを出したのは、英語散文ではなく **master 取り込みファイルに残っていた
残留日本語** が原因だった。以下4箇所を英語/ローマ字へ修整 (`latex_english_only_fixes/`):

1. `frontmatter/final_build_statement.tex`: 締めのモットー (日本語) を英訳に置換。
2. `chapters/ch_part_xiii_v52_to_v62.tex`: 文明名の括弧内日本語グロス
   (印度/サハラ以南/ポリネシア/中央アジア遊牧/先住アメリカ) を削除 (英語ラベルは保持)。
3. `chapters/ch_part_xiii_world_simulation_vision.tex`: 歴史用語をローマ字化
   (宗族→zōngzú, 科挙→kējǔ, 徳治→dézhì, 外戚→wàiqī, 鎖国→sakoku,
    一向一揆→Ikkō-ikki, 廃仏毀釈→haibutsu-kishaku, 本家・分家・養子先→honke/bunke/yōshi-saki,
    寺社預け→jisha-azuke, 座→za, 武家奉公→buke-hōkō, 江戸→Edo, ワクフ→waqf)。

結果: **CJK Unicode エラー 0 / 出力 PDF 内の CJK 文字 0**。完全に英語のみ。
(注: master の listings `literate` 表 (仮名→空白) は lstset 設定で通常組版されないため残置。)

### 既存ベースラインの残課題 (Phase F 由来でない)
- **`Illegal pream-token (C)`** (42件): source の某章が未定義列型 `C` を使用 (pass0 既存)。
  patch には `C{` 列無し。`\newcolumntype{C}{...}` を preamble に1行追加すれば解消可能 (要指示)。
- **undefined reference 6件**: source 既存プレースホルダ
  (ch:ch13/14-placeholder, ch:invariants-unified, ch:vnext-state,
   sec:nrmo-veto-rules, sec:v21-integrated-flow)。追記分の参照は解決済。

---

## 4. 再生成方法

```bash
cd integrated_v72
# latex_patches の章を chapters/ に上書き後:
make all          # pdflatex 3パス + bibtex + makeindex
# 出力: NRMO_Complete_v5_5.pdf
```

---

## 5. Phase A–F 全完了

```
A 再配置原則書             [完了]
B 中核コード v7_two_layer    [完了]
C LaTeX 7章 realignment     [完了]
D collective 実コード接続    [完了] engine/v7_collective_two_layer.py
E DecisionCompass 二層化     [完了] engine/v7_decision_compass.py
F 統合 + PDF 再生成          [完了] 本書 / 再生成 PDF 511p
```

## 6. 任意の残作業 (今後)
- 日本語描画が必要なら master を xelatex/lualatex + CJK へ移行 (要 fontspec/luatexja)。
- `CollectiveDomainDynamics` を実 agent population step へ完全接続 (現状は真 dynamics の代理)。
- investment/romance の §3 再検証 (`NRMO_v6_to_v6_1_..._Bundle_20260529.zip` 再アップ要)。
