#!/usr/bin/env python3
"""check_no_pipe_capture.py — active validation runner が子プロセスを PIPE capture
していないことを検査する。子・孫が pipe 書き込み端を保持すると EOF 待ちで詰まるため、
runner は必ずファイル redirect + wait(timeout) + process-group kill を使う。

検査対象 (active runners):
  - validate_nrmo_integrated_v72.py
  - scripts/*.py
  - tools/*.py
  - code/python/nrmo_v72_phase1/validation/*.py
禁止パターン: capture_output=True / stdout=subprocess.PIPE / stderr=subprocess.PIPE /
              communicate(timeout
許可リスト (ALLOW): このツール自身 (パターン文字列を保持するため)。
"""
import sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOW = {"check_no_pipe_capture.py"}
BANNED = ["capture_output=True", "stdout=subprocess.PIPE",
          "stderr=subprocess.PIPE", "communicate(timeout"]

targets = [ROOT / "validate_nrmo_integrated_v72.py"]
targets += sorted((ROOT / "scripts").glob("*.py"))
targets += sorted((ROOT / "tools").glob("*.py"))
targets += sorted((ROOT / "code" / "python" / "nrmo_v72_phase1" / "validation").glob("*.py"))

print("[NO-PIPE-CAPTURE AUDIT]")
hits = []
for p in targets:
    if p.name in ALLOW or not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    for pat in BANNED:
        if pat in text:
            hits.append((str(p.relative_to(ROOT)), pat))
if hits:
    for f, pat in hits:
        print(f"  FAIL: {f} uses '{pat}'")
    print(f"FOUND {len(hits)} banned PIPE/capture usages in active runners"); sys.exit(1)
print("OK: no PIPE/capture in active validation runners (file-redirect only)")
sys.exit(0)
