# Feature Landscape

**Domain:** CGM Analytics Application
**Researched:** 2026-04-23

## Table Stakes

Features users expect. Missing these makes the product feel incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Time-in-Range (TIR)** | Core CGM metric, every app shows this | Low | Standard calculation: % time in 70-180 mg/dL. Must include all 5 ranges (very low, low, target, high, very high) |
| **Average Glucose** | Basic summary statistic | Low | Mean of all readings with standard deviation |
| **Glucose Management Indicator (GMI)** | Users want A1C estimate | Low | Formula: GMI (%) = 3.31 + 0.02392 x mean glucose. **Caveat:** Only ~61% match within 0.5%, tends to overestimate in low A1C, underestimate in high A1C |
| **Coefficient of Variation (%CV)** | Standard variability metric | Low | Target <36%. Higher CV correlates with 2.5x hypoglycemia risk regardless of A1C |
| **Date Range Selection** | Users need to analyze specific periods | Low | Common ranges: 7, 14, 30, 90 days. Must allow custom ranges |
| **Glucose Trend Graph** | Visual pattern recognition is universal | Medium | Time-series with color-coded zones. 5-min interval granularity standard |
| **File Upload/Import** | Primary data entry method | Medium | Users expect simple drag-drop or file selection. Sugarmate exports are Excel format |
| **AGP Report Export** | Clinical standard for healthcare visits | Medium | Single-page standardized format. Expected for sharing with doctors |
| **Time Below/Above Range** | Safety-critical metrics | Low | % time <70 mg/dL (low) and <54 mg/dL (very low). Medical standard |

## Differentiators

Features that set products apart. Not universally expected, but highly valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Pattern Detection (Time-of-Day)** | Identifies recurring problem times | Medium-High | "You consistently spike at 3pm" - most users cannot see this themselves from raw graphs |
| **Pattern Detection (Day-of-Week)** | Identifies weekly patterns | Medium | Weekend vs weekday differences, specific problematic days |
| **Post-Meal Analysis** | Connects food to glucose impact | Medium-High | Requires meal logging OR meal detection algorithm. Levels scores meals 1-10 based on glucose response |
| **Anomaly Detection (Unexplained Events)** | Surfaces hidden problems | High | Unexplained highs/lows when no food/insulin/activity logged. Critical for identifying sensor errors, stress responses, or health issues |
| **Actionable Recommendations** | Translates data into action | High | Generic ("exercise more") vs specific ("10-min post-meal walk is more effective than 45-min gym session for your glucose"). Levels, Gheware lead here |
| **Sleep-Glucose Correlation** | Novel insight most apps miss | Medium | Gheware differentiator: "Less than 6 hours sleep increases your variability by 31%" |
| **Multi-Factor Analysis** | Connects glucose to lifestyle | High | Correlating CGM with sleep, activity, stress. Most apps show glucose only; advanced platforms show "why" |
| **Glucose Prediction (4-hour window)** | Proactive, not reactive | High | GlucoSenseDigital and DiabTrend offer 4-hour predictions. Uses LSTM/RNN models |
| **Meal Scoring** | Simplifies complex data | Medium | Levels 1-10 score: Glucose increase + slope + area under curve. Users love simple scores over complex metrics |
| **Best Day Analysis** | Positive framing helps motivation | Low-Medium | Dexcom Clarity feature: Shows your best day as a benchmark for achievable control |
| **Comparative Periods** | Progress tracking | Low-Medium | Side-by-side comparison of date ranges. "This month vs last month" |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time CGM connection (v1)** | Adds significant complexity, requires OAuth/API integrations with Dexcom/Libre, creates reliability dependency on third-party APIs. File imports cover 90% of use cases. | Focus on file upload. Leave real-time for v2+ |
| **Insulin Dosing Recommendations** | Medical liability. Requires FDA clearance as medical device. High regulatory burden. | Provide glucose insights only. Include disclaimer: "Not medical advice" |
| **Carb Counting/Food Database** | Crowded space (MyFitnessPal, Cronometer, etc.). Food entry is tedious and users often already have a preferred tool. | Accept manual meal logging with time stamp. Focus on analyzing impact, not food database |
| **Prescriptive Alerts ("Eat now!")** | Annoying, creates alert fatigue, often wrong. Users hate intrusive notifications. | Show patterns passively. Let users set their own goals and check the app when they want |
| **Perfect A1C Estimation Claims** | GMI is inaccurate for 25-30% of users. Claiming accuracy erodes trust when wrong. | Present GMI as "estimated" with caveats. Reference that differences up to 1% are common |
| **Complicated Data Entry** | #1 complaint in diabetes app research. Users abandon apps that require many steps to log data. | Automatic import from file. Minimal manual entry. Single-click actions where possible |
| **Paywalled Essential Reports** | Users feel cheated when basic features require payment. | Core metrics free. Advanced analytics can be premium |
| **English-Only Without Cultural Adaptation** | 41% of studies identified non-personalized content as a barrier. Food, measurements, cultural context vary. | Plan for internationalization from start. Use metric/imperial toggle. Avoid US-centric examples |

## Feature Dependencies

```
File Upload/Import
    |
    v
Data Validation & Parsing
    |
    v
Time-in-Range / Average Glucose / GMI / %CV  <-- All table stakes depend on clean data
    |
    v
Pattern Detection (Time-of-Day, Day-of-Week)
    |
    +---> Anomaly Detection (requires pattern baseline)
    |
    +---> Comparative Periods (requires historical data)

Post-Meal Analysis
    |
    +---> Meal Scoring (requires post-meal analysis)

Multi-Factor Analysis (Sleep, Activity)
    |
    +---> Actionable Recommendations (requires multiple data sources)
```

## MVP Recommendation

**Prioritize (Phase 1):**
1. File upload/import (Sugarmate Excel format)
2. Data validation and parsing
3. Core metrics: TIR, Average Glucose, GMI, %CV
4. Glucose trend graph with date range selection
5. AGP report export

**Defer (Phase 2):**
- Pattern detection (time-of-day, day-of-week)
- Comparative periods

**Defer (Phase 3):**
- Post-meal analysis (requires meal logging)
- Anomaly detection
- Actionable recommendations

## Competitive Feature Matrix

| Feature | Dexcom Clarity | LibreView | Levels | Nightscout | Sugarmate |
|---------|---------------|-----------|--------|------------|-----------|
| Time-in-Range | Yes | Yes | Yes | Yes | Yes |
| GMI | Yes | Yes | Yes | Yes | Yes |
| Pattern Detection | 4 patterns | Daily patterns | Meal scores | Manual reports | Basic |
| Anomaly Detection | No | No | Yes (AI) | No | No |
| Actionable Recommendations | Limited | No | Yes (AI) | No | No |
| AGP Report | Yes | Yes | No | Yes (via plugin) | No |
| Sleep Correlation | No | No | Yes | Via integration | No |
| File Import | No (device only) | No (device only) | No (device only) | Yes | N/A (is the device app) |
| Open Source | No | No | No | Yes | No |

## Key Insights from Research

### What Users Actually Want (from usability studies)

1. **Automatic data upload** - The #1 desired feature. Manual entry is a friction point.
2. **Clear visual reports** - Color-coded graphs that are easy to interpret at a glance.
3. **In-app help** - Users struggle to understand metrics. Tutorials and contextual help reduce abandonment.
4. **Healthcare sharing** - Direct export or sharing with doctors is highly valued.

### What Users Hate (from app store reviews and studies)

1. **Data entry burden** - 54.3% negative reviews related to device integration issues. Apps that require manual entry are abandoned.
2. **"Fat finger phenomenon"** - Small buttons leading to incorrect entries.
3. **Complicated save steps** - Users forget to save and lose data.
4. **Paywalls on basic features** - Feels exploitative.
5. **Unreliable notifications** - Safety-critical for CGM users. Broken alerts = dangerous.
6. **Apps that "stand alone"** - Users want connection to healthcare providers, not isolation.

### Pattern Detection Algorithms (Technical Notes)

For anomaly/pattern detection, proven approaches include:

| Algorithm | Use Case | Performance |
|-----------|----------|-------------|
| Template Matching | Meal detection | F1 = 0.90, 0.78 false positives/day |
| Isolation Forest | Anomaly detection | 75% sensitivity, 0.08 false positives/day |
| RUSBoost (Ensemble) | Hypoglycemia prediction | AUC = 0.988, 17.5 min lead time |
| Random Forest | Meal pattern classification | F1 = 0.83 |

**Key insight:** Personalization is critical. All successful approaches emphasize personalizing detection algorithms to individual glucose response patterns.

## Sources

### Primary Sources (HIGH confidence)
- [Dexcom Clarity Reports](https://dexcom.com/en-gb/healthcare-professionals/faqs/what-reports-can-i-view-in-dexcom-clarity) - Official Dexcom documentation
- [AGP Report Standard](http://www.agpreport.org/agp/agpreports) - International consensus standard
- [GMI Research (Bergenstal et al.)](https://ncbi.nlm.nih.gov/pmc/articles/PMC6196826/) - Original GMI validation study
- [cgm_format Library](https://github.com/GlucoseDAO/cgm_format) - Open source CGM data normalization
- [iglu R Package](https://irinagain.github.io/iglu/index.html) - Academic CGM analysis library

### Secondary Sources (MEDIUM confidence)
- [Levels Zone Scores](https://support.levels.com/article/32-zone-scores) - Meal scoring methodology
- [Nightscout Reports](https://nightscout.github.io/nightscout/reports) - Open source analytics features
- [Diabetes App Usability Study (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8349717/) - Systematic review of app problems
- [Gheware Features](https://gheware.com/) - AI-powered analytics platform
- [GlucoSenseDigital](https://glucosensedigital.com/features/) - AI forecasting features

### Research Papers (MEDIUM confidence)
- Meal Detection Algorithms: [Nature Scientific Reports 2025](https://www.nature.com/articles/s41598-025-92275-3), [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10709931/)
- Anomaly Detection: [PMC9294564](https://pmc.ncbi.nlm.nih.gov/articles/PMC9294564/), [Frontiers](https://www.frontiersin.org/journals/clinical-diabetes-and-healthcare/articles/10.3389/fcdhc.2022.1066744/full)
- Glucose Variability: [Frontiers Physiology](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2018.01257/full)

### App Comparisons (LOW confidence - marketing materials)
- [CGM Comparison 2026](https://optimizebiomarkers.com/cgm) - Market comparison
- [Best Diabetes Apps](https://iheald.com/blog/best-diabetes-management-apps-2026) - Consumer comparison