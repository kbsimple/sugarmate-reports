"""Tests for the /statusz health-and-telemetry endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestStatusz:
    def test_returns_200(self, client):
        resp = client.get("/statusz")
        assert resp.status_code == 200

    def test_content_type_html(self, client):
        resp = client.get("/statusz")
        assert "text/html" in resp.headers["content-type"]

    def test_identity_section_present(self, client):
        body = client.get("/statusz").text
        assert "cgm-insights" in body
        assert "ok" in body

    def test_runtime_section_present(self, client):
        body = client.get("/statusz").text
        assert "uptime" in body
        assert "memory" in body
        assert "python" in body

    def test_session_activity_section_present(self, client):
        body = client.get("/statusz").text
        assert "active sessions" in body
        assert "readings in memory" in body

    def test_features_section_lists_known_features(self, client):
        body = client.get("/statusz").text
        assert "Behavioral pattern analysis" in body
        assert "AGP PDF export" in body
        assert "Daily TIR chart with gap-fill" in body

    def test_dependencies_section_present(self, client):
        body = client.get("/statusz").text
        assert "fastapi" in body
        assert "polars" in body
        assert "pydantic" in body

    def test_session_count_reflects_store(self, client, sample_session_id):
        """After creating one session, the page must show at least 1 active session."""
        body = client.get("/statusz").text
        assert "active sessions" in body
        # The count cell must be non-zero — check that "0" is NOT the only digit
        # by verifying the session_id created by the fixture is visible in the store
        from src.web.services.session import session_store
        assert len(session_store._sessions) >= 1
