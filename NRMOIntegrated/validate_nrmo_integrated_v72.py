#!/usr/bin/env python3
"""NRMO Integrated v7.2 provenance-aware validation entry.

The NRMO repository is the specification/provenance source of truth. The current
executable runtime is maintained in zarame96/DecisionCompass and is intentionally
excluded from this repository by .gitignore.

Default behavior validates provenance only and MUST NOT report a runtime FULL PASS.
Runtime validation requires an explicit DecisionCompass checkout via --runtime-root
and verifies the checkout SHA before executing the delegated validation suite.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

SPEC_ROOT = Path(__file__).resolve().parent
NRMO_REPO_ROOT = SPEC_ROOT.parent
PINNED_RUNTIME_REPOSITORY = "zarame96/DecisionCompass"
PINNED_RUNTIME_SHA = "ae00f9fd23760a6b4dd078723a1eed74ef7bffc9"
SOURCE_OF_TRUTH_FILE = SPEC_ROOT / "IMPLEMENTATION_SOURCE_OF_TRUTH.md"
RESULTS_FILE = SPEC_ROOT / "validation_results.json"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Validate NRMO provenance, or delegate FULL runtime validation to an explicit DecisionCompass checkout."
    )
    p.add_argument(
        "--check-provenance",
        action="store_true",
        help="Validate the NRMO repository/source-of-truth declaration only (no runtime FULL PASS).",
    )
    p.add_argument(
        "--runtime-root",
        type=Path,
        help="Path to a checked-out zarame96/DecisionCompass repository root.",
    )
    p.add_argument(
        "--expected-runtime-sha",
        default=PINNED_RUNTIME_SHA,
        help="Exact DecisionCompass commit expected for this validation run.",
    )
    return p


def _git_head(repo: Path) -> str:
    try:
        cp = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except Exception as exc:
        raise RuntimeError(f"cannot inspect runtime git SHA: {exc}") from exc
    if cp.returncode != 0:
        raise RuntimeError(f"runtime root is not a readable git checkout: {cp.stderr.strip()}")
    return cp.stdout.strip()


def check_provenance() -> int:
    errors = []
    gitignore = NRMO_REPO_ROOT / ".gitignore"
    if not SOURCE_OF_TRUTH_FILE.is_file():
        errors.append("missing IMPLEMENTATION_SOURCE_OF_TRUTH.md")
    if not gitignore.is_file():
        errors.append("missing repository .gitignore")
    else:
        text = gitignore.read_text(encoding="utf-8", errors="replace")
        if "NRMOIntegrated/code/" not in text:
            errors.append(".gitignore does not exclude NRMOIntegrated/code/")
        if "DecisionCompass" not in text:
            errors.append(".gitignore does not state DecisionCompass runtime ownership")
    if (SPEC_ROOT / "code").exists():
        errors.append("NRMOIntegrated/code exists despite external-runtime source-of-truth policy")

    manifest = SPEC_ROOT / "PACKAGE_MANIFEST.md"
    if not manifest.is_file():
        errors.append("missing PACKAGE_MANIFEST.md")
    else:
        text = manifest.read_text(encoding="utf-8", errors="replace")
        if PINNED_RUNTIME_REPOSITORY not in text:
            errors.append("PACKAGE_MANIFEST.md does not name the runtime source-of-truth repository")
        if PINNED_RUNTIME_SHA not in text:
            errors.append("PACKAGE_MANIFEST.md does not pin the audited runtime SHA")

    record = {
        "validation_scope": "nrmo_repository_provenance_only",
        "runtime_validated": False,
        "runtime_repository": PINNED_RUNTIME_REPOSITORY,
        "pinned_runtime_sha": PINNED_RUNTIME_SHA,
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
    }
    RESULTS_FILE.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    if errors:
        print("FINAL: FAIL — NRMO provenance check")
        for err in errors:
            print(f"- {err}")
        return 1
    print("FINAL: PROVENANCE PASS ONLY — RUNTIME NOT VALIDATED")
    print(f"runtime source: {PINNED_RUNTIME_REPOSITORY}@{PINNED_RUNTIME_SHA}")
    return 0


def _rel(path: object, runtime_integrated: Path) -> str:
    s = str(path)
    try:
        return os.path.relpath(s, str(runtime_integrated)) if s.startswith(str(runtime_integrated)) else s
    except Exception:
        return s


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _run_step(step: dict, cwd: Path, env: dict) -> dict:
    start = time.time()
    fd, log_path = tempfile.mkstemp(prefix="nrmo_step_", suffix=".log")
    os.close(fd)
    try:
        with open(log_path, "w", encoding="utf-8", errors="ignore") as out:
            proc = subprocess.Popen(
                step["cmd"], cwd=str(cwd), env=env, text=True,
                stdout=out, stderr=subprocess.STDOUT, start_new_session=True,
            )
            try:
                proc.wait(timeout=step["timeout"])
                rc = proc.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_group(proc)
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
                rc = -1
        text = Path(log_path).read_text(encoding="utf-8", errors="ignore")
        markers_ok = all(m in text for m in step.get("pass_markers", []))
        status = "TIMEOUT" if timed_out else ("PASS" if rc == 0 and markers_ok else "FAIL")
        return {
            "name": step["name"],
            "cmd": [_rel(c, cwd) for c in step["cmd"]],
            "required": True,
            "returncode": rc,
            "elapsed": round(time.time() - start, 2),
            "status": status,
            "stdout": text[-5000:],
        }
    finally:
        try:
            os.unlink(log_path)
        except Exception:
            pass


def validate_runtime(runtime_repo: Path, expected_sha: str) -> int:
    runtime_repo = runtime_repo.resolve()
    actual_sha = _git_head(runtime_repo)
    if actual_sha != expected_sha:
        print("FINAL: FAIL — runtime SHA mismatch")
        print(f"expected: {expected_sha}")
        print(f"actual:   {actual_sha}")
        return 1

    runtime_integrated = runtime_repo / "NRMOIntegrated"
    phase1 = runtime_integrated / "code" / "python" / "nrmo_v72_phase1"
    core = phase1 / "core"
    required_paths = [
        phase1 / "run_os_validations.py",
        phase1 / "validation" / "test_os_boundary_properties.py",
        phase1 / "validation" / "test_v8_integrity.py",
        phase1 / "v7_maxforward" / "validate_part_a_subprocess.py",
        phase1 / "v7_maxforward" / "validate_part_b_subprocess.py",
        phase1 / "validation" / "test_domain_harness.py",
        runtime_integrated / "scripts" / "validate_cpp.sh",
        runtime_integrated / "tools" / "check_no_pipe_capture.py",
    ]
    missing = [str(p) for p in required_paths if not p.is_file()]
    if missing:
        print("FINAL: FAIL — pinned runtime checkout is incomplete")
        for p in missing:
            print(f"- missing: {p}")
        return 1

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(core), str(phase1), str(phase1 / "v7_maxforward"), env.get("PYTHONPATH", "")]
    )
    steps = [
        {"name": "OS/SOP validation", "cmd": [sys.executable, str(phase1 / "run_os_validations.py")], "timeout": 120, "pass_markers": ["ALL PASS WITH NO SKIPS"]},
        {"name": "OS/SOP boundary+property", "cmd": [sys.executable, str(phase1 / "validation" / "test_os_boundary_properties.py")], "timeout": 120, "pass_markers": ["ALL BOUNDARY/PROPERTY PASS"]},
        {"name": "v8 integrity", "cmd": [sys.executable, str(phase1 / "validation" / "test_v8_integrity.py")], "timeout": 120, "pass_markers": []},
        {"name": "Omega subsystem alive", "cmd": [sys.executable, str(phase1 / "v7_maxforward" / "validate_part_a_subprocess.py")], "timeout": 180, "pass_markers": ["ALL SUBSYSTEMS ALIVE"]},
        {"name": "NRMO separation contract", "cmd": [sys.executable, str(phase1 / "v7_maxforward" / "validate_part_b_subprocess.py")], "timeout": 180, "pass_markers": ["ALL PASS"]},
        {"name": "domain harness", "cmd": [sys.executable, str(phase1 / "validation" / "test_domain_harness.py")], "timeout": 120, "pass_markers": ["domain_harness OK"]},
        {"name": "C++ syntax", "cmd": ["bash", str(runtime_integrated / "scripts" / "validate_cpp.sh")], "timeout": 120, "pass_markers": ["C++ syntax OK"]},
        {"name": "no-pipe audit", "cmd": [sys.executable, str(runtime_integrated / "tools" / "check_no_pipe_capture.py")], "timeout": 60, "pass_markers": ["no PIPE/capture in active validation runners"]},
    ]

    results = [_run_step(step, runtime_integrated, env) for step in steps]
    report = {
        "validation_scope": "delegated_runtime_full",
        "runtime_repository": PINNED_RUNTIME_REPOSITORY,
        "expected_runtime_sha": expected_sha,
        "actual_runtime_sha": actual_sha,
        "runtime_root": str(runtime_repo),
        "results": results,
    }
    RESULTS_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    failed = [r for r in results if r["status"] != "PASS"]
    for r in results:
        print(f"{r['status']}: {r['name']} ({r['elapsed']:.2f}s)")
    if failed:
        print("FINAL: FAIL — delegated runtime validation")
        return 1
    print("FINAL: ALL DELEGATED RUNTIME VALIDATIONS PASS WITH NO SKIPS")
    print(f"validated runtime SHA: {actual_sha}")
    return 0


def main() -> int:
    args = _parser().parse_args()
    if args.runtime_root is not None:
        return validate_runtime(args.runtime_root, args.expected_runtime_sha)
    return check_provenance()


if __name__ == "__main__":
    raise SystemExit(main())
