---
phase: 06-anomaly-detection
reviewed: 2026-06-11T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/cgm_insights/analytics/anomaly_detection.py
  - src/cgm_insights/output/suggestions.py
  - src/web/routes/upload.py
  - src/web/routes/results.py
  - src/web/templates/components/anomaly_detection.html
  - tests/test_analytics/test_anomaly_detection.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 6: Anomaly Detection — Code Review

**Reviewed:** 2026-06-11
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Overall the implementation is solid: Pydantic v2 models are correct (`ConfigDict(frozen=True)`, `model_dump()`, `model_validate()`), Polars is used throughout with no pandas, ANLY-05 is enforced, and all user-facing text passes regulatory language constraints. No forbidden clinical terms appear in user-visible strings; `alert alert-info` and `badge-error` are DaisyUI CSS class names and are acceptable.

Two medium-severity logic bugs were found: a loop-advancement issue in the PISA artifact scanner that allows artifact readings to become reference values in subsequent iterations, and a parameter-threading gap where `min_days` passed to `analyze_anomalies()` is not forwarded to `_compute_bucket_baselines()`. Four lower-severity issues round out the findings.

---

## Warnings

### WR-01: PISA Loop Advancement — Artifact Readings Become Reference Values

**File:** `src/cgm_insights/analytics/anomaly_detection.py:176-181`

**Issue:** When a PISA artifact is confirmed (readings `i` through `nadir_idx` are flagged), the outer `while` loop increments `i` by 1 unconditionally. The next iteration therefore uses `glucose_values[i]` — an artifact reading — as the reference for the next drop-percentage calculation. If a subsequent artifact segment produces a ≥20% relative drop against this already-suppressed reference, spurious secondary PISA detections can occur, or conversely a true consecutive PISA event may be missed because the reference baseline is wrong.

**Fix:** After flagging an artifact segment, advance `i` past the nadir so the next reference is always a non-artifact reading:

```python
if recovered:
    for idx in range(i, nadir_idx + 1):
        mask[idx] = True
    i = nadir_idx + 1  # skip past the artifact segment
    continue

i += 1
```

---

### WR-02: `min_days` Parameter Not Forwarded to `_compute_bucket_baselines`

**File:** `src/cgm_insights/analytics/anomaly_detection.py:412-441` (caller) and `anomaly_detection.py:266`

**Issue:** `analyze_anomalies(readings, min_days=N)` applies `min_days` only to the initial `days_analyzed < min_days` guard. `_compute_bucket_baselines()` always uses the module-level constant `MIN_DAYS_FOR_BASELINE` (5) regardless. Callers passing `min_days=3` expect analysis to proceed with a 3-day minimum, but per-bucket baselines still require 5 days of data; most or all buckets will be filtered out, returning 0 anomalies silently rather than `insufficient_data=True`. The behavior is surprising and undocumented.

**Fix:** Thread the parameter through, or at minimum document the discrepancy prominently. The cleanest fix:

```python
def _compute_bucket_baselines(
    df: pl.DataFrame,
    min_days: int = MIN_DAYS_FOR_BASELINE,
) -> pl.DataFrame:
    ...
    .filter(pl.col("days_with_data") >= min_days)
```

And pass `min_days` from `analyze_anomalies` to `_compute_bucket_baselines`.

---

## Info

### IN-01: `strftime("%-d")` Is Not Portable to Windows

**File:** `src/cgm_insights/analytics/anomaly_detection.py:390`

**Issue:** `%-d` (no-leading-zero day) is a POSIX extension supported on Linux and macOS, but raises `ValueError` on Windows. If CI ever runs on Windows or a Windows Docker image, `_build_weekly_summaries` crashes on every non-empty result.

**Fix:**
```python
week_label = f"Week of {monday.strftime('%b')} {monday.day}"
```

---

### IN-02: `most_affected_period` Is Non-Deterministic on Ties

**File:** `src/cgm_insights/analytics/anomaly_detection.py:378-386`

**Issue:** When two 2-hour periods have the same anomaly count, `period_df.sort("count", descending=True)["period_hour"][0]` produces an unspecified result; Polars does not guarantee stable sort order for ties. This is not a crash or incorrect aggregate, but it makes the field non-reproducible for identical input.

**Fix:** Add a secondary sort key to break ties deterministically:
```python
.sort(["count", "period_hour"], descending=[True, False])
```

---

### IN-03: ANLY-05 Test Checks Only Top-Level Keys

**File:** `tests/test_analytics/test_anomaly_detection.py:138-150`

**Issue:** The test asserts `forbidden.intersection(dumped.keys())` is empty, but only inspects top-level keys of `model_dump()`. A future developer who adds a per-reading field inside `WeeklySummary` (e.g., `sample_timestamps`) would not be caught by this test.

**Fix:** Extend the assertion to walk nested structures:
```python
def _has_forbidden_field(data, forbidden):
    if isinstance(data, dict):
        return bool(forbidden.intersection(data.keys())) or any(
            _has_forbidden_field(v, forbidden) for v in data.values()
        )
    if isinstance(data, list):
        return any(_has_forbidden_field(item, forbidden) for item in data)
    return False

assert not _has_forbidden_field(dumped, forbidden)
```

---

### IN-04: `reference <= 0` Guard Is Dead Code

**File:** `src/cgm_insights/analytics/anomaly_detection.py:141-144`

**Issue:** `CGMReading.glucose_mg_dl` is validated to be ≥ 40.0 by the Pydantic model. The `if reference <= 0: continue` guard can never be reached. It is harmless but misleads readers into thinking the input could contain zero or negative glucose values.

**Fix:** Remove the guard, or replace it with an assertion:
```python
assert reference > 0, f"glucose_mg_dl must be positive, got {reference}"
```

---

_Reviewed: 2026-06-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
