# Retrospective: CGM Insights

---

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-25
**Phases:** 3 | **Plans:** 11

### What Was Built
- Core Python library with Pydantic models, Polars parsing, 5-band TIR, SD, CV, GMI
- CLI with trend graph, daily table, period comparison, wellness suggestions
- FastAPI + HTMX web app with Chart.js dashboard and AGP PDF export
- 221-test suite covering library, CLI, web, integration

### What Worked
- Build-order constraint (library → CLI → web) forced clean separation that paid off in later phases
- Sugarmate format first gave immediate validation data
- ReportLab for PDF — no system dependencies made deployment easy

### What Was Inefficient
- GlucoStats pandas 2.x compat issue required fallback implementation — research would have caught this upfront
- asciichartpy vs asciichart package naming confusion — small but avoidable

### Key Lessons
- Validate library dependencies against target Python version before planning
- The 4-plan pattern (library → API → web → CLI+tests) established here became the template for v2.0

---

## Milestone: v2.0 — Pattern Analysis

**Shipped:** 2026-06-11
**Phases:** 3 | **Plans:** 12

### What Was Built
- Behavioral patterns: 30/60/120 min sliding windows, weekday/weekend split, consistency scoring
- Overnight analysis: 10pm-6am window, NGSI stability index, excursion detection
- Anomaly detection: PISA artifact filter, 2-SD baseline outliers, severity classification, weekly summaries
- All three modules wired library → CLI flag → web component (uniform 4-plan architecture)

### What Worked
- The 4-plan architecture from v1.0 replicated cleanly across all three phases
- Code review after each phase caught meaningful bugs (PISA loop, sort stability, None guards)
- Building behavioral patterns first gave overnight and anomaly modules a ready time-bucketing foundation

### What Was Inefficient
- Anomaly detection and suggestions were built fully (web UI, CLI, library) but later removed in v3.0 — scope could have been scoped to library/CLI only given the UI was already getting complex
- REQUIREMENTS.md traceability table was not updated as phases completed — stale at archive time

### Key Lessons
- UI features should be validated for "does this add value?" before building the full web component
- Keep REQUIREMENTS.md traceability table updated at plan completion, not milestone close

---

## Milestone: v3.0 — UX Improvements

**Shipped:** 2026-06-12
**Phases:** 1 (Phase 8) | **Plans:** 4 | **Quick tasks:** 3

### What Was Built
- Fixed blank Time-of-Day chart (patterns JS variable wiring bug)
- Behavioral patterns redesigned: inline two-dimensional display (range + variability), canvas-rendered
- Out-of-range insights elevated as primary card: weekday/weekend segmented, expandable per-date detail
- Multiple quick-task polish passes: day-of-week formatting, 21-day TIR, percentiles card, SD card, loading animation, simplified metrics

### What Worked
- Quick tasks were the right tool for the polish pass — fast, atomic, low ceremony
- Identifying and fixing the UTC/local date bug eliminated an invisible data correctness issue
- Simplification pass (remove GMI, anomaly section, suggestions) made the report cleaner and more focused

### What Was Inefficient
- Phase 7 (Render deployment) was on the roadmap but never executed — should have been removed or deferred explicitly earlier
- Browser UAT requires manual testing — 3 scenarios remain unverified at close

### Patterns Established
- UTC/local timezone discipline: always use local calendar date for client-side grouping keys
- dayType parameter pattern: filter data by weekday/weekend at the JS function level, not at render time
- Quick-task slug convention: YYMMDD-xxx-slug (base36 timestamp suffix)

### Key Lessons
- Removing features can be as valuable as adding them — the simplification pass improved clarity
- Phase 7 should have been marked deferred in the roadmap much earlier rather than staying as "not started"

---

## Cross-Milestone Trends

| Metric | v1.0 | v2.0 | v3.0 |
|--------|------|------|------|
| Phases | 3 | 3 | 1 |
| Plans | 11 | 12 | 4 |
| Timeline | 2 days | 1 day | 2 days |
| Tests at close | 221 | 240 | 267 |
| Code review findings fixed | — | 9 | 2 |

**Trend:** Consistent 4-plan-per-phase architecture. Test count growing steadily. Quick tasks emerged in v3.0 as the right tool for polish work.

---

*Written: 2026-06-13*
