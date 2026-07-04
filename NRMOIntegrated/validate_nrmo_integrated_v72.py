#!/usr/bin/env python3
"""
validate_nrmo_integrated_v72.py — NRMO Integrated v7.2 FULL 正式検証入口 (package root)。

設計 (10/10 引き継ぎ書 P0-1/P0-3 準拠):
  - 各 step を subprocess + per-step timeout で隔離実行 (状態持ち越しなし)
  - validation_results.json を生成
  - 厳密表示: FAIL/TIMEOUT があれば FINAL: FAIL,
              required SKIP があれば FINAL: FAIL,
              optional SKIP のみなら PARTIAL PASS,
              全 required PASS なら ALL REQUIRED VALIDATIONS PASS WITH NO SKIPS
  - 追加パス設定なし・外部依存なし・5 分以内・終了コード 0/1

正式入口は軽量・決定的・短時間。長期 rollout は run_long_validations.py に分離。
"""
from __future__ import annotations
from pathlib import Path
import subprocess, sys, json, time, os, signal, tempfile

ROOT = Path(__file__).resolve().parent
PHASE1 = ROOT / "code" / "python" / "nrmo_v72_phase1"
CORE = PHASE1 / "core"

def _rel(c):
    """cmd 引数が ROOT 配下の絶対パスなら相対表記にする (生成物のパスを clean に)。"""
    s = str(c)
    try:
        rs = str(ROOT)
        if s.startswith(rs + os.sep):
            return os.path.relpath(s, rs)
    except Exception:
        pass
    return s

# subprocess が import を解決できるよう PYTHONPATH を補強 (絶対パスは __file__ 由来のみ)
ENV = dict(os.environ)
ENV["PYTHONPATH"] = os.pathsep.join(
    [str(CORE), str(PHASE1), str(PHASE1 / "v7_maxforward"), ENV.get("PYTHONPATH", "")])

VALIDATION_STEPS = [
    {"name": "OS/SOP validation",
     "cmd": [sys.executable, str(PHASE1 / "run_os_validations.py")],
     "timeout": 120, "required": True,
     "pass_markers": ["ALL PASS WITH NO SKIPS"]},
    {"name": "OS/SOP boundary+property",
     "cmd": [sys.executable, str(PHASE1 / "validation" / "test_os_boundary_properties.py")],
     "timeout": 120, "required": True, "pass_markers": ["ALL BOUNDARY/PROPERTY PASS"]},
    {"name": "v8 integrity",
     "cmd": [sys.executable, str(PHASE1 / "validation" / "test_v8_integrity.py")],
     "timeout": 120, "required": True, "pass_markers": []},
    {"name": "Omega subsystem alive",
     "cmd": [sys.executable, str(PHASE1 / "v7_maxforward" / "validate_part_a_subprocess.py")],
     "timeout": 180, "required": True, "pass_markers": ["ALL SUBSYSTEMS ALIVE"]},
    {"name": "NRMO separation contract",
     "cmd": [sys.executable, str(PHASE1 / "v7_maxforward" / "validate_part_b_subprocess.py")],
     "timeout": 180, "required": True, "pass_markers": ["ALL PASS"]},
    {"name": "domain harness (self-contained, light)",
     "cmd": [sys.executable, str(PHASE1 / "validation" / "test_domain_harness.py")],
     "timeout": 120, "required": True, "pass_markers": ["domain_harness OK"]},
    {"name": "C++ syntax",
     "cmd": ["bash", str(ROOT / "scripts" / "validate_cpp.sh")],
     "timeout": 120, "required": True, "pass_markers": ["C++ syntax OK"]},
    {"name": "no-pipe audit (active runners)",
     "cmd": [sys.executable, str(ROOT / "tools" / "check_no_pipe_capture.py")],
     "timeout": 60, "required": True,
     "pass_markers": ["no PIPE/capture in active validation runners"]},
]


def hard_exit(code):
    """stdout/stderr を flush して os._exit で確実に終了する。
    子プロセスや非daemonスレッド・スレッドプールが interpreter を生かし続けても
    プロセスを return code 付きで即時終了させる (10/10 P0)。"""
    try: sys.stdout.flush()
    except Exception: pass
    try: sys.stderr.flush()
    except Exception: pass
    os._exit(code)


def _kill_group(proc):
    """子を process group ごと kill (start_new_session=True 前提)。"""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try: proc.kill()
        except Exception: pass


def run_step(step):
    """各 validation step を実行する。
    PIPE (capture) は使わない: step の子・孫プロセスが stdout/stderr の書き込み端を
    保持すると communicate() が EOF 待ちで詰まるため、一時ログファイルへ redirect し、
    直接の子の終了 (wait) のみを待つ。timeout / 正常終了どちらでも最後に process group
    を掃除し、孫プロセスの残留を潰す。"""
    start = time.time()
    fd, log_path = tempfile.mkstemp(prefix="nrmo_step_", suffix=".log")
    os.close(fd)
    pgid = None
    try:
        with open(log_path, "w", encoding="utf-8", errors="ignore") as out:
            proc = subprocess.Popen(step["cmd"], cwd=str(ROOT), env=ENV, text=True,
                                    stdout=out, stderr=subprocess.STDOUT,
                                    start_new_session=True)
            try:
                pgid = os.getpgid(proc.pid)
            except Exception:
                pgid = proc.pid
            try:
                proc.wait(timeout=step["timeout"])
                rc = proc.returncode
                status_timeout = False
            except subprocess.TimeoutExpired:
                status_timeout = True
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    try: proc.kill()
                    except Exception: pass
                try: proc.wait(timeout=5)
                except Exception: pass
                rc = -1

        text = Path(log_path).read_text(encoding="utf-8", errors="ignore")

        # 正常終了でも孫プロセス残留対策として process group を掃除
        if not status_timeout and pgid is not None:
            try:
                os.killpg(pgid, signal.SIGTERM)
            except Exception:
                pass

        elapsed = time.time() - start
        if status_timeout:
            status = "TIMEOUT"
        else:
            markers_ok = all(m in text for m in step.get("pass_markers", []))
            status = "PASS" if (rc == 0 and markers_ok) else "FAIL"
        return {"name": step["name"], "cmd": [_rel(c) for c in step["cmd"]],
                "required": step["required"], "returncode": rc,
                "elapsed": round(elapsed, 2), "status": status,
                "stdout": text[-5000:], "stderr": "TIMEOUT" if status_timeout else ""}
    finally:
        try: os.unlink(log_path)
        except Exception: pass


def main():
    t0 = time.time()
    results = [run_step(s) for s in VALIDATION_STEPS]
    (ROOT / "validation_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print("NRMO Integrated v7.2 FULL Validation")
    print("=" * 60)
    for r in results:
        req = "required" if r["required"] else "optional"
        print(f"{r['status']}: {r['name']} ({r['elapsed']:.2f}s, {req})")
    print("-" * 60)

    has_fail = any(r["status"] == "FAIL" for r in results)
    has_timeout = any(r["status"] == "TIMEOUT" for r in results)
    req_skip = any(r["status"] == "SKIP" and r["required"] for r in results)
    opt_skip = any(r["status"] == "SKIP" and not r["required"] for r in results)

    if has_fail or has_timeout or req_skip:
        print("FINAL: FAIL")
        print(f"  total {time.time()-t0:.1f}s, results → validation_results.json")
        hard_exit(1)
    if opt_skip:
        print("FINAL: PARTIAL PASS / OPTIONAL SKIPS PRESENT")
        print(f"  total {time.time()-t0:.1f}s, results → validation_results.json")
        hard_exit(0)
    print("FINAL: ALL REQUIRED VALIDATIONS PASS WITH NO SKIPS")
    print(f"  total {time.time()-t0:.1f}s, results → validation_results.json")
    hard_exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        hard_exit(int(e.code) if isinstance(e.code, int) else 0)
    except Exception as exc:
        print(f"FINAL: FAIL (entry exception: {exc})")
        hard_exit(1)
