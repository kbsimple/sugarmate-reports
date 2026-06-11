---
phase: 5
plan: "05-03"
subsystem: web
tags: [overnight-patterns, web-integration, jinja2, session, upload, results]
dependency_graph:
  requires: [05-02]
  provides: [overnight-patterns-ui]
  affects: [results-page, session-store, upload-flow]
tech_stack:
  added: []
  patterns: [session-dict-passthrough, jinja2-component-include, pydantic-model-validate]
key_files:
  created:
    - src/web/templates/components/overnight_patterns.html
  modified:
    - src/web/services/session.py
    - src/web/routes/upload.py
    - src/web/routes/results.py
    - src/web/templates/results.html
decisions:
  - Wellness disclaimer uses "Actual overnight timing varies" (not "sleep timing") to comply with no-sleep-word constraint
  - overnight_patterns_dict stored as-is (model_dump()) matching behavioral_patterns pattern
  - Suggestions sorted by priority after merging overnight into existing suggestions list
metrics:
  duration: "~10 minutes"
  completed: "2026-06-11"
  tasks_completed: 3
  files_modified: 5
---

# Phase 5 Plan 03: Web integration — session, upload, results, and overnight_patterns.html component Summary

Wired overnight glucose analysis end-to-end through the web layer: `SessionData` stores the dict, `upload.py` computes it and passes it to `session_store.store()`, `results.py` reconstructs `OvernightAnalysisResult`, generates overnight suggestions, and passes `overnight_patterns_data` to the template, and `overnight_patterns.html` renders the full metrics card.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Update session.py and upload.py | 4891e09 | session.py, upload.py |
| 2 | Update results.py and results.html | 4891e09 | results.py, results.html |
| 3 | Create overnight_patterns.html component | 4891e09 | components/overnight_patterns.html |

## What Was Built

- `SessionData.overnight_patterns: Optional[dict]` field added
- `SessionStore.store()` accepts and stores `overnight_patterns` kwarg
- `upload.py` calls `analyze_overnight_patterns(readings)` after behavioral analysis and passes `overnight_patterns_dict` to `session_store.store()`
- `results.py` imports `OvernightAnalysisResult` and `generate_overnight_suggestions`, extracts `overnight_patterns_data` from session, generates overnight suggestions (merged + sorted by priority), passes `overnight_patterns` to template context and `/data` JSON endpoint
- `results.html` includes `overnight_patterns.html` after the behavioral patterns block
- `overnight_patterns.html` component renders: insufficient-data alert, metrics row (mean glucose / TIR / CV / TBR), stability score progress bar with color-coded label, weekday vs weekend comparison, excursion summary, wellness disclaimer

## Deviations from Plan

None — plan executed exactly as written. One proactive constraint applied:

**[CLAUDE.md constraint] Wellness disclaimer wording:** The plan body used "Actual sleep timing varies" but the hard constraint forbids the word "sleep" in all user-facing text. The disclaimer was written as "Actual overnight timing varies" per the user prompt's corrected version.

## Known Stubs

None. All data flows from `OvernightAnalysisResult.model_dump()` through session to template.

## Threat Flags

None. No new network endpoints or auth paths introduced; this is a template/session data passthrough.

## Self-Check: PASSED

- `src/web/templates/components/overnight_patterns.html` — FOUND
- `4891e09` commit — verified via `git log`
- All 231 tests pass (0 failures, 2 skipped)
- Template renders without "sleep" or "NGSI" — verified
