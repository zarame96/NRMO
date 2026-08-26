# v7.2 実装統合マップ
## 既存資産(omega_full / strong_engine / MaxForwardEngine / core.ruin)の再利用計画

---

## 1. 発見事項サマリ

土台理論(v7.2, avoidability window)を実装に落とす際、
ゼロから書く必要はなかった。以下が既に存在する。

| 理論上の要素 | 既存の実装 | 場所 |
|---|---|---|
| Viability Kernel所属の近似(モンテカルロ) | `survived_ratio = n_ok / repeats`(rollout生存率) | `engine/omega_full.py::score_candidate()` |
| 長期の窓の狭まり検知 | `estimate_long_run_drift()` / `lambda_drift` | `engine/omega_full.py` |
| Passive Ruin(旧定義: streak方式) | `update_passive_ruin()` | `core/ruin.py` |
| True Ruin(絶対境界) | `check_true_ruin()` / `is_ruin_state()` | `core/ruin.py` |
| civ-sim側での試行 → real-side還元の二層構造 | Strong Engine Ω Full(real) / MaxForwardEngine(civ-sim) | `ch20_strong_engine.tex` |
| 状態遷移モデル(world dynamics) | `transition()` | `core/state.py` |

---

## 2. 核心的な不整合: Passive Ruinの二重定義

`core/ruin.py::update_passive_ruin()` は、今日確定した定義
(「窓が開いている間に、それを閉じる選択をしてしまうこと」)
とは異なる、旧い定義で実装されている。

```python
# 既存実装(streak方式) — 状態が悪い領域に留まった回数を数える
if s.O < th.passive_O_threshold: s.low_O_streak += 1
if s.low_O_streak >= th.passive_O_streak: return STAGNATION_TRAP
```

これは「動いていないことそのもの」を見る、v7.2以前の(そして
今日最初に僕が誤って提示した)定義に近い。

### 2.1 統合方針: 廃止ではなく、二段構えにする

streak方式を削除するのではなく、**遅行指標(lagging indicator)**
として位置づけ直し、新しい**先行指標(leading indicator)**である
avoidability window方式を、判定の主軸に追加する。

```python
def detect_passive_ruin_v72(state_before, candidate_action, state_after,
                             streak_state, th, horizon_set):
    """
    v7.2: 二段構えのPassive Ruin検知。
    """
    # 先行指標(NEW): 選択の瞬間に、窓を閉じる行為かどうか
    for h in horizon_set:
        if window_open(state_before, h) and closes_window(state_after, h):
            return "PASSIVE_RUIN_WINDOW_CLOSURE", h

    # 遅行指標(既存、保持): 悪い状態が続いていないかの後追い確認
    legacy_signal = update_passive_ruin(state_after, th)  # 既存コードそのまま流用
    if legacy_signal:
        return f"PASSIVE_RUIN_LEGACY_{legacy_signal}", None

    return None, None
```

先行指標が「選択の瞬間」に検知できなかった見落としを、
遅行指標(streak)が後から拾う、という二重の安全網になる。
既存コードを捨てずに、新しい理論の傘の下に位置づけ直す。

---

## 3. window_open() / closes_window() の実装 — 既存rollout機構の転用

`omega_full.py::score_candidate()`内の`survived_ratio`計算ロジックを、
**Core用の共有ユーティリティとして切り出す**。

```python
# 新規: core/viability.py (Coreから呼べる共有モジュール)
# 統治-実行分離を守るため、omega_full.py固有のスコアリング
# (report/drift_pen等)は持ち込まず、rollout生存判定のみを抽出する。

def viability_score(state, wp, rng, cfg, horizon,
                    n_rollouts=30, rollout_action_fn=None):
    """
    omega_full.score_candidate()のロールアウト部分を
    ガバナンス用途向けに抽出したもの。
    rollout_action_fn未指定時はriskadjusted_reference()を使う
    (既存のデフォルト方針を踏襲)。
    """
    survived = 0
    for _ in range(n_rollouts):
        s = state.copy()
        for _ in range(horizon):
            action = rollout_action_fn(s) if rollout_action_fn else riskadjusted_reference(s)
            s = transition(s, action, wp, rng, cfg)
            if is_ruin_state(s):
                break
        else:
            survived += 1
    return survived / n_rollouts  # 0.0-1.0、viability kernel所属の近似スコア

def window_open(state, horizon, threshold=0.5, **kwargs):
    return viability_score(state, horizon=horizon, **kwargs) > threshold

def closes_window(state_after, horizon, threshold=0.5, **kwargs):
    return viability_score(state_after, horizon=horizon, **kwargs) <= threshold
```

**設計上の注意**: この`viability.py`は`core/`配下に置き、
`engine/omega_full.py`からも`core/`からも呼べる共有基盤にする。
逆にomega_full.py側のスコアリング固有ロジック(drift penalty,
portfolio synergy等)はCoreに持ち込まない。これにより
「Engineが判定を左右する」という統治-実行分離の破れを防ぐ。

---

## 4. MaxForwardEngine / Strong Engineの二層構造の再利用

v7.2 open itemsに残っていた「シミュレーション検証」は、
ゼロから検証環境を作る必要がない。既存の二層構造
(civ-sim側=MaxForwardEngine で試し、real-side=Strong Engineへ
知見を還元する)が、まさにこの検証のための設計として
既に存在している。

**次のアクション候補**: v7.2のCore拡張(Horizon-Integrated Core)を、
まずcivi-sim側(MaxForwardEngine)でのみ有効化し、v7.1版との
A/Bテストを回す。real-side(Strong Engine Ω Full)への適用は、
civ-sim側での検証結果を見てから判断する。これはv8.x系の
失敗(検証なしに前進側を強化してStagnation worldで劣化した)
という前例を踏まえた、意図的に慎重な順序。

---

## 5. 未使用のまま残る資産(範囲外・記録のみ)

- `research/loom100/`: 100年企業経営シミュレーション。MaxForward
  概念への言及が複数あり(`firm_ifrs.py`等)、関連性はあるが、
  今回のTimeHorizonLayer統合の範囲には含めない。将来、
  StrongEngine側の対称拡張(項目4、前回のopen items参照)に
  着手する際に、参照資産として再検討する価値がある。

---

## 6. 更新された未解決点リスト(v3から)

1. ~~窓の測定方法~~ → 理論的定義(viability theory)は確立。
   **実装は本ドキュメントで設計したが、まだコードとして
   `core/viability.py`を作成・pushしていない。**
2. 候補行動の生成方法 — 既存の`generate_base_candidates()`
  (strong_engine.py)/ `build_candidate_pool()`(omega_full.py)が
  既にこれを担っている。**転用可能、追加実装は最小限で済む見込み。**
3. ~~lock-in判定基準~~ → viability_score閾値方式で解消(本ドキュメント §3)。
4. StrongEngine側への対称拡張 — 未着手。
5. シミュレーション検証 — MaxForwardEngine/civ-sim層を使った
   段階的検証の道筋は見えた(§4)。実行はまだ。
6. ~~$\lambda_{\text{drift}}$との重複確認~~ → 確認完了。重複ではなく
   補完関係(drift = 長期の緩やかな狭まり、window closure = 即時の
   閉鎖)として整理できる。
