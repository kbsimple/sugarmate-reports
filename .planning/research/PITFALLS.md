# Pitfalls Research

**Domain:** CGM Analytics - Anomaly Detection, Sleep Analysis, Behavioral Pattern Analysis
**Researched:** 2026-06-10
**Confidence:** HIGH (peer-reviewed research + existing codebase analysis)

---

## Executive Summary

This research covers pitfalls specific to adding **anomaly detection (ANLY-02)**, **sleep analysis (ANLY-03)**, and **behavioral pattern analysis** to an existing CGM analytics system. The foundational pitfalls (regulatory boundaries, data quality, CGM lag) remain critical but are documented separately. This document focuses on **integration-specific pitfalls** for v2.0 features.

---

## Critical Pitfalls

Mistakes that cause rewrites, incorrect insights, or regulatory issues.

### Pitfall 1: Pressure-Induced Sensor Attenuation (PISA) Misinterpreted as Anomaly

**What goes wrong:**
Anomaly detection flags false lows during sleep as "unusual glucose events" when they're actually sensor artifacts from sleeping on the CGM sensor. Users see "anomalies" that don't represent real glucose patterns.

**Why it happens:**
- PISA affects ~3% of overnight CGM readings (Baysal et al., 2014)
- When sleeping on the sensor side, 32.4% of readings show excursions >25 mg/dL (Mensh et al., 2013)
- Effects persist 30-90 minutes after position change
- PISA causes false low readings (glucose-oxidase reaction affected by reduced blood flow and oxygen tension)
- Without meal/activity/sleep data, there's no way to know if a low reading is real or artifact

**Consequences:**
- Users receive incorrect "anomaly" alerts for non-existent events
- Trust in anomaly detection erodes after repeated false positives
- Overnight pattern analysis corrupted by artifact data
- Inappropriate wellness suggestions based on sensor errors

**Prevention:**
1. Implement PISA detection algorithm checking for:
   - Sudden glucose drops exceeding physiological rate-of-change (>2 mg/dL/min sustained)
   - Recovery pattern after artifact resolves
   - Timing correlation with likely sleep periods (10pm-6am)
2. Label detected PISA events separately from behavioral anomalies
3. Use wellness language: "sensor readings during sleep may include artifacts from sleeping position"
4. Exclude likely PISA periods from pattern calculations

**Detection:**
- Overnight "anomalies" that cluster around expected sleep times
- Rate of change >2 mg/dL/min downward followed by rapid recovery
- Users reporting "impossible" low glucose values overnight
- Anomaly detection showing higher false positive rates overnight

**Phase to address:** ANLY-02 (Anomaly Detection)

---

### Pitfall 2: Fixed Sleep Window (10pm-6am) Misidentifies Actual Sleep

**What goes wrong:**
Analysis assumes all readings between 10pm-6am are "sleep" when actual sleep times vary dramatically. Night shift workers, early risers, and irregular sleepers have their daytime glucose patterns misclassified as "overnight."

**Why it happens:**
- Fixed 10pm-6am window is a convenience assumption, not validated against actual sleep
- Sleep onset can range from 9pm to 2am+ across populations
- Wake times range from 4am to 9am+
- ~20-30% of adults have irregular sleep schedules
- No actigraphy or self-reported sleep times available

**Consequences:**
- "Sleep" analysis shows high variability (should be lower during actual sleep)
- Multiple meals/activity patterns appearing in "overnight" data
- Users questioning why their 11pm snack shows up in "sleep" analysis
- Cross-day consistency poor for "sleep" patterns

**Prevention:**
1. Label findings clearly: "10pm-6am window" NOT "overnight" or "sleep"
2. Consider alternative sleep inference methods:
   - Lowest glucose variability periods (stable glucose suggests sleep)
   - Rate-of-change analysis (glucose changes slow during sleep)
   - Multi-day baseline comparison (consistency suggests pattern)
3. Flag results when sleep window assumption likely violated:
   - High variability in presumed sleep period
   - Glucose patterns inconsistent with typical sleep behavior
4. Provide user configuration for custom sleep windows

**Detection:**
- "Sleep" analysis showing CV >30% (unusual for actual sleep)
- Users reporting that "sleep" patterns don't match their actual sleep times
- Cross-day consistency metrics poor for "overnight" period

**Phase to address:** ANLY-03 (Sleep Analysis)

---

### Pitfall 3: Anomaly Detection Thresholds Not Personalized

**What goes wrong:**
Anomaly detection generates too many false positives for high-variability users, or misses real anomalies for stable users. One-size-fits-all thresholds fail across diverse glucose patterns.

**Why it happens:**
- Physiological glucose rate of change varies: 75% of time <1 mg/dL/min, but ~8% >2 mg/dL/min
- Aggressive settings: 88% detection rate but 7% false positive rate
- Cautious settings: 64% detection rate but 1.7% false positive rate
- No single threshold works for all users (personalization needed)
- What's "anomalous" for one person may be normal for another

**Consequences:**
- Users with higher baseline variability get excessive flags
- Stable users miss meaningful anomalies
- Alert fatigue from false positives
- Erosion of trust in anomaly detection

**Prevention:**
1. Use multi-tier anomaly classification:
   - Tier 1 (Physiologically implausible): Rate >5 mg/dL/min — very likely artifact
   - Tier 2 (Unusual for user): >2 std dev from user's personal baseline
   - Tier 3 (Outside established pattern): Time-of-day deviation >20% from pattern
2. Require minimum occurrences before flagging:
   - Single occurrence: "notable"
   - 2+ occurrences: "pattern deviation"
   - 5+ occurrences: "anomaly"
3. Separate artifact detection from behavioral anomalies
4. Use wellness language: "unusual reading" not "anomaly" or "abnormal"

**Detection:**
- Users ignoring or disabling alerts
- High proportion of flagged anomalies that user dismisses
- False positives concentrated in specific time periods
- Users with higher baseline variability getting more flags

**Phase to address:** ANLY-02 (Anomaly Detection)

---

### Pitfall 4: Wellness Language Accidentally Crosses Medical Device Line

**What goes wrong:**
Feature descriptions or output language inadvertently triggers FDA medical device classification, requiring regulatory compliance.

**Why it happens:**
- "Anomaly detection" sounds like disease screening
- "Sleep analysis" implies clinical diagnosis of sleep disorders
- Presenting data as percentages and thresholds looks clinical
- Users naturally interpret pattern findings as health recommendations
- Disclaimers like "not medical advice" don't protect — FDA looks at actual behavior

**Consequences:**
- FDA enforcement action requiring app modification or removal
- Legal liability if users make medical decisions based on app output
- Required premarket approval (510(k) or PMA)
- Potential criminal penalties for unauthorized medical device distribution

**Prevention:**
Use wellness-framed language throughout:

| Avoid | Use Instead |
|-------|-------------|
| "Anomaly detected" | "Unusual pattern observed" |
| "Sleep analysis" | "10pm-6am window analysis" |
| "Abnormal glucose" | "Glucose outside your typical range" |
| "Risk assessment" | "Pattern summary" |
| "Diagnose" | "Identify patterns" |
| "Predict" | "Observe trends" |
| "Should" | "Consider" |
| "Medical condition" | "Health pattern" |

**Additional safeguards:**
1. Frame as observations, not diagnoses:
   - "Your glucose at noon tends to be 15% higher than your average"
   - NOT: "You have post-meal hyperglycemia"
2. Keep recommendations lifestyle-focused:
   - "Consider discussing patterns with your healthcare team"
   - NOT: "Reduce carbohydrate intake at breakfast"
3. Avoid clinical thresholds in recommendations
4. Present data, don't tell user what to do about it

**Detection:**
- Language audit for disease-specific claims
- Review all user-facing text for medical framing
- Legal review of feature descriptions

**Phase to address:** All phases (ongoing review)

---

### Pitfall 5: Sliding Window Computational Complexity Explodes

**What goes wrong:**
Computing 30/60/120 minute windows starting every 5 minutes for all 288 daily readings creates massive data volume and slow performance. For 14 days: 288 windows/day x 3 window sizes x 14 days = 12,096 window calculations per metric.

**Why it happens:**
- Naive sliding window: O(n * W) where n = readings, W = window size
- 5-minute intervals with overlapping windows means almost complete data overlap
- Each reading is part of multiple windows simultaneously
- Computing each window independently wastes computation

**Consequences:**
- Analysis taking >1 second for typical dataset
- Memory usage growing linearly with data size
- Performance degrading exponentially with window count
- Users experiencing lag when viewing results

**Prevention:**
1. Use incremental window algorithms:
   - Sum: Add new reading, subtract evicted reading — O(1) per window
   - Average: Maintain running sum and count — O(1) per window
   - Standard deviation: Maintain running sum, sum of squares, count — O(1) per window

2. Implement ring buffer for sliding windows:
   ```python
   class IncrementalWindow:
       def __init__(self, size_minutes: int, interval_minutes: int = 5):
           self.size = size_minutes // interval_minutes
           self.buffer = [0.0] * self.size
           self.sum = 0.0
           self.count = 0
           self.position = 0

       def add(self, value: float):
           evicted = self.buffer[self.position]
           self.sum = self.sum - evicted + value
           self.buffer[self.position] = value
           self.position = (self.position + 1) % self.size
           self.count = min(self.count + 1, self.size)
           return self.sum / self.count if self.count > 0 else 0
   ```

3. Compute windows only when needed (lazy evaluation)
4. For anomaly detection: compute baseline once per time period, compare individual readings

**Detection:**
- Performance tests with max dataset size (14+ days)
- Memory profiling for sliding window operations
- Timing analysis showing O(n) not O(n*W)

**Phase to address:** Behavioral Pattern Analysis (sliding windows)

---

## Moderate Pitfalls

### Pitfall 6: Cross-Day Pattern Consistency Overstated

**What goes wrong:**
Analysis assumes patterns are consistent across days when research shows significant variability. Users receive misleading "consistent pattern" insights.

**Why it happens:**
- ICC (intraclass correlation coefficient) for glucose reproducibility: 0.30-0.46 (poor to fair)
- Day-of-week patterns vary significantly: Sunday highest glucose, Wednesday lowest
- Seasonal variations: November-February worst control, April-August best
- Holidays show 5-8% decreases in time-in-range
- Weekend behavior differs from weekday (2-hour delay in glucose control window)

**Consequences:**
- Pattern insights that don't match user's actual experience
- Inconsistent recommendations week-to-week
- User confusion when "pattern" doesn't hold

**Prevention:**
1. Separate weekday vs weekend analysis
2. Include confidence intervals on patterns
3. Require minimum occurrences (3+ days) before reporting pattern
4. Flag patterns with high variability
5. Label seasonal context when applicable

**Detection:**
- Pattern confidence intervals overlapping significantly
- User reports that patterns "don't hold"
- Week-to-week pattern variability >20%

**Phase to address:** Behavioral Pattern Analysis

---

### Pitfall 7: Missing PISA Artifacts in Pattern Calculations

**What goes wrong:**
Pattern detection includes PISA artifacts as legitimate data, corrupting time-of-day and overnight patterns.

**Why it happens:**
- PISA artifacts look like real low glucose readings
- No explicit PISA detection before pattern analysis
- Artifacts concentrated in overnight hours (sleeping on sensor)
- Existing codebase does not filter PISA events

**Consequences:**
- "Morning glucose tends to be lower" when actually PISA artifacts
- False overnight hypoglycemia patterns
- Incorrect recommendations based on artifact data

**Prevention:**
1. Run PISA detection before pattern analysis
2. Exclude flagged PISA periods from aggregations
3. Mark pattern confidence lower when potential artifacts detected
4. Include PISA flag in data quality assessment

**Detection:**
- Overnight patterns showing unexpectedly low glucose
- Time-of-day patterns that don't match user's reported experience
- Pattern detection in existing codebase: verify artifact handling

**Phase to address:** ANLY-02 (Anomaly Detection) + ANLY-03 (Sleep Analysis)

---

## Minor Pitfalls

### Pitfall 8: Confusing Artifact Detection with Anomaly Detection

**What goes wrong:**
Development treats PISA/artifact detection as the same problem as behavioral anomaly detection, leading to incorrect algorithm selection.

**Why it happens:**
- Both involve identifying "unusual" readings
- Artifact detection: sensor errors, physiological implausibility
- Anomaly detection: behavioral outliers outside user's normal patterns
- Different algorithms optimal for each

**Consequences:**
- Wrong thresholds for each problem
- Artifacts flagged as behavioral anomalies
- Real anomalies missed because filtered as "artifacts"

**Prevention:**
1. Separate artifact detection from anomaly detection
2. Use different thresholds:
   - Artifact: physiological rate of change (>2-5 mg/dL/min)
   - Anomaly: statistical deviation from personal baseline (>2 std dev)
3. Process pipeline: artifact detection → clean data → pattern analysis → anomaly detection
4. Document which problem each algorithm addresses

**Phase to address:** ANLY-02 (Anomaly Detection)

---

### Pitfall 9: Over-Engineering for Theoretical Scale

**What goes wrong:**
Implementing complex algorithms for scale that won't be reached, delaying time-to-market for minimal benefit.

**Why it happens:**
- Premature optimization for millions of users
- Implementing distributed processing for single-user analysis
- Building real-time systems for batch file uploads

**Consequences:**
- Increased complexity and maintenance burden
- Delayed feature delivery
- Over-engineered code that's harder to debug

**Prevention:**
1. Optimize for current scale (14-day uploads, single user)
2. Design interfaces for future scaling, but implement simple first
3. Performance test at 10x expected load, not 1000x
4. Document scaling considerations for future phases

**Phase to address:** All phases (engineering judgment)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Fixed 10pm-6am sleep window | Fast implementation | Misclassifies ~30% of users | MVP only — label clearly |
| Naive sliding window | Simpler code | O(n*W) performance, scales poorly | MVP only — must refactor |
| Single anomaly threshold | Simpler logic | False positives/negatives | Never — must personalize |
| Skip PISA detection | Faster time-to-market | False anomalies erode trust | Never — critical for accuracy |
| Population baselines | No personalization needed | Irrelevant for many users | Never — must be personal |
| No artifact filtering | Simpler pipeline | Corrupted patterns | Never — critical for accuracy |

---

## Integration Gotchas

Common mistakes when connecting to existing system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Existing patterns.py | Duplicate time-of-day logic in sliding windows | Extend existing `_group_by_time_period` for sliding windows |
| GlucoStats | Assume it handles all CGM analysis | Use for metrics (TIR, CV, GMI), custom logic for patterns |
| Wellness language | Add disclaimers as afterthought | Bake wellness framing into all output from design |
| Baseline comparison | Use population baselines | Always compute personal baseline from user's data |
| Data quality | Assume validation handled upstream | Re-validate before anomaly/sleep analysis |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Naive sliding window | O(n*W) performance | Use incremental O(1) algorithms | >1000 readings with multiple windows |
| Recomputing baselines | Analysis slow on repeated calls | Cache baseline calculations | Each analysis call |
| Per-reading anomaly flags | Excessive memory | Aggregate anomalies by time period | Large datasets |
| No window size limits | Memory explosion | Cap window sizes at 180 minutes | Users requesting larger windows |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Anomaly Detection:** Often missing PISA filtering — verify overnight anomalies aren't sensor artifacts
- [ ] **Sleep Analysis:** Often missing user-configurable sleep window — verify "10pm-6am" is labeled, not "sleep"
- [ ] **Sliding Windows:** Often missing incremental optimization — verify O(1) per window, not O(W)
- [ ] **Wellness Language:** Often missing in technical error messages — verify ALL user-facing text
- [ ] **Baseline Comparison:** Often missing personalization — verify baseline is computed from user's own data
- [ ] **Cross-Day Consistency:** Often missing weekday/weekend separation — verify patterns account for day-type differences
- [ ] **Pattern Confidence:** Often missing confidence intervals — verify patterns show certainty level

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| PISA not detected | MEDIUM | Add PISA detection module, reprocess historical data, re-issue insights |
| Fixed sleep window confusion | LOW | Update labeling in all output, add user configuration option |
| Aggressive thresholds | MEDIUM | Adjust thresholds based on user feedback, add personalization layer |
| Wellness language crossed | HIGH | Audit all output text, potentially redesign UI, may need legal review |
| Sliding window performance | MEDIUM | Refactor to incremental algorithm, may need architecture change |
| Cross-day consistency poor | LOW | Add confidence intervals, separate weekday/weekend analysis |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| PISA misinterpretation | ANLY-02 (Anomaly Detection) | Test with known PISA data, verify artifacts flagged separately |
| Fixed sleep window | ANLY-03 (Sleep Analysis) | Verify labeling says "10pm-6am window" not "sleep", test with edge cases |
| Aggressive thresholds | ANLY-02 (Anomaly Detection) | Test with high-variability users, verify personalization |
| Wellness language crossing | All phases (ongoing) | Manual review of all output text, verify wellness framing |
| Sliding window performance | Behavioral Pattern Analysis | Performance test with max dataset size (14+ days), verify O(n) not O(n*W) |
| Missing cross-day patterns | Behavioral Pattern Analysis | Verify weekday/weekend separation, test with known holiday data |
| PISA in pattern calculations | ANLY-02 + ANLY-03 | Verify PISA periods excluded from pattern aggregations |

---

## Sources

### Anomaly Detection & PISA
- [Novel Method to Detect Pressure-Induced Sensor Attenuations (PISA)](https://journals.sagepub.com/doi/10.1177/1932296814553267) — Baysal et al., Journal of Diabetes Science and Technology (2014) — HIGH confidence
- [Susceptibility of CGM Performance to Sleeping Position](https://pmc.ncbi.nlm.nih.gov/articles/PMC3879750/) — Mensh et al. (2013) — HIGH confidence
- [Unsupervised Detection of Pressure-Induced Failures in CGM Sensors](https://www.research.unipd.it/handle/11577/3540043) — University of Padua (2024) — HIGH confidence
- [Accuracy Requirements for Hypoglycemia Detector](https://pubmed.ncbi.nlm.nih.gov/19885133/) — Research on MARD requirements — HIGH confidence
- [Critical Discussion of Alert Evaluations in CGM](https://pmc.ncbi.nlm.nih.gov/articles/PMC11307228/) — Episode vs value-based approaches — HIGH confidence

### Sleep Inference
- [Modeling CGM Data During Sleep](https://pmc.ncbi.nlm.nih.gov/articles/PMC8942115/) — Gaynanova et al., Biostatistics (2020) — HIGH confidence
- [Nocturnal Glucose Prediction Using ML/DL](https://www.mdpi.com/2075-4418/14/7/740) — Kozinetz et al., Diagnostics (2024) — HIGH confidence
- [Predicting Nocturnal Hypoglycemia in Adults with T1D](https://www.mdpi.com/1424-8220/20/6/1705) — MDPI Sensors (2020) — HIGH confidence

### Sliding Window Algorithms
- [Maintaining Stream Statistics over Sliding Windows](https://moodle2.units.it/pluginfile.php/718390/mod_resource/content/0/Stream_statistics_sliding_window.pdf) — Datar, Gionis, Indyk, Motwani (SIAM) — HIGH confidence
- [Hammer Slide: Work- and CPU-efficient Streaming Window Aggregation](https://adms-conf.org/2018-camera-ready/SIMDWindowPaper_ADMS'18.pdf) — ADMS 2018 — MEDIUM confidence

### Cross-Day & Behavioral Patterns
- [Reproducibility of CGM Under Real-Life Conditions](https://www.nature.com/articles/s41598-023-40949-1.pdf) — Scientific Reports (2023) — HIGH confidence
- [Temporal Glycemic Patterns in T1D and T2D](https://par.nsf.gov/biblio/10616916-temporal-glycemic-patterns-type-type-diabetes-insights-extended-continuous-glucose-monitoring) — NSF Public Access (2025) — HIGH confidence
- [Intelligent Data-Driven Model for Diabetes Diurnal Patterns](https://eprints.whiterose.ac.uk/id/eprint/157489/1/Diabetes_diurnal_patterns_IEEE_journal_Accepted_.pdf) — IEEE (2020) — HIGH confidence
- [Chronobiologically-Informed Features from CGM Data](https://journals.plos.org/digitalhealth/article/file?id=10.1371%2Fjournal.pdig.0000815&type=printable) — PLOS Digital Health (2024) — HIGH confidence

### Wellness Language & FDA
- [FDA 2026 Guidance on Digital Health Platforms](https://aimdek.com/blogs/fdas-new-2026-guidance-digital-health-platforms-wearables-and-cds/) — FDA guidance summary — HIGH confidence
- [AI Claims Warning Letter Analysis](https://www.jdsupra.com/legalnews/ai-claims-yay-or-oy-a-recent-warning-6654618/) — JDSupra (2025) — HIGH confidence
- [Health App Regulatory Compliance for AI-Built Apps](https://topflightapps.com/ideas/health-app-regulatory-compliance-ai-built/) — TopFlight Apps — MEDIUM confidence

---

*Pitfalls research for: CGM Insights v2.0 (Anomaly Detection, Sleep Analysis, Behavioral Patterns)*
*Researched: 2026-06-10*