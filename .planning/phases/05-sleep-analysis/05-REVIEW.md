---
phase: 05-sleep-analysis
reviewed: 2026-06-11T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/cgm_insights/analytics/overnight_patterns.py
  - src/cgm_insights/output/suggestions.py
  - src/cgm_insights/analytics/__init__.py
  - src/cgm_insights/__init__.py
  - src/web/templates/components/overnight_patterns.html
  - src/web/services/session.py
  - src/web/routes/upload.py
  - src/web/routes/results.py
  - src/web/templates/results.html
  - tests/test_analytics/test_overnight_patterns.py
  - src/cgm_insights/cli.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-06-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 5 overnight pattern analysis is structurally complete and all four warnings from the prior review (WR-01 through WR-04) have been resolved in the current code: the `std_g is None` guard is present, the post-filter re-check fires correctly, `MIN_NIGHTS_FOR_SPLIT=3` is defined and applied, and `day_type` is re-derived from `night_date.dt.weekday()` using the correct Polars ISO weekday encoding (`>= 6` for Saturday/Sunday).

Regulatory language is clean — "sleep" is absent from all user-facing text, "NGSI" appears only in a "NEVER use" docstring comment, and none of the prohibited clinical terms appear in any UI string. The `ConfigDict(frozen=True)` constraint is satisfied. Window math, midnight-crossing OR filter, `night_date` assignment, and CV/stability formula all match spec.

Two new warnings are identified. The more subtle is a **weighting inconsistency** between `mean_glucose` (mean-of-means, equal-night weighting) and `tir_pct`/`tbr_pct` (pooled reading ratio) that produces internally inconsistent metric pairs when nightly reading counts vary. The second is a **dead code path** in `_detect_excursions` where `has_very_low` can never change the result, which obscures whether very-low differentiation was intentionally abandoned. Three info-level items cover a missing edge-case test, a `nights_with_data` semantics discrepancy in the pre-check early return, and a double-parse in the upload handler.

---

## Warnings

### WR-01: `mean_glucose` and `tir_pct` / `tbr_pct` use inconsistent weighting schemes

**File:** `src/cgm_insights/analytics/overnight_patterns.py:150-156`

**Issue:** `mean_glucose` is computed as the mean of per-night means (`per_night["daily_mean"].mean()`), which weights every night equally regardless of its reading count. `tir_pct` and `tbr_pct` are computed from pooled reading counts (`tir_count.sum() / total_readings * 100`), which weight nights with more readings more heavily. When nightly reading counts differ — common with real CGM datasets that have gap nights — the two metrics describe different implicit populations.

Concrete example: Night A has 10 readings all at 100 mg/dL (TIR 100%, mean 100). Night B has 50 readings all at 200 mg/dL (TIR 0%, mean 200). Current code produces `mean_glucose=150 mg/dL`, `tir_pct=16.7%`. A user seeing "mean 150, TIR 17%" will find the combination confusing — a mean of 150 mg/dL is consistent with substantially higher TIR than 17%.

The same inconsistency exists in `_split_stats` for the weekday/weekend sub-metrics.

**Fix:** Use consistent per-night equal weighting throughout:

```python
# In _compute_metrics, replace the pooled tir/tbr block (lines 151-156) with:
per_night = per_night.with_columns(
    (pl.col("tir_count") / pl.col("count") * 100).alias("tir_pct_night"),
    (pl.col("tbr_count") / pl.col("count") * 100).alias("tbr_pct_night"),
)
tir_pct = per_night["tir_pct_night"].mean() or 0.0
tbr_pct = per_night["tbr_pct_night"].mean() or 0.0
```

Apply the same pattern in `_split_stats`: replace `(tir / total * 100)` with the mean of per-night TIR values:

```python
def _split_stats(nights: pl.DataFrame) -> tuple[Optional[float], Optional[float]]:
    if nights.height < MIN_NIGHTS_FOR_SPLIT:
        return None, None
    mean_g = nights["daily_mean"].mean()
    nights = nights.with_columns(
        (pl.col("tir_count") / pl.col("count") * 100).alias("tir_pct_night")
    )
    tir_p = nights["tir_pct_night"].mean() or 0.0
    return mean_g, tir_p
```

---

### WR-02: `has_very_low` in `_detect_excursions` is dead code — obscures whether very-low differentiation was abandoned

**File:** `src/cgm_insights/analytics/overnight_patterns.py:272-276`

**Issue:** Lines 272–276:

```python
has_low = _has_sustained_run(glucose_values, 70, above=False)     # v < 70
has_very_low = _has_sustained_run(glucose_values, 54, above=False) # v < 54
has_high = _has_sustained_run(glucose_values, 180, above=True)

night_has_low = has_low or has_very_low
```

Because any reading below 54 is also below 70, a qualifying run for `has_very_low` is always a subset of the run checked by `has_low`. Therefore `has_very_low` can never be `True` when `has_low` is `False`. The `or has_very_low` branch is unreachable. `night_has_low` is always equal to `has_low`.

This does not cause incorrect output in the current version — `sustained_low_nights` counts correctly — but it creates two maintenance hazards: (a) the `has_very_low` computation runs on every night needlessly; (b) when `excursion_summary` is later extended with a `sustained_very_low_nights` key, a developer may copy this pattern assuming the two thresholds already produce independent counts.

**Fix — option A (remove):** If very-low differentiation is not needed:

```python
has_low = _has_sustained_run(glucose_values, 70, above=False)
has_high = _has_sustained_run(glucose_values, 180, above=True)

if has_low:
    sustained_low_nights += 1
if has_high:
    sustained_high_nights += 1
if has_low or has_high:
    total_excursion_nights += 1
```

**Fix — option B (make it meaningful):** If very-low should be tracked distinctly:

```python
has_low = _has_sustained_run(glucose_values, 70, above=False)
has_very_low = _has_sustained_run(glucose_values, 54, above=False)
has_high = _has_sustained_run(glucose_values, 180, above=True)

if has_low:
    sustained_low_nights += 1          # includes very-low
if has_very_low:
    sustained_very_low_nights += 1     # add new counter + key to return dict
if has_high:
    sustained_high_nights += 1
if has_low or has_high:
    total_excursion_nights += 1
```

---

## Info

### IN-01: Post-filter re-check code path (lines 328–332) has no dedicated test

**File:** `tests/test_analytics/test_overnight_patterns.py` (gap)

**Issue:** `analyze_overnight_patterns` has two `insufficient_data=True` return paths: (1) the pre-filter check at lines 319–323, which fires when the raw unique `night_date` count is below `min_nights`; and (2) the post-filter re-check at lines 328–332, which fires when `metrics["nights_with_data"]` falls below `min_nights` after the per-night `count >= 3` filter removes thin nights. The test suite covers path (1) via `test_fewer_than_min_nights_returns_insufficient_data` but has no test for path (2). A dataset with 5 raw nights where one has only 2 readings exercises path (2) silently.

**Fix:** Add a test:

```python
def test_post_filter_recheck_insufficient_data():
    """5 raw nights but only 4 with >= 3 readings must return insufficient_data=True."""
    readings = create_overnight_readings(n_nights=4)
    # 5th night has only 2 readings — will be dropped by count >= 3 filter
    thin_night_start = datetime(2024, 1, 12, 22, 0)
    readings += [
        CGMReading(
            timestamp=thin_night_start + timedelta(minutes=i * 5),
            glucose_mg_dl=100.0,
            source="test",
        )
        for i in range(2)
    ]
    result = analyze_overnight_patterns(readings)
    assert result.insufficient_data is True
    assert result.nights_with_data < MIN_NIGHTS_FOR_ANALYSIS
```

---

### IN-02: `nights_with_data` semantics differ between early return and full-analysis return

**File:** `src/cgm_insights/analytics/overnight_patterns.py:319-323`

**Issue:** When the pre-check fires (line 319–323), `OvernightAnalysisResult` is returned with `nights_with_data=night_count`, where `night_count` is the raw count of unique `night_date` values — including nights with fewer than 3 readings. The model docstring states: "Nights meeting the minimum readings threshold." When `insufficient_data=False` the value is `metrics["nights_with_data"]` — the count after the `>= 3` filter, which matches the docstring. The two return paths use different semantics for the same field, which can mislead downstream consumers or UI copy.

**Fix:** Either clarify in the docstring or compute the filtered count in the early return path:

```python
# Option A: Clarify the docstring for nights_with_data field:
nights_with_data: int = Field(
    ...,
    ge=0,
    description=(
        "When insufficient_data=True due to pre-filter check: distinct overnight windows "
        "with any data. When insufficient_data=False: nights with >= 3 readings."
    ),
)

# Option B: Use consistent semantics in the early return (small extra cost):
# In analyze_overnight_patterns, before the pre-check early return, count qualifying nights:
qualifying_count = (
    overnight_df.group_by("night_date")
    .agg(pl.col("glucose").count().alias("cnt"))
    .filter(pl.col("cnt") >= 3)
    .height
)
if qualifying_count < min_nights:
    return OvernightAnalysisResult(nights_with_data=qualifying_count, insufficient_data=True)
```

---

### IN-03: Upload handler parses the file twice, applying warmup exclusion twice

**File:** `src/web/routes/upload.py:112-128`

**Issue:** The upload handler calls `parser.parse()` + `exclude_warmup_period()` on the temp file directly (lines 112–120) to produce `readings` for pattern analysis, then immediately calls `analyze_file()` (lines 123–128), which internally re-parses the same temp file and re-applies warmup exclusion. The two parse runs are deterministic and produce identical data, so this is not a correctness bug. However, the file is read twice and warmup logic is applied twice, adding unnecessary latency proportional to file size (10 MB max). It also fragments the code path: if parse parameters change, both call sites must be updated consistently.

**Fix:** Replace the `analyze_file()` call with direct metric calculation using the already-parsed `readings`:

```python
from cgm_insights.ingestion import validate_completeness
from cgm_insights.analytics import calculate_metrics

# After readings = exclude_warmup_period(readings):
validation = validate_completeness(readings)
results = calculate_metrics(readings, validation)
# Remove the analyze_file() call entirely
```

---

_Reviewed: 2026-06-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
