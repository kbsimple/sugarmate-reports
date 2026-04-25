"""Tests for visualization module."""

from datetime import datetime
from io import StringIO

import pytest
from rich.console import Console

from cgm_insights.models import CGMReading, AnalysisResults, TimeInRange
from cgm_insights.output.visualization import (
    classify_glucose_zone,
    render_trend_graph,
    render_daily_table,
    render_comparison,
    calculate_delta,
)


def create_test_reading(glucose: float, day: int = 1) -> CGMReading:
    """Create a test CGM reading."""
    return CGMReading(
        timestamp=datetime(2024, 1, day, 12, 0),
        glucose_mg_dl=glucose,
        source="test",
    )


def create_test_results(
    avg_glucose: float = 148.5,
    tir: float = 70.0,
    cv: float = 28.5,
    gmi: float = 6.8,
) -> AnalysisResults:
    """Create test analysis results."""
    return AnalysisResults(
        date_range_start=datetime(2024, 4, 1),
        date_range_end=datetime(2024, 4, 14),
        total_readings=4032,
        time_in_range=TimeInRange(
            very_low_pct=1.0,
            low_pct=4.0,
            target_pct=tir,
            high_pct=20.0,
            very_high_pct=5.0,
        ),
        average_glucose=avg_glucose,
        glucose_std=42.3,
        cv_pct=cv,
        gmi=gmi,
        data_quality_flags=[],
        completeness_pct=95.0,
    )


class TestClassifyGlucoseZone:
    """Tests for classify_glucose_zone function."""

    def test_very_low_zone(self):
        """Test values below 54 are classified as very_low."""
        assert classify_glucose_zone(40) == "very_low"
        assert classify_glucose_zone(53) == "very_low"
        assert classify_glucose_zone(45) == "very_low"

    def test_low_zone(self):
        """Test values 54-69 are classified as low."""
        assert classify_glucose_zone(54) == "low"
        assert classify_glucose_zone(60) == "low"
        assert classify_glucose_zone(69) == "low"

    def test_target_zone(self):
        """Test values 70-180 are classified as target."""
        assert classify_glucose_zone(70) == "target"
        assert classify_glucose_zone(100) == "target"
        assert classify_glucose_zone(150) == "target"
        assert classify_glucose_zone(180) == "target"

    def test_high_zone(self):
        """Test values 181-250 are classified as high."""
        assert classify_glucose_zone(181) == "high"
        assert classify_glucose_zone(200) == "high"
        assert classify_glucose_zone(250) == "high"

    def test_very_high_zone(self):
        """Test values above 250 are classified as very_high."""
        assert classify_glucose_zone(251) == "very_high"
        assert classify_glucose_zone(300) == "very_high"
        assert classify_glucose_zone(400) == "very_high"


class TestRenderTrendGraph:
    """Tests for render_trend_graph function."""

    def test_renders_with_sample_readings(self):
        """Test that render_trend_graph works with sample readings."""
        readings = [
            create_test_reading(100 + i * 5, day=i)
            for i in range(1, 15)
        ]
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        # Should not raise an exception
        render_trend_graph(readings, console)

        # Output should contain expected elements
        result = output.getvalue()
        assert "Glucose Trend" in result or "glucose" in result.lower()

    def test_handles_empty_readings(self):
        """Test that empty readings are handled gracefully."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        # Should not raise an exception
        render_trend_graph([], console)

        result = output.getvalue()
        assert "No readings" in result

    def test_handles_single_reading(self):
        """Test that single reading is handled gracefully."""
        readings = [create_test_reading(120, day=1)]
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        # Should not raise an exception
        render_trend_graph(readings, console)

        result = output.getvalue()
        assert "Single reading" in result
        assert "120" in result


class TestRenderDailyTable:
    """Tests for render_daily_table function."""

    def test_table_contains_metrics(self):
        """Test that daily table contains all required metrics."""
        results = create_test_results()
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        render_daily_table(results, console)

        result = output.getvalue()
        # Check for key metrics in output
        assert "Average" in result
        assert "CV" in result
        assert "GMI" in result
        assert "Time in Target" in result or "Target" in result

    def test_table_handles_good_values(self):
        """Test that good values are styled appropriately."""
        # Create results with good glucose control
        good_results = create_test_results(
            avg_glucose=120,  # In target range
            tir=85.0,  # >70%
            cv=30.0,  # <36%
            gmi=6.0,  # <7%
        )
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        # Should not raise an exception
        render_daily_table(good_results, console)

        result = output.getvalue()
        assert "120" in result

    def test_table_shows_date_range(self):
        """Test that table shows date range."""
        results = create_test_results()
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        render_daily_table(results, console)

        result = output.getvalue()
        # Date range should appear (strip ANSI codes for comparison)
        # The date format is YYYY-MM-DD, checking for year and month
        assert "2024" in result
        assert "04" in result
        assert "01" in result


class TestRenderComparison:
    """Tests for render_comparison function."""

    def test_comparison_shows_both_periods(self):
        """Test that comparison shows current and previous periods."""
        current = create_test_results(avg_glucose=140, tir=75.0)
        previous = create_test_results(avg_glucose=160, tir=65.0)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        render_comparison(current, previous, console)

        result = output.getvalue()
        assert "Current" in result
        assert "Previous" in result
        assert "140" in result  # Current average
        assert "160" in result  # Previous average

    def test_comparison_calculates_delta(self):
        """Test that comparison calculates delta correctly."""
        current = create_test_results(avg_glucose=140, tir=75.0)
        previous = create_test_results(avg_glucose=160, tir=65.0)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        render_comparison(current, previous, console)

        result = output.getvalue()
        # Delta should appear (improvement for TIR, lower avg)
        assert "Change" in result

    def test_comparison_shows_improvement_indicators(self):
        """Test that improvement indicators appear."""
        # Current is better than previous
        current = create_test_results(avg_glucose=130, tir=80.0)
        previous = create_test_results(avg_glucose=160, tir=60.0)
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        render_comparison(current, previous, console)

        result = output.getvalue()
        # Should contain change indicators
        assert "Change" in result


class TestCalculateDelta:
    """Tests for calculate_delta helper function."""

    def test_calculates_positive_delta(self):
        """Test positive delta calculation."""
        delta, direction = calculate_delta(110.0, 100.0)
        assert delta == pytest.approx(10.0, abs=0.1)
        assert direction == "↑"  # Increase

    def test_calculates_negative_delta(self):
        """Test negative delta calculation."""
        delta, direction = calculate_delta(90.0, 100.0)
        assert delta == pytest.approx(-10.0, abs=0.1)
        assert direction == "↓"  # Decrease

    def test_handles_zero_previous(self):
        """Test handling of zero previous value."""
        delta, direction = calculate_delta(100.0, 0.0)
        assert delta == 0.0
        assert direction == ""

    def test_lower_is_better_direction(self):
        """Test direction when lower is better."""
        # Lower glucose is better
        delta, direction = calculate_delta(90.0, 100.0, lower_is_better=True)
        assert delta == pytest.approx(-10.0, abs=0.1)
        assert direction == "↓"  # Improvement (going down)

        # Higher glucose is worse
        delta, direction = calculate_delta(110.0, 100.0, lower_is_better=True)
        assert delta == pytest.approx(10.0, abs=0.1)
        assert direction == "↑"  # Worsening (going up)

    def test_small_change_uses_neutral_indicator(self):
        """Test that small changes use neutral indicator."""
        delta, direction = calculate_delta(100.05, 100.0)
        assert abs(delta) < 0.1
        assert direction == "↔"  # No significant change