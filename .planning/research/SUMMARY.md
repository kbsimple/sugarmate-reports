# Research Summary: CGM Insights

**Project:** CGM Analytics Application
**Synthesized:** 2026-04-23
**Overall Confidence:** HIGH

---

## Executive Summary

This project builds a CGM (Continuous Glucose Monitor) analytics application that processes Sugarmate Excel exports to generate actionable glucose insights. The recommended approach is a **Python-first architecture** using Polars for high-performance data processing, GlucoStats for validated CGM metrics, and FastAPI with HTMX for a simple web interface that avoids JavaScript build complexity.

The core insight from research is that **wellness positioning is critical** — this must stay on the "informational insights" side of the FDA medical device boundary. The app should present glucose patterns and suggestions, never treatment recommendations. Additionally, **data quality handling is foundational** because CGM data inherently contains gaps, compression artifacts, and sensor inaccuracies that must be detected and flagged before analysis.

Three key risks require mitigation from day one: (1) regulatory compliance requires careful language throughout, (2) CGM data must be validated before metrics are calculated, and (3) insights must be actionable, not just observations — users need context and suggestions, not raw patterns.

---

## Key Technology Choices

| Technology | Role | Rationale |
|------------|------|-----------|
| **Polars 1.40.0** | Primary data processing | 7-9x faster than pandas for file I/O; lazy evaluation for memory efficiency; native Parquet/Arrow support; ideal for ~8,600 CGM readings/month |
| **GlucoStats 1.0.0** | CGM metrics calculation | Purpose-built library with 59 validated statistics including TIR, MAGE, GMI; scikit-learn compatible; published research validation |
| **FastAPI + HTMX** | Web framework + frontend | Server-side rendering eliminates React/build complexity; 5x faster page loads; Python developers stay productive |
| **Typer** | CLI interface | Thin wrapper for core library access; type-hint based; automatic help generation |

**Package Manager:** uv (10-100x faster than pip, 2026 standard)

---

## Table Stakes Features

Must-have features for a credible CGM analytics application:

1. **Time-in-Range (TIR)** — Core CGM metric; all 5 ranges (very low to very high)
2. **Average Glucose** — Mean with standard deviation
3. **Glucose Management Indicator (GMI)** — A1C estimate with caveat about ~25-30% inaccuracy
4. **Coefficient of Variation (%CV)** — Variability metric; target <36%
5. **Date Range Selection** — 7, 14, 30, 90 day presets + custom ranges
6. **Glucose Trend Graph** — Time-series with color-coded zones
7. **File Upload/Import** — Sugarmate Excel format
8. **AGP Report Export** — Clinical standard for healthcare sharing

**Defer to v2+:** Pattern detection, post-meal analysis, anomaly detection, actionable recommendations, sleep correlation

---

## Architecture Approach

**Layered separation pattern** with the analysis engine as an independent Python library:

```
[CLI Tool] [Web Frontend] [Direct Import]
         \         |          /
          \        |         /
           [Core Analysis Engine]
           [Ingestion | Analytics | Output]
                    |
              [Data Layer]
```

**Key Principle:** Interface layers (CLI, Web API) contain no business logic. They only parse input, call core engine functions, and format output. This enables:
- Core library usable independently as a package
- Testing without spinning up web server
- Future interfaces (API, desktop app) without rewrites

**Build Order:**
1. Data Models (no dependencies)
2. Ingestion — Parser + Sugarmate format + Validator
3. Analytics — Basic metrics (TIR, CV, GMI)
4. Output — Formatter
5. CLI — Validates core library works
6. Web API — Upload + analysis endpoints
7. Frontend — Upload UI + results display
8. Enhanced analytics — Patterns, anomalies, suggestions

---

## Critical Pitfalls to Avoid

| Pitfall | Prevention |
|---------|------------|
| **Medical device regulatory boundary** | Use wellness language ("glucose patterns," not "diabetes management"); include clear disclaimers; never provide treatment recommendations |
| **Treating CGM as accurate blood glucose** | Document 5-25 minute physiological lag; consider rate-of-change in timing; never recommend insulin timing |
| **Ignoring data quality issues** | Require 80% data completeness; detect compression lows; flag sensor warm-up period; validate before analysis |
| **Over-promising without actionability** | Follow chain: data -> pattern -> insight -> action; never show pattern without hypothesis; use "consider" language |

**Additional moderate pitfalls:**
- Alert fatigue (batch insights, user control)
- Single metrics without context (show TIR + CV + TBR together)
- Insufficient data for patterns (14+ days minimum)
- Performance on large datasets (vectorized operations, efficient structures)

---

## Recommended Phase Order

### Phase 1: Foundation + Core Metrics
**Rationale:** Must establish regulatory framing and data validation before any analysis. Core metrics are table stakes.

**Delivers:** File upload, data validation, TIR/GMI/CV calculations, basic visualization

**Features:** File Upload, Data Validation, Time-in-Range, Average Glucose, GMI, %CV, Glucose Trend Graph, Date Range Selection

**Pitfalls to Avoid:**
- Medical device boundary (legal review of all copy)
- Data quality issues (validation, completeness checks)
- CGM lag awareness in timing logic

**Research Flag:** Standard patterns — GlucoStats provides validated metric calculations.

---

### Phase 2: CLI Tool + Validation
**Rationale:** CLI validates core library works independently before web interface adds complexity.

**Delivers:** Command-line tool for local analysis, JSON/HTML report output

**Features:** CLI interface, file analysis from terminal, report generation

**Pitfalls to Avoid:**
- Performance degradation (test with realistic data volumes)
- Insufficient data (minimum thresholds before analysis)

**Research Flag:** Standard patterns — Typer is well-documented.

---

### Phase 3: Web Interface + AGP Export
**Rationale:** Web interface for broader access; AGP report is table stakes for clinical sharing.

**Delivers:** Browser-based upload, interactive results, downloadable AGP report

**Features:** Web Upload UI, Results Dashboard, AGP Report Export

**Pitfalls to Avoid:**
- Alert fatigue (thoughtful notification design)
- Single metrics without context (show related metrics together)

**Research Flag:** May need research — AGP report format requires specific structure.

---

### Phase 4: Pattern Detection (v2)
**Rationale:** Requires substantial data and validated core. Differentiator feature.

**Delivers:** Time-of-day patterns, day-of-week patterns, comparative periods

**Features:** Pattern Detection (Time-of-Day), Pattern Detection (Day-of-Week), Comparative Periods

**Pitfalls to Avoid:**
- Insufficient data for patterns (14+ days, validation)
- Over-promising without context

**Research Flag:** Needs research — Pattern detection algorithms require deeper investigation.

---

### Phase 5: Advanced Analytics (v3)
**Rationale:** Requires meal logging or detection algorithms. Highest complexity.

**Delivers:** Post-meal analysis, anomaly detection, actionable recommendations

**Features:** Post-Meal Analysis, Meal Scoring, Anomaly Detection, Actionable Recommendations

**Pitfalls to Avoid:**
- Food demonization (context-aware, avoid good/bad labels)
- Over-promising actionability without user context

**Research Flag:** Needs research — Anomaly detection algorithms, meal scoring approaches.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | Polars + FastAPI + GlucoStats are proven, well-documented choices |
| **Features** | HIGH | Table stakes clearly defined by competitive analysis; GlucoStats covers core metrics |
| **Architecture** | HIGH | Layered separation is standard pattern; thin interfaces proven approach |
| **Pitfalls** | HIGH | FDA guidance, CGM research papers, and app usability studies provide clear prevention strategies |
| **GlucoStats** | MEDIUM | New library (Sept 2025); may need patches for Sugarmate-specific format |

---

## Gaps to Address

1. **AGP Report Format:** Research needed on exact structure for clinical-standard export
2. **Sugarmate Excel Format:** Verify column names, data structure, edge cases
3. **Pattern Detection Algorithms:** Specific algorithms for time-of-day/day-of-week patterns need investigation
4. **Meal Detection:** If pursuing post-meal analysis, detection algorithm research required

---

## Sources

### Stack Research
- Polars vs Pandas benchmarks (Analytics Insight 2026)
- GlucoStats documentation and BMC Bioinformatics paper
- FastAPI deployment guides (Railway, SnapDeploy)
- uv package manager guide (2026)

### Features Research
- Dexcom Clarity, LibreView, Levels feature documentation
- AGP Report Standard (agpreport.org)
- GMI validation study (Bergenstal et al.)
- Diabetes app usability systematic review (PMC)

### Architecture Research
- Glucose360, iglu, cgmquantify open-source implementations
- FastAPI best practices for production
- Multi-interface Python library patterns

### Pitfalls Research
- FDA General Wellness Guidance (2026)
- CGM data quality processing algorithms (PMC)
- CGM accuracy and lag studies (medRxiv, Nature)
- Diabetes app privacy analysis (JMIR)
- Alert fatigue research (NCBI)
