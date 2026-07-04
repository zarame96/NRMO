#!/usr/bin/env python3
"""check_validation_status_consistency.py — VALIDATION_STATUS.md が
validation_results.json と一致し、かつ正式入口が実際に return code 0 で
完走することを検査する。

PIPE (capture_output) は使わない: 検証対象 entry の子・孫が stdout/stderr の
書き込み端を保持すると EOF 待ちで詰まる環境があるため、ログファイルへ redirect し
直接の子の終了 (wait) のみを待つ。timeout 時は process group ごと kill。
"""
import os, sys, json, signal, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "validate_nrmo_integrated_v72.py"
MARK = "ALL REQUIRED VALIDATIONS PASS WITH NO SKIPS"
jp = ROOT / "validation_results.json"
vs = ROOT / "VALIDATION_STATUS.md"


def run_entry(timeout=300):
    fd, log_path = tempfile.mkstemp(suffix=".log", prefix="nrmo_cc_")
    os.close(fd)
    with open(log_path, "w") as out:
        proc = subprocess.Popen([sys.executable, "-u", str(ENTRY)], cwd=str(ROOT),
                                stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True)
        try:
            proc.wait(timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                try: proc.kill()
                except Exception: pass
            try: proc.wait(timeout=5)
            except Exception: pass
            rc = None  # timeout
    try:
        text = Path(log_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = ""
    finally:
        try: os.unlink(log_path)
        except Exception: pass
    return rc, text


def main():
    print("[VALIDATION_STATUS CONSISTENCY]")
    # 1. 正式入口を実行し、終了まで見届けて return code 0 と final marker を確認
    rc, text = run_entry(timeout=300)
    if rc is None:
        print("FAIL: validate_nrmo_integrated_v72.py did not finish within 300s"); sys.exit(1)
    if rc != 0:
        print(f"FAIL: official entry returned rc={rc} (must be 0)"); print(text[-1500:]); sys.exit(1)
    if MARK not in text:
        print("FAIL: official entry did not print ALL REQUIRED ... NO SKIPS"); sys.exit(1)
    print("OK: official entry ran to completion with return code 0")

    # 2. json 全 PASS
    if not jp.exists():
        print("FAIL: validation_results.json not found"); sys.exit(1)
    data = json.loads(jp.read_text(encoding="utf-8"))
    all_pass = all(r["status"] == "PASS" for r in data)
    if not all_pass:
        print("FAIL: validation_results.json has non-PASS steps"); sys.exit(1)
    print("OK: validation_results.json all PASS")

    # 3. VALIDATION_STATUS.md が json と一致 (ALL PASS を主張)
    status_text = vs.read_text(encoding="utf-8") if vs.exists() else ""
    claims_pass = MARK in status_text
    if all_pass and claims_pass:
        print("OK: VALIDATION_STATUS.md consistent with json (ALL PASS)")
        sys.stdout.flush(); sys.exit(0)
    print(f"FAIL: mismatch (json all_pass={all_pass}, status_claims_pass={claims_pass})"); sys.exit(1)


if __name__ == "__main__":
    main()
