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


def create_overnight_readings(
    n_nights: int,
    glucose_value: float = 100.0,
    start_hour: int = 22,
    interval_minutes: int = 5,
) -> list[CGMReading]:
    """Create CGMReading objects covering n_nights of overnight data.

    Each night starts at start_hour:00 on 2024-01-08 (Monday) and covers
    8 hours at interval_minutes resolution.

    Args:
        n_nights: Number of overnight windows to generate.
        glucose_value: Constant glucose value for all readings (mg/dL).
        start_hour: Hour-of-day to start each overnight window (default 22).
        interval_minutes: Sampling interval in minutes (default 5).

    Returns:
        List of CGMReading objects.
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


def test_empty_readings_returns_insufficient_data():
    """Empty reading list must return OvernightAnalysisResult with insufficient_data=True."""
    result = analyze_overnight_patterns([])
    assert result.insufficient_data is True
    assert result.nights_with_data == 0
    assert result.mean_glucose is None


def test_fewer_than_min_nights_returns_insufficient_data():
    """Four nights of overnight data must return insufficient_data=True."""
    readings = create_overnight_readings(n_nights=4)
    result = analyze_overnight_patterns(readings)
    assert result.insufficient_data is True
    assert result.nights_with_data == 4


def test_exactly_min_nights_produces_result():
    """Five nights of data is the minimum for a valid analysis result."""
    readings = create_overnight_readings(n_nights=5, glucose_value=110.0)
    result = analyze_overnight_patterns(readings)
    assert result.insufficient_data is False
    assert result.nights_with_data == 5
    assert result.mean_glucose is not None
    assert 109.0 <= result.mean_glucose <= 111.0


def test_midnight_crossing_filter_captures_pre_and_post_midnight():
    """Readings at 23:30 and 01:00 must both appear in the overnight DataFrame;
    a reading at 12:00 must be excluded."""
    readings = [
        CGMReading(timestamp=datetime(2024, 1, 8, 23, 30), glucose_mg_dl=100.0, source="test"),
        CGMReading(timestamp=datetime(2024, 1, 9, 1, 0), glucose_mg_dl=100.0, source="test"),
        CGMReading(timestamp=datetime(2024, 1, 8, 12, 0), glucose_mg_dl=100.0, source="test"),
    ]
    df = _get_overnight_df(readings)
    # 23:30 = mod 1410 >= 1320 (included); 01:00 = mod 60 < 360 (included); 12:00 excluded
    assert df.height == 2


def test_night_date_uses_evening_start_not_morning_end():
    """A reading at 01:00 on Tuesday belongs to Monday's overnight window.

    night_date for a 2024-01-09 01:00 reading must be 2024-01-08 (Monday),
    not 2024-01-09 (Tuesday).
    """
    readings = [
        # Monday 23:00 — stays Monday
        CGMReading(timestamp=datetime(2024, 1, 8, 23, 0), glucose_mg_dl=100.0, source="test"),
        # Tuesday 01:00 — maps back to Monday night
        CGMReading(timestamp=datetime(2024, 1, 9, 1, 0), glucose_mg_dl=100.0, source="test"),
    ]
    df = _get_overnight_df(readings)
    night_dates = df["night_date"].to_list()
    monday = date(2024, 1, 8)
    assert all(d == monday for d in night_dates), (
        f"Expected all night_dates = {monday}, got {night_dates}"
    )


def test_stability_score_matches_formula():
    """Stability score must equal max(0, 1 - cv/100) and be labeled correctly.

    With constant glucose across all nights, CV = 0 → stability_score = 1.0,
    label = 'Stable'.
    """
    readings = create_overnight_readings(n_nights=7, glucose_value=105.0)
    result = analyze_overnight_patterns(readings)
    assert result.stability_score is not None
    # Constant glucose → CV ≈ 0 → stability_score ≈ 1.0
    assert result.stability_score >= 0.99
    assert result.stability_label == "Stable"


def test_excursion_detection_requires_three_consecutive_readings():
    """Two consecutive high readings do NOT constitute a sustained excursion;
    three consecutive readings DO."""
    def make_night(night_offset: int, glucose_values: list[float]) -> list[CGMReading]:
        """Create readings for one overnight window at 5-min intervals from 22:00."""
        start = datetime(2024, 1, 8, 22, 0) + timedelta(days=night_offset)
        return [
            CGMReading(
                timestamp=start + timedelta(minutes=i * 5),
                glucose_mg_dl=g,
                source="test",
            )
            for i, g in enumerate(glucose_values)
        ]

    # Night with only 2 consecutive highs — should NOT trigger excursion
    two_high_night = make_night(0, [200.0, 200.0] + [100.0] * 94)
    # Night with 3 consecutive highs — SHOULD trigger excursion
    three_high_night = make_night(0, [200.0, 200.0, 200.0] + [100.0] * 93)

    # Pad with 4 normal nights starting at day 1
    normal_nights = [
        CGMReading(
            timestamp=datetime(2024, 1, 9, 22, 0) + timedelta(days=d, minutes=m * 5),
            glucose_mg_dl=100.0,
            source="test",
        )
        for d in range(4)
        for m in range(96)  # 8 hours * 12 readings/hour
    ]

    result_no_excursion = analyze_overnight_patterns(two_high_night + normal_nights)
    result_with_excursion = analyze_overnight_patterns(three_high_night + normal_nights)

    assert result_no_excursion.excursion_summary.get("sustained_high_nights", 0) == 0
    assert result_with_excursion.excursion_summary.get("sustained_high_nights", 0) >= 1


def test_overnight_analysis_result_is_frozen():
    """OvernightAnalysisResult must be immutable (ConfigDict frozen=True)."""
    result = OvernightAnalysisResult(nights_with_data=0, insufficient_data=True)
    with pytest.raises(Exception):
        result.nights_with_data = 5  # type: ignore[misc]


def test_overnight_window_constants():
    """OVERNIGHT_START_MINUTE must be 1320 (22:00) and OVERNIGHT_WINDOW_MINUTES must be 480."""
    assert OVERNIGHT_START_MINUTE == 1320  # 22 * 60
    assert OVERNIGHT_WINDOW_MINUTES == 480  # 8 hours
    # Derived: window end wraps to 06:00
    assert (OVERNIGHT_START_MINUTE + OVERNIGHT_WINDOW_MINUTES) - 1440 == 6 * 60


def test_tir_and_tbr_are_valid_percentages():
    """tir_pct and tbr_pct must be in [0.0, 100.0].

    95 mg/dL is in target range (70-180), so TIR should be ~100% and TBR ~0%.
    """
    readings = create_overnight_readings(n_nights=7, glucose_value=95.0)
    result = analyze_overnight_patterns(readings)
    assert result.tir_pct is not None
    assert 0.0 <= result.tir_pct <= 100.0
    assert result.tbr_pct is not None
    assert 0.0 <= result.tbr_pct <= 100.0
    assert result.tir_pct >= 99.0
    assert result.tbr_pct <= 1.0
