"""Integration tests for web interface.

Tests cover:
- Full workflow from upload to results to export
- End-to-end user journey validation
"""

import io

import pytest
from fastapi.testclient import TestClient

from src.web.services.session import session_store
from tests.fixtures.sample_data import create_sample_csv_content


class TestFullWorkflow:
    """Tests for the complete user workflow."""

    def test_upload_to_results_workflow(self, test_client: TestClient):
        """Test complete workflow: upload -> get results."""
        # Step 1: Upload a file
        csv_content = create_sample_csv_content()
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        upload_response = test_client.post("/api/upload", files=files)

        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        upload_data = upload_response.json()

        assert "session_id" in upload_data
        session_id = upload_data["session_id"]
        assert session_id  # Non-empty session ID

        # Step 2: Get results
        results_response = test_client.get(f"/api/results/{session_id}/data")

        assert results_response.status_code == 200, f"Results failed: {results_response.text}"
        results_data = results_response.json()

        # Verify results structure
        assert "results" in results_data
        assert "patterns" in results_data
        assert "glucose_readings" in results_data

        # Verify results content
        results = results_data["results"]
        assert results["total_readings"] > 0
        assert results["average_glucose"] > 0
        assert "time_in_range" in results

    def test_upload_to_export_workflow(self, test_client: TestClient):
        """Test complete workflow: upload -> export AGP."""
        # Step 1: Upload a file
        csv_content = create_sample_csv_content()
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        upload_response = test_client.post("/api/upload", files=files)

        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        session_id = upload_response.json()["session_id"]

        # Step 2: Export AGP report
        export_response = test_client.get(f"/export/{session_id}/agp")

        assert export_response.status_code == 200, f"Export failed: {export_response.text}"
        assert export_response.headers["content-type"] == "application/pdf"
        assert export_response.content.startswith(b"%PDF")

    def test_upload_preview_export_workflow(self, test_client: TestClient):
        """Test workflow: upload -> preview -> export."""
        # Step 1: Upload
        csv_content = create_sample_csv_content()
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        upload_response = test_client.post("/api/upload", files=files)
        assert upload_response.status_code == 200
        session_id = upload_response.json()["session_id"]

        # Step 2: Preview AGP
        preview_response = test_client.get(f"/export/{session_id}/preview")
        assert preview_response.status_code == 200
        assert "text/html" in preview_response.headers["content-type"]

        # Step 3: Export AGP
        export_response = test_client.get(f"/export/{session_id}/agp")
        assert export_response.status_code == 200
        assert export_response.content.startswith(b"%PDF")

    def test_multiple_uploads_isolated(self, test_client: TestClient):
        """Test that multiple uploads create isolated sessions."""
        # Upload 1
        csv_content1 = create_sample_csv_content()
        files1 = {"file": ("test1.csv", io.BytesIO(csv_content1.encode()), "text/csv")}
        response1 = test_client.post("/api/upload", files=files1)
        session_id1 = response1.json()["session_id"]

        # Upload 2
        csv_content2 = create_sample_csv_content()
        files2 = {"file": ("test2.csv", io.BytesIO(csv_content2.encode()), "text/csv")}
        response2 = test_client.post("/api/upload", files=files2)
        session_id2 = response2.json()["session_id"]

        # Sessions should be different
        assert session_id1 != session_id2

        # Both should have valid results
        results1 = test_client.get(f"/api/results/{session_id1}/data").json()
        results2 = test_client.get(f"/api/results/{session_id2}/data").json()

        assert results1["results"]["total_readings"] > 0
        assert results2["results"]["total_readings"] > 0

    def test_session_lifecycle(self, test_client: TestClient):
        """Test session lifecycle: create -> use -> delete."""
        # Create session via upload
        csv_content = create_sample_csv_content()
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        response = test_client.post("/api/upload", files=files)
        session_id = response.json()["session_id"]

        # Use session for results
        results_response = test_client.get(f"/api/results/{session_id}/data")
        assert results_response.status_code == 200

        # Use session for export
        export_response = test_client.get(f"/export/{session_id}/agp")
        assert export_response.status_code == 200

        # Delete session
        deleted = session_store.delete(session_id)
        assert deleted is True

        # Session should no longer be accessible
        results_response2 = test_client.get(f"/api/results/{session_id}/data")
        assert results_response2.status_code == 404

        export_response2 = test_client.get(f"/export/{session_id}/agp")
        assert export_response2.status_code == 404


class TestErrorHandling:
    """Tests for error handling across the workflow."""

    def test_invalid_session_for_results(self, test_client: TestClient):
        """Test that invalid session returns 404 for results."""
        response = test_client.get("/api/results/invalid-session-id/data")
        assert response.status_code == 404

    def test_invalid_session_for_export(self, test_client: TestClient):
        """Test that invalid session returns 404 for export."""
        response = test_client.get("/export/invalid-session-id/agp")
        assert response.status_code == 404

    def test_upload_invalid_file_type(self, test_client: TestClient):
        """Test that invalid file type is rejected."""
        files = {"file": ("test.txt", io.BytesIO(b"invalid"), "text/plain")}
        response = test_client.post("/api/upload", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_empty_file(self, test_client: TestClient):
        """Test that empty file is rejected."""
        files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
        response = test_client.post("/api/upload", files=files)
        assert response.status_code in [400, 422, 500]  # Various error codes possible


class TestDataConsistency:
    """Tests for data consistency across endpoints."""

    def test_results_match_upload(self, test_client: TestClient):
        """Test that results endpoint returns same data as upload."""
        # Upload
        csv_content = create_sample_csv_content()
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        upload_response = test_client.post("/api/upload", files=files)
        session_id = upload_response.json()["session_id"]

        # Get results
        results_response = test_client.get(f"/api/results/{session_id}/data")
        results = results_response.json()

        # Verify session store contains same data
        session_data = session_store.get(session_id)
        assert session_data is not None
        assert session_data.results.total_readings == results["results"]["total_readings"]

    def test_export_uses_session_data(self, test_client: TestClient):
        """Test that export uses the same session data."""
        # Upload
        csv_content = create_sample_csv_content()
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        upload_response = test_client.post("/api/upload", files=files)
        session_id = upload_response.json()["session_id"]

        # Get session data
        session_data = session_store.get(session_id)
        assert session_data is not None

        # Export should use same session
        export_response = test_client.get(f"/export/{session_id}/agp")
        assert export_response.status_code == 200

        # Session should still be valid after export
        session_data2 = session_store.get(session_id)
        assert session_data2 is not None
        assert session_data2.results.total_readings == session_data.results.total_readings


class TestPerformance:
    """Tests for performance characteristics."""

    def test_results_response_time(self, test_client: TestClient, sample_session_id: str):
        """Test that results endpoint responds quickly."""
        import time

        start = time.time()
        response = test_client.get(f"/api/results/{sample_session_id}/data")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond within 1 second

    def test_export_response_time(self, test_client: TestClient, sample_session_id: str):
        """Test that export endpoint responds quickly."""
        import time

        start = time.time()
        response = test_client.get(f"/export/{sample_session_id}/agp")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 2.0  # PDF generation should be fast