---
phase: 6
plan: "06-02"
subsystem: analytics/output
tags: [anomaly-detection, public-api, suggestions, wellness-language]
dependency_graph:
  requires: [06-01]
  provides: [analyze_anomalies public export, AnomalyDetectionResult public export, generate_anomaly_suggestions]
  affects: [cgm_insights.__init__, cgm_insights.analytics.__init__, cgm_insights.output.suggestions]
tech_stack:
  added: []
  patterns: [suggestion template pattern, severity-tiered suggestion selection]
key_files:
  modified:
    - src/cgm_insights/analytics/__init__.py
    - src/cgm_insights/__init__.py
    - src/cgm_insights/output/suggestions.py
decisions:
  - "generate_anomaly_suggestions includes pattern_reference='Anomaly detection summary' per Suggestion model requirement (field is required)"
  - "At-most-one-suggestion design: only highest severity tier surfaces to avoid suggestion flood"
metrics:
  duration: "~5 minutes"
  completed: "2026-06-11T21:20:32Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 6 Plan 02: Public API wiring and anomaly suggestion templates Summary

## One-liner

Wired `analyze_anomalies` / `AnomalyDetectionResult` into all public export surfaces and added three severity-tiered wellness-language suggestion templates with `generate_anomaly_suggestions()` that returns at most one suggestion per result.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Wire exports in analytics/__init__.py and cgm_insights/__init__.py | 8dfa4e0 |
| 2 | Add anomaly suggestion templates and generate_anomaly_suggestions() | 8dfa4e0 |

## Decisions Made

1. **`pattern_reference` field included** — The `Suggestion` pydantic model declares `pattern_reference` as a required field (no default). Used `"Anomaly detection summary"` as the fixed string since anomaly suggestions are aggregate (not tied to a specific named pattern).

2. **At-most-one suggestion** — Only the highest-severity tier (severe > moderate > mild) produces a suggestion. This avoids flooding the user with redundant suggestions when anomalies span multiple severity levels.

## Deviations from Plan

None — plan executed exactly as written, with one note: `pattern_reference` was anticipated by the plan's NOTE directive and handled correctly.

## Known Stubs

None.

## Threat Flags

None. This plan only adds export wiring and suggestion generation; no new network endpoints or trust-boundary changes introduced.

## Self-Check: PASSED

- `src/cgm_insights/analytics/__init__.py` — modified, exports verified
- `src/cgm_insights/__init__.py` — modified, exports verified
- `src/cgm_insights/output/suggestions.py` — modified, function verified
- Commit 8dfa4e0 — exists in git log
- 231 tests passed, 0 failures
