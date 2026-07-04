#!/usr/bin/env python3
"""
[REDIRECTOR] 正式入口はパッケージ root の validate_nrmo_integrated_v72.py。
互換のため、この phase1 版は root の正式入口へ委譲する。
"""
import os, sys, subprocess
from pathlib import Path
_here = Path(__file__).resolve()
# package root を PACKAGE_MANIFEST.md の存在で探索
root = None
for p in _here.parents:
    if (p / "PACKAGE_MANIFEST.md").exists():
        root = p; break
if root is None:
    print("Cannot locate package root (PACKAGE_MANIFEST.md)"); sys.exit(1)
entry = root / "validate_nrmo_integrated_v72.py"
print(f"[redirect] running official entry: {entry}")
sys.exit(subprocess.run([sys.executable, str(entry)]).returncode)
