# Phase 6: Anomaly Detection - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 11 (3 new, 8 modified)
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/cgm_insights/analytics/anomaly_detection.py` | analysis module | CRUD / transform | `src/cgm_insights/analytics/overnight_patterns.py` | exact |
| `src/web/templates/components/anomaly_detection.html` | component | request-response | `src/web/templates/components/overnight_patterns.html` | exact |
| `tests/test_analytics/test_anomaly_detection.py` | test | batch | `tests/test_analytics/test_overnight_patterns.py` | exact |
| `src/cgm_insights/analytics/__init__.py` | config / barrel | — | itself (Phase 5 addition) | exact |
| `src/cgm_insights/__init__.py` | config / barrel | — | itself (Phase 5 addition) | exact |
| `src/cgm_insights/output/suggestions.py` | service | transform | itself (Phase 5 addition) | exact |
| `src/cgm_insights/cli.py` | CLI tool | request-response | itself | role-match |
| `src/web/routes/upload.py` | controller | request-response | itself (Phase 5 addition) | exact |
| `src/web/routes/results.py` | controller | request-response | itself (Phase 5 addition) | exact |
| `src/web/services/session.py` | service | request-response | itself (Phase 5 addition) | exact |
| `src/web/templates/results.html` | template | request-response | itself (Phase 5 addition) | exact |

---

## Pattern Assignments

### `src/cgm_insights/analytics/anomaly_detection.py` (analysis module, transform)

**Analog:** `src/cgm_insights/analytics/overnight_patterns.py`

**Module docstring pattern** (lines 1–6):
```python
"""Overnight glucose pattern analysis for CGM data.

Analyzes glucose behavior during the 10pm–6am window across multiple nights.
All insights use wellness language — no medical advice. The window is a proxy
for overnight periods; actual sleep timing is not inferred.
"""
```
Mirror this docstring style: one-sentence summary, domain constraints, regulatory disclaimer.

**Imports pattern** (lines 8–16):
```python
from __future__ import annotations

from typing import Optional

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from cgm_insights.analytics.behavioral_patterns import _build_df, _get_subset
from cgm_insights.models import CGMReading
```
`anomaly_detection.py` imports `_build_df` from `behavioral_patterns` (same shared utility). It does NOT need `_get_subset` since anomaly detection spans the full 24-hour timeline, not a window subset.

**Module-level constants pattern** (lines 19–24):
```python
OVERNIGHT_START_MINUTE: int = 1320
OVERNIGHT_WINDOW_MINUTES: int = 480
MIN_NIGHTS_FOR_ANALYSIS: int = 5
MIN_NIGHTS_FOR_SPLIT: int = 3
MIN_READINGS_PER_NIGHT_FOR_EXCURSION: int = 6
EXCURSION_MIN_RUN: int = 3
```
Define equivalent typed integer constants for anomaly thresholds (e.g. `MIN_DAYS_FOR_ANALYSIS`, `SPIKE_THRESHOLD_MG_DL`, `SPIKE_MIN_RISE_MG_DL`, `DROP_THRESHOLD_MG_DL`).

**Result model pattern** (lines 27–69):
```python
class OvernightAnalysisResult(BaseModel):
    """..."""
    mean_glucose: Optional[float] = Field(None, ge=40.0, le=400.0)
    tir_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    ...
    nights_with_data: int = Field(..., ge=0)
    insufficient_data: bool = Field(False)
    window_label: str = Field("10pm–6am")

    model_config = ConfigDict(frozen=True)
```
Create `AnomalyDetectionResult(BaseModel)` with `model_config = ConfigDict(frozen=True)`. All Optional fields use `Field(None, ...)` with validation bounds; required fields use `Field(..., ge=0)`. Always include `insufficient_data: bool = Field(False)` and a `days_with_data: int = Field(..., ge=0)`.

**Private helper function pattern** (lines 72–100):
```python
def _get_overnight_df(readings: list[CGMReading]) -> pl.DataFrame:
    """Build overnight-window DataFrame from CGM readings.
    ...
    """
    df = _build_df(readings)
    overnight_df = _get_subset(df, OVERNIGHT_START_MINUTE, OVERNIGHT_WINDOW_MINUTES)
    overnight_df = overnight_df.with_columns(...)
    return overnight_df
```
All private helpers are prefixed `_`, take typed args, have Google-style docstrings with Args/Returns, and never raise — they return empty DataFrames or dicts on edge cases.

**Core computation helper pattern** (lines 103–204):
```python
def _compute_metrics(overnight_df: pl.DataFrame) -> dict:
    if overnight_df.height == 0:
        return {"nights_with_data": 0}

    per_night = (
        overnight_df.group_by("night_date")
        .agg(...)
        .filter(pl.col("count") >= 3)
    )
    ...
    return {
        "mean_glucose": mean_glucose,
        ...
        "nights_with_data": nights_with_data,
    }
```
Anomaly computation helpers follow the same pattern: empty-check first (`if df.height == 0: return {...}`), use Polars `group_by().agg()` for per-day aggregation, return a plain `dict`.

**Excursion / detection loop pattern** (lines 207–289):
```python
def _has_sustained_run(values: list[float], threshold: float, above: bool) -> bool:
    run = 0
    for v in values:
        in_range = (v > threshold) if above else (v < threshold)
        if in_range:
            run += 1
            if run >= EXCURSION_MIN_RUN:
                return True
        else:
            run = 0
    return False


def _detect_excursions(overnight_df: pl.DataFrame) -> dict:
    if overnight_df.height == 0:
        return {"sustained_low_nights": 0, ...}
    ...
    for night in night_dates:
        night_rows = df_with_night_mod.filter(pl.col("night_date") == night)
        if night_rows.height < MIN_READINGS_PER_NIGHT_FOR_EXCURSION:
            continue
        ...
    return {"sustained_low_nights": ..., ...}
```
For spike/drop event detection, mirror the `_has_sustained_run` + `_detect_excursions` pairing. Use a per-reading loop for run-detection; use Polars filtering for per-day grouping. Always skip groups with insufficient readings.

**Public entry-point pattern** (lines 292–350):
```python
def analyze_overnight_patterns(
    readings: list[CGMReading],
    min_nights: int = MIN_NIGHTS_FOR_ANALYSIS,
) -> OvernightAnalysisResult:
    """Analyze glucose patterns during the 10pm–6am window.
    ...
    Returns:
        OvernightAnalysisResult. Never raises — returns insufficient_data=True
        on empty input or insufficient nights.
    """
    if not readings:
        return OvernightAnalysisResult(nights_with_data=0, insufficient_data=True)

    ...

    if metrics.get("nights_with_data", 0) < min_nights:
        return OvernightAnalysisResult(
            nights_with_data=metrics.get("nights_with_data", 0),
            insufficient_data=True,
        )

    return OvernightAnalysisResult(
        ...,
        insufficient_data=False,
    )
```
`analyze_anomaly_detection(readings, min_days=MIN_DAYS_FOR_ANALYSIS)` must:
- Return `AnomalyDetectionResult(days_with_data=0, insufficient_data=True)` on empty input (never raises).
- Re-check after per-day filtering and return `insufficient_data=True` if still below threshold.
- Final return sets `insufficient_data=False` explicitly.

**Key differences from analog:**
- Works across the full 24-hour day (no `_get_subset` window filter needed).
- Uses `date` as the grouping key instead of `night_date` (no midnight-crossing attribution needed).
- Detects rapid-rise spikes and rapid-drop events rather than sustained excursions.
- May expose per-event lists (e.g. `spike_events: list[dict]`) in addition to aggregate counts.

---

### `src/web/templates/components/anomaly_detection.html` (component, request-response)

**Analog:** `src/web/templates/components/overnight_patterns.html`

**Component header comment pattern** (lines 1–11):
```jinja2
{# Overnight Patterns component.

Parameters:
  - overnight_patterns: dict from OvernightAnalysisResult.model_dump(), or None.
    Keys: mean_glucose (float|null), ...
#}
```
Use the same `{# ComponentName component.\n\nParameters:\n  - anomaly_detection: dict ... #}` block documenting every key the template touches.

**Card wrapper pattern** (lines 12–14):
```html
<div class="card bg-base-100 shadow-md">
    <div class="card-body">
        <h3 class="card-title text-lg font-bold">Overnight Patterns (10pm–6am)</h3>
```
Wrap in `card bg-base-100 shadow-md` / `card-body` / `card-title text-lg font-bold`. The heading should say "Anomaly Detection" (or equivalent user-facing label).

**Insufficient data guard pattern** (lines 16–27):
```jinja2
{% if not overnight_patterns or overnight_patterns.insufficient_data %}
<div class="alert alert-info">
    <svg ...>...</svg>
    <div>
        <h3 class="font-bold">Not enough overnight data</h3>
        <p class="text-sm mt-1">...</p>
    </div>
</div>
{% else %}
```
Mirror identical guard: `{% if not anomaly_detection or anomaly_detection.insufficient_data %}` → `alert alert-info` with SVG icon and descriptive minimum-data message.

**Stats horizontal row pattern** (lines 32–61):
```jinja2
<div class="stats stats-horizontal shadow w-full mb-4">
    {% if overnight_patterns.mean_glucose is not none %}
    <div class="stat">
        <div class="stat-title text-xs">Mean Glucose</div>
        <div class="stat-value text-lg">{{ overnight_patterns.mean_glucose | round(0) | int }}</div>
        <div class="stat-desc">mg/dL</div>
    </div>
    {% endif %}
    ...
</div>
```
Use `stats stats-horizontal shadow w-full mb-4` for the top-level metric row. Each metric: `stat-title text-xs` / `stat-value text-lg` / `stat-desc`. Guard every metric with `{% if value is not none %}`.

**Badge list pattern** (lines 110–123):
```jinja2
<div class="flex items-center gap-2 mb-1">
    <span class="badge badge-error badge-sm">low</span>
    <span class="text-sm">{{ exc.sustained_low_nights }} of {{ exc.total_nights }} nights ...</span>
</div>
```
Use `badge badge-error badge-sm` for low/severe anomalies, `badge badge-warning badge-sm` for elevated/high anomalies. Pair each badge with a `text-sm` prose sentence.

**Wellness disclaimer pattern** (lines 128–133):
```jinja2
<div class="bg-base-200 rounded-lg p-2 mt-4">
    <p class="text-xs text-base-content/60">
        <strong>Wellness Information Only:</strong> ...
    </p>
</div>
```
Always append the wellness disclaimer block at the bottom of the card body, outside the `{% if not insufficient_data %}` block, so it always renders.

**Key differences from analog:**
- Parameter name is `anomaly_detection` (not `overnight_patterns`).
- Heading and prose describe rapid glucose changes, not overnight windows.
- May include a per-event list section (no analog for this sub-pattern; use `badge` rows as the closest match).

---

### `tests/test_analytics/test_anomaly_detection.py` (test, batch)

**Analog:** `tests/test_analytics/test_overnight_patterns.py`

**Import block pattern** (lines 1–14):
```python
"""Tests for overnight glucose pattern analysis."""
from datetime import datetime, timedelta, date

import pytest

from cgm_insights.analytics.overnight_patterns import (
    MIN_NIGHTS_FOR_ANALYSIS,
    OVERNIGHT_START_MINUTE,
    OVERNIGHT_WINDOW_MINUTES,
    OvernightAnalysisResult,
    _get_overnight_df,
    analyze_overnight_patterns,
)
from cgm_insights.models import CGMReading
```
Import module-level constants, the result model, private helpers needed for structural tests, and the public entry point. Import `CGMReading` from `cgm_insights.models`.

**Factory helper pattern** (lines 17–49):
```python
def create_overnight_readings(
    n_nights: int,
    glucose_value: float = 100.0,
    start_hour: int = 22,
    interval_minutes: int = 5,
) -> list[CGMReading]:
    """Create CGMReading objects covering n_nights of overnight data.
    ...
    """
    base = datetime(2024, 1, 8, start_hour, 0)  # Monday 22:00
    readings = []
    for night in range(n_nights):
        night_start = base + timedelta(days=night)
        for minute in range(0, 8 * 60, interval_minutes):
            readings.append(
                CGMReading(
                    timestamp=night_start + timedelta(minutes=minute),
                    glucose_mg_dl=glucose_value,
                    source="test",
                )
            )
    return readings
```
Define a `create_readings(n_days, glucose_value, ...)` factory: starts at a fixed Monday datetime, generates readings at `interval_minutes` cadence, uses `source="test"`. The factory is the only helper — no `@pytest.fixture` used in Phase 5 tests.

**Mandatory test cases to mirror:**

1. **Empty input returns insufficient_data** (line 52–57):
```python
def test_empty_readings_returns_insufficient_data():
    result = analyze_overnight_patterns([])
    assert result.insufficient_data is True
    assert result.nights_with_data == 0
    assert result.mean_glucose is None
```

2. **Below-minimum count returns insufficient_data** (lines 60–65):
```python
def test_fewer_than_min_nights_returns_insufficient_data():
    readings = create_overnight_readings(n_nights=4)
    result = analyze_overnight_patterns(readings)
    assert result.insufficient_data is True
    assert result.nights_with_data == 4
```

3. **At-minimum count produces valid result** (lines 68–75):
```python
def test_exactly_min_nights_produces_result():
    readings = create_overnight_readings(n_nights=5, glucose_value=110.0)
    result = analyze_overnight_patterns(readings)
    assert result.insufficient_data is False
    assert result.nights_with_data == 5
    assert result.mean_glucose is not None
    assert 109.0 <= result.mean_glucose <= 111.0
```

4. **Result model is frozen/immutable** (lines 163–167):
```python
def test_overnight_analysis_result_is_frozen():
    result = OvernightAnalysisResult(nights_with_data=0, insufficient_data=True)
    with pytest.raises(Exception):
        result.nights_with_data = 5  # type: ignore[misc]
```

5. **Constants test** (lines 170–175): assert all module-level constants have the expected values.

6. **Detection boundary test** (lines 125–160): test that N-1 consecutive triggering readings does NOT fire the detection, while N consecutive readings DOES. Mirror the `make_night` inner factory + normal-nights padding pattern.

**Key differences from analog:**
- Factory function generates daytime readings at any hour (not pinned to 22:00 overnight window).
- Detection boundary test verifies spike/drop logic, not `_has_sustained_run` high/low excursions.
- No `_get_overnight_df` structural test (no midnight-crossing attribution needed for anomaly detection).

---

### `src/cgm_insights/analytics/__init__.py` (barrel, config)

**Analog:** itself — Phase 5 addition pattern (lines 23–44)

**Phase 5 addition pattern to mirror** (lines 23–26, 44–47):
```python
from .overnight_patterns import (
    analyze_overnight_patterns,
    OvernightAnalysisResult,
)
```
```python
    # Overnight pattern analysis (Phase 5)
    "analyze_overnight_patterns",
    "OvernightAnalysisResult",
```
Add immediately after the Phase 5 block:
```python
from .anomaly_detection import (
    analyze_anomaly_detection,
    AnomalyDetectionResult,
)
```
And in `__all__`:
```python
    # Anomaly detection (Phase 6)
    "analyze_anomaly_detection",
    "AnomalyDetectionResult",
```

---

### `src/cgm_insights/__init__.py` (barrel, config)

**Analog:** itself — Phase 5 addition pattern (lines 38–40, 72–75)

**Phase 5 addition pattern to mirror** (lines 38–40):
```python
from .analytics import (
    ...
    analyze_overnight_patterns,
    OvernightAnalysisResult,
)
```
```python
    # Overnight pattern analysis (Phase 5)
    "analyze_overnight_patterns",
    "OvernightAnalysisResult",
```
Add immediately after those lines:
```python
    analyze_anomaly_detection,
    AnomalyDetectionResult,
```
And in `__all__`:
```python
    # Anomaly detection (Phase 6)
    "analyze_anomaly_detection",
    "AnomalyDetectionResult",
```

---

### `src/cgm_insights/output/suggestions.py` (service, transform)

**Analog:** itself — Phase 5 overnight additions (lines 20, 190–252, 373–467)

**New import to add** (mirror line 20):
```python
from cgm_insights.analytics.overnight_patterns import OvernightAnalysisResult
```
Add:
```python
from cgm_insights.analytics.anomaly_detection import AnomalyDetectionResult
```

**New template entries** (mirror lines 190–252 in `SUGGESTION_TEMPLATES`): add keys such as `"anomaly_spike"`, `"anomaly_drop"`, `"anomaly_high_frequency"` following the exact dict structure:
```python
"overnight_stable": {
    "title": "...",
    "description": "...",
    "action": "...",
    "category": SuggestionCategory.TIMING,
    "priority": 3,
},
```
All action strings must use wellness prefixes from `WELLNESS_PREFIXES`/`WELLNESS_CONNECTORS`. Safety-category templates must encourage consulting a healthcare provider.

**New generator function** (mirror lines 373–467 `generate_overnight_suggestions`):
```python
def generate_anomaly_suggestions(
    anomaly_result: AnomalyDetectionResult,
) -> list[Suggestion]:
    """Generate actionable suggestions from anomaly detection.

    Args:
        anomaly_result: Result from analyze_anomaly_detection().

    Returns:
        List of Suggestion objects sorted by priority (1=highest).
    """
    if anomaly_result.insufficient_data:
        return []

    suggestions: list[Suggestion] = []
    # ... match on anomaly_result fields, append Suggestion objects ...
    suggestions.sort(key=lambda s: s.priority)
    return suggestions
```
The function must: short-circuit on `insufficient_data`, create `Suggestion(...)` objects from `SUGGESTION_TEMPLATES`, sort by priority before returning.

---

### `src/cgm_insights/cli.py` (CLI, request-response)

**Note:** The CLI file was not directly provided for reading. The modification pattern follows what `upload.py` demonstrates for calling new analysis functions.

**Pattern to mirror** (from `upload.py` lines 19–20, 139–140):
```python
from cgm_insights.analytics.overnight_patterns import analyze_overnight_patterns
...
overnight_result = analyze_overnight_patterns(readings)
overnight_patterns_dict = overnight_result.model_dump()
```
Add after these lines:
```python
from cgm_insights.analytics.anomaly_detection import analyze_anomaly_detection
...
anomaly_result = analyze_anomaly_detection(readings)
```
In CLI output, mirror the existing `format_suggestions_rich` pattern from `suggestions.py` (lines 591–634): append anomaly suggestions to the existing suggestions list and render via Rich table.

---

### `src/web/routes/upload.py` (controller, request-response)

**Analog:** itself — Phase 5 overnight additions (lines 19–20, 139–159)

**Phase 5 import pattern to mirror** (lines 19–20):
```python
from cgm_insights.analytics.overnight_patterns import analyze_overnight_patterns
```
Add:
```python
from cgm_insights.analytics.anomaly_detection import analyze_anomaly_detection
```

**Phase 5 analysis call pattern to mirror** (lines 139–141):
```python
# Overnight pattern analysis (Phase 5)
overnight_result = analyze_overnight_patterns(readings)
overnight_patterns_dict = overnight_result.model_dump()
```
Add after:
```python
# Anomaly detection (Phase 6)
anomaly_result = analyze_anomaly_detection(readings)
anomaly_detection_dict = anomaly_result.model_dump()
```

**Phase 5 session store call pattern to mirror** (lines 152–160):
```python
session_store.store(
    session_id,
    results,
    patterns=all_patterns,
    raw_readings=raw_readings,
    behavioral_patterns=behavioral_patterns_dict,
    overnight_patterns=overnight_patterns_dict,
)
```
Add `anomaly_detection=anomaly_detection_dict` as a new keyword argument (requires `session.py` change first).

---

### `src/web/services/session.py` (service, request-response)

**Analog:** itself — Phase 5 `overnight_patterns` field additions (lines 31, 52, 69)

**Phase 5 dataclass field pattern to mirror** (lines 30–31):
```python
behavioral_patterns: Optional[dict] = field(default=None)
overnight_patterns: Optional[dict] = field(default=None)
```
Add:
```python
anomaly_detection: Optional[dict] = field(default=None)
```

**Phase 5 `store()` parameter pattern to mirror** (lines 52, 64–69):
```python
def store(
    self,
    session_id: str,
    results: AnalysisResults,
    patterns: Optional[list[PatternResult]] = None,
    raw_readings: Optional[list[dict]] = None,
    behavioral_patterns: Optional[dict] = None,
    overnight_patterns: Optional[dict] = None,
) -> None:
    ...
    self._sessions[session_id] = SessionData(
        ...
        overnight_patterns=overnight_patterns,
    )
```
Add `anomaly_detection: Optional[dict] = None` parameter and pass through to `SessionData(anomaly_detection=anomaly_detection)`.

---

### `src/web/routes/results.py` (controller, request-response)

**Analog:** itself — Phase 5 overnight additions (lines 13–14, 49–71, 121–122)

**Phase 5 import pattern to mirror** (lines 13–14):
```python
from cgm_insights.analytics.overnight_patterns import OvernightAnalysisResult
from cgm_insights.output.suggestions import generate_suggestions, generate_behavioral_suggestions, generate_overnight_suggestions
```
Add `AnomalyDetectionResult` and `generate_anomaly_suggestions` to those imports.

**Phase 5 extraction + validation pattern to mirror** (lines 49–71):
```python
# Extract overnight patterns from session (Phase 5)
overnight_patterns_data = session_data.overnight_patterns  # dict or None

# Add overnight suggestions if analysis succeeded
if overnight_patterns_data and not overnight_patterns_data.get("insufficient_data", True):
    overnight_result = OvernightAnalysisResult.model_validate(overnight_patterns_data)
    suggestions = suggestions + generate_overnight_suggestions(overnight_result)
    suggestions.sort(key=lambda s: s.priority)
```
Mirror exactly for Phase 6:
```python
# Extract anomaly detection from session (Phase 6)
anomaly_detection_data = session_data.anomaly_detection  # dict or None

if anomaly_detection_data and not anomaly_detection_data.get("insufficient_data", True):
    anomaly_result = AnomalyDetectionResult.model_validate(anomaly_detection_data)
    suggestions = suggestions + generate_anomaly_suggestions(anomaly_result)
    suggestions.sort(key=lambda s: s.priority)
```

**Phase 5 template context pattern to mirror** (lines 121–122):
```python
"behavioral_patterns": behavioral_patterns_data,  # Phase 4
"overnight_patterns": overnight_patterns_data,    # Phase 5
```
Add:
```python
"anomaly_detection": anomaly_detection_data,      # Phase 6
```

---

### `src/web/templates/results.html` (template, request-response)

**Analog:** itself — Phase 5 overnight include block (lines 124–128)

**Phase 5 include pattern to mirror** (lines 123–128):
```html
<!-- Overnight Patterns (Phase 5) -->
<div class="mb-6">
    {% with overnight_patterns=overnight_patterns %}
    {% include 'components/overnight_patterns.html' %}
    {% endwith %}
</div>
```
Add immediately after:
```html
<!-- Anomaly Detection (Phase 6) -->
<div class="mb-6">
    {% with anomaly_detection=anomaly_detection %}
    {% include 'components/anomaly_detection.html' %}
    {% endwith %}
</div>
```
Place before the `<!-- Patterns and Suggestions -->` block (line 129).

---

## Shared Patterns

### Pydantic frozen result model
**Source:** `overnight_patterns.py` lines 27–69 / `behavioral_patterns.py` lines 32–61 and 64–79
**Apply to:** `anomaly_detection.py` result model
```python
model_config = ConfigDict(frozen=True)
```
All result models are frozen. Optional numeric fields use `Field(None, ge=..., le=...)`. Required count/flag fields use `Field(..., ge=0)` or `Field(False)`.

### Never-raise public API
**Source:** `overnight_patterns.py` lines 292–350
**Apply to:** `analyze_anomaly_detection()`
The public function docstring must say "Never raises — returns insufficient_data=True on empty input or insufficient data." Every code path returns a valid result model instance.

### Polars `_build_df` shared utility
**Source:** `behavioral_patterns.py` lines 82–110
**Apply to:** `anomaly_detection.py` (import `_build_df` from `behavioral_patterns`)
```python
from cgm_insights.analytics.behavioral_patterns import _build_df
```
All analysis modules reuse this single DataFrame builder. Do not copy or reimplement it.

### Wellness language compliance
**Source:** `suggestions.py` lines 24–44
**Apply to:** `suggestions.py` new templates, component HTML, result model field docstrings
```python
WELLNESS_PREFIXES = ["Consider", "You might consider", ...]
WELLNESS_DISCLAIMER = (
    "This is for informational purposes only and is not medical advice. "
    "Always discuss glucose patterns with your healthcare provider."
)
```
No clinical metric names, no diagnosis language, no treatment recommendations.

### Component wellness disclaimer block
**Source:** `overnight_patterns.html` lines 128–133
**Apply to:** `anomaly_detection.html`
```html
<div class="bg-base-200 rounded-lg p-2 mt-4">
    <p class="text-xs text-base-content/60">
        <strong>Wellness Information Only:</strong> ...
    </p>
</div>
```
Always placed outside the `{% if not insufficient_data %}` guard so it renders regardless of data state.

### Session field extension pattern
**Source:** `session.py` lines 30–31, 52, 63–69
**Apply to:** `session.py` Phase 6 addition
Each new analysis result adds one `Optional[dict] = field(default=None)` to `SessionData`, one `Optional[dict] = None` keyword to `store()`, and one pass-through in the `SessionData(...)` constructor call.

### `model_validate` + suggestions pattern
**Source:** `results.py` lines 62–71
**Apply to:** `results.py` Phase 6 addition
```python
if data and not data.get("insufficient_data", True):
    result = ResultModel.model_validate(data)
    suggestions = suggestions + generate_X_suggestions(result)
    suggestions.sort(key=lambda s: s.priority)
```
Always guard with both a truthiness check and `insufficient_data` check before calling `model_validate`.

---

## No Analog Found

All files have clear analogs. No entries.

---

## Metadata

**Analog search scope:** `src/cgm_insights/analytics/`, `src/web/`, `tests/test_analytics/`
**Files scanned:** 11
**Pattern extraction date:** 2026-06-11

## PATTERNS COMPLETE
