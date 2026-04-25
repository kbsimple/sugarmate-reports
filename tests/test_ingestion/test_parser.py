"""Tests for parser interface and Sugarmate parser."""

import pytest
from datetime import datetime
from pathlib import Path
from cgm_insights.ingestion import Parser, SugarmateParser, get_parser, PARSERS


def test_parser_interface_exists():
    """Test Parser abstract base class has required methods."""
    assert hasattr(Parser, "can_parse")
    assert hasattr(Parser, "parse")


def test_sugarmate_can_parse_csv():
    """Test SugarmateParser identifies CSV files."""
    assert SugarmateParser.can_parse("data.csv")
    assert SugarmateParser.can_parse("readings.csv")
    assert not SugarmateParser.can_parse("data.xlsx")


def test_sugarmate_parse_sample_data():
    """Test parsing sample CSV file."""
    sample_path = Path(__file__).parent.parent.parent / "data" / "readings.csv"
    if not sample_path.exists():
        pytest.skip("Sample data file not found")

    parser = SugarmateParser()
    readings = parser.parse(str(sample_path))

    assert len(readings) > 0
    assert all(r.source == "sugarmate" for r in readings)


def test_sugarmate_parse_extracts_glucose():
    """Test glucose values are extracted correctly."""
    sample_path = Path(__file__).parent.parent.parent / "data" / "readings.csv"
    if not sample_path.exists():
        pytest.skip("Sample data file not found")

    parser = SugarmateParser()
    readings = parser.parse(str(sample_path))

    # Check first few readings have valid glucose values
    for reading in readings[:5]:
        assert 40 <= reading.glucose_mg_dl <= 400


def test_sugarmate_parse_date_filter():
    """Test date range filtering."""
    sample_path = Path(__file__).parent.parent.parent / "data" / "readings.csv"
    if not sample_path.exists():
        pytest.skip("Sample data file not found")

    parser = SugarmateParser()
    start = datetime(2026, 4, 20)
    end = datetime(2026, 4, 22)

    readings = parser.parse(str(sample_path), start_date=start, end_date=end)

    # All readings should be within date range
    for reading in readings:
        assert reading.timestamp >= start
        assert reading.timestamp <= end


def test_get_parser_returns_sugarmate_for_csv():
    """Test get_parser returns SugarmateParser for CSV files."""
    parser = get_parser("test.csv")
    assert isinstance(parser, SugarmateParser)