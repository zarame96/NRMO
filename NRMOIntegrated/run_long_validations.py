#!/usr/bin/env python3
"""
run_long_validations.py — 長期検証 (正式入口から分離, P1-7)。任意。
heavy rollout: steps>=150, seeds>=10, horizon>=20。
内容:
  1. v7_maxforward/run_all_validations.py  (本物サブシステム + 分離契約 + full domain reproduce)
  2. v7_maxforward/v7_validate.py          (store/investment/romance 3 domain フル)
正式入口 (validate_nrmo_integrated_v72.py) は軽量版を使う。こちらは時間がかかる。
"""
from pathlib import Path
import subprocess, sys, time

ROOT = Path(__file__).resolve().parent
MF = ROOT / "code" / "python" / "nrmo_v72_phase1" / "v7_maxforward"

STEPS = [
    ("real nrmo_core adapter (bundled v52_codebase)",
     [sys.executable, str(MF / "nrmo_separation_realcheck.py")], 300),
    ("run_all_validations (full)", [sys.executable, str(MF / "run_all_validations.py")], 600),
    ("v7_validate 3-domain (full)", [sys.executable, str(MF / "v7_validate.py")], 600),
]

def main():
    print("NRMO long-run validations (optional, heavy)")
    print("=" * 60)
    fail = 0
    for name, cmd, to in STEPS:
        t = time.time()
        try:
            r = subprocess.run(cmd, cwd=str(MF), capture_output=True, text=True, timeout=to)
            ok = r.returncode == 0
            print(f"{'PASS' if ok else 'FAIL'}: {name} ({time.time()-t:.1f}s)")
            if not ok:
                fail += 1
                print(r.stdout[-1500:]); print(r.stderr[-800:])
            else:
                print("  " + (r.stdout.strip().split("\n")[-1] if r.stdout.strip() else ""))
        except subprocess.TimeoutExpired:
            fail += 1; print(f"TIMEOUT: {name}")
    print("-" * 60)
    print("LONG-RUN: ALL PASS" if fail == 0 else f"LONG-RUN: {fail} FAILED")
    sys.exit(1 if fail else 0)

if __name__ == "__main__":
    main()
