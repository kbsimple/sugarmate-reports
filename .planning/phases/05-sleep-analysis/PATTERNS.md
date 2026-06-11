# Phase 5: Sleep Analysis - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 11 (3 new, 8 modified)
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/cgm_insights/analytics/overnight_patterns.py` | analysis module | CRUD/transform | `src/cgm_insights/analytics/behavioral_patterns.py` | exact |
| `src/web/templates/components/overnight_patterns.html` | template component | request-response | `src/web/templates/components/behavioral_patterns.html` | exact |
| `tests/test_analytics/test_overnight_patterns.py` | test | CRUD | `tests/test_analytics/test_behavioral_patterns.py` | exact |
| `src/cgm_insights/analytics/__init__.py` | module init | — | `src/cgm_insights/analytics/__init__.py` (self) | exact |
| `src/cgm_insights/__init__.py` | package init | — | `src/cgm_insights/__init__.py` (self) | exact |
| `src/cgm_insights/output/suggestions.py` | output/service | transform | `src/cgm_insights/output/suggestions.py` (self) | exact |
| `src/cgm_insights/cli.py` | CLI | request-response | `src/cgm_insights/cli.py` (self) | exact |
| `src/web/routes/upload.py` | route | request-response | `src/web/routes/upload.py` (self) | exact |
| `src/web/routes/results.py` | route | request-response | `src/web/routes/results.py` (self) | exact |
| `src/web/services/session.py` | service | CRUD | `src/web/services/session.py` (self) | exact |
| `src/web/templates/results.html` | template | request-response | `src/web/templates/results.html` (self) | exact |

---

## Pattern Assignments

### `src/cgm_insights/analytics/overnight_patterns.py` (new — analysis module, transform)

**Analog:** `src/cgm_insights/analytics/behavioral_patterns.py`

**Imports pattern** (lines 1–16):
```python
"""Overnight glucose pattern analysis for CGM data.

Analyzes glucose behavior during the overnight window (typically 22:00–06:00)
across multiple nights. All insights use wellness language — no medical advice.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from cgm_insights.models import CGMReading
```

**Module-level constants pattern** (lines 19–21 of behavioral_patterns.py):
```python
# Define overnight window boundaries as module constants (minutes from midnight)
OVERNIGHT_START_MINUTE: int = 22 * 60   # 22:00 = 1320
OVERNIGHT_END_MINUTE: int = 6 * 60      # 06:00 = 360
MIN_NIGHTS_FOR_ANALYSIS: int = 5        # mirror MIN_DAYS_FOR_CONSISTENCY
```

**Enum pattern** (lines 24–29 of behavioral_patterns.py):
```python
class OvernightLabel(str, Enum):
    """Qualitative label for overnight glucose level."""
    STABLE = "Stable"
    ELEVATED = "Elevated"
    LOW = "Low"
```

**Pydantic result model pattern** (lines 32–79 of behavioral_patterns.py):
```python
class OvernightPattern(BaseModel):
    """Overnight glucose statistics for a single night.

    Attributes:
        night_date: Calendar date of the night (evening date).
        avg_glucose: Mean glucose during overnight window (mg/dL).
        min_glucose: Minimum glucose reading during the window (mg/dL).
        max_glucose: Maximum glucose reading during the window (mg/dL).
        cv_score: Coefficient of variation during the window.
        overnight_label: Qualitative label (Stable/Elevated/Low).
        reading_count: Total readings in the overnight window.
    """

    night_date: ...
    avg_glucose: float = Field(..., ge=40.0, le=400.0)
    min_glucose: float = Field(..., ge=40.0, le=400.0)
    max_glucose: float = Field(..., ge=40.0, le=400.0)
    cv_score: float = Field(..., ge=0.0)
    overnight_label: OvernightLabel
    reading_count: int = Field(..., ge=1)

    model_config = ConfigDict(frozen=True)


class OvernightAnalysisResult(BaseModel):
    """Results from overnight pattern analysis.

    Attributes:
        patterns: Per-night OvernightPattern objects.
        total_nights: Total nights with sufficient data.
        avg_overnight_glucose: Mean glucose across all overnight windows.
        insufficient_data: True when total_nights < MIN_NIGHTS_FOR_ANALYSIS.
    """

    patterns: list[OvernightPattern] = Field(default_factory=list)
    total_nights: int = Field(..., ge=0)
    avg_overnight_glucose: Optional[float] = Field(None, ge=40.0, le=400.0)
    insufficient_data: bool = Field(False)

    model_config = ConfigDict(frozen=True)
```

**DataFrame builder pattern** (`_build_df`, lines 82–110 of behavioral_patterns.py):
```python
def _build_overnight_df(readings: list[CGMReading]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "timestamp": [r.timestamp for r in readings],
            "glucose": [r.glucose_mg_dl for r in readings],
        }
    ).with_columns(
        [
            pl.col("timestamp").cast(pl.Datetime),
            (
                pl.col("timestamp").dt.hour().cast(pl.Int32) * 60
                + pl.col("timestamp").dt.minute().cast(pl.Int32)
            ).alias("mod"),
            pl.col("timestamp").dt.date().alias("date"),
        ]
    )
```
Key difference: overnight window crosses midnight (1320–360 mod), so filtering uses OR logic identical to `_get_subset` in behavioral_patterns.py (lines 143–152).

**Insufficient data guard pattern** (lines 291–305 of behavioral_patterns.py):
```python
def analyze_overnight_patterns(
    readings: list[CGMReading],
    min_nights: int = MIN_NIGHTS_FOR_ANALYSIS,
) -> OvernightAnalysisResult:
    if not readings:
        return OvernightAnalysisResult(
            patterns=[],
            total_nights=0,
            insufficient_data=True,
        )
    df = _build_overnight_df(readings)
    # filter to overnight window (crosses midnight)
    overnight_df = df.filter(
        (pl.col("mod") >= OVERNIGHT_START_MINUTE) | (pl.col("mod") < OVERNIGHT_END_MINUTE)
    )
    total_nights = overnight_df.select(pl.col("date").n_unique()).item()
    if total_nights < min_nights:
        return OvernightAnalysisResult(
            patterns=[],
            total_nights=total_nights,
            insufficient_data=True,
        )
    ...
```

**Key differences from behavioral_patterns.py:**
- No sliding window loop — one fixed overnight window per night
- Group by `date` (night date), not by bucket_start
- Compute per-night stats: avg, min, max, cv
- Label is threshold-based (e.g., avg >= 180 → Elevated, avg <= 70 → Low, else Stable) rather than quartile-based — this is domain-specific and does not exist in the analog
- No weekday/weekend segmentation needed for the core overnight metric (simplification)

---

### `src/web/templates/components/overnight_patterns.html` (new — template component)

**Analog:** `src/web/templates/components/behavioral_patterns.html`

**Parameter docblock pattern** (lines 1–11 of behavioral_patterns.html):
```jinja
{# Overnight Patterns component.

Parameters:
  - overnight_patterns: dict from OvernightAnalysisResult.model_dump(), or None.
    Keys: patterns (list of dicts), total_nights (int),
          avg_overnight_glucose (float|null), insufficient_data (bool).
  Each pattern dict has: night_date (str), avg_glucose (float),
    min_glucose (float), max_glucose (float), cv_score (float),
    overnight_label (str: "Stable"|"Elevated"|"Low"), reading_count (int).
#}
```

**Insufficient data state pattern** (lines 16–27 of behavioral_patterns.html):
```jinja
{% if not overnight_patterns or overnight_patterns.insufficient_data %}
<div class="alert alert-info">
    <svg ...>...</svg>
    <div>
        <h3 class="font-bold">Not enough data for overnight patterns</h3>
        <p class="text-sm mt-1">Overnight patterns require at least 5 nights of data. ...</p>
    </div>
</div>
```

**Card wrapper + wellness disclaimer pattern** (lines 12–89 of behavioral_patterns.html):
```jinja
<div class="card bg-base-100 shadow-md">
    <div class="card-body">
        <h3 class="card-title text-lg font-bold">Overnight Patterns</h3>
        ...
        {# Wellness disclaimer — always shown #}
        <div class="bg-base-200 rounded-lg p-2 mt-4">
            <p class="text-xs text-base-content/60">
                <strong>Wellness Information Only:</strong> ...
            </p>
        </div>
    </div>
</div>
```

**Badge-per-label pattern** (lines 47–53 of behavioral_patterns.html):
```jinja
{% if pattern.overnight_label == "Stable" %}
<span class="badge badge-success">Stable</span>
{% elif pattern.overnight_label == "Elevated" %}
<span class="badge badge-warning">Elevated</span>
{% else %}
<span class="badge badge-error">Low</span>
{% endif %}
```

**Key differences from behavioral_patterns.html:**
- No tabs (no window sizes) — single flat list of nights, sorted by `night_date`
- Each row shows: date, overnight_label badge, avg/min/max glucose
- `details/summary` disclosure shows cv_score (same collapsible pattern)
- No weekday/weekend sub-rows

---

### `tests/test_analytics/test_overnight_patterns.py` (new — test file)

**Analog:** `tests/test_analytics/test_behavioral_patterns.py`

**Imports pattern** (lines 1–22 of test_behavioral_patterns.py):
```python
"""Tests for overnight pattern analysis."""
from datetime import datetime, timedelta, date as DateType

import polars as pl
import pytest

from cgm_insights.analytics.overnight_patterns import (
    MIN_NIGHTS_FOR_ANALYSIS,
    OvernightAnalysisResult,
    OvernightPattern,
    OvernightLabel,
    _build_overnight_df,
    analyze_overnight_patterns,
)
from cgm_insights.models import CGMReading
```

**Fixture factory pattern** (lines 25–51 of test_behavioral_patterns.py):
```python
def create_readings_for_n_nights(
    n_nights: int,
    glucose_value: float = 100.0,
    start_date: datetime = None,
) -> list[CGMReading]:
    """Create n_nights of CGM readings at 5-minute intervals.

    Args:
        n_nights: Number of full nights of data.
        glucose_value: Constant glucose value for all readings.
        start_date: Starting datetime (defaults to 2024-01-08 22:00 Monday).

    Returns:
        List of CGMReading objects covering overnight window for n_nights.
    """
    if start_date is None:
        start_date = datetime(2024, 1, 8, 22, 0)  # 22:00 Monday
    readings = []
    for night in range(n_nights):
        night_start = start_date + timedelta(days=night)
        # 8 hours from 22:00 to 06:00 = 480 minutes
        for minute in range(0, 480, 5):
            readings.append(CGMReading(
                timestamp=night_start + timedelta(minutes=minute),
                glucose_mg_dl=glucose_value,
                source="test",
            ))
    return readings
```

**Test case pattern** — mirror these 5 test shapes from test_behavioral_patterns.py:
1. `test_empty_readings_returns_insufficient_data` — empty list → `insufficient_data=True, total_nights=0`
2. `test_fewer_than_5_nights_returns_insufficient_data` — 4 nights → `insufficient_data=True`
3. `test_exactly_5_nights_produces_patterns` — 5 nights → `insufficient_data=False`, patterns non-empty
4. Midnight-crossing filter test — reading at 23:30 and 01:00 both captured; reading at 12:00 excluded
5. Label assignment test — high glucose readings (e.g., 200 mg/dL) → `OvernightLabel.ELEVATED`; low readings (e.g., 60 mg/dL) → `OvernightLabel.LOW`; normal (100 mg/dL) → `OvernightLabel.STABLE`

**Comment style pattern** (lines 54–55 of test_behavioral_patterns.py):
```python
# --- Test 1: Empty readings returns insufficient_data=True ---

def test_empty_readings_returns_insufficient_data():
    """Empty reading list should return OvernightAnalysisResult with insufficient_data=True."""
```

---

### `src/cgm_insights/analytics/__init__.py` (modify — add exports)

**Analog:** self (lines 1–42 of analytics/__init__.py)

**Addition pattern** — append to existing import block and `__all__` exactly as `behavioral_patterns` was added (lines 17–22 and 37–41):
```python
# Add after behavioral_patterns block (line 22):
from .overnight_patterns import (
    analyze_overnight_patterns,
    OvernightPattern,
    OvernightAnalysisResult,
    OvernightLabel,
)

# Add to __all__ after "ConsistencyLabel" entry (line 41):
    # Overnight pattern analysis
    "analyze_overnight_patterns",
    "OvernightPattern",
    "OvernightAnalysisResult",
    "OvernightLabel",
```

---

### `src/cgm_insights/__init__.py` (modify — add exports)

**Analog:** self (lines 1–74 of cgm_insights/__init__.py)

**Addition pattern** — mirror how `analyze_behavioral_patterns` and `BehavioralPattern` were added (lines 36–38):
```python
# Add to analytics import block (after BehavioralPattern, line 38):
    analyze_overnight_patterns,
    OvernightAnalysisResult,

# Add to __all__ (after "BehavioralPattern" entry):
    # Overnight pattern analysis
    "analyze_overnight_patterns",
    "OvernightAnalysisResult",
```

---

### `src/cgm_insights/output/suggestions.py` (modify — add overnight templates + function)

**Analog:** self (lines 162–306 of suggestions.py)

**Template dict entry pattern** (lines 162–188 of suggestions.py):
```python
# Add to SUGGESTION_TEMPLATES dict:
"overnight_elevated": {
    "title": "Elevated overnight glucose detected",
    "description": "Your glucose tends to be higher during the overnight window.",
    "action": "Consider discussing overnight glucose patterns with your healthcare provider.",
    "category": SuggestionCategory.CONTROL,
    "priority": 2,
},
"overnight_low": {
    "title": "Lower overnight glucose detected",
    "description": "Your glucose tends to be lower during overnight hours.",
    "action": "Be mindful of this pattern and consider having glucose sources available.",
    "category": SuggestionCategory.SAFETY,
    "priority": 1,
},
"overnight_variable": {
    "title": "Variable overnight glucose",
    "description": "Your overnight glucose varies considerably across nights.",
    "action": "Consider tracking what might contribute to overnight variability.",
    "category": SuggestionCategory.VARIABILITY,
    "priority": 3,
},
```

**New function pattern** — mirror `generate_behavioral_suggestions` (lines 224–306 of suggestions.py):
```python
def generate_overnight_suggestions(
    overnight_result: OvernightAnalysisResult,
) -> list[Suggestion]:
    """Generate suggestions from overnight pattern analysis.

    Args:
        overnight_result: Result from analyze_overnight_patterns().

    Returns:
        List of Suggestion objects sorted by priority (1=highest).
    """
    if not overnight_result.patterns:
        return []

    suggestions: list[Suggestion] = []
    # similar pattern: select notable nights, cap at 3
    elevated = [p for p in overnight_result.patterns if p.overnight_label == OvernightLabel.ELEVATED][:3]
    low = [p for p in overnight_result.patterns if p.overnight_label == OvernightLabel.LOW][:3]
    ...
    suggestions.sort(key=lambda s: s.priority)
    return suggestions
```

**Import addition** — add at top of suggestions.py after behavioral_patterns imports (lines 15–18):
```python
from cgm_insights.analytics.overnight_patterns import (
    OvernightAnalysisResult,
    OvernightLabel,
)
```

---

### `src/cgm_insights/cli.py` (modify — add `--overnight` flag)

**Analog:** self (lines 56–259 of cli.py)

**Render helper function pattern** (lines 56–109 of cli.py) — `_render_behavioral_patterns`:
```python
def _render_overnight_patterns(
    result,
    console: Console,
) -> None:
    """Render overnight patterns as a Rich table.

    Args:
        result: OvernightAnalysisResult from analyze_overnight_patterns().
        console: Rich Console for output.
    """
    from rich.table import Table

    console.print("\n[bold cyan]Overnight Patterns[/bold cyan]")
    console.print(f"[dim]({result.total_nights} nights of data)[/dim]\n")

    table = Table(title="Overnight Window (22:00–06:00)", show_header=True, header_style="bold")
    table.add_column("Night", style="white", width=12)
    table.add_column("Label", style="cyan", width=12)
    table.add_column("Avg Glucose", style="white", width=12)
    table.add_column("Min / Max", style="dim", width=14)
    ...
    console.print(table)
```

**`_run_analysis` parameter addition** (lines 112–121 of cli.py) — add `overnight: bool` parameter alongside `behavioral: bool`:
```python
def _run_analysis(
    ...
    behavioral: bool,
    overnight: bool,       # ADD THIS
    console: Console,
) -> None:
```

**Flag handler block pattern** (lines 195–207 of cli.py) — add after behavioral block:
```python
    if overnight and readings:
        try:
            overnight_result = analyze_overnight_patterns(readings)
            if overnight_result.insufficient_data:
                console.print(
                    "\n[yellow]Overnight patterns require at least 5 nights of data.[/yellow]"
                )
            else:
                _render_overnight_patterns(overnight_result, console)
        except Exception as e:
            console.print(f"\n[yellow]Could not generate overnight patterns: {e}[/yellow]")
    elif overnight and not readings:
        console.print("\n[yellow]Overnight patterns require data. No readings available.[/yellow]")
```

**Typer option pattern** (lines 238–244 of cli.py) — add to both `analyze` and `download_and_analyze` commands:
```python
    overnight: bool = typer.Option(
        True,
        "--overnight/--no-overnight",
        help="Show overnight glucose patterns (22:00–06:00 window)",
    ),
```

**Import addition** (lines 40–43 of cli.py) — add alongside behavioral_patterns import:
```python
from cgm_insights.analytics.overnight_patterns import (
    analyze_overnight_patterns,
)
```

---

### `src/web/routes/upload.py` (modify — call analyze_overnight_patterns)

**Analog:** self (lines 1–188 of upload.py)

**Import addition pattern** (line 19 of upload.py):
```python
# Add alongside behavioral_patterns import:
from cgm_insights.analytics.overnight_patterns import analyze_overnight_patterns
```

**Analysis call pattern** (lines 133–136 of upload.py) — add after behavioral_result block:
```python
# Overnight pattern analysis (Phase 5)
overnight_result = analyze_overnight_patterns(readings)
overnight_patterns_dict = overnight_result.model_dump()
```

**Session store call pattern** (lines 147–154 of upload.py) — add `overnight_patterns` kwarg:
```python
session_store.store(
    session_id,
    results,
    patterns=all_patterns,
    raw_readings=raw_readings,
    behavioral_patterns=behavioral_patterns_dict,
    overnight_patterns=overnight_patterns_dict,   # ADD
)
```

---

### `src/web/routes/results.py` (modify — wire overnight_patterns into template)

**Analog:** self (lines 1–112 of results.py)

**Import addition pattern** (lines 12–13 of results.py):
```python
from cgm_insights.analytics.overnight_patterns import OvernightAnalysisResult
from cgm_insights.output.suggestions import generate_overnight_suggestions
```

**Session data extraction pattern** (lines 41–46 of results.py):
```python
# Add alongside behavioral_patterns_data extraction:
overnight_patterns_data = session_data.overnight_patterns  # dict or None
```

**Suggestions merge pattern** (lines 58–61 of results.py) — add after behavioral suggestions block:
```python
if overnight_patterns_data and not overnight_patterns_data.get("insufficient_data", True):
    overnight_result = OvernightAnalysisResult.model_validate(overnight_patterns_data)
    suggestions = suggestions + generate_overnight_suggestions(overnight_result)
    suggestions.sort(key=lambda s: s.priority)
```

**Template context pattern** (lines 98–112 of results.py) — add to TemplateResponse dict:
```python
"overnight_patterns": overnight_patterns_data,   # ADD alongside behavioral_patterns
```

---

### `src/web/services/session.py` (modify — add overnight_patterns field)

**Analog:** self (lines 1–164 of session.py)

**Dataclass field addition pattern** (lines 15–29 of session.py) — add after `behavioral_patterns`:
```python
@dataclass
class SessionData:
    results: AnalysisResults
    patterns: list[PatternResult] = field(default_factory=list)
    raw_readings: list[dict] = field(default_factory=list)
    behavioral_patterns: Optional[dict] = field(default=None)
    overnight_patterns: Optional[dict] = field(default=None)    # ADD
```

**`store()` signature pattern** (lines 43–64 of session.py) — add parameter and assignment:
```python
def store(
    self,
    session_id: str,
    results: AnalysisResults,
    patterns: Optional[list[PatternResult]] = None,
    raw_readings: Optional[list[dict]] = None,
    behavioral_patterns: Optional[dict] = None,
    overnight_patterns: Optional[dict] = None,    # ADD
) -> None:
    self._sessions[session_id] = SessionData(
        results=results,
        patterns=patterns or [],
        raw_readings=raw_readings or [],
        behavioral_patterns=behavioral_patterns,
        overnight_patterns=overnight_patterns,    # ADD
    )
```

---

### `src/web/templates/results.html` (modify — include overnight component)

**Analog:** self (lines 115–121 of results.html)

**Component include pattern** (lines 115–120 of results.html) — add immediately after behavioral_patterns block:
```jinja
{# Add after behavioral_patterns block (after line 120): #}

<!-- Overnight Patterns (Phase 5) -->
<div class="mb-6">
    {% with overnight_patterns=overnight_patterns %}
    {% include 'components/overnight_patterns.html' %}
    {% endwith %}
</div>
```

---

## Shared Patterns

### Wellness language (apply to ALL new output text)
**Source:** `src/cgm_insights/output/suggestions.py` lines 23–43
```python
WELLNESS_PREFIXES = ["Consider", "You might consider", "A pattern of", ...]
WELLNESS_CONNECTORS = ["This may indicate", "This pattern suggests", ...]
WELLNESS_DISCLAIMER = (
    "This is for informational purposes only and is not medical advice. "
    "Always discuss glucose patterns with your healthcare provider."
)
```
Apply to: overnight suggestion templates, HTML component disclaimer block.

### Pydantic frozen model config (apply to all new Pydantic models)
**Source:** `src/cgm_insights/analytics/behavioral_patterns.py` lines 61, 79
```python
model_config = ConfigDict(frozen=True)
```

### Insufficient data guard (apply to analyze_overnight_patterns public function)
**Source:** `src/cgm_insights/analytics/behavioral_patterns.py` lines 291–305
Pattern: check `not readings` first (return with `insufficient_data=True, total_X=0`), then check `total_X < min_X` after building DataFrame.

### Midnight-crossing filter (apply to overnight window filtering)
**Source:** `src/cgm_insights/analytics/behavioral_patterns.py` lines 143–152 (`_get_subset`)
```python
# Overnight window (22:00–06:00) always crosses midnight:
df.filter(
    (pl.col("mod") >= OVERNIGHT_START_MINUTE) | (pl.col("mod") < OVERNIGHT_END_MINUTE)
)
```

### model_dump() / model_validate() round-trip (apply to web layer)
**Source:** `src/web/routes/upload.py` lines 134–135; `src/web/routes/results.py` lines 58–60
```python
# Serialize at upload:
overnight_result.model_dump()
# Deserialize at results display:
OvernightAnalysisResult.model_validate(overnight_patterns_data)
```

### Exception handling in CLI (apply to _run_analysis overnight block)
**Source:** `src/cgm_insights/cli.py` lines 195–207
```python
try:
    ...
except Exception as e:
    console.print(f"\n[yellow]Could not generate overnight patterns: {e}[/yellow]")
```

---

## No Analog Found

All files have direct analogs. No entries.

---

## Metadata

**Analog search scope:** `src/cgm_insights/analytics/`, `src/web/templates/components/`, `tests/test_analytics/`, `src/cgm_insights/output/`, `src/cgm_insights/cli.py`, `src/web/routes/`, `src/web/services/`, `src/web/templates/`
**Files scanned:** 10
**Pattern extraction date:** 2026-06-11
