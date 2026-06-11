# Feature Research

**Domain:** CGM Insights - Anomaly Detection, Sleep Analysis, Behavioral Patterns
**Researched:** 2026-06-10
**Confidence:** MEDIUM (wellness app context limits clinical research applicability)

## Executive Summary

This research covers three feature areas for CGM Insights v2.0: anomaly detection, sleep analysis, and behavioral pattern analysis. The findings draw from clinical diabetes management research, commercial wellness apps (Levels, GluTrend, January AI), and patient experience studies. Key insight: Most advanced CGM analytics are designed for medical/clinical contexts with labeled data (meals, insulin, activity). This project must work with glucose data alone, requiring adaptation of techniques and careful wellness-language positioning.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist after basic pattern detection (already built). Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Glucose Anomaly Alerts** | Dexcom/Abbott apps already surface "unusual" readings | MEDIUM | Must avoid alert fatigue; focus on actionable patterns not individual readings |
| **Overnight/Bedtime Summary** | Sleep is a known high-risk period; users want to know "did I stay in range overnight?" | LOW | Existing 10pm-6am window assumption is standard; provide aggregate stats |
| **Pattern Explanations** | Users want to understand *why* something is anomalous, not just that it is | MEDIUM | Wellness framing: "This reading is unusual for your typical Tuesday at 2pm" |
| **Day-Type Segmentation** | Weekday vs weekend is a natural categorization users intuitively understand | LOW | Research shows meaningful metabolic differences between weekdays/weekends |
| **Time-in-Pattern** | Extension of time-in-range concept; users expect richer metrics beyond TIR | MEDIUM | JMIR research validates this as clinically meaningful |
| **Consistency Scoring** | "How consistent am I?" is a natural user question after seeing patterns | MEDIUM | Research shows cross-day consistency varies significantly by glycemic status |

### Differentiators (Competitive Advantage)

Features that set the product apart from basic CGM apps. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Inferred Sleep Window Detection** | More accurate than fixed 10pm-6am assumption; detects individual sleep patterns from glucose stability | HIGH | Research shows glucose patterns during sleep are distinct; can detect sleep onset/offset from reduced variability and lower mean glucose |
| **Pattern Similarity Analysis** | "Your Tuesdays look similar to your Wednesdays, but different from weekends" - actionable behavioral insight | MEDIUM | Uses Dynamic Time Warping (DTW) or similar; research validates clustering approaches |
| **Anomaly Context Attribution** | Not just flagging anomalies, but suggesting likely causes from patterns | MEDIUM | Without meal/activity data, limited to temporal patterns: "This happened during a period where you're usually stable" |
| **Sliding Window Pattern Library** | Detect patterns at multiple time scales (30/60/120 min) with 5-min stepping | MEDIUM | GlucoNet research uses 180-min windows; sliding windows capture transient patterns fixed windows miss |
| **Cross-Day Consistency Metrics** | Quantify "how predictable is my glucose?" - valuable for understanding variability sources | MEDIUM | Functional ICC methodology from Nature research; fair/poor agreement common even in controlled subjects |
| **Anomaly Severity Scoring** | Rank anomalies by deviation magnitude and duration, not binary classification | MEDIUM | Isolation Forest approach from sensor failure research adapted for glucose |
| **Wellness Coaching Insights** | Template-based suggestions tied to detected patterns: "Consider a short walk after this meal window" | LOW-MEDIUM | Must use wellness language; no medical advice; January AI model: suggestions not prescriptions |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for wellness-focused CGM app.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Predictive Hypoglycemia Alerts** | Users want early warning | Medical claim; requires clinical validation; liability risk; alert fatigue if poorly calibrated | Focus on pattern-based insights: "Your glucose tends to drop in this time window on weekends" |
| **Anomaly Count/Score** | Simple metric for "how good am I doing?" | Arbitrary; penalizes normal glucose variability; may encourage gaming | Consistency score + time-in-pattern; focus on controllability not anomaly count |
| **Real-Time Anomaly Detection** | Continuous monitoring feels valuable | Computationally intensive; no real-time data pipeline in current architecture; alert fatigue risk | Batch analysis with next-upload processing; "Review your anomalies" dashboard |
| **Meal Detection from Glucose Spikes** | Users want to know "what did I eat that caused this?" | Without meal logging, false attribution risk; spikes have multiple causes; may suggest incorrect meal timing | Post-hoc pattern analysis: "This spike pattern is consistent with your typical post-7pm behavior" |
| **Sleep Quality Diagnosis** | Sleep is important and users want to improve it | Medical claim territory; sleep apnea/insomnia diagnosis outside scope | Sleep-adjacent glucose patterns: "Your overnight glucose was more variable on nights following late meals" |
| **Automated Alerts for Every Anomaly** | Proactive notification feels helpful | Alert fatigue is #1 UX issue in CGM research; users disable alerts; 55% recall with 2-3 false alarms over 10 days is acceptable | Aggregate anomaly summary: "3 unusual readings this week" with drill-down |

---

## Feature Dependencies

```
[Time-in-Range Metrics] (BUILT)
    └──requires──> [Glucose readings + range definitions]

[Time-of-Day Patterns] (BUILT)
    └──requires──> [Time-in-Range Metrics]

[Sleep Analysis]
    └──requires──> [Time-of-Day Patterns]
    └──requires──> [Time-in-Range Metrics]
    └──enhanced_by──> [Inferred Sleep Window Detection]

[Anomaly Detection]
    └──requires──> [Time-of-Day Patterns]
    └──requires──> [Day-of-Week Patterns]
    └──enhanced_by──> [Cross-Day Consistency Metrics]

[Cross-Day Consistency]
    └──requires──> [Time-of-Day Patterns]
    └──requires──> [Day-of-Week Patterns]

[Sliding Window Patterns]
    └──requires──> [Glucose readings at 5-min intervals]
    └──enhanced_by──> [Pattern Similarity Analysis]

[Pattern Similarity Analysis]
    └──requires──> [Sliding Window Patterns]

[Weekday vs Weekend Segmentation]
    └──requires──> [Day-of-Week Patterns]
    └──independent──> [Other analyses]

[Behavioral Pattern Insights]
    └──requires──> [Anomaly Detection]
    └──requires──> [Cross-Day Consistency]
    └──requires──> [Weekday vs Weekend Segmentation]
```

### Dependency Notes

- **Sleep Analysis requires Time-of-Day Patterns:** Sleep analysis builds on existing period-based analysis; the 10pm-6am fixed window is already available, enhanced analysis adds value
- **Anomaly Detection requires Pattern Baselines:** Can't detect anomalies without established "normal" patterns; requires both time-of-day AND day-of-week baselines
- **Pattern Similarity Analysis enhances Sliding Window Patterns:** Without similarity analysis, sliding windows just produce more segments; similarity gives them meaning
- **Behavioral Pattern Insights is a synthesis layer:** Combines anomaly detection, consistency metrics, and day-type segmentation into actionable insights

---

## MVP Definition

### v2.0 Launch With

Minimum viable for this milestone — what's needed to deliver value.

- [x] **Time-in-Range Metrics** — Already built; foundation for all analysis
- [x] **Time-of-Day Patterns (12 periods)** — Already built; required for anomaly detection
- [x] **Day-of-Week Patterns** — Already built; required for weekday/weekend segmentation
- [ ] **Sleep Analysis (Fixed Window)** — Aggregate overnight stats using existing 10pm-6am window; low complexity, high value
- [ ] **Anomaly Detection (Basic)** — Statistical outliers from established patterns; flag readings >2 SD from time-of-day/day-of-week mean
- [ ] **Weekday vs Weekend Segmentation** — Split existing pattern analysis by day type; research shows meaningful differences
- [ ] **Cross-Day Consistency Score** — Functional ICC approach; "how predictable is your glucose?" metric

### v2.1 Enhancement (Post-MVP)

Add after core anomaly/pattern features work.

- [ ] **Sliding Window Pattern Detection** — 30/60/120 min windows sliding every 5 min; captures transient patterns
- [ ] **Inferred Sleep Window Detection** — Detect actual sleep from glucose stability patterns; more accurate than fixed window
- [ ] **Pattern Similarity Clustering** — DTW-based similarity; "your Tuesdays look like your Wednesdays"
- [ ] **Anomaly Context Attribution** — Explain anomalies relative to patterns; "this happened during a usually-stable period"
- [ ] **Time-in-Pattern Metric** — Novel metric from JMIR research; percentage of time in identified pattern types

### Future Consideration (v3+)

Defer until core value is validated with users.

- [ ] **Anomaly Severity Scoring** — Rank anomalies by impact; focus user attention
- [ ] **Wellness Coaching Templates** — Actionable suggestions tied to detected patterns; requires careful wellness-language framing
- [ ] **Sleep Quality Correlation** — Link overnight glucose variability to next-day metrics; stay on wellness side of diagnosis line

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Sleep Analysis (Fixed Window) | HIGH | LOW | P1 |
| Weekday vs Weekend Segmentation | MEDIUM | LOW | P1 |
| Anomaly Detection (Basic) | HIGH | MEDIUM | P1 |
| Cross-Day Consistency Score | MEDIUM | MEDIUM | P1 |
| Sliding Window Patterns | MEDIUM | MEDIUM | P2 |
| Pattern Similarity Analysis | MEDIUM | MEDIUM | P2 |
| Inferred Sleep Window Detection | HIGH | HIGH | P2 |
| Anomaly Context Attribution | MEDIUM | MEDIUM | P2 |
| Time-in-Pattern Metric | LOW-MEDIUM | MEDIUM | P3 |
| Anomaly Severity Scoring | MEDIUM | MEDIUM | P3 |
| Wellness Coaching Templates | MEDIUM | LOW-MEDIUM | P3 |

**Priority key:**
- P1: Must have for v2.0 launch
- P2: Should have, add when P1 works
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Dexcom Clarity | Levels | January AI | GluTrend | Our Approach |
|---------|----------------|--------|------------|----------|---------------|
| Anomaly Detection | Pattern-based alerts | Trend insights | Glucose prediction | AI alerts | Pattern deviation scoring |
| Sleep Analysis | Day/night splits | Sleep + glucose integration | Meal impact on sleep | Overnight summary | Fixed window + inferred option |
| Time-in-Pattern | Time-in-range only | Habit scoring | Weekly targets | GluCoins gamification | Pattern type percentages |
| Consistency Metrics | Compare days | Trend consistency | Weekly review | GluShields badges | Cross-day ICC scoring |
| Meal Context | Manual logging | Photo + predicted glucose | AI food recognition | Meal photos | No meal data (constraint) |
| Activity Context | Manual/Apple Health | Fitness app integration | Activity tracking | Activity insights | No activity data (constraint) |
| Wellness Insights | Clinical reports | Habit programs | AI nutritionist | AI-powered suggestions | Template-based suggestions |

**Key Differentiation Opportunity:** Our constraint (glucose data only, no meals/activity) forces focus on pattern-based insights rather than correlation-based insights. This can be a strength: simpler data pipeline, clearer insights, no user burden of logging.

---

## Algorithmic Approaches (Research-Based)

### Anomaly Detection

| Approach | Source | Performance | Complexity | Wellness Applicability |
|----------|--------|-------------|------------|------------------------|
| **Statistical Outliers** (z-score from time-period mean) | Standard practice | Simple baseline | LOW | HIGH - transparent, explainable |
| **Isolation Forest** | University of Padova sensor failure research | 74% recall, 2-3 false alarms/10 days | MEDIUM | MEDIUM - good for unsupervised, but less interpretable |
| **Dynamic Mode Decomposition** | UVA meal detection research | 89%+ detection for significant events | HIGH | LOW - overkill for wellness, better for clinical |
| **Pattern Deviation Scoring** | JMIR Time-in-Patterns research | Validated for clinical use | MEDIUM | HIGH - ties directly to pattern analysis |

**Recommendation:** Start with statistical outliers (z-score from established patterns) as baseline. Isolation Forest is well-supported for CGM data but requires more infrastructure. Pattern deviation scoring from JMIR research integrates naturally with existing pattern detection.

### Sleep Analysis

| Approach | Source | Performance | Complexity | Notes |
|----------|--------|-------------|------------|-------|
| **Fixed Time Window** (10pm-6am) | Common practice | Baseline | LOW | Already planned; good starting point |
| **Glucose Stability Detection** | Sleep research shows ~16% glucose decrease in first 5h | Correlates with actigraphy | MEDIUM | Detect sleep onset from reduced variance + lower mean |
| **Variability-Based Sleep Detection** | Midpoint = min variability | Strong correlation (r=0.85) with HbA1c | MEDIUM | Midnight is typically min variability; can infer sleep quality |

**Recommendation:** v2.0 ships with fixed 10pm-6am window. v2.1 can add glucose stability detection for inferred sleep windows if users want more personalization.

### Cross-Day Consistency

| Approach | Source | Performance | Notes |
|----------|--------|-------------|-------|
| **Functional ICC** | Nature Scientific Reports 2023 | ICC 0.30-0.46 (poor-fair) in normative data | Provides actual reproducibility metric |
| **Day-to-Day Correlation** | Simple Pearson between same time periods | Easy to implement | Less sophisticated but interpretable |
| **Pattern Similarity (DTW)** | JMIR research | Clusters patients into 4 meaningful groups | More complex, requires pattern library |

**Recommendation:** Functional ICC is most rigorous but may be overkill. Start with day-to-day correlation (how similar is Tuesday 2pm to Wednesday 2pm?), which is interpretable and aligns with user mental model.

### Weekday vs Weekend

| Finding | Source | Implication |
|---------|--------|-------------|
| Weekends have higher glucose than weekdays | Multiple studies (Gecili, Clemmensen) | Separate analysis is meaningful |
| Mondays show 17-18% higher fasting insulin | Clemmensen 2022 | "Social jetlag" from weekend affects Monday readings |
| Sunday = highest average glucose | Miller 2025 | End-of-week pattern; may reflect relaxation of routines |

**Recommendation:** Weekday vs weekend segmentation is simple to implement and has clear user-facing justification. Can extend to day-of-week patterns (e.g., "Your Mondays are different from your Tuesdays") in v2.1.

---

## Wellness Language Guidelines (Regulatory Compliance)

Based on competitor analysis (January AI, Levels, GluTrend), the following framing keeps insights on the wellness side:

| Avoid (Medical) | Use Instead (Wellness) |
|------------------|----------------------|
| "You are experiencing hypoglycemia" | "Your glucose is lower than your typical range" |
| "This indicates insulin timing issues" | "This pattern often relates to meal timing" |
| "Anomalous readings may indicate..." | "This reading is unusual for your patterns" |
| "You should adjust your insulin..." | "Consider discussing this pattern with your care team" |
| "This is a symptom of..." | "This is associated with..." |
| "Diagnosis: Sleep apnea" | "Your overnight glucose patterns show more variability than typical" |

**Key Principle:** Describe observations and patterns, not medical conditions. Use "associated with," "correlated with," "often relates to" rather than causal language.

---

## Technical Implementation Notes

### Anomaly Detection Pipeline

1. **Pattern Establishment Phase:** Require minimum 7-14 days of data to establish patterns
2. **Baseline Calculation:** For each time-of-day period + day-of-week combination, calculate mean and SD
3. **Anomaly Scoring:** Flag readings >2 SD from baseline as "unusual"
4. **Aggregation:** Group anomalies by day, type, and context for user review
5. **Alert Fatigue Prevention:** Only surface aggregate summaries ("3 unusual readings this week"), not individual alerts

### Sleep Analysis Implementation

1. **Fixed Window (v2.0):** Extract 10pm-6am readings, calculate TIR, mean, SD, CV
2. **Basic Insights:** Compare weekday vs weekend overnight patterns
3. **Inferred Sleep (v2.1):** Detect sleep onset from glucose stability (reduced variance + decreasing trend)

### Cross-Day Consistency Implementation

1. **Correlation Method:** For each time-of-day period, calculate Pearson correlation between days
2. **Consistency Score:** Aggregate across all periods into single "predictability" score (0-100%)
3. **Interpretability:** "Your glucose patterns are [highly/moderately/less] consistent from day to day"

---

## Sources

**Anomaly Detection:**
- [Dynamic Mode Decomposition for Meal Detection (arXiv 2507.00080)](https://arxiv.org/pdf/2507.00080) - UVA meal detection research
- [Unsupervised Detection of Sensor Failures (University of Padova)](https://www.research.unipd.it/handle/11577/3540043) - Isolation Forest for CGM anomaly detection
- [Machine Learning Time in Patterns (JMIR AI 2023)](https://ai.jmir.org/2023/1/e45450) - DTW-based pattern recognition

**Sleep Analysis:**
- [Sleep Quality and Glycemic Variability (Diabetologia 2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9254230/) - EEG-based sleep + CGM correlation
- [Sleep Variability and Time-in-Range (Sleep Health 2023)](https://www.sciencedirect.com/science/article/abs/pii/S2352721823001407) - Weekday/weekend sleep impact
- [Modeling CGM During Sleep (Biostatistics 2022)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8942115/) - Glucose decreases 16% in first 5h of sleep

**Cross-Day Consistency:**
- [CGM Reproducibility Under Real-Life Conditions (Nature 2023)](https://www.nature.com/articles/s41598-023-40949-1.pdf) - Functional ICC methodology
- [Temporal Glycemic Patterns (NSF Public Access)](https://par.nsf.gov/biblio/10616916-temporal-glycemic-patterns-type-type-diabetes-insights-from-extended-continuous-glucose-monitoring) - Day-of-week patterns

**Weekday/Weekend Patterns:**
- [Weekday Variation on Glucose (Maastricht Study 2022)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9797041/) - Monday effect on metabolism
- [Functional Data Analysis for CGM (Cambridge Journals)](https://www.cambridge.org/core/journals/journal-of-clinical-and-translational-science/article/functional-data-analysis-and-prediction-tools-for-continuous-glucosemonitoring-studies/086968798CACBCA27E4954283E1AAC0A) - FPCA for temporal patterns

**User Experience/Alert Design:**
- [CGM Alert Experience Study (Radian 2024)](https://www.weareradian.com/cgm-study-alerts) - Alert fatigue, false alarms, UX issues
- [Designing CGM Experience (PMC 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10899853/) - User needs hierarchy for alerts

**Competitor Analysis:**
- [Gluroo Dec 2024 Features](https://gluroo.com/blog/releases/gluroo-dec-2024-feature-release-better-charts-heads-up-display-daily-view-and-health-care-provider-support/)
- [Levels Metabolic Health](https://www.levels.com/)
- [January AI App Store](https://apps.apple.com/us/app/january-glucose-food-tracker/id6470235391)
- [Dexcom G7 Features](https://www.dexcom.com/en-us/all-access/dexcom-cgm-explained/new-g7-app-features)
- [Tidepool Trends](https://support.tidepool.org/hc/en-us/articles/360029760391-Viewing-Diabetes-Data-Trends-CGM)

---
*Feature research for: CGM Insights v2.0 - Anomaly Detection, Sleep Analysis, Behavioral Patterns*
*Researched: 2026-06-10*