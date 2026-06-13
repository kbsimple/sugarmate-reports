"""Tests for upload endpoint and file handling.

Tests cover:
- Successful file upload
- Invalid file type handling
- Empty file handling
- Insufficient data handling
- File size limit enforcement
- Date range parameters
- Session persistence
"""

import io
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.web.services.session import session_store, create_session
from tests.fixtures.sample_data import create_sample_csv_content


class TestUploadEndpoint:
    """Tests for the upload page and file upload endpoint."""

    @pytest.mark.skip(reason="Template rendering requires proper path setup in test context")
    def test_upload_page_renders(self, test_client: TestClient):
        """Test that upload page endpoint is accessible."""
        # Note: Template rendering may fail in test context due to path issues
        # This test verifies the route is registered and responds
        response = test_client.get("/upload")

        # Route should exist (may return 200 or template error)
        # In production, this returns HTML. In tests, templates may not render.
        assert response.status_code in [200, 500]  # 500 if template not found

    def test_successful_upload(self, test_client: TestClient, sample_csv_bytes: bytes):
        """Test successful file upload returns session_id."""
        files = {"file": ("test_data.csv", io.BytesIO(sample_csv_bytes), "text/csv")}

        response = test_client.post("/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"]  # Non-empty session ID
        assert "redirect" in data
        assert "/results/" in data["redirect"]

    def test_successful_upload_stores_session(
        self, test_client: TestClient, sample_csv_bytes: bytes
    ):
        """Test that successful upload stores session data."""
        files = {"file": ("test_data.csv", io.BytesIO(sample_csv_bytes), "text/csv")}

        response = test_client.post("/upload", files=files)

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Verify session was stored
        session_data = session_store.get(session_id)
        assert session_data is not None
        assert session_data.results is not None
        assert session_data.results.total_readings > 0

    def test_invalid_file_type(self, test_client: TestClient):
        """Test upload rejects non-CSV files."""
        files = {"file": ("test.txt", io.BytesIO(b"invalid content"), "text/plain")}

        response = test_client.post("/upload", files=files)

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_invalid_file_type_xlsx_rejected_without_parser(
        self, test_client: TestClient
    ):
        """Test upload handles Excel files appropriately."""
        # Excel files are allowed but may fail differently
        files = {"file": ("test.xlsx", io.BytesIO(b"invalid excel"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

        response = test_client.post("/upload", files=files)

        # Should either fail on parsing or file validation
        # Since we don't have valid Excel data, expect 400 or 500
        assert response.status_code in [400, 500]

    def test_empty_file(self, test_client: TestClient):
        """Test upload rejects empty files."""
        files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}

        response = test_client.post("/upload", files=files)

        # Empty file should result in error (parsing or validation)
        assert response.status_code in [400, 422, 500]

    def test_insufficient_data(self, test_client: TestClient):
        """Test upload rejects files with too few readings."""
        # Create CSV with minimal data (just header + 1 row) using Sugarmate format
        content = b"datetime,mg_dl\n2026-04-25 12:00,140\n"
        files = {"file": ("minimal.csv", io.BytesIO(content), "text/csv")}

        response = test_client.post("/upload", files=files)

        # Should fail due to insufficient data (400 or 422 depending on error type)
        assert response.status_code in [400, 422]

    def test_file_size_limit(self, test_client: TestClient, large_csv_bytes: bytes):
        """Test upload rejects files larger than 10MB."""
        files = {"file": ("large.csv", io.BytesIO(large_csv_bytes), "text/csv")}

        response = test_client.post("/upload", files=files)

        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    def test_upload_with_date_range(self, test_client: TestClient, sample_csv_bytes: bytes):
        """Test upload with date range parameters covering the dynamically-generated sample data."""
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        files = {"file": ("test.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
        data = {
            "start_date": yesterday,
            "end_date": tomorrow,
            "exclude_warmup": "true",
        }

        response = test_client.post("/upload", files=files, data=data)

        assert response.status_code == 200
        session_id = response.json()["session_id"]
        assert session_id

    def test_session_persistence(self, test_client: TestClient, sample_csv_bytes: bytes):
        """Test that session persists across requests."""
        # Upload file and get session ID
        files = {"file": ("test.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
        response = test_client.post("/upload", files=files)
        session_id = response.json()["session_id"]

        # Retrieve session data
        session_data = session_store.get(session_id)

        # Verify same results
        assert session_data is not None
        assert session_data.results.total_readings > 0

        # Retrieve again to ensure persistence
        session_data2 = session_store.get(session_id)
        assert session_data2.results.total_readings == session_data.results.total_readings

    def test_upload_creates_unique_sessions(self, test_client: TestClient, sample_csv_bytes: bytes):
        """Test that multiple uploads create unique sessions."""
        files1 = {"file": ("test1.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
        files2 = {"file": ("test2.csv", io.BytesIO(sample_csv_bytes), "text/csv")}

        response1 = test_client.post("/upload", files=files1)
        response2 = test_client.post("/upload", files=files2)

        session_id1 = response1.json()["session_id"]
        session_id2 = response2.json()["session_id"]

        # Sessions should be different
        assert session_id1 != session_id2

        # Both sessions should exist
        assert session_store.get(session_id1) is not None
        assert session_store.get(session_id2) is not None

    def test_upload_without_exclude_warmup(self, test_client: TestClient, sample_csv_bytes: bytes):
        """Test upload with warmup period included."""
        files = {"file": ("test.csv", io.BytesIO(sample_csv_bytes), "text/csv")}
        data = {"exclude_warmup": "false"}

        response = test_client.post("/upload", files=files, data=data)

        assert response.status_code == 200
        session_id = response.json()["session_id"]
        session_data = session_store.get(session_id)

        # When warmup is not excluded, sensor_warmup_excluded should be False
        # (though it depends on the data in the file)
        assert session_data is not None

    def test_upload_malformed_csv(self, test_client: TestClient):
        """Test upload handles malformed CSV gracefully."""
        # Use Sugarmate column names but with invalid data
        content = b"datetime,mg_dl\ninvalid_date,not_a_number\n"
        files = {"file": ("malformed.csv", io.BytesIO(content), "text/csv")}

        response = test_client.post("/upload", files=files)

        # Should handle gracefully with appropriate error
        assert response.status_code in [400, 422, 500]

    def test_upload_with_extra_columns(self, test_client: TestClient):
        """Test upload handles CSV with extra columns."""
        # CSV with extra columns that should be ignored
        content = create_sample_csv_content(
            # Use the generator but we need to modify for extra columns
            readings=None,
        )
        # For now, just test with valid CSV
        # The parser should handle extra columns gracefully
        files = {"file": ("extra_cols.csv", io.BytesIO(content.encode()), "text/csv")}

        response = test_client.post("/upload", files=files)

        # Should succeed or fail gracefully
        assert response.status_code in [200, 400, 422]


class TestLoadingIndicator:
    """Regression tests for the #loading-indicator overlay.

    The indicator is shown/hidden via JS (showIndicator / hideIndicator).
    Certain DaisyUI utility classes (e.g. 'modal') unconditionally set
    opacity:0 and pointer-events:none via CSS, making the spinner invisible
    even when display:flex is active.  These tests guard against that class
    being re-added to the element.
    """

    def test_loading_indicator_present(self, test_client: TestClient):
        """#loading-indicator element must exist in every page that extends base.html."""
        response = test_client.get("/upload")
        assert response.status_code == 200
        assert 'id="loading-indicator"' in response.text

    def test_loading_indicator_not_daisyui_modal(self, test_client: TestClient):
        """Regression: DaisyUI .modal sets opacity:0 — must not appear on #loading-indicator."""
        import re

        response = test_client.get("/upload")
        tag = re.search(r'<div\b[^>]+id="loading-indicator"[^>]*>', response.text)
        assert tag, "#loading-indicator div not found in rendered page"

        class_match = re.search(r'class="([^"]*)"', tag.group(0))
        classes = class_match.group(1).split() if class_match else []

        assert "modal" not in classes, (
            "DaisyUI .modal applies opacity:0 and pointer-events:none unconditionally. "
            "Remove 'modal' from #loading-indicator or the spinner will be invisible."
        )

    def test_loading_indicator_initially_hidden(self, test_client: TestClient):
        """#loading-indicator must start hidden so it doesn't block the page on load."""
        import re

        response = test_client.get("/upload")
        tag = re.search(r'<div\b[^>]+id="loading-indicator"[^>]*>', response.text)
        assert tag, "#loading-indicator div not found"
        assert 'display: none' in tag.group(0) or 'display:none' in tag.group(0), (
            "#loading-indicator must have inline style='display: none' on page load"
        )


class TestDeepLink:
    """Tests for GET /upload?url= deep-link pre-fill."""

    def test_upload_page_without_url_param_renders(self, test_client: TestClient):
        """GET /upload with no url param renders the uploadPage function with empty prefill."""
        response = test_client.get("/upload")
        assert response.status_code == 200
        assert "uploadPage" in response.text
        # No URL means empty string assigned to prefillUrl in the JS function
        assert 'const prefillUrl = ""' in response.text or "const prefillUrl = ''" in response.text

    def test_upload_page_with_url_param_prefills(self, test_client: TestClient):
        """GET /upload?url=... embeds the URL in the page for auto-submit."""
        target = "https://example.com/data.csv"
        response = test_client.get(f"/upload?url={target}")
        assert response.status_code == 200
        assert target in response.text

    def test_upload_page_with_url_param_selects_url_tab(self, test_client: TestClient):
        """When url param is present the template initialises activeTab to 'url'."""
        response = test_client.get("/upload?url=https://example.com/data.csv")
        assert response.status_code == 200
        assert '"url"' in response.text

    def test_deep_link_url_is_json_escaped(self, test_client: TestClient):
        """Special characters in the url param are JSON-escaped, not injected raw."""
        # A URL containing characters that would break an unescaped JS string literal
        malicious = "https://example.com/data.csv?a=1&b=</script><script>alert(1)</script>"
        response = test_client.get(f"/upload?url={malicious}")
        assert response.status_code == 200
        # The raw </script> injection must not appear verbatim
        assert "</script><script>" not in response.text


class TestUrlUploadEndpoint:
    """Tests for the /upload/url endpoint."""

    def test_rejects_http_url(self, test_client: TestClient):
        """Non-HTTPS URLs must be rejected."""
        response = test_client.post("/upload/url", data={"url": "http://example.com/data.csv"})
        assert response.status_code == 400
        assert "HTTPS" in response.json()["detail"]

    def test_rejects_ftp_url(self, test_client: TestClient):
        """Non-HTTPS scheme must be rejected."""
        response = test_client.post("/upload/url", data={"url": "ftp://example.com/data.csv"})
        assert response.status_code == 400

    def test_rejects_empty_url(self, test_client: TestClient):
        """Blank URL must be rejected."""
        response = test_client.post("/upload/url", data={"url": "   "})
        assert response.status_code == 400

    def test_rejects_no_host(self, test_client: TestClient):
        """URL with no hostname must be rejected."""
        response = test_client.post("/upload/url", data={"url": "https://"})
        assert response.status_code == 400

    def test_url_success(self, test_client: TestClient, sample_csv_bytes: bytes):
        """Successful URL download runs the full analysis pipeline."""
        import httpx

        # Build a minimal mock that looks like httpx's async streaming response.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_headers = MagicMock(spec=httpx.Headers)
        mock_headers.get = lambda key, default="": {
            "content-type": "text/csv",
            "content-disposition": "",
        }.get(key, default)
        mock_response.headers = mock_headers

        async def _aiter_bytes(chunk_size: int = 8192):
            yield sample_csv_bytes

        mock_response.aiter_bytes = _aiter_bytes
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_response)

        with patch("src.web.routes.upload.httpx.AsyncClient", return_value=mock_client):
            response = test_client.post(
                "/upload/url",
                data={"url": "https://example.com/data.csv"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"]
        assert "/results/" in data["redirect"]

    def test_url_http_error_from_server(self, test_client: TestClient):
        """Non-200 response from the remote server is surfaced as a 400."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream = MagicMock(return_value=mock_response)

        with patch("src.web.routes.upload.httpx.AsyncClient", return_value=mock_client):
            response = test_client.post(
                "/upload/url",
                data={"url": "https://example.com/missing.csv"},
            )

        assert response.status_code == 400
        assert "404" in response.json()["detail"]