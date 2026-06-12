---
phase: 08-tod-chart-patterns-ux
plan: "03"
subsystem: web-frontend
tags: [jinja2, daisyui, behavioral-patterns, cgm, out-of-range-insights]
dependency_graph:
  requires:
    - "08-01"
    - "08-02"
  provides:
    - out-of-range-priority-insights-component
    - time-windows-to-focus-on
  affects:
    - src/web/templates/results.html
    - src/web/templates/components/out_of_range_insights.html
tech_stack:
  added: []
  patterns:
    - "Jinja2 list.append pattern for multi-pass filtering: set has_above=[] / set _=has_above.append(1)"
    - "DaisyUI alert-warning for Above Range, alert-error for Below Range"
    - "Guard-then-render: detect presence of out-of-range patterns before rendering outer card"
key_files:
  created:
    - src/web/templates/components/out_of_range_insights.html
  modified:
    - src/web/templates/results.html
decisions:
  - "Use two-pass loop (first detect has_above/has_below, then render) to avoid empty outer card wrapper"
  - "60-min hourly-boundary filter (bucket_start_minute % 60 == 0) matches behavioral_patterns.html density filter pattern from Plan 02"
  - "Render nothing (no empty state) when no out-of-range patterns — cleaner UX than showing an empty card"
metrics:
  duration: "~10 minutes"
  completed: "2026-06-12"
  tasks_completed: 2
  files_modified: 1
  files_created: 1
---

# Phase 8 Plan 03: Out-of-Range Priority Insights Component Summary

**One-liner:** Created out_of_range_insights.html showing hourly time windows consistently outside 70-180 mg/dL, with weekday/weekend split, wired into results.html above behavioral_patterns tabs.

## What Was Done

Two tasks:
1. Created `src/web/templates/components/out_of_range_insights.html` — new DaisyUI card component that surfaces 60-min hourly-boundary patterns outside 70-180 mg/dL range as above/below range alert rows with WD/WE split.
2. Edited `src/web/templates/results.html` — inserted the out_of_range_insights include block (with `{% with behavioral_patterns=behavioral_patterns %}` pattern) immediately above the existing behavioral_patterns include block.

## Tasks

| # | Name | Commit | Files Changed |
|---|------|--------|---------------|
| 1 | Create out_of_range_insights.html component | 07b500d | src/web/templates/components/out_of_range_insights.html (created) |
| 2 | Wire out_of_range_insights include into results.html above behavioral_patterns | 2eb7c1c | src/web/templates/results.html |

## Deviations from Plan

None - plan executed exactly as written.

## Acceptance Criteria Verification

- `test -f src/web/templates/components/out_of_range_insights.html` exits 0: PASSED
- `grep "Time Windows to Focus On"` matches: PASSED
- `grep "These time windows consistently show glucose outside"` matches: PASSED
- `grep "alert alert-warning"` matches: PASSED
- `grep "alert alert-error"` matches: PASSED
- `grep "weekday_avg_glucose is not none"` matches: PASSED (2 occurrences)
- `grep "bucket_start_minute % 60 == 0"` matches: PASSED (2 occurrences)
- `grep "selectattr.*window_size_min.*equalto.*60"` matches: PASSED
- `grep -c "<details"` returns 0: PASSED (no accordion)
- `grep "Wellness Information Only"` matches: PASSED
- `grep -c "out_of_range_insights.html" results.html` returns 1: PASSED
- out_of_range_insights line (104) < behavioral_patterns.html line (111): PASSED
- `grep "const patterns = {{ patterns | tojson }};"` exits 0: PASSED (Plan 01 intact)
- `python3 -m pytest tests/web/test_results.py -v` — 19 passed: PASSED
- `python3 -m pytest --tb=short -q` — 235 passed, 18 skipped, 0 FAILED: PASSED

## Phase 8 Success Criteria Status

1. Time-of-Day chart renders data (Plan 01) — COMPLETE
2. Behavioral patterns shows range status inline, no accordion (Plan 02) — COMPLETE
3. Variability + range status visible simultaneously (Plan 02) — COMPLETE
4. Out-of-range windows surfaced as priority insights with WD/WE segmentation (Plan 03) — COMPLETE
5. Each insight shows time window, avg value, WD/WE split (Plan 03) — COMPLETE
6. Wellness language throughout; no medical advice (all plans) — COMPLETE

## Known Stubs

None. The component renders dynamically from `behavioral_patterns.patterns` data — no hardcoded or placeholder values. If behavioral_patterns is None or insufficient_data, the component renders nothing (by design, not a stub).

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The component renders the same behavioral_patterns session data already visible in the behavioral_patterns tabs and /data JSON endpoint. Trust boundaries unchanged from T-08-03-01 through T-08-03-03 (all accepted in threat model).

## Self-Check: PASSED

- File exists: src/web/templates/components/out_of_range_insights.html — FOUND
- File exists: src/web/templates/results.html (modified) — FOUND
- Commit 07b500d exists: FOUND
- Commit 2eb7c1c exists: FOUND
- out_of_range_insights at line 104, behavioral_patterns.html at line 111 — ORDER CORRECT
- All 235 tests pass: CONFIRMED
