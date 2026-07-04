#!/usr/bin/env python3
"""check_manifest_consistency.py — PACKAGE_MANIFEST が参照する主要ファイルの実在を確認。"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
required = [
    "validate_nrmo_integrated_v72.py", "README.md", "PACKAGE_MANIFEST.md",
    "VALIDATION_STATUS.md", "IMPLEMENTATION_STATUS.md", "requirements.txt",
    "RELEASE_CHECKLIST.md", "run_long_validations.py",
    "scripts/validate_cpp.sh",
    "code/python/nrmo_v72_phase1/run_os_validations.py",
    "code/python/nrmo_v72_phase1/validation/test_os_boundary_properties.py",
    "code/python/nrmo_v72_phase1/v7_maxforward/validate_part_a_subprocess.py",
    "code/python/nrmo_v72_phase1/v7_maxforward/validate_part_b_subprocess.py",
    "code/python/nrmo_v72_phase1/v7_maxforward/investment_stress_models.py",
    "code/python/nrmo_v72_phase1/v7_maxforward/romance_simulation_harness.py",
    "v52_codebase/governance/nrmo_core.py",
]
missing = [f for f in required if not (ROOT / f).exists()]
print("[MANIFEST CONSISTENCY]")
if missing:
    for m in missing: print(f"  MISSING: {m}")
    print(f"FAIL: {len(missing)} referenced files missing"); sys.exit(1)
print("OK: all key referenced files present"); sys.exit(0)
