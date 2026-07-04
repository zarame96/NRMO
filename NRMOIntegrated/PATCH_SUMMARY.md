# PATCH_SUMMARY — OS/SOP Code化 + hygiene (2026-05-31)

## 追加 (18 OS/SOP モジュール, core/)
common_types, dag_layer, parallel_ooda, hst_n, aallowed, apcso, secretary_console,
shutdown_guard, ttm_pps, defensive_offense, investment_sop, hare_no_hi, life_sop,
mode_selector, nonergodic_monitor, time_horizon, situation_parameters,
meta_governance, nrmo_os_integrator。

ユーザー指摘の未収録分も実装: TTM/PPS, Secretary Console, Investment SOP, Life SOP,
Hare-no-Hi / Narrative Random Generator。

## テスト/検証
- validation/test_*.py × 16 (各モジュール単体)
- run_os_validations.py: 40/40 PASS, SKIP 0 (SKIP時に ALL PASS と出さない)
- validate_nrmo_integrated_v72.py (正式入口): v8 14/14 + Omega 10/10 + 分離 8/8 +
  OS 40/40 + C++ compile = CORE VALIDATION PASS

## hygiene 修正
- run_all_validations.py: SKIP時 ALL PASS 誤表示を修正 (real core 有→ALL PASS WITH REAL CORE,
  無→PARTIAL PASS, exit 2)。
- 環境変数別名 NRMO_CORE_PATH / NRMO_ROOT_PATH 追加 (旧 NRMO_V6_* も後方互換)。

## domain harness 自己完結化 (外部 bundle 撤廃)
- `investment_stress_models.py` / `romance_simulation_harness.py` をパッケージ内に新規実装 (proxy dynamics)。
- `v7_adapters.py` / `v7_validate.py` の 外部 bundle パス挿入を撤廃 (__file__ 基準)。
- `v7_validate.py` が 3 domain (store/investment/romance) を外部依存なしで完走。
- 実 nrmo_core adapter も同梱 `v52_codebase` を既定参照 (ruin=0, admissible違反=0)。
- 正式入口 `validate_nrmo_integrated_v72.py` → **ALL VALIDATION PASS** (SKIP なし)。

## strict separation audit (Task 4)
core の本物 Engine (strong_engine_omega_full/shinobi/map_layer/unified) に
ruin_penalty/veto_threshold/override_veto/mutate_boundary の参照なし。
分離違反語彙は separation_engine.py の「排除」を明記するコメントのみ。

## 注意 (誤読防止)
製品版完成ではない。investment/romance domain harness は本フェーズで自己完結実装済 (proxy)。
proxy を実 dynamics と称さない。simulation を proof と呼ばない。
