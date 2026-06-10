---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Pattern Analysis Release
status: defining_requirements
last_updated: "2026-06-10T00:00:00Z"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# STATE.md: CGM Insights

**Last Updated:** 2026-06-10
**Status:** Defining requirements for v2.0

---

## Project Reference

**Core Value:** Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

**Current Focus:** Pattern Analysis Release — anomaly detection, sleep analysis, behavioral pattern analysis

---

## Current Position

| Field | Value |
|-------|-------|
| Phase | Not started (defining requirements) |
| Plan | — |
| Status | Defining requirements |
| Progress | `░░░░░░░░░░░░` 0% |

---

## v1.0 Completed

| Phase | Status | Plans |
|-------|--------|-------|
| 1. Core Analysis Library | ✓ Complete | 4/4 |
| 2. CLI Tool + Insights | ✓ Complete | 3/3 |
| 3. Web Interface + Reports | ✓ Complete | 4/4 |

**Shipped:** Data pipeline, validated metrics, CLI, pattern detection, web dashboard, AGP export

---

## v2.0 Scope

**Target features:**
- ANLY-02: Anomaly detection — unexplained highs/lows outside established patterns
- ANLY-03: Sleep analysis — overnight patterns (10pm-6am inferred)
- NEW: Behavioral pattern analysis — time-bucketed sliding windows, weekday/weekend segmentation, cross-day consistency

**Deferred:**
- ANLY-01 (post-meal) — no meal logging data
- ANLY-04 (activity) — no activity data

---

## Accumulated Context

### Key Decisions (v1.0)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-23 | 3-phase roadmap (coarse granularity) | Consolidates research's 5 phases into 3 aligned with build order constraint |
| 2026-04-23 | Phase 1 = Core library only | Enforces architecture constraint: reusable library before interfaces |
| 2026-04-23 | Insights in Phase 2 | Pattern detection requires metrics from Phase 1; visualization + insights are natural companions |
| 2026-04-25 | Pydantic v2 ConfigDict pattern | Modern Pydantic pattern, avoids deprecation warnings |
| 2026-04-25 | Glucose range 40-400 mg/dL | Physiologically plausible bounds for CGM device limits |
| 2026-04-25 | 5-band time-in-range model | Follows clinical standards (very_low/low/target/high/very_high) |
| 2026-04-25 | Filter invalid glucose values | Graceful handling of edge values instead of rejecting entire file |
| 2026-04-25 | Custom metric calculation | GlucoStats pandas 2.x compatibility issues; implemented fallback calculation |
| 2026-04-25 | GMI_CAVEAT constant | Wellness disclaimer required per regulatory requirements |
| 2026-04-25 | Typer CLI framework | Simple, Pythonic CLI framework with Rich integration |
| 2026-04-25 | asciichartpy for trend graphs | Correct package with plot function; asciichart lacks it |
| 2026-04-25 | Rich tables for metrics | Professional terminal tables with color-coded target ranges |
| 2026-04-25 | Visualization on by default | --viz enabled; users can disable with --no-viz |
| 2026-04-25 | 2-hour time blocks for patterns | Time-of-day patterns grouped into 12 periods for meaningful analysis |
| 2026-04-25 | 20% baseline deviation for patterns | Patterns flagged when glucose deviates >20% from average |
| 2026-04-25 | Template-based suggestions | Wellness language templates ensure no medical advice in outputs |
| 2026-04-25 | --insights flag defaults to on | Best user experience with insights visible by default |
| 2026-04-25 | Chart.js via CDN for visualizations | No build step needed, simple integration |
| 2026-04-25 | SessionData stores patterns and readings | Single session object for all dashboard data |
| 2026-04-25 | ReportLab for AGP PDF generation | Pure Python, no system dependencies (WeasyPrint needs GTK) |
| 2026-04-25 | pytest-cov for coverage reporting | Coverage measurement for test quality |
| 2026-04-25 | Test fixtures with TestClient | Isolated tests with session store reset |

### Active Constraints

- **Architecture:** Python library first, CLI second, web last
- **Regulatory:** Wellness language only, no medical advice
- **Technology:** Polars, GlucoStats, FastAPI + HTMX, Typer, Rich, asciichartpy, Chart.js, ReportLab
- **v2.0 data:** No external data sources (meals, activity) — analysis from glucose data alone

---

## Session Continuity

**Entry Point:** Starting v2.0 requirements

**Next Action:** `/gsd-new-milestone` (in progress — defining requirements)

---
*This file tracks current position and context. Update after each phase transition.*