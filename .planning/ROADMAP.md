# Roadmap: CGM Insights

**Created:** 2026-04-23
**Granularity:** Coarse
**Architecture:** Python analysis engine (library) → CLI → Web frontend

---

## Core Value

Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

---

## Phases

### v1.0 (Complete)

- [x] **Phase 1: Core Analysis Library** - Foundation data pipeline with validated metrics, reusable as independent library
- [x] **Phase 2: CLI Tool + Insights** - Command-line interface validates core library, visualization and pattern detection
- [x] **Phase 3: Web Interface + Reports** - Browser-based upload with interactive dashboard and AGP report export

### v2.0 (Complete)

- [x] **Phase 4: Behavioral Pattern Analysis** - Users see time-bucketed patterns with cross-day consistency
- [x] **Phase 5: Sleep Analysis** - Users understand overnight glucose behavior
- [x] **Phase 6: Anomaly Detection** - Users identify unusual glucose deviations

### v3.0 (Current)

- [ ] **Phase 7: Render Deployment** - App is publicly accessible on Render with correct module paths, clean dependencies, and production-ready CORS

---

## Phase Details

### Phase 1: Core Analysis Library
**Goal:** Users can upload CGM data files and receive validated, accurate glucose metrics through a reusable Python library.

**Depends on:** Nothing (first phase)

**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, METR-01, METR-02, METR-03, METR-04, METR-05

**Success Criteria** (what must be TRUE):
1. User can upload a Sugarmate Excel file and see it parsed into structured glucose data
2. User is notified of data gaps and missing readings with clear completeness percentage
3. User can select analysis date range (7, 14, 30, 90 days or custom)
4. User sees Time-in-Range percentage across all 5 glucose bands (very low, low, target, high, very high)
5. User sees average glucose with standard deviation and GMI, with accuracy caveat displayed

**Plans:**
- [x] 01-01-PLAN.md — Environment setup (Python 3.10+, pyproject.toml, package structure)
- [x] 01-02-PLAN.md — Data models (CGMReading, ValidationResult, AnalysisResults)
- [x] 01-03-PLAN.md — Data ingestion (Parser, Sugarmate CSV, Validator, Normalizer)
- [x] 01-04-PLAN.md — Analytics & Output (GlucoStats metrics, formatter, public API)

---

### Phase 2: CLI Tool + Insights
**Goal:** Users can run analysis from command line and see glucose trends, patterns, and actionable suggestions.

**Depends on:** Phase 1

**Requirements:** VIZ-01, VIZ-02, VIZ-03, INSG-01, INSG-02, INSG-03, INSG-04

**Success Criteria** (what must be TRUE):
1. User can run analysis from terminal with file path and date range arguments
2. User can view glucose trend graph with color-coded zones (low/target/high)
3. User can view daily glucose summary statistics
4. User can compare two date ranges side-by-side (current vs previous period)
5. User sees time-of-day patterns surfaced with specific actionable suggestions
6. All insights use wellness language ("consider," "pattern") not medical advice

**Plans:**
- [x] 02-01-PLAN.md — CLI Entry Point (Typer setup, analyze command, basic text output)
- [x] 02-02-PLAN.md — Visualization Module (trend graph, daily table, period comparison)
- [x] 02-03-PLAN.md — Pattern Detection & Insights (time-of-day, day-of-week, wellness suggestions)

---

### Phase 3: Web Interface + Reports
**Goal:** Users can upload CGM data through a browser, explore results interactively, and export AGP reports for healthcare sharing.

**Depends on:** Phase 2

**Requirements:** RPT-01, RPT-02

**Success Criteria** (what must be TRUE):
1. User can upload Sugarmate file through web browser
2. User sees interactive dashboard with all metrics, graphs, and insights
3. User can export AGP (Ambulatory Glucose Profile) report for healthcare provider
4. AGP report includes all standard elements: glucose profile, daily glucose, and data statistics

**Plans:**
- [x] 03-01-PLAN.md — FastAPI Foundation & Upload (app structure, upload endpoint, base templates)
- [x] 03-02-PLAN.md — Interactive Dashboard (results page, Chart.js visualizations, patterns display)
- [x] 03-03-PLAN.md — AGP Report Export (PDF generation, standard AGP format, download endpoint)
- [x] 03-04-PLAN.md — Web Test Suite (upload tests, results tests, export tests, integration tests)

**UI hint:** yes

---

### Phase 4: Behavioral Pattern Analysis
**Goal:** Users can see how their glucose behavior varies across time periods and days, understanding which times are consistent and which vary.

**Depends on:** Phase 3 (v1.0 complete)

**Requirements:** BHVR-01, BHVR-02, BHVR-03, BHVR-04, BHVR-05, BHVR-06

**Success Criteria** (what must be TRUE):
1. User can view glucose patterns by time bucket (30/60/120 min windows sliding every 5 minutes)
2. User can compare weekday vs weekend patterns for each time period
3. User can see consistency scores showing how similar behavior is across days for each time period
4. User receives wellness-framed insights identifying predictable periods and variable periods
5. System surfaces actionable suggestions from behavioral patterns (e.g., consistent lunch timing)

**Plans:** 4 plans

Plans:
- [x] 04-01-PLAN.md — Core library: BehavioralPattern model, sliding-window algorithm, wellness suggestion templates
- [x] 04-02-PLAN.md — Public API wiring: analytics/__init__.py and cgm_insights/__init__.py exports
- [x] 04-03-PLAN.md — Web integration: session storage, upload pipeline, results route, behavioral_patterns.html tab component
- [x] 04-04-PLAN.md — CLI flag and test suite: --behavioral flag, Rich table renderer, test_behavioral_patterns.py

---

### Phase 5: Sleep Analysis
**Goal:** Users can understand their overnight glucose patterns and stability without needing sleep tracking data.

**Depends on:** Phase 4 (behavioral patterns provide time-bucketing foundation)

**Requirements:** SLEEP-01, SLEEP-02, SLEEP-03, SLEEP-04, SLEEP-05, SLEEP-06

**Success Criteria** (what must be TRUE):
1. User can view overnight glucose metrics (mean glucose, TIR, CV, time below range) for 10pm-6am window
2. User can compare weekday vs weekend overnight patterns (stability and control differences)
3. User can see NGSI-style stability index quantifying overnight glycemic stability
4. User is notified of sustained overnight excursions (highs/lows during overnight window)
5. All insights use "overnight" and "10pm-6am window" terminology, not "sleep" claims

**Plans:** 4 plans

Plans:
- [x] 05-01-PLAN.md — Core library: overnight_patterns.py module with OvernightAnalysisResult and analysis functions
- [x] 05-02-PLAN.md — Public API wiring: analytics/__init__.py and cgm_insights/__init__.py exports; overnight suggestion templates
- [x] 05-03-PLAN.md — Web integration: session storage, upload pipeline, results route, overnight_patterns.html component
- [x] 05-04-PLAN.md — CLI flag and test suite: --overnight flag, Rich table renderer, test_overnight_patterns.py

---

### Phase 6: Anomaly Detection
**Goal:** Users can identify glucose readings that deviate significantly from their personal baseline without being overwhelmed by alerts.

**Depends on:** Phase 4 (behavioral patterns establish baseline), Phase 5 (overnight context for anomaly context)

**Requirements:** ANLY-02, ANLY-03, ANLY-04, ANLY-05, ANLY-06

**Success Criteria** (what must be TRUE):
1. User can view detected anomalies (values >2 SD from time-of-day/day-of-week baseline)
2. Anomalies exclude PISA artifacts (pressure-induced sensor attenuation) to prevent false positives
3. Anomalies are classified by severity (mild, moderate, severe) based on deviation magnitude and duration
4. User sees weekly summary of anomaly patterns (aggregate counts, time distribution) rather than individual alerts
5. All anomaly insights use wellness language ("unusual pattern" not "abnormal")

**Plans:** 4 plans

Plans:
- [x] 06-01-PLAN.md — Core library: anomaly_detection.py with AnomalyDetectionResult, WeeklySummary, PISA filter, severity classification, analyze_anomalies()
- [x] 06-02-PLAN.md — Public API wiring: analytics/__init__.py and cgm_insights/__init__.py exports; generate_anomaly_suggestions() + templates in suggestions.py
- [x] 06-03-PLAN.md — Web integration: session storage, upload pipeline, results route, anomaly_detection.html component
- [x] 06-04-PLAN.md — CLI flag and test suite: --anomaly flag, Rich table renderer, test_anomaly_detection.py (≥8 tests)

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Analysis Library | 4/4 | Complete | 01-01, 01-02, 01-03, 01-04 |
| 2. CLI Tool + Insights | 3/3 | Complete | 02-01, 02-02, 02-03 |
| 3. Web Interface + Reports | 4/4 | Complete | 03-01, 03-02, 03-03, 03-04 |
| 4. Behavioral Pattern Analysis | 4/4 | Complete | 04-01, 04-02, 04-03, 04-04 |
| 5. Sleep Analysis | 4/4 | Complete | 05-01, 05-02, 05-03, 05-04 |
| 6. Anomaly Detection | 4/4 | Complete | 06-01, 06-02, 06-03, 06-04 |
| 7. Render Deployment | 0/1 | Not started | — |

---

## Architecture Notes

**Build Order (per constraint):**
1. Core library with no web dependencies
2. CLI tool that imports core library
3. Web frontend as thin adapters over core library

**Regulatory Compliance:**
- All user-facing text reviewed for wellness positioning
- No treatment recommendations, insulin dosing, or medical diagnoses
- GMI caveats displayed prominently

**Technology Stack:**
- Polars for high-performance data processing
- GlucoStats for validated CGM metrics
- FastAPI + HTMX for web interface
- Typer for CLI

**v2.0 Architecture:**
- Builds on existing core library, CLI, and web interfaces
- New analysis modules integrate into existing pipeline
- All features accessible via library API, CLI flags, and web UI

---

## Coverage

### v1.0 Requirements (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete (01-03) |
| DATA-02 | Phase 1 | Complete (01-02, 01-03) |
| DATA-03 | Phase 1 | Complete (01-03) |
| DATA-04 | Phase 1 | Complete (01-03) |
| DATA-05 | Phase 1 | Complete (01-03) |
| METR-01 | Phase 1 | Complete (01-04) |
| METR-02 | Phase 1 | Complete (01-04) |
| METR-03 | Phase 1 | Complete (01-04) |
| METR-04 | Phase 1 | Complete (01-04) |
| METR-05 | Phase 1 | Complete (01-04) |
| VIZ-01 | Phase 2 | Complete (02-02) |
| VIZ-02 | Phase 2 | Complete (02-01, 02-02) |
| VIZ-03 | Phase 2 | Complete (02-02) |
| INSG-01 | Phase 2 | Complete (02-03) |
| INSG-02 | Phase 2 | Complete (02-03) |
| INSG-03 | Phase 2 | Complete (02-03) |
| INSG-04 | Phase 2 | Complete (02-03) |
| RPT-01 | Phase 3 | Complete (03-01, 03-02) |
| RPT-02 | Phase 3 | Complete (03-03) |

### v2.0 Requirements (Current)

| Requirement | Phase | Status |
|-------------|-------|--------|
| BHVR-01 | Phase 4 | Complete (04-01, 04-02, 04-03, 04-04) |
| BHVR-02 | Phase 4 | Complete (04-01, 04-03, 04-04) |
| BHVR-03 | Phase 4 | Complete (04-01) |
| BHVR-04 | Phase 4 | Complete (04-01) |
| BHVR-05 | Phase 4 | Complete (04-01, 04-03, 04-04) |
| BHVR-06 | Phase 4 | Complete (04-01, 04-03, 04-04) |
| SLEEP-01 | Phase 5 | Complete (05-01, 05-02, 05-03, 05-04) |
| SLEEP-02 | Phase 5 | Complete (05-01, 05-02, 05-03, 05-04) |
| SLEEP-03 | Phase 5 | Complete (05-01, 05-02, 05-03, 05-04) |
| SLEEP-04 | Phase 5 | Complete (05-01, 05-02, 05-03, 05-04) |
| SLEEP-05 | Phase 5 | Complete (05-01, 05-02, 05-03, 05-04) |
| SLEEP-06 | Phase 5 | Complete (05-01, 05-02, 05-03, 05-04) |
| ANLY-02 | Phase 6 | Complete (06-01) |
| ANLY-03 | Phase 6 | Complete (06-01) |
| ANLY-04 | Phase 6 | Complete (06-01) |
| ANLY-05 | Phase 6 | Complete (06-01) |
| ANLY-06 | Phase 6 | Complete (06-02, 06-03, 06-04) |

**Summary:**
- v1.0 requirements: 19 total (complete)
- v2.0 requirements: 17 total
- Phase 4: 6 requirements (all complete)
- Phase 5: 6 requirements (all planned)
- Phase 6: 5 requirements (all planned)
- Coverage: 17/17 (100%)

---
*Last updated: 2026-06-11*
