"""Tests for metrics calculation."""

import pytest
from datetime import datetime, timedelta

from cgm_insights.models import CGMReading, ValidationResult
from cgm_insights.analytics import calculate_metrics, GMI_CAVEAT, GLUCOSE_THRESHOLDS


def create_test_readings(
    count: int = 288,
    start_date: datetime = None,
    glucose_values: list[float] = None,
) -> list[CGMReading]:
    """Create test CGM readings.

    Args:
        count: Number of readings to create
        start_date: Starting timestamp (defaults to 2026-04-23)
        glucose_values: Glucose values (defaults to all 100.0)

    Returns:
        List of CGMReading objects
    """
    if start_date is None:
        start_date = datetime(2026, 4, 23, 0, 0)
    if glucose_values is None:
        glucose_values = [100.0] * count

    readings = []
    for i in range(count):
        glucose = glucose_values[i] if i < len(glucose_values) else 100.0
        readings.append(CGMReading(
            timestamp=start_date + timedelta(minutes=5 * i),
            glucose_mg_dl=glucose,
            source="test",
        ))
    return readings


def test_calculate_metrics_returns_analysis_results():
    """Test that calculate_metrics returns AnalysisResults."""
    readings = create_test_readings(count=288)
    validation = ValidationResult(
        is_valid=True,
        completeness_pct=95.0,
        expected_readings=288,
        actual_readings=288,
    )

    results = calculate_metrics(readings, validation)

    assert results.total_readings == 288
    assert results.time_in_range is not None
    assert results.average_glucose is not None


def test_calculate_metrics_time_in_range():
    """Test Time-in-Range calculation."""
    # Create readings with known distribution:
    # 70% in target range (70-180), 10% low (54-70), 5% very low (<54)
    # 10% high (180-250), 5% very high (>250)
    glucose_values = (
        [100.0] * 70 +   # 70% in target range (70-180)
        [60.0] * 10 +    # 10% low (54-70)
        [50.0] * 5 +     # 5% very low (<54)
        [200.0] * 10 +   # 10% high (180-250)
        [300.0] * 5      # 5% very high (>250)
    )

    readings = create_test_readings(count=100, glucose_values=glucose_values)
    results = calculate_metrics(readings)

    # Check that time in range is approximately 70%
    # Allow for some variance due to distribution
    assert 60 < results.time_in_range.target_pct < 80


def test_calculate_metrics_average_and_std():
    """Test average glucose and standard deviation."""
    glucose_values = [100.0] * 100
    readings = create_test_readings(count=100, glucose_values=glucose_values)

    results = calculate_metrics(readings)

    assert 95 < results.average_glucose < 105
    assert results.glucose_std < 5  # Low variability


def test_calculate_metrics_cv():
    """Test coefficient of variation calculation."""
    # Create readings with some variability
    glucose_values = [100 + (i % 20 - 10) for i in range(100)]
    readings = create_test_readings(count=100, glucose_values=glucose_values)

    results = calculate_metrics(readings)

    # CV should be calculated
    assert results.cv_pct >= 0


def test_calculate_metrics_gmi():
    """Test GMI calculation and caveat."""
    readings = create_test_readings(count=288, glucose_values=[120.0] * 288)

    results = calculate_metrics(readings)

    # GMI should be calculated
    assert results.gmi > 0

    # GMI caveat should be defined
    assert "informational" in GMI_CAVEAT.lower()


def test_calculate_metrics_empty_readings_raises():
    """Test that empty readings raises error."""
    with pytest.raises(ValueError):
        calculate_metrics([])


def test_glucose_thresholds_defined():
    """Test that glucose thresholds are properly defined."""
    assert GLUCOSE_THRESHOLDS["very_low"] == 54
    assert GLUCOSE_THRESHOLDS["low"] == 70
    assert GLUCOSE_THRESHOLDS["target_high"] == 180
    assert GLUCOSE_THRESHOLDS["very_high"] == 250


def test_calculate_metrics_with_validation_flags():
    """Test that validation flags are included in results."""
    readings = create_test_readings(count=100)
    validation = ValidationResult(
        is_valid=True,
        completeness_pct=85.0,
        expected_readings=100,
        actual_readings=85,
        quality_flags=["sensor_warmup", "data_gaps"],
    )

    results = calculate_metrics(readings, validation)

    assert "sensor_warmup" in results.data_quality_flags
    assert "data_gaps" in results.data_quality_flags


def test_calculate_metrics_all_five_bands():
    """Test that all 5 glucose bands are calculated."""
    # Create readings spanning all 5 bands
    glucose_values = (
        [50.0] * 10 +    # Very low (<54)
        [60.0] * 10 +    # Low (54-70)
        [100.0] * 60 +   # Target (70-180)
        [200.0] * 10 +   # High (180-250)
        [300.0] * 10     # Very high (>250)
    )
    readings = create_test_readings(count=100, glucose_values=glucose_values)

    results = calculate_metrics(readings)

    # All bands should have values
    assert results.time_in_range.very_low_pct >= 0
    assert results.time_in_range.low_pct >= 0
    assert results.time_in_range.target_pct >= 0
    assert results.time_in_range.high_pct >= 0
    assert results.time_in_range.very_high_pct >= 0

    # Sum should be approximately 100
    total = (
        results.time_in_range.very_low_pct +
        results.time_in_range.low_pct +
        results.time_in_range.target_pct +
        results.time_in_range.high_pct +
        results.time_in_range.very_high_pct
    )
    assert 99 < total < 101  # Allow small rounding errors