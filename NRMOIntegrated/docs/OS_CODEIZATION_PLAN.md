# OS CODEIZATION PLAN — 実施記録 (2026-05-31)

目的: 仕様中心だった OS/SOP/認知補助系を、監査可能な小モジュールへ Code 化。
方針: 巨大 NRMO クラスを作らない。Small modules / Clear authority / Deterministic tests /
      No boundary mutation / No fake completion claim。

実装 (core/): common_types, dag_layer, parallel_ooda, hst_n, aallowed, apcso,
  secretary_console, shutdown_guard, ttm_pps, defensive_offense, investment_sop,
  hare_no_hi, life_sop, mode_selector, nonergodic_monitor, time_horizon,
  situation_parameters, meta_governance, nrmo_os_integrator。
テスト (validation/): test_*.py × 16。
runner: run_os_validations.py (SKIP時 ALL PASS 禁止), validate_nrmo_integrated_v72.py (正式入口)。

統合: nrmo_os_integrator が
  raw → Shutdown → Secretary → DAG → HST-N → ModeSelector → TypeZero(opt)
      → PassivePattern(opt) → ParallelOODA → Aallowed → NRMO.filter
      → Engine.select(opt) → APCSO → MetaGovernance.audit
の順で調停。OS は境界を変えず、Engine は admissible のみ受け取る。

正しい完成表現: executable research reference implementation with OS/SOP modules codeized,
with authority-boundary validation. (製品版完成ではない)
