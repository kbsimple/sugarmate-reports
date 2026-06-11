# Architecture Patterns

**Domain:** CGM Analytics Application
**Researched:** 2026-04-23 (Updated: 2026-06-10 for v2.0)

---

## v2.0 Extension: Anomaly Detection, Sleep Analysis, Behavioral Patterns

This section documents the architectural integration points for adding anomaly detection (ANLY-02), sleep analysis (ANLY-03), and behavioral pattern analysis to the existing CGM Insights architecture.

### Existing Architecture Summary

The current architecture follows a **layered separation pattern** with the Python analysis engine at the core:

```
src/
├── cgm_insights/              # Core library (independently usable)
│   ├── models/                # Pydantic data models
│   │   ├── reading.py         # CGMReading
│   │   └── results.py        # AnalysisResults, TimeInRange, ValidationResult
│   ├── ingestion/             # Data parsing pipeline
│   ├── analytics/             # Analysis modules
│   │   ├── metrics.py        # Core metrics (TIR, GMI, CV)
│   │   ├── patterns.py       # Time-of-day, day-of-week patterns
│   │   └── completeness.py   # Minimum data checks
│   ├── output/                # Formatters and display
│   │   ├── formatter.py
│   │   ├── suggestions.py
│   │   └── visualization.py
│   └── __init__.py           # Public API: analyze_file(), format_results()
├── cli.py                     # Typer CLI
└── web/                       # FastAPI frontend
    ├── routes/
    │   ├── upload.py
    │   ├── results.py
    │   └── export.py
    └── services/
        ├── session.py        # SessionData dataclass
        └── agp_generator.py
```

---

## Recommended Architecture for v2.0

### New Module Structure

```
src/cgm_insights/
├── analytics/
│   ├── metrics.py            # [EXISTING] Core metrics
│   ├── patterns.py           # [EXISTING] Time-of-day, day-of-week
│   ├── anomaly.py            # [NEW] Anomaly detection
│   ├── sleep.py              # [NEW] Sleep analysis (10pm-6am)
│   ├── behavioral.py         # [NEW] Behavioral pattern analysis
│   └── completeness.py       # [EXISTING] Minimum data checks
├── models/
│   ├── reading.py            # [EXISTING]
│   ├── results.py            # [MODIFIED] Add new result fields
│   └── patterns.py           # [NEW] Extract shared pattern types
```

### Proposed Model Extensions

```python
# models/patterns.py (NEW FILE)
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
from typing import Literal
from datetime import datetime, time

class PatternType(str, Enum):
    TIME_OF_DAY = "time_of_day"
    DAY_OF_WEEK = "day_of_week"
    SLEEP = "sleep"                    # NEW
    BEHAVIORAL = "behavioral"          # NEW

class AnomalyType(str, Enum):         # NEW
    UNEXPLAINED_HIGH = "unexplained_high"
    UNEXPLAINED_LOW = "unexplained_low"
    SENSOR_ARTIFACT = "sensor_artifact"
    PATTERN_DEVIATION = "pattern_deviation"

class AnomalyResult(BaseModel):        # NEW
    anomaly_type: AnomalyType
    timestamp: datetime
    glucose_value: float
    expected_range: tuple[float, float]
    deviation_magnitude: float
    confidence: float
    context: dict                      # time of day, day of week, recent trend

class SleepMetrics(BaseModel):         # NEW
    window_start: time                  # Actual inferred start
    window_end: time                    # Actual inferred end
    avg_glucose: float
    glucose_cv: float
    time_in_range_pct: float
    time_below_range_pct: float
    time_above_range_pct: float
    stability_index: float              # NGSI-like metric (0-1 scale)
    excursions: list[dict]              # >30mg/dL changes in 30min

class BehavioralPattern(BaseModel):    # NEW
    pattern_type: Literal["consistency", "variability", "weekday_weekend"]
    time_bucket: str                   # "30min", "60min", "120min"
    description: str
    weekday_avg: float | None
    weekend_avg: float | None
    consistency_score: float           # Cross-day similarity (0-1)
    variability_cv: float
```

### Analyzer Pipeline Extension

```python
# analytics/anomaly.py (NEW FILE)
"""Anomaly detection for CGM glucose data.

Implements multiple detection methods:
1. Statistical outlier detection (Z-score based)
2. Pattern deviation detection (vs established baseline)
3. Rate-of-change anomalies (rapid rises/drops)

All detection uses wellness language - no medical diagnosis.
"""

from datetime import datetime, timedelta
from typing import Literal

from cgm_insights.models import CGMReading
from cgm_insights.analytics.patterns import PatternResult

# Thresholds for anomaly detection
RAPID_RISE_THRESHOLD = 40      # mg/dL per hour - rapid rise
RAPID_DROP_THRESHOLD = 40      # mg/dL per hour - rapid drop
Z_SCORE_THRESHOLD = 2.5        # Standard deviations for outlier
MIN_BASELINE_DAYS = 7          # Days needed for pattern baseline


def detect_anomalies(
    readings: list[CGMReading],
    baseline_patterns: list[PatternResult] | None = None,
    sensitivity: Literal["low", "medium", "high"] = "medium"
) -> list[AnomalyResult]:
    """Detect glucose anomalies beyond expected patterns.

    Uses statistical methods and pattern comparison to identify:
    - Unexplained highs/lows outside established patterns
    - Rapid rate-of-change events
    - Sensor artifacts (compression lows, etc.)

    Args:
        readings: Sorted list of CGM readings
        baseline_patterns: Pre-computed patterns for comparison
        sensitivity: Detection sensitivity level

    Returns:
        List of detected anomalies sorted by severity
    """
    pass
```

```python
# analytics/sleep.py (NEW FILE)
"""Sleep period analysis for CGM data.

Infers overnight glucose patterns from 10pm-6am window.
Uses NGSI-style metrics for stability assessment.
"""

from datetime import time

from cgm_insights.models import CGMReading

# Default sleep window (typical sleep hours)
DEFAULT_SLEEP_START = time(22, 0)   # 10 PM
DEFAULT_SLEEP_END = time(6, 0)      # 6 AM

# Stability thresholds
OPTIMAL_STABILITY_INDEX = 0.8
MODERATE_INSTABILITY = 0.5
EXCURSION_THRESHOLD = 30            # mg/dL change in 30 minutes


def analyze_sleep(
    readings: list[CGMReading],
    sleep_start: time = DEFAULT_SLEEP_START,
    sleep_end: time = DEFAULT_SLEEP_END
) -> SleepMetrics | None:
    """Analyze overnight glucose patterns.

    Args:
        readings: Sorted list of CGM readings
        sleep_start: Start of sleep window (default 10 PM)
        sleep_end: End of sleep window (default 6 AM)

    Returns:
        SleepMetrics if sufficient overnight data, None otherwise
    """
    pass
```

```python
# analytics/behavioral.py (NEW FILE)
"""Behavioral pattern analysis for CGM data.

Provides time-bucketed analysis with sliding windows,
weekday vs weekend segmentation, and cross-day consistency.
"""

from cgm_insights.models import CGMReading

# Time bucket configurations
TIME_BUCKETS = [30, 60, 120]      # Minutes per bucket
SLIDING_WINDOW_STEP = 5           # Minutes between windows
MIN_DAYS_FOR_CONSISTENCY = 7      # Days needed for cross-day analysis


def analyze_behavioral_patterns(
    readings: list[CGMReading],
    time_buckets: list[int] = TIME_BUCKETS
) -> list[BehavioralPattern]:
    """Analyze behavioral patterns across multiple time scales.

    Computes:
    - Time-bucketed glucose averages (30/60/120 min windows)
    - Weekday vs weekend comparisons
    - Cross-day consistency scores

    Args:
        readings: Sorted list of CGM readings
        time_buckets: Minutes per analysis bucket

    Returns:
        List of detected behavioral patterns
    """
    pass


def calculate_cross_day_consistency(
    readings: list[CGMReading],
    time_bucket_minutes: int = 60
) -> dict[str, float]:
    """Calculate how consistent glucose is at each time across days.

    For each time bucket (e.g., noon-1pm), computes variance
    across weekdays vs weekends.

    Args:
        readings: Sorted list of CGM readings
        time_bucket_minutes: Size of time buckets

    Returns:
        Dict with consistency scores per time bucket
    """
    pass
```

---

## Integration Patterns

### Pattern 1: Analyzer Composition

**What:** New analytics modules follow the same pattern as `patterns.py` — pure functions that take readings and return typed results.

**When to use:** All new analytics features.

**Trade-offs:**
- Pros: Consistent API, easy to test independently, works with CLI and web
- Cons: Results must be aggregated at higher level

**Example:**
```python
# In __init__.py or analyzer.py
from cgm_insights.analytics import (
    detect_time_of_day_patterns,
    detect_day_of_week_patterns,
    detect_anomalies,           # NEW
    analyze_sleep,              # NEW
    analyze_behavioral_patterns # NEW
)

def analyze_all(readings: list[CGMReading]) -> AnalysisResults:
    """Full analysis pipeline."""
    results = calculate_metrics(readings, validation)
    patterns = detect_time_of_day_patterns(readings) + detect_day_of_week_patterns(readings)
    anomalies = detect_anomalies(readings, baseline_patterns=patterns)
    sleep = analyze_sleep(readings)
    behavioral = analyze_behavioral_patterns(readings)

    return AnalysisResults(
        ...,
        patterns=patterns,
        anomalies=anomalies,
        sleep_metrics=sleep,
        behavioral_patterns=behavioral
    )
```

### Pattern 2: Result Model Extension

**What:** Extend `AnalysisResults` to include new result types while maintaining backward compatibility.

**When to use:** When adding new analysis types.

**Trade-offs:**
- Pros: Single result object for all analysis, backward compatible with Optional fields
- Cons: Model grows larger over time

**Example:**
```python
class AnalysisResults(BaseModel):
    # Existing fields...

    # New optional fields for v2.0
    anomalies: list[AnomalyResult] | None = Field(
        None, description="Detected anomalies outside expected patterns"
    )
    sleep_metrics: SleepMetrics | None = Field(
        None, description="Overnight glucose analysis"
    )
    behavioral_patterns: list[BehavioralPattern] | None = Field(
        None, description="Cross-day behavioral patterns"
    )
```

### Pattern 3: Session Store Extension

**What:** Extend `SessionData` to store new result types alongside existing patterns.

**When to use:** When web frontend needs to display new analysis results.

**Example:**
```python
@dataclass
class SessionData:
    results: AnalysisResults
    patterns: list[PatternResult] = field(default_factory=list)
    anomalies: list[AnomalyResult] = field(default_factory=list)    # NEW
    sleep_metrics: SleepMetrics | None = None                       # NEW
    behavioral_patterns: list[BehavioralPattern] = field(default_factory=list)  # NEW
    raw_readings: list[dict] = field(default_factory=list)
```

### Pattern 4: Suggestion Generator Extension

**What:** Extend `suggestions.py` to generate suggestions from new pattern types.

**When to use:** When new analysis should produce actionable insights.

**Example:**
```python
SUGGESTION_TEMPLATES = {
    # Existing templates...

    # New templates for v2.0
    "sleep_high_variability": {
        "title": "Overnight glucose variability detected",
        "description": "Your glucose varies more during sleep hours.",
        "action": "Consider discussing overnight patterns with your healthcare provider.",
        "category": SuggestionCategory.VARIABILITY,
        "priority": 2,
    },
    "anomaly_unexplained_high": {
        "title": "Unexplained high glucose detected",
        "description": "A glucose reading was significantly higher than your typical pattern.",
        "action": "Consider tracking what might have contributed to this unusual reading.",
        "category": SuggestionCategory.SAFETY,
        "priority": 1,
    },
    "weekend_pattern": {
        "title": "Weekend pattern differs from weekdays",
        "description": "Your glucose patterns differ between weekdays and weekends.",
        "action": "Consider maintaining consistent routines through the weekend.",
        "category": SuggestionCategory.TIMING,
        "priority": 3,
    },
}
```

---

## Data Flow for v2.0

### Extended Analysis Pipeline

```
[File Upload]
     |
     v
[Parser] → [Normalizer] → [Validator]
                         |
                         v
                   [calculate_metrics()]
                         |
         +---------------+---------------+---------------+
         |               |               |               |
         v               v               v               v
   [Patterns]      [Anomalies]     [Sleep]        [Behavioral]
   (existing)       (NEW)          (NEW)          (NEW)
         |               |               |               |
         +---------------+---------------+---------------+
                         |
                         v
                  [AnalysisResults]
                   (extended model)
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
   [Formatter]    [Suggestions]   [Visualization]
    (extended)    (extended)      (extended)
          |              |              |
          v              v              v
   [CLI Output]   [Web Display]  [Charts]
```

### Web Integration Flow

```
[Upload Route]
     |
     v
[analyze_file()] + [detect_anomalies()] + [analyze_sleep()] + [analyze_behavioral()]
     |
     v
[SessionData] (extended with anomalies, sleep_metrics, behavioral_patterns)
     |
     v
[Results Route]
     |
     +-- [format_results()] → JSON for charts
     +-- [format_anomalies()] → Anomaly cards
     +-- [format_sleep()] → Sleep summary
     +-- [format_behavioral()] → Consistency scores
     +-- [generate_suggestions()] → Actionable insights
```

---

## Component Responsibilities

### New Components

| Component | Responsibility | Implementation Notes |
|-----------|----------------|---------------------|
| `analytics/anomaly.py` | Detect glucose anomalies | Statistical methods (Z-score, rate-of-change) |
| `analytics/sleep.py` | Analyze overnight patterns | 10pm-6am window, NGSI-style metrics |
| `analytics/behavioral.py` | Cross-day consistency analysis | Sliding window time buckets, weekday/weekend |
| `models/patterns.py` | Extended pattern types | New enums and result models |

### Modified Components

| Component | Changes | Impact |
|-----------|---------|--------|
| `models/results.py` | Add `anomalies`, `sleep_metrics`, `behavioral_patterns` | Backward compatible (Optional fields) |
| `web/services/session.py` | Extend `SessionData` with new fields | Minor change |
| `output/suggestions.py` | Add templates for new pattern types | Additive only |
| `__init__.py` | Export new analyzers | Additive only |

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| MVP (current) | In-memory session store sufficient, pure Python analysis |
| 100+ sessions | Consider Redis for session storage, background job processing |
| Production | Add caching for analysis results, lazy computation for expensive analytics |

### Performance Notes

1. **Anomaly detection:** O(n) for Z-score, O(n) for rate-of-change — acceptable for 288 readings/day
2. **Sleep analysis:** Filters to overnight hours first — ~96 readings/night
3. **Behavioral patterns:** Most expensive — sliding windows over all days
   - For 14 days: ~4032 readings × 3 bucket sizes = manageable
   - Consider caching results if re-analyzed frequently

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Tight Coupling Between Analyzers

**What people do:** Have anomaly detection call pattern detection directly, creating circular dependencies.

**Why it's wrong:** Changes to one analyzer break the other, harder to test independently.

**Do this instead:** Pass baseline patterns as optional parameter; analyzers remain independent.

### Anti-Pattern 2: Blocking Web Request for Analysis

**What people do:** Run all analysis synchronously in upload route.

**Why it's wrong:** Behavioral analysis can take seconds; web requests timeout.

**Do this instead:** For MVP, acceptable; for scale, move to background task (FastAPI BackgroundTasks or Celery).

### Anti-Pattern 3: Mixing Medical Claims with Wellness Language

**What people do:** Frame anomaly detection as "diagnosis" or "abnormal glucose."

**Why it's wrong:** Regulatory risk; project explicitly avoids medical advice.

**Do this instead:** Use wellness language: "unusual pattern," "deviation from your baseline," "consider discussing with your healthcare provider."

### Anti-Pattern 4: Over-Engineering Sliding Windows

**What people do:** Implement full sktime/tslearn pipeline for simple time bucketing.

**Why it's wrong:** Adds heavy dependencies for simple grouping logic.

**Do this instead:** Native Python grouping by hour/minute buckets; sliding windows are just offset grouping.

---

## Implementation Order (Build Sequence)

### Phase 1: Foundation (ANLY-02 prep)
1. **Create `models/patterns.py`** — Extract `PatternType`, `PatternSeverity` to shared module
2. **Add anomaly models** — `AnomalyResult`, `AnomalyType`
3. **Add sleep models** — `SleepMetrics`
4. **Add behavioral models** — `BehavioralPattern`

### Phase 2: Anomaly Detection (ANLY-02)
5. **Implement `analytics/anomaly.py`** — Statistical detection + pattern comparison
6. **Extend `SessionData`** — Add `anomalies` field
7. **Add `format_anomalies()`** — Output formatting
8. **Update `upload.py`** — Call `detect_anomalies()` and store results
9. **Add suggestion templates** — For anomaly insights

### Phase 3: Sleep Analysis (ANLY-03)
10. **Implement `analytics/sleep.py`** — Filter to 10pm-6am, compute metrics
11. **Extend `SessionData`** — Add `sleep_metrics` field
12. **Add `format_sleep()`** — Output formatting
13. **Update `upload.py`** — Call `analyze_sleep()` and store results
14. **Add suggestion templates** — For sleep insights

### Phase 4: Behavioral Patterns (NEW)
15. **Implement `analytics/behavioral.py`** — Time buckets, weekday/weekend, consistency
16. **Extend `SessionData`** — Add `behavioral_patterns` field
17. **Add `format_behavioral()`** — Output formatting
18. **Update `upload.py`** — Call `analyze_behavioral_patterns()` and store results
19. **Add suggestion templates** — For behavioral insights

### Phase 5: Integration & Display
20. **Update `results.py` route** — Render all new result types
21. **Update `format_results()`** — Include new fields in output dict
22. **Update CLI `analyze` command** — Add flags for new analyses
23. **Update templates** — Display anomaly cards, sleep summary, consistency scores

---

## Sources

### Existing Architecture
- [Glucose360 Open-Source Platform](https://github.com/vurhd2/Glucose360) - Reference architecture for CGM analysis library + web app
- [GlucoStats Python Library](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-025-06250-w) - 59 glucose metrics with scikit-learn compatibility
- [FastAPI Best Practices](https://fastlaunchapi.dev/blog/fastapi-best-practices-production-2026) - Web API architecture patterns

### Anomaly Detection (v2.0)
- [CGM Data Analysis 2.0: Functional Data Pattern Recognition and AI Applications](https://ar5iv.labs.arxiv.org/html/2505.07885) — Comprehensive review of advanced CGM analysis methods including anomaly detection
- [Unsupervised Detection of Pressure Induced Failures in CGM Sensors](https://www.research.unipd.it/handle/11577/3540043) — Isolation Forest and Histogram-based Outlier Score methods for sensor anomaly detection
- [PyOD Time Series Detectors](https://pyod.readthedocs.io/en/latest/pyod.models.timeseries.html) — Sliding window anomaly detection implementations

### Sleep Analysis (v2.0)
- [Nocturnal Glycemic Stability Index (NGSI)](https://www.medrxiv.org/content/10.1101/2025.05.18.25327867v1) — Novel metric for overnight glucose stability (2025)
- [Machine Learning Models for Nocturnal Glucose Prediction](https://www.mdpi.com/2075-4418/14/7/740) — MLP, CNN, RF, GBT models for overnight prediction
- [Binary Classifiers for Nocturnal Hypoglycemia](https://pmc.ncbi.nlm.nih.gov/articles/PMC11696951/) — SVM-based prediction methods

### Behavioral Patterns (v2.0)
- [QoCGM: Quantification of Continuous Glucose Monitoring](https://peerj.com/articles/19501) — Day-to-day variability metrics (D2d_mean, D2d_TIR)
- [Temporal Glycemic Patterns in T1D and T2D](https://par.nsf.gov/biblio/10616916-temporal-glycemic-patterns-type-type-diabetes-insights-from-extended-continuous-glucose-monitoring) — Weekday/weekend differences analysis
- [Seasonal, Weekly, Individual Variations in CGM Use](https://preview-www.nature.com/articles/s41598-025-98276-6) — Behavioral patterns in CGM data

---
*Architecture research for: CGM Insights*
*Last updated: 2026-06-10 for v2.0 milestone*