"""Overnight glucose pattern analysis for CGM data.

Analyzes glucose behavior during the 10pm–6am window across multiple nights.
All insights use wellness language — no medical advice. The window is a proxy
for overnight periods; actual sleep timing is not inferred.
"""

from __future__ import annotations

from typing import Optional

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from cgm_insights.analytics.behavioral_patterns import _build_df, _get_subset
from cgm_insights.models import CGMReading


OVERNIGHT_START_MINUTE: int = 1320   # 22:00 = 22 * 60
OVERNIGHT_WINDOW_MINUTES: int = 480  # 8 hours = 6:00 end
MIN_NIGHTS_FOR_ANALYSIS: int = 5
MIN_NIGHTS_FOR_SPLIT: int = 3         # minimum nights for weekday/weekend sub-analysis
MIN_READINGS_PER_NIGHT_FOR_EXCURSION: int = 6
EXCURSION_MIN_RUN: int = 3           # >=3 consecutive readings = >=15 min at 5-min sampling


class OvernightAnalysisResult(BaseModel):
    """Results from overnight (10pm–6am) glucose pattern analysis.

    Attributes:
        mean_glucose: Mean overnight glucose across all analyzed nights (mg/dL).
        tir_pct: Time-in-range (70–180 mg/dL) during overnight window (%).
        cv: CV of daily overnight means (cross-night variability, %).
        tbr_pct: Time below range (<70 mg/dL) during overnight window (%).
        stability_score: Overnight stability score [0, 1] (1 = most stable).
            Computed as max(0, 1 - cv/100). Named "Overnight Stability Score"
            in user-facing output. NEVER labeled "NGSI" — that is an ML-derived
            clinical index whose formula is not publicly reproducible.
        stability_label: Qualitative label for stability_score:
            ">= 0.8" = "Stable", "0.5-0.8" = "Moderate variation",
            "< 0.5" = "High variation".
        weekday_mean_glucose: Mean overnight glucose on weekday-start nights, or None.
        weekend_mean_glucose: Mean overnight glucose on weekend-start nights, or None.
        weekday_tir_pct: Weekday overnight TIR (%), or None.
        weekend_tir_pct: Weekend overnight TIR (%), or None.
        excursion_summary: Dict with keys: sustained_low_nights (int),
            sustained_high_nights (int), total_excursion_nights (int),
            total_nights (int).
        nights_with_data: Nights meeting the minimum readings threshold.
        insufficient_data: True when nights_with_data < MIN_NIGHTS_FOR_ANALYSIS.
        window_label: Always "10pm–6am".
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


def _get_overnight_df(readings: list[CGMReading]) -> pl.DataFrame:
    """Build overnight-window DataFrame from CGM readings.

    Calls _build_df() to add mod/date/day_type columns, then filters to the
    22:00–06:00 window using _get_subset() (handles midnight crossing via OR).
    Adds a `night_date` column: for readings after 22:00 (mod >= 1320),
    night_date = date; for readings before 06:00 (mod < 360), night_date =
    date - 1 day. This classifies each reading by the EVENING it belongs to,
    not the calendar morning.

    Args:
        readings: List of CGMReading objects.

    Returns:
        DataFrame with columns: timestamp, glucose, mod, date, day_type,
        night_date. Filtered to 22:00–06:00 window.
    """
    df = _build_df(readings)
    overnight_df = _get_subset(df, OVERNIGHT_START_MINUTE, OVERNIGHT_WINDOW_MINUTES)
    # Add night_date: readings after 22:00 keep their calendar date (the START night).
    # Readings before 06:00 are on the NEXT calendar day — subtract 1 to get the
    # evening date. Critical: never use the 06:00-side date for weekday classification.
    overnight_df = overnight_df.with_columns(
        pl.when(pl.col("mod") >= OVERNIGHT_START_MINUTE)
        .then(pl.col("date"))
        .otherwise(pl.col("date") - pl.duration(days=1))
        .alias("night_date")
    )
    return overnight_df


def _compute_metrics(overnight_df: pl.DataFrame) -> dict:
    """Compute overnight glucose metrics across all analyzed nights.

    Args:
        overnight_df: DataFrame from _get_overnight_df() with night_date column.

    Returns:
        Dict with keys: mean_glucose, tir_pct, cv, tbr_pct, stability_score,
        stability_label, weekday_mean_glucose, weekend_mean_glucose,
        weekday_tir_pct, weekend_tir_pct, nights_with_data.
        Returns {"nights_with_data": 0} if overnight_df is empty.
    """
    if overnight_df.height == 0:
        return {"nights_with_data": 0}

    # Per-night aggregation — only keep nights with >= 3 readings
    per_night = (
        overnight_df.group_by("night_date")
        .agg(
            pl.col("glucose").mean().alias("daily_mean"),
            pl.col("glucose").count().alias("count"),
            pl.col("glucose")
            .filter(pl.col("glucose").is_between(70, 180))
            .count()
            .alias("tir_count"),
            pl.col("glucose")
            .filter(pl.col("glucose") < 70)
            .count()
            .alias("tbr_count"),
            pl.col("day_type").first().alias("day_type"),
        )
        .filter(pl.col("count") >= 3)
    )

    # Re-derive day_type from night_date to avoid non-deterministic .first() on mixed
    # boundary nights (e.g. Fri 22:00 readings are "weekday"; Sat 01:00 are "weekend").
    per_night = per_night.with_columns(
        pl.when(pl.col("night_date").dt.weekday() >= 6)
        .then(pl.lit("weekend"))
        .otherwise(pl.lit("weekday"))
        .alias("day_type")
    )

    if per_night.height == 0:
        return {"nights_with_data": 0}

    nights_with_data = per_night.height
    mean_glucose = per_night["daily_mean"].mean()

    # Compute per-night TIR/TBR fractions, then average across nights — consistent
    # with how mean_glucose weights every night equally regardless of reading count.
    per_night = per_night.with_columns(
        (pl.col("tir_count") / pl.col("count") * 100).alias("tir_pct_night"),
        (pl.col("tbr_count") / pl.col("count") * 100).alias("tbr_pct_night"),
    )
    tir_pct = per_night["tir_pct_night"].mean() or 0.0
    tbr_pct = per_night["tbr_pct_night"].mean() or 0.0

    # CV of daily overnight means (cross-night variability, NOT intra-night CV)
    std_g = per_night["daily_mean"].std()
    if std_g is None or mean_glucose is None or mean_glucose <= 0:
        cv = 0.0
    else:
        cv = std_g / mean_glucose * 100

    stability_score = max(0.0, 1.0 - (cv / 100.0))
    if stability_score >= 0.8:
        stability_label = "Stable"
    elif stability_score >= 0.5:
        stability_label = "Moderate variation"
    else:
        stability_label = "High variation"

    # Weekday / weekend split — filter per_night rows by day_type
    weekday_nights = per_night.filter(pl.col("day_type") == "weekday")
    weekend_nights = per_night.filter(pl.col("day_type") == "weekend")

    def _split_stats(
        nights: pl.DataFrame,
    ) -> tuple[Optional[float], Optional[float]]:
        """Return (mean_glucose, tir_pct) for a day-type subset or (None, None)."""
        if nights.height < MIN_NIGHTS_FOR_SPLIT:
            return None, None
        mean_g = nights["daily_mean"].mean()
        # Use per-night TIR fractions averaged across nights — same equal-night
        # weighting as mean_g above (consistent with _compute_metrics top-level).
        nights = nights.with_columns(
            (pl.col("tir_count") / pl.col("count") * 100).alias("tir_pct_night")
        )
        tir_p = nights["tir_pct_night"].mean() or 0.0
        return mean_g, tir_p

    weekday_mean, weekday_tir = _split_stats(weekday_nights)
    weekend_mean, weekend_tir = _split_stats(weekend_nights)

    return {
        "mean_glucose": mean_glucose,
        "tir_pct": tir_pct,
        "cv": cv,
        "tbr_pct": tbr_pct,
        "stability_score": stability_score,
        "stability_label": stability_label,
        "weekday_mean_glucose": weekday_mean,
        "weekend_mean_glucose": weekend_mean,
        "weekday_tir_pct": weekday_tir,
        "weekend_tir_pct": weekend_tir,
        "nights_with_data": nights_with_data,
    }


def _has_sustained_run(values: list[float], threshold: float, above: bool) -> bool:
    """Return True if values contain a run of >= EXCURSION_MIN_RUN consecutive readings.

    Args:
        values: Ordered glucose readings for one night.
        threshold: Glucose level boundary.
        above: If True, check for values > threshold; if False, check for values < threshold.

    Returns:
        True if a qualifying run exists, False otherwise.
    """
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
    """Detect sustained overnight excursions and return aggregated counts.

    Args:
        overnight_df: DataFrame from _get_overnight_df() with night_date, mod, glucose.

    Returns:
        Dict with keys: sustained_low_nights, sustained_high_nights,
        total_excursion_nights, total_nights.
    """
    if overnight_df.height == 0:
        return {
            "sustained_low_nights": 0,
            "sustained_high_nights": 0,
            "total_excursion_nights": 0,
            "total_nights": 0,
        }

    sustained_low_nights = 0
    sustained_high_nights = 0
    total_excursion_nights = 0

    # Add night_mod for chronological sort across midnight boundary
    df_with_night_mod = overnight_df.with_columns(
        pl.when(pl.col("mod") < OVERNIGHT_START_MINUTE)
        .then(pl.col("mod") + 1440)
        .otherwise(pl.col("mod"))
        .alias("night_mod")
    )

    night_dates = overnight_df.select("night_date").unique().to_series().to_list()
    total_nights = 0

    for night in night_dates:
        night_rows = df_with_night_mod.filter(pl.col("night_date") == night)
        if night_rows.height < MIN_READINGS_PER_NIGHT_FOR_EXCURSION:
            continue

        total_nights += 1
        sorted_rows = night_rows.sort("night_mod")
        glucose_values = sorted_rows["glucose"].to_list()

        has_low = _has_sustained_run(glucose_values, 70, above=False)
        has_very_low = _has_sustained_run(glucose_values, 54, above=False)
        has_high = _has_sustained_run(glucose_values, 180, above=True)

        night_has_low = has_low or has_very_low
        if night_has_low:
            sustained_low_nights += 1
        if has_high:
            sustained_high_nights += 1
        if night_has_low or has_high:
            total_excursion_nights += 1

    return {
        "sustained_low_nights": sustained_low_nights,
        "sustained_high_nights": sustained_high_nights,
        "total_excursion_nights": total_excursion_nights,
        "total_nights": total_nights,
    }


def analyze_overnight_patterns(
    readings: list[CGMReading],
    min_nights: int = MIN_NIGHTS_FOR_ANALYSIS,
) -> OvernightAnalysisResult:
    """Analyze glucose patterns during the 10pm–6am window.

    Uses a fixed overnight window (22:00–06:00, always midnight-crossing).
    Classifies each reading by the EVENING start date (not calendar morning).
    Returns insufficient_data=True when fewer than min_nights distinct nights
    have sufficient overnight data.

    Args:
        readings: List of CGM readings (sorted or unsorted).
        min_nights: Minimum distinct nights required for valid analysis.

    Returns:
        OvernightAnalysisResult. Never raises — returns insufficient_data=True
        on empty input or insufficient nights.
    """
    if not readings:
        return OvernightAnalysisResult(nights_with_data=0, insufficient_data=True)

    overnight_df = _get_overnight_df(readings)

    if overnight_df.height == 0:
        return OvernightAnalysisResult(nights_with_data=0, insufficient_data=True)

    night_count = overnight_df.select(pl.col("night_date").n_unique()).item()
    if night_count < min_nights:
        return OvernightAnalysisResult(
            nights_with_data=night_count, insufficient_data=True
        )

    metrics = _compute_metrics(overnight_df)

    # Re-check after per-night reading filter: some raw nights may have been filtered out.
    if metrics.get("nights_with_data", 0) < min_nights:
        return OvernightAnalysisResult(
            nights_with_data=metrics.get("nights_with_data", 0),
            insufficient_data=True,
        )

    excursions = _detect_excursions(overnight_df)

    return OvernightAnalysisResult(
        mean_glucose=metrics.get("mean_glucose"),
        tir_pct=metrics.get("tir_pct"),
        cv=metrics.get("cv"),
        tbr_pct=metrics.get("tbr_pct"),
        stability_score=metrics.get("stability_score"),
        stability_label=metrics.get("stability_label"),
        weekday_mean_glucose=metrics.get("weekday_mean_glucose"),
        weekend_mean_glucose=metrics.get("weekend_mean_glucose"),
        weekday_tir_pct=metrics.get("weekday_tir_pct"),
        weekend_tir_pct=metrics.get("weekend_tir_pct"),
        excursion_summary=excursions,
        nights_with_data=metrics.get("nights_with_data", 0),
        insufficient_data=False,
    )
