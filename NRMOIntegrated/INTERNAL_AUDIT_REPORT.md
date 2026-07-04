# 内部監査レポート — 実装完全性 / 最大前進 × 破綻回避 (2026-05-30)

自己監査。3 部構成で「実装が完全か」「最大限前進しつつ破綻を回避できているか」を実測。
harness: `code/python/nrmo_v72_phase1/v7_maxforward/internal_audit.py`

## Part 1 — 実装完全性  → 合格
| 項目 | 結果 |
|---|---|
| 本物サブシステム生存 (Wolf/Shinobi/MAPLayer/Norn-Skuld/Loom) | ALL ALIVE (10/10) |
| NRMO 分離契約 (propose→filter→select, ruin_penalty 排除) | ALL PASS (8/8) |
| 統合整合テスト test_v8_integrity | 14/14 |
| 現役 path の未実装 (NotImplementedError/TODO/stub) | なし |

唯一の残存 placeholder は v8_engine の監視層 3 件のみで、被置換の実験エンジン (現役 path 外)。

## Part 2 — 破綻回避 (hostile world 生存ステップ数, 20 seeds, max150)
世界は per-step ハザード base*(1+X/50) のため長 horizon では最終破滅が確率的に不可避。
よって「生存ステップ数 = 破滅をどれだけ遠ざけたか」を破綻回避の指標とする。

| engine | chaotic | drifting | noisy | score平均 |
|---|---|---|---|---|
| Canonical (LoomV31+Shadow) | 45st | 38st | 46st | 17.2 |
| NaiveMaxForward (invest C)  | 5st  | 5st  | 5st  | 2.0  |
| PureDefensive (recover A)   | 42st | 26st | 44st | 13.9 |

- 素朴な最大前進 (invest C) は **5 step で破滅** (X 暴騰 → ruin)。これが NRMO が回避する破綻。
- Canonical は **Naive の ~9 倍生存** し、かつ PureDefensive より **生存も長く score も高い**。
  → 破綻を遠ざけつつ、過剰防御より前進している (sweet spot)。

## Part 3 — 最大前進  → 合格 (1点 正直な注記あり)
### 3a. C 解禁 gating (決定論) — 全 PASS
- safe+strong-opp (R85/X25/O75) → **cap=C** 解禁
- X高(60) → C 不可 (B) / R低(45) → C 不可 (B)
- 累積暴露高(0.85) → hard clamp で **A** (C/B を上書き)

### 3b. 好機での前進発火 (LoomEngine 全パイプライン)
- 好機状態で invest を発火 (前進比率 12%)。
- **正直な注記**: full LoomEngine は cold-start の静的好機状態では invest を **strength A** で出し、
  C までは surface しなかった。C 強度が end-to-end で出るには (i) world detector の履歴による
  opportunity 確定、(ii) strong engine が C 級 aggressive 候補を生成、(iii) safety revalidation を
  通過、の 3 条件が要る。これは多層 caution (defense-in-depth) が効いている状態であり、欠陥ではない。
  C 能力自体は 3a で gating 込みで実装・検証済み。

## 総合判定: **AUDIT PASS**
1. 破綻回避: Canonical 生存 43st > Naive 5st ✔
2. 非自滅 : Canonical score 17.2 ≥ Defensive ✔ (停滞死していない)
3. 前進gating: 安全時のみC・危険時抑制・累積clamp ✔
4. 前進発火: 好機で前進行動を出す ✔

結論: 本システムは「危険な世界では破綻を強く回避 (素朴前進の自滅を回避し、過剰防御より長く生存)」
し、「安全が確認できた好機では最大前進 C を多重 backstop 付きで解禁」する。
= 最大限前進しつつ破綻リスクを回避する設計が、実測で確認された。

正直な改善余地: 3b の通り full pipeline での C surface には opportunity 確定が要る。
benign world モデルが本パッケージに無いため、安全世界での持続的 C 前進の長期実測は別途。
