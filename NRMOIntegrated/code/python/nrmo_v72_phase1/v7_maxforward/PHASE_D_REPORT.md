# Phase D 完了報告 — collective_engine の二層構造接続 (実コード接続)

作成日: 2026-05-30
指針: NRMO_Realignment_Master_Spec.md §8
成果物: `engine/v7_collective_two_layer.py`

---

## 1. 何をしたか

Master Spec §8 に従い、`collective_engine_v71.py` の実クラス `CollectiveStrongEngine`
を二層構造の **現実側** として接続した。

```
[現実側]  CollectiveStrongEngineRealSide
            ・実 CollectiveStrongEngine を実体として保持
            ・forecast_next_shock (実関数) で破滅の縁を検出
            ・平時 = 最大前進 (civ-sim 最善構成) / 縁 = triage 方向転換 (止めず守って前進)

[civ-sim側] CollectiveMaxForwardEngine
            ・攻撃(全体成長) 〜 防御(triage退避) の連続 spectrum を
              ★真の集団 dynamics★ で ★長期地平★ に試行 (死は許容)
            ・攻撃ピーク / 防御ピーク / 最善構成を算出

[双方向]   observe() / feedback()
```

action_spectrum はスカラ a∈[0,1] (0=攻撃 / 1=防御) を実 `CollectiveConfiguration`
にマップ (`config_from_aggression`)。pool rate・coverage・budget_augment・triage 重み・
rescue_rate_cap が a に応じて連続変化する。

---

## 2. 第4原則の徹底 (最重要)

実 `CollectiveStrongEngine` の内部スコアリングは `_rollout_collective`
(collective_engine_v71.py L667) を使う。コメント自身が
"lightweight model ... without invoking the full agent population step" と認める通り、
これは引き継ぎ書 §7 が禁じる **「engine 内部に civ-sim 固定 dynamics を持たせる」反パターン**。

Phase D ではスコアリングを **civ-sim 側の真の集団 dynamics・長期地平の rollout** に
置換した。実 engine は接続・実行を確認した上で (実コード接続)、評価軸を二層構造側に移している。

---

## 3. 検証結果 (再現可能, `python3 v7_collective_two_layer.py`)

### [A] 実コード接続
`CollectiveStrongEngine.select_configuration` を実引数で呼び出し、
`n_admissible=25`, forecast≈0.32 で正常動作を確認。実コードは生きている。

### [B] 世界依存性 (civ-sim 探索, 長期地平 sim_horizon=60)
| 世界 | 最善 aggression | 備考 |
|---|---|---|
| 穏やかな世界 | **0.00 (攻撃)** | surv 100%, wealth 876。攻撃が純粋に最善 |
| fat-tail 世界 | **0.25 (保険込み)** | 純攻撃 a=0 は surv 83% に落ち破滅 → 保険込みが最善 |

→ §1 の世界依存性 (V9-minimum: 危険な世界では慎重が最善) を spectrum 探索で再現。

### [C] 評価地平 — ★正直な所見 (§8 と逆向き)★
標準世界の civ-sim 最善 aggression: h8→0.00, h20→0.00, h60→0.25, h120→0.25。

- **この集団保険 domain**: 短期→攻撃 / 長期→やや防御(保険)。
  理由: 保険が薄い攻撃側の破滅リスクは**地平とともに累積**するため、長期評価ほど保険が報われる。
- **単一文明 domain (§8/文明)**: 短期→防御 / 長期→成長。
  理由: **成長複利**が長い地平で顕在化する。

両者は **逆向き** だが、どちらも「長期評価が真のコスト構造を顕在化させる」点は共通。
顕在化するコスト (複利成長 vs 累積 tail) が domain で異なるだけ。
**ラベルを §8 に合わせる過度な調整はしていない** (引き継ぎ書 §7「過度な調整」回避)。
→ 評価地平は必須。最善の向きは世界依存 + domain 構造依存 (第1原則)。

### [D] 現実側二層の動作 (horizon 80 世代, 40 seeds)
| 世界 | ruin | 最終wealth(生存時) | 縁での triage 方向転換率 |
|---|---|---|---|
| 標準世界 | **5%** | 607 | 50% |
| fat-tail 世界 | **2%** | 242 | 63% |

- max_forward が主体、縁でのみ triage 方向転換 (世界依存: 危険なほど方向転換が増える)。
- fat-tail の ruin が標準より低いのは、危険な世界ほど方向転換が増え保険込みが選ばれ、
  よくヘッジされるため (世界依存挙動として整合)。

---

## 4. 残る課題 (正直な報告)

- **残留 tail ruin (標準 5% / fat-tail 2%)**: 前ステップまで状態が健全な単発巨大 tail に
  よる一撃破滅で、反応的な縁方向転換では捕捉できない。事前の構造的保険でしか防げない。
  投資 domain の fat_tail ruin 27-38% (§3 既知課題) と同種だが、集団ははるかに低い。
- **`CollectiveDomainDynamics` は合成モデル**: 実 agent population step (world_sim_v50 の
  本体 step) には未接続。第4原則を満たす真の dynamics の **代理** であり、実 population step
  への完全接続は Phase F (全体統合) の対象。

---

## 5. 実行方法

```bash
# v6 実コード (collective_engine_v71.py) のある src を環境変数で指定
NRMO_V6_SRC=/path/to/NRMO_v6_Repaired/world_sim_v50/src \
  python3 engine/v7_collective_two_layer.py
# 既定値: (同梱) world_sim_v50/src
```

---

## 6. 残作業 (更新後)

- Phase E: DecisionCompass の二層構造化 (Master Spec §5)
- Phase F: 全 Python/LaTeX 統合 + `CollectiveDomainDynamics` を実 population step へ接続 +
  NRMO Integrated PDF 再生成
