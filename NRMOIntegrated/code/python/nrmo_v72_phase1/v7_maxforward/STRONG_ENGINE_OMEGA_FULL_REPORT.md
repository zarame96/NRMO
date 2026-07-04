# StrongEngine Ω Full — 訂正 + 本物サブシステムの駆動・検証

作成日: 2026-05-30 (訂正版)

## 0. 訂正 (重要)

前版で私が作った `strong_engine_omega_full.py` は本物と同名の薄いスタブで、
Wolf/Shinobi/MAPLayer/Norn-Skuld の名前を騙る中身の薄い実装だった。これは誤り。
本物の完全実装は既に存在する:

  code/python/nrmo_v72_phase1/core/
    strong_engine_omega_full.py … StrongEngineOmegaFull (Aggressive: Wolf Pursuit /
      small_reversible_attack / anti_stagnation / momentum_exploitation,
      Defensive/Recovery/Exploration 候補 module, Mutation/Synthesis/Invention pathway)
    shinobi_engine.py … ShinobiEngine (Norn/Skuld task manager + 12 units P/E cores
      + Thompson Sampling learners 防御/race)
    map_layer.py … MAPLayer (L1/L2/L3 V-Cache 階層履歴, regime shift 検出)
    loom_engine.py … LoomEngine (sparse-candidate 決定境界)
    unified_engine.py … 上記を統合

対応: スタブを削除し、本物の実コードをそのまま駆動して各サブシステムが
スカスカでなく実際に発火することを実証した。

---

## 1. 本物サブシステムの駆動・検証 (engine/omega_full_integrated.py)

実 UnifiedEngine / ShinobiEngine / LoomEngine を実 ChaoticWorld 上で駆動し、
各サブシステムの実カウンタで生存を確認 (代表 seed):

- Aggressive (Wolf Pursuit 等): mode_counters wolf_pursuit 生成2/採用1,
  small_reversible_attack 16/2, anti_stagnation 11/0; generated_count=29, eligible=16
- MAPLayer V-Cache: L1=5, L2=10, L3=41 events, near_ruin=13, regime_shift=28
- Shinobi (Norn/Skuld/Thompson): 12 units (P=4,E=8), Norn 使用10/10,
  race learner posteriors=4, 防御 learner 機構 functional
- Loom: 69 decisions, sparse threads 平均2.8

生存検証 10 項目すべて PASS (ALL SUBSYSTEMS ALIVE / non-hollow)。
加えて本物パッケージ自身の統合テスト validation/test_v8_integrity.py は 14/14 PASS。

---

## 2. NRMO 分離契約 (engine/run_all_validations.py Part B, separation_engine.py)

批評の分離規律 (propose→filter→select, ruin_penalty 排除, veto 閾値非参照) を
汎用参照 engine で検証 (numpy のみ, 一発実行)。generator は汎用名
(ForwardPush/LowExposurePath/WeakDimRepair/Diversify/Baseline) とし、本物の
サブシステム名は騙らない。8 契約 invariant すべて PASS:

  engine_never_reads_veto_thresholds / selected_action_always_in_admissible /
  vetoed_action_unreachable / empty_admissible_returns_hold /
  domain_rollout_uses_domain_dynamics / memory_changes_future_candidate_distribution /
  no_NRMO_boundary_mutation_by_engine / all_domain_examples_reproduce

実 nrmo_core への接続 (engine/nrmo_separation_realcheck.py):
実 construct_admissible_set を Governance.filter として 120 step,
ruin=0 / admissible違反=0。Engine は実 NRMO の filter() のみ黒箱使用。

一発実行 python3 engine/run_all_validations.py (NRMO_V6_CORE 設定時):
Part A 本物10 + Part B 契約8 = ALL PASS。

---

## 3. 実行
    # 本物サブシステム駆動・検証
    NRMO_V6_CORE=/path/NRMO_v6_Repaired/code/python/nrmo_v72_phase1/core \
      python3 engine/omega_full_integrated.py
    # 一発検証 (本物 + 分離契約)
    NRMO_V6_CORE=/path/.../core python3 engine/run_all_validations.py
    # 実 nrmo_core 分離
    NRMO_V6_ROOT=/path/NRMO_v6_Repaired python3 engine/nrmo_separation_realcheck.py

## 4. 正直なまとめ
- 本物の Ω Full サブシステムは実装済みで動作する (上記カウンタ・14/14 テストが証跡)。
- 私の前版スタブは削除。本物の名前は実コードにのみ使用。
- separation_engine.py は分離契約検証用の汎用参照であり、本物の代替や模倣ではない。
