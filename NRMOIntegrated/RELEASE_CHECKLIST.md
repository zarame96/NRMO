# Release Checklist — NRMO Integrated v7.2 FULL

- [x] validate_nrmo_integrated_v72.py passes (FINAL: ALL REQUIRED VALIDATIONS PASS WITH NO SKIPS)
- [x] official entry exits with **return code 0** (hard_exit via os._exit; verified by `timeout 60s python -u validate_nrmo_integrated_v72.py`)
- [x] validation_results.json attached and all PASS (cmd paths recorded ROOT-relative)
- [x] distribution zip cleaned of __pycache__ and *.pyc
- [x] no PIPE/capture in active validation runners (entry run_step + wrappers use file-redirect; verified by tools/check_no_pipe_capture.py)
- [x] correct timeout hierarchy (outer 3-run timeout 300s > inner step timeouts <=180s) + ps-based orphan cleanup before/after each run
- [x] heavy real nrmo_core adapter moved to run_long_validations.py to keep the entry lightweight/stable
- [x] no SKIP in required validations
- [x] no TIMEOUT (per-step Popen + start_new_session; timeout kills the process group)
- [x] no hardcoded local paths (home-dir / temp-dir absolute paths) in active code/docs, excluding archive
- [x] README matches validation output
- [x] VALIDATION_STATUS updated and consistent with validation_results.json
- [x] check_validation_status_consistency.py runs the official entry to completion and asserts rc 0
- [x] v7.1 moved to archive/v7_1
- [x] PDF version matches package version (v7.2)
- [x] no false empirical claims (terminology_audit passes)
- [x] decision_trace output available (NRMOOSIntegrator.write_trace)
- [x] 3 consecutive runs succeed via `python scripts/validate_three_runs.py` (rc 0, each <60s, FINAL marker present; evidence: validation_three_runs.json)
