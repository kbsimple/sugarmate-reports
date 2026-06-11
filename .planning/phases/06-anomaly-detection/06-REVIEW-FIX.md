---
phase: 06-anomaly-detection
fixed_at: 2026-06-11T00:00:00Z
review_path: .planning/phases/06-anomaly-detection/06-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 2
skipped: 2
status: partial
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-06-11
**Source review:** .planning/phases/06-anomaly-detection/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (CR + WR): 4
- Fixed: 2
- Skipped: 2

## Fixed Issues

### CR-01: Year-Boundary Crash — `dt.year()` Mismatches ISO Week in `_build_weekly_summaries`

**Files modified:** `src/cgm_insights/analytics/anomaly_detection.py`
**Commit:** b99399c
**Applied fix:** Replaced `pl.col("timestamp").dt.year()` with `pl.col("timestamp").dt.iso_year()` in the `_build_weekly_summaries` function so the year column is always the ISO week-year. Removed the surrounding dead `try/except AttributeError` block (both branches had the same bug; `dt.iso_year()` is available in all supported Polars versions). The `fromisocalendar(year, iso_week, 1)` call now always receives a consistent ISO year, preventing `ValueError: Invalid week: 53` on year-boundary datasets.

---

### WR-01: `min_days` Parameter Not Threaded Into `_compute_bucket_baselines`

**Files modified:** `src/cgm_insights/analytics/anomaly_detection.py`
**Commit:** 1670a2b
**Applied fix:** Added `min_days: int = MIN_DAYS_FOR_BASELINE` parameter to `_compute_bucket_baselines`, updated the `.filter(pl.col("days_with_data") >= ...)` line to use it, and updated the call site in `analyze_anomalies` to pass `min_days=min_days`. The caller's `min_days` value is now fully honoured at both the early-exit guard and the per-bucket baseline filter.

---

## Skipped Issues

### WR-02: File Parsed Twice on Every Upload

**File:** `src/web/routes/upload.py:112-127`
**Reason:** Out of scope per instructions — shared architectural concern that affects all phases equally, not a Phase 6 bug.
**Original issue:** `upload.py` calls `get_parser` + `parser.parse()` twice per upload (once directly for anomaly analysis, once inside `analyze_file()`), doubling I/O and parse time.

---

### WR-03: In-Memory Session Store Has No Eviction

**File:** `src/web/services/session.py:36-135`
**Reason:** Out of scope per instructions — architectural concern not specific to Phase 6.
**Original issue:** `SessionStore._sessions` is a plain dict with no size cap, TTL, or eviction, causing unbounded memory growth under sustained load.

---

_Fixed: 2026-06-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
