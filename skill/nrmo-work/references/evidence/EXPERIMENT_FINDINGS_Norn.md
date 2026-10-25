# Norn 実エンジン実験 — 所見 (v0.4.18)

発端: 「リアルっぽい実験をしたらいい」（Zarame）。ChatGPT 版 `norn_realtest.py`(実エンジンを
店舗3シナリオで1回ずつ叩く)を、DecisionCompass の統合スタック上で**時系列実験**へ発展させた。
実装: `scripts/norn_experiment.py`。実 NRMO(4部品装着済み bridge)を16日分の店舗状況で駆動し、
各日の出力を Norn(永続化)が観測 → 再起動相当の新 Norn が DB を読んで drift_report。

> **2026-09-09 追補（原記録を保持した原因分析の訂正）**
>
> 以下の「結果」は v0.4.18 当時の負の実験証拠として有効であり、削除・改変しない。
> ただし当時の「DecisionCompass 側の配線バグではない」「NRMO 理論側の宿題」という原因帰属は、
> その後のコード調査により**過度に強い結論だった**ことが判明した。
>
> 少なくとも次の実装要因が後から確認・修正された。
> 1. `AggressiveEngineSubmodule` / `ExplorationCandidateModule` の候補期待値が固定値で、状態変化が候補評価へ十分伝播しなかった。
> 2. `integrator_bridge` が `selected_action` を admissible 候補へ差し替えた後も、`forward_score` を旧選択の値のまま保持する経路があり、選択とスコアが同期していなかった。
>
> したがって本実験が証明したのは「当時の production 統合スタックの観測可能出力が状態変化へ反応しなかった」ことまでであり、
> その原因を NRMO 理論単独へ帰属することではない。現在は **理論 / engine implementation / bridge / experiment design** を分離して評価する。
> 2026-09-09 main には状態感応性と selected/forward 同期の回帰修正が入り、別途回帰テストも追加された。
> ただしこれは real-world validation を意味せず、StrongEngine Ω Full production 統合（Issue #87）の再検証も別途必要である。

## 実験条件
- 16日。Phase A(0-9)安定 → Phase B(10-13)じわじわ悪化(資源↓/露出↑) → 14悪化継続 →
  15急変ショック(資源0.22/露出0.88/防衛モード)。意図的に「緩慢」と「急変」を混在。
- 状況は DecisionContext(resources/exposure/stability/options)で与え、pipeline が R/E/G/O/K/X に
  変換してエンジンへ(配線は検証済み: resources→R, exposure→X)。

## 結果（実測・正直な記録）
- **エンジンは genuine に走っている**: 16日すべて OODA 仮説5・DAG PASS・procedure genuinely_ran=True
  (not_genuine 0 / unobservable 0)。domain=work(unknown 解消)。passive/active も観測(level none)。
  永続化16件、z 割れ無し。→ 監査基盤としては完全に機能。
- **しかし drift は全 STABLE**。15日目に資源急落・露出急騰・防衛モードの急変を入れても、
  SIGNAL も DRIFT も出ない。
- 診断: 安定→悪化→急変で、エンジンの観測可能出力が**ほぼ不変**だった:
  - selected_action = recover（固定）
  - forward_score = 0.5（固定）
  - admissible = recover/invest/defend/explore（並び替わるのみ、4件固定）
  - passive_pattern = none（固定）
  - forgone_forward 合計 19.95（候補を渡せば値は出るが、日次でほぼ一定）

## 解釈（v0.4.18 当時の解釈。2026-09-09追補を優先）
- Norn の STABLE は**誤りではなく正しい**。「変化すべきものが変化していない」を正直に捉えている。
  計測器は動作しており、不変なのは観測対象（エンジン出力）の側。
- すなわち本実験は、本プロジェクトが一貫して明記してきた**最大の既知ギャップ**を実証した:
  > 「NRMO の判断品質 vs 現実は未検証」。
  プロキシ実装の StrongEngine Ω Full は、状況の深刻さ(資源・露出の大変動)を
  観測可能な選択・前進スコアの差として**まだ表現していない**。
- 当時は「これは NRMOIntegrated 本体の設計課題であり、DecisionCompass 側の配線バグではない」と解釈した。
  **この原因帰属は2026-09-09時点では撤回・訂正する。** 状態伝播が存在していても、候補生成の固定期待値と
  bridge の selected/forward 非同期が状態感応性を失わせ得たためである。原実験結果そのものは負の証拠として保持する。

## 次の一手（2026-09-09更新）
- (A) `scripts/norn_experiment.py` を回帰計測器として維持し、修正前後で同一シナリオを比較する。
- (B) Issue #87 / PR #88 の StrongEngine Ω Full production 実装を、現在 main の状態感応性修正を失わない形で再統合する。
- (C) Norn の観測軸を拡張（forward_score/selected 同一性/admissible 幅/mode を事実として記録）。
- (D) simulation / CI / Provider Verified / real-world validation を別の証拠段階として扱い、相互に代用しない。

## ChatGPT handoff との関係
handoff の audit_observer.py / drift_reporter.py / norn_realtest.py は、本ビルドの統合版が
**既に取り込み・上回り済み**: z 割れ修正(v0.4.13)、4部品装着(v0.4.14)、active 配管(v0.4.15)、
SQLite 永続化(v0.4.16)。handoff 記載の「domain 修正」も本実験では context 由来で domain=work を確認。
未修正とされた z 割れも本ビルドでは解消済み。realtest は本 harness が時系列・統合版として継承。
