"""Tests for data validator."""

import pytest
from datetime import datetime, timedelta

from cgm_insights.models import CGMReading
from cgm_insights.ingestion import (
    validate_completeness,
    detect_sensor_warmup,
    filter_by_date_range,
    exclude_warmup_period,
    MIN_COMPLETENESS_PCT,
)


def test_validate_completeness_complete_data():
    """Test completeness calculation for complete data."""
    # Create 288 readings (1 day at 5-minute intervals)
    start = datetime(2026, 4, 23, 0, 0)
    readings = [
        CGMReading(
            timestamp=start + timedelta(minutes=5 * i),
            glucose_mg_dl=100.0,
            source="test",
        )
        for i in range(288)
    ]

    result = validate_completeness(readings)

    assert result.is_valid is True
    assert result.completeness_pct >= 95.0  # Allow small rounding
    assert result.gap_count == 0


def test_validate_completeness_with_gaps():
    """Test that gaps are detected."""
    # Create readings with a 30-minute gap
    start = datetime(2026, 4, 23, 0, 0)
    readings = []
    for i in range(100):
        readings.append(
            CGMReading(
                timestamp=start + timedelta(minutes=5 * i),
                glucose_mg_dl=100.0,
                source="test",
            )
        )
    # Skip 6 readings (30 minutes)
    for i in range(106, 200):
        readings.append(
            CGMReading(
                timestamp=start + timedelta(minutes=5 * i),
                glucose_mg_dl=100.0,
                source="test",
            )
        )

    result = validate_completeness(readings)

    assert result.gap_count >= 1
    assert "data_gaps" in result.quality_flags


def test_validate_completeness_low_completeness():
    """Test that low completeness is flagged."""
    # Create only 50% of expected readings
    start = datetime(2026, 4, 23, 0, 0)
    readings = [
        CGMReading(
            timestamp=start + timedelta(minutes=10 * i),  # 10-minute intervals
            glucose_mg_dl=100.0,
            source="test",
        )
        for i in range(144)  # Half the expected readings
    ]

    result = validate_completeness(readings)

    assert result.is_valid is False
    assert "low_completeness" in result.quality_flags


def test_detect_sensor_warmup():
    """Test sensor warmup returns 0 — real warmup exclusion is handled by exclude_warmup_period."""
    start = datetime(2026, 4, 23, 0, 0)
    readings = [
        CGMReading(
            timestamp=start + timedelta(minutes=5 * i),
            glucose_mg_dl=100.0,
            source="test",
        )
        for i in range(10)
    ]

    warmup_minutes = detect_sensor_warmup(readings)

    assert warmup_minutes == 0


def test_filter_by_date_range():
    """Test date range filtering."""
    start = datetime(2026, 4, 20, 0, 0)
    readings = [
        CGMReading(
            timestamp=start + timedelta(days=i),
            glucose_mg_dl=100.0,
            source="test",
        )
        for i in range(10)
    ]

    filtered = filter_by_date_range(
        readings,
        start_date=datetime(2026, 4, 22),
        end_date=datetime(2026, 4, 25),
    )

    assert len(filtered) == 4


def test_exclude_warmup_period():
    """Test warmup period exclusion."""
    start = datetime(2026, 4, 23, 0, 0)
    # Create 50 readings (first 24 are within 2-hour warmup)
    readings = [
        CGMReading(
            timestamp=start + timedelta(minutes=5 * i),
            glucose_mg_dl=100.0,
            source="test",
        )
        for i in range(50)
    ]

    filtered = exclude_warmup_period(readings, warmup_hours=2)

    # First 24 readings (2 hours) should be excluded
    assert len(filtered) == 50 - 24
    assert filtered[0].timestamp >= start + timedelta(hours=2)


def test_normalize_for_glucostats():
    """Test normalization to GlucoStats format."""
    readings = [
        CGMReading(
            timestamp=datetime(2026, 4, 23, 8, i * 5),
            glucose_mg_dl=100.0 + i,
            source="test",
        )
        for i in range(10)
    ]

    from cgm_insights.ingestion import normalize_for_glucostats
    import polars as pl

    df = normalize_for_glucostats(readings)

    assert "time" in df.columns
    assert "glucose" in df.columns
    assert len(df) == 10


def test_to_glucostats_dataframe():
    """Test conversion to pandas DataFrame."""
    import polars as pl
    from cgm_insights.ingestion import to_glucostats_dataframe
    import pandas as pd

    df = pl.DataFrame(
        {
            "time": [datetime(2026, 4, 23, 8, 0), datetime(2026, 4, 23, 8, 5)],
            "glucose": [100.0, 105.0],
        }
    )

    pandas_df = to_glucostats_dataframe(df)

    assert isinstance(pandas_df, pd.DataFrame)
    assert "time" in pandas_df.columns
    assert "glucose" in pandas_df.columns