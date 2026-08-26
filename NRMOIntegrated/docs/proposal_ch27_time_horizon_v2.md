# TimeHorizonLayer 土台修正案 v3
## PassiveRuin/TrueRuinを因果連鎖の上流・下流として統合

---

## 1. 確定した理解(v1→v2→v3の到達点)

- **TrueRuin**: 単一・絶対の終着点。到達すれば回避不能。状態として、
  事後的に確定する(下流)。
- **PassiveRuin**: 回避可能な窓がまだ開いている時点で、
  その窓を自ら閉じてしまう選択。選択の瞬間に診断可能(上流)。

両者は別カテゴリの失敗ではなく、**同一の因果連鎖の異なる観測点**。

```
[窓が開いている状態]
      |
      | ← ここでPassiveRuin診断が可能(選択の直前)
      v
[窓を閉じる選択(気づかれずに、あるいは軽視されて行われる)]
      |
      | ← 時間経過(窓が完全に閉じるまでのラグ)
      v
[TrueRuin(窓が閉じきった、回避不能な終着点)]
      |
      | ← ここでTrueRuin診断が可能(事後・手遅れ)
```

**設計上の帰結**: Coreの本質的な役割は、TrueRuinの検知(手遅れ)ではなく、
**PassiveRuinの検知——選択の実行前に、その選択が窓を閉じる行為か
どうかを判定すること**に重心を移すべき。

---

## 2. Core veto() の再設計: 事後評価から事前介入へ

現行(v1/v2)は「状態を評価する」設計だったが、これは本質的に
事後的(post-hoc)。真に必要なのは、**候補となる行動(action)を
実行する前に、その行動がPassiveRuinを引き起こすかを判定すること**。

```python
def NRMO_CORE.veto(state, candidate_action, horizon_set):
    """
    候補行動を実際に適用する前に、
    窓を閉じる選択かどうかを判定する。
    """
    verdicts = {}

    for horizon in horizon_set:
        window_before = avoidability_window(state, horizon)
        projected_state = apply(state, candidate_action)
        window_after = avoidability_window(projected_state, horizon)

        # 1. TrueRuin絶対判定(結果が直接そこに到達する場合)
        if is_true_ruin(projected_state, horizon):
            verdicts[horizon] = "REJECT_TRUE_RUIN"
            continue

        # 2. PassiveRuin判定(窓が開いていたのに、この選択で不可逆に閉じる)
        if window_before.is_open and window_after.triggers_lock_in():
            verdicts[horizon] = "REJECT_PASSIVE_RUIN"
            continue

        verdicts[horizon] = "ALLOW"

    # 最も厳しい判定を採用(horizon間でMinimax)
    final = most_restrictive(verdicts)
    return {
        "verdict": final,
        "horizon_breakdown": verdicts,
        "binding_horizon": binding(verdicts),
    }
```

### 2.1 これが実行フロー上どこに位置するか

旧v2.1 Integrated Flow(ch27記載)のStep 5-6は:

```
5. TimeHorizonLayer.evaluate() -> warn_flag (display only)
6. NRMOSystemV20.process()  [FROZEN v2.0 pipeline、行動は既に決まっている前提]
```

新設計では、この順序自体を変える必要がある。**行動が確定する前に
Coreが評価しなければ、事前介入は成立しない。**

```
新フロー:
5'. 候補行動の生成(複数の選択肢が並ぶ、まだ未実行)
6'. NRMO_CORE.veto(state, candidate_action, horizons) -> 各候補を評価
7'. REJECT_TRUE_RUIN / REJECT_PASSIVE_RUIN の候補を除外
8'. 残った候補の中から実行(ALLOWまたはMODIFY_REQUIREDの候補)
```

これはCoreの役割を「実行後の監査」から「実行前のフィルタ」に
根本的に変える提案であり、v7.1の"FROZEN"パイプラインへの
かなり大きな変更になる。段階的な検証が必須。

---

## 3. 設計思想上の意味

PassiveRuinが「選択の瞬間に診断可能」だと分かったことで、
NRMOの重心が変わる。

**旧来の重心**: 詰んだ状態(TrueRuin)を避けること。
**新しい重心**: 詰みに向かう"選択"そのものを、実行前に見抜くこと。

これは、今日ずっと議論してきた「恐怖側/前進側の非対称性」の
話にも接続する。もしPassiveRuin検知が事前介入として機能するなら、
StrongEngine(前進側)が暴走を恐れて出力を抑える理由も、
より正確に絞り込める可能性がある——「前進すること自体」を
恐れるのではなく、「窓を閉じる前進」だけを止めればよい、
という区別が、原理的にはできるようになる。

---

## 4. 残された未解決点(v2から持ち越し+新規)

1. **窓(avoidability_window)の測定方法** — 依然未定義。ここが
   実装上の最大のボトルネック。
2. **候補行動の生成方法** — 新フローは「複数の候補行動が並ぶ」
   ことを前提にしているが、現行の意思決定プロセスがそもそも
   複数候補を明示的に生成しているかどうかは要確認。
3. **"lock_in"の判定基準** — 「不可逆に窓を閉じる」と「一時的に
   窓を狭めるが、まだ回復可能」の境界線をどう引くか。
4. **v7.1 FROZENパイプラインとの互換性** — 事前介入型への転換は
   相当大きな設計変更。v8.x系の過去の失敗(Stagnation worldでの
   劣化)を踏まえ、段階的検証(まずシミュレーション上でのみ試す等)
   が必須。
