# NRMO / ALB 統合アーキテクチャ設計メモ v0.1

作成日: 2026-09-16
状態: 核（Core）の合意のみ。仕様書ではない。NRMO本体（v7.3、511ページ相当）の
成熟度には遠く及ばない、最初の一章分。

> 収録注記（2026-10-21）：原本は当時の作業環境の出力ファイルで、リポジトリ未収録だった。
> 当該対話ログに残る作成時の全文から復元して収録した。本文は原本どおり。
> 未確定事項への提案は `ALB_THEORY_CH02_FILL_v0.1.md` を参照。

---

## 0. この文書がある理由

Issue #87（「現行 DecisionCompass は安全側・HOLD 寄りに偏りすぎる」）の
実質は、NRMO が本来持つべき対の片方（攻勢側）が存在しないことによる
構造的な欠落である。PDF §22.3.3 Failure 3 が警告する病理——
「安全を理由に推進力を抑圧し、停滞・自己免罪・決定主体の消失に至る」
——の実例として現れている。

NRMO 単独運用は「凶器」になり得る。対になる攻勢の憲法を作る。

---

## 1. 全体階層（合意済み）

```
Human Sovereign（最終決定権。委任しない）
    ↓
???（仮称未定。NRMOとALBの声を受け、決定はしない）
    ↓
NRMO（守勢）                    ALB(=NPMO)（攻勢）
authority = veto_only           authority = force_only
    ↓                                ↓
Engine                          DefensiveEngine
（NRMOの枠内、守の中の攻）        （ALBの枠内、攻の中の守）
```

上下関係ではなく、NRMO と ALB は対等。ALB は NRMO の外殻組織
（StrongEngine を格上げしたもの）ではなく、独立して新設する。

---

## 2. NRMO（既存、確認のための要約）

詳細は `NRMO SYSTEM_7.3.md` を正典とする。ここでは対称設計の基準点
としてのみ記す。

```
System = (NRMO, Engine, Separation)
Separation := NRMO.authority = veto_only
              Engine → NRMO : cannot ignore

signal ∈ {
  PASS,
  INTERVENE_MINOR  (= HOLD),
  INTERVENE_MAJOR  (= SAFE_EXIT)
}

P(Ruin | a) ≥ θ_N → INTERVENE

health(NRMO) ∝ 1 / veto_frequency
```

Engine（StrongEngine）は NRMO の枠内で動く攻勢的な性質
（high-speed, non-continuous jumps, world-bending）を持つが、
NRMO の veto から逃れることはできない。「守の中の攻」。
主役にはなり得ない（§22.4.1 の枠を出ない）。

---

## 3. ALB（Attack of Last Boss、=NPMO）— Core

NRMO と完全に対称な構造として設計する。どちらが強い・上位という
関係を持たせない。

```
System = (ALB, DefensiveEngine, Separation)
Separation := ALB.authority = force_only
              DefensiveEngine → ALB : cannot ignore

signal ∈ {
  PASS,
  INTERVENE_MINOR  (= 仮称未定)
  INTERVENE_MAJOR  (= 仮称未定)
}

P(Passive Ruin | ¬a) ≥ θ_A → INTERVENE

health(ALB) ∝ 1 / force_frequency
```

DefensiveEngine は ALB の枠内で動く防御的な性質を持つ最低限の
担保機構。ALB の枠を出て単独で動くことはできない。「攻の中の守」。
主役にはなり得ない。

**NRMO と ALB の非対称になりかけた点、および決定した修正**

- 当初「push信号は情報提示のみ」としたが、あなたの指定により却下。
  veto と同じ出力レベル（強制力を持つ介入）とする
- 当初「ADVANCE / SEIZE」という新語を作ったが、これ自体が NRMO を
  正典・ALB を仮のものとして扱う非対称の入口だったため撤回。
  NRMO 側の既存語彙（HOLD, SAFE_EXIT）と同じ抽象度の
  `INTERVENE_MINOR / INTERVENE_MAJOR` という共通スキーマに統一
- HOLD・SAFE_EXIT に相当する ALB 側の具体語は、意図的に未定のまま
  残す。「用語は後からついてくる」（本人の言）

---

## 4. 中間層（仮称未定）

NRMO と ALB、両方の上位、Human Sovereign の下位に位置する。

**確定した1つの制約（絶対条件）**

この層は決定しない。決定するのは常に人間。

**確定した出力方針**

NRMO の生信号と ALB の生信号、両方をそのまま人間に提示する。
加えて、両者から合成した推奨も出す（理想形として合意済み）。

**まだ解けていない懸念（本人未確認）**

生信号と推奨を両方出すとしても、推奨の合成過程がブラックボックス
だと、人間は事実上その推奨に従うことになり、この層が実質的な
第四の意思決定者になる。これは NRMO §4.10 の Norn に課した
「監査は秤を持たない」と同じ問題である。

**提案（未確定、本人の承認待ち）**

この層の合成ロジックは、Norn から見て追跡可能な形にする。
NRMO の veto がなぜ発火したか、ALB の force がなぜ発火したか、
そしてこの層がなぜその推奨に至ったかを、事後に Norn が検証できる
構造にする。

---

## 5. 未確定事項（次にやること）

1. 中間層の名前
2. ALB 側の INTERVENE_MINOR / INTERVENE_MAJOR に相当する具体語
3. 中間層の合成ロジックの具体設計（§4の提案の承認、または別案）
4. DefensiveEngine の具体的な定義（Engine が
   high-speed/non-continuous jumps/world-bending と定義されて
   いるのに対応する、DefensiveEngine 側の性質定義）
5. θ_A（Passive Ruin 確率の閾値）の具体的な決め方
6. Norn の観測対象拡張（NRMO の veto 頻度だけでなく、ALB の
   force 頻度、および中間層の推奨と人間の実際の決定の一致率を
   観測範囲に含めるか）

---

## 6. この会話での訂正の記録

設計途中で生じた誤りと訂正。今後同じ迂回をしないための記録。

- 「NPMO は NRMO の統治外にあるべき」という発言を、一時
  「NPMO が生成した行動は NRMO の veto を経由しない」という
  意味に誤読した。正しくは「目的・戦略の立て方が独立している」
  だけであり、§22.5「Engine → NRMO: cannot ignore」に相当する
  不変条件は ALB 側にも同様に適用される
  （`DefensiveEngine → ALB: cannot ignore` はこの文脈での対称形。
  ALB 自体が生成する force 行動を、更に上位の NRMO の veto が
  無視できるかどうかは、本メモでは未確定のまま残っている）
- 中間層を「自動仲裁システム」と誤認し、本人の意図
  （「仲裁ではなく人間が決める」）と衝突していると指摘したが、
  中間層が「決定せず整理・提示のみ行う」なら矛盾しないことが
  後に判明。決定するかしないかが分岐点
- StrongEngine を NPMO(ALB) に統合する案を提示したが、
  「StrongEngine は最後まで NRMO の枠内の補助組織にしかなり
  得ない」との理由で却下。ALB は独立した新設組織とする
