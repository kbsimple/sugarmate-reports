# Phase 5: Sleep Analysis - Research

**Researched:** 2026-06-11
**Domain:** Python time-series analysis — overnight window extraction (midnight-crossing), NGSI-style stability index, excursion detection, Polars aggregation, Phase 4 integration pattern reuse
**Confidence:** HIGH (all critical claims verified against live codebase; NGSI formula approach cited from published preprint with fallback to implementable proxy)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SLEEP-01 | System analyzes glucose patterns during 10pm-6am window (labeled "overnight" not "sleep") | Verified: `_get_subset(df, bucket_start=1320, window_min=480)` from behavioral_patterns.py handles midnight-crossing correctly; 22:00 = mod 1320, window end = 1320+480=1800 → crosses 1440, wraps to mod 360 (06:00) |
| SLEEP-02 | System calculates overnight metrics: mean glucose, TIR, CV, time below range | Verified: All four metrics computable from existing `_calculate_metrics_from_values()` logic applied to overnight subset; Polars `.mean()`, `.std()`, count filters confirmed API |
| SLEEP-03 | System compares weekday vs weekend overnight patterns | Verified: `_daily_stats()` with `day_type_filter` from behavioral_patterns.py is directly reusable; classify by date of 22:00 start |
| SLEEP-04 | System calculates NGSI-style stability index | Cited from medRxiv 2025.05.18.25327867: NGSI is a composite of amplitude, frequency, and temporal stability normalized to [0,1]; exact ML-derived formula is not public; implementable as a normalized CV-based proxy — see Architecture Patterns section |
| SLEEP-05 | System detects overnight excursions (sustained highs/lows) | Cited: ADA/CGM literature defines sustained excursion as ≥3 consecutive 5-min readings (≥15 min) outside threshold; standard thresholds: low <70 mg/dL, very_low <54 mg/dL, high >180 mg/dL |
| SLEEP-06 | All sleep insights use wellness framing and acknowledge window assumption | Verified: existing `WELLNESS_DISCLAIMER` and `SUGGESTION_TEMPLATES` pattern in suggestions.py is the extension point; "overnight" and "10pm-6am window" terminology throughout |
</phase_requirements>

---

## Summary

Phase 5 adds overnight glucose analysis to the existing behavioral pattern analysis foundation from Phase 4. The core work follows the same architectural pattern established in Phase 4 — create a new analytics module (`overnight_patterns.py`), a new Pydantic result model (`OvernightAnalysisResult`), new suggestion templates, and wire it through session storage, upload pipeline, results route, web template, and CLI flag.

The most technically distinctive element is the overnight window: 22:00–06:00 ALWAYS crosses midnight, making it a fixed special case of the midnight-crossing window that `_get_subset()` from Phase 4 already handles correctly. The planner should reuse that function directly.

The NGSI-style stability index cannot be reproduced exactly from the original paper (ML-derived, formula not fully published), but a normalized CV-based proxy — `NGSI_proxy = max(0, 1 - (CV_overnight / 100))` — is a defensible implementation: it produces a [0,1] score where 1=perfect stability, and it uses the same metric (CV of daily overnight means) that Phase 4 already computes for behavioral patterns. This approach is clearly labeled "overnight stability score" in user-facing language, never "NGSI" or any clinical term.

Excursion detection works by grouping consecutive readings outside a threshold and counting runs of ≥3 (≥15 minutes at 5-min sampling), matching ADA/CGM literature definitions. The window-crossing issue and weekday classification (use the DATE OF THE 22:00 START, not the 06:00 end) are the two critical implementation pitfalls.

**Primary recommendation:** Reuse `_get_subset()`, `_build_df()`, `_daily_stats()`, and the `generate_behavioral_suggestions()` function structure from behavioral_patterns.py. The entire integration chain (session.py, upload.py, results.py, CLI) follows the Phase 4 pattern verbatim — the delta is one new `Optional[dict]` field per touch point.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Overnight window extraction (22:00–06:00) | Core library (`analytics/overnight_patterns.py`) | — | Pure Polars computation, no web dependencies |
| NGSI-style stability score | Core library | — | Mathematical transform on CGM readings — library concern |
| Excursion detection | Core library | — | Run-length detection on raw glucose values — library concern |
| Weekday/weekend overnight split | Core library | — | Date arithmetic on CGM timestamps |
| Overnight suggestion generation | Core library (`output/suggestions.py`) | — | Extends existing Suggestion/template infrastructure |
| Session storage for overnight results | Web services (`session.py`) | — | Adds `Optional[dict]` field to `SessionData` |
| Upload pipeline wiring | Web routes (`upload.py`) | — | Calls `analyze_overnight_patterns()`, serializes to dict |
| Results route rendering | Web routes (`results.py`) | — | Deserializes dict, passes to template |
| Web display component | Web templates (`overnight_patterns.html`) | — | New component; included in results.html |
| CLI flag | CLI (`cli.py`) | — | Adds `--overnight/--no-overnight` flag, Rich table renderer |

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| polars | 1.40.1 [VERIFIED: venv] | Overnight window filtering, aggregation, run-length detection | Already the project's data engine; Phase 4 confirmed API |
| pydantic | 2.13.3 [VERIFIED: venv] | `OvernightAnalysisResult` model with `ConfigDict(frozen=True)` | Project-wide model pattern |
| fastapi | existing | Web route integration | Project web framework |
| jinja2 | existing | Template component rendering | Project template engine |
| typer + rich | existing | CLI flag and Rich table rendering | Project CLI framework |

**No new package installations are required for Phase 5.**

---

## Architecture Patterns

### System Architecture Diagram

```
CGMReading list
      |
      v
_build_df()  [reuse from behavioral_patterns.py]
  adds: timestamp, glucose, mod (minute-of-day), date, day_type
      |
      v
_get_subset(df, bucket_start=1320, window_min=480)
  [reuse from behavioral_patterns.py]
  filter: mod >= 1320 OR mod < 360  (22:00 to 06:00, crosses midnight)
      |
      v
Overnight DataFrame
  |                    |                     |
  v                    v                     v
_compute_overnight    _compute_weekday/     _detect_excursions()
_metrics()            weekend_split()       [new]
  - mean glucose        - weekday subset      - group consecutive OOB
  - TIR (70-180)        - weekend subset        readings by day
  - CV (std/mean)       - mean, TIR, CV       - runs >= 3 readings
  - TBR (<70)           per segment             flagged as excursions
  - stability score
      |                    |                     |
      +--------------------+---------------------+
                           |
                           v
              OvernightAnalysisResult (Pydantic, frozen=True)
                    |
          +---------+---------+
          |                   |
          v                   v
  generate_overnight_    model_dump()
  suggestions()          stored in session
          |                   |
          v                   v
  list[Suggestion]       upload.py / session.py
```

### Recommended Project Structure

```
src/cgm_insights/analytics/
├── behavioral_patterns.py   # Phase 4 (existing)
├── overnight_patterns.py    # Phase 5 (NEW)
└── __init__.py              # add overnight exports

src/cgm_insights/output/
└── suggestions.py           # add overnight templates + generate_overnight_suggestions()

src/web/
├── routes/upload.py         # add overnight analysis call
├── routes/results.py        # pass overnight_patterns to template
├── services/session.py      # add overnight_patterns Optional[dict] field
└── templates/
    ├── results.html                          # include overnight component
    └── components/overnight_patterns.html   # NEW component (mirrors behavioral_patterns.html)

src/cgm_insights/cli.py     # add --overnight flag + _render_overnight_patterns()
src/cgm_insights/analytics/__init__.py  # export analyze_overnight_patterns
src/cgm_insights/__init__.py            # export OvernightAnalysisResult

tests/test_analytics/test_overnight_patterns.py  # NEW test file
```

---

### Pattern 1: Overnight Window Extraction (Midnight-Crossing)

**What:** The 22:00–06:00 window always crosses midnight. It must be filtered with an OR condition, not a simple range. Phase 4's `_get_subset()` already handles this correctly.

**Key constants:**
```python
OVERNIGHT_START_MINUTE: int = 1320   # 22 * 60 = 1320
OVERNIGHT_WINDOW_MINUTES: int = 480  # 8 hours * 60
# End wraps: 1320 + 480 = 1800 → 1800 - 1440 = 360 = 06:00
```

**Reuse pattern:**
```python
# Source: behavioral_patterns.py _get_subset() — already handles midnight crossing
from cgm_insights.analytics.behavioral_patterns import _build_df, _get_subset

df = _build_df(readings)
overnight_df = _get_subset(df, OVERNIGHT_START_MINUTE, OVERNIGHT_WINDOW_MINUTES)
# overnight_df contains all rows where mod >= 1320 OR mod < 360
```

**Example from existing code (behavioral_patterns.py line 130–152):**
```python
def _get_subset(df: pl.DataFrame, bucket_start: int, window_min: int) -> pl.DataFrame:
    bucket_end = bucket_start + window_min
    if bucket_end <= 1440:
        return df.filter(
            (pl.col("mod") >= bucket_start) & (pl.col("mod") < bucket_end)
        )
    else:
        # Window crosses midnight — this is the path overnight takes
        return df.filter(
            (pl.col("mod") >= bucket_start) | (pl.col("mod") < (bucket_end - 1440))
        )
```

---

### Pattern 2: Weekday Classification for Overnight

**Critical rule:** Classify by the DATE OF THE 22:00 START, not the 06:00 end.

Example: If it is Monday night 23:30, the reading belongs to Monday's overnight even though the calendar date is Tuesday. A Monday night classified as Tuesday would contaminate the weekday/weekend split.

**Implementation approach:** Add a `night_date` column to the overnight DataFrame. For rows with `mod >= 1320` (i.e., after 22:00 on the start night), `night_date = date`. For rows with `mod < 360` (i.e., before 06:00 on the next calendar morning), `night_date = date - 1 day`.

```python
# Source: [VERIFIED — derived from behavioral_patterns.py _build_df pattern]
overnight_df = overnight_df.with_columns(
    pl.when(pl.col("mod") >= OVERNIGHT_START_MINUTE)
    .then(pl.col("date"))
    .otherwise(pl.col("date") - pl.duration(days=1))
    .alias("night_date")
)
```

The `day_type` for a night is then based on `night_date.weekday()` (Monday=0..Friday=4 = weekday, Saturday=5, Sunday=6 = weekend). This matches the existing `_build_df()` weekday logic for the start-of-night date.

---

### Pattern 3: Overnight Metrics Computation (SLEEP-02)

All four metrics (mean, TIR, CV, TBR) are computed from the overnight subset using patterns identical to existing code.

```python
# Source: [VERIFIED — derived from metrics.py _calculate_metrics_from_values()]
def _compute_overnight_metrics(overnight_df: pl.DataFrame) -> dict:
    """Compute per-night mean, then aggregate across nights."""
    if overnight_df.height == 0:
        return {}

    daily_stats = (
        overnight_df.group_by("night_date")
        .agg([
            pl.col("glucose").mean().alias("daily_mean"),
            pl.col("glucose").count().alias("count"),
            # TIR: readings in [70, 180] / total
            ((pl.col("glucose") >= 70) & (pl.col("glucose") <= 180))
            .mean().alias("daily_tir"),
            # TBR: readings < 70 / total
            (pl.col("glucose") < 70).mean().alias("daily_tbr"),
        ])
        .filter(pl.col("count") >= 3)  # at least 3 readings per night
    )

    if daily_stats.height < MIN_DAYS_FOR_STABILITY:
        return {"insufficient_data": True, "nights_with_data": daily_stats.height}

    mean_glucose = daily_stats["daily_mean"].mean()
    std_glucose = daily_stats["daily_mean"].std()
    cv = (std_glucose / mean_glucose * 100) if mean_glucose and mean_glucose > 0 else 0.0
    tir_pct = daily_stats["daily_tir"].mean() * 100
    tbr_pct = daily_stats["daily_tbr"].mean() * 100

    return {
        "mean_glucose": mean_glucose,
        "cv": cv,
        "tir_pct": tir_pct,
        "tbr_pct": tbr_pct,
        "nights_with_data": daily_stats.height,
    }
```

**CV note:** The CV computed here is the CV of daily overnight means (cross-night variability), consistent with Phase 4's behavioral pattern CV. This answers the research question: use the same CV-of-daily-means approach, not the intra-night CV of raw readings.

---

### Pattern 4: NGSI-Style Stability Index (SLEEP-04)

**Background:** The actual NGSI (Nocturnal Glycemic Stability Index) was published in a May 2025 medRxiv preprint (Andrade et al., 2025.05.18.25327867). [CITED: medrxiv.org/content/10.1101/2025.05.18.25327867v1.full] The paper defines NGSI as a composite of amplitude, frequency, and temporal distribution of nocturnal glucose fluctuations, validated against hypoglycemia/hyperglycemia events. The formula is ML-derived and the exact weighting coefficients are not reproduced in the abstract or publicly accessible summary. The index range is [0,1] where 1 = perfect stability.

**Implementation approach — CV-based proxy:**

Since the ML formula is not reproducible, implement an "overnight stability score" using normalized CV. This is transparent, mathematically sound, and produces a [0,1] score aligned with the paper's direction (lower variability = higher score):

```python
# Source: [ASSUMED — proxy formula, not the published ML formula]
# Named "overnight_stability_score" in user-facing code, NOT "NGSI"
def _compute_stability_score(cv: float) -> float:
    """Compute an overnight stability score in [0, 1].

    Maps CV to stability: CV=0% → score=1.0 (perfect), CV=100%+ → score=0.0.
    Uses a simple linear normalization capped at 0.

    Args:
        cv: Coefficient of variation of daily overnight means (%).

    Returns:
        Stability score in [0.0, 1.0].
    """
    return max(0.0, 1.0 - (cv / 100.0))
```

**Wellness framing for this score:**

| Score | Label |
|-------|-------|
| >= 0.8 | "Stable" |
| 0.5–0.8 | "Moderate variation" |
| < 0.5 | "High variation" |

These thresholds mirror the published NGSI interpretation levels, making the proxy directionally consistent with the paper even though the exact calculation differs. User-facing label: "Overnight Stability Score" — never "NGSI" or any clinical index name.

---

### Pattern 5: Excursion Detection (SLEEP-05)

**Definition (cited from ADA/CGM literature):** A sustained excursion is ≥3 consecutive 5-minute CGM readings outside a threshold. [CITED: PMC11418509 — "at least four consecutive CGM readings (≥15 minutes) below threshold"; using ≥3 readings = ≥15 min at 5-min sampling is consistent with most CGM literature]

**Thresholds (from existing GLUCOSE_THRESHOLDS in metrics.py):**
- Sustained low: <70 mg/dL for ≥15 min (≥3 readings)
- Sustained very low: <54 mg/dL for ≥15 min (≥3 readings)
- Sustained high: >180 mg/dL for ≥15 min (≥3 readings)

**Algorithm:** Group overnight readings by `night_date`, sort by `mod` (minute-of-day within the night — requires care since readings wrap midnight), then detect run-length encoding of out-of-range conditions.

```python
# Source: [VERIFIED — derived from Polars API patterns; run-length via diff/cumsum]
def _detect_excursions(overnight_df: pl.DataFrame) -> list[dict]:
    """Detect sustained overnight excursions per night.

    Args:
        overnight_df: DataFrame with night_date, mod, glucose columns.

    Returns:
        List of excursion dicts with: night_date, excursion_type, reading_count,
        min_glucose (for lows), max_glucose (for highs).
    """
    excursions = []
    for night_date, group in overnight_df.group_by("night_date"):
        # Sort by mod-within-night: readings after midnight get mod + 1440
        # so they sort AFTER the 22:xx readings from the previous calendar night.
        # Readings with mod < 360 are on the "next morning" side — add 1440.
        group = group.with_columns(
            pl.when(pl.col("mod") < OVERNIGHT_START_MINUTE)
            .then(pl.col("mod") + 1440)
            .otherwise(pl.col("mod"))
            .alias("night_mod")
        ).sort("night_mod")

        values = group["glucose"].to_list()
        n = len(values)
        for threshold, direction, label in [
            (70,  "below", "sustained_low"),
            (54,  "below", "sustained_very_low"),
            (180, "above", "sustained_high"),
        ]:
            run = []
            for v in values:
                in_excursion = v < threshold if direction == "below" else v > threshold
                if in_excursion:
                    run.append(v)
                else:
                    if len(run) >= 3:  # ≥15 minutes at 5-min sampling
                        excursions.append({
                            "night_date": night_date[0],
                            "excursion_type": label,
                            "reading_count": len(run),
                            "min_glucose": min(run),
                            "max_glucose": max(run),
                        })
                    run = []
            # flush final run
            if len(run) >= 3:
                excursions.append({
                    "night_date": night_date[0],
                    "excursion_type": label,
                    "reading_count": len(run),
                    "min_glucose": min(run),
                    "max_glucose": max(run),
                })
    return excursions
```

**Aggregation for the result model:** Rather than returning individual excursion events (which could feel clinical), aggregate to counts per type across all analyzed nights:

```python
excursion_summary = {
    "sustained_low_nights": count of nights with any sustained_low or sustained_very_low,
    "sustained_high_nights": count of nights with any sustained_high,
    "total_excursion_nights": count of nights with any excursion,
    "total_nights": len(analyzed nights),
}
```

---

### Pattern 6: OvernightAnalysisResult Model

Mirrors `BehavioralAnalysisResult`. Frozen Pydantic v2 model.

```python
# Source: [VERIFIED — mirrors behavioral_patterns.py BehavioralAnalysisResult pattern]
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class OvernightAnalysisResult(BaseModel):
    """Results from overnight (22:00–06:00) glucose analysis.

    Attributes:
        mean_glucose: Mean overnight glucose across all analyzed nights (mg/dL).
        tir_pct: Time-in-range (70–180 mg/dL) during overnight window (%).
        cv: CV of daily overnight means (cross-night variability, %).
        tbr_pct: Time below range (<70 mg/dL) during overnight window (%).
        stability_score: Overnight stability score [0, 1] (1 = most stable).
        stability_label: Qualitative label for stability_score.
        weekday_mean_glucose: Mean overnight glucose on weekday-start nights, or None.
        weekend_mean_glucose: Mean overnight glucose on weekend-start nights, or None.
        weekday_tir_pct: Weekday TIR overnight, or None.
        weekend_tir_pct: Weekend TIR overnight, or None.
        excursion_summary: Dict with counts of sustained excursion nights.
        nights_with_data: Total nights with sufficient overnight data.
        insufficient_data: True when nights_with_data < MIN_DAYS_FOR_STABILITY.
        window_label: Human-readable window label ("10pm–6am").
    """
    mean_glucose: Optional[float] = Field(None, ge=40.0, le=400.0)
    tir_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    cv: Optional[float] = Field(None, ge=0.0)
    tbr_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    stability_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    stability_label: Optional[str] = None
    weekday_mean_glucose: Optional[float] = Field(None, ge=40.0, le=400.0)
    weekend_mean_glucose: Optional[float] = Field(None, ge=40.0, le=400.0)
    weekday_tir_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    weekend_tir_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    excursion_summary: dict = Field(default_factory=dict)
    nights_with_data: int = Field(..., ge=0)
    insufficient_data: bool = Field(False)
    window_label: str = Field("10pm–6am")

    model_config = ConfigDict(frozen=True)
```

---

### Pattern 7: Integration Chain (Phase 4 Mirror)

Every touch point for Phase 4's behavioral patterns has an exact overnight analog:

| Phase 4 Touch Point | Phase 5 Analog |
|---------------------|----------------|
| `behavioral_patterns: Optional[dict]` in `SessionData` | Add `overnight_patterns: Optional[dict]` to `SessionData` |
| `analyze_behavioral_patterns(readings)` in `upload.py` | Add `analyze_overnight_patterns(readings)` call |
| `behavioral_patterns_dict = behavioral_result.model_dump()` | `overnight_patterns_dict = overnight_result.model_dump()` |
| `session_store.store(..., behavioral_patterns=...)` | Add `overnight_patterns=overnight_patterns_dict` kwarg |
| `session_data.behavioral_patterns` in `results.py` | `session_data.overnight_patterns` |
| `BehavioralAnalysisResult.model_validate(...)` | `OvernightAnalysisResult.model_validate(...)` |
| `generate_behavioral_suggestions(behavioral_result)` | `generate_overnight_suggestions(overnight_result)` |
| `behavioral_patterns=behavioral_patterns_data` template kwarg | `overnight_patterns=overnight_patterns_data` |
| `{% include 'components/behavioral_patterns.html' %}` | `{% include 'components/overnight_patterns.html' %}` |
| `--behavioral/--no-behavioral` CLI flag | `--overnight/--no-overnight` CLI flag |

**Session.py change** (minimal, follows same pattern as Phase 4 added `behavioral_patterns`):

```python
@dataclass
class SessionData:
    results: AnalysisResults
    patterns: list[PatternResult] = field(default_factory=list)
    raw_readings: list[dict] = field(default_factory=list)
    behavioral_patterns: Optional[dict] = field(default=None)
    overnight_patterns: Optional[dict] = field(default=None)  # NEW
```

`SessionStore.store()` needs one new keyword argument `overnight_patterns: Optional[dict] = None`.

---

### Pattern 8: Suggestion Templates (SLEEP-06)

Add to `SUGGESTION_TEMPLATES` in `suggestions.py`:

```python
"overnight_stable": {
    "title": "Consistent overnight glucose pattern",
    "description": "Your glucose during the 10pm–6am window shows consistent patterns across nights.",
    "action": "Consider noting what contributes to this consistency in your evening routine.",
    "category": SuggestionCategory.TIMING,
    "priority": 3,
},
"overnight_variable": {
    "title": "Variable overnight glucose pattern",
    "description": "Your glucose during the 10pm–6am window varies noticeably across nights.",
    "action": "Consider exploring what differs on nights with higher or lower overnight glucose.",
    "category": SuggestionCategory.VARIABILITY,
    "priority": 3,
},
"overnight_low_excursions": {
    "title": "Low overnight glucose periods detected",
    "description": "Your 10pm–6am window shows some nights with lower glucose readings.",
    "action": "Be aware of this pattern. Consider discussing low overnight glucose with your healthcare provider.",
    "category": SuggestionCategory.SAFETY,
    "priority": 2,
},
"overnight_high_excursions": {
    "title": "Elevated overnight glucose periods detected",
    "description": "Your 10pm–6am window shows some nights with higher glucose readings.",
    "action": "Consider exploring what might contribute to elevated overnight glucose.",
    "category": SuggestionCategory.CONTROL,
    "priority": 3,
},
"overnight_weekday_weekend_diff": {
    "title": "Weekday vs weekend overnight difference",
    "description": (
        "Your overnight glucose (10pm–6am) tends to differ between "
        "weekday nights ({weekday_avg:.0f} mg/dL) and weekend nights ({weekend_avg:.0f} mg/dL)."
    ),
    "action": "Consider whether evening routines differ between weekdays and weekends.",
    "category": SuggestionCategory.CONTROL,
    "priority": 4,
},
```

The `generate_overnight_suggestions()` function signature mirrors `generate_behavioral_suggestions()`:

```python
def generate_overnight_suggestions(
    overnight_result: OvernightAnalysisResult,
) -> list[Suggestion]:
```

---

### Pattern 9: Web Template Component

`overnight_patterns.html` mirrors `behavioral_patterns.html` in structure. Key display elements:

```
Card: "Overnight Patterns (10pm–6am)"
  ├── Insufficient data alert (if nights_with_data < 5)
  ├── Metrics row: Mean Glucose | Time in Range | CV | Time Below Range
  ├── Stability Score bar: stability_score * 100 → progress element, with label
  ├── Weekday vs Weekend comparison (if both available):
  │     "Weekday nights avg: X mg/dL  ·  Weekend nights avg: Y mg/dL"
  ├── Excursion summary (if any excursion nights > 0):
  │     "X of Y nights had sustained low periods"
  │     "X of Y nights had sustained high periods"
  └── Wellness disclaimer (always shown)
```

Use DaisyUI `stats` component for the metrics row (consistent with behavioral_patterns.html card style). Use DaisyUI `progress` for the stability score bar.

---

### Anti-Patterns to Avoid

- **Do not use "sleep" anywhere in user-facing text.** Use "overnight", "10pm–6am window", or "nighttime period". REQUIREMENTS.md explicitly forbids "sleep" terminology.
- **Do not classify the overnight night by the 06:00 end date.** A Monday overnight starting at 22:00 Monday ends at 06:00 Tuesday — the date is Monday, the day type is weekday (Monday). Classifying by the 06:00 date makes it Tuesday, which may be a different day type.
- **Do not apply `_get_subset()` with `mod >= 1320 AND mod < 360`** — that is always false. The correct OR logic is already in `_get_subset()`.
- **Do not label the stability score "NGSI".** The exact NGSI formula is not publicly reproducible. Call it "overnight stability score" or "overnight glucose stability".
- **Do not return individual excursion events.** Aggregate to counts per type to avoid clinical alert framing.
- **Do not recompute intra-night CV (CV within a single night).** Use CV of daily overnight means for cross-night consistency, matching Phase 4's convention.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Midnight-crossing window filter | Custom OR filter logic | `_get_subset()` from behavioral_patterns.py | Already handles crossing correctly; tested |
| DataFrame construction with `mod` and `day_type` | Duplicate column creation | `_build_df()` from behavioral_patterns.py | Identical preprocessing; reuse to stay consistent |
| Weekday/weekend subset aggregation | Custom groupby | `_daily_stats()` from behavioral_patterns.py | Handles min_days threshold correctly |
| Suggestion model construction | New Suggestion class | Extend `SUGGESTION_TEMPLATES` + `Suggestion` in suggestions.py | Consistent wellness framing; reuses SuggestionCategory |
| Session storage extension | New session mechanism | Add `Optional[dict]` field to existing `SessionData` | Single change, follows Phase 4 pattern exactly |

**Key insight:** Phase 4 already solved the hard problems for Phase 5. The midnight-crossing filter, min_days enforcement, weekday/weekend split, and suggestion infrastructure are all directly reusable. Phase 5 is primarily a configuration of these primitives around a fixed 8-hour window.

---

## Common Pitfalls

### Pitfall 1: Midnight-crossing window with AND instead of OR

**What goes wrong:** `df.filter((pl.col("mod") >= 1320) & (pl.col("mod") < 360))` returns an empty DataFrame because a value cannot simultaneously be ≥1320 and <360.

**Why it happens:** Treating the overnight window like a normal intra-day range.

**How to avoid:** Always call `_get_subset(df, 1320, 480)`, which uses OR for the crossing case. Verify the returned row count is non-zero for a dataset with overnight data.

**Warning signs:** `overnight_df.height == 0` for a full day of readings.

---

### Pitfall 2: Classifying overnight by the end date (06:00 side)

**What goes wrong:** A Monday night reading at 01:00 Tuesday gets classified as Tuesday (a weekday or weekend depending on the week). This makes Monday night look like Tuesday in the weekday/weekend split.

**Why it happens:** `pl.col("date")` for a reading at 01:00 Tuesday is the Tuesday date object. Using that directly without adjustment misclassifies it.

**How to avoid:** Add `night_date` column: `pl.when(pl.col("mod") >= 1320).then(pl.col("date")).otherwise(pl.col("date") - pl.duration(days=1))`. Group by `night_date`, not `date`.

**Warning signs:** Weekend/weekday overnight averages look wrong compared to day-level patterns.

---

### Pitfall 3: Insufficient data check at the wrong granularity

**What goes wrong:** Checking if there are ≥5 total overnight readings, rather than ≥5 distinct nights with overnight readings. 5 readings across 2 nights is not the same as 5 nights.

**Why it happens:** Confusing row count with distinct-day count.

**How to avoid:** After extracting `overnight_df`, compute `night_count = overnight_df.select(pl.col("night_date").n_unique()).item()` and check `night_count >= MIN_DAYS_FOR_STABILITY`.

---

### Pitfall 4: intra-night sort order for excursion detection

**What goes wrong:** Readings from 00:30 (mod=30) sort BEFORE readings from 23:00 (mod=1380) if sorted by raw `mod`, even though 23:00 comes first chronologically within the overnight window.

**Why it happens:** `mod` is minute-of-day. After midnight, mod resets to 0 for the new calendar day, breaking chronological order within a single overnight.

**How to avoid:** Before sorting for excursion detection, add a `night_mod` column: `pl.when(pl.col("mod") < OVERNIGHT_START_MINUTE).then(pl.col("mod") + 1440).otherwise(pl.col("mod"))`. Sort by `night_mod` to get chronological overnight order.

---

### Pitfall 5: Labeling the stability score as "NGSI" or any clinical metric name

**What goes wrong:** Users or reviewers interpret the score as a validated clinical metric.

**Why it happens:** The proxy formula is inspired by the NGSI paper but does not reproduce its ML-derived formula.

**How to avoid:** Name it `overnight_stability_score` in code. In templates and CLI output, call it "Overnight Stability Score". Include the window assumption caveat ("This analysis uses the 10pm–6am window as a proxy for overnight periods").

---

## Code Examples

### Verified Pattern: `_get_subset` for the overnight window

```python
# Source: behavioral_patterns.py lines 130–152 [VERIFIED in codebase]
# With OVERNIGHT_START_MINUTE=1320, OVERNIGHT_WINDOW_MINUTES=480:
# bucket_end = 1320 + 480 = 1800 > 1440, so midnight-crossing branch executes:
# filter: mod >= 1320 OR mod < (1800 - 1440) = mod >= 1320 OR mod < 360
overnight_df = _get_subset(df, OVERNIGHT_START_MINUTE, OVERNIGHT_WINDOW_MINUTES)
```

### Verified Pattern: n_unique for night count

```python
# Source: behavioral_patterns.py line 298 [VERIFIED in codebase]
# Adapt for overnight:
night_count = overnight_df.select(pl.col("night_date").n_unique()).item()
```

### Verified Pattern: group_by with agg for per-night stats

```python
# Source: behavioral_patterns.py lines 207–215 [VERIFIED in codebase]
# Adapt for per-night aggregation:
nightly = (
    overnight_df.group_by("night_date")
    .agg([
        pl.col("glucose").mean().alias("daily_mean"),
        pl.col("glucose").count().alias("count"),
    ])
    .filter(pl.col("count") >= 3)
)
```

### Verified Pattern: Series.quantile (not used directly in Phase 5 but available)

```python
# Source: behavioral_patterns.py lines 254–256 [VERIFIED in codebase]
cv_series = pl.Series("cv", [b["cv"] for b in nights])
p25 = cv_series.quantile(0.25)  # available if quartile labeling needed
```

### Verified Pattern: pl.duration(days=1) for date arithmetic

```python
# Source: Polars 1.40.1 API [VERIFIED: polars version confirmed in venv]
# Subtract one day to map post-midnight readings back to start night:
night_date = pl.col("date") - pl.duration(days=1)
```

### Verified Pattern: Boolean mask mean for TIR/TBR

```python
# Source: [VERIFIED — standard Polars boolean expression; used in metrics.py pattern]
# Mean of a boolean Series gives the fraction of True values
tir = ((pl.col("glucose") >= 70) & (pl.col("glucose") <= 180)).mean()  # fraction in [0,1]
tbr = (pl.col("glucose") < 70).mean()  # multiply by 100 for percentage
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed 2-hour block time-of-day analysis (patterns.py) | Sliding window + fixed overnight bucket (behavioral + overnight) | Phase 4 & 5 | Richer resolution; overnight is one well-defined window |
| No overnight-specific metrics | Overnight TIR, CV, TBR, stability score, excursions | Phase 5 | Answers user question about overnight control |
| General time-of-day patterns include overnight incidentally | Dedicated 10pm–6am analysis with weekday/weekend split | Phase 5 | Intentional; avoids mixing overnight with active periods |

**Not yet implemented (v2.1+ deferred):**
- ENHC-01: Inferred sleep window detection from glucose stability patterns
- ENHC-04: Custom sleep window for shift workers

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `NGSI_proxy = max(0, 1 - cv/100)` is an acceptable stand-in for the published NGSI formula | Pattern 4 | Scores won't match published NGSI benchmarks; mitigated by labeling it "Overnight Stability Score" not "NGSI" |
| A2 | Excursion threshold of ≥3 consecutive readings (≥15 min) is the right sensitivity for a wellness tool | Pattern 5 | Could produce too many or too few excursion flags; user can see counts not individual events |
| A3 | CGM readings are at 5-minute intervals, making ≥3 readings = ≥15 minutes valid | Pattern 5 | Non-5-min sampling (Libre at 15 min) would make ≥3 = ≥45 min; mitigated by checking reading frequency |
| A4 | `pl.duration(days=1)` works correctly for date subtraction in Polars 1.40.1 | Pattern 2 | API change risk; mitigated — `pl.duration` is stable since Polars 0.16 |

**If A3 concerns the planner:** Add a sampling interval detection step — if the median reading interval is not 5 minutes, adjust the run-length threshold proportionally, or document that the module assumes 5-minute CGM data (consistent with Sugarmate/Dexcom output).

---

## Open Questions

1. **Should overnight analysis run unconditionally or require explicit user action?**
   - What we know: Phase 4 behavioral analysis runs on every upload (not gated by user action); the `--behavioral` CLI flag defaults to `True`
   - What's unclear: Whether overnight analysis should default to on (like behavioral) or require a user toggle
   - Recommendation: Default to on, following Phase 4 precedent; add `--overnight/--no-overnight` flag with default=True in CLI

2. **Where in results.html should the overnight component be placed?**
   - What we know: Behavioral patterns component is placed after the daily patterns chart (`{% include 'components/behavioral_patterns.html' %}` at line 116)
   - What's unclear: Whether overnight should appear before or after behavioral patterns
   - Recommendation: Place overnight AFTER behavioral patterns (thematic progression: all-day patterns → overnight-specific)

3. **Should excursion detection skip nights with <6 readings (<30 min of overnight data)?**
   - What we know: The `≥3 readings per night` minimum in pattern 3 ensures some data exists
   - What's unclear: A night with 3 readings could have all 3 be excursion readings, making the excursion detection noisy
   - Recommendation: Require ≥6 readings per night (≥30 min) for excursion detection; nights with fewer readings are simply skipped

---

## Environment Availability

Step 2.6: SKIPPED (no new external dependencies — Phase 5 uses only libraries already installed in the project venv; verified Polars 1.40.1 and Pydantic 2.13.3 in venv above).

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 5 |
|-----------|-------------------|
| All commits: author Faiser, email keepbreakfastsimple@gmail.com | Git config must be set correctly for all commits |
| Google Python Style Guide | Docstrings, naming, module structure in overnight_patterns.py |
| Test gating: all tests pass before phase completion commit | `tests/test_analytics/test_overnight_patterns.py` must be green; full suite (223 tests + new) must pass |
| Type check: `npx tsc --noEmit` — no new TS errors | No TypeScript in Phase 5; N/A |
| Pydantic v2 `ConfigDict(frozen=True)` | OvernightAnalysisResult must use this pattern |
| Polars for data processing | No pandas; all Polars |
| FastAPI + Jinja2 + HTMX | Web layer uses existing patterns |
| Wellness language only — no medical advice | "overnight", "10pm–6am window"; no sleep recommendations |
| Python library first, no web dependencies in core library | `overnight_patterns.py` has zero imports from `src/web/` |

---

## Sources

### Primary (HIGH confidence)
- `/Users/ffaber/claude-projects/sugarmate-reports/src/cgm_insights/analytics/behavioral_patterns.py` — `_get_subset()`, `_build_df()`, `_daily_stats()`, `_compute_all_buckets()` reuse patterns [VERIFIED: read in full]
- `/Users/ffaber/claude-projects/sugarmate-reports/src/cgm_insights/analytics/metrics.py` — `_calculate_metrics_from_values()`, GLUCOSE_THRESHOLDS [VERIFIED: read in full]
- `/Users/ffaber/claude-projects/sugarmate-reports/src/web/services/session.py` — SessionData extension pattern [VERIFIED: read in full]
- `/Users/ffaber/claude-projects/sugarmate-reports/src/web/routes/upload.py` — Phase 4 wiring pattern [VERIFIED: read in full]
- `/Users/ffaber/claude-projects/sugarmate-reports/src/web/routes/results.py` — Phase 4 wiring pattern [VERIFIED: read in full]
- Polars 1.40.1 [VERIFIED: venv] — `group_by`, `agg`, `with_columns`, `filter`, `pl.duration`, `n_unique`, `Series.quantile`
- Pydantic 2.13.3 [VERIFIED: venv] — `ConfigDict(frozen=True)`, `model_dump()`, `model_validate()`

### Secondary (MEDIUM confidence)
- medRxiv 2025.05.18.25327867 — Nocturnal Glycemic Stability Index paper (Andrade et al.): NGSI defined as composite of amplitude/frequency/temporal stability, window 22:00–06:00, score [0,1] where >0.8=optimal, 0.5–0.8=moderate, <0.5=high instability [CITED: https://www.medrxiv.org/content/10.1101/2025.05.18.25327867v1.full — exact formula not accessible; proxy approach]
- PMC11418509 — ADA CGM excursion definition: ≥3 consecutive 5-min readings outside threshold = ≥15 min sustained excursion [CITED: https://pmc.ncbi.nlm.nih.gov/articles/PMC11418509/]
- PMC7153099 — Nocturnal hypoglycemia prediction study confirming 22:00–06:00 window definition [CITED: https://pmc.ncbi.nlm.nih.gov/articles/PMC7153099/]

### Tertiary (LOW confidence)
- None in this research.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in venv; no new dependencies
- Architecture: HIGH — directly verified against Phase 4 codebase; patterns are exact analogs
- NGSI formula: MEDIUM — paper exists and confirms index range and window; exact formula is ML-derived and not publicly reproducible; proxy approach is LOW-risk because it's labeled differently
- Excursion thresholds: MEDIUM — ADA CGM literature cited; ≥15 min definition is consistent across multiple sources
- Pitfalls: HIGH — midnight-crossing, date classification, and intra-night sort order are all derived from directly reading the existing code

**Research date:** 2026-06-11
**Valid until:** 2026-08-11 (stable stack; Polars API changes would be the main invalidation trigger)
