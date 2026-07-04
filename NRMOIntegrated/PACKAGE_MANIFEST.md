# NRMO Integrated System v7.2 — 全同梱パッケージ

統一版: **v7.2**（書面のシステム/モノグラフ版を v7.2 に統一。各 Part の出自版は
version_manifest に provenance として保持）。

## 同梱物
- **PDF**: `NRMO_Integrated_System_v7_2.pdf`（511頁・英語のみ・CJK 0・タイトル v7.2）
- **LaTeX**: master `NRMO_Complete_v5_5.tex` + `chapters/ parts/ frontmatter/ appendices/ assets/`
  （v7 Realignment 7章 + Phase D/E 節 + english-only 化 + 版統一 適用済）
- **Python**: `code/python/`
  - `nrmo_v72_phase1/`（本物の Ω Full / Shinobi / MAPLayer / Loom / Unified / v851 等）
    - `core/loom_canonical.py`（★Loom 正典 pin）
    - core_fixes 適用済（loom_core cumulative 配線+消費、falsifiability is_triggered、
      最大前進 C 解禁）
    - `v7_maxforward/`（二層構造・分離契約・本物駆動・各報告）
  - `loom_*`, `nrmo_universal_adapter.py` 等のアダプタ
- **C++**: `code/cpp/nrmo_core.hpp`, `example_store.cpp`（構文確認済 g++ -std=c++17）
- **frontend**: `code/frontend/`
- **旧コード基盤**: `v52_codebase/`（CivState 単一文明研究コード）, `world_sim_v50/`（多文明シム）

## Loom 正典 (loom_canonical.py)
- 制御核 (production / Ω Full 最大前進): **`loom_core.LoomCore`**
- standalone Loom エンジン運用識別: **`loom_v3_1_shadow.LoomV31Shadow`**
  （Loom v3.1 凍結 Behavioral Core + Sociable Shadow。v3.2/v3.2.1 は negative result→archived）

## 検証
- `code/python/nrmo_v72_phase1/validation/test_v8_integrity.py` … 14/14 PASS
- `v7_maxforward/run_all_validations.py` … 本物サブシステム10 + 分離契約8 = ALL PASS
- `v7_maxforward/omega_full_integrated.py` … 本物 Wolf/Shinobi/MAPLayer/Norn-Skuld/Loom 駆動

## ビルド
```
pdflatex -shell-escape -interaction=nonstopmode NRMO_Complete_v5_5.tex
bibtex NRMO_Complete_v5_5 ; makeindex NRMO_Complete_v5_5.idx
pdflatex ... ; pdflatex ...   # 計3パス
```

## 既知のベースライン事項（本作業由来でない）
- LaTeX: 既存 source の未定義列型 `C`（Illegal pream-token, 42件）、source 既存の
  undefined ref 6件（プレースホルダ）。
- `v8_engine.py` の監視層 placeholder 3件（被置換の実験エンジン、現役 path 外）。
- investment/romance domain harness は別 bundle（本パッケージ未収録）。

---

## OS/SOP モジュール (v7.2 本フェーズ追加)

配置: `code/python/nrmo_v72_phase1/core/`
- common_types, dag_layer, parallel_ooda, hst_n, aallowed, apcso, secretary_console,
  shutdown_guard, ttm_pps, defensive_offense, investment_sop, hare_no_hi, life_sop,
  mode_selector, nonergodic_monitor, time_horizon, situation_parameters,
  meta_governance, nrmo_os_integrator

テスト: `code/python/nrmo_v72_phase1/validation/test_*.py` × 16

### 正式検証入口
`code/python/nrmo_v72_phase1/validate_nrmo_integrated_v72.py`
- v8 integrity 14/14 / Omega 10/10 + 分離 8/8 / OS/SOP 40/40 / C++ compile
- 実 nrmo_core adapter は `NRMO_ROOT_PATH` 設定時のみ (任意)
- SKIP があれば ALL PASS とは表示しない

### 環境変数 (v7.2)
- `NRMO_CORE_PATH` (旧 `NRMO_V6_CORE` 後方互換)
- `NRMO_ROOT_PATH` (旧 `NRMO_V6_ROOT` 後方互換)

### OS validation runner
`code/python/nrmo_v72_phase1/run_os_validations.py` → 40/40 PASS WITH NO SKIPS

### 注意
製品版完成ではない。investment/romance domain harness は本フェーズで
パッケージ内に自己完結実装 (proxy dynamics; 外部 bundle 依存を撤廃)。
proxy を実 dynamics と称さない。simulation を proof と呼ばない。


### Domain harness (自己完結, v7.2 本フェーズ)
- `v7_maxforward/investment_stress_models.py` — 投資ストレス proxy シナリオ (MarketScenario / run_static_policy)
- `v7_maxforward/romance_simulation_harness.py` — 関係性 proxy harness (REGIMES / init_state / step / outcome, 倫理 guard 内蔵)
- `v7_maxforward/v7_adapters.py`, `v7_validate.py` — 外部 `/tmp/vbundle` パス挿入を撤廃し `__file__` 基準に自己完結化
- `validation/test_domain_harness.py` — 外部 bundle 非依存を検証
これらは **proxy domain dynamics** であり、真の市場/人間 dynamics ではない。

---

## v7.2 10/10 hardening (2026-06-01)

### 正式検証入口 (package root)
- `validate_nrmo_integrated_v72.py` — per-step timeout + subprocess 隔離 + `validation_results.json` 生成 +
  厳密表示 (FAIL/TIMEOUT/required-SKIP→FAIL; optional-SKIP→PARTIAL; 全required PASS→ALL REQUIRED ... NO SKIPS)。
- `code/python/nrmo_v72_phase1/validate_nrmo_integrated_v72.py` は root 入口への redirector。

### Part A/B subprocess 分離
- `v7_maxforward/validate_part_a_subprocess.py` — 本物サブシステム生存 (ALL SUBSYSTEMS ALIVE)。
- `v7_maxforward/validate_part_b_subprocess.py` — NRMO/Engine 分離契約 8 + 軽量 domain reproduce。

### テスト深化 / 長期分離
- `validation/test_os_boundary_properties.py` — boundary/property テスト (30)。
- `run_long_validations.py` — 長期 rollout (steps≥150, seeds≥10, horizon≥20) を入口から分離 (任意)。

### 製品品質
- `requirements.txt` (numpy のみ), `.github/workflows/validate.yml` (CI),
  `scripts/smoke_import_all.py`, `scripts/validate_cpp.sh`,
  `tools/terminology_audit.py`, `tools/check_manifest_consistency.py`,
  `tools/check_validation_status_consistency.py`, `RELEASE_CHECKLIST.md`。
- `nrmo_os_integrator` は decision_trace を全層出力 (`write_trace`)。Shutdown は
  NONE/SAFE_ROUTE/HOLD_ONLY/HARD_SILENCE の 3 段階で、HARD_SILENCE 時は空文字を返す。

### 表現規約 (proxy 明記)
- store/investment/romance harness は **proxy dynamics**。
- Type ZERO / Passive Pattern は **operational proxy adapters** (完全な認知/人格エミュレーションではない)。
- ローカル絶対パス (ユーザーホーム配下や一時ディレクトリ等) は active code から除去済 (archive を除き grep 0)。
