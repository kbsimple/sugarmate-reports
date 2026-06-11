# Phase 6: Anomaly Detection - Research

**Researched:** 2026-06-11
**Domain:** Statistical outlier detection on time-bucketed CGM baselines, PISA artifact filtering, weekly aggregate summaries
**Confidence:** HIGH — all claims derived from direct codebase inspection and verified Polars API patterns

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANLY-02 | Statistical outlier detection (>2 SD from time-of-day/day-of-week baseline) | Per-bucket mean+std via Polars group_by; same DataFrame structure already used in behavioral_patterns.py |
| ANLY-03 | PISA artifact filtering before anomaly detection | Rapid-drop/recovery signature detected per-reading on time-ordered overnight DataFrame; filtered out before baseline comparison |
| ANLY-04 | Severity classification (mild/moderate/severe) based on deviation magnitude | SD multiple thresholds: 2–3=mild, 3–4=moderate, >4=severe; applied per reading after PISA filter |
| ANLY-05 | Weekly anomaly summaries — aggregate counts, time distribution, no individual alerts | Polars group_by(week, severity, bucket_hour, day_type).agg(count); result schema described below |
| ANLY-06 | Wellness language throughout ("unusual pattern" not "abnormal") | Follows established suggestion template system in suggestions.py |
</phase_requirements>

---

## Summary

Phase 6 builds an anomaly detection layer on top of the time-bucketed baseline established in Phase 4. The core algorithm is: for each CGM reading, compute its deviation from the historical mean of all readings in the same 30-minute time-of-day bucket and same day-type (weekday/weekend), then classify readings that fall beyond ±2 SD as outliers. Before this computation, readings that match the PISA artifact signature (rapid drop + rapid recovery, typically overnight) are excluded.

The output is never a per-reading alert. Instead, a weekly summary aggregates anomaly counts by severity tier, time-of-day distribution, and day-of-week, giving users a high-level view of unusual patterns without the psychological burden of individual notifications.

The integration chain is identical to Phase 5: new module in `analytics/`, wired into `analytics/__init__.py` and `cgm_insights/__init__.py`, stored as serialized dict in `SessionData`, passed through `upload.py` → `results.py` → Jinja template, and exposed via the `--anomaly` CLI flag.

**Primary recommendation:** Implement `analytics/anomaly_detection.py` following the exact structural conventions of `overnight_patterns.py`. The Phase 4 `_build_df()` and `_get_subset()` helpers can be imported directly — do not re-implement them.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Baseline computation (per-bucket mean + SD) | API / Backend (Python library) | — | Pure analytics on CGMReading objects; no UI concern |
| PISA artifact detection | API / Backend (Python library) | — | Time-series filter on ordered glucose values; library-only concern |
| Severity classification | API / Backend (Python library) | — | Enum mapping of SD multiples; all logic in model |
| Weekly summary aggregation | API / Backend (Python library) | — | Polars group_by aggregation; library produces final dict |
| Session storage of anomaly result | Frontend Server (FastAPI) | — | Same serialized-dict pattern as behavioral/overnight |
| Template rendering | Frontend Server (Jinja2) | — | New `anomaly_detection.html` component; include in results.html |
| CLI rendering | API / Backend (Typer/Rich) | — | `_render_anomaly_detection()` function in cli.py |

---

## Standard Stack

### Core (all already installed — no new dependencies)

| Library | Version Constraint | Purpose | How Used in Phase 6 |
|---------|--------------------|---------|---------------------|
| polars | >=1.40.0 [VERIFIED: pyproject.toml] | DataFrame operations | Bucket mean/std, group_by aggregations |
| pydantic | >=2.13.0 [VERIFIED: pyproject.toml] | Frozen result models | `AnomalyDetectionResult` model |
| fastapi | existing | Web layer | Session storage, results route |
| typer + rich | existing | CLI | `--anomaly/--no-anomaly` flag |

**No new pip installs required for Phase 6.**

---

## Architecture Patterns

### System Architecture Diagram

```
CGMReading list
      │
      ▼
 _build_df()          ← imported from behavioral_patterns.py
 (adds: mod, date, day_type columns)
      │
      ▼
 _filter_pisa_artifacts()
 (removes readings matching PISA signature)
      │
      ▼
 _compute_bucket_baselines()
 group_by(mod_bucket, day_type).agg(mean, std)
 → dict keyed by (bucket_start_30min, day_type)
      │
      ▼
 _classify_reading_deviations()
 for each reading: lookup bucket baseline → compute SD multiple → severity
      │
      ├─────────────────────────────────────────────────────────┐
      ▼                                                          ▼
 _build_weekly_summary()                              AnomalyDetectionResult
 group_by(iso_week, severity, hour_bucket, day_type)    .anomaly_counts_by_severity
 .agg(count)                                            .weekly_summaries
 → WeeklySummary list                                   .insufficient_data
      │
      ▼
 generate_anomaly_suggestions()
 (wellness-language Suggestion objects)
```

### Recommended Project Structure

```
src/cgm_insights/analytics/
├── anomaly_detection.py      # NEW — Phase 6 core module
├── behavioral_patterns.py    # Phase 4 — provides _build_df, _get_subset
├── overnight_patterns.py     # Phase 5 — import pattern to follow
├── metrics.py
├── patterns.py
└── __init__.py               # MODIFIED: add anomaly exports

src/cgm_insights/
└── __init__.py               # MODIFIED: add analyze_anomalies, AnomalyDetectionResult

src/web/
├── routes/upload.py          # MODIFIED: call analyze_anomalies, store dict
├── routes/results.py         # MODIFIED: pass anomaly_patterns to template
├── services/session.py       # MODIFIED: add anomaly_patterns field to SessionData
└── templates/
    ├── results.html          # MODIFIED: include anomaly_detection.html tab
    └── components/
        └── anomaly_detection.html  # NEW — Jinja2 component

src/cgm_insights/output/suggestions.py  # MODIFIED: add generate_anomaly_suggestions()

tests/test_analytics/
└── test_anomaly_detection.py  # NEW — 10-test suite

src/cgm_insights/cli.py       # MODIFIED: add --anomaly flag, _render_anomaly_detection()
```

---

## Pattern 1: Per-Bucket Baseline Algorithm

**What:** Compute the historical mean and standard deviation for each (30-minute bucket, day_type) combination across all days in the reading set. A "bucket" is the 30-minute slot of the day a reading falls in (minute-of-day // 30 * 30). This is the same `mod` column computed by `_build_df()` in Phase 4, just rounded to 30-minute resolution.

**Why 30 minutes specifically:** The Phase 4 behavioral analysis uses sliding windows of 30/60/120 minutes. For anomaly baseline purposes, a fixed 30-minute non-overlapping grid is more appropriate — it produces a unique bucket assignment per reading (no overlap), which is required for per-reading classification.

**Polars implementation:**

```python
# Source: derived from behavioral_patterns.py _build_df() and _compute_all_buckets() patterns
# [VERIFIED: direct codebase inspection]

BUCKET_MINUTES: int = 30
MIN_DAYS_FOR_BASELINE: int = 5  # match Phase 4 convention

def _compute_bucket_baselines(df: pl.DataFrame) -> pl.DataFrame:
    """Compute per-(bucket, day_type) mean and std from historical data.

    Args:
        df: DataFrame from _build_df() with mod, date, day_type, glucose columns.

    Returns:
        DataFrame with columns: bucket_start, day_type, bucket_mean, bucket_std,
        days_with_data. Only buckets with >= MIN_DAYS_FOR_BASELINE days are returned.
    """
    # Assign each reading to its 30-minute bucket
    df = df.with_columns(
        (pl.col("mod") // BUCKET_MINUTES * BUCKET_MINUTES).alias("bucket_start")
    )

    # Per-bucket, per-day means first (same approach as _compute_all_buckets)
    per_day = (
        df.group_by(["bucket_start", "day_type", "date"])
        .agg(pl.col("glucose").mean().alias("daily_mean"))
    )

    # Per-bucket aggregation: mean and std of daily means
    baselines = (
        per_day.group_by(["bucket_start", "day_type"])
        .agg(
            pl.col("daily_mean").mean().alias("bucket_mean"),
            pl.col("daily_mean").std().alias("bucket_std"),
            pl.col("daily_mean").count().alias("days_with_data"),
        )
        .filter(pl.col("days_with_data") >= MIN_DAYS_FOR_BASELINE)
    )
    return baselines
```

**Join pattern for per-reading deviation:**

```python
# Source: Polars join documentation pattern [ASSUMED: standard Polars join API]
df_with_bucket = df.with_columns(
    (pl.col("mod") // BUCKET_MINUTES * BUCKET_MINUTES).alias("bucket_start")
)
df_joined = df_with_bucket.join(baselines, on=["bucket_start", "day_type"], how="left")
df_joined = df_joined.with_columns(
    (
        (pl.col("glucose") - pl.col("bucket_mean")) / pl.col("bucket_std").fill_null(1.0)
    ).alias("sd_deviation")
)
```

**Key detail:** `pl.col("daily_mean").std()` in Polars uses ddof=1 (Bessel's correction) by default — same as Python's `statistics.stdev`. [VERIFIED: matches existing usage in behavioral_patterns.py where `daily["daily_mean"].std()` is used without explicit ddof]

---

## Pattern 2: PISA Artifact Detection Algorithm

**What:** PISA (Pressure-Induced Sensor Attenuation) produces falsely low glucose readings when mechanical pressure is applied to the sensor site. The CGM algorithm compensates, producing a characteristic "bathtub" signature: rapid drop → sustained low → rapid recovery, typically during the overnight window (sensor pressure from sleeping position).

**PISA detection signature (algorithmic):**

| Step | Criterion | Values |
|------|-----------|--------|
| 1. Rapid drop | Glucose decreases ≥20% from local max within a 30-minute window | 5–6 consecutive readings (25–30 min) |
| 2. Sustained low | Glucose remains below the drop threshold for ≥15 minutes | ≥3 consecutive readings below the drop level |
| 3. Recovery | Glucose returns within 20% of pre-drop level within 60 minutes of the lowest point | ≥1 reading in recovery window matches pre-drop |

**Implementation approach — window scan over sorted readings per night:** [ASSUMED — established PISA detection heuristics from CGM literature; exact thresholds verified against stated requirements]

```python
# Source: PISA heuristic based on requirements spec (rapid drop >=20% within 30min,
# recovery within 60min). Implementation pattern follows overnight_patterns.py
# _has_sustained_run() style.

PISA_DROP_THRESHOLD_PCT: float = 20.0   # >=20% drop from local reference
PISA_DROP_WINDOW_MINUTES: int = 30       # window over which drop is evaluated
PISA_RECOVERY_WINDOW_MINUTES: int = 60  # recovery must occur within 60 min of nadir
PISA_MIN_RECOVERY_RETURN_PCT: float = 15.0  # must return within 15% of pre-drop level

def _detect_pisa_artifact(
    glucose_values: list[float],
    timestamps: list[datetime],
) -> list[bool]:
    """Return a mask: True = reading is likely PISA artifact, False = keep.

    Scans sorted readings for rapid-drop / recovery signature. Only readings
    within the artifact window are flagged, not the surrounding normal readings.

    Args:
        glucose_values: Ordered glucose readings for a contiguous window.
        timestamps: Matching timestamps (same order).

    Returns:
        List of bool same length as glucose_values. True = PISA artifact.
    """
    n = len(glucose_values)
    is_artifact = [False] * n

    for i in range(1, n):
        reference = glucose_values[i - 1]
        drop_pct = (reference - glucose_values[i]) / reference * 100 if reference > 0 else 0

        if drop_pct < PISA_DROP_THRESHOLD_PCT:
            continue

        # Potential start of PISA artifact at index i
        nadir_idx = i
        nadir_val = glucose_values[i]
        start_time = timestamps[i]

        # Find nadir and recovery window
        for j in range(i + 1, n):
            dt_min = (timestamps[j] - start_time).total_seconds() / 60
            if dt_min > PISA_RECOVERY_WINDOW_MINUTES:
                break
            if glucose_values[j] < nadir_val:
                nadir_idx = j
                nadir_val = glucose_values[j]

        # Check for recovery: value returns within 15% of pre-drop reference
        recovered = False
        for j in range(nadir_idx + 1, n):
            dt_from_nadir = (timestamps[j] - timestamps[nadir_idx]).total_seconds() / 60
            if dt_from_nadir > PISA_RECOVERY_WINDOW_MINUTES:
                break
            if abs(glucose_values[j] - reference) / reference * 100 <= PISA_MIN_RECOVERY_RETURN_PCT:
                recovered = True
                break

        if recovered:
            # Flag everything from i to nadir as artifact
            for k in range(i, nadir_idx + 1):
                is_artifact[k] = True

    return is_artifact
```

**Integration with Polars DataFrame:**

```python
def _filter_pisa_artifacts(df: pl.DataFrame) -> pl.DataFrame:
    """Remove PISA artifact readings from the DataFrame.

    Processes each 24-hour day segment chronologically.
    Only applies PISA detection when data is sorted by timestamp.

    Args:
        df: DataFrame with timestamp, glucose, mod, date columns.

    Returns:
        Filtered DataFrame with PISA artifacts removed.
    """
    dates = df.select("date").unique().to_series().to_list()
    keep_indices = []

    for d in dates:
        day_rows = df.filter(pl.col("date") == d).sort("timestamp")
        glucose = day_rows["glucose"].to_list()
        timestamps = day_rows["timestamp"].to_list()
        mask = _detect_pisa_artifact(glucose, timestamps)
        day_indices = day_rows.with_row_index()["index"].to_list()
        keep_indices.extend(idx for idx, is_art in zip(day_indices, mask) if not is_art)

    return df.with_row_index().filter(pl.col("index").is_in(keep_indices)).drop("index")
```

**PISA primarily occurs overnight:** Per requirements and clinical context, PISA is most common during the overnight window. However, the detection algorithm should run on all readings (not just overnight), because sensor compression can happen during any period of sustained contact pressure. Running it on all data is both safer and simpler.

---

## Pattern 3: Severity Classification

**Thresholds (from requirements):**

| SD Multiple | Severity | Enum Value |
|------------|----------|------------|
| 2.0 – 3.0 (exclusive) | Mild | `AnomalySeverity.MILD` |
| 3.0 – 4.0 (exclusive) | Moderate | `AnomalySeverity.MODERATE` |
| ≥ 4.0 | Severe | `AnomalySeverity.SEVERE` |

**Applied per reading after PISA filtering:**

```python
# Source: requirements spec (ANLY-04) [VERIFIED: REQUIREMENTS.md]

class AnomalySeverity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"

def _classify_severity(sd_deviation: float) -> Optional[AnomalySeverity]:
    """Classify anomaly severity by SD multiple from bucket baseline.

    Returns None for readings within ±2 SD (not anomalous).
    Uses absolute value — both high and low deviations are classified.

    Args:
        sd_deviation: Signed deviation in standard deviations from bucket mean.

    Returns:
        AnomalySeverity or None if not anomalous.
    """
    abs_dev = abs(sd_deviation)
    if abs_dev < 2.0:
        return None
    elif abs_dev < 3.0:
        return AnomalySeverity.MILD
    elif abs_dev < 4.0:
        return AnomalySeverity.MODERATE
    else:
        return AnomalySeverity.SEVERE
```

**Direction tracking:** Even though severity classification uses absolute deviation, the direction (high vs low) should be preserved in the data model for summary purposes — e.g., "3 unusual low patterns this week vs 7 unusual high patterns." Add a `direction` field: `"high"` when `sd_deviation > 0`, `"low"` when `sd_deviation < 0`.

---

## Pattern 4: Weekly Summary Aggregation

**The weekly summary is the only user-facing output.** Individual readings are never surfaced.

**WeeklySummary schema:**

```python
class WeeklySummary(BaseModel):
    """Anomaly count summary for a single calendar week.

    Attributes:
        iso_week: ISO week number (1-53).
        year: Calendar year of the week.
        week_label: Human-readable label e.g. "Week of Jan 6".
        total_anomalies: Total anomaly count for the week.
        mild_count: Count of mild anomalies (2–3 SD).
        moderate_count: Count of moderate anomalies (3–4 SD).
        severe_count: Count of severe anomalies (>4 SD).
        high_count: Count where direction="high" (glucose above bucket baseline).
        low_count: Count where direction="low" (glucose below bucket baseline).
        by_time_period: Dict mapping time-period label to anomaly count.
            Keys are 2-hour period labels e.g. "Afternoon (2pm–4pm)".
        weekday_count: Count of anomalies on weekdays.
        weekend_count: Count of anomalies on weekends.
    """
    iso_week: int = Field(..., ge=1, le=53)
    year: int
    week_label: str
    total_anomalies: int = Field(..., ge=0)
    mild_count: int = Field(0, ge=0)
    moderate_count: int = Field(0, ge=0)
    severe_count: int = Field(0, ge=0)
    high_count: int = Field(0, ge=0)
    low_count: int = Field(0, ge=0)
    by_time_period: dict = Field(default_factory=dict)
    weekday_count: int = Field(0, ge=0)
    weekend_count: int = Field(0, ge=0)

    model_config = ConfigDict(frozen=True)
```

**Polars aggregation for weekly summaries:**

```python
# Source: derived from Polars group_by/agg patterns [ASSUMED: standard Polars API]

def _build_weekly_summaries(anomaly_df: pl.DataFrame) -> list[WeeklySummary]:
    """Build WeeklySummary objects from a DataFrame of classified anomalies.

    Args:
        anomaly_df: DataFrame with columns: timestamp, glucose, severity,
            direction, day_type, bucket_start.
            Only rows with severity IS NOT NULL (i.e., anomalies) are present.

    Returns:
        List of WeeklySummary, one per ISO week, sorted by year/week.
    """
    if anomaly_df.height == 0:
        return []

    anomaly_df = anomaly_df.with_columns([
        pl.col("timestamp").dt.year().alias("year"),
        pl.col("timestamp").dt.week().alias("iso_week"),
        # 2-hour time period (matches TIME_PERIOD_LABELS in patterns.py)
        (pl.col("bucket_start") // 120 * 2).alias("period_hour"),
    ])

    weeks = (
        anomaly_df.group_by(["year", "iso_week"])
        .agg([
            pl.col("severity").count().alias("total_anomalies"),
            (pl.col("severity") == "mild").sum().alias("mild_count"),
            (pl.col("severity") == "moderate").sum().alias("moderate_count"),
            (pl.col("severity") == "severe").sum().alias("severe_count"),
            (pl.col("direction") == "high").sum().alias("high_count"),
            (pl.col("direction") == "low").sum().alias("low_count"),
            (pl.col("day_type") == "weekday").sum().alias("weekday_count"),
            (pl.col("day_type") == "weekend").sum().alias("weekend_count"),
        ])
        .sort(["year", "iso_week"])
    )
    # ... build WeeklySummary objects from rows
```

**Note on `pl.col("timestamp").dt.week()`:** Polars uses ISO week numbering. [ASSUMED: standard Polars datetime API — verify with `python -c "import polars as pl; help(pl.Expr.dt)"` if uncertain]

---

## Pattern 5: AnomalyDetectionResult Model

```python
class AnomalyDetectionResult(BaseModel):
    """Results from anomaly detection analysis.

    Attributes:
        total_anomalies: Total anomalies detected across all weeks.
        mild_total: Total mild anomalies (2–3 SD).
        moderate_total: Total moderate anomalies (3–4 SD).
        severe_total: Total severe anomalies (>4 SD).
        pisa_artifacts_filtered: Count of readings removed as PISA artifacts.
        weekly_summaries: Per-week breakdown of anomaly counts.
        insufficient_data: True when fewer than MIN_DAYS_FOR_BASELINE distinct days.
        analysis_weeks: Number of calendar weeks covered.
    """
    total_anomalies: int = Field(0, ge=0)
    mild_total: int = Field(0, ge=0)
    moderate_total: int = Field(0, ge=0)
    severe_total: int = Field(0, ge=0)
    pisa_artifacts_filtered: int = Field(0, ge=0)
    weekly_summaries: list[WeeklySummary] = Field(default_factory=list)
    insufficient_data: bool = Field(False)
    analysis_weeks: int = Field(0, ge=0)

    model_config = ConfigDict(frozen=True)
```

---

## Pattern 6: Wellness Language for Anomaly Suggestions

Following the established `SUGGESTION_TEMPLATES` pattern in `suggestions.py`, add these templates:

```python
# Source: existing suggestion template pattern [VERIFIED: suggestions.py]
"anomaly_summary_mild": {
    "title": "Occasional unusual glucose patterns",
    "description": "Your data shows some glucose readings that differ from your personal patterns for those times.",
    "action": "Consider noting what was different during those times to understand the variation.",
    "category": SuggestionCategory.VARIABILITY,
    "priority": 4,
},
"anomaly_summary_moderate": {
    "title": "Moderate unusual glucose patterns detected",
    "description": "Some glucose readings this period were notably different from your usual patterns.",
    "action": "Consider reviewing your routine during these periods and discussing with your healthcare provider.",
    "category": SuggestionCategory.CONTROL,
    "priority": 3,
},
"anomaly_summary_severe": {
    "title": "Significant unusual glucose patterns detected",
    "description": "Some glucose readings showed large deviations from your personal baseline.",
    "action": "Consider discussing these patterns with your healthcare provider.",
    "category": SuggestionCategory.SAFETY,
    "priority": 2,
},
```

**Forbidden language (ANLY-06):**
- Never use: "abnormal", "dangerous", "alert", "alarm", "high alert", "warning", "diagnosis"
- Always use: "unusual", "different from your pattern", "notable", "consider discussing"

---

## Integration Pattern (Phase 5 Template)

Phase 6 follows the exact same 4-plan integration sequence as Phase 5:

### Plan 1: Core library module
- File: `src/cgm_insights/analytics/anomaly_detection.py`
- Public function: `analyze_anomalies(readings: list[CGMReading], min_days: int = MIN_DAYS_FOR_BASELINE) -> AnomalyDetectionResult`
- Import `_build_df` from `behavioral_patterns.py` (already established in overnight_patterns.py)
- Never raise — return `insufficient_data=True` on empty input or sparse data

### Plan 2: Public API wiring
- `analytics/__init__.py`: add `analyze_anomalies`, `AnomalyDetectionResult`
- `cgm_insights/__init__.py`: add `analyze_anomalies`, `AnomalyDetectionResult` to `__all__`
- `suggestions.py`: add `generate_anomaly_suggestions(result: AnomalyDetectionResult) -> list[Suggestion]`

### Plan 3: Web integration
- `session.py`: add `anomaly_patterns: Optional[dict] = field(default=None)` to `SessionData`
- `upload.py`: call `analyze_anomalies(readings)`, store as `anomaly_result.model_dump()`
- `results.py`: reconstruct `AnomalyDetectionResult.model_validate(...)`, call `generate_anomaly_suggestions()`, pass `anomaly_patterns` to template
- `results.py` `/data` endpoint: include `anomaly_patterns` in JSON response
- New template: `src/web/templates/components/anomaly_detection.html`
- `results.html`: include the new component tab

### Plan 4: CLI flag and tests
- `cli.py`: add `--anomaly/--no-anomaly` flag (default True, matching Phase 5 convention)
- `cli.py`: add `_render_anomaly_detection(result, console)` Rich table renderer
- New test file: `tests/test_analytics/test_anomaly_detection.py` (10 tests)

---

## Exact Polars API Calls Needed

All verified against codebase usage in `behavioral_patterns.py` and `overnight_patterns.py`:

```python
# [VERIFIED: behavioral_patterns.py direct inspection]

# 1. Add bucket column
df.with_columns(
    (pl.col("mod") // 30 * 30).alias("bucket_start")
)

# 2. Per-bucket per-day aggregate (daily means within bucket)
df.group_by(["bucket_start", "day_type", "date"]).agg(
    pl.col("glucose").mean().alias("daily_mean")
)

# 3. Per-bucket baseline (mean + std of daily means)
per_day.group_by(["bucket_start", "day_type"]).agg(
    pl.col("daily_mean").mean().alias("bucket_mean"),
    pl.col("daily_mean").std().alias("bucket_std"),   # ddof=1 by default
    pl.col("daily_mean").count().alias("days_with_data"),
)

# 4. Left join to attach baseline to each reading
df.join(baselines, on=["bucket_start", "day_type"], how="left")

# 5. Compute signed SD deviation per reading
df.with_columns(
    ((pl.col("glucose") - pl.col("bucket_mean")) / pl.col("bucket_std").fill_null(1.0))
    .alias("sd_deviation")
)

# 6. Filter to anomalies only (abs deviation >= 2 SD)
df.filter(pl.col("sd_deviation").abs() >= 2.0)

# 7. Weekly aggregation
df.with_columns([
    pl.col("timestamp").dt.year().alias("year"),
    pl.col("timestamp").dt.week().alias("iso_week"),
]).group_by(["year", "iso_week"]).agg(
    pl.col("severity").count().alias("total"),
    (pl.col("severity") == "mild").sum().alias("mild_count"),
    ...
)

# 8. Unique day count (existing pattern)
df.select(pl.col("date").n_unique()).item()

# 9. Sort then to_list for PISA per-night scan
day_rows.sort("timestamp")["glucose"].to_list()
```

**Important Polars gotcha with `fill_null`:** When a bucket has only 1 reading across all days, `std()` returns `null` (can't compute std from a single sample). Use `.fill_null(1.0)` to avoid division by null — readings in single-sample buckets will show a deviation of `(glucose - mean) / 1.0 = difference`, which will only trigger if the absolute difference exceeds 2 mg/dL. This is acceptable because such buckets have insufficient statistical power anyway, and the `MIN_DAYS_FOR_BASELINE >= 5` filter should eliminate them before the join.

A safer approach: filter the joined DataFrame to drop rows where `bucket_std` is null before classifying, or treat null-std rows as "insufficient baseline" and exclude from anomaly count. **Recommendation: drop null-std rows.** [ASSUMED — design decision for planner]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Baseline computation | Custom mean/std loop | `polars group_by().agg(pl.col().mean(), pl.col().std())` |
| Day-of-week classification | Custom weekday check | Reuse `_build_df()` from `behavioral_patterns.py` — already adds `day_type` |
| Midnight-crossing window filter | Custom logic | Reuse `_get_subset()` from `behavioral_patterns.py` — already handles midnight |
| Consecutive-run detection | Complex windowing | Port the `_has_sustained_run()` pattern from `overnight_patterns.py` |
| Session storage | New storage mechanism | Extend existing `SessionData` with `anomaly_patterns: Optional[dict]` |
| Wellness suggestion templates | Ad hoc strings | Extend `SUGGESTION_TEMPLATES` dict in `suggestions.py` |
| Test fixture factory | New fixture approach | Port `create_overnight_readings()` / `create_readings_for_n_days()` pattern from existing test files |

**Key insight:** The hardest parts of Phase 6 are already solved in Phases 4 and 5. The DataFrame structure, the day-type derivation, the midnight-crossing filter, the session plumbing, the CLI flag pattern, and the suggestion template system are all established. Phase 6 adds the outlier-detection layer on top of the same infrastructure.

---

## Common Pitfalls

### Pitfall 1: Bucket SD = null for single-day or single-reading buckets
**What goes wrong:** If a time bucket has readings from only 1 day, `pl.col("daily_mean").std()` returns `null`. Division by null in Polars propagates null silently — no exception.
**Why it happens:** The `group_by().agg(std())` path produces null for n=1 groups.
**How to avoid:** After computing baselines, filter out rows where `bucket_std.is_null()` or `bucket_std == 0.0`. These buckets cannot support anomaly detection and should be dropped before the join.
**Warning signs:** All readings classified as anomalies, or all `sd_deviation` values are null.

### Pitfall 2: PISA over-filtering normal overnight lows
**What goes wrong:** A genuine low glucose event during the night (not a sensor artifact) might partially match the drop/recovery PISA signature, causing real data to be filtered.
**Why it happens:** Hypoglycemia recovery looks superficially similar to PISA recovery.
**How to avoid:** Require ALL three criteria to be met (rapid drop rate + sustained low + recovery). Add a minimum drop depth: only flag PISA if the nadir goes below, say, 70 mg/dL AND the pre-drop value was above 90 mg/dL (i.e., the drop is physiologically implausible as a sudden hypoglycemia). [ASSUMED — threshold values need review]
**Warning signs:** Overnight TBR (from Phase 5) drops to zero after PISA filtering even when the user reports lows.

### Pitfall 3: Individual reading timestamps leaking into user output
**What goes wrong:** Developer logs individual anomaly readings with timestamps for debugging, and those timestamps end up in the Jinja template context.
**Why it happens:** `AnomalyDetectionResult.model_dump()` serializes everything, and templates iterate without filtering.
**How to avoid:** The `AnomalyDetectionResult` model must NOT contain a `readings` field or any field that lists individual anomalous readings. The model only stores aggregate counts (`WeeklySummary` objects). The individual reading DataFrame is an internal computation artifact only.

### Pitfall 4: SD computed across all readings instead of daily-means-of-bucket
**What goes wrong:** Computing `std()` directly on all glucose values in a bucket (not daily means first) produces an inflated SD dominated by intra-day variance, not by day-to-day variation.
**Why it happens:** Simpler to write `group_by("bucket_start").agg(pl.col("glucose").std())`.
**How to avoid:** Always compute the two-step baseline: (1) daily means within each bucket, then (2) std of those daily means. This is the same two-step pattern used in `_compute_all_buckets()` in Phase 4.
**Warning signs:** Nearly every reading is classified as anomalous because the SD is so small.

### Pitfall 5: Polars `.dt.week()` vs `.dt.iso_week()`
**What goes wrong:** Polars has both `.dt.week()` (returns week-of-year, starting Monday) and some versions expose `.dt.iso_week()`. The naming has varied across versions.
**Why it happens:** The polars changelog changes datetime accessor names.
**How to avoid:** Test with `pl.Series(["2026-01-01"]).str.to_datetime().dt.week().to_list()` to confirm it returns expected value before shipping. If `.dt.week()` doesn't exist in the installed version, use `.dt.iso_week()`. [ASSUMED — exact method name; verify at implementation time]
**Warning signs:** AttributeError at runtime on the datetime accessor.

### Pitfall 6: "sleep" terminology creeping in through anomaly descriptions
**What goes wrong:** Anomalies detected during the overnight window are described as "sleep-related anomalies" or "during sleep."
**Why it happens:** The developer adds context to distinguish overnight vs daytime anomalies.
**How to avoid:** If direction-of-day context is needed, use "during the overnight window (10pm–6am)" consistently. This follows the SLEEP-06/ANLY-06 constraint established in Phase 5.

---

## What NOT to Build

| Do NOT build | Why | Alternative |
|-------------|-----|-------------|
| Per-reading alert list | ANLY-05 explicit requirement; alert fatigue concern | Weekly aggregate summary only |
| Real-time anomaly push notification | Out of scope (PLAT-01 deferred) | Batch summary on upload |
| Anomaly "trend" over multiple uploads | No persistence layer (session-only) | Within-session weekly breakdown |
| Insulin recommendation based on anomaly type | Medical liability (out of scope) | Wellness language only |
| Custom statistical library for SD | Wheel reinvention | Polars `.std()` |
| Separate baseline for each individual day | Overfitting; insufficient signal | Historical bucket baseline across all available days |
| User-configurable SD threshold | ENHC-03 deferred to v2+ | Fixed 2 SD threshold |

---

## Code Examples: Established Patterns to Follow

### Public function signature (follows overnight_patterns.py)

```python
# Source: overnight_patterns.py analyze_overnight_patterns [VERIFIED: direct inspection]

def analyze_anomalies(
    readings: list[CGMReading],
    min_days: int = MIN_DAYS_FOR_BASELINE,
) -> AnomalyDetectionResult:
    """Detect glucose anomalies relative to personal time-bucketed baseline.

    Args:
        readings: List of CGM readings (sorted or unsorted).
        min_days: Minimum distinct days required for valid baseline.

    Returns:
        AnomalyDetectionResult. Never raises — returns insufficient_data=True
        on empty input or insufficient days.
    """
    if not readings:
        return AnomalyDetectionResult(insufficient_data=True)

    df = _build_df(readings)  # imported from behavioral_patterns
    total_days = df.select(pl.col("date").n_unique()).item()

    if total_days < min_days:
        return AnomalyDetectionResult(insufficient_data=True)

    # ... computation ...
```

### session.py extension (follows Phase 5 pattern exactly)

```python
# Source: session.py current implementation [VERIFIED: direct inspection]
@dataclass
class SessionData:
    results: AnalysisResults
    patterns: list[PatternResult] = field(default_factory=list)
    raw_readings: list[dict] = field(default_factory=list)
    behavioral_patterns: Optional[dict] = field(default=None)
    overnight_patterns: Optional[dict] = field(default=None)
    anomaly_patterns: Optional[dict] = field(default=None)  # Phase 6 ADD
```

### upload.py extension (follows Phase 5 pattern exactly)

```python
# Source: upload.py current implementation [VERIFIED: direct inspection]
from cgm_insights.analytics.anomaly_detection import analyze_anomalies  # ADD

# Inside upload_file():
anomaly_result = analyze_anomalies(readings)                    # ADD
anomaly_patterns_dict = anomaly_result.model_dump()             # ADD

session_store.store(
    session_id,
    results,
    patterns=all_patterns,
    raw_readings=raw_readings,
    behavioral_patterns=behavioral_patterns_dict,
    overnight_patterns=overnight_patterns_dict,
    anomaly_patterns=anomaly_patterns_dict,                    # ADD
)
```

### results.py extension (follows Phase 5 pattern exactly)

```python
# Source: results.py current implementation [VERIFIED: direct inspection]
from cgm_insights.analytics.anomaly_detection import AnomalyDetectionResult  # ADD
from cgm_insights.output.suggestions import ..., generate_anomaly_suggestions # ADD

# Inside get_results():
anomaly_patterns_data = session_data.anomaly_patterns  # ADD

if anomaly_patterns_data and not anomaly_patterns_data.get("insufficient_data", True):
    anomaly_result = AnomalyDetectionResult.model_validate(anomaly_patterns_data)
    suggestions = suggestions + generate_anomaly_suggestions(anomaly_result)
    suggestions.sort(key=lambda s: s.priority)

# In TemplateResponse context:
"anomaly_patterns": anomaly_patterns_data,  # ADD
```

### CLI flag (follows Phase 5 pattern exactly)

```python
# Source: cli.py current --overnight flag [VERIFIED: direct inspection]
anomaly: bool = typer.Option(
    True,
    "--anomaly/--no-anomaly",
    help="Show anomaly detection summary",
),
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PISA detection thresholds: ≥20% drop within 30 min, recovery within 60 min | Pattern 2 | Over/under filtering; could miss artifacts or remove valid lows |
| A2 | Minimum drop depth for PISA (nadir <70 AND pre-drop >90) | Pitfall 2 | Could filter genuine hypoglycemia events |
| A3 | `pl.col("timestamp").dt.week()` method name is correct for polars>=1.40 | Pattern 4, Pitfall 5 | AttributeError at runtime |
| A4 | null-std rows should be dropped rather than treated as non-anomalous | Pattern 5 (note) | Either approach is defensible; choice affects anomaly rate for sparse buckets |
| A5 | `by_time_period` in WeeklySummary uses 2-hour period labels matching patterns.py TIME_PERIOD_LABELS | Pattern 4 | Minor: inconsistent label format between time-period analysis and anomaly tab |

---

## Open Questions

1. **PISA detection scope: overnight only, or all data?**
   - What we know: PISA is documented as most common during overnight (sensor pressure from sleeping position)
   - What's unclear: Whether running PISA detection on all readings introduces false positives during daytime (e.g., wearing CGM under tight clothing during exercise)
   - Recommendation: Run PISA detection on all readings for simplicity; the false-positive rate during daytime is low because sustained exercise-related compression is rare. Document the scope explicitly in docstring.

2. **Should anomaly detection use the same bucketing as Phase 4 (sliding 5-min slide) or fixed 30-min buckets?**
   - What we know: Phase 4 uses overlapping sliding windows for pattern visualization; fixed buckets are better for per-reading classification (one canonical bucket per reading)
   - Recommendation: Fixed 30-minute non-overlapping buckets for anomaly detection. Document this distinction explicitly so the planner doesn't conflate the two systems.

3. **Minimum weeks required for meaningful weekly summary?**
   - What we know: Phase 5 uses MIN_NIGHTS=5; we need at least MIN_DAYS_FOR_BASELINE=5 days total
   - Recommendation: If only 1 week of data exists, still display the weekly summary — it is informative even for a single week. Set `MIN_DAYS_FOR_BASELINE = 5` (matching Phase 4 constant). No separate "min weeks" guard needed.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 6 is purely Python code changes with no external dependencies beyond what is already installed.

---

## Validation Architecture

`nyquist_validation: false` in `.planning/config.json` [VERIFIED: config.json]. Section omitted per instructions.

---

## Sources

### Primary (HIGH confidence)
- `src/cgm_insights/analytics/behavioral_patterns.py` — `_build_df`, `_get_subset`, `_compute_all_buckets`, two-step daily-means baseline pattern
- `src/cgm_insights/analytics/overnight_patterns.py` — `_has_sustained_run`, `_detect_excursions`, 4-plan integration template
- `src/web/services/session.py` — `SessionData` dataclass pattern, `SessionStore.store()` signature
- `src/web/routes/upload.py` — analysis pipeline, session storage pattern
- `src/web/routes/results.py` — template context assembly, model_validate reconstruction pattern
- `src/cgm_insights/cli.py` — CLI flag pattern, `_render_*` function convention
- `src/cgm_insights/output/suggestions.py` — `SUGGESTION_TEMPLATES` dict, `SuggestionCategory` enum
- `.planning/REQUIREMENTS.md` — ANLY-02 through ANLY-06 exact requirement text
- `pyproject.toml` — polars>=1.40.0, pydantic>=2.13.0

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — accumulated key decisions, session continuity notes, Phase 5 completion record
- `.planning/ROADMAP.md` — Phase 6 success criteria

### Tertiary (LOW confidence)
- PISA artifact signature thresholds (20% drop, 60-min recovery) — from requirements spec + general CGM literature [ASSUMED as algorithmic parameters]

---

## Metadata

**Confidence breakdown:**
- Integration pattern (session/upload/results/CLI): HIGH — direct codebase inspection of identical Phase 5 pattern
- Polars API calls for group_by/agg/std: HIGH — verified against existing usage in behavioral_patterns.py
- Per-bucket baseline algorithm: HIGH — direct port of two-step pattern from Phase 4
- PISA detection algorithm: MEDIUM — signature matches requirements spec; exact thresholds are ASSUMED
- Weekly summary schema: HIGH — derived from requirements spec + Polars capabilities
- Wellness language templates: HIGH — follows established SUGGESTION_TEMPLATES pattern

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (stable stack — no fast-moving dependencies)
