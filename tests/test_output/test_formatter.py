"""Tests for output formatter."""

from datetime import datetime

from cgm_insights.models import AnalysisResults, TimeInRange
from cgm_insights.output import format_results, format_quality_flags, format_summary


def create_test_results() -> AnalysisResults:
    """Create test analysis results."""
    return AnalysisResults(
        date_range_start=datetime(2026, 4, 1),
        date_range_end=datetime(2026, 4, 14),
        total_readings=4032,
        time_in_range=TimeInRange(
            very_low_pct=1.0,
            low_pct=4.0,
            target_pct=70.0,
            high_pct=20.0,
            very_high_pct=5.0,
        ),
        average_glucose=148.5,
        glucose_std=42.3,
        cv_pct=28.5,
        gmi=6.8,
        data_quality_flags=["sensor_warmup"],
        completeness_pct=95.0,
    )


def test_format_results_contains_all_metrics():
    """Test that format_results includes all required metrics."""
    results = create_test_results()
    formatted = format_results(results)

    assert "glucose_metrics" in formatted
    assert "average_mg_dl" in formatted["glucose_metrics"]
    assert "cv_pct" in formatted["glucose_metrics"]
    assert "gmi" in formatted["glucose_metrics"]

    assert "time_in_range" in formatted
    assert "target_pct" in formatted["time_in_range"]
    assert "very_low_pct" in formatted["time_in_range"]


def test_format_results_includes_gmi_caveat():
    """Test that GMI caveat is included."""
    results = create_test_results()
    formatted = format_results(results, include_caveats=True)

    assert "caveats" in formatted
    assert "gmi" in formatted["caveats"]
    assert "informational" in formatted["caveats"]["gmi"].lower()


def test_format_quality_flags_human_readable():
    """Test that quality flags are formatted human-readable."""
    flags = ["sensor_warmup", "data_gaps", "low_completeness"]
    formatted = format_quality_flags(flags)

    assert len(formatted) == 3
    assert all("message" in f for f in formatted)
    assert all("severity" in f for f in formatted)


def test_format_summary_text():
    """Test that format_summary produces readable text."""
    results = create_test_results()
    summary = format_summary(results)

    assert "Analysis Period" in summary
    assert "Time in Range" in summary
    assert "Glucose Metrics" in summary
    assert "148" in summary  # Average glucose


def test_format_results_with_quality_flags():
    """Test that quality flags are included in formatted results."""
    results = create_test_results()
    formatted = format_results(results)

    assert "quality" in formatted
    assert "flags" in formatted["quality"]
    assert "sensor_warmup" in formatted["quality"]["flags"]


def test_format_results_date_range():
    """Test that date range is properly formatted."""
    results = create_test_results()
    formatted = format_results(results)

    assert "date_range" in formatted
    assert "start" in formatted["date_range"]
    assert "end" in formatted["date_range"]


def test_format_results_readings_count():
    """Test that readings count is included."""
    results = create_test_results()
    formatted = format_results(results)

    assert "readings" in formatted
    assert "total" in formatted["readings"]
    assert formatted["readings"]["total"] == 4032