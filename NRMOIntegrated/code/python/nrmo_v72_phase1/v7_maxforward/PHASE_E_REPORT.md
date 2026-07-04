# Phase E 完了報告 — DecisionCompass の二層構造化 (実コード接続)

作成日: 2026-05-30
指針: NRMO_Realignment_Master_Spec.md §5
成果物: `engine/v7_decision_compass.py`
備考: 前セッションの `DecisionCompass_*.py` は環境リセットで消失。実 `nrmo_core` を核に
      二層構造の正本として再構築 (Master Spec §5 の設計に忠実)。

---

## 1. 何をしたか

DecisionCompass を「個人意思決定 domain の完全現実側アプリ」として二層構造に接続。
**実コード3点** を結合した:

```
憲法境界(Loom) = 実 nrmo_core.construct_admissible_set  (governance: veto only)
真の dynamics  = 実 civstate_transition / is_ruin_state  (第4原則)
engine         = v7 二層 (StrongEngineOmegaFull + MaxForwardEngine)
```

CivState (R,E,G,O,K,X) を「個人の状況」として再解釈:
R=資源/蓄え, E=心身/環境, G=生活の安定, O=選択肢, K=技能, X=暴露/リスク。

---

## 2. gov-exec 分離 (不可侵, 実証済)

```
A_t = NRMO(X_t)     governance が admissible set を構築 (YES/NO/HOLD のみ)
a_t = Engine(A_t)   engine は A_t の中だけで探索。veto ロジックを見ず override 不可。
```

`_Restricted` wrapper で engine に admissible set だけを渡すことで分離を構造的に保証。

---

## 3. 検証結果 (再現可能, `python3 v7_decision_compass.py`)

### [A] 単発推奨 (リスクに応じ admissible が縮小)
| 状況 | 結果 |
|---|---|
| 健全 (低暴露・安定) | ALLOW 前進g=0.18 (admissible 3/5, veto 2) |
| やや過熱 (高暴露) | ALLOW 前進g=0.18 (admissible 2/5, veto 3) |
| 縁 (高暴露・低統治) | **EXIT_HOLD** (veto 5/5) → 暴露を下げる方向転換を先に |

### [B] gov-exec 分離
候補 g=[0.95, 0.55, 0.42, 0.30, 0.18] → veto=[T,T,F,F,F] → admissible g=[0.42,0.30,0.18]。
engine 選択 g=0.18 は admissible 内 (override 不可)。✓

### [C] 軌道実行 (200 ステップ, 12 seeds)
ruin **0%** / 最終前進量(生存時) 644 / HOLD 0.0。
governance が破滅成分を削り、engine が admissible 内で前進を継続。

---

## 4. 正直な所見 — 「最大前進」が慎重寄りに出る件

健全状態の admissible 各 action の前進量 (生存100%, sim_horizon=40):
`g=0.42→422, g=0.30→467, g=0.18→481`。低成長ほど僅差で前進量が高い。

理由: 実 `civstate_transition` で高成長は暴露 X を上げ、前進量 = R+E+G+O+K−X を
押し下げる。生存100%の admissible 内では低成長が僅差で最善になる。

**これは警告対象の「過度な防御 (停滞=passive death)」ではない:**
1. 攻撃側を削ったのは engine でなく **governance** (gov-exec 分離が正しく働いた結果)。
2. 選択 g=0.18 は **前進方向** (g>0, sf=0.42, 停滞ではない)。
3. 生存圧ではなく **domain の前進量勾配** が慎重を選ばせている = 世界依存性 (V9-minimum 的)。

**ただし注記:** 慎重へ倒れる度合いは前進量メトリクスの暴露ペナルティ重み (R+E+G+O+K−X) に
依存する。この重みは既存 `engine/v7_civ_dynamics.py` の `CivilizationDynamics.wealth` と
同一規約。重みを変えれば最善 g は動く。過度な調整を避け、実 dynamics の出力をそのまま報告した。

---

## 5. 実行方法
```bash
NRMO_V6_ROOT=/path/to/NRMO_v6_Repaired python3 engine/v7_decision_compass.py
# 依存: 同 engine/ の v7_two_layer.py, v6 の v52_codebase (nrmo_core) と world_sim_v50/src (vnext_plus)
```

---

## 6. 残作業 (更新後)
- Phase F: 全 Python/LaTeX 統合 + 実 population step 完全接続 + NRMO Integrated PDF 再生成。
- (任意) investment/romance の §3 再検証: `NRMO_v6_to_v6_1_..._Bundle_20260529.zip` 再アップ要。
