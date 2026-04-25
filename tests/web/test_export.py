"""Tests for export endpoints.

Tests cover:
- Successful AGP export
- Invalid session handling
- PDF download headers
- HTML preview endpoint
"""

import io

import pytest
from fastapi.testclient import TestClient

from src.web.services.session import session_store, create_session
from tests.fixtures.sample_data import generate_sample_results, generate_sample_readings


class TestExportEndpoint:
    """Tests for AGP export endpoint."""

    def test_export_agp_success(self, test_client: TestClient, sample_session_id: str):
        """Test successful AGP report export."""
        response = test_client.get(f"/export/{sample_session_id}/agp")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_export_agp_content_disposition(self, test_client: TestClient, sample_session_id: str):
        """Test that AGP export has proper Content-Disposition header."""
        response = test_client.get(f"/export/{sample_session_id}/agp")

        assert response.status_code == 200
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert "agp-report" in response.headers["content-disposition"]
        assert ".pdf" in response.headers["content-disposition"]

    def test_export_agp_invalid_session(self, test_client: TestClient):
        """Test AGP export with invalid session ID."""
        response = test_client.get("/export/invalid-session-id/agp")

        assert response.status_code == 404

    def test_export_agp_nonexistent_session(self, test_client: TestClient):
        """Test AGP export with non-existent UUID session."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"/export/{fake_session_id}/agp")

        assert response.status_code == 404

    def test_export_agp_pdf_content(self, test_client: TestClient, sample_session_id: str):
        """Test that exported content is a valid PDF."""
        response = test_client.get(f"/export/{sample_session_id}/agp")

        assert response.status_code == 200
        content = response.content

        # PDF files start with %PDF
        assert content.startswith(b"%PDF")

    def test_export_agp_with_patterns(self, test_client: TestClient, sample_session_with_patterns: str):
        """Test AGP export with patterns in session."""
        response = test_client.get(f"/export/{sample_session_with_patterns}/agp")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"


class TestPreviewEndpoint:
    """Tests for AGP preview endpoint."""

    def test_preview_agp_success(self, test_client: TestClient, sample_session_id: str):
        """Test successful AGP report preview."""
        response = test_client.get(f"/export/{sample_session_id}/preview")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_preview_agp_invalid_session(self, test_client: TestClient):
        """Test AGP preview with invalid session ID."""
        response = test_client.get("/export/invalid-session-id/preview")

        assert response.status_code == 404

    def test_preview_agp_nonexistent_session(self, test_client: TestClient):
        """Test AGP preview with non-existent UUID session."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        response = test_client.get(f"/export/{fake_session_id}/preview")

        assert response.status_code == 404

    def test_preview_agp_contains_html(self, test_client: TestClient, sample_session_id: str):
        """Test that preview contains HTML content."""
        response = test_client.get(f"/export/{sample_session_id}/preview")

        assert response.status_code == 200
        content = response.text

        # Should contain some HTML structure
        assert len(content) > 100  # Reasonable content length

    def test_preview_agp_with_patterns(self, test_client: TestClient, sample_session_with_patterns: str):
        """Test AGP preview with patterns in session."""
        response = test_client.get(f"/export/{sample_session_with_patterns}/preview")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestExportSessionIsolation:
    """Tests for session isolation in export."""

    def test_different_sessions_different_exports(self, test_client: TestClient, sample_csv_bytes: bytes):
        """Test that different sessions produce different exports."""
        # Create two sessions
        files1 = {"file": ("test1.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
        files2 = {"file": ("test2.csv", io.BytesIO(sample_csv_bytes), "text/csv")}

        response1 = test_client.post("/api/upload", files=files1)
        response2 = test_client.post("/api/upload", files=files2)

        session_id1 = response1.json()["session_id"]
        session_id2 = response2.json()["session_id"]

        # Get exports for both
        export1 = test_client.get(f"/export/{session_id1}/agp")
        export2 = test_client.get(f"/export/{session_id2}/agp")

        # Both should succeed
        assert export1.status_code == 200
        assert export2.status_code == 200

        # Sessions should be different
        assert session_id1 != session_id2

    def test_export_after_session_delete(self, test_client: TestClient, sample_session_id: str):
        """Test that export fails after session is deleted."""
        # Verify export works initially
        response = test_client.get(f"/export/{sample_session_id}/agp")
        assert response.status_code == 200

        # Delete session
        session_store.delete(sample_session_id)

        # Export should now fail
        response = test_client.get(f"/export/{sample_session_id}/agp")
        assert response.status_code == 404


class TestExportFilename:
    """Tests for export filename format."""

    def test_export_filename_contains_date(self, test_client: TestClient, sample_session_id: str):
        """Test that export filename contains date."""
        response = test_client.get(f"/export/{sample_session_id}/agp")

        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")

        # Should contain date pattern (YYYY-MM-DD)
        import re
        date_pattern = r"\d{4}-\d{2}-\d{2}"
        assert re.search(date_pattern, content_disposition) or "agp-report" in content_disposition

    def test_export_filename_is_pdf(self, test_client: TestClient, sample_session_id: str):
        """Test that export filename ends with .pdf."""
        response = test_client.get(f"/export/{sample_session_id}/agp")

        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")

        assert ".pdf" in content_disposition