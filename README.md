# NRMO — Non-Ruin Maximizing Objective

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22018104.svg)](https://doi.org/10.5281/zenodo.22018104)

破滅を避け、前へ。停滞も死。

個人開発の意思決定フレームワークの理論一式。破滅（吸収状態）を避ける制約の内側で前進を最大化する。破滅には二種類ある——散る破滅（True Ruin、絶対・単一の終着点）と、腐る破滅（Passive Ruin、回避可能な窓が開いている間に、それを閉じる選択をしてしまうこと）。

## 構成
- `NRMOIntegrated/` — 理論文書（LaTeX/PDF）、シミュレーション、開発履歴、憲法・仕様書
- `research/` — 検証・調査資料

実装（React/TypeScript PWA・Pythonエンジン）は別リポジトリ `DecisionCompass` で管理。

## v7.2の変更点
TimeHorizonLayerをNRMO CORE内部に統合。従来はdisplay-only(判定に無関与)だった多horizon評価を、実際の判定(veto)に反映させる改訂を行った。旧v7.1の設計は`NRMOIntegrated/archive/ch27_time_horizon_v7_1.tex`に保存。

## 状態
公開。未完成のまま、次に委ねる。

License: MIT。

---

## English

A personally developed decision theory framework. Its core idea: maximize forward progress within the constraint of avoiding ruin (an absorbing failure state). There are two kinds of ruin — True Ruin (a single, absolute terminal state) and Passive Ruin (choosing, while an avoidability window is still open, an action that closes it).

### Contents
- `NRMOIntegrated/` — Theory documents (LaTeX/PDF), simulations, development history, constitution and specifications
- `research/` — Validation and research materials

The implementation (React/TypeScript PWA + Python engine) is maintained in a separate repository, `DecisionCompass`.

### v7.2 changes
TimeHorizonLayer is now integrated into NRMO CORE itself. The previously display-only, multi-horizon evaluation now participates directly in the veto decision. The prior v7.1 design is preserved at `NRMOIntegrated/archive/ch27_time_horizon_v7_1.tex`.

### Status
Public. Released unfinished, to be carried forward by whoever finds it.

License: MIT.
