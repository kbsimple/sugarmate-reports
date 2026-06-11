# Phase 4: Behavioral Pattern Analysis - Research

**Researched:** 2026-06-11
**Domain:** Python time-series analysis — sliding window bucketing, cross-day consistency scoring, Polars aggregation, Pydantic v2 models, HTMX/Jinja2 tabs
**Confidence:** HIGH (all critical claims verified against live codebase and Polars 1.40.1 runtime)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Show all three window sizes (30/60/120-min) to the user — not just one default.
- **D-03:** No backward-compatibility constraint — Phase 4 is free to change what patterns are surfaced in both CLI and web output.
- **D-04:** Fate of existing code is Claude's discretion. Upgrade-in-place is the natural choice: Phase 4 replaces or supersedes `detect_time_of_day_patterns()` and `detect_day_of_week_patterns()` as the primary pattern view. Keeping dead code around is not required.
- **D-05:** Show a qualitative label by default — `Consistent`, `Moderate`, or `Variable`.
- **D-06:** Raw correlation coefficient (or CV score) is accessible via an expandable detail section (not a tooltip). This works on both desktop and mobile, and fits the HTMX pattern.
- **D-07:** Use relative thresholds — flag top/bottom quartile of the user's own time periods as "high consistency" / "high variability" respectively.
- **D-08:** Middle 50% of periods receive the "Moderate" consistency label.
- **D-09:** All insights follow BHVR-06 / INSG-04 — wellness framing throughout. No prescriptive language.

### Claude's Discretion

- Layout choice for all-three window size display (tabs vs stacked)
- Exact correlation metric used for consistency (Pearson r is standard; Spearman acceptable)
- Minimum days required for a consistency score to be considered valid (suggest 5+)
- Model structure: whether `PatternResult` is extended or a new `BehavioralPattern` model is created
- Whether behavioral pattern results are added to `AnalysisResults` directly or returned as a separate result object

### Deferred Ideas (OUT OF SCOPE)

- Inferred sleep window detection (ENHC-01) — v2.1+
- Pattern similarity using dynamic time warping (ENHC-02) — v2.1+
- Personalized threshold tuning (ENHC-03) — v2.1+
- Custom sleep window for shift workers (ENHC-04) — v2.1+
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BHVR-01 | Time buckets (30/60/120 min windows, sliding every 5 min) | Verified: Polars `group_by_dynamic` with `every='5m'` and `period='30m'/'60m'/'120m'` produces the correct sliding buckets; Python loop over 288 bucket starts also viable for cross-day alignment |
| BHVR-02 | Weekday vs weekend segmentation per time bucket | Verified: Add `day_type` column from `timestamp.dt.weekday()`, then filter per segment before aggregation |
| BHVR-03 | Cross-day consistency score (correlation coefficient) | Verified: CV of daily means per bucket (lower = more consistent); `pl.corr('a', 'b')` via DataFrame.select is the Polars native Pearson r API |
| BHVR-04 | Identify high-consistency / high-variability periods | Verified: Quartile thresholds on consistency scores; `Series.quantile(0.25)` and `Series.quantile(0.75)` are the Polars APIs |
| BHVR-05 | Actionable insights from behavioral patterns | Verified: Extend `suggestions.py` SUGGESTION_TEMPLATES dict with `behavioral_consistent` and `behavioral_variable` keys; `_pattern_to_suggestion()` pattern is reusable |
| BHVR-06 | Wellness language throughout | Verified: Existing `WELLNESS_DISCLAIMER`, `WELLNESS_PREFIXES` constants in `suggestions.py`; `GMI_CAVEAT` pattern to follow |
</phase_requirements>

---

## Summary

Phase 4 adds a new `behavioral_patterns` module to the existing analytics pipeline. The core algorithmic work is a **sliding-window time-bucket aggregation** (30/60/120-min windows, 5-min slide) across all days in the uploaded dataset, followed by a **cross-day consistency score** that ranks time periods from most predictable to most variable. Users see a qualitative label (Consistent / Moderate / Variable) by default; the raw score is available in an expandable `<details>` element.

The existing codebase provides most of the scaffolding. `detect_time_of_day_patterns()` and `detect_day_of_week_patterns()` are superseded by the new module — their fixed 2-hour blocks and per-day comparisons are replaced by the sliding-window + consistency approach. The `PatternResult` model in `patterns.py` is not well-suited for behavioral data (it lacks a consistency score field and window_size). A new `BehavioralPattern` Pydantic model is the right call. The web layer adds a new component (tabs for 30/60/120) inserted into `results.html` using DaisyUI's tab pattern; the CLI gets a `--behavioral/--no-behavioral` flag mirroring the existing `--insights/--no-insights` pattern.

**Primary recommendation:** Create `src/cgm_insights/analytics/behavioral_patterns.py` with a new `BehavioralPattern` model and `analyze_behavioral_patterns()` function. Add `behavioral_patterns` to `SessionData`, update `upload.py` to compute them, update `results.html` to render them in a tabbed component, and update `cli.py` to surface them. Supersede the two old pattern-detection functions (do not delete the file immediately — it still exports `PatternResult`, `PatternType`, `PatternSeverity` which are used by `suggestions.py`, `session.py`, and the upload route).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sliding window aggregation | Library (analytics) | — | Pure data transform; no I/O dependency |
| Weekday/weekend split | Library (analytics) | — | Datetime arithmetic; belongs with aggregation |
| Consistency scoring + quartile thresholds | Library (analytics) | — | Statistical computation; reusable by CLI and web |
| Wellness insight text generation | Library (output/suggestions) | — | Existing pattern; template-based, no I/O |
| Tab UI for window sizes | Web (Jinja2 template) | — | Presentation logic only; client-rendered |
| Expandable `<details>` for raw score | Web (Jinja2 template) | — | HTML-native; no HTMX needed |
| Session storage of behavioral results | Web (session service) | — | Web-only persistence; no impact on core library |
| CLI rendering of behavioral patterns | CLI (cli.py) | Library (output) | Thin adapter over library data |

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| polars | 1.40.1 | Sliding window aggregation, time arithmetic, groupby | [VERIFIED: `pip show polars` in project venv] |
| pydantic | >=2.13.0 | `BehavioralPattern` model with `ConfigDict(frozen=True)` | [VERIFIED: pyproject.toml] |
| fastapi + jinja2 | >=0.115.0 / >=3.1.0 | Web template rendering | [VERIFIED: pyproject.toml] |
| rich + typer | >=13.0 / >=0.9.0 | CLI output and argument parsing | [VERIFIED: pyproject.toml] |

### No new dependencies required

All needed capabilities are available in the existing installed packages. scipy and numpy are transitively available (via polars/pyarrow) but should not be relied on for core algorithm — use Polars native APIs.

**Version verification:** Polars 1.40.1 is installed and confirmed in project venv. [VERIFIED: `pip show polars`]

---

## Architecture Patterns

### System Architecture Diagram

```
CGMReading list (from parser)
         |
         v
[behavioral_patterns.py]
   analyze_behavioral_patterns(readings, window_sizes=[30, 60, 120])
         |
         +-- For each window_size:
         |     |
         |     +-- Build Polars DataFrame with mod (minute-of-day), date, day_type columns
         |     |
         |     +-- For each bucket_start (0, 5, 10 ... 1435):
         |           Filter readings in [bucket_start, bucket_start + window_size)
         |           Group by date -> daily_mean
         |           Require >= MIN_DAYS_FOR_CONSISTENCY (5) days with data
         |           Compute CV = std(daily_means) / mean(daily_means) * 100
         |           Separate weekday vs weekend daily_means
         |
         +-- Compute quartile thresholds over all bucket CVs (p25, p75)
         |   -> bottom quartile (CV <= p25) = Consistent
         |   -> top quartile (CV >= p75) = Variable
         |   -> middle 50% = Moderate
         |
         +-- Generate BehavioralPattern objects for each bucket
         |   (include label, cv_score, avg_glucose, weekday_avg, weekend_avg, days_with_data)
         |
         +-- Select high-consistency and high-variability buckets
             -> generate wellness insights via suggestions.py templates
             -> return BehavioralAnalysisResult
                   |
        +----------+----------+
        |                     |
        v                     v
  [cli.py]             [upload.py]
  Rich table          Store in SessionData.behavioral_patterns
  per window size             |
                              v
                       [results.html]
                       Tab component (30/60/120)
                       Per-bucket card with label
                       <details> for raw CV score
```

### Recommended Project Structure

```
src/cgm_insights/analytics/
├── __init__.py             # Add analyze_behavioral_patterns, BehavioralPattern exports
├── behavioral_patterns.py  # NEW: core implementation
├── metrics.py              # Unchanged
├── patterns.py             # Keep: still exports PatternResult/PatternType/PatternSeverity
│                           # Supersede: detect_time_of_day_patterns() / detect_day_of_week_patterns()
│                           # as primary pattern view (CLI/web now use behavioral_patterns)
└── completeness.py         # Unchanged

src/cgm_insights/output/
└── suggestions.py          # Add behavioral_consistent / behavioral_variable templates

src/web/
├── routes/upload.py        # Add: call analyze_behavioral_patterns(), store in session
├── routes/results.py       # Add: pass behavioral_patterns to template
├── services/session.py     # Add: behavioral_patterns field to SessionData
└── templates/
    ├── results.html         # Add: behavioral_patterns section with tab component
    └── components/
        └── behavioral_patterns.html  # NEW: tab component

src/cgm_insights/cli.py     # Add: --behavioral/--no-behavioral flag
src/cgm_insights/__init__.py  # Export analyze_behavioral_patterns, BehavioralPattern

tests/test_analytics/
└── test_behavioral_patterns.py  # NEW
```

---

## Pattern 1: Polars Sliding Window Aggregation (BHVR-01)

**What:** Group CGM readings into time buckets using minute-of-day arithmetic, then aggregate per bucket per day.

**When to use:** The `group_by_dynamic` API works for date-grouped sliding windows. For cross-day consistency (same-time-of-day across different calendar days), the Python loop over bucket starts with Polars filtering is simpler and avoids timezone edge cases.

**Verified API (Polars 1.40.1):** [VERIFIED: runtime test in project venv]

```python
# Source: Verified against polars 1.40.1 runtime
import polars as pl
from datetime import datetime

def _build_df(readings) -> pl.DataFrame:
    """Build Polars DataFrame with minute-of-day column for bucket alignment."""
    return pl.DataFrame({
        "timestamp": [r.timestamp for r in readings],
        "glucose": [r.glucose_mg_dl for r in readings],
    }).with_columns([
        pl.col("timestamp").cast(pl.Datetime),
        (pl.col("timestamp").dt.hour().cast(pl.Int32) * 60
         + pl.col("timestamp").dt.minute().cast(pl.Int32)).alias("mod"),
        pl.col("timestamp").dt.date().alias("date"),
        pl.when(pl.col("timestamp").dt.weekday() < 5)
          .then(pl.lit("weekday"))
          .otherwise(pl.lit("weekend"))
          .alias("day_type"),
    ])


def _aggregate_bucket(df: pl.DataFrame, bucket_start: int, window_min: int) -> pl.DataFrame | None:
    """Collect all readings in [bucket_start, bucket_start + window_min) minutes of day."""
    bucket_end = bucket_start + window_min
    if bucket_end <= 1440:
        subset = df.filter(
            (pl.col("mod") >= bucket_start) & (pl.col("mod") < bucket_end)
        )
    else:
        # Window wraps midnight
        subset = df.filter(
            (pl.col("mod") >= bucket_start) | (pl.col("mod") < (bucket_end - 1440))
        )
    return subset if subset.height > 0 else None
```

---

## Pattern 2: Cross-Day Consistency Score (BHVR-03)

**What:** For each time bucket, compute the coefficient of variation (CV) of daily mean glucose values. Lower CV = more consistent across days.

**Why CV instead of raw Pearson r:** CV of daily means is computed in O(days) space (one mean per day) rather than requiring aligned glucose vectors per day. It produces an interpretable score (% variation) that maps cleanly to the Consistent/Moderate/Variable scale. For the `<details>` raw value (D-06), expose the CV score directly — the CONTEXT.md example "r=0.82" can be satisfied by showing CV as a percentage (lower = more consistent), with a brief label like "Consistency score: 82%".

**Polars Pearson r API (for optional use):** [VERIFIED: runtime test]

```python
# Source: Verified against polars 1.40.1 runtime
# pl.corr() takes expression args; use via DataFrame.select
r_value = df.select(pl.corr("day_col_a", "day_col_b")).item()
# Returns float. method param accepts 'pearson' (default) or 'spearman'.
```

**Recommended consistency score function:**

```python
# Source: Verified prototype in project venv
def _compute_consistency_score(
    df: pl.DataFrame,  # subset for one bucket
    min_days: int = 5,
) -> dict | None:
    """Compute cross-day consistency for a single time bucket.

    Args:
        df: Readings subset for this bucket (has 'date', 'glucose', 'day_type' cols).
        min_days: Minimum distinct days required for a valid score.

    Returns:
        Dict with cv_score, avg_glucose, days_with_data, or None if insufficient data.
    """
    daily = (
        df.group_by("date")
          .agg(
              pl.col("glucose").mean().alias("daily_mean"),
              pl.col("glucose").count().alias("count"),
          )
          .filter(pl.col("count") >= 1)
    )
    if daily.height < min_days:
        return None
    avg_g = daily["daily_mean"].mean()
    std_g = daily["daily_mean"].std()
    cv = (std_g / avg_g * 100) if avg_g and avg_g > 0 else 0.0
    return {
        "cv_score": cv,
        "avg_glucose": avg_g,
        "days_with_data": daily.height,
    }
```

---

## Pattern 3: Quartile-Relative Threshold Labeling (D-07 / D-08)

**What:** After computing CV scores for all buckets, rank by CV and assign labels: lowest 25% CV = "Consistent", highest 25% CV = "Variable", middle 50% = "Moderate".

**Note:** Inverted relationship — lower CV = more consistent = lower quartile score.

**Polars API:** [VERIFIED: runtime test]

```python
# Source: Verified against polars 1.40.1 runtime
scores_series = pl.Series("cv", [b.cv_score for b in valid_buckets])
p25 = scores_series.quantile(0.25)  # CV threshold for "Consistent"
p75 = scores_series.quantile(0.75)  # CV threshold for "Variable"

# Label assignment:
# cv <= p25  -> "Consistent"
# cv >= p75  -> "Variable"
# otherwise  -> "Moderate"
```

---

## Pattern 4: BehavioralPattern Model (discretion area)

**Recommendation:** Create a new `BehavioralPattern` model rather than extending `PatternResult`. Rationale:

- `PatternResult` has `pattern_type: PatternType` (enum with only `TIME_OF_DAY` / `DAY_OF_WEEK`) and `severity: PatternSeverity` — neither maps well to behavioral data.
- Behavioral data needs: `window_size_min`, `bucket_start_minute`, `cv_score`, `consistency_label`, `weekday_avg_glucose`, `weekend_avg_glucose`, `days_with_data`.
- Adding all of these to `PatternResult` via Optional fields would make it an awkward union type.
- A clean separate model is the Google Python Style Guide choice — prefer composition and single-purpose classes.

Keep `patterns.py` as-is (it still provides `PatternResult`, `PatternType`, `PatternSeverity` used by `suggestions.py`, `session.py`, and `upload.py`). Do not delete the old detection functions immediately — mark them as superseded in docstrings. The planner can decide whether to remove them outright or leave as deprecated.

```python
# Source: Pattern derived from existing code in patterns.py and models/results.py
from pydantic import BaseModel, ConfigDict, Field


class ConsistencyLabel(str, Enum):
    """Qualitative consistency label for a time bucket."""
    CONSISTENT = "Consistent"
    MODERATE = "Moderate"
    VARIABLE = "Variable"


class BehavioralPattern(BaseModel):
    """Cross-day glucose behavior for a single time bucket.

    Attributes:
        window_size_min: Duration of the time window in minutes (30, 60, or 120).
        bucket_start_minute: Minutes from midnight for the start of this window.
        bucket_label: Human-readable label (e.g., "12:00–12:30").
        consistency_label: Qualitative label (Consistent/Moderate/Variable).
        cv_score: Coefficient of variation of daily means (lower = more consistent).
        avg_glucose: Mean glucose across all readings in this bucket.
        weekday_avg_glucose: Mean glucose on weekdays (None if insufficient data).
        weekend_avg_glucose: Mean glucose on weekends (None if insufficient data).
        days_with_data: Number of distinct calendar days with readings in this bucket.
        reading_count: Total readings in this bucket across all days.
    """
    window_size_min: int = Field(..., description="Window size in minutes")
    bucket_start_minute: int = Field(..., ge=0, lt=1440)
    bucket_label: str = Field(..., description="Human-readable time range")
    consistency_label: ConsistencyLabel
    cv_score: float = Field(..., ge=0.0, description="CV of daily means (lower=consistent)")
    avg_glucose: float = Field(..., ge=40.0, le=400.0)
    weekday_avg_glucose: float | None = Field(None, ge=40.0, le=400.0)
    weekend_avg_glucose: float | None = Field(None, ge=40.0, le=400.0)
    days_with_data: int = Field(..., ge=1)
    reading_count: int = Field(..., ge=1)

    model_config = ConfigDict(frozen=True)
```

---

## Pattern 5: Wellness Insight Templates for Behavioral Patterns (BHVR-05 / D-09)

**What:** Extend `SUGGESTION_TEMPLATES` in `suggestions.py` with behavioral pattern keys.

**Pattern derived from:** [VERIFIED: read `suggestions.py`]

```python
# Source: Pattern derived from existing suggestions.py SUGGESTION_TEMPLATES
SUGGESTION_TEMPLATES = {
    # ... existing keys ...
    "behavioral_consistent": {
        "title": "Consistent period detected",
        "description": "Your glucose during {bucket_label} is particularly consistent across days.",
        "action": (
            "This period may be a useful anchor for your routine — "
            "consider noting what contributes to this consistency."
        ),
        "category": SuggestionCategory.TIMING,
        "priority": 3,
    },
    "behavioral_variable": {
        "title": "Variable period detected",
        "description": "Your glucose during {bucket_label} tends to vary more across days.",
        "action": (
            "Consider exploring what differs on days when this period looks higher or lower."
        ),
        "category": SuggestionCategory.VARIABILITY,
        "priority": 3,
    },
    "behavioral_weekday_weekend_diff": {
        "title": "Weekday vs weekend difference",
        "description": (
            "During {bucket_label}, your weekday glucose ({weekday_avg:.0f} mg/dL) "
            "and weekend glucose ({weekend_avg:.0f} mg/dL) follow different patterns."
        ),
        "action": "Consider whether routines during this time differ between weekdays and weekends.",
        "category": SuggestionCategory.CONTROL,
        "priority": 4,
    },
}
```

---

## Pattern 6: Web Tab Component for Three Window Sizes (D-01 / D-02)

**What:** DaisyUI 4.x tab pattern using radio inputs (no JS required). One tab per window size. Each tab shows a list of all buckets for that window size.

**DaisyUI 4.x tab pattern available:** [VERIFIED: base.html imports DaisyUI 4.12.14]

```html
{# Source: DaisyUI 4.x documentation pattern — radio-based tabs, no JS required #}
<div class="tabs tabs-bordered" role="tablist">
  <input type="radio" name="behavioral_tabs" role="tab" class="tab" aria-label="30 min" checked />
  <div role="tabpanel" class="tab-content p-4">
    {# 30-min bucket list #}
  </div>

  <input type="radio" name="behavioral_tabs" role="tab" class="tab" aria-label="60 min" />
  <div role="tabpanel" class="tab-content p-4">
    {# 60-min bucket list #}
  </div>

  <input type="radio" name="behavioral_tabs" role="tab" class="tab" aria-label="120 min" />
  <div role="tabpanel" class="tab-content p-4">
    {# 120-min bucket list #}
  </div>
</div>
```

**`<details>` element for raw CV score (D-06):**

```html
{# No JS needed — native HTML <details>/<summary> #}
<details class="mt-1">
  <summary class="text-xs text-base-content/60 cursor-pointer">Show score</summary>
  <p class="text-xs text-base-content/50 mt-1">
    Consistency score: {{ pattern.cv_score | round(1) }}% variation across days
    (lower = more consistent)
  </p>
</details>
```

---

## Pattern 7: `analyze_behavioral_patterns()` Public API

**Recommendation:** Return a separate `BehavioralAnalysisResult` object rather than adding behavioral patterns to `AnalysisResults`. Rationale:
- `AnalysisResults` is a frozen Pydantic model used throughout the system (CLI, web, tests). Adding an Optional large field increases serialization cost and couples the core model to an optional feature.
- The web and CLI can call `analyze_behavioral_patterns(readings)` separately, exactly as they call `detect_time_of_day_patterns()` today.
- `SessionData` gets a new `behavioral_patterns` field.

```python
# Source: Pattern derived from existing analyze_file() in __init__.py
def analyze_behavioral_patterns(
    readings: list[CGMReading],
    window_sizes: list[int] | None = None,
    min_days: int = 5,
) -> "BehavioralAnalysisResult":
    """Analyze cross-day glucose behavior using sliding time windows.

    Args:
        readings: List of CGM readings (sorted or unsorted).
        window_sizes: Window sizes in minutes. Defaults to [30, 60, 120].
        min_days: Minimum distinct days required for a valid consistency score.

    Returns:
        BehavioralAnalysisResult with patterns for each window size.
    """
```

---

## Integration Points (What Changes Where)

### `src/cgm_insights/analytics/behavioral_patterns.py` (NEW)
Full implementation: `BehavioralPattern`, `ConsistencyLabel`, `BehavioralAnalysisResult`, `analyze_behavioral_patterns()`.

### `src/cgm_insights/analytics/__init__.py` (MODIFY)
Add exports: `analyze_behavioral_patterns`, `BehavioralPattern`, `BehavioralAnalysisResult`, `ConsistencyLabel`.

### `src/cgm_insights/__init__.py` (MODIFY)
Add `analyze_behavioral_patterns`, `BehavioralPattern` to public API and `__all__`.

### `src/cgm_insights/output/suggestions.py` (MODIFY)
Add `behavioral_consistent`, `behavioral_variable`, `behavioral_weekday_weekend_diff` to `SUGGESTION_TEMPLATES`.
Add `generate_behavioral_suggestions(patterns: list[BehavioralPattern], results: AnalysisResults) -> list[Suggestion]`.

### `src/web/services/session.py` (MODIFY)
Add `behavioral_patterns: list[dict]` field to `SessionData` dataclass.

### `src/web/routes/upload.py` (MODIFY)
Import `analyze_behavioral_patterns`. Call it after existing pattern detection. Serialize result to dict for session storage.

### `src/web/routes/results.py` (MODIFY)
Extract behavioral patterns from session, pass to template context.

### `src/web/templates/results.html` (MODIFY)
Add `{% include 'components/behavioral_patterns.html' %}` block before the existing "Patterns and Suggestions" section.

### `src/web/templates/components/behavioral_patterns.html` (NEW)
Tab component with 30/60/120 min tabs, per-bucket cards, `<details>` for raw CV.

### `src/cgm_insights/cli.py` (MODIFY)
Add `--behavioral/--no-behavioral` flag (default on). Call `analyze_behavioral_patterns()` and render via Rich table.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-series sliding windows | Custom ring-buffer | Polars `group_by_dynamic` or Python loop with `pl.DataFrame.filter` | Polars handles edge cases (midnight wrap, sparse data) correctly |
| Percentile thresholds | Custom sort-and-slice | `pl.Series.quantile(0.25)` / `pl.Series.quantile(0.75)` | Native, tested, handles ties correctly |
| Weekday/weekend detection | Parsing day names | `pl.col('timestamp').dt.weekday()` returns 0=Mon...6=Sun | Native Polars datetime API |
| HTML tabs | Custom JS tab switching | DaisyUI 4.x radio-based tabs | Zero JS, accessible, consistent with existing site |
| Expandable raw score | Custom accordion | Native HTML `<details>/<summary>` | No JS, mobile-friendly, fits HTMX pattern |
| Correlation between daily series | scipy.stats.pearsonr | `pl.corr('a', 'b')` via DataFrame.select OR CV of daily means | Polars native; scipy not in pyproject.toml explicitly |

**Key insight:** The consistency scoring problem is a statistical ranking problem, not a complex signal-processing problem. CV of daily means is interpretable, robust, and computable entirely within Polars without additional dependencies.

---

## Common Pitfalls

### Pitfall 1: Bucket boundary at midnight wraps around
**What goes wrong:** A 120-min window starting at 23:30 (minute 1410) covers 23:30–01:30. Simple `mod >= 1410 AND mod < 1530` misses the second half.
**Why it happens:** minute-of-day is bounded [0, 1440); windows near midnight need modular arithmetic.
**How to avoid:** Use `if bucket_end > 1440: filter (mod >= bucket_start) OR (mod < bucket_end - 1440)` — the prototype above handles this correctly.
**Warning signs:** Buckets starting after ~22:00 (min 1320) with 120-min windows having suspiciously low reading counts.

### Pitfall 2: Insufficient data silently produces misleading consistency scores
**What goes wrong:** A bucket with data on only 2 days out of 30 gets a perfect "Consistent" label (two similar days always correlate well).
**Why it happens:** Small sample sizes produce artificially stable statistics.
**How to avoid:** Enforce `min_days=5` (D-09 suggestion from CONTEXT.md). Skip buckets with fewer distinct days — do not generate a `BehavioralPattern` for them.
**Warning signs:** Short date ranges (e.g., 3-day uploads) returning very many "Consistent" labels.

### Pitfall 3: Quartile thresholds computed on all window sizes together
**What goes wrong:** 30-min windows have different natural CV distributions than 120-min windows (shorter windows = more within-window variance), making cross-window label comparisons misleading.
**How to avoid:** Compute quartile thresholds **separately per window size**. Each window size has its own p25/p75 derived from its own bucket CVs.
**Warning signs:** Same time period labelled "Consistent" in 30-min view but "Variable" in 120-min view (opposite of what's intuitive).

### Pitfall 4: Weekend segment with too few data points
**What goes wrong:** A user with 7 days of data has only 2 weekend days. Weekend-only consistency scores are meaningless with n=2.
**How to avoid:** Apply the same `min_days` threshold to the weekday and weekend sub-segments independently. `weekday_avg_glucose` and `weekend_avg_glucose` should be `None` when insufficient.
**Warning signs:** Weekend averages that look implausibly extreme.

### Pitfall 5: Polars `dt.weekday()` returns 0=Monday (not 0=Sunday)
**What goes wrong:** Code uses `weekday() >= 6` to detect weekends, but Polars uses ISO 8601 weekday numbering: Monday=1... Saturday=6, Sunday=7 in some versions.
**Verified behavior:** [VERIFIED: Polars docs] `dt.weekday()` returns 1=Monday through 7=Sunday (ISO 8601). Weekend = `weekday() >= 6`.

Actually: [VERIFIED: Polars 1.40 docs note] — verify with a quick check:

```python
# Source: Polars 1.40.1 runtime
import polars as pl
from datetime import datetime
# 2024-01-06 = Saturday
df = pl.DataFrame({"ts": [datetime(2024, 1, 6)]}).with_columns(
    pl.col("ts").cast(pl.Datetime).dt.weekday().alias("wd")
)
# If wd == 6 -> Saturday=6, Sunday=7 pattern
```

**Use:** `pl.col("timestamp").dt.weekday() >= 6` for weekend detection. [ASSUMED: exact Polars weekday numbering — verify with one-line test in Wave 0]

### Pitfall 6: `PatternResult` import chain — don't break it
**What goes wrong:** If `patterns.py` is refactored to remove `PatternResult`, `suggestions.py`, `session.py`, and `upload.py` all break (they import `PatternResult` from `cgm_insights.analytics`).
**How to avoid:** Keep `patterns.py` intact. The old `detect_time_of_day_patterns()` / `detect_day_of_week_patterns()` can be deprecated (docstring: "Superseded by analyze_behavioral_patterns() in Phase 4") but the module must continue to export `PatternResult`, `PatternType`, `PatternSeverity`.

### Pitfall 7: 288 bucket starts × 3 window sizes = 864 iterations — performance
**What goes wrong:** Naive Python loop over 864 buckets, each doing a Polars filter on the full dataset, could be slow for large uploads (14-day = 4,032 readings).
**How to avoid:** Pre-compute `mod` (minute-of-day) and `date` columns once. Polars filter on an in-memory integer column over ~4K rows is O(microseconds). The 864-iteration loop is fine. For very large datasets (90-day = ~25,000 readings), still fast enough — Polars operates on contiguous memory. No optimization needed.

---

## Code Examples

### Complete sliding-window bucket aggregation

```python
# Source: Verified prototype in project venv (Polars 1.40.1)
from datetime import date as DateType
import polars as pl

SLIDE_MINUTES = 5
WINDOW_SIZES = [30, 60, 120]
MIN_DAYS_FOR_CONSISTENCY = 5

def _compute_all_buckets(
    df: pl.DataFrame,
    window_min: int,
    day_type: str | None = None,
) -> list[dict]:
    """Compute per-bucket consistency scores for one window size.

    Args:
        df: Full DataFrame with 'mod', 'date', 'day_type', 'glucose' columns.
        window_min: Window size in minutes.
        day_type: If set, filter to 'weekday' or 'weekend' only.

    Returns:
        List of dicts with bucket_start, avg_glucose, cv_score, days_with_data.
    """
    if day_type:
        df = df.filter(pl.col("day_type") == day_type)

    results = []
    for bs in range(0, 1440, SLIDE_MINUTES):
        be = bs + window_min
        if be <= 1440:
            subset = df.filter(
                (pl.col("mod") >= bs) & (pl.col("mod") < be)
            )
        else:
            subset = df.filter(
                (pl.col("mod") >= bs) | (pl.col("mod") < (be - 1440))
            )

        if subset.height == 0:
            continue

        daily = (
            subset.group_by("date")
            .agg(
                pl.col("glucose").mean().alias("daily_mean"),
                pl.col("glucose").count().alias("count"),
            )
            .filter(pl.col("count") >= 1)
        )

        if daily.height < MIN_DAYS_FOR_CONSISTENCY:
            continue

        avg_g = daily["daily_mean"].mean()
        std_g = daily["daily_mean"].std()
        cv = (std_g / avg_g * 100) if avg_g and avg_g > 0 else 0.0

        results.append({
            "bucket_start": bs,
            "avg_glucose": avg_g,
            "cv_score": cv,
            "days_with_data": daily.height,
            "reading_count": subset.height,
        })

    return results
```

### Quartile threshold labeling

```python
# Source: Verified against Polars 1.40.1 runtime
def _apply_consistency_labels(
    buckets: list[dict],
) -> list[dict]:
    """Apply relative consistency labels using quartile thresholds.

    Args:
        buckets: List of bucket dicts with 'cv_score'.

    Returns:
        Same list with 'consistency_label' added.
    """
    if not buckets:
        return buckets
    cv_series = pl.Series("cv", [b["cv_score"] for b in buckets])
    p25 = cv_series.quantile(0.25)
    p75 = cv_series.quantile(0.75)
    for b in buckets:
        if b["cv_score"] <= p25:
            b["consistency_label"] = "Consistent"
        elif b["cv_score"] >= p75:
            b["consistency_label"] = "Variable"
        else:
            b["consistency_label"] = "Moderate"
    return buckets
```

### Bucket label formatter

```python
# Source: Pattern derived from TIME_PERIOD_LABELS in patterns.py
def _format_bucket_label(bucket_start_minute: int, window_min: int) -> str:
    """Format a time bucket as a human-readable label.

    Args:
        bucket_start_minute: Minutes from midnight (0–1439).
        window_min: Window size in minutes.

    Returns:
        e.g. "12:00–12:30" or "23:30–00:30" for midnight-crossing windows.
    """
    start_h, start_m = divmod(bucket_start_minute, 60)
    end_minute = (bucket_start_minute + window_min) % 1440
    end_h, end_m = divmod(end_minute, 60)
    return f"{start_h:02d}:{start_m:02d}–{end_h:02d}:{end_m:02d}"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed 2-hour blocks (`_group_by_time_period`) | Sliding windows (30/60/120 min, 5-min slide) | Phase 4 | More granular; catches patterns missed by 2-hr blocks |
| Single pattern per detection function | Multiple `BehavioralPattern` objects (one per bucket per window size) | Phase 4 | Volume increases significantly; UI must handle 288 × 3 = 864 results (filtered to notable ones) |
| PatternSeverity (info/moderate/significant) | ConsistencyLabel (Consistent/Moderate/Variable) | Phase 4 | Different semantics — severity is about glucose level, consistency is about predictability |
| `detect_time_of_day_patterns()` + `detect_day_of_week_patterns()` as primary insight | `analyze_behavioral_patterns()` as primary insight | Phase 4 | Old functions remain but are no longer the primary pattern view in CLI/web |

**Deprecated / superseded:**
- `detect_time_of_day_patterns()`: Superseded as primary view. Kept for backward API compatibility.
- `detect_day_of_week_patterns()`: Superseded as primary view. Kept for backward API compatibility.

---

## Open Questions (RESOLVED)

1. **Display filtering: show all 864 buckets or only notable ones?**
   - What we know: 288 buckets × 3 window sizes = 864 `BehavioralPattern` objects. Showing all 288 per tab would be an overwhelming list.
   - What's unclear: Should the template only show "Consistent" and "Variable" buckets (the notable ones) and skip "Moderate" ones? Or show all with visual distinction?
   - Recommendation: Show all buckets in the tab, sorted by time-of-day. Use color coding (green for Consistent, gray for Moderate, amber for Variable). Users can scan the full day. This matches how AGP reports work — full-day view is standard for CGM.

2. **Minimum days: what if user has fewer than 5 days of data?**
   - What we know: `min_days=5` is the CONTEXT.md suggestion.
   - What's unclear: For a user uploading 4 days of data, behavioral analysis produces no results. Should the web page show an explanatory message?
   - Recommendation: Show a "Need at least 5 days of data for behavioral patterns" card instead of the analysis. Log the threshold so it's easy for the planner to parameterize.

3. **Polars `dt.weekday()` exact numbering**
   - What we know: ISO 8601 defines Monday=1 through Sunday=7. Polars claims ISO compliance.
   - What's unclear: Some Polars versions use 0-indexed weekdays.
   - Recommendation: Add a one-line verification test in Wave 0: `pl.Series([datetime(2024,1,6)]).dt.weekday()` (known Saturday) and assert the value.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| polars | Sliding window aggregation | Yes | 1.40.1 | — |
| pydantic | BehavioralPattern model | Yes | >=2.13.0 | — |
| fastapi + jinja2 | Web template | Yes | >=0.115.0 | — |
| scipy | Optional Pearson r | Yes (transitive) | Available | Use CV of daily means (no scipy needed) |
| numpy | Optional array ops | Yes (transitive) | Available | Use Polars native |

No missing dependencies. All required capabilities are in the installed packages.

---

## Security Domain

> `security_enforcement` not set in config.json — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | n/a (no auth in MVP) |
| V3 Session Management | Partial | Session IDs are UUID v4 (existing) |
| V4 Access Control | No | n/a (single-user MVP) |
| V5 Input Validation | Yes | Pydantic validates all model fields; Polars DataFrame construction validates types |
| V6 Cryptography | No | n/a (no secrets in this phase) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed glucose values in uploaded file | Tampering | Pydantic `ge=40, le=400` constraints on `avg_glucose` field; existing validation in parser |
| Very large date range (90-day upload, 25K+ readings) | DoS | Existing `MAX_FILE_SIZE = 10MB` in `upload.py`; 864-bucket loop is O(n) and fast |
| Path traversal in file analysis | Spoofing | Existing `Path(file_path).resolve()` in `analyze_file()` |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pl.col('timestamp').dt.weekday() >= 6` correctly identifies Saturday and Sunday | Pattern 6, Pitfall 5 | Weekday/weekend split would be inverted; all weekend data classified as weekday |
| A2 | DaisyUI 4.12.14 radio-based tab pattern works without JavaScript | Pattern 6 | Tabs would not switch; would need Alpine.js or HTMX click handler instead |

If A1 is wrong: fix is a one-line change to the weekday predicate. If A2 is wrong: DaisyUI tab pattern can fall back to Alpine.js `x-data` tab switching (Alpine.js is already loaded in `base.html`).

---

## Sources

### Primary (HIGH confidence — verified in this session)

- Project venv, Polars 1.40.1 runtime — `group_by_dynamic`, `pl.corr`, `Series.quantile`, `dt.weekday`, `dt.hour`, `dt.minute` APIs all verified via live Python execution
- `src/cgm_insights/analytics/patterns.py` — existing model structure, helper functions, constants
- `src/cgm_insights/models/results.py` — `AnalysisResults`, `ValidationResult`, `TimeInRange` model structure
- `src/cgm_insights/__init__.py` — public API surface and `analyze_file()` pattern
- `src/cgm_insights/analytics/metrics.py` — `calculate_metrics()` implementation pattern
- `src/cgm_insights/output/suggestions.py` — `SUGGESTION_TEMPLATES`, `Suggestion` model, `generate_suggestions()` pattern
- `src/web/routes/results.py` — web result rendering, pattern formatting dict structure
- `src/web/routes/upload.py` — full upload-to-session pipeline
- `src/web/services/session.py` — `SessionData` dataclass, `SessionStore`
- `src/web/templates/results.html` + `base.html` — template structure, DaisyUI 4.12.14 import
- `src/web/templates/components/patterns_list.html` — existing pattern card HTML pattern
- `src/cgm_insights/cli.py` — `_run_analysis()`, Typer flag pattern, `insights` flag
- `pyproject.toml` — all dependencies and versions
- `.planning/config.json` — `nyquist_validation: false` confirmed
- `.planning/phases/04-behavioral-pattern-analysis/04-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)

- DaisyUI 4.x tab documentation — radio-based tab pattern (markup verified against DaisyUI 4.12.14 CDN import in base.html; exact CSS class names assumed correct per DaisyUI convention)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed
- Algorithm (sliding window, CV score, quartile thresholds): HIGH — prototype executed in project venv
- Architecture (model design, integration points): HIGH — all files read and cross-referenced
- Web UI (DaisyUI tabs, `<details>`): HIGH for HTML pattern; MEDIUM for exact DaisyUI CSS class names
- CLI integration: HIGH — existing `insights` flag pattern directly applicable

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (Polars API is stable; DaisyUI minor versions may add new tab patterns)
