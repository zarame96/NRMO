# ALB Theory — Chapter 1: Foundations (v0.2)

> 収録注記（2026-10-21）：原本は 2026-09-16 の作業環境の出力ファイルで、リポジトリ未収録だった。
> 当該対話ログに残る作成時の全文から復元して収録した。本文は原本どおり。
> 次稿への持ち越し4件への提案は `ALB_THEORY_CH02_FILL_v0.1.md` を参照。

Draft v0.2。v0.1 を精読し、3件の問題を修正した。

**v0.1 → v0.2 変更点**

1. **誤り(修正済み)**：§1.3(旧)の禁止事項表で「ALB: 推進の目的・戦略・
   成功の定義を行うこと」としていたが、これは意味が通らない。ALB は
   推進(攻)側ではなく防御(守)側の統治者であり、禁止されるべきは
   「防御の目的・戦略・成功の定義」だった。単純な写し間違い
2. **欠落(補完済み)**：形式定義に、NRMO 側にある
   `Engine ̸⊆ NRMO` に相当する条件、`DefensiveEngine ̸⊆ ALB` が
   抜けていた。3条件中2条件しか写していなかった
3. **欠落(補完済み、影響大)**：NRMO §22 は Rejected Designs として
   3つの Failure(1: Engine を NRMO の中に置く、2: NRMO が Engine の
   目的に介入する、3: 安全を理由に推進力を抑圧する)を定義しているが、
   v0.1 は Failure 3 のみ鏡写しにし、Failure 1・2 の鏡像を欠いていた。
   さらに Consensus 1(NRMO 単独の限界の形式証明)の鏡像も欠いていた。
   本稿で追加する

---

## 1.1 Consensus 1：ALB 単独の限界（形式証明）

NRMO §22.2.1 の証明を、防御側の言葉で鏡写しにする。

```
Premise 1: ALB constraint = P(Passive Ruin | ¬a) ≥ θ_A → INTERVENE
Premise 2: 境界の持続的な維持 ⊆ { a | P(Passive Ruin | ¬a) < θ_A で
           行われる予防的行動 }
Therefore: ALB 単独では、境界の持続的な維持を構造的に行えない

∀w ∈ Worlds : ALB_only(w) ⇒ ¬CanMaintainBoundary(w)          (1.1)
```

ALB は閾値 θ_A を超えたときにのみ介入する force-only の憲法である。
しかし本物の防御の多くは、閾値に達する**前**の、地味で継続的な
予防行動でできている。ALB はこの種の行動を構造的に生成できない
(force は「介入」であって「継続」ではない)。ゆえに ALB 単独では
足りず、DefensiveEngine が要る。NRMO 単独では非連続な跳躍を
起こせないのと対称に、ALB 単独では持続的な防御を維持できない。

## 1.2 Consensus 2：DefensiveEngine は不可欠である

NRMO §22.2.2 と対称の経験則。

観測（理論上の想定）：
- 防御力を持たない推進のみの系 → 初期は生存するが、一度の
  不可逆な損失で全体が消える
- 弱い防御(場当たり的な用心)のみ → 生存はするが、慢性的に
  すり減り続ける

結論：DefensiveEngine が不要だとする理論は、Issue #87 が示した
現実(安全側への偏り)そのものを説明できない。

## 1.3 Rejected Designs（3つの失敗パターン）

NRMO §22.3 の3つの Failure を、それぞれ鏡写しにする。

### 1.3.1 Failure 1: DefensiveEngine を ALB の中に置く

DefensiveEngine を ALB の制約下に完全に組み込むと、すべての防御
行動が `P(Passive Ruin | ¬a) ≥ θ_A` を満たすときにのみ許可される
ことになる。

```
DefensiveEngine ⊆ ALB ⇒ 全ての防御行動が P(Passive Ruin) ≥ θ_A に従属
```

しかし本物の防御は、しばしば `P(Passive Ruin) < θ_A` の段階、
つまりまだ危険域に入る前の予防行動を必要とする。矛盾。よって失敗。

これは Failure 1(Engine を NRMO の中に置く)の鏡像であり、対称に
「非連続な跳躍ができなくなる」ことが「予防的な継続行動ができなく
なる」ことに置き換わっている。

### 1.3.2 Failure 2: ALB が DefensiveEngine の目的・戦略に介入する

ALB が防御の「やり方」まで指図し始めると、憲法が支配者になる。
これは §1.6(Operation Flow)の

```
DefensiveEngine.purpose   <-- ALB has no access
DefensiveEngine.strategy  <-- ALB has no access
DefensiveEngine.success   <-- ALB has no access
```

という不可侵条件を破ることに等しい。ALB が「何を守るべきか」
「どう守るべきか」まで定義し始めた瞬間、ALB はもはや force-only
の憲法ではなく、防御そのものを乗っ取った実行者になる。

### 1.3.3 Failure 3: 「攻めろ」を理由に防御を抑圧する

Failure 3(NRMO 側、安全を理由に推進を抑圧する)の正確な鏡像。

攻めそのものが目的化し、防御が「弱腰」「機会損失の元凶」として
扱われ、抑圧される。帰結は NRMO 側と同型で四つ現れる。

- 教条化(ALB の絶対化。「常に攻めるべき」という信仰)
- 消耗(防御の欠如による慢性的な損耗、修復不能点への接近)
- 自己免罪(「攻めているから仕方ない」を損失の言い訳にする)
- 決定主体の消失(攻めることそのものが自己目的化し、
  なぜ攻めているかを誰も説明できなくなる)

NRMO 単独が「凶器」なら、ALB 単独は「無防備な暴走」である。

## 1.4 正しい構造

| 層 | 役割 | 権限 |
|---|---|---|
| ALB（憲法） | 停滞の強制介入 | force のみ（PASS / INTERVENE_MINOR / INTERVENE_MAJOR） |
| DefensiveEngine（推進の中の守） | 最低限の担保、単独暴走の抑制 | 観測、待機、最小限の自己防御 |
| 禁止 | DefensiveEngine: ALB を無視すること／ALB: **防御**の目的・戦略・成功の定義を行うこと | — |

## 1.5 DefensiveEngine の定義

NRMO §22.4.1 の Engine 定義（high-speed, single-purpose orientation,
non-continuous jumps, failure-premise, world-bending）と対称に、
DefensiveEngine は以下の性質を持つ。

- **低速で慎重**：Engine が high-speed であるのに対し、DefensiveEngine
  は判断速度より確実性を優先する
- **複数目的の保持**：Engine が single-purpose であるのに対し、
  DefensiveEngine は同時に複数の防御目的（資本保全、信用保全、
  関係保全など）を保持し続ける
- **連続的な減衰**：Engine が非連続な跳躍であるのに対し、
  DefensiveEngine は閾値を跳ばず、連続的にリスクを減衰させる
  （急停止ではなく、漸進的な後退）
- **単一失敗致命の前提**：Engine が failure-premise（多くの失敗を
  織り込み、試行の大半が失敗しても構わない）であるのに対し、
  DefensiveEngine は個々の判断が一度でも失敗することを許容しない
  前提で動く（失敗前提の推進を、失敗しない防御で下支えする）
- **境界維持**：Engine が world-bending（環境を変える力）を持つのに
  対し、DefensiveEngine は境界を変えず、既存の許容集合を維持する力
  を持つ

## 1.6 形式的定義

```
System = (ALB, DefensiveEngine, Separation)

Separation :=
  DefensiveEngine ̸⊆ ALB,
  ALB.authority = force_only,
  DefensiveEngine → ALB : cannot ignore

signal ∈ { PASS, INTERVENE_MINOR, INTERVENE_MAJOR }

P(Passive Ruin | ¬a) ≥ θ_A → INTERVENE

health(ALB) ∝ 1 / force_frequency
```

## 1.7 Operation Flow

```
DefensiveEngine: OBSERVE -> WAIT -> PERSIST/DECAY -> ITERATE
        | (停滞状態のたび)
        v
ALB: P(Passive Ruin | ¬a) >= θ_A ?
        |-- NO : PASS（DefensiveEngineは待機継続）
        |-- YES: INTERVENE_MINOR または INTERVENE_MAJOR

DefensiveEngine.purpose   <-- ALB has no access
DefensiveEngine.strategy  <-- ALB has no access
DefensiveEngine.success   <-- ALB has no access
```

ALB は「なぜ待機しているか」という理由にはアクセスしない。
観測できるのは「待機している」という状態のみ。これは NRMO が
Engine の purpose/strategy にアクセスしないのと対称。

## 1.8 Cross-Domain 理論実験

NRMO §22.7 の表を鏡写しにする。この表自体が「理論実験」に相当する
——抽象構造を4つの具体領域に当てはめ、破綻しないかを検証する。

| 領域 | ALB の役割 | DefensiveEngine の役割 |
|---|---|---|
| 事業 | 機会損失の検知・強制着手トリガー | 最低限の資本保全ライン(赤字上限)の維持 |
| 投資 | ポジション不足・機会逸失の検知、強制建玉 | 集中リスクの分散、追証耐性の維持 |
| 人間関係 | 関係の停滞・沈黙の長期化を検知、接触の強制 | 相手の自由度・可逆性の維持(強制はしても支配しない) |
| キャリア | 挑戦不足・停滞キャリアの検知、応募・提案の強制 | 信用・評判の最低ラインの維持 |

**理論実験としての検証結果（初見での整合性チェック）**

- 「人間関係」領域で緊張が出る。ALB が「接触を強制」すると読めるが、
  §4.3・§11 の「相手の自由な判断を狭める助言をしない」という
  NRMO 側の禁止事項と、文言上ぶつかる可能性がある
- ここでの「強制」の主体は常に**あなた自身**（DefensiveEngine を
  動かすのはあなた）であり、相手を強制するのではない、という
  区別が必要。ALB が強制するのは「あなたが動くこと」であって、
  「相手が応じること」ではない。この区別はまだ本文(§1.5・§1.7)に
  明文化されていない（未確定、次稿で解消する）

## 1.9 Health Metrics

- Healthy: force frequency が低下（DefensiveEngine が学習し、
  自発的に動けるようになっている）
- Warning: force frequency が上昇（DefensiveEngine の慢性的停滞、
  または ALB の閾値過敏）
- Pathological: force frequency が極めて高い（ALB が慢性的に
  強制し続けている状態。これは「ALB が宗教化している」状態に
  相当し、NRMO の「veto の宗教化」と対称の病理）

## 1.10 Implementation Checklist

- [ ] ALB は force-only の憲法か
- [ ] DefensiveEngine は ALB の外にあるか（⊄ ALB）
- [ ] ALB は「何を守るべきか」を定義していないか
- [ ] ALB は「どう守るか」を定義していないか
- [ ] ALB は force 権限のみを行使しているか
- [ ] force の頻度は時間とともに低下しているか
- [ ] DefensiveEngine は θ_A 到達前の予防的行動を取れているか（Failure 1 の回避）

## 1.11 Final Declaration

> ALB without a DefensiveEngine breaks and eventually fails.
> A DefensiveEngine without ALB stays exposed and eventually fails.
>
> The caged beast model has a mirror: the caged watchdog model.
> Both survive only together.

---

## 次稿への持ち越し（現時点で残っている穴）

1. §1.8 で見つかった「強制の対象は自分か、相手か」の区別が
   まだ文書化されていない
2. θ_A（Passive Ruin 確率の閾値）の具体的な算出方法が未定義
   （NRMO の ε に対応する数式的定義がまだない）
3. DefensiveEngine の「連続的な減衰」が、実際にどういう数式・
   アルゴリズムになるか、Engine 側の探索アルゴリズムに相当する
   具体化がまだない
4. NRMO 側の Part VII 以降(数学的証明群、実証データ)に相当する、
   ALB 側の実証・証明パートがまだ影も形もない
