#!/usr/bin/env python3
"""validate_three_runs.py — 公式「3 連続検証」証跡。

設計:
- PIPE 不使用 (entry の子・孫が pipe を保持しても EOF 待ちで詰まらないよう、stdout は
  一時ログファイルへ redirect。直接の子の wait(timeout) のみ待つ)。
- 1 回あたり timeout=300s (entry 内 step timeout 最大 180s + cleanup 余裕)。
  外側 timeout を内側 step より長くし、timeout 階層の逆転を防ぐ。
- 各 run の前後で ps ベースの孤児 validation プロセス cleanup を実行
  (entry の step 子は start_new_session=True で別 process group のため、
   entry を kill しても残り得る。これを cmdline マーカで掃除する)。
- validation_three_runs.json に cleanup_before_count / cleanup_after_count を記録。
"""
import os, sys, json, time, signal, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "validate_nrmo_integrated_v72.py"
MARK = "ALL REQUIRED VALIDATIONS PASS WITH NO SKIPS"
PER_RUN_TIMEOUT = 300

_MARKERS = [
    "validate_nrmo_integrated_v72.py", "nrmo_separation_realcheck.py",
    "validate_part_a_subprocess.py", "validate_part_b_subprocess.py",
    "test_domain_harness.py", "run_os_validations.py",
    "test_os_boundary_properties.py", "test_v8_integrity.py",
]


def _ps_lines():
    """ps 出力を一時ファイル経由で取得 (PIPE 不使用)。"""
    fd, p = tempfile.mkstemp(prefix="nrmo_ps_", suffix=".txt")
    os.close(fd)
    try:
        with open(p, "w") as out:
            subprocess.run(["ps", "-eo", "pid,pgid,cmd"], stdout=out,
                           stderr=subprocess.DEVNULL, timeout=10)
        return Path(p).read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    finally:
        try: os.unlink(p)
        except Exception: pass


def _list_orphans():
    self_pid = os.getpid()
    root_s = str(ROOT)
    pids = []
    for line in _ps_lines()[1:]:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmd = parts[2]
        if pid == self_pid:
            continue
        if "python" not in cmd:
            continue
        if "validate_three_runs.py" in cmd:   # 自分自身は除外
            continue
        if root_s in cmd and any(m in cmd for m in _MARKERS):
            pids.append(pid)
    return pids


def cleanup_orphan_validation_processes():
    """残留 validation プロセスを SIGTERM → 1s → SIGKILL で掃除。kill 件数を返す。"""
    pids = _list_orphans()
    for pid in pids:
        try: os.kill(pid, signal.SIGTERM)
        except Exception: pass
    if pids:
        time.sleep(1)
        for pid in _list_orphans():
            try: os.kill(pid, signal.SIGKILL)
            except Exception: pass
    return len(pids)


def run_once(timeout=PER_RUN_TIMEOUT):
    fd, log_path = tempfile.mkstemp(prefix="nrmo_run_", suffix=".log")
    os.close(fd)
    t = time.time()
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
            rc = -1
    elapsed = round(time.time() - t, 2)
    try:
        text = Path(log_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = ""
    finally:
        try: os.unlink(log_path)
        except Exception: pass
    return rc, elapsed, (MARK in text)


def main():
    runs = []; all_ok = True
    for i in range(1, 4):
        before = cleanup_orphan_validation_processes()   # run 前掃除
        rc, elapsed, marker = run_once()
        after = cleanup_orphan_validation_processes()     # run 後掃除 (孤児step子を潰す)
        ok = (rc == 0 and marker)
        all_ok = all_ok and ok
        runs.append({"run": i, "returncode": rc, "elapsed": elapsed,
                     "final_marker": marker,
                     "cleanup_before_count": before, "cleanup_after_count": after,
                     "status": "PASS" if ok else "FAIL"})
        print(f"run {i}: rc={rc} elapsed={elapsed}s marker={marker} "
              f"cleanup(before={before},after={after}) -> {'PASS' if ok else 'FAIL'}")
    (ROOT / "validation_three_runs.json").write_text(
        json.dumps({"all_pass": all_ok, "timeout_per_run_s": PER_RUN_TIMEOUT, "runs": runs},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    print("-" * 50)
    print("THREE RUNS: ALL PASS" if all_ok else "THREE RUNS: FAIL")
    sys.stdout.flush(); sys.stderr.flush()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
