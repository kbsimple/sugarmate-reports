"""Tests for CGMReading model."""

import pytest
from datetime import datetime
from pydantic import ValidationError
from cgm_insights.models import CGMReading


def test_valid_reading():
    """Test that valid glucose reading is accepted."""
    reading = CGMReading(
        timestamp=datetime(2026, 4, 23, 8, 3),
        glucose_mg_dl=150,
        trend="→",
        source="sugarmate"
    )
    assert reading.glucose_mg_dl == 150
    assert reading.trend == "→"


def test_rejects_glucose_below_range():
    """Test that glucose below 40 mg/dL is rejected."""
    with pytest.raises(ValidationError):
        CGMReading(
            timestamp=datetime(2026, 4, 23, 8, 3),
            glucose_mg_dl=30
        )


def test_rejects_glucose_above_range():
    """Test that glucose above 400 mg/dL is rejected."""
    with pytest.raises(ValidationError):
        CGMReading(
            timestamp=datetime(2026, 4, 23, 8, 3),
            glucose_mg_dl=500
        )


def test_accepts_edge_values():
    """Test that edge values (40 and 400) are accepted."""
    low = CGMReading(timestamp=datetime(2026, 4, 23, 8, 3), glucose_mg_dl=40)
    high = CGMReading(timestamp=datetime(2026, 4, 23, 8, 3), glucose_mg_dl=400)
    assert low.glucose_mg_dl == 40
    assert high.glucose_mg_dl == 400


def test_optional_trend_and_source():
    """Test that trend and source are optional with defaults."""
    reading = CGMReading(
        timestamp=datetime(2026, 4, 23, 8, 3),
        glucose_mg_dl=100
    )
    assert reading.trend is None
    assert reading.source == "unknown"