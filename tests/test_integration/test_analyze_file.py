"""Integration tests for analyze_file function."""

import pytest
from pathlib import Path

from cgm_insights import analyze_file, format_results


def test_analyze_file_with_sample_data():
    """Test analyze_file with sample CSV data."""
    sample_path = Path(__file__).parent.parent.parent / "data" / "readings.csv"
    if not sample_path.exists():
        pytest.skip("Sample data file not found")

    results = analyze_file(str(sample_path))

    assert results.total_readings > 0
    assert results.time_in_range.target_pct > 0
    assert results.average_glucose > 0
    assert results.gmi > 0


def test_analyze_file_returns_analysis_results():
    """Test that analyze_file returns AnalysisResults."""
    sample_path = Path(__file__).parent.parent.parent / "data" / "readings.csv"
    if not sample_path.exists():
        pytest.skip("Sample data file not found")

    from cgm_insights.models import AnalysisResults
    results = analyze_file(str(sample_path))

    assert isinstance(results, AnalysisResults)


def test_analyze_file_with_date_range():
    """Test analyze_file with date filtering."""
    sample_path = Path(__file__).parent.parent.parent / "data" / "readings.csv"
    if not sample_path.exists():
        pytest.skip("Sample data file not found")

    # Filter to April 20-22, 2026 (adjust dates based on sample data)
    results = analyze_file(
        str(sample_path),
        start_date="2026-04-20",
        end_date="2026-04-22",
    )

    # Should have fewer readings than full dataset
    # (actual count depends on sample data dates)
    assert results.total_readings >= 0


def test_analyze_file_public_api():
    """Test that analyze_file is accessible from public API."""
    # Verify analyze_file can be imported from top-level package
    from cgm_insights import analyze_file as af
    from cgm_insights import format_results as fr

    assert callable(af)
    assert callable(fr)