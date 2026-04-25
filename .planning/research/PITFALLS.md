# Domain Pitfalls: CGM Analytics Application

**Domain:** Continuous Glucose Monitor (CGM) Data Analysis Application
**Researched:** 2026-04-23
**Confidence:** HIGH

---

## Critical Pitfalls

Mistakes that cause rewrites, legal liability, or major user harm.

### Pitfall 1: Crossing the Medical Device Regulatory Boundary

**What goes wrong:** The app makes claims or provides functionality that crosses from "general wellness" into regulated medical device territory, triggering FDA oversight requirements.

**Why it happens:** Developers inadvertently use disease-specific language ("diabetes management," "hypoglycemia detection"), provide treatment guidance, or set clinical thresholds (70-180 mg/dL) as diagnostic indicators rather than informational ranges.

**Consequences:**
- FDA enforcement action requiring app removal or modification
- Legal liability if users make medical decisions based on app recommendations
- Required premarket approval (510(k) or PMA) if classified as medical device
- Potential criminal penalties for unauthorized medical device distribution

**Prevention:**
- Use wellness-focused language: "glucose patterns," "insights," not "diabetes management"
- Never provide treatment recommendations (insulin doses, medication timing)
- Display ranges as informational, not diagnostic thresholds
- Include clear disclaimer: "Not a medical device. For informational purposes only. Not intended for diagnosis or treatment."
- Avoid clinical alerts that recommend specific medical actions
- Do NOT market to diabetics for disease management if seeking wellness classification

**Detection:**
- Audit all UI copy for disease-specific claims
- Review feature specifications against FDA guidance criteria
- Legal review of marketing materials before launch

**Phase to address:** Foundation (must be embedded from day one - retrofitting is painful)

---

### Pitfall 2: Treating CGM Data as Accurate Blood Glucose

**What goes wrong:** The app treats CGM readings as equivalent to blood glucose measurements, ignoring the 5-25 minute physiological lag between interstitial fluid and blood glucose, leading to misleading insights.

**Why it happens:** Developers assume sensor data is "ground truth" without understanding that CGMs measure interstitial fluid glucose, not blood glucose. The lag varies by individual and glucose rate of change.

**Consequences:**
- Incorrect pattern identification (meal peaks appear later than actual consumption)
- Misleading correlation analysis (exercise effects misaligned)
- User confusion when CGM readings don't match fingerstick tests
- Erosion of trust in app insights

**Prevention:**
- Document and communicate the physiological lag in app education
- Consider rate-of-change when detecting patterns (rising/falling glucose affects lag)
- Never recommend insulin timing based on CGM alone
- Display trend arrows prominently when showing current values
- Use time-alignment techniques when correlating with user-logged events

**Detection:**
- User reports of "inaccurate" insights that match symptoms
- Pattern timing that doesn't align with logged meals/activities
- Correlation tests against fingerstick data (if available)

**Phase to address:** Analysis Engine (core to pattern detection algorithms)

---

### Pitfall 3: Ignoring Data Quality Issues (Gaps, Artifacts, Compression Lows)

**What goes wrong:** The app calculates metrics and detects patterns on incomplete or corrupted data without flagging quality issues, producing unreliable results.

**Why it happens:** CGM data naturally contains gaps (sensor disconnection, signal loss), artifacts (duplicate timestamps, parallel profiles), and false readings (compression lows from sleeping on sensor, medication interference). Raw data is rarely clean.

**Specific data quality issues:**

| Issue | Cause | Effect |
|-------|-------|--------|
| Data gaps | Sensor disconnection, signal loss | Affects variability metrics (CONGA, MAGE), TIR accuracy |
| Compression lows | Sleeping on sensor (pressure reduces blood flow) | False hypoglycemia readings during sleep |
| Sensor drift | First 24-48 hours after insertion | 10-15% accuracy degradation |
| End-of-life decay | Days 10-14 of sensor wear | Declining accuracy |
| Acetaminophen interference | Tylenol and similar medications | False elevated readings |
| Duplication errors | Multiple device uploads, EHR integration | 25.9% of profiles affected in studies |

**Consequences:**
- Time Below Range dramatically overstated due to compression lows
- Pattern detection based on artifacts, not real physiology
- Users receive suggestions based on corrupted data
- 14-day TIR calculations invalid if <80% data completeness

**Prevention:**
- Require minimum 80% data completeness for reliable metrics
- Detect and flag compression lows (rapid drops during typical sleep hours)
- Identify sensor warm-up period (first 24-48 hours) and exclude or weight lower
- Detect duplicate timestamps and parallel profiles before analysis
- Check for physiological plausibility (glucose changes >5 mg/dL/min are suspect)
- Display data quality indicators alongside insights

**Detection:**
- Calculate data completeness percentage before generating insights
- Flag suspicious patterns (overnight lows without symptoms, rapid spikes/drops)
- Cross-reference with sensor metadata (wear time, signal quality if available)

**Phase to address:** Data Import & Validation (must be caught before analysis)

---

### Pitfall 4: Over-Promising Actionability Without Context

**What goes wrong:** The app presents "insights" that are actually just data observations without actionable context, leading to user frustration and disengagement.

**Why it happens:** Developers confuse "showing patterns" with "providing actionable insights." A spike at 2pm is data; knowing it correlates with lunch and stress is insight; knowing what to change is actionability.

**Consequences:**
- Users see the data but don't know what to do with it
- "So what?" response to insights
- App abandonment after initial curiosity wears off
- Negative reviews citing lack of value

**Prevention:**
- Distinguish three levels: Data (what) -> Pattern (when) -> Insight (why) -> Action (what to do)
- Never present a pattern without at least one hypothesis for cause
- Require user context (meals, activity, stress) for personalized suggestions
- Use "consider" language rather than prescriptive recommendations
- Provide educational content explaining why patterns matter
- Offer specific experiments users can try ("test eating this food with more protein")

**Detection:**
- User feedback surveys asking "did you know what to do after seeing this?"
- Engagement metrics on insight cards vs. raw data views
- Support requests asking "what does this mean?"

**Phase to address:** Insight Generation (core value proposition - must be designed in)

---

## Moderate Pitfalls

### Pitfall 5: Alert Fatigue and Notification Overload

**What goes wrong:** The app generates too many alerts or notifications, causing users to ignore or disable them entirely, including potentially valuable insights.

**Why it happens:** Each pattern or anomaly seems important to developers, but users quickly become overwhelmed. Research shows alarm fatigue is linked to worse glucose control and diabetes distress.

**Consequences:**
- Users disable notifications entirely
- Important insights missed
- User frustration and potential abandonment
- Mental health impact from constant monitoring pressure

**Prevention:**
- Prioritize: Only alert on patterns that warrant action
- Batch insights: Weekly digest rather than daily notifications
- User control: Let users set notification preferences and thresholds
- Smart timing: Don't send insights at inconvenient times
- Quiet modes: Allow users to pause non-critical notifications
- Focus on 2-3 key insights per session, not everything

**Detection:**
- Track notification dismissal rates
- Monitor notification opt-out rates
- User feedback on notification volume

**Phase to address:** Frontend & UX (design notification system thoughtfully)

---

### Pitfall 6: Presenting Single Metrics Without Context

**What goes wrong:** The app displays Time in Range, average glucose, or other metrics in isolation, without the context needed for interpretation.

**Why it happens:** Developers focus on individual metrics without understanding that TIR interpretation requires glycemic variability (CV), and both must be considered together. A 70% TIR means something different at 25% CV vs 40% CV.

**Consequences:**
- Users misinterpret their glucose control
- False sense of security or unnecessary worry
- Misleading comparisons between time periods

**Key metric relationships:**
- TIR + CV together indicate control quality
- Same TIR with higher CV = worse outcomes
- GMI (Glucose Management Indicator) estimates A1C from CGM
- Time Below Range is critical for hypoglycemia risk (target <4%)

**Prevention:**
- Always show related metrics together (TIR, CV, GMI, TBR)
- Provide reference ranges and what they mean
- Explain how metrics relate to each other
- Show trends over time, not just current values

**Detection:**
- User confusion about what "good" looks like
- Questions about why TIR improved but control feels worse

**Phase to address:** Analysis Engine (metric calculation and presentation)

---

### Pitfall 7: Insufficient Data Period for Pattern Detection

**What goes wrong:** The app attempts to identify patterns from too few days of data, producing unreliable or misleading results.

**Why it happens:** Users upload partial data or the app eagerly generates insights before sufficient data is collected.

**Consequences:**
- Day-of-week patterns from 3 days are meaningless
- Meal patterns from 2 instances are coincidental
- Users receive unreliable suggestions
- Wasted development effort on premature analysis

**Minimum data requirements:**
- 14+ days for reliable pattern identification
- 70-80% data completeness for accurate TIR
- Multiple instances for meal or activity correlations
- Full week minimum for day-of-week analysis

**Prevention:**
- Display "insufficient data" message until thresholds met
- Show data collection progress toward analysis-ready state
- Indicate confidence level based on data quantity
- Prioritize basic metrics (average, ranges) over complex patterns for small datasets

**Detection:**
- Data quantity checks before pattern analysis
- Variance in patterns between consecutive periods (instability = unreliable)

**Phase to address:** Data Import & Validation (validate before analysis)

---

### Pitfall 8: Performance Degradation with Large Datasets

**What goes wrong:** Analysis becomes slow or unresponsive when processing typical CGM data volumes (288 readings/day = 8,640/month = 100,000+/year).

**Why it happens:** Naive implementations using pure Python loops or unoptimized data structures cannot handle time-series operations on millions of points.

**Consequences:**
- Poor user experience (long waits for results)
- Browser/server timeouts
- Users give up on analysis

**Prevention:**
- Use vectorized operations (NumPy, Pandas)
- Consider C++ extensions for critical paths (PyO3, Cython)
- Implement streaming/chunked processing for large files
- Cache intermediate results
- Use efficient data structures (avoid repeated DataFrame copies)
- Consider specialized libraries: GlucoStats (Python), cgmguru (R via reticulate)

**Detection:**
- Performance testing with realistic data volumes
- Load testing with multi-month uploads
- Memory profiling for large datasets

**Phase to address:** Analysis Engine (architecture decision from start)

---

## Minor Pitfalls

### Pitfall 9: Confusing Food Demonization with Pattern Recognition

**What goes wrong:** The app suggests certain foods are "bad" based on glucose spikes, ignoring context (portion size, meal composition, activity, stress).

**Why it happens:** Simplistic pattern matching without considering confounding factors.

**Consequences:**
- Users develop unhealthy relationship with food
- Misleading insights (spike may be due to stress, not food)
- Reduced trust when "bad" food doesn't cause spike next time

**Prevention:**
- Never label foods as good/bad
- Emphasize context (what else was eaten, activity level)
- Show confidence level for food-glucose correlations
- Encourage controlled experiments rather than conclusions

**Detection:**
- User feedback about food anxiety
- Contradictory insights (same food, different outcomes)

**Phase to address:** Insight Generation (nuance in messaging)

---

### Pitfall 10: Privacy and Data Handling Oversights

**What goes wrong:** The app handles sensitive health data without proper privacy measures, exposing users to risk and the developer to liability.

**Why it happens:** Health data privacy requirements (HIPAA, state laws, GDPR) are complex and easy to overlook in MVP development.

**Key concerns:**
- 59.8% of diabetes apps request "dangerous permissions"
- 28.4% have no privacy policy
- Free apps often monetize through data sharing
- Glucose data is considered sensitive/PHI

**Prevention:**
- Provide clear, accessible privacy policy
- Request minimal permissions
- Encrypt data at rest and in transit
- No third-party data sharing without explicit consent
- Allow data export and deletion
- Consider HIPAA compliance even if not legally required

**Detection:**
- Privacy audit of app permissions
- Third-party SDK review for data transmission
- Legal review of data handling practices

**Phase to address:** Foundation (privacy by design from start)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Project Setup | Regulatory boundary crossing | Legal review of app positioning, clear wellness framing |
| Data Import | Data quality issues ignored | Implement validation, completeness checks, artifact detection |
| Analysis Engine | Treating CGM as blood glucose | Document lag, implement time-alignment |
| Analysis Engine | Insufficient data for patterns | Minimum data thresholds before analysis |
| Analysis Engine | Performance on large datasets | Vectorized operations, efficient data structures |
| Insight Generation | Over-promising actionability | Three-level model: data -> pattern -> action |
| Insight Generation | Food demonization | Context-aware suggestions, avoid good/bad labels |
| Frontend/UX | Alert fatigue | User-controlled notifications, batching, quiet modes |
| Frontend/UX | Single metrics without context | Show related metrics together with education |

---

## Quick Reference: Critical Prevention Checklist

- [ ] Legal review confirms wellness positioning, not medical device
- [ ] Clear disclaimers that app is not for diagnosis/treatment
- [ ] Data quality validation before any analysis
- [ ] Minimum 80% data completeness required for metrics
- [ ] Minimum 14 days for pattern detection
- [ ] Physiological lag documented and considered in timing
- [ ] Related metrics shown together (TIR + CV + TBR)
- [ ] Actionable suggestions, not just observations
- [ ] Privacy policy and minimal permissions
- [ ] Performance tested with realistic data volumes

---

## Sources

- [FDA General Wellness Guidance (2026)](https://www.fda.gov/media/100032/download) - HIGH confidence
- [PMC: Processing Algorithm for CGM Data Quality Issues](https://pmc.ncbi.nlm.nih.gov/articles/PMC11843558/) - HIGH confidence
- [medRxiv: Assessing Accuracy of CGM Metrics](https://www.medrxiv.org/content/10.1101/2025.02.13.25322196v1.full) - HIGH confidence
- [PMC: Minding the Gaps in CGM](https://pmc.ncbi.nlm.nih.gov/articles/PMC3692219/) - HIGH confidence
- [PMC: Designing the CGM Experience](https://pmc.ncbi.nlm.nih.gov/articles/PMC10899853/) - HIGH confidence
- [NCBI: Diabetes Device Alarm Fatigue](https://ncbi.nlm.nih.gov/pmc/articles/PMC3869147/) - HIGH confidence
- [BMC Bioinformatics: GlucoStats Library](https://bmcbioinformatics.biomedirect.com/articles/10.1186/s12859-025-06250-w) - HIGH confidence
- [Nature: CGM-LSM Foundation Model](http://www.nature.com/articles/s44401-25-00039-y) - HIGH confidence
- [JMIR: Diabetes Apps Privacy Analysis](https://diabetes.jmir.org/2021/1/e16146/PDF) - HIGH confidence
- [FDA Safety Communication: Diabetes App Alerts](https://www.fda.gov/medical-devices/safety-communications/fda-alerts-patients-regularly-check-diabetes-related-smartphone-device-alert-settings-especially) - HIGH confidence
- [AP News: FDA Alert on Diabetes Apps](https://apnews.com/article/diabetes-smartphone-apps-death-injury-fda-health-920b97d30e4330bfc67f249430b7c17e) - HIGH confidence
- [Dexcom: Preventing Alert Fatigue](https://dexcom.com/en-us/all-access/dexcom-cgm-explained/preventing-alert-fatigue) - HIGH confidence
- [PMC: Critical Reappraisal of TIR](https://pmc.ncbi.nlm.nih.gov/articles/PMC7753853/) - HIGH confidence
- [UX Collective: CGM App UX Comparison](https://uxdesign.cc/comparing-dexcoms-home-screen-ux-over-time-9a974bea3f11) - MEDIUM confidence