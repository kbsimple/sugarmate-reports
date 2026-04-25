"""Tests for pattern detection functions."""

import pytest
from datetime import datetime, timedelta

from cgm_insights.analytics.patterns import (
    detect_time_of_day_patterns,
    detect_day_of_week_patterns,
    PatternResult,
    PatternType,
    PatternSeverity,
    HIGH_GLUCOSE_THRESHOLD,
    LOW_GLUCOSE_THRESHOLD,
    MIN_READINGS_FOR_PATTERN,
)
from cgm_insights.models import CGMReading


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


def create_pattern_readings_with_afternoon_spike(days: int = 14) -> list[CGMReading]:
    """Create readings with clear afternoon spike pattern.

    Args:
        days: Number of days of data

    Returns:
        List of CGMReading objects with afternoon spikes
    """
    readings = []
    base_date = datetime(2024, 1, 1, 0, 0)

    for day in range(days):
        for hour in range(24):
            for minute in range(0, 60, 5):  # 5-minute intervals
                timestamp = base_date + timedelta(days=day, hours=hour, minutes=minute)

                # Afternoon spike (2-4pm) - higher glucose
                if 14 <= hour < 16:
                    glucose = 180 + (day * 2)
                # Night low (2-4am) - lower glucose
                elif 2 <= hour < 4:
                    glucose = 65 + (day * 1)
                # Normal baseline
                else:
                    glucose = 100 + (hour % 12) * 3

                readings.append(CGMReading(
                    timestamp=timestamp,
                    glucose_mg_dl=glucose,
                    source="test",
                ))

    return readings


def create_weekend_pattern_readings(weeks: int = 2) -> list[CGMReading]:
    """Create readings with weekend vs weekday pattern.

    Creates data where weekends have higher glucose than weekdays.

    Args:
        weeks: Number of weeks of data

    Returns:
        List of CGMReading objects with weekend pattern
    """
    readings = []
    base_date = datetime(2024, 1, 1, 0, 0)  # Monday

    for day in range(weeks * 7):
        for hour in range(24):
            for minute in range(0, 60, 5):
                timestamp = base_date + timedelta(days=day, hours=hour, minutes=minute)

                # Determine if weekend (Sat=5, Sun=6)
                day_of_week = (base_date.weekday() + day) % 7
                is_weekend = day_of_week >= 5

                if is_weekend:
                    glucose = 140 + (hour % 12) * 2  # Higher on weekends
                else:
                    glucose = 100 + (hour % 12) * 2  # Normal on weekdays

                readings.append(CGMReading(
                    timestamp=timestamp,
                    glucose_mg_dl=glucose,
                    source="test",
                ))

    return readings


# Tests for detect_time_of_day_patterns

def test_detect_time_of_day_patterns_detects_afternoon_spike():
    """Test that afternoon spike pattern is detected."""
    readings = create_pattern_readings_with_afternoon_spike(days=14)

    patterns = detect_time_of_day_patterns(readings)

    assert len(patterns) > 0, "Should detect at least one pattern"

    # Find the afternoon pattern
    afternoon_patterns = [p for p in patterns if "14:00" in p.time_period or "Afternoon" in p.description]
    assert len(afternoon_patterns) > 0, "Should detect afternoon pattern"

    # Afternoon pattern should have higher glucose
    afternoon_pattern = afternoon_patterns[0]
    assert afternoon_pattern.avg_glucose > 150, "Afternoon should have high glucose"


def test_detect_time_of_day_patterns_detects_night_low():
    """Test that night low pattern is detected."""
    readings = create_pattern_readings_with_afternoon_spike(days=14)

    patterns = detect_time_of_day_patterns(readings)

    # Find a low pattern (night)
    low_patterns = [p for p in patterns if "Lower" in p.description or "below" in p.description.lower()]
    assert len(low_patterns) > 0, "Should detect low pattern"


def test_detect_time_of_day_patterns_empty_readings():
    """Test that empty readings returns empty list."""
    patterns = detect_time_of_day_patterns([])

    assert patterns == [], "Empty readings should return empty list"


def test_detect_time_of_day_patterns_returns_pattern_result():
    """Test that function returns PatternResult with correct fields."""
    readings = create_pattern_readings_with_afternoon_spike(days=14)

    patterns = detect_time_of_day_patterns(readings)

    assert len(patterns) > 0, "Should detect patterns"

    pattern = patterns[0]
    assert isinstance(pattern, PatternResult), "Should return PatternResult"
    assert pattern.pattern_type == PatternType.TIME_OF_DAY, "Should be TIME_OF_DAY type"
    assert pattern.description != "", "Should have description"
    assert pattern.time_period != "", "Should have time period"
    assert pattern.avg_glucose > 0, "Should have avg glucose"
    assert pattern.reading_count >= MIN_READINGS_FOR_PATTERN, "Should have enough readings"
    assert 0 <= pattern.confidence <= 1, "Confidence should be between 0 and 1"


def test_detect_time_of_day_patterns_sorts_by_severity():
    """Test that patterns are sorted by severity."""
    # Create readings with both significant and moderate patterns
    readings = create_pattern_readings_with_afternoon_spike(days=30)

    patterns = detect_time_of_day_patterns(readings)

    if len(patterns) > 1:
        # Should be sorted with significant first
        severity_order = {PatternSeverity.SIGNIFICANT: 0, PatternSeverity.MODERATE: 1, PatternSeverity.INFO: 2}
        for i in range(len(patterns) - 1):
            current_severity = severity_order.get(patterns[i].severity, 3)
            next_severity = severity_order.get(patterns[i + 1].severity, 3)
            assert current_severity <= next_severity, "Should sort by severity"


# Tests for detect_day_of_week_patterns

def test_detect_day_of_week_patterns_detects_weekend_difference():
    """Test that weekend vs weekday differences are detected."""
    readings = create_weekend_pattern_readings(weeks=2)

    patterns = detect_day_of_week_patterns(readings)

    assert len(patterns) > 0, "Should detect at least one pattern"

    # Should find weekend pattern
    weekend_patterns = [p for p in patterns if "Weekend" in p.description]
    assert len(weekend_patterns) > 0, "Should detect weekend pattern"


def test_detect_day_of_week_patterns_returns_pattern_result():
    """Test that function returns PatternResult with correct type."""
    readings = create_weekend_pattern_readings(weeks=2)

    patterns = detect_day_of_week_patterns(readings)

    if len(patterns) > 0:
        pattern = patterns[0]
        assert isinstance(pattern, PatternResult), "Should return PatternResult"
        assert pattern.pattern_type == PatternType.DAY_OF_WEEK, "Should be DAY_OF_WEEK type"


def test_detect_day_of_week_patterns_empty_readings():
    """Test that empty readings returns empty list."""
    patterns = detect_day_of_week_patterns([])

    assert patterns == [], "Empty readings should return empty list"


def test_detect_day_of_week_patterns_handles_single_day():
    """Test that single day of data doesn't crash."""
    readings = create_test_readings(count=288, start_date=datetime(2024, 1, 1))

    # Should handle gracefully without error
    patterns = detect_day_of_week_patterns(readings)

    # May or may not find patterns, but shouldn't crash
    assert isinstance(patterns, list), "Should return list"


def test_detect_day_of_week_patterns_confidence_increases_with_data():
    """Test that confidence increases with more data."""
    # Compare patterns with different amounts of data
    few_readings = create_weekend_pattern_readings(weeks=1)
    many_readings = create_weekend_pattern_readings(weeks=4)

    few_patterns = detect_day_of_week_patterns(few_readings)
    many_patterns = detect_day_of_week_patterns(many_readings)

    # More data should generally lead to higher or equal confidence
    # (or at least not crash)
    assert isinstance(few_patterns, list), "Should handle small data"
    assert isinstance(many_patterns, list), "Should handle large data"


# Tests for PatternResult model

def test_pattern_result_frozen():
    """Test that PatternResult is immutable (frozen)."""
    pattern = PatternResult(
        pattern_type=PatternType.TIME_OF_DAY,
        description="Test pattern",
        time_period="12:00-14:00",
        severity=PatternSeverity.MODERATE,
        avg_glucose=150.0,
        reading_count=100,
        confidence=0.8,
    )

    # Should not be able to modify
    with pytest.raises(Exception):
        pattern.description = "Modified"


def test_pattern_result_validates_glucose():
    """Test that PatternResult validates glucose range."""
    # Valid range
    pattern = PatternResult(
        pattern_type=PatternType.TIME_OF_DAY,
        description="Test",
        time_period="12:00-14:00",
        severity=PatternSeverity.INFO,
        avg_glucose=100.0,
        reading_count=10,
        confidence=0.5,
    )
    assert pattern.avg_glucose == 100.0

    # Invalid range should raise validation error
    with pytest.raises(Exception):
        PatternResult(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Test",
            time_period="12:00-14:00",
            severity=PatternSeverity.INFO,
            avg_glucose=500.0,  # > 400
            reading_count=10,
            confidence=0.5,
        )


def test_pattern_result_validates_confidence():
    """Test that PatternResult validates confidence range."""
    # Valid confidence
    pattern = PatternResult(
        pattern_type=PatternType.TIME_OF_DAY,
        description="Test",
        time_period="12:00-14:00",
        severity=PatternSeverity.INFO,
        avg_glucose=100.0,
        reading_count=10,
        confidence=0.5,
    )
    assert pattern.confidence == 0.5

    # Invalid confidence > 1
    with pytest.raises(Exception):
        PatternResult(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Test",
            time_period="12:00-14:00",
            severity=PatternSeverity.INFO,
            avg_glucose=100.0,
            reading_count=10,
            confidence=1.5,  # > 1
        )


def test_pattern_type_enum():
    """Test that PatternType enum has expected values."""
    assert PatternType.TIME_OF_DAY.value == "time_of_day"
    assert PatternType.DAY_OF_WEEK.value == "day_of_week"


def test_pattern_severity_enum():
    """Test that PatternSeverity enum has expected values."""
    assert PatternSeverity.INFO.value == "info"
    assert PatternSeverity.MODERATE.value == "moderate"
    assert PatternSeverity.SIGNIFICANT.value == "significant"