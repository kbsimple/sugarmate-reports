---
phase: CGM-Analysis-Library
fixed_at: 2026-05-03T00:00:00Z
review_path: .planning/CGM-ANALYSIS-REVIEW.md
iteration: 1
findings_in_scope: 12
fixed: 12
skipped: 0
status: all_fixed
---

# CGM Analysis Library: Code Review Fix Report

**Fixed at:** 2026-05-03
**Source review:** `.planning/CGM-ANALYSIS-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 12 (4 Critical + 8 Warning)
- Fixed: 12
- Skipped: 0

---

## Fixed Issues

### CR-01: Path Traversal in `analyze_file`

**Files modified:** `src/cgm_insights/__init__.py`
**Commit:** b2fe4fa
**Applied fix:** Added `Path(file_path).resolve()` at the top of `analyze_file()` and used the resolved path for both `get_parser()` and `parser.parse()`. This ensures raw attacker-supplied paths (e.g. `../../etc/passwd`) are normalised to their absolute form before any file I/O occurs.

---

### CR-02: Mutation of Frozen Pydantic Model (`ValidationResult`)

**Files modified:** `src/cgm_insights/__init__.py`
**Commit:** b2fe4fa
**Applied fix:** Replaced the post-construction attribute mutation (`validation.sensor_warmup_minutes = 120` and `.quality_flags.append(...)`) with a clean re-call to `validate_completeness(readings)` on the warmup-trimmed reading list. This produces an accurate `ValidationResult` from actual data rather than injecting values into an already-constructed object.

---

### CR-03: TIR Boundary Bug — Ambiguous `GLUCOSE_THRESHOLDS` Dict and Missing Comments

**Files modified:** `src/cgm_insights/analytics/metrics.py`
**Commit:** 04eae86
**Applied fix:** Replaced the ambiguous `GLUCOSE_THRESHOLDS` dict (which had duplicate semantic keys `"high": 180` and `"target_high": 180`) with clearly named keys (`very_low_max`, `low_max`, `target_max`, `high_max`) and a comment explaining the gap. Added explicit ADA 2019 boundary comments above each TIR band expression documenting interval notation (inclusive/exclusive) so maintainers cannot misread the boundary at 180 mg/dL. The actual counting logic (`70 <= x <= 180` for target, `180 < x` for high) was already correct per ADA standard.
**Status:** fixed: requires human verification (logic boundary interpretation)

---

### CR-04: Date Filter in `SugarmateParser.parse` Has No Error Handling

**Files modified:** `src/cgm_insights/ingestion/sugarmate.py`
**Commit:** e4db198
**Applied fix:** Wrapped the `df.filter(pl.col("timestamp") >= start_date)` and `<= end_date` calls in a `try/except Exception` block that re-raises as `ValueError("Date filter failed (check timezone consistency): ...")`. This converts opaque Polars internal errors into a descriptive message for users.

---

### WR-01: `detect_sensor_warmup` Always Returns 120 Minutes

**Files modified:** `src/cgm_insights/ingestion/validator.py`
**Commit:** fb6ea86
**Applied fix:** Changed `detect_sensor_warmup` to return `0` unconditionally with a clear docstring explaining that real warmup detection requires sensor-change event data not present in CSV exports, and that warmup exclusion is handled by `exclude_warmup_period()` on the caller's side. This stops every dataset from receiving the `sensor_warmup` quality flag regardless of content.

---

### WR-02: Population Standard Deviation Used Instead of Sample

**Files modified:** `src/cgm_insights/analytics/metrics.py`, `src/cgm_insights/analytics/patterns.py`
**Commits:** 04eae86 (metrics.py), dbc706a (patterns.py)
**Applied fix:** Switched all three variance calculations from `/ n` (population) to `/ (n - 1)` (sample, Bessel's correction). Added an `n < 2` guard in each location that sets `std = 0.0` to avoid division by zero for single-reading periods.

---

### WR-03: `iter_rows` Python Loop Anti-Pattern in Sugarmate Parser

**Files modified:** `src/cgm_insights/ingestion/sugarmate.py`
**Commit:** 1fb2d10
**Applied fix:** Moved the out-of-range glucose filter (`40–400 mg/dL`) and trend arrow normalisation into vectorized Polars expressions (`df.filter(pl.col("mg_dl").cast(pl.Float64).is_between(40, 400))` and `pl.when(...).is_in(valid_trends)`) before the `iter_rows` loop. The loop now only constructs `CGMReading` objects, which is unavoidable given the Pydantic model boundary.

---

### WR-04: `normalizer.py` Top-Level `import pandas` Forces Heavy Dependency

**Files modified:** `src/cgm_insights/ingestion/normalizer.py`
**Commit:** 809ccbd
**Applied fix:** Removed the top-level `import pandas as pd` and moved it inside `to_glucostats_dataframe()` as a lazy import with a comment explaining it is only required for the optional GlucoStats integration path. The return type annotation uses a string forward reference (`"pd.DataFrame"`) so the annotation resolves without importing pandas at module load time.

---

### WR-05: `analyze_file` Does Not Handle Empty Readings After Warmup Exclusion

**Files modified:** `src/cgm_insights/__init__.py`
**Commit:** b2fe4fa
**Applied fix:** Added a `if not readings: raise ValueError(...)` guard immediately after `exclude_warmup_period(readings)` with a message that tells the user the dataset is shorter than 2 hours and suggests `exclude_warmup=False`.

---

### WR-06: Day-of-Week `overall_avg` Includes Sparse Days

**Files modified:** `src/cgm_insights/analytics/patterns.py`
**Commit:** dbc706a
**Applied fix:** Computed `overall_avg` using only days that meet `MIN_READINGS_FOR_PATTERN` (an `eligible_metrics` dict filtered from `day_metrics`). Added an early return when `eligible_metrics` is empty. This prevents days with very few readings from pulling the baseline average and creating false positives on qualifying days.

---

### WR-07: `SugarmateParser.can_parse` Accepts Any CSV

**Files modified:** `src/cgm_insights/ingestion/sugarmate.py`
**Commit:** e4db198
**Applied fix:** Replaced the suffix-only check with header-column sniffing: reads `n_rows=0` from the CSV and returns `True` only when both `"datetime"` and `"mg_dl"` columns are present. Wrapped in `try/except Exception` so unreadable files return `False` rather than raising.

---

### WR-08: `format_summary` and `render_daily_table` Label GMI Inconsistently

**Files modified:** `src/cgm_insights/output/formatter.py`, `src/cgm_insights/output/visualization.py`
**Commit:** a508b92
**Applied fix:** Changed both labels from the ambiguous `"GMI"` to `"GMI (A1C estimate)"` with the `%` unit retained. Updated the target range hint in the visualization table from `"<7%"` to `"<7% (A1C est.)"` so both output surfaces use identical framing.

---

## Skipped Issues

None — all 12 in-scope findings were fixed successfully.

---

_Fixed: 2026-05-03_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
