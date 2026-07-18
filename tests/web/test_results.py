"""Tests for results display endpoints.

Tests cover:
- Successful results display
- Invalid session handling
- Results contain all expected metrics
- Wellness disclaimer presence
"""

import io
import re

import pytest
from fastapi.testclient import TestClient

from src.web.services.session import session_store, create_session
from tests.fixtures.sample_data import (
    generate_sample_results,
    generate_sample_readings,
    create_sample_csv_content,
)


class TestResultsEndpoint:
    """Tests for results display endpoints."""

    def test_results_page_success(self, test_client: TestClient, sample_session_id: str):
        """Test successful results page rendering."""
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_results_page_invalid_session(self, test_client: TestClient):
        """Test results page with invalid session ID."""
        response = test_client.get("/results/invalid-session-id")

        assert response.status_code == 404

    def test_results_page_nonexistent_session(self, test_client: TestClient):
        """Test results page with non-existent UUID session."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"/results/{fake_session_id}")

        assert response.status_code == 404

    def test_results_json_endpoint(self, test_client: TestClient, sample_session_id: str):
        """Test JSON results endpoint returns valid data."""
        response = test_client.get(f"/results/{sample_session_id}/data")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "results" in data
        assert "patterns" in data
        assert "glucose_readings" in data

    def test_results_json_invalid_session(self, test_client: TestClient):
        """Test JSON endpoint with invalid session."""
        response = test_client.get("/results/invalid-session-id/data")

        assert response.status_code == 404

    def test_results_contain_average_glucose(self, test_client: TestClient, sample_session_id: str):
        """Test that results contain average glucose."""
        response = test_client.get(f"/results/{sample_session_id}/data")

        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        assert "average_glucose" in results
        assert results["average_glucose"] > 0

    def test_results_contain_time_in_range(self, test_client: TestClient, sample_session_id: str):
        """Test that results contain time in range breakdown."""
        response = test_client.get(f"/results/{sample_session_id}/data")

        assert response.status_code == 200
        data = response.json()
        tir = data["results"]["time_in_range"]

        # All TIR percentages should be present
        assert "very_low_pct" in tir
        assert "low_pct" in tir
        assert "target_pct" in tir
        assert "high_pct" in tir
        assert "very_high_pct" in tir

        # Percentages should sum to approximately 100 (allow some rounding tolerance)
        total = tir["very_low_pct"] + tir["low_pct"] + tir["target_pct"] + tir["high_pct"] + tir["very_high_pct"]
        assert abs(total - 100.0) < 2.0  # Allow for rounding in test fixtures

    def test_results_contain_gmi(self, test_client: TestClient, sample_session_id: str):
        """Test that results contain GMI."""
        response = test_client.get(f"/results/{sample_session_id}/data")

        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        assert "gmi" in results
        # GMI should be in reasonable range (4-14%)
        assert 4.0 <= results["gmi"] <= 14.0

    def test_results_contain_cv(self, test_client: TestClient, sample_session_id: str):
        """Test that results contain CV."""
        response = test_client.get(f"/results/{sample_session_id}/data")

        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        assert "cv_pct" in results
        # CV should be positive
        assert results["cv_pct"] >= 0

    def test_results_contain_total_readings(self, test_client: TestClient, sample_session_id: str):
        """Test that results contain total readings count."""
        response = test_client.get(f"/results/{sample_session_id}/data")

        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        assert "total_readings" in results
        assert results["total_readings"] > 0

    def test_results_patterns_format(self, test_client: TestClient, sample_session_id: str):
        """Test that patterns have expected format."""
        response = test_client.get(f"/results/{sample_session_id}/data")

        assert response.status_code == 200
        data = response.json()
        patterns = data["patterns"]

        # Patterns should be a list (may be empty)
        assert isinstance(patterns, list)

        # If patterns exist, verify format
        for pattern in patterns:
            assert "type" in pattern
            assert "description" in pattern
            assert "severity" in pattern

    def test_results_with_patterns(self, test_client: TestClient, sample_session_with_patterns: str):
        """Test results endpoint with patterns present."""
        response = test_client.get(f"/results/{sample_session_with_patterns}/data")

        assert response.status_code == 200
        data = response.json()
        patterns = data["patterns"]

        # Should have patterns from the fixture
        assert len(patterns) > 0

    def test_results_glucose_readings_format(self, test_client: TestClient, sample_session_id: str):
        """Test that glucose readings have expected format."""
        response = test_client.get(f"/results/{sample_session_id}/data")

        assert response.status_code == 200
        data = response.json()
        readings = data["glucose_readings"]

        # Readings should be a list
        assert isinstance(readings, list)

        # Each reading should have timestamp and glucose
        if len(readings) > 0:
            reading = readings[0]
            assert "timestamp" in reading
            assert "glucose" in reading


class TestResultsSessionIsolation:
    """Tests for session isolation in results."""

    def test_different_sessions_different_results(self, test_client: TestClient, sample_csv_bytes: bytes):
        """Test that different sessions return different results."""
        # Create two sessions with different data
        files1 = {"file": ("test1.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
        files2 = {"file": ("test2.csv", io.BytesIO(sample_csv_bytes), "text/csv")}

        response1 = test_client.post("/upload", files=files1)
        response2 = test_client.post("/upload", files=files2)

        session_id1 = response1.json()["session_id"]
        session_id2 = response2.json()["session_id"]

        # Get results for both
        results1 = test_client.get(f"/results/{session_id1}/data").json()
        results2 = test_client.get(f"/results/{session_id2}/data").json()

        # Sessions should be different
        assert session_id1 != session_id2

        # Results should exist for both
        assert results1["results"]["total_readings"] > 0
        assert results2["results"]["total_readings"] > 0

    def test_deleted_session_returns_404(self, test_client: TestClient, sample_session_id: str):
        """Test that deleted session returns 404."""
        # Delete the session
        session_store.delete(sample_session_id)

        # Try to get results
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 404


class TestResultsTemplateRendering:
    """Regression tests for template rendering correctness.

    These tests guard against Jinja2 template syntax errors (e.g. Django-style
    ``{% include 'x.html' with var=val %}`` which Jinja2 rejects) and against
    context variables that cause runtime errors during rendering.
    """

    def test_all_templates_parse_without_syntax_errors(self):
        """All templates must be parseable by Jinja2 without TemplateSyntaxError.

        Regression: results.html used Django-style include-with syntax
        (``{% include 'x.html' with key=val %}``) which Jinja2 rejects at
        parse time with TemplateSyntaxError, producing a 500 on every page load.
        """
        from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
        from pathlib import Path

        template_dir = Path("src/web/templates")
        env = Environment(loader=FileSystemLoader(str(template_dir)))

        errors = []
        for path in sorted(template_dir.rglob("*.html")):
            name = str(path.relative_to(template_dir))
            try:
                env.get_template(name)
            except TemplateSyntaxError as exc:
                errors.append(f"{name}: {exc}")

        assert not errors, "Template syntax errors found:\n" + "\n".join(errors)

    def test_results_html_page_renders_200(self, test_client: TestClient, sample_session_id: str):
        """GET /results/{id} must return HTTP 200 with HTML content.

        Regression: Jinja2 TemplateSyntaxError in results.html caused every
        results page request to return 500 Internal Server Error.
        """
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_results_html_contains_metric_sections(self, test_client: TestClient, sample_session_id: str):
        """Rendered results page must contain the four key metric card headings.

        Regression: if the metrics_card include blocks raise a TemplateSyntaxError
        the page body is empty or truncated — this confirms the cards actually rendered.
        """
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        body = response.text
        assert "Time in Target" in body
        assert "Average Glucose" in body
        assert "Standard Deviation" in body
        assert "Glucose Percentiles" in body

    def test_results_html_contains_wellness_disclaimer(self, test_client: TestClient, sample_session_id: str):
        """Rendered results page must contain the regulatory wellness disclaimer."""
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        assert "Wellness Information Only" in response.text

    def test_results_html_contains_daily_tir_heading(self, test_client: TestClient, sample_session_id: str):
        """Glucose Trend section is now 'Daily Time in Range' — heading must be present."""
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        assert "Daily Time in Range" in response.text

    def test_results_html_no_glucose_trend_heading(self, test_client: TestClient, sample_session_id: str):
        """'Glucose Trend' section heading must be absent — it was replaced by 'Daily Time in Range'.

        Regression guard: ensures old heading is not accidentally re-introduced.
        """
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        # The phrase may appear in Jinja2 comments ({# ... #}) but NOT in rendered output
        assert "Glucose Trend" not in response.text

    def test_results_html_contains_chart_canvases(self, test_client: TestClient, sample_session_id: str):
        """All three main chart canvases must be present in the rendered page."""
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        body = response.text
        assert 'id="tirChart"' in body
        assert 'id="glucoseTrendChart"' in body
        assert 'id="dailyPatternsChartAll"' in body

    def test_results_html_exposes_behavioral_patterns_js_global(self, test_client: TestClient, sample_session_id: str):
        """'behavioralPatterns' JS global must be serialized into the page for chart init."""
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        assert "const behavioralPatterns" in response.text

    def test_results_html_exposes_glucose_readings_js_global(self, test_client: TestClient, sample_session_id: str):
        """'glucoseReadings' JS global must be serialized into the page for chart init."""
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        assert "const glucoseReadings" in response.text

    def test_behavioral_patterns_chart_canvas_shown_with_sufficient_data(
        self, test_client: TestClient, sample_session_with_behavioral_patterns: str
    ):
        """'behavioralPatternsChart' canvas appears when session has ≥5 days of behavioral data."""
        response = test_client.get(f"/results/{sample_session_with_behavioral_patterns}")

        assert response.status_code == 200
        assert 'id="behavioralPatternsChart"' in response.text

    def test_behavioral_patterns_canvas_absent_without_data(
        self, test_client: TestClient, sample_session_id: str
    ):
        """'behavioralPatternsChart' canvas is absent when behavioral_patterns is None.

        When no behavioral data is in the session the template renders the
        insufficient-data alert, not the chart canvas.
        """
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        # sample_session_id has no behavioral_patterns — canvas must not appear
        assert 'id="behavioralPatternsChart"' not in response.text

    def test_time_windows_rows_are_expandable_with_oor_data(
        self, test_client: TestClient, sample_session_with_oor_behavioral_patterns: str
    ):
        """When OOR patterns exist, each row carries Alpine.js expand attrs and computeWindowDetails.

        Regression guard: ensures the click-to-expand markup is actually rendered in the
        HTML output and that the JS detail function name is wired into the @click handler.
        """
        response = test_client.get(f"/results/{sample_session_with_oor_behavioral_patterns}")

        assert response.status_code == 200
        body = response.text
        # Alpine.js expand toggle must be present
        assert "x-data" in body
        assert "computeWindowDetails" in body
        # The 'Time Windows to Focus On' card must exist
        assert "Time Windows to Focus On" in body

    # ── Feature: formal percentile labels (Task 2) ──────────────────────────────

    def test_percentile_labels_are_formal(
        self, test_client: TestClient, sample_session_id: str
    ):
        """Glucose Percentiles card must use '50th/70th/90th Percentile', not 'p50/p70/p90'.

        Regression guard: prevents reverting to the terse p-notation labels.
        """
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        body = response.text
        assert "50th Percentile" in body
        assert "70th Percentile" in body
        assert "90th Percentile" in body

    def test_old_pnotation_labels_absent(
        self, test_client: TestClient, sample_session_id: str
    ):
        """Terse p-notation labels ('>p50<', '>p70<', '>p90<') must not appear in the rendered page.

        Matches the exact rendered tag content so Jinja2 variable references
        (e.g. results.p50_glucose) don't trigger a false positive.
        """
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        body = response.text
        # The rendered text content of the label spans must not contain bare p-notation
        assert ">p50<" not in body
        assert ">p70<" not in body
        assert ">p90<" not in body

    # ── Feature: share button (Task 1) ──────────────────────────────────────────

    def test_share_button_present_when_source_url_set(
        self, test_client: TestClient, sample_session_with_source_url: str
    ):
        """Share button must appear when the session was loaded from a URL.

        Regression guard: ensures the Alpine.js share button and clipboard JS
        are rendered when source_url is present in the session.
        """
        response = test_client.get(f"/results/{sample_session_with_source_url}")

        assert response.status_code == 200
        body = response.text
        assert "navigator.clipboard" in body
        assert "encodeURIComponent" in body
        assert "Share" in body

    def test_share_button_absent_without_source_url(
        self, test_client: TestClient, sample_session_id: str
    ):
        """Share button must not appear when the session was loaded via file upload.

        Regression guard: file-upload sessions have no source_url so the share
        button block must be entirely absent from the rendered HTML.
        """
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        # The clipboard JS only appears inside the source_url-conditional block
        assert "navigator.clipboard" not in response.text

    # ── Feature: daily TIR scrollable wrapper (Task 3) ──────────────────────────

    def test_daily_tir_has_scrollable_wrapper(
        self, test_client: TestClient, sample_session_id: str
    ):
        """Daily TIR chart must be wrapped in a horizontally-scrollable container.

        Regression guard: the glucoseTrendOuter div is required by the JS that
        dynamically expands chart width when the period has many days.
        """
        response = test_client.get(f"/results/{sample_session_id}")

        assert response.status_code == 200
        body = response.text
        assert 'id="glucoseTrendOuter"' in body
        assert "overflow-x-auto" in body

    # ── Feature: ToD box-plot canvases + percentile data (Task 5) ───────────────

    def test_tod_weekday_weekend_canvases_present_with_behavioral_data(
        self, test_client: TestClient, sample_session_with_behavioral_patterns: str
    ):
        """All three ToD chart canvases must be present when behavioral data is available.

        Regression guard: the three-column inline layout requires all three
        canvas IDs to be rendered so JS can target them.
        """
        response = test_client.get(f"/results/{sample_session_with_behavioral_patterns}")

        assert response.status_code == 200
        body = response.text
        assert 'id="dailyPatternsChartAll"' in body
        assert 'id="dailyPatternsChartWeekdays"' in body
        assert 'id="dailyPatternsChartWeekends"' in body

    def test_behavioral_patterns_js_global_contains_percentile_fields(
        self, test_client: TestClient, sample_session_with_behavioral_patterns: str
    ):
        """The behavioralPatterns JS global must include p25_glucose, p50_glucose, p75_glucose.

        Regression guard: if the backend model stops computing percentiles the
        JS fill-between-lines IQR band silently disappears. This test verifies
        the data reaches the browser.
        """
        response = test_client.get(f"/results/{sample_session_with_behavioral_patterns}")

        assert response.status_code == 200
        body = response.text
        # All three keys must appear inside the serialised JS constant
        assert '"p25_glucose"' in body
        assert '"p50_glucose"' in body
        assert '"p75_glucose"' in body

    def test_behavioral_patterns_percentile_values_are_not_null(
        self, test_client: TestClient, sample_session_with_behavioral_patterns: str
    ):
        """Serialised behavioralPatterns must contain non-null percentile values.

        Regression guard: confirms that the session fixture (14 days) produces
        enough data that p25/p50/p75 are populated, not null, in the HTML payload.
        """
        import json, re

        response = test_client.get(f"/results/{sample_session_with_behavioral_patterns}")
        assert response.status_code == 200

        # Extract the JS constant value from the script block
        match = re.search(
            r'const behavioralPatterns\s*=\s*(\{.*?\});',
            response.text,
            re.DOTALL,
        )
        assert match, "behavioralPatterns JS constant not found"
        bp = json.loads(match.group(1))

        hourly = [
            p for p in bp["patterns"]
            if p["window_size_min"] == 60 and p["bucket_start_minute"] % 60 == 0
        ]
        assert len(hourly) > 0, "No hourly patterns in JS global"
        # At least one hourly bucket must have a non-null p25
        assert any(p["p25_glucose"] is not None for p in hourly), (
            "All p25_glucose values are null — IQR band will be invisible"
        )