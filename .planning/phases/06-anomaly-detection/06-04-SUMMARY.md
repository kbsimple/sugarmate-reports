---
phase: 6
plan: "06-04"
subsystem: cli
tags: [cli, anomaly-detection, testing, wellness-language]
dependency_graph:
  requires: [06-01]
  provides: [anomaly-cli-flag, anomaly-test-suite]
  affects: [cli.py]
tech_stack:
  added: []
  patterns: [typer-option, rich-table, pytest-factory]
key_files:
  created:
    - tests/test_analytics/test_anomaly_detection.py
  modified:
    - src/cgm_insights/cli.py
    - src/cgm_insights/analytics/anomaly_detection.py
decisions:
  - "baselines.height==0 with sufficient days returns insufficient_data=False — uniform data has no variance but analysis ran"
metrics:
  duration_minutes: 5
  completed_date: "2026-06-11"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 6 Plan 04: CLI flag and test suite Summary

**One-liner:** `--anomaly/--no-anomaly` CLI flag wired through both commands with Rich table renderer and 9-test suite covering empty input, insufficient days, frozen models, PISA filtering, severity boundaries, and no-individual-readings guarantee.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add `_render_anomaly_detection()` and wire `--anomaly` flag | e5febf8 | src/cgm_insights/cli.py, src/cgm_insights/analytics/anomaly_detection.py |
| 2 | Write `tests/test_analytics/test_anomaly_detection.py` | e5febf8 | tests/test_analytics/test_anomaly_detection.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `insufficient_data=True` for uniform data with sufficient days**
- **Found during:** Task 2 (test execution)
- **Issue:** `analyze_anomalies()` returned `insufficient_data=True` when `baselines.height == 0` even though `days_analyzed >= MIN_DAYS_FOR_BASELINE`. This occurs with perfectly uniform glucose data (SD=0 for all buckets), which gets filtered by the `bucket_std > 0` guard. The plan spec required `insufficient_data=False` for 5 days of valid data.
- **Fix:** Changed the early-return branch when `baselines.height == 0` to return `insufficient_data=False` — no variance means no anomalies detectable, but the analysis did complete successfully.
- **Files modified:** `src/cgm_insights/analytics/anomaly_detection.py`
- **Commit:** e5febf8

## Verification

- 9/9 new tests pass
- 240 total tests pass (+ 2 skipped), 0 failures
- `--anomaly/--no-anomaly` flag confirmed in `analyze --help`
- No "alert", "alarm", "abnormal", or "dangerous" in any user-facing output

## Known Stubs

None.

## Threat Flags

None — no new network endpoints or auth paths introduced.

## Self-Check: PASSED

- `tests/test_analytics/test_anomaly_detection.py` — FOUND
- `src/cgm_insights/cli.py` — FOUND (modified)
- `src/cgm_insights/analytics/anomaly_detection.py` — FOUND (modified)
- Commit e5febf8 — FOUND
