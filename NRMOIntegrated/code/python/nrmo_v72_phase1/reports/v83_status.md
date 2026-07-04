# NRMO v8.3 進捗状況

## 完了 (全 7 部品)
- core/veto_classification.py     (NRMO Core 出力分類)
- core/cumulative_risk_tracker.py  (累積リスク追跡, window=20)
- core/passive_pattern_proxy.py    (受動的破壊検出 + 補正提案、上書きなし)
- core/typezero_proxy.py           (入力/出力整形)
- core/strong_engine_omega.py      (mutation/synthesis/invention + Wolf/Edge + λ_drift=1.0)
- core/shinobi_engine.py           (P-Core×4 + E-Core×8, Norn/Skuld, Thompson Sampling defensive/race)
- core/map_layer.py                (3D V-Cache: L1直近5step / L2中期30step / L3長期episodic)

## 統合
- core/v83_engine.py               (20 レイヤー pipeline)

## V8.3 Decision Pipeline (20 layers)
[0]   TypeZero Pre-check
[0.5] PassivePattern Pre-Check
[1]   Frame Definition
[2]   Falsifiability Monitor
[3]   Belief Update (POMDP)
[4]   Distribution Shift Monitor
[4.5] MAPLayer query
[5]   Candidate Generation (StrongEngine Ω Full)
[6]   CMDP Hard Constraint (veto_type 明示)
[6.5] Shinobi 12 units consensus
[7]   Multi-Framework Evaluation
[8]   Knightian Uncertainty (state-adaptive)
[9]   Calibration Gates
[9.5] PassivePattern Recheck (受動的破壊検出)
[9.7] NRMO Revalidation (PassivePattern 提案を再評価)
[10]  Anti-Goodhart
[11]  Reflexivity
[12]  Skin in the Game
[13]  Tower Transparency
[14]  Action Selection
[14.5] MAPLayer Update
[15]  TypeZero Output Adapter

## 残り
- 検証: ChaoticWorld + paired Phase 4 で v7.1 vs v8.3
- 書面化: LaTeX/PDF v8.3 report

## 動作確認結果
✅ 全 20 レイヤー pipeline 稼働
✅ Normal world で ACCEPT 出力
✅ Multi-framework が実機能 (P0-1 修正済み)
✅ PassivePattern が score 計算 (発火なしは正常: opportunity 適切な action 選択)
