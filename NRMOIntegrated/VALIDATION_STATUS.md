# VALIDATION_STATUS — NRMO Integrated v7.2 FULL

Last validated: 2026-06-01
Command: `python validate_nrmo_integrated_v72.py` (run from package root)
Environment: Python 3.11+, numpy, g++ (C++17). No external paths/bundles/network.
Entry wall-clock (sum of steps): 9.0s (lightweight; heavy checks are in run_long_validations.py)

Required validations (official entry):
- PASS: OS/SOP validation (0.06s)
- PASS: OS/SOP boundary+property (0.06s)
- PASS: v8 integrity (1.02s)
- PASS: Omega subsystem alive (0.27s)
- PASS: NRMO separation contract (6.38s)
- PASS: domain harness (self-contained, light) (0.31s)
- PASS: C++ syntax (0.57s)
- PASS: no-pipe audit (active runners) (0.03s)

Optional validations:
- (none)

Skipped validations: (none)
Timeouts: (none)

Final result:
ALL REQUIRED VALIDATIONS PASS WITH NO SKIPS

Moved to long validation (run_long_validations.py, heavy/optional):
- real nrmo_core adapter (bundled v52_codebase) — 入口の軽量・短時間性と 3 連続安定性のため移動。
- run_all_validations (full) / v7_validate 3-domain (full)。

3 consecutive runs (scripts/validate_three_runs.py; timeout 300s each; ps-based orphan cleanup before/after):
- run 1: rc=0, 8.84s, final_marker=true, cleanup(before=0,after=0) -> PASS
- run 2: rc=0, 8.75s, final_marker=true, cleanup(before=0,after=0) -> PASS
- run 3: rc=0, 8.74s, final_marker=true, cleanup(before=0,after=0) -> PASS
- summary: ALL PASS (evidence: validation_three_runs.json)

Subprocess discipline (deadlock-free):
- 入口 run_step / validate_three_runs / check_validation_status_consistency は PIPE 不使用 (一時ログ redirect + wait(timeout) + process group kill)。
- 外側 runner timeout(300s) > 内側 step timeout(<=180s) で timeout 階層の逆転を排除。
- validate_three_runs は ps ベースで孤児 validation プロセスを各 run 前後に掃除 (SIGTERM→SIGKILL)。
- tools/check_no_pipe_capture.py が active runner の PIPE/capture 不使用を検査 (入口の必須 step)。

Notes:
- store/investment/romance harness は **proxy dynamics**。Type ZERO / Passive Pattern は **operational proxy adapters**。