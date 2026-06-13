# Milestones: CGM Insights

---

## v1.0 MVP — ✅ Shipped 2026-04-25

**Phases:** 1–3 | **Plans:** 11 | **Requirements:** 19/19

**Delivered:** File upload → validated metrics → interactive dashboard → AGP PDF export. End-to-end CGM analysis from browser or CLI with wellness-framed pattern detection.

**Key accomplishments:**
1. Core Python library: `analyze_file()` with Pydantic models, Polars parsing, 5-band TIR, SD, CV, GMI
2. CLI: `cgm-insights analyze <file>` with trend graph, daily table, period comparison, and pattern suggestions
3. Web: FastAPI + HTMX upload → Chart.js dashboard with TIR chart, time-of-day patterns
4. AGP PDF export via ReportLab (pure Python, no system dependencies)
5. Full test suite: 221 tests covering library, CLI, web, and integration

**Timeline:** 2026-04-24 → 2026-04-25 (2 days)
**Archive:** [v1.0-ROADMAP.md](./milestones/v1.0-ROADMAP.md) | [v1.0-REQUIREMENTS.md](./milestones/v1.0-REQUIREMENTS.md)

---

## v2.0 Pattern Analysis — ✅ Shipped 2026-06-11

**Phases:** 4–6 | **Plans:** 12 | **Requirements:** 17/17

**Delivered:** Three deep analysis modules — behavioral patterns (sliding-window, weekday/weekend, consistency scoring), overnight patterns (10pm-6am window with NGSI stability index), and anomaly detection (PISA-filtered, severity-classified, weekly summaries). All accessible via library, CLI flags, and web dashboard.

**Key accomplishments:**
1. Behavioral patterns: 30/60/120 min sliding windows, consistency labels, weekday/weekend split
2. Overnight analysis: mean, TIR, CV, TBR, stability score, weekday/weekend overnight comparison
3. Anomaly detection: PISA artifact filtering, 2-SD baseline outliers, mild/moderate/severe classification, weekly aggregates
4. All three modules wired through library → CLI → web (12 plans, uniform architecture)
5. 240 tests; multiple code-review findings fixed across all three phases

**Timeline:** 2026-06-11 → 2026-06-11 (1 day, intensive session)
**Archive:** [v2.0-ROADMAP.md](./milestones/v2.0-ROADMAP.md) | [v2.0-REQUIREMENTS.md](./milestones/v2.0-REQUIREMENTS.md)

---

## v3.0 UX Improvements — ✅ Shipped 2026-06-12

**Phases:** 8 (Phase 7 deferred) | **Plans:** 4 | **Quick tasks:** 3

**Delivered:** Fixed blank Time-of-Day chart. Redesigned behavioral patterns with inline range + variability per window (no accordion). Elevated out-of-range time windows as the primary insight card, weekday/weekend segmented with expandable per-date detail tables. Polish pass: day-of-week formatting, 21-day TIR chart, percentiles card, SD card, loading animation, simplified metrics.

**Key accomplishments:**
1. Time-of-Day chart fixed — patterns JS variable wiring bug resolved
2. Behavioral patterns redesigned — inline two-dimensional display (range + variability), canvas-rendered
3. Out-of-range insights elevated — weekday/weekend segmented priority cards with expandable detail
4. UTC/local date grouping bug fixed — late-night readings were bleeding into next UTC day
5. Metrics simplified — GMI removed, Standard Deviation + glucose percentiles (p50/p70/p90) added

**Known deferred items at close (acknowledged 2026-06-13):** 5 (see STATE.md Deferred Items)
- Phase 08 browser UAT (3 scenarios pending manual testing)
- Phase 08 verification (human review needed)
- Quick task audit tooling flags (tooling artifact, not implementation gaps)

**Timeline:** 2026-06-11 → 2026-06-13
**Archive:** [v3.0-ROADMAP.md](./milestones/v3.0-ROADMAP.md) | [v3.0-REQUIREMENTS.md](./milestones/v3.0-REQUIREMENTS.md)

---

*All milestones archived 2026-06-13*
