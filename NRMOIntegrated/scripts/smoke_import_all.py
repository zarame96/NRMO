#!/usr/bin/env python3
"""smoke_import_all.py — core 配下の全 py を import し、import error を検出する (P2-3)。"""
import importlib, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "code" / "python" / "nrmo_v72_phase1" / "core"
sys.path.insert(0, str(CORE))
fails = []
for py in sorted(CORE.glob("*.py")):
    if py.name == "__init__.py":
        continue
    name = py.stem
    try:
        importlib.import_module(name)
        print(f"PASS import: {name}")
    except Exception as e:
        fails.append((name, f"{type(e).__name__}: {e}"))
        print(f"FAIL import: {name}  -- {type(e).__name__}: {e}")
print("-" * 50)
if fails:
    print(f"SMOKE IMPORT: {len(fails)} FAILED"); sys.exit(1)
print("SMOKE IMPORT: ALL CORE MODULES IMPORT OK"); sys.exit(0)
