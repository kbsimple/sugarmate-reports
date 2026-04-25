# Roadmap: CGM Insights

**Created:** 2026-04-23
**Granularity:** Coarse
**Architecture:** Python analysis engine (library) → CLI → Web frontend

---

## Core Value

Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

---

## Phases

- [ ] **Phase 1: Core Analysis Library** - Foundation data pipeline with validated metrics, reusable as independent library
- [ ] **Phase 2: CLI Tool + Insights** - Command-line interface validates core library, visualization and pattern detection
- [ ] **Phase 3: Web Interface + Reports** - Browser-based upload with interactive dashboard and AGP report export

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

**Plans:** TBD

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

**Plans:** TBD

**UI hint:** yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Analysis Library | 4/4 | Planned | - |
| 2. CLI Tool + Insights | 0/3 | Not started | - |
| 3. Web Interface + Reports | 0/3 | Not started | - |

---

## Architecture Notes

**Build Order (per constraint):**
1. Core library with no web dependencies
2. CLI tool that imports core library
3. Web frontend as thin adapter over core library

**Regulatory Compliance:**
- All user-facing text reviewed for wellness positioning
- No treatment recommendations, insulin dosing, or medical diagnoses
- GMI caveats displayed prominently

**Technology Stack:**
- Polars for high-performance data processing
- GlucoStats for validated CGM metrics
- FastAPI + HTMX for web interface
- Typer for CLI

---

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Planned (01-03) |
| DATA-02 | Phase 1 | Planned (01-02, 01-03) |
| DATA-03 | Phase 1 | Planned (01-03) |
| DATA-04 | Phase 1 | Planned (01-03) |
| DATA-05 | Phase 1 | Planned (01-03) |
| METR-01 | Phase 1 | Planned (01-04) |
| METR-02 | Phase 1 | Planned (01-04) |
| METR-03 | Phase 1 | Planned (01-04) |
| METR-04 | Phase 1 | Planned (01-04) |
| METR-05 | Phase 1 | Planned (01-04) |
| VIZ-01 | Phase 2 | Pending |
| VIZ-02 | Phase 2 | Pending |
| VIZ-03 | Phase 2 | Pending |
| INSG-01 | Phase 2 | Pending |
| INSG-02 | Phase 2 | Pending |
| INSG-03 | Phase 2 | Pending |
| INSG-04 | Phase 2 | Pending |
| RPT-01 | Phase 3 | Pending |
| RPT-02 | Phase 3 | Pending |

**Summary:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---

*Last updated: 2026-04-24*