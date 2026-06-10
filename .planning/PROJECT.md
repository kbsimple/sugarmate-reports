# CGM Insights

## What This Is

A web application for CGM (Continuous Glucose Monitor) users to upload their data exports and receive actionable insights to improve glucose control. The app analyzes patterns, surfaces anomalies, and provides specific suggestions to help users stay in range more consistently. Built with a Python analysis engine (reusable as a library or CLI) and a simple web frontend.

## Core Value

Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

## Current Milestone: v2.0 Pattern Analysis Release

**Goal:** Surface behavioral patterns and anomalies from CGM data so users understand when they're consistent and can take targeted action.

**Target features:**
- **ANLY-02**: Anomaly detection — unexplained highs/lows outside established patterns
- **ANLY-03**: Sleep analysis — overnight patterns inferred from 10pm-6am window
- **NEW**: Behavioral pattern analysis — time-bucketed patterns (30/60/120 min), sliding windows every 5 minutes, weekday vs weekend segmentation, cross-day consistency

**Deferred (no data):**
- ANLY-01 (post-meal) — no meal logging
- ANLY-04 (activity) — no activity data

## Requirements

### Validated

(v1.0 shipped)

- [x] Upload CGM data files (Sugarmate exports)
- [x] Parse and validate uploaded data
- [x] Display key statistics (time-in-range, average glucose, variability)
- [x] Detect patterns (time-of-day, day-of-week)
- [x] Generate actionable suggestions
- [x] AGP report export

### Active

- [ ] Anomaly detection — identify unexplained highs/lows outside established patterns
- [ ] Sleep analysis — overnight patterns from inferred 10pm-6am window
- [ ] Time-bucketed behavioral patterns (30/60/120 min windows, sliding every 5 min)
- [ ] Weekday vs weekend segmentation
- [ ] Cross-day consistency analysis ("is noon behavior similar across weekdays?")

### Out of Scope

- Real-time CGM connection — file imports only
- Medical advice or diagnosis — informational insights only
- Post-meal analysis (ANLY-01) — no meal logging data
- Activity analysis (ANLY-04) — no activity data
- Carb counting / food database — outside core value

## Context

**v1.0 shipped with:**
- Core library: `analyze_file()`, `format_results()`, CGMReading, AnalysisResults
- CLI: `cgm-insights analyze <file>` with `--viz`, `--compare`, `--insights` flags
- Pattern detection: time-of-day, day-of-week analysis
- Web: FastAPI app with upload endpoint, Chart.js dashboard
- AGP export: PDF generation with ReportLab

**CGM data characteristics:**
- Readings every 5 minutes (~288/day)
- Glucose values in mg/dL
- Trend arrows indicating direction
- Normal range: 70-180 mg/dL

**v2.0 data constraints:**
- No meal data — cannot label spikes as "breakfast" or "lunch"
- No activity data — cannot correlate exercise with glucose
- Sleep inferred from 10pm-6am window (typical sleep hours)

## Constraints

- **Architecture**: Python analysis engine must be decoupled from web frontend for reusability as library/CLI
- **Data formats**: Sugarmate Excel exports, extensible to other formats
- **Safety**: No insulin dosing recommendations or medical diagnoses
- **v2.0 data**: No external data sources (meals, activity) — analysis from glucose data alone

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python analysis engine + web frontend | Reusable outside web context (library, CLI) | ✓ Good |
| File imports only for v1 | Simpler than real-time API integration | ✓ Good |
| Sugarmate format first | User has immediate dataset to validate against | ✓ Good |
| Pydantic v2 ConfigDict pattern | Modern Pydantic, avoids deprecation warnings | ✓ Good |
| Glucose range 40-400 mg/dL | Physiologically plausible bounds | ✓ Good |
| 5-band time-in-range model | Clinical standards | ✓ Good |
| ReportLab for AGP PDF | Pure Python, no system dependencies | ✓ Good |
| Sleep window 10pm-6am | Typical sleep hours, infer from glucose patterns | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-10 after v1.0 completion, starting v2.0*