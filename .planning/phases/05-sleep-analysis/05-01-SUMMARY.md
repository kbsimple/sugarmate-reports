---
phase: 05-sleep-analysis
plan: "01"
subsystem: analytics
tags: [polars, pydantic, cgm, overnight-analysis, glucose-patterns]

requires:
  - phase: 04-behavioral-patterns
    provides: _build_df and _get_subset helper functions from behavioral_patterns.py

provides:
  - overnight_patterns.py module with OvernightAnalysisResult model
  - analyze_overnight_patterns() public API function
  - _get_overnight_df(), _compute_metrics(), _detect_excursions() helpers

affects: [05-sleep-analysis, cli-integration, web-results-display]

tech-stack:
  added: []
  patterns:
    - "Midnight-crossing window filter via night_date column offset"
    - "CV of daily means (cross-night variability) not intra-night CV"
    - "Run-length excursion detection with chronological night_mod sort"

key-files:
  created:
    - src/cgm_insights/analytics/overnight_patterns.py
  modified: []

key-decisions:
  - "CV computed as std-of-daily-overnight-means / mean * 100 (cross-night variability, not intra-night)"
  - "stability_score = max(0, 1 - cv/100) — wellness proxy, never labeled NGSI"
  - "night_date offsets post-midnight readings back to the evening start date for correct weekday classification"
  - "Excursions returned as night-level aggregate counts, not individual events, to avoid clinical alert framing"

patterns-established:
  - "OvernightAnalysisResult: Pydantic v2 frozen model, Optional fields default to None"
  - "analyze_overnight_patterns: never raises, returns insufficient_data=True on empty/sparse input"

requirements-completed: [SLEEP-01, SLEEP-02, SLEEP-03, SLEEP-04, SLEEP-05]

duration: 15min
completed: "2026-06-11"
---

# Phase 5 Plan 01: Core overnight patterns library module Summary

**Overnight glucose analysis module using 22:00–06:00 window with per-night CV stability scoring and sustained excursion detection via run-length encoding**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-11T00:00:00Z
- **Completed:** 2026-06-11T00:15:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Created `overnight_patterns.py` reusing `_build_df`/`_get_subset` from `behavioral_patterns.py` — no re-implementation
- Implemented cross-night CV stability scoring (CV of daily overnight means) and three-tier stability label
- Implemented run-length excursion detection with chronological night_mod sort for midnight-crossing windows
- All 221 existing tests pass with no regressions

## Task Commits

1. **Tasks 1+2: Module constants, OvernightAnalysisResult, all helper functions, public API** - `af09e2b` (feat)

## Files Created/Modified

- `src/cgm_insights/analytics/overnight_patterns.py` - Complete overnight analysis module with all five components

## Decisions Made

- CV computed as std-of-daily-overnight-means / overall-mean * 100 (cross-night variability); this matches how `_compute_all_buckets` computes CV in behavioral_patterns
- stability_score uses max(0, 1 - cv/100) clamp; labeled "Overnight Stability Score" in user-facing output, never "NGSI"
- night_date maps post-midnight readings back one day so weekday/weekend classification is based on the evening the overnight started, not the calendar morning
- Excursions aggregated to night-level counts (sustained_low_nights, sustained_high_nights) to avoid clinical alert framing
- _has_sustained_run() helper extracted as pure function for testability

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all verification assertions passed on first run. The existing test suite (221 tests) passed with 2 skipped and no failures.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Core overnight analysis library is complete and importable
- `analyze_overnight_patterns()` is ready for Plan 05-02 (CLI integration) and Plan 05-03 (web display)
- Plan 05-04 (tests) can test against the real implementation

---
*Phase: 05-sleep-analysis*
*Completed: 2026-06-11*
