#!/usr/bin/env bash
# C++ 参照実装の構文チェック (g++ 必須)。package-relative。
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/code/cpp"
if ! command -v g++ >/dev/null 2>&1; then
  echo "FAIL: g++ not found (install g++ to run C++ syntax check)"
  exit 1
fi
g++ -std=c++17 -fsyntax-only "$CPP/example_store.cpp" -I "$CPP"
echo "C++ syntax OK"
