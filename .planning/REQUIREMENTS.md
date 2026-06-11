# Requirements: CGM Insights

**Defined:** 2026-04-24 (v1.0), 2026-06-10 (v2.0)
**Core Value:** Users upload their CGM data and leave knowing exactly what to focus on to improve their glucose control.

## v1.0 Requirements (Shipped)

Requirements for initial release. All phases complete.

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

- [x] **VIZ-01**: User can view glucose trend graph with color-coded zones (low/target/high)
- [x] **VIZ-02**: User can view daily glucose summary statistics
- [x] **VIZ-03**: User can compare date ranges side-by-side (this period vs previous)

### Insights

- [x] **INSG-01**: System identifies time-of-day patterns (e.g., "You consistently spike in the afternoon")
- [x] **INSG-02**: System identifies day-of-week patterns (e.g., "Weekends show higher variability")
- [x] **INSG-03**: System surfaces actionable suggestions tied to patterns (e.g., "Consider a short walk after lunch")
- [x] **INSG-04**: All insights use wellness language, not medical advice

### Reports

- [x] **RPT-01**: User can export AGP (Ambulatory Glucose Profile) report for healthcare sharing
- [x] **RPT-02**: Report includes all standard AGP elements (glucose profile, daily glucose, data statistics)

---

## v2.0 Requirements (Current Milestone)

Pattern Analysis Release — anomaly detection, sleep analysis, behavioral patterns.

### Anomaly Detection

- [ ] **ANLY-02**: System detects statistical outliers from user's personal baseline (glucose values >2 SD from time-of-day/day-of-week pattern)
- [ ] **ANLY-03**: System filters PISA artifacts (pressure-induced sensor attenuation) before anomaly detection to prevent false positives
- [ ] **ANLY-04**: System classifies anomalies by severity (mild, moderate, severe) based on deviation magnitude and duration
- [ ] **ANLY-05**: System provides weekly anomaly summaries (aggregate counts, patterns, time distribution) to avoid alert fatigue
- [ ] **ANLY-06**: All anomaly insights use wellness language ("unusual pattern" not "abnormal", "consider discussing" not "diagnosis")

### Sleep Analysis

- [ ] **SLEEP-01**: System analyzes glucose patterns during 10pm-6am window (labeled as "overnight" not "sleep")
- [ ] **SLEEP-02**: System calculates overnight metrics: mean glucose, TIR, CV, time below range
- [ ] **SLEEP-03**: System compares weekday vs weekend overnight patterns (differences in stability and control)
- [ ] **SLEEP-04**: System calculates NGSI-style stability index (nocturnal glycemic stability) for overnight periods
- [ ] **SLEEP-05**: System detects overnight excursions (sustained highs/lows during overnight window)
- [x] **SLEEP-06**: All sleep insights use wellness framing and acknowledge window assumption

### Behavioral Patterns

- [ ] **BHVR-01**: System groups glucose behavior into time buckets (30, 60, 120 minute windows) with sliding starts every 5 minutes
- [ ] **BHVR-02**: System separates patterns by weekday vs weekend (different metabolic profiles)
- [ ] **BHVR-03**: System calculates cross-day consistency score for each time period (correlation coefficient indicating how similar behavior is across days)
- [ ] **BHVR-04**: System identifies high-consistency time periods (where behavior is predictable) and high-variability periods (where behavior varies)
- [ ] **BHVR-05**: System surfaces actionable insights from behavioral patterns (e.g., "Your 12pm readings are consistent on weekdays — consider this for meal timing")
- [ ] **BHVR-06**: All behavioral insights use wellness language and avoid prescriptive recommendations

---

## v2+ Requirements (Future)

Deferred to future releases. Tracked but not in current roadmap.

### Post-Meal Analysis (ANLY-01 deferred)

- **ANLY-01**: Post-meal analysis with meal logging — requires meal data not currently available

### Activity Analysis (ANLY-04 deferred)

- **ANLY-04**: Activity impact analysis — requires activity data not currently available

### Platform Features

- **PLAT-01**: Real-time CGM connection (Dexcom, Libre APIs)
- **PLAT-02**: Multi-device sync and cloud storage
- **PLAT-03**: User accounts and data persistence

### Enhanced Analytics (v2.1+)

- **ENHC-01**: Inferred sleep window detection (from glucose stability patterns, not fixed 10pm-6am)
- **ENHC-02**: Pattern similarity analysis using dynamic time warping (DTW)
- **ENHC-03**: Personalized anomaly threshold tuning based on user feedback
- **ENHC-04**: Custom sleep window configuration for shift workers

---

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
| Individual anomaly alerts | Alert fatigue — aggregate summaries only |
| "Sleep" terminology | Sleep inferred, not confirmed; use "overnight" or "10pm-6am window" |
| Medical claims in insights | FDA enforcement risk; wellness framing required |

---

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

### v1.0 (Complete)

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
| VIZ-01 | Phase 2 | Complete |
| VIZ-02 | Phase 2 | Complete |
| VIZ-03 | Phase 2 | Complete |
| INSG-01 | Phase 2 | Complete |
| INSG-02 | Phase 2 | Complete |
| INSG-03 | Phase 2 | Complete |
| INSG-04 | Phase 2 | Complete |
| RPT-01 | Phase 3 | Complete |
| RPT-02 | Phase 3 | Complete |

### v2.0 (Current)

| Requirement | Phase | Status |
|-------------|-------|--------|
| BHVR-01 | Phase 4 | Pending |
| BHVR-02 | Phase 4 | Pending |
| BHVR-03 | Phase 4 | Pending |
| BHVR-04 | Phase 4 | Pending |
| BHVR-05 | Phase 4 | Pending |
| BHVR-06 | Phase 4 | Pending |
| SLEEP-01 | Phase 5 | Pending |
| SLEEP-02 | Phase 5 | Pending |
| SLEEP-03 | Phase 5 | Pending |
| SLEEP-04 | Phase 5 | Pending |
| SLEEP-05 | Phase 5 | Pending |
| SLEEP-06 | Phase 5 | Pending |
| ANLY-02 | Phase 6 | Pending |
| ANLY-03 | Phase 6 | Pending |
| ANLY-04 | Phase 6 | Pending |
| ANLY-05 | Phase 6 | Pending |
| ANLY-06 | Phase 6 | Pending |

**Coverage:**
- v2.0 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---

*Requirements defined: 2026-04-24 (v1.0), 2026-06-10 (v2.0)*
*Last updated: 2026-06-10 after v2.0 roadmap creation*