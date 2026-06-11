---
phase: 06-anomaly-detection
reviewed: 2026-06-11T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/cgm_insights/analytics/anomaly_detection.py
  - src/cgm_insights/output/suggestions.py
  - src/cgm_insights/analytics/__init__.py
  - src/cgm_insights/__init__.py
  - src/web/templates/components/anomaly_detection.html
  - src/web/services/session.py
  - src/web/routes/upload.py
  - src/web/routes/results.py
  - src/web/templates/results.html
  - tests/test_analytics/test_anomaly_detection.py
  - src/cgm_insights/cli.py
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-06-11
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This review covers Phase 6 anomaly detection: the core algorithm in `anomaly_detection.py`, the `suggestions.py` integration, web routes, template components, session storage, CLI rendering, and the test suite.

Previously-fixed issues were verified: PISA loop advancement (`i = nadir_idx + 1`) is correct, the `strftime` week label is portable, secondary `period_hour` sort key is present, and `baselines.height==0` with sufficient days correctly returns `insufficient_data=False`.

One critical bug was found: `_build_weekly_summaries` pairs `dt.year()` (calendar year) with `dt.week()` (ISO week number) when building `(year, iso_week)` group keys. These must be paired together as ISO values. For dates in late December that belong to the following year's ISO week 1, `dt.year()` returns the calendar year but `dt.week()` returns 1 — this misgroups those anomalies into a phantom prior-year week 1. More dangerously, for early-January dates that belong to the prior year's ISO week 52 or 53 (e.g., 2021-01-01 through 2021-01-03 belong to ISO week 53 of **year 2020**), `dt.year()` returns 2021 but `dt.week()` returns 53. The subsequent `dt.date.fromisocalendar(2021, 53, 1)` call raises `ValueError: Invalid week: 53` because 2021 only has 52 ISO weeks — this crashes the entire upload response for any CGM dataset that contains anomalous readings spanning a year boundary.

Wellness language compliance was checked: no prohibited terms (`alarm`, `abnormal`, `dangerous`, `critical`, `hypoglycemia`, `hyperglycemia`) appear in user-facing text. `alert` appears only as a DaisyUI CSS class, which is acceptable per project constraints. The `CRITICAL:` comment in `suggestions.py` is a code comment, not user-facing text.

Three warnings address a `min_days` parameter that is silently ignored by `_compute_bucket_baselines`, a double file-parse in `upload.py`, and an unbounded in-memory session store. Three informational items cover missing test coverage for `generate_anomaly_suggestions`, a missing constant assertion, and unused `Optional` import.

---

## Critical Issues

### CR-01: Year-Boundary Crash — `dt.year()` Mismatches ISO Week in `_build_weekly_summaries`

**File:** `src/cgm_insights/analytics/anomaly_detection.py:339-348`

**Issue:** `_build_weekly_summaries` computes the `(year, iso_week)` group key using `pl.col("timestamp").dt.year()` paired with `pl.col("timestamp").dt.week()`. Polars `dt.week()` returns the **ISO week number**, but `dt.year()` returns the **calendar year** — these diverge at year boundaries.

Two failure modes:

1. **Silent data loss (wrong week label):** Dates like 2024-12-30 and 2024-12-31 are ISO week 1 of **2025**, but `dt.year()` returns 2024. The resulting key `(2024, 1)` does not match the true ISO week `(2025, 1)`, so those anomalies land in the wrong week bucket and produce an incorrect week label (`"Week of Jan 1, 2024"` instead of `"Week of Dec 30, 2024"`).

2. **Runtime crash (`ValueError`):** Dates like 2021-01-01 through 2021-01-03 are ISO week 53 of **2020**, but `dt.year()` returns 2021. The code then calls `dt.date.fromisocalendar(2021, 53, 1)`, which raises `ValueError: Invalid week: 53` because 2021 has only 52 ISO weeks. This crashes `analyze_anomalies()` — and therefore the entire upload response — for any dataset that contains anomalous readings spanning this boundary.

Polars 1.40 provides `dt.iso_year()` which returns the correct ISO week-year. Confirmed via test: `pl.Series([datetime(2021, 1, 1)]).dt.iso_year()` returns `[2020]`.

**Fix:** Replace `dt.year()` with `dt.iso_year()` in the `with_columns` block, and drop the `try/except AttributeError` fallback entirely (it is dead code in polars ≥1.15 where `dt.week()` is available; `dt.iso_year()` exists in polars ≥1.0):

```python
# Before (line 339-347):
try:
    anomaly_df = anomaly_df.with_columns([
        pl.col("timestamp").dt.year().alias("year"),
        pl.col("timestamp").dt.week().alias("iso_week"),
    ])
except AttributeError:
    anomaly_df = anomaly_df.with_columns([
        pl.col("timestamp").dt.year().alias("year"),
        pl.col("timestamp").dt.iso_week().alias("iso_week"),
    ])

# After (no try/except needed; dt.iso_year() and dt.week() both exist in polars>=1.40):
anomaly_df = anomaly_df.with_columns([
    pl.col("timestamp").dt.iso_year().alias("year"),
    pl.col("timestamp").dt.week().alias("iso_week"),
])
```

Note: both the `try` branch and the `except` branch use `dt.year()` for the `"year"` alias — the `except` branch has the same bug. The fix must use `dt.iso_year()` in both positions, or collapse to the single correct form above.

---

## Warnings

### WR-01: `min_days` Parameter Not Threaded Into `_compute_bucket_baselines`

**File:** `src/cgm_insights/analytics/anomaly_detection.py:238-273`, `451`

**Issue:** `analyze_anomalies()` accepts a `min_days` parameter (line 415) and uses it for the early-exit guard (`days_analyzed < min_days`, line 441). However, the call to `_compute_bucket_baselines(df_clean)` at line 451 passes no `min_days` argument. `_compute_bucket_baselines` hardcodes `MIN_DAYS_FOR_BASELINE` (line 269):

```python
.filter(pl.col("days_with_data") >= MIN_DAYS_FOR_BASELINE)
```

If a caller passes `min_days=10`, the early-exit check enforces 10-day minimum for the overall dataset, but individual bucket baselines are still built from buckets with as few as 5 days of data. The `min_days` contract is only half-honoured, and callers who pass a custom value get baseline quality that silently diverges from their intent.

**Fix:** Add `min_days` to `_compute_bucket_baselines` and thread it through:

```python
def _compute_bucket_baselines(df: pl.DataFrame, min_days: int = MIN_DAYS_FOR_BASELINE) -> pl.DataFrame:
    ...
    .filter(pl.col("days_with_data") >= min_days)
```

And update the call site:
```python
baselines = _compute_bucket_baselines(df_clean, min_days=min_days)
```

---

### WR-02: File Parsed Twice on Every Upload

**File:** `src/web/routes/upload.py:112-127`

**Issue:** `upload.py` parses the uploaded file twice:

1. Line 112–120: `get_parser(tmp_path)` + `parser.parse()` to get `readings` for pattern/anomaly analysis.
2. Line 123–127: `analyze_file(tmp_path, ...)` which internally calls `get_parser` + `parser.parse` again (see `src/cgm_insights/__init__.py:132-133`).

For a year of 5-minute CGM data (~105,000 rows as a CSV), this doubles the I/O and parse time on every upload. More importantly, the two parse passes may not produce identical results if the file is large and Polars reads it differently on re-read (edge case, but possible if the file changes between reads — not an issue for temp files, but still semantically redundant). The `readings` list used for anomaly detection (line 144) came from the first parse; `results` from `analyze_file` came from the second. Both use the same `exclude_warmup` flag, so they are equivalent in practice, but the duplication is fragile.

**Fix:** Refactor `analyze_file()` to accept an already-parsed `readings` list, or expose a lower-level helper that accepts readings and skips parsing:

```python
# Option A: accept pre-parsed readings in analyze_file()
async def upload_file(...):
    readings = parser.parse(tmp_path, ...)
    if exclude_warmup:
        readings = exclude_warmup_period(readings)
    results = calculate_metrics(readings, validate_completeness(readings))
    # ... rest of analysis on same `readings`
```

This is a refactor that requires changes to `analyze_file()` but removes the duplicate I/O.

---

### WR-03: In-Memory Session Store Has No Eviction — Unbounded Memory Growth

**File:** `src/web/services/session.py:36-135`

**Issue:** `SessionStore._sessions` is a plain dict with no size cap, expiry, or eviction. Each stored session holds a full `AnalysisResults` Pydantic model, a list of `PatternResult` objects, a `raw_readings` list of up to 2000 dicts, and three analysis result dicts. For a production or load-test scenario with many uploads, this will grow without bound until the process runs out of memory or is restarted. There is a `delete()` method but nothing calls it after results are displayed.

**Fix:** Add a simple LRU cap or TTL-based eviction. At minimum, cap the store size:

```python
MAX_SESSIONS = 500

def store(self, session_id: str, ...) -> None:
    if len(self._sessions) >= MAX_SESSIONS:
        # Evict oldest entry (dict preserves insertion order in Python 3.7+)
        oldest_key = next(iter(self._sessions))
        del self._sessions[oldest_key]
    self._sessions[session_id] = SessionData(...)
```

The MVP comment in the docstring acknowledges this, but there is no guard at all — even a hard cap prevents OOM in the MVP deployment.

---

## Info

### IN-01: No Tests for `generate_anomaly_suggestions`

**File:** `tests/test_analytics/test_anomaly_detection.py`

**Issue:** `generate_anomaly_suggestions()` in `suggestions.py` has no test coverage. The spec requires: at-most-1 suggestion, highest-severity tier selected, empty list if `insufficient_data=True` or `total_anomalies==0`. None of these contracts are tested. The existing test file only covers `anomaly_detection.py`; the suggestions integration is entirely untested.

**Fix:** Add at minimum three tests:

```python
from cgm_insights.analytics.anomaly_detection import AnomalyDetectionResult
from cgm_insights.output.suggestions import generate_anomaly_suggestions

def test_generate_anomaly_suggestions_insufficient_data_returns_empty():
    result = AnomalyDetectionResult(insufficient_data=True)
    assert generate_anomaly_suggestions(result) == []

def test_generate_anomaly_suggestions_zero_anomalies_returns_empty():
    result = AnomalyDetectionResult(insufficient_data=False, total_anomalies=0)
    assert generate_anomaly_suggestions(result) == []

def test_generate_anomaly_suggestions_severe_wins():
    result = AnomalyDetectionResult(
        insufficient_data=False,
        total_anomalies=10,
        mild_total=5,
        moderate_total=3,
        severe_total=2,
    )
    suggestions = generate_anomaly_suggestions(result)
    assert len(suggestions) == 1
    assert suggestions[0].title == "Significant unusual glucose patterns detected"
```

---

### IN-02: `test_module_constants` Missing `PISA_MIN_RECOVERY_RETURN_PCT`

**File:** `tests/test_analytics/test_anomaly_detection.py:153-161`

**Issue:** `test_module_constants` asserts on all module constants except `PISA_MIN_RECOVERY_RETURN_PCT`. The constant is imported at line 12 but not asserted. A future refactor could change its value (e.g., from 15.0 to 20.0) without breaking the test.

**Fix:** Add the missing assertion:

```python
assert PISA_MIN_RECOVERY_RETURN_PCT == 15.0
```

---

### IN-03: `Optional` Import Unused in `anomaly_detection.py`

**File:** `src/cgm_insights/analytics/anomaly_detection.py:17`

**Issue:** `from typing import Optional` is imported at line 17. In Python 3.10+ (and with `from __future__ import annotations` already present at line 12), `Optional[X]` can be written as `X | None`. The import is only used in two type hints in the file (`Optional[AnomalySeverity]` at line 283 and `Optional[str]` at line 377) — both could use the `X | None` syntax already available via the `__future__` import, making the `Optional` import redundant.

**Fix:** Remove the `Optional` import and update the type hints:

```python
# anomaly_detection.py line 17: remove this import
# from typing import Optional

# Line 283: change
def _classify_severity(abs_sd: float) -> AnomalySeverity | None:

# Line 377 (most_affected_period field):
most_affected_period: str | None = None
```

---

_Reviewed: 2026-06-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
