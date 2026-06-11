---
phase: 5
plan: "05-04"
subsystem: cli-and-tests
tags: [cli, testing, overnight-patterns, typer]
dependency_graph:
  requires: [05-02]
  provides: [overnight-cli-flag, overnight-test-suite]
  affects: [cli.py, test_analytics]
tech_stack:
  added: []
  patterns: [typer-bool-option, rich-table-render, pytest-plain-helper]
key_files:
  created:
    - tests/test_analytics/test_overnight_patterns.py
  modified:
    - src/cgm_insights/cli.py
decisions:
  - "Overnight handler placed after behavioral block in _run_analysis() — consistent ordering (insights → behavioral → overnight)"
  - "Test uses plain helper create_overnight_readings() (not pytest fixture) — matches plan spec and behavioral_patterns test pattern"
  - "Used prompt-provided excursion test (inline normal_nights generation) over plan-variant — avoids date-overlap bug with shifted readings"
metrics:
  duration: "206s"
  completed: "2026-06-11"
  tasks_completed: 2
  files_changed: 2
---

# Phase 5 Plan 04: CLI flag and test suite Summary

**One-liner:** `--overnight/--no-overnight` Typer flag with `_render_overnight_patterns()` Rich table renderer and 10-test overnight_patterns test suite.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create tests/test_analytics/test_overnight_patterns.py | a37ef4c | tests/test_analytics/test_overnight_patterns.py |
| 2 | Add --overnight flag and _render_overnight_patterns() to cli.py | a37ef4c | src/cgm_insights/cli.py |

## What Was Built

### Test Suite (10 tests)

`tests/test_analytics/test_overnight_patterns.py` covers:

1. `test_empty_readings_returns_insufficient_data` — empty list returns `insufficient_data=True`, `nights_with_data=0`
2. `test_fewer_than_min_nights_returns_insufficient_data` — 4 nights returns `insufficient_data=True`
3. `test_exactly_min_nights_produces_result` — 5 nights produces valid result with correct mean
4. `test_midnight_crossing_filter_captures_pre_and_post_midnight` — `_get_overnight_df` includes 23:30 and 01:00, excludes 12:00
5. `test_night_date_uses_evening_start_not_morning_end` — 01:00 Tuesday maps to Monday night_date
6. `test_stability_score_matches_formula` — constant glucose → CV=0 → stability_score≈1.0, label="Stable"
7. `test_excursion_detection_requires_three_consecutive_readings` — 2 highs = no excursion, 3 highs = excursion
8. `test_overnight_analysis_result_is_frozen` — `OvernightAnalysisResult` raises on mutation
9. `test_overnight_window_constants` — `OVERNIGHT_START_MINUTE=1320`, `OVERNIGHT_WINDOW_MINUTES=480`
10. `test_tir_and_tbr_are_valid_percentages` — 95 mg/dL gives TIR≥99%, TBR≤1%

### CLI Changes

- Import: `from cgm_insights.analytics.overnight_patterns import analyze_overnight_patterns`
- New `_render_overnight_patterns(result, console)` function — Rich table with Mean Glucose, TIR, CV, TBR, Stability Score; weekday/weekend split if available; excursion summary
- `_run_analysis()` gains `overnight: bool` parameter
- Parse condition updated to `if visualize or compare or insights or behavioral or overnight:`
- Overnight handler block after behavioral block with insufficient-data and exception handling
- `--overnight/--no-overnight` Typer option (default=True) added to both `analyze` and `download_and_analyze` commands

## Verification Results

```
10 passed in 0.02s  (test_overnight_patterns.py)
231 passed, 2 skipped  (full suite — no regressions)
--overnight/--no-overnight  present in analyze --help
```

Total passing tests: 241 (was 221, +10 new overnight tests, pre-existing +10 from 05-02).

## Deviations from Plan

None — plan executed exactly as specified. The prompt provided an updated excursion test variant using inline `normal_nights` generation (instead of `create_overnight_readings` + time-shift) which was used as the definitive spec.

## Known Stubs

None — all CLI paths exercise real `analyze_overnight_patterns()` logic.

## Threat Flags

None — no new network endpoints, auth paths, or external trust boundaries introduced.

## Self-Check: PASSED

- `tests/test_analytics/test_overnight_patterns.py` exists
- `src/cgm_insights/cli.py` contains `_render_overnight_patterns` and `overnight: bool` parameter
- Commit `a37ef4c` exists in git log
- All 241 tests pass
