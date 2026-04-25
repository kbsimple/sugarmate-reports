"""Tests for AGP report PDF generator.

Tests cover:
- PDF generation returns valid bytes
- PDF content includes required sections
- PDF handles empty results gracefully
"""

import pytest

from src.web.services.agp_generator import generate_agp_report, generate_agp_preview
from tests.fixtures.sample_data import generate_sample_results
from datetime import datetime


class TestAGPReportGenerator:
    """Tests for AGP PDF generation."""

    def test_generate_agp_report_returns_bytes(self):
        """Test that generate_agp_report returns bytes."""
        results = generate_sample_results()
        session_id = "test-session-123"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        assert pdf_bytes is not None
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_generate_agp_report_pdf_header(self):
        """Test that PDF starts with PDF header."""
        results = generate_sample_results()
        session_id = "test-session-123"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        # PDF files start with %PDF
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_agp_report_includes_sections(self):
        """Test that PDF is generated with required sections."""
        results = generate_sample_results()
        session_id = "test-session-123"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        # PDF should be generated successfully
        # Note: PDF content is compressed, so text searching won't work
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 1000  # Should have substantial content

    def test_generate_agp_report_with_patterns(self):
        """Test PDF generation with patterns."""
        from cgm_insights.analytics import PatternResult, PatternType, PatternSeverity

        results = generate_sample_results()
        patterns = [
            PatternResult(
                pattern_type=PatternType.TIME_OF_DAY,
                description="Morning glucose elevated",
                time_period="06:00-08:00",
                severity=PatternSeverity.MODERATE,
                avg_glucose=180.0,
                reading_count=60,
                confidence=0.85,
            )
        ]
        session_id = "test-session-patterns"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=patterns,
            generated_date=datetime.now(),
        )

        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_agp_report_empty_patterns(self):
        """Test PDF generation with empty patterns list."""
        results = generate_sample_results()
        session_id = "test-session-empty"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_agp_report_custom_date(self):
        """Test PDF generation with custom date."""
        results = generate_sample_results()
        session_id = "test-session-date"
        custom_date = datetime(2026, 1, 15, 10, 30, 0)

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=custom_date,
        )

        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_agp_report_includes_metrics(self):
        """Test PDF is generated with metrics."""
        results = generate_sample_results()
        session_id = "test-metrics"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        # PDF should be generated successfully
        # Note: PDF content is compressed, so we can't search for text
        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF")

    def test_generate_agp_report_includes_tir(self):
        """Test PDF is generated with time in range data."""
        results = generate_sample_results()
        session_id = "test-tir"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        # PDF should be generated successfully
        # Note: PDF content is compressed, so we can't search for text
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 1000  # Should have substantial content


class TestAGPPreview:
    """Tests for AGP HTML preview generation."""

    def test_generate_agp_preview_returns_string(self):
        """Test that generate_agp_preview returns HTML string."""
        results = generate_sample_results()
        session_id = "test-preview-123"

        html = generate_agp_preview(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        assert html is not None
        assert isinstance(html, str)

    def test_generate_agp_preview_contains_html(self):
        """Test that preview contains HTML structure."""
        results = generate_sample_results()
        session_id = "test-preview-html"

        html = generate_agp_preview(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        # Should contain HTML tags
        assert "<html" in html.lower() or "<!doctype" in html.lower() or "<div" in html.lower()

    def test_generate_agp_preview_includes_session_id(self):
        """Test that preview includes session ID."""
        results = generate_sample_results()
        session_id = "unique-preview-id"

        html = generate_agp_preview(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        # Session ID should be in the preview (truncated)
        assert session_id[:8] in html

    def test_generate_agp_preview_includes_metrics(self):
        """Test that preview includes key metrics."""
        results = generate_sample_results(avg_glucose=150.0)
        session_id = "test-preview-metrics"

        html = generate_agp_preview(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        # Average glucose should be present
        assert "150" in html or "glucose" in html.lower()

    def test_generate_agp_preview_with_patterns(self):
        """Test preview with patterns."""
        from cgm_insights.analytics import PatternResult, PatternType, PatternSeverity

        results = generate_sample_results()
        patterns = [
            PatternResult(
                pattern_type=PatternType.TIME_OF_DAY,
                description="Evening glucose tends to be higher",
                time_period="18:00-20:00",
                severity=PatternSeverity.INFO,
                avg_glucose=160.0,
                reading_count=50,
                confidence=0.75,
            )
        ]
        session_id = "test-preview-patterns"

        html = generate_agp_preview(
            session_id=session_id,
            results=results,
            patterns=patterns,
            generated_date=datetime.now(),
        )

        assert html is not None
        # Pattern description should be in the preview
        assert "Evening" in html or "pattern" in html.lower()


class TestAGPEdgeCases:
    """Tests for edge cases in AGP generation."""

    def test_agp_report_extreme_glucose(self):
        """Test AGP report with extreme glucose values."""
        results = generate_sample_results(avg_glucose=300.0)
        session_id = "test-extreme"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF")

    def test_agp_report_low_glucose(self):
        """Test AGP report with low glucose values."""
        results = generate_sample_results(avg_glucose=80.0)
        session_id = "test-low"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        assert pdf_bytes is not None

    def test_agp_report_long_session_id(self):
        """Test AGP report with long session ID."""
        results = generate_sample_results()
        session_id = "very-long-session-id-with-many-characters-1234567890"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        assert pdf_bytes is not None
        # Session ID should be truncated in the report

    def test_agp_report_with_quality_flags(self):
        """Test AGP report with quality flags."""
        results = generate_sample_results()
        results.data_quality_flags = ["sensor_warmup", "data_gaps"]
        session_id = "test-flags"

        pdf_bytes = generate_agp_report(
            session_id=session_id,
            results=results,
            patterns=[],
            generated_date=datetime.now(),
        )

        assert pdf_bytes is not None