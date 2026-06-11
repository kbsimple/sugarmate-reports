---
phase: 6
plan: "06-03"
subsystem: web
tags: [anomaly-detection, web-integration, jinja2, fastapi, session]
dependency_graph:
  requires: [06-02]
  provides: [anomaly-detection-web-layer]
  affects: [web-results-page, web-upload-pipeline]
tech_stack:
  added: []
  patterns: [four-point-web-integration, jinja2-component-include, session-dict-storage]
key_files:
  created:
    - src/web/templates/components/anomaly_detection.html
  modified:
    - src/web/services/session.py
    - src/web/routes/upload.py
    - src/web/routes/results.py
    - src/web/templates/results.html
decisions:
  - Mirrors the four-point overnight_patterns integration pattern exactly (session field, upload call, results extraction, template component)
  - Wellness disclaimer placed outside the insufficient_data guard so it always renders
  - severity label "significant" used in place of "severe" in user-facing badge text to avoid forbidden wellness terms
metrics:
  duration: "~5 minutes"
  completed: "2026-06-11"
  tasks_completed: 2
  files_changed: 5
---

# Phase 6 Plan 03: Web Integration Summary

**One-liner:** Anomaly detection wired into the FastAPI/Jinja2 web layer using the four-point session/upload/results/template pattern.

## What Was Built

Four-point web integration for anomaly detection following the identical pattern established by overnight_patterns in Phase 5:

1. **`session.py`** — Added `anomaly_detection: Optional[dict]` field to `SessionData` dataclass and matching `anomaly_detection` parameter to `SessionStore.store()`.

2. **`upload.py`** — Added `analyze_anomalies` import; calls `analyze_anomalies(readings)` after the overnight block and stores the serialized dict in the session via `anomaly_detection=anomaly_detection_dict`.

3. **`results.py`** — Added `AnomalyDetectionResult` and `generate_anomaly_suggestions` imports; extracts `session_data.anomaly_detection`, validates and merges suggestions, passes `anomaly_detection` to template context and `/data` JSON endpoint.

4. **`anomaly_detection.html`** — New DaisyUI card component with: file-level parameter docblock, insufficient-data guard, stats row (total/mild/moderate/significant), PISA filter note, weekly breakdown with severity badges (badge-error for significant, badge-warning for moderate, badge-info for mild), and always-visible wellness disclaimer.

5. **`results.html`** — Added `anomaly_detection` include block after overnight_patterns block, immediately before `<!-- Patterns and Suggestions -->`.

## Verification

All plan verification steps passed:
- `SessionData.__dataclass_fields__` contains `anomaly_detection` field
- `web.routes.upload` imports without errors
- `web.routes.results` imports without errors
- Jinja2 template renders correctly with `None` data (shows insufficient-data card + disclaimer)
- Jinja2 template renders correctly with `insufficient_data=True`
- 240 tests pass (0 new failures)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data flows from `analyze_anomalies()` through session storage to template rendering.

## Threat Flags

None — no new network endpoints added. The `/results/{session_id}/data` endpoint already existed and was extended with a new key.

## Self-Check: PASSED

- `/Users/ffaber/claude-projects/sugarmate-reports/src/web/templates/components/anomaly_detection.html` — FOUND
- `/Users/ffaber/claude-projects/sugarmate-reports/src/web/services/session.py` — FOUND (anomaly_detection field verified)
- `/Users/ffaber/claude-projects/sugarmate-reports/src/web/routes/upload.py` — FOUND (imports OK)
- `/Users/ffaber/claude-projects/sugarmate-reports/src/web/routes/results.py` — FOUND (imports OK)
- `/Users/ffaber/claude-projects/sugarmate-reports/src/web/templates/results.html` — FOUND (include block added)
- Commit `be62810` — FOUND
