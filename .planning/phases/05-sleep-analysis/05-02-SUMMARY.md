---
phase: 05-sleep-analysis
plan: "02"
subsystem: analytics
tags: [overnight-patterns, suggestions, public-api, python, polars]

# Dependency graph
requires:
  - phase: 05-01
    provides: analyze_overnight_patterns and OvernightAnalysisResult in overnight_patterns.py

provides:
  - analyze_overnight_patterns exported from cgm_insights.analytics and cgm_insights top-level
  - OvernightAnalysisResult exported from both public APIs
  - generate_overnight_suggestions() function in output/suggestions.py
  - Five overnight suggestion templates (stable, variable, low_excursions, high_excursions, weekday_weekend_diff)

affects: [05-03, 05-04, web-integration, cli-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Suggestion template pattern extended to overnight window — same Suggestion/SuggestionCategory datamodel as behavioral patterns"
    - "Export wiring: re-export from analytics/__init__ then cgm_insights/__init__ for two-level public API"

key-files:
  created: []
  modified:
    - src/cgm_insights/analytics/__init__.py
    - src/cgm_insights/__init__.py
    - src/cgm_insights/output/suggestions.py

key-decisions:
  - "Overnight suggestions threshold: >10 mg/dL weekday/weekend diff (matches behavioral_patterns threshold)"
  - "stability_label values Stable / Moderate variation / High variation drive template selection"
  - "excursion_summary dict keys sustained_low_nights and sustained_high_nights gate excursion suggestions"

patterns-established:
  - "Overnight suggestion selection: one stability + one low excursion + one high excursion + one weekday/weekend diff"

requirements-completed: [SLEEP-06]

# Metrics
duration: 5min
completed: 2026-06-11
---

# Phase 5 Plan 02: Public API wiring and overnight suggestion templates Summary

**Overnight patterns wired into both public APIs; generate_overnight_suggestions() added with five wellness-language templates covering stability, excursions, and weekday/weekend differences**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-11T22:00:00Z
- **Completed:** 2026-06-11T22:05:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `analyze_overnight_patterns` and `OvernightAnalysisResult` re-exported from `cgm_insights.analytics` and top-level `cgm_insights`
- Five overnight suggestion templates added to `SUGGESTION_TEMPLATES` dict
- `generate_overnight_suggestions()` implemented with stability/excursion/weekday-weekend logic
- All 221 existing tests pass with 0 regressions

## Task Commits

1. **Task 1 + Task 2: Wire exports and add suggestion templates** - `319d0ca` (feat)

## Files Created/Modified
- `src/cgm_insights/analytics/__init__.py` - Added overnight_patterns import block and __all__ entries
- `src/cgm_insights/__init__.py` - Added analyze_overnight_patterns and OvernightAnalysisResult to analytics import and __all__
- `src/cgm_insights/output/suggestions.py` - Added OvernightAnalysisResult import, five templates, generate_overnight_suggestions()

## Decisions Made
- Used `>10 mg/dL` as weekday/weekend diff threshold, matching the existing behavioral_patterns threshold in generate_behavioral_suggestions()
- stability_label string comparisons ("Stable", "Moderate variation", "High variation") match values defined in overnight_patterns.py from Plan 05-01
- Both tasks committed in a single atomic commit since they form one logical unit (export wiring + suggestion layer)

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None - smoke tests and full suite passed on first run.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 5 Plans 03 and 04 can proceed (web integration and CLI flag)
- `generate_overnight_suggestions()` is ready to be wired into the web report and CLI output

## Known Stubs
None - all templates are fully wired to OvernightAnalysisResult fields.

## Threat Flags
None - no new network endpoints or trust boundaries introduced.

---
*Phase: 05-sleep-analysis*
*Completed: 2026-06-11*

## Self-Check: PASSED
- `src/cgm_insights/analytics/__init__.py`: FOUND
- `src/cgm_insights/__init__.py`: FOUND
- `src/cgm_insights/output/suggestions.py`: FOUND
- Commit `319d0ca`: FOUND (verified by git log)
