# CGM Insights

## What This Is

A web application for CGM (Continuous Glucose Monitor) users to upload their Sugarmate data exports and receive a focused, actionable glucose report. The app analyzes time-in-range, glucose variability, daily patterns, overnight patterns, and time windows that consistently fall outside range — segmented by weekday and weekend. Built on a reusable Python analysis engine (also usable as a library or CLI) with a FastAPI + HTMX web frontend.

## Core Value

Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

## Current State: All v3.0 Milestones Archived (2026-06-13)

All three milestones (v1.0, v2.0, v3.0) have been completed and archived. The project is in a clean, stable state ready for the next milestone.

**What shipped:**
- v1.0 MVP: Upload → validated metrics → interactive dashboard → AGP PDF export
- v2.0 Pattern Analysis: Behavioral patterns, overnight analysis, anomaly detection (library + CLI + web)
- v3.0 UX Improvements: ToD chart fix, behavioral patterns redesign, out-of-range priority insights, metric simplification

**Currently running:** 267 tests passing, 1 skipped

## Requirements

### Validated

- ✓ Upload CGM data files (Sugarmate exports) — v1.0
- ✓ Parse and validate uploaded data — v1.0
- ✓ Display key statistics (time-in-range, average glucose, SD, CV, percentiles) — v1.0/v3.0
- ✓ Detect patterns (time-of-day, day-of-week) — v1.0
- ✓ AGP report export — v1.0
- ✓ Time-bucketed behavioral patterns (30/60/120 min windows, sliding every 5 min) — v2.0
- ✓ Weekday vs weekend segmentation — v2.0
- ✓ Cross-day consistency analysis — v2.0
- ✓ Overnight glucose analysis (10pm-6am window, NGSI stability) — v2.0
- ✓ Anomaly detection (PISA-filtered, severity-classified, weekly summaries) — v2.0
- ✓ Time-of-Day chart rendering fix — v3.0
- ✓ Inline range status per behavioral pattern window — v3.0
- ✓ Out-of-range priority insights card with weekday/weekend split — v3.0

### Out of Scope

- Real-time CGM connection — file imports only
- Medical advice or diagnosis — informational insights only
- Post-meal analysis (ANLY-01) — no meal logging data
- Activity analysis (ANLY-04) — no activity data
- Carb counting / food database — outside core value
- Insulin dosing recommendations — medical liability
- Prescriptive alerts — alert fatigue, wellness framing required
- Render/cloud deployment — deferred (Phase 7 never executed)

## Context

**Technology stack:**
- Python 3.12, Polars, Pydantic v2, FastAPI + HTMX, Jinja2
- Chart.js (CDN), DaisyUI + Tailwind (CDN), Alpine.js
- Typer + Rich (CLI), ReportLab (AGP PDF)
- pytest (267 tests)

**Codebase:** ~5,987 Python LOC, ~1,715 HTML LOC, ~558 JS LOC, 31 Python files

**CGM data characteristics:**
- Readings every 5 minutes (~288/day)
- Glucose values in mg/dL
- Normal range: 70-180 mg/dL (ADA 2019 consensus, 5-band model)
- Sugarmate CSV format (extensible to other formats)

**Known deferred items (acknowledged at v3.0 close):**
- Phase 08 browser UAT: 3 scenarios pending manual testing
- Phase 07 (Render deployment): never executed, remains as tech debt
- Anomaly detection and suggestions: code exists in library/CLI but removed from web UI (simplification)

## Constraints

- **Architecture**: Python analysis engine must be decoupled from web frontend
- **Data formats**: Sugarmate Excel/CSV exports; extensible
- **Safety**: No insulin dosing recommendations or medical diagnoses
- **Regulatory**: Wellness language only throughout all user-facing text

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python analysis engine + web frontend | Reusable outside web context (library, CLI) | ✓ Good |
| File imports only | Simpler than real-time API integration | ✓ Good |
| Sugarmate format first | User has immediate dataset to validate against | ✓ Good |
| Pydantic v2 ConfigDict pattern | Modern Pydantic, avoids deprecation warnings | ✓ Good |
| 5-band time-in-range model | ADA 2019 clinical standards | ✓ Good |
| ReportLab for AGP PDF | Pure Python, no system dependencies | ✓ Good |
| Sleep window 10pm-6am | Typical sleep hours, inferred from glucose patterns | ✓ Good |
| CV = std-of-daily-overnight-means / mean | Cross-night variability, not intra-night | ✓ Good |
| PISA artifact filtering before anomaly detection | Prevents false positives from sensor pressure | ✓ Good |
| Anomaly detection removed from web UI (v3.0) | Low value-to-complexity ratio in practice | ✓ Good |
| GMI removed from web UI (v3.0) | Misleading for many users; SD + percentiles more useful | ✓ Good |
| UTC/local date key fix for TIR chart | toISOString() shifts late-night readings across UTC day boundary | ✓ Good |
| dayType filter in computeWindowDetails | Weekday/weekend rows must only show matching dates | ✓ Good |

---
*Last updated: 2026-06-13 after v3.0 milestone close*
