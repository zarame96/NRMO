# NRMO v7.2 Phase 1 — Main Colab Notebook
# 
# このファイルは Google Colab で実行可能。
# Colab セル区切り: `# %% [markdown]` または `# %% [code]`
# 
# 使い方:
#   1. このファイルを Colab にアップロード
#   2. nrmo_v72_phase1 フォルダ全体をマウント
#   3. 各セルを順次実行

# %% [markdown]
# # NRMO v7.2 Phase 1 — ベースライン特性化ベンチマーク
# 
# このノートブックは Phase 1 を実行します:
# - v5.0, v7.1, v7.2 の 3 エンジン
# - 5 worlds × 5 horizons の 25 cells
# - 各 cell で 100K runs (Phase 1 完全版) または 1K runs (quick test)
# 
# 結果:
# - 統計検定 (KS, Mann-Whitney, Bootstrap)
# - Pareto 改善検証
# - 8 つの収束基準クリア確認

# %% [code]
# Cell 1: 環境セットアップ
import os
import sys
from pathlib import Path

# Google Drive をマウント
try:
    from google.colab import drive
    drive.mount('/content/drive')
    PHASE1_DIR = '/content/drive/MyDrive/nrmo_v72_phase1'
except ImportError:
    # ローカル実行時
    PHASE1_DIR = os.environ.get('NRMO_PHASE1_DIR', '.')

sys.path.insert(0, os.path.join(PHASE1_DIR, 'core'))
sys.path.insert(0, os.path.join(PHASE1_DIR, 'benchmark'))

print(f"PHASE1_DIR: {PHASE1_DIR}")
print(f"Contents: {os.listdir(PHASE1_DIR) if os.path.exists(PHASE1_DIR) else 'NOT FOUND'}")


# %% [code]
# Cell 2: 必要パッケージのインストール
import subprocess
subprocess.run(['pip', 'install', '-q', 'numpy', 'scipy', 'matplotlib'])

# %% [code]
# Cell 3: モジュールインポート
from world_models import World, WorldType, WorldState, Action
from engines import V50Engine, V71Engine, V72Engine
from runner import BenchmarkConfig, BenchmarkRunner, CheckpointManager
from statistical_tests import run_all_tests, ConvergenceReport
from dashboard import BenchmarkDashboard

print("All modules imported successfully")


# %% [code]
# Cell 4: クイックテスト (動作確認 1K runs)
config_quick = BenchmarkConfig(
    engines=["v5.0", "v7.1", "v7.2"],
    worlds=["Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"],
    horizons=[200, 500, 1000],
    runs_per_cell=1000,
    n_workers=4,
    checkpoint_dir=f"{PHASE1_DIR}/results_quick",
)

runner_quick = BenchmarkRunner(config_quick)
runner_quick.run_all(skip_completed=True)


# %% [code]
# Cell 5: クイックテストの結果可視化
dashboard = BenchmarkDashboard(f"{PHASE1_DIR}/results_quick")
dashboard.print_summary_table()
dashboard.plot_score_heatmap(f"{PHASE1_DIR}/quick_heatmap.png")
dashboard.plot_pareto_check(f"{PHASE1_DIR}/quick_pareto.png")
dashboard.plot_distribution_comparison(f"{PHASE1_DIR}/quick_dist.png")


# %% [code]
# Cell 6: クイックテストの統計検定
import numpy as np
import json

all_results = dashboard.all_results

# v7.1 vs v7.2 で全 cell の検定
print("\n" + "=" * 80)
print("v7.1 vs v7.2 統計検定")
print("=" * 80)

cells_checked = 0
cells_passed = 0

for r in all_results:
    if r["engine"] != "v7.2":
        continue
    
    # 対応する v7.1 を見つける
    matching = [x for x in all_results 
                 if x["engine"] == "v7.1" and 
                    x["world"] == r["world"] and 
                    x["horizon"] == r["horizon"]]
    
    if not matching:
        continue
    
    v71 = matching[0]
    baseline_scores = np.array(v71["raw_scores"])
    candidate_scores = np.array(r["raw_scores"])
    
    report = run_all_tests(
        baseline_scores, candidate_scores,
        cell_id=f"{r['world']}_H{r['horizon']}",
        baseline_name="v7.1",
        candidate_name="v7.2",
    )
    
    summary = report.summarize()
    cells_checked += 1
    if summary['all_passed']:
        cells_passed += 1
    
    print(f"\n  {summary['cell']}: All passed = {summary['all_passed']}")
    for k, v in summary['individual'].items():
        if v is not None:
            print(f"    {k}: {'✓' if v else '✗'}")

print(f"\n{'=' * 80}")
print(f"Total: {cells_passed}/{cells_checked} cells passed all criteria")


# %% [code]
# Cell 7: 本番ベンチマーク (100K runs per cell)
# 注意: これは長時間 (Colab Pro+ で数日〜数週間)
# ローカルテストでは小規模に
RUNS_PER_CELL = 100000  # Phase 1 完全版

config_full = BenchmarkConfig(
    engines=["v5.0", "v7.1", "v7.2"],
    worlds=["Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"],
    horizons=[200, 500, 1000, 2000],
    runs_per_cell=RUNS_PER_CELL,
    n_workers=8,
    checkpoint_dir=f"{PHASE1_DIR}/results_full",
)

# 安全のため、明示的に実行を有効化する
EXECUTE_FULL_BENCHMARK = False
if EXECUTE_FULL_BENCHMARK:
    runner_full = BenchmarkRunner(config_full)
    runner_full.run_all(skip_completed=True)
else:
    print("Full benchmark disabled by flag.")
    print("Set EXECUTE_FULL_BENCHMARK = True to run.")
    print(f"Total cells: 3 engines × 5 worlds × 4 horizons = 60")
    print(f"Total runs: 60 × {RUNS_PER_CELL} = {60 * RUNS_PER_CELL:,}")
    print(f"Estimated time (4 cores @ 500 runs/sec):")
    total_runs = 60 * RUNS_PER_CELL
    secs = total_runs / 500
    print(f"  {secs / 3600:.1f} hours / {secs / 86400:.1f} days")


# %% [code]
# Cell 8: 結果のサマリーとレポート出力
final_report = {
    "phase": 1,
    "completed_cells": len(dashboard.all_results),
    "summary": {},
}

for r in dashboard.all_results:
    key = f"{r['engine']}_{r['world']}_H{r['horizon']}"
    final_report["summary"][key] = r["stats"]

with open(f"{PHASE1_DIR}/phase1_final_report.json", "w") as f:
    json.dump(final_report, f, indent=2)

print("Phase 1 Final Report saved")
print(f"  Path: {PHASE1_DIR}/phase1_final_report.json")
print(f"  Cells: {len(final_report['summary'])}")
