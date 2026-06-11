"""Tests for anomaly detection analysis."""
from datetime import datetime, timedelta

import pytest

from cgm_insights.analytics.anomaly_detection import (
    MIN_DAYS_FOR_BASELINE,
    BUCKET_MINUTES,
    PISA_DROP_THRESHOLD_PCT,
    PISA_RECOVERY_WINDOW_MINUTES,
    ANOMALY_SD_MILD,
    ANOMALY_SD_MODERATE,
    ANOMALY_SD_SEVERE,
    AnomalyDetectionResult,
    WeeklySummary,
    _classify_severity,
    analyze_anomalies,
)
from cgm_insights.models import CGMReading


def create_readings(
    n_days: int,
    glucose_value: float = 100.0,
    interval_minutes: int = 5,
    start_dt: datetime | None = None,
) -> list[CGMReading]:
    """Create CGMReading objects covering n_days of continuous data.

    Each day generates readings at interval_minutes cadence from 00:00 to 23:55.
    Default start is Monday 2024-01-08 00:00:00 for deterministic day_type.

    Args:
        n_days: Number of calendar days of readings to generate.
        glucose_value: Uniform glucose value for all readings (mg/dL).
        interval_minutes: Time between consecutive readings (default: 5).
        start_dt: Override start datetime (default: 2024-01-08 00:00:00).

    Returns:
        List of CGMReading with source="test".
    """
    if start_dt is None:
        start_dt = datetime(2024, 1, 8, 0, 0)
    readings = []
    for day in range(n_days):
        day_start = start_dt + timedelta(days=day)
        minutes_in_day = 24 * 60
        for minute in range(0, minutes_in_day, interval_minutes):
            readings.append(
                CGMReading(
                    timestamp=day_start + timedelta(minutes=minute),
                    glucose_mg_dl=glucose_value,
                    source="test",
                )
            )
    return readings


def test_empty_readings_returns_insufficient_data():
    """Empty reading list returns AnomalyDetectionResult with insufficient_data=True."""
    result = analyze_anomalies([])
    assert result.insufficient_data is True
    assert result.total_anomalies == 0
    assert result.weekly_summaries == []


def test_fewer_than_min_days_returns_insufficient_data():
    """Four days of data (below MIN_DAYS_FOR_BASELINE=5) returns insufficient_data=True."""
    readings = create_readings(n_days=4)
    result = analyze_anomalies(readings)
    assert result.insufficient_data is True
    assert result.days_analyzed == 4


def test_exactly_min_days_produces_result():
    """Five days is the minimum for a valid analysis result.

    Uniform glucose means SD=0 across all buckets, so baselines are empty
    after the bucket_std>0 filter — total_anomalies must be 0.
    """
    readings = create_readings(n_days=5, glucose_value=110.0)
    result = analyze_anomalies(readings)
    assert result.insufficient_data is False
    assert result.days_analyzed == 5
    assert result.total_anomalies == 0


def test_anomaly_detection_result_is_frozen():
    """AnomalyDetectionResult must be immutable (ConfigDict frozen=True)."""
    result = AnomalyDetectionResult(insufficient_data=True)
    with pytest.raises(Exception):
        result.total_anomalies = 5  # type: ignore[misc]


def test_weekly_summary_is_frozen():
    """WeeklySummary must be immutable (ConfigDict frozen=True)."""
    summary = WeeklySummary(
        iso_week=1,
        year=2024,
        week_label="Week of Jan 1",
        total_anomalies=0,
    )
    with pytest.raises(Exception):
        summary.total_anomalies = 99  # type: ignore[misc]


def test_pisa_artifacts_filtered_count():
    """PISA drop/recovery pattern must be detected and filtered.

    Insert 3 readings with 40% drop and same-minute recovery into 10 normal days.
    pisa_artifacts_filtered must be >= 1.
    """
    base_readings = create_readings(n_days=10, glucose_value=100.0)
    # Insert PISA signature: drop to 60 (40% below 100) then recover to 98
    pisa_base = datetime(2024, 1, 8, 2, 0)
    pisa_readings = [
        CGMReading(timestamp=pisa_base, glucose_mg_dl=100.0, source="test"),
        CGMReading(timestamp=pisa_base + timedelta(minutes=5), glucose_mg_dl=60.0, source="test"),
        CGMReading(timestamp=pisa_base + timedelta(minutes=10), glucose_mg_dl=58.0, source="test"),
        CGMReading(timestamp=pisa_base + timedelta(minutes=30), glucose_mg_dl=98.0, source="test"),
    ]
    all_readings = base_readings + pisa_readings
    result = analyze_anomalies(all_readings)
    assert result.pisa_artifacts_filtered >= 1


def test_classify_severity_thresholds():
    """_classify_severity must return correct tier at exact boundary values."""
    assert _classify_severity(1.9) is None
    assert _classify_severity(2.0).value == "mild"
    assert _classify_severity(2.99).value == "mild"
    assert _classify_severity(3.0).value == "moderate"
    assert _classify_severity(3.99).value == "moderate"
    assert _classify_severity(4.0).value == "severe"
    assert _classify_severity(10.0).value == "severe"


def test_weekly_summaries_have_no_individual_readings():
    """AnomalyDetectionResult.model_dump() must not contain individual reading fields.

    Enforces ANLY-05: no individual reading timestamps or glucose values in output.
    """
    readings = create_readings(n_days=30, glucose_value=100.0)
    result = analyze_anomalies(readings)
    dumped = result.model_dump()
    forbidden = {"readings", "anomalous_readings", "raw_readings"}
    assert not forbidden.intersection(dumped.keys()), (
        f"AnomalyDetectionResult.model_dump() contains individual reading fields: "
        f"{forbidden.intersection(dumped.keys())}"
    )


def test_module_constants():
    """Module constants must match their specified values."""
    assert MIN_DAYS_FOR_BASELINE == 5
    assert BUCKET_MINUTES == 30
    assert PISA_DROP_THRESHOLD_PCT == 20.0
    assert PISA_RECOVERY_WINDOW_MINUTES == 60
    assert ANOMALY_SD_MILD == 2.0
    assert ANOMALY_SD_MODERATE == 3.0
    assert ANOMALY_SD_SEVERE == 4.0
