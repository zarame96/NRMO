#!/bin/bash
# NRMO v7.2 Phase 1 — Results Analyzer
#
# 使い方: ./analyze_results.sh [quick|full]

set -e

MODE="${1:-quick}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "============================================================"
echo "NRMO v7.2 Phase 1 — Results Analysis"
echo "Mode: $MODE"
echo "============================================================"

cd "$PROJECT_ROOT/benchmark"

python3 <<EOF
import sys, os
sys.path.insert(0, '$PROJECT_ROOT/core')
sys.path.insert(0, '$PROJECT_ROOT/benchmark')

import numpy as np
from dashboard import BenchmarkDashboard
from statistical_tests import run_all_tests

results_dir = "$PROJECT_ROOT/results_${MODE}"
output_dir = "$PROJECT_ROOT/analysis_${MODE}"
os.makedirs(output_dir, exist_ok=True)

dashboard = BenchmarkDashboard(results_dir)
print(f"Loaded {len(dashboard.all_results)} cells from {results_dir}")

if not dashboard.all_results:
    print("No results to analyze. Run benchmark first.")
    sys.exit(1)

# 可視化
dashboard.print_summary_table()
dashboard.plot_score_heatmap(f"{output_dir}/heatmap.png")
dashboard.plot_pareto_check(f"{output_dir}/pareto.png")
dashboard.plot_distribution_comparison(f"{output_dir}/distribution.png")

# 統計検定: v7.1 vs v7.2
print("\n" + "=" * 80)
print("Statistical Tests: v7.1 vs v7.2")
print("=" * 80)

cells_passed = 0
cells_total = 0

for r in dashboard.all_results:
    if r["engine"] != "v7.2":
        continue
    
    matching = [x for x in dashboard.all_results
                if x["engine"] == "v7.1" and
                x["world"] == r["world"] and
                x["horizon"] == r["horizon"]]
    
    if not matching:
        continue
    
    v71 = matching[0]
    baseline = np.array(v71["raw_scores"])
    candidate = np.array(r["raw_scores"])
    
    report = run_all_tests(
        baseline, candidate,
        cell_id=f"{r['world']}_H{r['horizon']}"
    )
    
    summary = report.summarize()
    cells_total += 1
    if summary["all_passed"]:
        cells_passed += 1
    
    status = "✓" if summary["all_passed"] else "✗"
    print(f"  [{status}] {summary['cell']}")
    for k, v in summary["individual"].items():
        if v is not None:
            print(f"      {k}: {'✓' if v else '✗'}")

print(f"\n{'=' * 80}")
print(f"Overall: {cells_passed}/{cells_total} cells passed all 8 criteria")
print(f"Analysis saved to: {output_dir}")
EOF
