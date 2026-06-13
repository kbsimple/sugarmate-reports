---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: UX Improvements
status: phase_complete
last_updated: "2026-06-12T00:00:00Z"
progress:
  total_phases: 1
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
  percent: 100
current_phase: 8
current_phase_name: Time-of-Day Chart & Patterns UX
---

# STATE.md: CGM Insights

**Last Updated:** 2026-06-12
**Status:** v3.0 Phase 8 COMPLETE — ToD chart fix, behavioral patterns redesign, out-of-range insights, SC-5 gap closure

Last activity: 2026-06-12 - Completed quick task 260612-bh9: 7 report UI updates (dismissable banner, weekday/weekend splits, hourly ToD patterns, 3-week avg overlay, behavioral colors)

---

## Project Reference

**Core Value:** Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

**Current Focus:** v2.0 Pattern Analysis Release — behavioral patterns, sleep analysis, anomaly detection

---

## Current Position

| Field | Value |
|-------|-------|
| Phase | Phase 8: Time-of-Day Chart & Patterns UX |
| Plan | 08-04 complete (all 4 plans done) |
| Status | Complete |
| Progress | `████████████` 100% (1/1 v3.0 phase, 4/4 plans in Phase 8) |

---

## v1.0 Completed

| Phase | Status | Plans |
|-------|--------|-------|
| 1. Core Analysis Library | Complete | 4/4 |
| 2. CLI Tool + Insights | Complete | 3/3 |
| 3. Web Interface + Reports | Complete | 4/4 |

**Shipped:** Data pipeline, validated metrics, CLI, pattern detection, web dashboard, AGP export

---

## v2.0 Phases

| Phase | Status | Plans |
|-------|--------|-------|
| 4. Behavioral Pattern Analysis | Complete | 4/4 |
| 5. Sleep Analysis | Complete | 4/4 |
| 6. Anomaly Detection | Complete | 4/4 |

**Scope:** 17 requirements across 3 phases

---

## v2.0 Requirements by Phase

### Phase 4: Behavioral Pattern Analysis (6 requirements)
- BHVR-01: Time buckets (30/60/120 min, sliding every 5 min)
- BHVR-02: Weekday vs weekend segmentation
- BHVR-03: Cross-day consistency scores
- BHVR-04: Identify high-consistency and high-variability periods
- BHVR-05: Actionable insights from patterns
- BHVR-06: Wellness language throughout

### Phase 5: Sleep Analysis (6 requirements)
- SLEEP-01: 10pm-6am window analysis
- SLEEP-02: Overnight metrics (mean, TIR, CV, TBR)
- SLEEP-03: Weekday vs weekend overnight comparison
- SLEEP-04: NGSI stability index
- SLEEP-05: Overnight excursion detection
- SLEEP-06: "Overnight" terminology (not "sleep")

### Phase 6: Anomaly Detection (5 requirements)
- ANLY-02: Statistical outlier detection (>2 SD from baseline)
- ANLY-03: PISA artifact filtering
- ANLY-04: Severity classification (mild/moderate/severe)
- ANLY-05: Weekly anomaly summaries (no individual alerts)
- ANLY-06: Wellness language throughout

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

### Key Decisions (v2.0)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-10 | 3-phase roadmap (coarse granularity) | Groups related features: behavioral patterns, sleep analysis, anomaly detection |
| 2026-06-10 | Behavioral patterns first (Phase 4) | Establishes time-bucketed analysis foundation; provides baseline for anomaly detection |
| 2026-06-10 | Sleep analysis second (Phase 5) | Builds on time-bucketing from Phase 4; focused overnight window analysis |
| 2026-06-10 | Anomaly detection last (Phase 6) | Depends on behavioral baselines from Phase 4; uses overnight context from Phase 5 |
| 2026-06-11 | CV computed as std-of-daily-overnight-means / mean * 100 | Cross-night variability metric, not intra-night; matches behavioral_patterns approach |
| 2026-06-11 | night_date maps post-midnight readings back one day | Ensures overnight readings belong to the EVENING they started, not calendar morning |
| 2026-06-11 | Excursions aggregated to night-level counts | Avoids clinical alert framing; sustained_low_nights/sustained_high_nights/total_excursion_nights |
| 2026-06-11 | baselines.height==0 returns insufficient_data=False | Uniform data has no variance to detect against, but analysis ran successfully with sufficient days |

### Active Constraints

- **Architecture:** Python library first, CLI second, web last
- **Regulatory:** Wellness language only, no medical advice
- **Technology:** Polars, GlucoStats, FastAPI + HTMX, Typer, Rich, asciichartpy, Chart.js, ReportLab
- **v2.0 data:** No external data sources (meals, activity) — analysis from glucose data alone

---

## Session Continuity

**Entry Point:** v2.0 roadmap created

**Next Action:** `/gsd-execute-phase` to execute Plan 06-03 (web integration)

**Session (2026-06-11):** Phase 4 complete — 4 plans executed (sliding-window behavioral analysis, public API wiring, web integration, CLI flag + tests). 221 tests passing. 6 code review findings fixed (dead suggestion integration, midnight-bucket suggestion selection, min_days threading, /data endpoint, CLI warning gap, empty-string guard).

**Session (2026-06-11):** Phase 5 Plan 01 complete — overnight_patterns.py created with OvernightAnalysisResult model, _get_overnight_df, _compute_metrics, _detect_excursions, and analyze_overnight_patterns. All 221 existing tests pass. Commit af09e2b.

**Session (2026-06-11):** Phase 5 Plan 02 complete — overnight patterns wired into cgm_insights.analytics and cgm_insights public APIs; generate_overnight_suggestions() added with 5 wellness-language templates. All 221 tests pass. Commit 319d0ca.

**Session (2026-06-11):** Phase 5 Plan 04 complete — --overnight/--no-overnight CLI flag added to analyze and download_and_analyze commands; _render_overnight_patterns() Rich table renderer added; 10-test overnight_patterns test suite created. 241 tests pass (221 + 10 new + 10 from 05-02). Commit a37ef4c.

**Session (2026-06-11):** Phase 5 Plan 03 complete — overnight analysis wired through web layer: SessionData, upload.py, results.py template context, /data JSON endpoint, results.html include, overnight_patterns.html component. 231 tests pass. No "sleep" word in user-facing output. Commit 4891e09.

**Session (2026-06-11):** Phase 5 complete — 4 plans executed (overnight core library, API wiring + suggestions, web integration, CLI + 10-test suite). 231 tests passing. 4 code review findings fixed (std_g None guard, post-filter insufficient_data check, MIN_NIGHTS_FOR_SPLIT=3, night_date-based day_type derivation). SLEEP-01–06 all verified ✓.

**Session (2026-06-11):** Phase 6 Plan 01 complete — anomaly_detection.py created with PISA artifact filter (per-day drop/recovery signature), two-step Polars bucket baseline (_compute_bucket_baselines), severity classifier (2/3/4 SD), weekly summary builder (_build_weekly_summaries), and analyze_anomalies() public entry. All 231 existing tests pass. Commit 6f166ce.

**Session (2026-06-11):** Phase 6 Plan 02 complete — analyze_anomalies and AnomalyDetectionResult wired into analytics/__init__ and cgm_insights/__init__ public APIs; generate_anomaly_suggestions() added with 3 severity-tiered wellness-language templates. At-most-one-suggestion design selects highest severity tier. All 231 tests pass. Commit 8dfa4e0.

**Session (2026-06-11):** Phase 6 Plan 04 complete — --anomaly/--no-anomaly CLI flag added to analyze and download_and_analyze commands; _render_anomaly_detection() Rich table renderer added; 9-test anomaly_detection test suite created. Rule 1 fix: baselines.height==0 with sufficient days now returns insufficient_data=False. 240 tests pass. Commit e5febf8.

**Session (2026-06-11):** Phase 6 Plan 03 complete — anomaly detection wired into web layer: SessionData field, upload.py call, results.py extraction + suggestion merge, /data JSON endpoint, results.html include, anomaly_detection.html DaisyUI component. 240 tests pass. No forbidden wellness terms in user-facing output. Commit be62810. Phase 6 now fully complete (4/4 plans).

**Session (2026-06-11):** v2.0 MILESTONE COMPLETE — Phase 6 code review fixed WR-01 (PISA loop advancement: i=nadir_idx+1 after flagging), IN-01 (strftime portability: f-string day), IN-02 (deterministic period sort). ANLY-02–06 all verified ✓. 240 tests pass. All 3 v2.0 phases (4: Behavioral, 5: Overnight, 6: Anomaly) complete. Commit 36613a1.

**Session (2026-06-12):** Phase 8 complete — 4 plans executed (ToD chart const-patterns fix, behavioral_patterns.html accordion removal + inline range/consistency badges, out_of_range_insights.html component, pct_out_of_range gap closure SC-5). 252 tests passing. 1 warning + 3 info code review findings (advisory). 3 browser verification items saved to 08-HUMAN-UAT.md.

### Roadmap Evolution

- Phase 8 added: Fix Time-of-Day chart rendering, redesign behavioral patterns with inline range status (no accordion, variability + range dimensions), elevate out-of-range time windows as actionable priority insights segmented by weekday/weekend

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260612-bh9 | 7 UI updates: dismissable banner, weekday/weekend splits, hourly ToD, glucose trend avg overlay, behavioral colors | 2026-06-12 | a9c6d1b | [260612-bh9-report-ui-updates](./quick/260612-bh9-report-ui-updates/) |

---
*This file tracks current position and context. Update after each phase transition.*