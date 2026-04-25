"""Tests for results models."""

import pytest
from datetime import datetime
from pydantic import ValidationError
from cgm_insights.models import (
    ValidationResult,
    AnalysisResults,
    TimeInRange,
)


def test_validation_result_completeness():
    """Test ValidationResult captures completeness."""
    result = ValidationResult(
        is_valid=True,
        completeness_pct=92.5,
        expected_readings=288,
        actual_readings=266
    )
    assert result.completeness_pct == 92.5
    assert result.is_valid is True


def test_validation_result_flags_warmup():
    """Test ValidationResult flags sensor warmup."""
    result = ValidationResult(
        is_valid=True,
        completeness_pct=90.0,
        expected_readings=288,
        actual_readings=260,
        sensor_warmup_minutes=120,
        quality_flags=["sensor_warmup"]
    )
    assert "sensor_warmup" in result.quality_flags
    assert result.sensor_warmup_minutes == 120


def test_time_in_range_sum():
    """Test that TIR percentages sum to ~100."""
    tir = TimeInRange(
        very_low_pct=1.0,
        low_pct=4.0,
        target_pct=70.0,
        high_pct=20.0,
        very_high_pct=5.0
    )
    assert abs(tir.total_pct - 100.0) < 0.01


def test_analysis_results_required_fields():
    """Test AnalysisResults contains all required metric fields."""
    results = AnalysisResults(
        date_range_start=datetime(2026, 4, 1),
        date_range_end=datetime(2026, 4, 14),
        total_readings=4032,
        time_in_range=TimeInRange(
            very_low_pct=1.0,
            low_pct=4.0,
            target_pct=70.0,
            high_pct=20.0,
            very_high_pct=5.0
        ),
        average_glucose=148.5,
        glucose_std=42.3,
        cv_pct=28.5,
        gmi=6.8,
        completeness_pct=95.0
    )
    assert results.time_in_range.target_pct == 70.0
    assert results.cv_pct == 28.5
    assert results.gmi == 6.8


def test_analysis_results_quality_flags():
    """Test that quality flags are populated."""
    results = AnalysisResults(
        date_range_start=datetime(2026, 4, 1),
        date_range_end=datetime(2026, 4, 14),
        total_readings=4032,
        time_in_range=TimeInRange(
            very_low_pct=1.0,
            low_pct=4.0,
            target_pct=70.0,
            high_pct=20.0,
            very_high_pct=5.0
        ),
        average_glucose=148.5,
        glucose_std=42.3,
        cv_pct=28.5,
        gmi=6.8,
        data_quality_flags=["sensor_warmup", "data_gaps"],
        completeness_pct=90.0
    )
    assert len(results.data_quality_flags) == 2