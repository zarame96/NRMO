#!/bin/bash
# NRMO v7.2 Phase 1 — Baseline Benchmark Runner
#
# 使い方: ./run_baseline.sh [quick|full]
#   quick: 1000 runs (動作確認)
#   full:  100,000 runs (本番)

set -e

MODE="${1:-quick}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "============================================================"
echo "NRMO v7.2 Phase 1 — Baseline Benchmark"
echo "Mode: $MODE"
echo "Project root: $PROJECT_ROOT"
echo "============================================================"

cd "$PROJECT_ROOT/benchmark"

case "$MODE" in
    quick)
        N_RUNS=1000
        ;;
    full)
        N_RUNS=100000
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Usage: $0 [quick|full]"
        exit 1
        ;;
esac

# Python で実行
python3 <<EOF
import sys, os
sys.path.insert(0, '$PROJECT_ROOT/core')
sys.path.insert(0, '$PROJECT_ROOT/benchmark')

from runner import BenchmarkConfig, BenchmarkRunner

config = BenchmarkConfig(
    engines=["v5.0", "v7.1", "v7.2"],
    worlds=["Normal", "FastExpansion", "Vulnerable", "Stagnation", "Race"],
    horizons=[200, 500, 1000],
    runs_per_cell=$N_RUNS,
    n_workers=4,
    checkpoint_dir="$PROJECT_ROOT/results_${MODE}",
)

runner = BenchmarkRunner(config)
runner.run_all()
EOF

echo ""
echo "============================================================"
echo "Benchmark complete. Run analysis:"
echo "  $SCRIPT_DIR/analyze_results.sh $MODE"
echo "============================================================"
