# CGM Insights

## What This Is

A web application for CGM (Continuous Glucose Monitor) users to upload their data exports and receive actionable insights to improve glucose control. The app analyzes patterns, surfaces anomalies, and provides specific suggestions to help users stay in range more consistently. Built with a Python analysis engine (reusable as a library or CLI) and a simple web frontend.

## Core Value

Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Upload CGM data files (Sugarmate exports, extensible to other formats)
- [ ] Parse and validate uploaded data
- [ ] Display key statistics (time-in-range, average glucose, variability)
- [ ] Detect patterns (time-of-day, day-of-week, post-meal spikes)
- [ ] Identify anomalies and unexplained highs/lows
- [ ] Generate actionable suggestions to stay in range
- [ ] Layered experience: quick summary first, deep exploration available

### Out of Scope

- Real-time CGM connection — file imports only for v1
- Medical advice or diagnosis — informational insights only, not clinical recommendations

## Context

The initial dataset is from Sugarmate, a CGM tracking app that exports Excel files with daily glucose readings (5-minute intervals), trends, and daily statistics. The data spans 31 days with ~8,600 readings.

**CGM data characteristics:**
- Readings every 5 minutes (~288/day)
- Glucose values in mg/dL
- Trend arrows indicating direction
- Normal range: 70-180 mg/dL
- Key metrics: time-in-range, time below range, time above range, average glucose

**User goals:**
- Understand patterns in their glucose data
- Identify opportunities to improve control
- Get specific, actionable suggestions

## Constraints

- **Architecture**: Python analysis engine must be decoupled from web frontend for reusability as library/CLI
- **Data formats**: Start with Sugarmate Excel exports, design for extensibility
- **Safety**: No insulin dosing recommendations or medical diagnoses

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python analysis engine + web frontend | Reusable outside web context (library, future CLI) | — Pending |
| File imports only for v1 | Simpler than real-time API integration, covers most use cases | — Pending |
| Sugarmate format first | User has immediate dataset to validate against | — Pending |

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
*Last updated: 2026-04-24 after initialization*