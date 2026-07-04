# AUTHORITY BOUNDARIES — NRMO Integrated v7.2

```
Human Sovereign → Vision(人間) → NRMO Core/Governance → Admissible Set A_t
  → StrongEngine Ω Full → Action ∈ A_t
```

不変条件 (meta_governance.py が監査):
1. NRMO Core が admissible set A_t を定義。
2. StrongEngine は A_t 内のみ探索。
3. Engine は veto threshold を読まない。
4. Engine は NRMO 境界を書き換えない。
5. NRMO は Engine の目的/戦略/成功定義に介入しない。
6. Engine は破滅判定をスコアに混ぜず前進量を評価 (ruin_penalty 排除)。
7. 破滅リスクは NRMO.filter() が候補を削って処理。

OS/SOP モジュールの権限 (いずれも NRMO veto を上書き不可):
- DAG: 定義/主張/根拠/範囲/反証可能性の検査
- HST-N: 人間状態分類
- Aallowed: mode/domain 別 許可カテゴリ filter (veto ではない)
- APCSO: 選択肢整形 (一択強制禁止, hold/exit 必須, 最終決裁は人間)
- Secretary Console: 記録/感情フィルタ/デトックス/方向付け
- Shutdown Guard: 安全停止 (危険時は安全導線)
- TTM/PPS: 訓練と現実の分離 (TRAINING で現実実行禁止)
- Hare-no-Hi: 祝祭モード (不可逆/破滅的浪費/境界侵害は禁止)
- Investment SOP: 判断支援のみ (実注文しない)
- Meta Governance: 上記の権限越境を検出

禁止形: `score = forward - ruin_penalty` / `engine.veto_threshold` / `engine.override_veto` /
        TypeZero veto / PassivePattern 強制実行 / APCSO 一択強制。
