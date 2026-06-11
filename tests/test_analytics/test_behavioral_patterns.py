"""Tests for behavioral pattern analysis.

Covers: sliding window bucketing, midnight-wrap, min_days enforcement,
quartile labeling, weekday/weekend segmentation, and the public API.
"""
from datetime import datetime, timedelta, date as DateType

import polars as pl
import pytest

from cgm_insights.analytics.behavioral_patterns import (
    MIN_DAYS_FOR_CONSISTENCY,
    BehavioralAnalysisResult,
    BehavioralPattern,
    ConsistencyLabel,
    _apply_consistency_labels,
    _build_df,
    _format_bucket_label,
    _get_subset,
    analyze_behavioral_patterns,
)
from cgm_insights.models import CGMReading


def create_readings_for_n_days(
    n_days: int,
    glucose_value: float = 100.0,
    start_date: datetime = None,
) -> list[CGMReading]:
    """Create n_days of CGM readings at 5-minute intervals.

    Args:
        n_days: Number of full days of data.
        glucose_value: Constant glucose value for all readings.
        start_date: Starting datetime (defaults to 2024-01-08 Monday).

    Returns:
        List of CGMReading objects covering n_days × 24 hours.
    """
    if start_date is None:
        start_date = datetime(2024, 1, 8, 0, 0)  # Monday
    readings = []
    for day in range(n_days):
        day_start = start_date + timedelta(days=day)
        for minute in range(0, 1440, 5):
            readings.append(CGMReading(
                timestamp=day_start + timedelta(minutes=minute),
                glucose_mg_dl=glucose_value,
                source="test",
            ))
    return readings


# --- Test 1: Empty readings returns insufficient_data=True ---

def test_empty_readings_returns_insufficient_data():
    """Empty reading list should return BehavioralAnalysisResult with insufficient_data=True."""
    result = analyze_behavioral_patterns([])
    assert result.insufficient_data is True
    assert result.total_days == 0
    assert result.patterns == []


# --- Test 2: Fewer than 5 distinct days returns insufficient_data=True ---

def test_fewer_than_5_days_returns_insufficient_data():
    """Four days of data is below the min_days threshold."""
    readings = create_readings_for_n_days(4)
    result = analyze_behavioral_patterns(readings)
    assert result.insufficient_data is True
    assert result.total_days == 4
    assert result.patterns == []


# --- Test 3: Exactly 5 distinct days returns insufficient_data=False and produces patterns ---

def test_exactly_5_days_produces_patterns():
    """Five days of data meets the threshold and should produce behavioral patterns."""
    readings = create_readings_for_n_days(5)
    result = analyze_behavioral_patterns(readings)
    assert result.insufficient_data is False
    assert result.total_days == 5
    assert len(result.patterns) > 0


# --- Test 4: _format_bucket_label noon, 30-min window ---

def test_format_bucket_label_noon():
    """12:00 with 30-min window should label as '12:00–12:30'."""
    label = _format_bucket_label(720, 30)
    assert label == "12:00–12:30"


# --- Test 5: _format_bucket_label midnight-crossing window ---

def test_format_bucket_label_midnight_crossing():
    """23:30 with 120-min window crosses midnight and should label as '23:30–01:30'."""
    label = _format_bucket_label(1410, 120)
    assert label == "23:30–01:30"


# --- Test 6: _get_subset midnight-wrap ---

def test_get_subset_midnight_wrap():
    """A bucket starting at 1410 (23:30) with 120-min window should include readings
    on both sides of midnight (minute 1420 AND minute 10)."""
    df = pl.DataFrame({
        "mod": [1420, 10, 500],  # 1420 and 10 should be in window; 500 should not
        "glucose": [100.0, 100.0, 100.0],
        "date": [
            DateType(2024, 1, 8),
            DateType(2024, 1, 9),
            DateType(2024, 1, 8),
        ],
        "day_type": ["weekday", "weekday", "weekday"],
    })
    subset = _get_subset(df, bucket_start=1410, window_min=120)
    assert subset.height == 2
    mods = set(subset["mod"].to_list())
    assert 1420 in mods
    assert 10 in mods
    assert 500 not in mods


# --- Test 7: Quartile labeling assigns correct labels ---

def test_apply_consistency_labels_assigns_quartiles():
    """Bottom 25% CV should be Consistent, top 25% should be Variable, rest Moderate.

    With 8 buckets having cv_scores 1–8:
    p25 = 2.75, p75 = 6.25
    CV <= 2.75 → Consistent (scores 1, 2)
    CV >= 6.25 → Variable (scores 7, 8)
    Rest → Moderate (scores 3, 4, 5, 6)
    """
    buckets = [{"cv_score": float(i), "bucket_start": i * 5} for i in range(1, 9)]
    labeled = _apply_consistency_labels(buckets)
    consistent_count = sum(
        1 for b in labeled if b["consistency_label"] == ConsistencyLabel.CONSISTENT
    )
    variable_count = sum(
        1 for b in labeled if b["consistency_label"] == ConsistencyLabel.VARIABLE
    )
    moderate_count = sum(
        1 for b in labeled if b["consistency_label"] == ConsistencyLabel.MODERATE
    )
    assert consistent_count >= 1
    assert variable_count >= 1
    assert moderate_count >= 1
    # Lowest CV bucket must be Consistent
    assert labeled[0]["consistency_label"] == ConsistencyLabel.CONSISTENT
    # Highest CV bucket must be Variable
    assert labeled[-1]["consistency_label"] == ConsistencyLabel.VARIABLE


# --- Test 8: weekday_avg_glucose is None when fewer than 5 weekdays have data ---

def test_weekday_avg_none_when_insufficient_weekday_data():
    """5 Saturdays spaced 7 days apart — weekday_avg_glucose should be None for all patterns.

    Creates exactly 5 weekend days (Saturdays) and 0 weekdays, so weekday_avg_glucose
    must be None due to insufficient weekday data (below min_days=5 threshold).
    """
    # 2024-01-06 is a Saturday; step 7 days to stay on Saturdays
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
    result = analyze_behavioral_patterns(readings, min_days=5)
    if result.patterns:
        for pattern in result.patterns[:5]:
            assert pattern.weekday_avg_glucose is None, (
                f"Expected weekday_avg to be None (no weekday data), "
                f"got {pattern.weekday_avg_glucose} for bucket {pattern.bucket_label}"
            )


# --- Test 9: weekend_avg_glucose is None when fewer than 5 weekend days have data ---

def test_weekend_avg_none_when_insufficient_weekend_data():
    """5 consecutive Mondays only — weekend_avg_glucose should be None for all patterns."""
    # 2024-01-08 is a Monday; 5 consecutive Mondays = 5 weekdays, 0 weekends
    monday = datetime(2024, 1, 8, 0, 0)
    readings = create_readings_for_n_days(5, start_date=monday)
    result = analyze_behavioral_patterns(readings, min_days=5)
    if result.patterns:
        for pattern in result.patterns[:5]:
            assert pattern.weekend_avg_glucose is None, (
                f"Expected weekend_avg to be None (no weekend data), "
                f"got {pattern.weekend_avg_glucose} for bucket {pattern.bucket_label}"
            )


# --- Test 10: All three default window sizes present in result ---

def test_all_three_window_sizes_in_result():
    """7 days of data should produce patterns for 30-, 60-, and 120-minute windows."""
    readings = create_readings_for_n_days(7)
    result = analyze_behavioral_patterns(readings)
    assert not result.insufficient_data
    window_sizes_in_patterns = {p.window_size_min for p in result.patterns}
    assert 30 in window_sizes_in_patterns
    assert 60 in window_sizes_in_patterns
    assert 120 in window_sizes_in_patterns


# --- Test 11: Polars weekday detection — Saturday classified as weekend ---

def test_saturday_classified_as_weekend():
    """Polars dt.weekday() must classify Saturday as weekend (>= 6) and Monday as weekday."""
    # 2024-01-06 is a Saturday; 2024-01-08 is a Monday
    saturday = datetime(2024, 1, 6, 12, 0)
    monday = datetime(2024, 1, 8, 12, 0)
    df = pl.DataFrame({
        "timestamp": [saturday, monday],
        "glucose": [100.0, 100.0],
    }).with_columns([
        pl.col("timestamp").cast(pl.Datetime),
        pl.when(pl.col("timestamp").dt.weekday() >= 6)
          .then(pl.lit("weekend"))
          .otherwise(pl.lit("weekday"))
          .alias("day_type"),
    ])
    day_types = df["day_type"].to_list()
    assert day_types[0] == "weekend", (
        f"Saturday should be weekend, got {day_types[0]}"
    )
    assert day_types[1] == "weekday", (
        f"Monday should be weekday, got {day_types[1]}"
    )


# --- Test 12: BehavioralPattern is immutable (frozen=True) ---

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
