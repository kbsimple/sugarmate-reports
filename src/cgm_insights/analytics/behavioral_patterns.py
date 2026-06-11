"""Behavioral pattern analysis for CGM glucose data.

Implements sliding-window time-bucket aggregation (30/60/120-min windows,
5-min slide) with cross-day consistency scoring. All insights use wellness
language — no medical advice.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from cgm_insights.models import CGMReading


SLIDE_MINUTES: int = 5
DEFAULT_WINDOW_SIZES: list[int] = [30, 60, 120]
MIN_DAYS_FOR_CONSISTENCY: int = 5


class ConsistencyLabel(str, Enum):
    """Qualitative consistency label for a time bucket."""

    CONSISTENT = "Consistent"
    MODERATE = "Moderate"
    VARIABLE = "Variable"


class BehavioralPattern(BaseModel):
    """Cross-day glucose behavior for a single time bucket.

    Attributes:
        window_size_min: Duration of the time window in minutes (30, 60, or 120).
        bucket_start_minute: Minutes from midnight for the start of this window (0–1439).
        bucket_label: Human-readable label e.g. "12:00–12:30".
        consistency_label: Qualitative label (Consistent/Moderate/Variable).
        cv_score: Coefficient of variation of daily means. Lower = more consistent.
        avg_glucose: Mean glucose across all readings in this bucket (mg/dL).
        weekday_avg_glucose: Mean glucose on weekdays, or None if < 5 weekdays with data.
        weekend_avg_glucose: Mean glucose on weekends, or None if < 5 weekend days with data.
        days_with_data: Distinct calendar days with readings in this bucket.
        reading_count: Total readings in this bucket across all days.
    """

    window_size_min: int = Field(..., description="Window size in minutes")
    bucket_start_minute: int = Field(..., ge=0, lt=1440)
    bucket_label: str = Field(..., description="Human-readable time range")
    consistency_label: ConsistencyLabel
    cv_score: float = Field(
        ..., ge=0.0, description="CV of daily means (lower=more consistent)"
    )
    avg_glucose: float = Field(..., ge=40.0, le=400.0)
    weekday_avg_glucose: Optional[float] = Field(None, ge=40.0, le=400.0)
    weekend_avg_glucose: Optional[float] = Field(None, ge=40.0, le=400.0)
    days_with_data: int = Field(..., ge=1)
    reading_count: int = Field(..., ge=1)

    model_config = ConfigDict(frozen=True)


class BehavioralAnalysisResult(BaseModel):
    """Results from behavioral pattern analysis across all window sizes.

    Attributes:
        patterns: All valid BehavioralPattern objects across all window sizes.
        window_sizes: Window sizes that were analyzed.
        total_days: Total distinct calendar days in the reading set.
        insufficient_data: True when total_days < MIN_DAYS_FOR_CONSISTENCY.
    """

    patterns: list[BehavioralPattern] = Field(default_factory=list)
    window_sizes: list[int] = Field(default_factory=list)
    total_days: int = Field(..., ge=0)
    insufficient_data: bool = Field(False)

    model_config = ConfigDict(frozen=True)


def _build_df(readings: list[CGMReading]) -> pl.DataFrame:
    """Build a Polars DataFrame from CGM readings with time metadata columns.

    Args:
        readings: List of CGM readings to convert.

    Returns:
        DataFrame with timestamp, glucose, mod (minute-of-day), date, and
        day_type ('weekday' or 'weekend') columns.
    """
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
            pl.when(pl.col("timestamp").dt.weekday() >= 6)
            .then(pl.lit("weekend"))
            .otherwise(pl.lit("weekday"))
            .alias("day_type"),
        ]
    )


def _format_bucket_label(bucket_start_minute: int, window_min: int) -> str:
    """Format a time bucket as a human-readable label.

    Args:
        bucket_start_minute: Minutes from midnight (0–1439).
        window_min: Window size in minutes.

    Returns:
        Human-readable label such as "12:00–12:30" or "23:30–00:30" for
        midnight-crossing windows. Uses en dash between start and end.
    """
    start_h, start_m = divmod(bucket_start_minute, 60)
    end_minute = (bucket_start_minute + window_min) % 1440
    end_h, end_m = divmod(end_minute, 60)
    return f"{start_h:02d}:{start_m:02d}–{end_h:02d}:{end_m:02d}"


def _get_subset(df: pl.DataFrame, bucket_start: int, window_min: int) -> pl.DataFrame:
    """Filter DataFrame to readings falling within a time bucket.

    Handles midnight-crossing windows correctly via OR filter logic.

    Args:
        df: Full DataFrame with 'mod' (minute-of-day) column.
        bucket_start: Start minute of the bucket (0–1439).
        window_min: Window duration in minutes.

    Returns:
        Filtered DataFrame subset for readings in the bucket.
    """
    bucket_end = bucket_start + window_min
    if bucket_end <= 1440:
        return df.filter(
            (pl.col("mod") >= bucket_start) & (pl.col("mod") < bucket_end)
        )
    else:
        # Window crosses midnight
        return df.filter(
            (pl.col("mod") >= bucket_start) | (pl.col("mod") < (bucket_end - 1440))
        )


def _daily_stats(
    subset: pl.DataFrame,
    day_type_filter: Optional[str] = None,
    min_days: int = MIN_DAYS_FOR_CONSISTENCY,
) -> tuple[Optional[float], int]:
    """Compute average glucose and day count for a reading subset.

    Args:
        subset: DataFrame subset with 'glucose', 'date', and 'day_type' columns.
        day_type_filter: If set, restrict to 'weekday' or 'weekend' rows only.
        min_days: Minimum distinct days required before returning an average.

    Returns:
        Tuple of (avg_glucose, days_count). avg_glucose is None when fewer
        than min_days distinct days are present.
    """
    if day_type_filter is not None:
        subset = subset.filter(pl.col("day_type") == day_type_filter)
    if subset.height == 0:
        return None, 0
    daily = subset.group_by("date").agg(pl.col("glucose").mean().alias("daily_mean"))
    if daily.height < min_days:
        return None, daily.height
    avg = daily["daily_mean"].mean()
    return avg, daily.height


def _compute_all_buckets(
    df: pl.DataFrame,
    window_min: int,
    min_days: int = MIN_DAYS_FOR_CONSISTENCY,
) -> list[dict]:
    """Compute per-bucket statistics for one window size.

    Iterates over all 288 possible 5-minute bucket starts (0 to 1435),
    skipping buckets with fewer than min_days distinct days.

    Args:
        df: Full DataFrame with 'mod', 'date', 'day_type', and 'glucose' columns.
        window_min: Window size in minutes.
        min_days: Minimum distinct days required for a bucket to be included.

    Returns:
        List of dicts containing raw bucket statistics (no consistency labels yet).
        Each dict has: bucket_start, avg_glucose, cv_score, days_with_data,
        reading_count, weekday_avg_glucose, weekend_avg_glucose.
    """
    results = []
    for bs in range(0, 1440, SLIDE_MINUTES):
        subset = _get_subset(df, bs, window_min)
        if subset.height == 0:
            continue
        daily = (
            subset.group_by("date")
            .agg(
                pl.col("glucose").mean().alias("daily_mean"),
                pl.col("glucose").count().alias("count"),
            )
        )
        if daily.height < min_days:
            continue
        avg_g = daily["daily_mean"].mean()
        std_g = daily["daily_mean"].std()
        if std_g is None or avg_g is None or avg_g <= 0:
            cv = 0.0
        else:
            cv = std_g / avg_g * 100
        weekday_avg, _ = _daily_stats(subset, "weekday", min_days)
        weekend_avg, _ = _daily_stats(subset, "weekend", min_days)
        results.append(
            {
                "bucket_start": bs,
                "avg_glucose": avg_g,
                "cv_score": cv,
                "days_with_data": daily.height,
                "reading_count": subset.height,
                "weekday_avg_glucose": weekday_avg,
                "weekend_avg_glucose": weekend_avg,
            }
        )
    return results


def _apply_consistency_labels(buckets: list[dict]) -> list[dict]:
    """Assign Consistent/Moderate/Variable labels using per-window quartile thresholds.

    Labels are relative to the user's own distribution of CV scores for this
    window size. Bottom quartile (CV <= p25) = Consistent, top quartile
    (CV >= p75) = Variable, middle 50% = Moderate.

    Quartile thresholds are computed independently per window size call
    to avoid cross-window comparison artifacts (Pitfall 3).

    Args:
        buckets: List of bucket dicts with 'cv_score' key.

    Returns:
        Same list with 'consistency_label' (ConsistencyLabel) added to each dict.
    """
    if not buckets:
        return buckets
    cv_series = pl.Series("cv", [b["cv_score"] for b in buckets])
    p25 = cv_series.quantile(0.25)
    p75 = cv_series.quantile(0.75)
    # Degenerate case: all CV scores are identical (p25 == p75 means zero spread).
    # Labeling in this case floods every bucket with CONSISTENT, producing redundant
    # suggestions. Skip labeling entirely and return no buckets.
    if p25 == p75:
        return []
    for b in buckets:
        if b["cv_score"] <= p25:
            b["consistency_label"] = ConsistencyLabel.CONSISTENT
        elif b["cv_score"] >= p75:
            b["consistency_label"] = ConsistencyLabel.VARIABLE
        else:
            b["consistency_label"] = ConsistencyLabel.MODERATE
    return buckets


def analyze_behavioral_patterns(
    readings: list[CGMReading],
    window_sizes: Optional[list[int]] = None,
    min_days: int = MIN_DAYS_FOR_CONSISTENCY,
) -> BehavioralAnalysisResult:
    """Analyze cross-day glucose behavior using sliding time windows.

    Computes sliding-window time-bucket aggregation across all days in the
    reading set. Each bucket is scored by coefficient of variation of daily
    means and assigned a relative consistency label (Consistent/Moderate/Variable)
    using per-window quartile thresholds.

    Args:
        readings: List of CGM readings (sorted or unsorted).
        window_sizes: Window sizes in minutes. Defaults to [30, 60, 120].
        min_days: Minimum distinct days required for a valid consistency score.

    Returns:
        BehavioralAnalysisResult with patterns for each window size.
        Returns insufficient_data=True when total_days < min_days.
    """
    if window_sizes is None:
        window_sizes = DEFAULT_WINDOW_SIZES
    if not readings:
        return BehavioralAnalysisResult(
            patterns=[],
            window_sizes=window_sizes,
            total_days=0,
            insufficient_data=True,
        )
    df = _build_df(readings)
    total_days = df.select(pl.col("date").n_unique()).item()
    if total_days < min_days:
        return BehavioralAnalysisResult(
            patterns=[],
            window_sizes=window_sizes,
            total_days=total_days,
            insufficient_data=True,
        )
    all_patterns: list[BehavioralPattern] = []
    for window_min in window_sizes:
        raw_buckets = _compute_all_buckets(df, window_min, min_days)
        labeled = _apply_consistency_labels(raw_buckets)
        for b in labeled:
            pattern = BehavioralPattern(
                window_size_min=window_min,
                bucket_start_minute=b["bucket_start"],
                bucket_label=_format_bucket_label(b["bucket_start"], window_min),
                consistency_label=b["consistency_label"],
                cv_score=b["cv_score"],
                avg_glucose=b["avg_glucose"],
                weekday_avg_glucose=b["weekday_avg_glucose"],
                weekend_avg_glucose=b["weekend_avg_glucose"],
                days_with_data=b["days_with_data"],
                reading_count=b["reading_count"],
            )
            all_patterns.append(pattern)
    return BehavioralAnalysisResult(
        patterns=all_patterns,
        window_sizes=window_sizes,
        total_days=total_days,
        insufficient_data=False,
    )
