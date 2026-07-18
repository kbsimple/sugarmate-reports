"""Shared pytest fixtures for CGM Insights tests.

Provides fixtures for testing the web interface including:
- FastAPI TestClient
- Sample session data
- Temporary file handling
"""

import math
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from cgm_insights.models import AnalysisResults, TimeInRange, CGMReading
from cgm_insights.analytics import PatternResult, PatternType, PatternSeverity
from cgm_insights.analytics.behavioral_patterns import analyze_behavioral_patterns
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
    readings = generate_sample_readings(count=8640, days=30)
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

    readings = generate_sample_readings(count=8640, days=30)
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
def sample_session_with_behavioral_patterns() -> str:
    """Session with sufficient behavioral_patterns data (14 days, normal glucose).

    Used to test rendering of the behavioralPatternsChart canvas.

    Returns:
        Session ID string
    """
    session_id = create_session()
    results = generate_sample_results()
    # 30 days × 288 readings/day — full month, well above MIN_DAYS=5 threshold
    readings = generate_sample_readings(count=8640, days=30, avg_glucose=140.0, std_dev=20.0)
    raw_readings = [
        {"timestamp": r.timestamp.isoformat(), "glucose": r.glucose_mg_dl}
        for r in readings
    ]

    bp_result = analyze_behavioral_patterns(readings)
    bp_data = bp_result.model_dump() if not bp_result.insufficient_data else None

    session_store.store(
        session_id,
        results,
        patterns=[],
        raw_readings=raw_readings,
        behavioral_patterns=bp_data,
    )
    return session_id


@pytest.fixture
def sample_session_with_oor_behavioral_patterns() -> str:
    """Session with behavioral_patterns that include out-of-range hourly windows.

    Uses avg_glucose=220 so all hourly pattern averages exceed 180 mg/dL,
    guaranteeing expandable OOR rows appear in 'Time Windows to Focus On'.

    Returns:
        Session ID string
    """
    session_id = create_session()
    results = generate_sample_results(avg_glucose=220.0, tir_target=20.0)
    readings = generate_sample_readings(count=8640, days=30, avg_glucose=220.0, std_dev=15.0)
    raw_readings = [
        {"timestamp": r.timestamp.isoformat(), "glucose": r.glucose_mg_dl}
        for r in readings
    ]

    bp_result = analyze_behavioral_patterns(readings)
    bp_data = bp_result.model_dump() if not bp_result.insufficient_data else None

    session_store.store(
        session_id,
        results,
        patterns=[],
        raw_readings=raw_readings,
        behavioral_patterns=bp_data,
    )
    return session_id


@pytest.fixture
def sample_session_with_source_url() -> str:
    """Session that was loaded from a URL — source_url is populated.

    Used to verify the share button appears on the results page.
    """
    session_id = create_session()
    results = generate_sample_results()
    readings = generate_sample_readings(count=8640, days=30)
    raw_readings = [
        {"timestamp": r.timestamp.isoformat(), "glucose": r.glucose_mg_dl}
        for r in readings
    ]
    session_store.store(
        session_id,
        results,
        patterns=[],
        raw_readings=raw_readings,
        source_url="https://example.com/my-cgm-data.csv",
    )
    return session_id


@pytest.fixture
def sample_session_90_days() -> str:
    """Session with 90 days of readings — used to verify scroll triggers for large periods.

    Uses hourly intervals (24/day) to keep fixture generation fast while
    still producing 90 distinct calendar dates in glucoseReadings.

    Returns:
        Session ID string
    """
    session_id = create_session()
    results = generate_sample_results()
    readings = generate_sample_readings(count=2160, days=90)
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
def sample_session_with_mid_period_gap() -> str:
    """Session with a 5-day gap in the middle of a 30-day period.

    Days 0–9 and 15–29 have readings; days 10–14 have none.
    Used to verify that computeDailyTIR fills the gap with 0% grey bars.

    Returns:
        Session ID string
    """
    import math

    session_id = create_session()
    results = generate_sample_results()
    start = datetime(2026, 1, 1, 0, 0)
    SKIP = {10, 11, 12, 13, 14}
    readings = []
    for day in range(30):
        if day in SKIP:
            continue
        day_start = start + timedelta(days=day)
        for hour in range(0, 24, 2):
            ts = day_start + timedelta(hours=hour)
            glucose = max(70.0, min(200.0, 140.0 + 20.0 * math.sin(hour / 6.0)))
            readings.append(CGMReading(timestamp=ts, glucose_mg_dl=glucose, source="test"))
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