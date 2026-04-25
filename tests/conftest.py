"""Shared pytest fixtures for CGM Insights tests.

Provides fixtures for testing the web interface including:
- FastAPI TestClient
- Sample session data
- Temporary file handling
"""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from cgm_insights.models import AnalysisResults, TimeInRange
from cgm_insights.analytics import PatternResult, PatternType, PatternSeverity
from cgm_insights.output.suggestions import Suggestion
from src.web.app import app
from src.web.services.session import session_store, SessionData, create_session

from tests.fixtures.sample_data import (
    generate_sample_readings,
    generate_sample_results,
    create_sample_csv_content,
)


@pytest.fixture
def test_client() -> TestClient:
    """Create a FastAPI test client.

    Returns:
        TestClient instance for making requests to the app
    """
    return TestClient(app)


@pytest.fixture
def sample_csv_content() -> str:
    """Create valid CSV content for upload testing.

    Returns:
        CSV content string with header and sample readings
    """
    return create_sample_csv_content()


@pytest.fixture
def sample_csv_bytes() -> bytes:
    """Create valid CSV content as bytes for upload testing.

    Returns:
        CSV content as bytes
    """
    return create_sample_csv_content().encode("utf-8")


@pytest.fixture
def sample_session_id() -> str:
    """Create a session with sample results.

    Returns:
        Session ID string
    """
    session_id = create_session()
    results = generate_sample_results()
    readings = generate_sample_readings(count=500, days=14)
    raw_readings = [
        {"timestamp": r.timestamp.isoformat(), "glucose": r.glucose_mg_dl}
        for r in readings
    ]

    session_store.store(
        session_id,
        results,
        patterns=[],
        raw_readings=raw_readings,
    )

    return session_id


@pytest.fixture
def sample_session_with_patterns() -> str:
    """Create a session with patterns for testing.

    Returns:
        Session ID string
    """
    session_id = create_session()
    results = generate_sample_results()

    patterns = [
        PatternResult(
            pattern_type=PatternType.TIME_OF_DAY,
            description="Morning glucose elevated (avg 180 mg/dL)",
            time_period="06:00-08:00",
            severity=PatternSeverity.MODERATE,
            avg_glucose=180.0,
            reading_count=60,
            confidence=0.85,
        ),
        PatternResult(
            pattern_type=PatternType.DAY_OF_WEEK,
            description="Weekend glucose lower (avg 125 mg/dL)",
            time_period="Saturday-Sunday",
            severity=PatternSeverity.INFO,
            avg_glucose=125.0,
            reading_count=200,
            confidence=0.75,
        ),
    ]

    readings = generate_sample_readings(count=500, days=14)
    raw_readings = [
        {"timestamp": r.timestamp.isoformat(), "glucose": r.glucose_mg_dl}
        for r in readings
    ]

    session_store.store(
        session_id,
        results,
        patterns=patterns,
        raw_readings=raw_readings,
    )

    return session_id


@pytest.fixture
def temp_upload_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for file uploads.

    Yields:
        Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def empty_csv_file() -> bytes:
    """Create empty CSV content for error testing.

    Returns:
        Empty bytes
    """
    return b""


@pytest.fixture
def invalid_extension_file() -> bytes:
    """Create file with invalid extension content.

    Returns:
        Text file content
    """
    return b"This is not a CSV file"


@pytest.fixture
def insufficient_data_csv() -> bytes:
    """Create CSV with insufficient data.

    Returns:
        CSV content with too few readings
    """
    return b"timestamp,glucose\n2026-04-25T12:00:00,140\n"


@pytest.fixture
def large_csv_bytes() -> bytes:
    """Create CSV content larger than upload limit.

    Returns:
        Large CSV content (>10MB)
    """
    # Create content larger than 10MB limit
    header = b"timestamp,glucose\n"
    row = b"2026-04-25T12:00:00,140\n"

    content = header
    # Need about 11MB to exceed limit
    target_size = 11 * 1024 * 1024
    while len(content) < target_size:
        content += row

    return content


@pytest.fixture(autouse=True)
def reset_session_store():
    """Reset session store between tests.

    Ensures test isolation for session-related tests.
    """
    session_store._sessions.clear()
    yield
    session_store._sessions.clear()