# NRMO — Non-Ruin Maximizing Objective

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22018104.svg)](https://doi.org/10.5281/zenodo.22018104)

破滅を避け、前へ。停滞も死。

個人開発の意思決定フレームワークの理論一式。破滅（吸収状態）を避ける制約の内側で前進を最大化する。破滅には二種類ある——散る破滅（True Ruin、絶対・単一の終着点）と、腐る破滅（Passive Ruin、回避可能な窓が開いている間に、それを閉じる選択をしてしまうこと）。

## 最新版
**NRMO Integrated System v7.3**（`NRMOIntegrated/NRMO_Integrated_System_v7_3.pdf`）が現在の正式版（publication of record、2026-09-23指定）。v7.2 / v7.2 rev2 は歴史的ベースラインとして同じビルド内にそのまま保存されている。

## 構成
- `NRMOIntegrated/` — 理論文書（LaTeX/PDF）、シミュレーション、開発履歴、憲法・仕様書
- `research/` — 検証・調査資料

実装（React/TypeScript PWA・Pythonエンジン）は別リポジトリ `DecisionCompass` で管理。

## v7.2の変更点
TimeHorizonLayerをNRMO CORE内部に統合。従来はdisplay-only(判定に無関与)だった多horizon評価を、実際の判定(veto)に反映させる改訂を行った。旧v7.1の設計は`NRMOIntegrated/archive/ch27_time_horizon_v7_1.tex`に保存。


## v7.2.1の変更点
Passive Ruin検知(v7.2)を実際にコードとして動かして検証したところ、長期horizon(20年)で検知感度が崩壊する問題を発見。差分方式(diff-in-diff)への変更で緩和した。詳細は`NRMOIntegrated/docs/v72_1_validation_record.md`。

## v7.3の変更点
NRMO v7.3 の運用仕様（Governance Kernel / Decision Support Specification）を新しい Part XVI「Production Contract Integration」として統合した。v7.3 原本（`NRMOIntegrated/source/v7.3/original/`）を Normative Canon および v7.2 / v7.2.1 と突き合わせて整理したもので、空の `A_allowed` なら HOLD、Norn の責務とドリフト分類、10段階の評価手順、標準出力フォーマット（A/B/C の3候補提示を含む）などを明文化している。Part I–XV は v7.2 / v7.2.1 の内容をそのまま引き継ぎ、`NORMATIVE_CANON.md` は変更していない。行ごとの対応は`NRMOIntegrated/docs/V7_3_DIFFERENTIAL_TABLE.md`、正式版指定の記録は`NRMOIntegrated/docs/V7_3_PUBLICATION_OF_RECORD_DECISION.md`。

## 状態
公開。未完成のまま、次に委ねる。

License: MIT。

---

## English

A personally developed decision theory framework. Its core idea: maximize forward progress within the constraint of avoiding ruin (an absorbing failure state). There are two kinds of ruin — True Ruin (a single, absolute terminal state) and Passive Ruin (choosing, while an avoidability window is still open, an action that closes it).

### Current version
**NRMO Integrated System v7.3** (`NRMOIntegrated/NRMO_Integrated_System_v7_3.pdf`) is the current publication of record (designated 2026-09-23). v7.2 / v7.2 rev2 remains fully preserved in the same build as historical baseline material.

### Contents
- `NRMOIntegrated/` — Theory documents (LaTeX/PDF), simulations, development history, constitution and specifications
- `research/` — Validation and research materials

The implementation (React/TypeScript PWA + Python engine) is maintained in a separate repository, `DecisionCompass`.

### v7.2 changes
TimeHorizonLayer is now integrated into NRMO CORE itself. The previously display-only, multi-horizon evaluation now participates directly in the veto decision. The prior v7.1 design is preserved at `NRMOIntegrated/archive/ch27_time_horizon_v7_1.tex`.


### v7.2.1 changes
Running the v7.2 Passive Ruin detector for the first time revealed a long-horizon (20-year) sensitivity collapse. Mitigated via a delta-based (diff-in-diff) redesign. See `NRMOIntegrated/docs/v72_1_validation_record.md`.

### v7.3 changes
The NRMO v7.3 operational specification (Governance Kernel / Decision Support Specification) is integrated as a new Part XVI, "Production Contract Integration". It reconciles the located v7.3 original (`NRMOIntegrated/source/v7.3/original/`) against the Normative Canon and v7.2 / v7.2.1, and makes explicit rules such as HOLD on an empty `A_allowed`, Norn's responsibilities and drift classes, the ordered 10-step evaluation, and the standard output format (including the default A/B/C three-candidate presentation). Parts I–XV carry forward v7.2 / v7.2.1 content, and `NORMATIVE_CANON.md` is unchanged. See `NRMOIntegrated/docs/V7_3_DIFFERENTIAL_TABLE.md` for the row-by-row reconciliation and `NRMOIntegrated/docs/V7_3_PUBLICATION_OF_RECORD_DECISION.md` for the publication-of-record decision.

### Status
Public. Released unfinished, to be carried forward by whoever finds it.

License: MIT.
