---
phase: 04-behavioral-pattern-analysis
reviewed: 2026-06-11T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/cgm_insights/analytics/behavioral_patterns.py
  - src/cgm_insights/output/suggestions.py
  - src/cgm_insights/analytics/__init__.py
  - src/cgm_insights/__init__.py
  - src/web/templates/components/behavioral_patterns.html
  - src/web/services/session.py
  - src/web/routes/upload.py
  - src/web/routes/results.py
  - src/web/templates/results.html
  - tests/test_analytics/test_behavioral_patterns.py
  - src/cgm_insights/cli.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-06-11
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 4 implements sliding-window behavioral pattern analysis using Polars, with Pydantic v2 frozen models, wellness-language suggestions, and a Jinja2/DaisyUI component. The core algorithm is correct: weekday detection via `dt.weekday() >= 6` is accurate for Polars (Saturday=6, Sunday=7), midnight-crossing window logic is correct, and the quartile labeling approach is sound. Regulatory language in all user-facing templates and suggestion strings passes the wellness-only requirement.

One critical bug exists: the CV computation crashes with a `TypeError` when `min_days=1` is passed via the public API, because `std_g` will be `None` for a single-day bucket and the guard expression does not check for it. Four warnings cover a misleading test docstring that causes the test to pass for the wrong reason, a dead Polars filter expression, a missing immutability test, and an edge case in the quartile labeler when all CV scores are identical. Two info-level items note a double file parse in the upload route and the mutable list inside a frozen Pydantic model.

## Critical Issues

### CR-01: CV computation crashes with TypeError when min_days=1

**File:** `src/cgm_insights/analytics/behavioral_patterns.py:219`

**Issue:** `std_g` is the result of `daily["daily_mean"].std()`. Polars returns `None` (not `0.0`) when a Series has a single value (ddof=1 requires at least 2 observations). The guard on line 219 only tests `if avg_g and avg_g > 0` — it does not check whether `std_g` is `None`. When a caller passes `min_days=1`, the `daily.height < min_days` guard at line 215 does not skip single-day buckets, so the expression `None / avg_g * 100` reaches execution and raises `TypeError: unsupported operand type(s) for /: 'NoneType' and 'float'`. The default value of `min_days=5` protects all internal call sites, but `min_days` is exposed in the public `analyze_behavioral_patterns` signature with no documented lower bound.

**Fix:**
```python
# Line 219: replace the bare CV expression with an explicit None guard
std_g = daily["daily_mean"].std()
avg_g = daily["daily_mean"].mean()
cv = (std_g / avg_g * 100) if (std_g is not None and avg_g and avg_g > 0) else 0.0
```

Alternatively, document and enforce `min_days >= 2` at the top of `analyze_behavioral_patterns`:
```python
if min_days < 2:
    raise ValueError("min_days must be >= 2 (std requires at least 2 observations)")
```

## Warnings

### WR-01: Test docstring claims "5 consecutive Saturdays" but creates Sat–Wed

**File:** `tests/test_analytics/test_behavioral_patterns.py:158-168`

**Issue:** `test_weekday_avg_none_when_insufficient_weekday_data` states in its docstring: *"5 consecutive Saturdays only — weekday_avg_glucose should be None for all patterns."* However, `create_readings_for_n_days(5, start_date=saturday)` advances by `timedelta(days=day)` and creates five consecutive calendar days: Saturday 2024-01-06, Sunday 2024-01-07, Monday 2024-01-08, Tuesday 2024-01-09, Wednesday 2024-01-10. This yields 3 weekday days and 2 weekend days — not "5 Saturdays with no weekday data". The assertion `pattern.weekday_avg_glucose is None` still passes because 3 weekday days is below `min_days=5`, but the stated reason ("no weekday data") is wrong. This makes the test misleading: it does not actually verify the zero-weekday-days case, and a future refactor that lowers `min_days` for weekday/weekend filtering could silently break the intent.

**Fix:** Either correct the docstring to describe what the code actually tests ("fewer than 5 weekday days"), or change the test to truly supply zero weekday days by stepping 7 days at a time:
```python
saturday = datetime(2024, 1, 6, 0, 0)
readings = []
for week in range(5):
    day_start = saturday + timedelta(weeks=week)
    for minute in range(0, 1440, 5):
        readings.append(CGMReading(
            timestamp=day_start + timedelta(minutes=minute),
            glucose_mg_dl=100.0,
            source="test",
        ))
```

The same mismatch applies to `test_weekend_avg_none_when_insufficient_weekend_data` (line 174): "5 consecutive Mondays" produces Mon–Fri, which has 0 weekend days and genuinely tests the zero-weekend case correctly. That test is sound; only the Saturday test is misleading.

### WR-02: Dead Polars filter — `.filter(count >= 1)` can never remove rows

**File:** `src/cgm_insights/analytics/behavioral_patterns.py:213`

**Issue:** After `group_by("date").agg(pl.col("glucose").count().alias("count"))`, every row in `daily` has `count >= 1` by construction — a group cannot exist with zero members. The `.filter(pl.col("count") >= 1)` on line 213 is therefore a no-op. This is dead code that adds confusion: it implies rows with `count == 0` could exist, which they cannot.

**Fix:** Remove the filter entirely:
```python
daily = (
    subset.group_by("date")
    .agg(
        pl.col("glucose").mean().alias("daily_mean"),
        pl.col("glucose").count().alias("count"),
    )
)
```
If a minimum reading count per day is ever needed, the threshold should be `>= 2` or higher with a comment explaining the reasoning.

### WR-03: No test verifying that BehavioralPattern and BehavioralAnalysisResult are immutable

**File:** `tests/test_analytics/test_behavioral_patterns.py`

**Issue:** The project specification requires `ConfigDict(frozen=True)` on result models. Both `BehavioralPattern` and `BehavioralAnalysisResult` have this, but the test suite has no test that attempts mutation and asserts it raises. Without this test, a future refactor that accidentally removes `frozen=True` would go undetected until a consumer unexpectedly mutates a result.

**Fix:** Add a test:
```python
def test_behavioral_pattern_is_immutable():
    """BehavioralPattern must reject field assignment (frozen=True)."""
    pattern = BehavioralPattern(
        window_size_min=30,
        bucket_start_minute=720,
        bucket_label="12:00–12:30",
        consistency_label=ConsistencyLabel.CONSISTENT,
        cv_score=5.0,
        avg_glucose=120.0,
        days_with_data=5,
        reading_count=50,
    )
    with pytest.raises(Exception):  # ValidationError from Pydantic frozen model
        pattern.avg_glucose = 999.0
```

### WR-04: All-equal CV scores collapse all labels to CONSISTENT

**File:** `src/cgm_insights/analytics/behavioral_patterns.py:258-263`

**Issue:** In `_apply_consistency_labels`, when all CV scores are identical (e.g., constant glucose across all days), `p25 == p75 == cv_score`. The check `b["cv_score"] <= p25` is evaluated first and is `True` for all buckets, so every bucket is labeled `CONSISTENT` — none are `VARIABLE` or `MODERATE`. This is not incorrect per the algorithm, but `generate_behavioral_suggestions` then selects up to 3 consistent patterns and generates suggestions saying "this period is consistent," which would fire for every single bucket when all data is constant. In practice this only affects artificial test data or perfectly-controlled conditions. No code break occurs, but it can flood suggestions in degenerate inputs.

**Fix:** Consider adding a guard in `generate_behavioral_suggestions` or `_apply_consistency_labels` to skip labeling when the spread (p75 - p25) is below a minimum threshold (e.g., < 1.0 CV percentage point), treating the data as uniformly consistent and suppressing redundant pattern output.

## Info

### IN-01: Upload route parses the CGM file twice for the same request

**File:** `src/web/routes/upload.py:112-128`

**Issue:** `parser.parse(tmp_path, ...)` is called at line 116 to obtain `readings` for pattern analysis. Then `analyze_file(tmp_path, ...)` is called at line 123, which internally calls `get_parser` and `parser.parse` a second time on the same temp file. For large uploads (up to the 10 MB limit), this doubles I/O and parse time per request. The `readings` variable used for behavioral/overnight/anomaly analysis comes from the first parse; `results` from `analyze_file` comes from the second. Both apply the same warmup exclusion, so results are consistent — this is a performance concern, not a correctness bug.

**Fix:** Refactor `analyze_file` to accept an already-parsed `list[CGMReading]` as an optional parameter, or compute `results` directly from the already-parsed `readings`:
```python
from cgm_insights.analytics import calculate_metrics
from cgm_insights.ingestion import validate_completeness
validation = validate_completeness(readings)
results = calculate_metrics(readings, validation)
```

### IN-02: BehavioralAnalysisResult.patterns list is mutable despite frozen=True

**File:** `src/cgm_insights/analytics/behavioral_patterns.py:74`

**Issue:** `frozen=True` in Pydantic v2 prevents field *reassignment* (`result.patterns = new_list`) but does not prevent mutation of the list object itself (`result.patterns.append(item)` succeeds). This is a known Pydantic limitation: `list` fields in frozen models are not truly immutable. No existing code mutates this list after construction, so there is no current bug. However, the model advertises immutability that is not fully enforced.

**Fix:** If true immutability is required, use `tuple[BehavioralPattern, ...]` instead of `list[BehavioralPattern]`:
```python
patterns: tuple[BehavioralPattern, ...] = Field(default_factory=tuple)
```
This is a breaking API change if callers iterate or index the field. An alternative is to document the limitation in the class docstring.

---

_Reviewed: 2026-06-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
