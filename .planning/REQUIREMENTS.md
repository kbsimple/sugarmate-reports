# Requirements: CGM Insights

**Defined:** 2026-04-24
**Core Value:** Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Import

- [x] **DATA-01**: User can upload Sugarmate Excel export files
- [x] **DATA-02**: System parses glucose readings, timestamps, and trends from uploaded file
- [x] **DATA-03**: System validates data completeness and flags gaps/missing readings
- [x] **DATA-04**: System detects and handles sensor warm-up periods (first 2 hours typically inaccurate)
- [x] **DATA-05**: User can select date range for analysis (7, 14, 30, 90 days + custom)

### Core Metrics

- [x] **METR-01**: System calculates Time-in-Range (TIR) across all 5 glucose bands
- [x] **METR-02**: System calculates average glucose with standard deviation
- [x] **METR-03**: System calculates Glucose Management Indicator (GMI) with accuracy caveats
- [x] **METR-04**: System calculates Coefficient of Variation (%CV) for variability
- [x] **METR-05**: System calculates Time Below Range (TBR) and Time Very Low (severe hypoglycemia risk)

### Visualization

- [ ] **VIZ-01**: User can view glucose trend graph with color-coded zones (low/target/high)
- [ ] **VIZ-02**: User can view daily glucose summary statistics
- [ ] **VIZ-03**: User can compare date ranges side-by-side (this period vs previous)

### Insights

- [ ] **INSG-01**: System identifies time-of-day patterns (e.g., "You consistently spike in the afternoon")
- [ ] **INSG-02**: System identifies day-of-week patterns (e.g., "Weekends show higher variability")
- [ ] **INSG-03**: System surfaces actionable suggestions tied to patterns (e.g., "Consider a short walk after lunch")
- [ ] **INSG-04**: All insights use wellness language, not medical advice

### Reports

- [ ] **RPT-01**: User can export AGP (Ambulatory Glucose Profile) report for healthcare sharing
- [ ] **RPT-02**: Report includes all standard AGP elements (glucose profile, daily glucose, data statistics)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Analytics

- **ANLY-01**: Post-meal analysis with meal logging
- **ANLY-02**: Anomaly detection for unexplained glucose events
- **ANLY-03**: Sleep-glucose correlation analysis
- **ANLY-04**: Activity impact analysis

### Platform Features

- **PLAT-01**: Real-time CGM connection (Dexcom, Libre APIs)
- **PLAT-02**: Multi-device sync and cloud storage
- **PLAT-03**: User accounts and data persistence

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Insulin dosing recommendations | Medical liability, FDA-regulated device territory |
| Medical diagnoses | Regulatory boundary — informational only |
| Real-time CGM connection | Complexity, API integrations deferred to v2+ |
| Carb counting / food database | Crowded space, user friction, outside core value |
| Prescriptive alerts ("Eat now!") | Alert fatigue, user complaints |
| Perfect A1C accuracy claims | GMI inaccurate for 25-30% of users; honesty builds trust |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete |
| METR-01 | Phase 1 | Complete |
| METR-02 | Phase 1 | Complete |
| METR-03 | Phase 1 | Complete |
| METR-04 | Phase 1 | Complete |
| METR-05 | Phase 1 | Complete |
| VIZ-01 | Phase 2 | Pending |
| VIZ-02 | Phase 2 | Pending |
| VIZ-03 | Phase 2 | Pending |
| INSG-01 | Phase 2 | Pending |
| INSG-02 | Phase 2 | Pending |
| INSG-03 | Phase 2 | Pending |
| INSG-04 | Phase 2 | Pending |
| RPT-01 | Phase 3 | Pending |
| RPT-02 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-24 after roadmap creation*