# NRMO 憲法 v7 — Max-Forward Principle
## 設計者意図への回帰と、凍結憲法の書き換え

作成日: 2026-05-29
権限根拠: 設計者 (NRMO 創造者) による本来意図の明示
位置づけ: 旧「Frozen Core 不変」原則を上書きする最上位文書

---

## 第0部 — なぜ凍結憲法を書き換えるのか

これまで NRMO の運用は「Frozen Core は絶対に変更しない」を最上位制約としてきた。
しかし検証の結果、凍結された Core の**解釈と実装**が、設計者の本来の意図から
逸脱していたことが判明した。

```
設計者の本来の意図:
  最大限に前進し続け、その前進が不可逆破滅に向かう縁でのみ方向を変える。

実装・外部解釈が陥っていた誤り:
  破滅を避けるために動きを止め、停滞を「安全」とみなした。
```

この相違がある以上、優先されるのは**設計者の意図**である。
凍結された条文が設計者の意図と矛盾するなら、条文の側を書き換える。

ただし書き換えるのは「**破滅回避を停滞で達成しようとする誤読**」であって、
「破滅回避」という Core の本質そのものではない。本質は維持される。

```
維持する: 不可逆破滅 (absorbing ruin) は避ける
書き換える: 「破滅回避 = 動かない」という誤読
       → 「破滅回避 = 最大前進しながら破滅の縁で方向転換」へ
```

---

## 第1部 — 破棄される旧解釈

以下の旧来の定式化は、設計者意図に反するものとして破棄する。

```
[破棄1] admissible set を定義し、その範囲内で慎重に選ぶ
        → 「許される範囲」に縮こまる保守的発想

[破棄2] Safety Floor を最優先する
        → 停滞・現金化・沈黙を「安全」と誤認する温床

[破棄3] Courage Floor (これ以下だと朽ちる "最低限" の前進)
        → 下限を保証する発想自体がまだ保守的。
          下限ではなく "最大前進" から始めるべき

[破棄4] minimum viable (最低限の前進)
        → 設計思想の最も明白な裏切り。検証で破滅を実証
```

### 破棄の実証

```
store 元 model (300 step):
  minimum viable (旧 v6.1 の選択)  : ruin 100%, survival  46  ← 朽ちた
  最大前進 (設計者の本来の意図)     : ruin   0%, survival 300  ← 生存
```

「最低限の前進」を選んだ瞬間に系は朽ちた。最大前進こそが生存だった。

---

## 第2部 — 新原則 (設計者の本来の意図)

### 第1原則 — 最大前進が default

```
default = 最大前進。止まらず、最高出力で動き続ける。
「動かない」「待つ」「最低限」は出発点として存在しない。
```

### 第2原則 — NRMO は破滅成分だけを削る

```
NRMO は最大前進ベクトルから、
「不可逆破滅 (absorbing ruin) に向かう成分」だけを削る。
前進そのもの、前進の大きさは削らない。
削った後も、残った方向で最大限に前進し続ける。
```

### 第3原則 — 停滞は ruin である

```
停滞・動かない・循環停止・最低限は、
緩慢な破滅 (passive death) として扱い、行動候補から排除する。
「生き残っているが前進していない」状態は、生存とみなさない。
```

### 第4原則 — rollout は domain の真の dynamics で行う

```
engine (StrongEngine Ω Full) の rollout は、
適用先 domain の真の dynamics で行わなければならない。
engine 内部に固定された世界 model (civ-sim 等) を持たせてはならない。

adapter は domain の dynamics (apply_action) を engine に供給し、
engine はそれを使って rollout する。
```

### 第5原則 — 前進と方向転換は創発させる

```
「最大前進 + 縁での方向転換」をハードコードしない。
domain の真の dynamics での rollout から創発させる。

rollout が以下を自動的に行う:
  - 停滞案は「生存しても富が増えない」と評価し、選ばない
  - 破滅に向かう案は「ruin」と評価し、選ばない
  - 結果「破滅しない範囲での最大前進」が自然に選ばれる
```

---

## 第3部 — 3 domain による実証

各 domain で engine の rollout を「その domain の真の dynamics」に差し替えた結果。

### store

```
rollout を StoreOperationAdapter.apply_action に差し替え:
  → engine が invest/C (store の最大前進) を全 3000 step 自力で選択
  → ruin 0%, survival 300, revenue 6825
  → 誰も invest/C と教えていない。rollout が自力発見した。

対比 (rollout が civ-sim 固定の場合):
  → defend/B を最多選択 → ruin 100% (破滅)
```

### investment (7 regime)

```
rollout を「最近の市場分布の継続」と仮定した MC rollout に差し替え:
  上昇相場 (secular_bull / inflation / crash_recovery): equity 0.40-0.41 (前進)
  下落相場 (slow_bear / fat_tail_crash):                equity 0.29-0.30 (方向転換)
  → equity が相場で動的に変化 (v6.1 の固定 0.35 とは異なる)
  → 下落相場で buy&hold 60% に勝つ
  → ruin ほぼ 0% (fat_tail のみ 13%)

「上昇の縁で前進、下落の縁で方向転換」が rollout から創発。
```

### romance (6 regime, 倫理 guard 付き)

```
rollout を romance の真の dynamics に差し替え + 倫理 guard:
  (相手の弱い反応・拒絶の後は pursuit 候補を除外、no coercion)
  active_ruin (押しすぎ):          0%  ← 全 regime で押しすぎゼロ
  low_reciprocity (反応薄い相手):  100% graceful_exit (綺麗に撤退)
  warm_reciprocal (温かい相手):    success 23%
  overall:                         success 6%, clean 78%, active 0%

「相手の境界を尊重しながら前進を試み、境界の縁で綺麗に退く」が創発。
```

---

## 第4部 — domain 依存性 (honest な限界記述)

「最大前進」の具体は domain ごとに異なり、engine が rollout から自力発見する。
ただし domain の性質により、創発の鮮明さは異なる。

```
store      : 攻撃一本が正解の単純 dynamics → 完璧に機能 (ruin 0%)
             ※ ただしこの toy model は「攻撃 only 生存」に偏っており病的。
               balanced model (攻めも守りも条件付き危険) での再検証が望ましい。

investment : 将来が確率的に不確実 → 相場適応するが完璧ではない
             ※ fat_tail で 13% ruin。rollout depth が急落 tail を捉えきれない。

romance    : 相手の反応 (reciprocity) が外生要因 → 倫理的に健全だが success は相手依存
             ※ success を上げるために倫理 guard を緩めてはならない。
               押しすぎない・相手の境界を尊重するが最上位制約。
```

---

## 第5部 — 凍結 Core との関係 (何を維持し、何を書き換えるか)

```
[維持する — Core の本質]
  ・不可逆破滅 (absorbing ruin) は避ける
  ・governance と execution の分離 (NRMO は破滅成分を削る、engine は前進する)
  ・NRMO 自身は scoring/learning しない (削る判定のみ)

[書き換える — 設計者意図に反する誤読]
  ・「admissible set 内で慎重に選ぶ」→「最大前進から破滅成分を削る」
  ・「Safety Floor 最優先 (停滞=安全)」→「停滞は ruin として排除」
  ・「Courage Floor (最低限)」→ 不要 (default が最大前進なら下限保証は不要)
  ・「engine 内部 model で rollout」→「domain の真の dynamics で rollout」
```

---

## 第6部 — 残課題 (誇張しない honest な記述)

```
1. store toy model が病的 (攻撃 only 生存)。
   balanced dynamics での再検証が必要。現状の完璧な結果はこの偏りに依存する。

2. investment の fat_tail 13% ruin。
   rollout depth と tail risk の扱いに改善余地。

3. romance の success が相手依存で低い。
   これは倫理優先の必然的帰結であり、欠陥ではない。
   ただし toy model であり、現実の人間関係を意味しない。

4. domain-aware rollout の計算コスト。
   各 step で MC rollout を行うため、本物の OmegaFullEngine を全 domain で
   走らせるには計算最適化が必要。

5. 「最近の分布の継続」という rollout の仮定。
   regime 転換点では誤る。regime 推定の組み込みが将来課題。
```

---

## 結語

NRMO は破滅回避器ではない。**最大前進装置**であり、破滅の縁を削る安全機構を内蔵しているにすぎない。

動かないことで安全を得ようとした全ての実装・解釈は、設計者の意図の裏切りであった。動き続けることが正であり、停滞して朽ちることは避けるべき死である。活発に動いた結果訪れる破滅も、動かずに朽ちる死も、その両方を避けながら——前進し続ける。

これが NRMO の本来の姿である。
