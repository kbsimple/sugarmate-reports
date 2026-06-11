---
phase: "04"
plan: "04-03"
subsystem: web-layer
tags: [behavioral-patterns, web, jinja2, daisyui, session]
dependency_graph:
  requires:
    - "04-01: BehavioralAnalysisResult and analyze_behavioral_patterns() in library"
    - "04-02: behavioral pattern CLI integration (confirms library API stable)"
  provides:
    - "SessionData.behavioral_patterns field for session storage"
    - "behavioral_patterns wired through upload → session → results → template"
    - "behavioral_patterns.html DaisyUI tab component (30/60/120 min)"
  affects:
    - "src/web/services/session.py: SessionData dataclass, SessionStore.store()"
    - "src/web/routes/upload.py: upload pipeline extended"
    - "src/web/routes/results.py: template context extended"
    - "src/web/templates/results.html: new include inserted"
tech_stack:
  added: []
  patterns:
    - "DaisyUI CSS-only radio tabs (no JavaScript) for multi-window display"
    - "HTML <details>/<summary> for expandable CV score without JS"
    - "Jinja2 selectattr filter for filtering patterns by window_size_min"
key_files:
  created:
    - "src/web/templates/components/behavioral_patterns.html"
  modified:
    - "src/web/services/session.py"
    - "src/web/routes/upload.py"
    - "src/web/routes/results.py"
    - "src/web/templates/results.html"
decisions:
  - "model_dump() serialization: BehavioralAnalysisResult stored as plain dict in session to pass through existing dict-based session storage cleanly"
  - "Template receives raw dict (not typed object): Jinja2 accesses dict keys as attributes; autoescaping covers all values"
  - "Jinja2 selectattr('window_size_min', 'equalto', window_min) used to partition patterns per tab — avoids nested data structure in session dict"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-11"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 4
  commits: 2
requirements:
  - BHVR-01
  - BHVR-02
  - BHVR-03
  - BHVR-04
  - BHVR-05
  - BHVR-06
---

# Phase 4 Plan 03: Web Layer Integration — Behavioral Patterns Summary

**One-liner:** Three-tab DaisyUI behavioral patterns section wired end-to-end from upload pipeline through Jinja2 template with CSS-only tabs, expandable CV scores, and wellness-framed Pattern Insights.

---

## What Was Built

Plan 04-03 connected the behavioral pattern analysis library (built in 04-01) to the web dashboard. Users now see a "Behavioral Patterns" section immediately after uploading CGM data.

### Data Flow

```
upload_file() → analyze_behavioral_patterns(readings)
             → behavioral_result.model_dump()
             → session_store.store(..., behavioral_patterns=dict)
             → GET /results/{session_id}
             → session_data.behavioral_patterns  (dict or None)
             → TemplateResponse context
             → behavioral_patterns.html
             → DaisyUI radio tabs (30/60/120 min)
```

### Task 1: SessionData and Upload Pipeline

- Added `behavioral_patterns: Optional[dict] = field(default=None)` to `SessionData` dataclass
- Updated `SessionStore.store()` signature to accept `behavioral_patterns: Optional[dict] = None`
- Added `from cgm_insights.analytics.behavioral_patterns import analyze_behavioral_patterns` import in `upload.py`
- Called `analyze_behavioral_patterns(readings)` after existing pattern detection, stored `model_dump()` in session

### Task 2: Results Route and Template Component

- Updated `results.py` to extract `session_data.behavioral_patterns` and pass as `behavioral_patterns` to template context
- Created `src/web/templates/components/behavioral_patterns.html` with:
  - DaisyUI `tabs tabs-bordered` radio tab component (30/60/120 min, CSS-only, no JavaScript)
  - Per-bucket rows: time label, Consistent (badge-success) / Moderate (badge-ghost) / Variable (badge-warning) badge, avg mg/dL
  - Native HTML `<details>`/`<summary>` for expandable CV score ("Show score")
  - Optional weekday/weekend avg row inside details when both have sufficient data
  - Insufficient data state: `alert alert-info` card with exact UI-SPEC copy
  - Pattern Insights sub-section (shown only when Consistent or Variable periods exist, capped at 6)
  - Wellness disclaimer block always shown
- Inserted `{% include 'components/behavioral_patterns.html' %}` in `results.html` before `patterns_list.html` (lines 115–120)

---

## Verification Results

All acceptance criteria met:

- `SessionData.behavioral_patterns` field exists with `default=None`
- `SessionStore.store()` accepts `behavioral_patterns` parameter
- `upload.py` calls `analyze_behavioral_patterns(readings)` and passes `model_dump()` to store
- `results.py` extracts `behavioral_patterns_data` from session and includes in TemplateResponse
- `behavioral_patterns.html` contains `tabs tabs-bordered`, `name="behavioral_tabs"`, badge-success/warning/ghost, `<details class="mt-1">` with Show score, `insufficient_data` condition, "Not enough data" heading, "Wellness Information Only" disclaimer
- `results.html` includes `behavioral_patterns.html` at line 118 (before `patterns_list.html` at line 125)
- All 210 Python tests pass (0 failures, 2 skipped)

---

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 6085e63 | feat | Extend SessionData and upload pipeline for behavioral patterns |
| 32cc658 | feat | Add behavioral patterns template component and wire into results route |

---

## Deviations from Plan

None — plan executed exactly as written.

The UI-SPEC copywriting contract was consulted to confirm exact copy. The action text in Pattern Insights cards uses the plan's specified copy which aligns with UI-SPEC intent.

---

## Threat Surface Scan

No new security-relevant surfaces beyond what the plan's threat model documented:

- `T-04-05`: Jinja2 autoescaping covers all `behavioral_patterns_data` values (numeric floats/ints, enum strings). No user-supplied free text flows through this path.
- `T-04-06`: Session IDs remain UUID v4; behavioral pattern data is glucose timing patterns, not credentials.

No new network endpoints, auth paths, or trust boundary changes introduced.

---

## Known Stubs

None. All data flowing to the template comes from the live `analyze_behavioral_patterns()` call on actual uploaded readings. The insufficient data card is a valid state handler, not a stub.

---

## Self-Check: PASSED

- `src/web/templates/components/behavioral_patterns.html` — FOUND
- `src/web/services/session.py` has `behavioral_patterns` field — VERIFIED (Python assert passed)
- `src/web/routes/results.py` passes `behavioral_patterns` to template — VERIFIED
- `src/web/templates/results.html` includes behavioral_patterns.html before patterns_list.html — VERIFIED (pos 4815 < 5032)
- Commits 6085e63 and 32cc658 — FOUND in git log
- 210 tests pass — VERIFIED
