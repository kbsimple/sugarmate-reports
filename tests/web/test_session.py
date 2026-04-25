"""Tests for session management.

Tests cover:
- Session creation with UUID format
- Session storage and retrieval
- Session isolation between users
"""

import re

import pytest

from src.web.services.session import (
    SessionStore,
    SessionData,
    create_session,
    get_session,
)
from tests.fixtures.sample_data import generate_sample_results, generate_sample_readings


class TestSessionCreation:
    """Tests for session ID creation."""

    def test_create_session_returns_uuid(self):
        """Test that create_session returns a valid UUID string."""
        session_id = create_session()

        assert session_id is not None
        assert isinstance(session_id, str)

        # Verify UUID format (8-4-4-4-12 hex pattern)
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert uuid_pattern.match(session_id), f"Session ID {session_id} is not valid UUID format"

    def test_create_session_unique(self):
        """Test that multiple calls create unique session IDs."""
        session_id1 = create_session()
        session_id2 = create_session()

        assert session_id1 != session_id2

    def test_create_session_consistent_length(self):
        """Test that all session IDs have consistent length."""
        for _ in range(10):
            session_id = create_session()
            # UUID string with dashes is 36 characters
            assert len(session_id) == 36


class TestSessionStore:
    """Tests for SessionStore class."""

    def test_store_and_retrieve(self):
        """Test basic store and retrieve operations."""
        store = SessionStore()
        results = generate_sample_results()
        session_id = "test-session-123"

        store.store(session_id, results)

        retrieved = store.get(session_id)
        assert retrieved is not None
        assert retrieved.results == results

    def test_store_with_patterns(self):
        """Test storing session with patterns."""
        store = SessionStore()
        results = generate_sample_results()
        patterns = []
        session_id = "test-session-pattern"

        store.store(session_id, results, patterns=patterns)

        retrieved = store.get(session_id)
        assert retrieved.patterns == patterns

    def test_store_with_raw_readings(self):
        """Test storing session with raw readings."""
        store = SessionStore()
        results = generate_sample_results()
        readings = [
            {"timestamp": "2026-04-25T12:00:00", "glucose": 140},
            {"timestamp": "2026-04-25T12:05:00", "glucose": 145},
        ]
        session_id = "test-session-readings"

        store.store(session_id, results, raw_readings=readings)

        retrieved = store.get(session_id)
        assert retrieved.raw_readings == readings

    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session returns None."""
        store = SessionStore()

        retrieved = store.get("nonexistent-id")

        assert retrieved is None

    def test_get_results_nonexistent(self):
        """Test get_results for non-existent session."""
        store = SessionStore()

        results = store.get_results("nonexistent-id")

        assert results is None

    def test_get_patterns_nonexistent(self):
        """Test get_patterns for non-existent session."""
        store = SessionStore()

        patterns = store.get_patterns("nonexistent-id")

        assert patterns is None

    def test_get_raw_readings_nonexistent(self):
        """Test get_raw_readings for non-existent session."""
        store = SessionStore()

        readings = store.get_raw_readings("nonexistent-id")

        assert readings is None

    def test_session_isolation(self):
        """Test that sessions are isolated from each other."""
        store = SessionStore()
        results1 = generate_sample_results(avg_glucose=100.0)
        results2 = generate_sample_results(avg_glucose=200.0)

        store.store("session-1", results1)
        store.store("session-2", results2)

        retrieved1 = store.get("session-1")
        retrieved2 = store.get("session-2")

        assert retrieved1.results.average_glucose == 100.0
        assert retrieved2.results.average_glucose == 200.0

    def test_overwrite_session(self):
        """Test that storing with same ID overwrites data."""
        store = SessionStore()
        results1 = generate_sample_results(avg_glucose=100.0)
        results2 = generate_sample_results(avg_glucose=200.0)

        store.store("same-session", results1)
        store.store("same-session", results2)

        retrieved = store.get("same-session")
        assert retrieved.results.average_glucose == 200.0

    def test_delete_session(self):
        """Test deleting a session."""
        store = SessionStore()
        results = generate_sample_results()

        store.store("to-delete", results)
        assert store.get("to-delete") is not None

        deleted = store.delete("to-delete")
        assert deleted is True
        assert store.get("to-delete") is None

    def test_delete_nonexistent_session(self):
        """Test deleting non-existent session returns False."""
        store = SessionStore()

        deleted = store.delete("nonexistent")

        assert deleted is False

    def test_session_exists(self):
        """Test checking if session exists."""
        store = SessionStore()
        results = generate_sample_results()

        store.store("existing", results)

        assert store.exists("existing") is True
        assert store.exists("nonexistent") is False


class TestSessionData:
    """Tests for SessionData dataclass."""

    def test_session_data_creation(self):
        """Test creating SessionData with results."""
        results = generate_sample_results()

        session_data = SessionData(results=results)

        assert session_data.results == results
        assert session_data.patterns == []
        assert session_data.raw_readings == []

    def test_session_data_with_patterns(self):
        """Test creating SessionData with patterns."""
        results = generate_sample_results()
        patterns = []

        session_data = SessionData(results=results, patterns=patterns)

        assert session_data.patterns == patterns

    def test_session_data_with_readings(self):
        """Test creating SessionData with raw readings."""
        results = generate_sample_results()
        readings = [{"timestamp": "2026-04-25T12:00:00", "glucose": 140}]

        session_data = SessionData(results=results, raw_readings=readings)

        assert session_data.raw_readings == readings


class TestGetSession:
    """Tests for get_session convenience function."""

    def test_get_session_retrieves_data(self):
        """Test get_session convenience function."""
        store = SessionStore()
        results = generate_sample_results()
        session_id = "test-get-session"

        store.store(session_id, results)

        session_data = get_session(session_id, store)
        assert session_data is not None
        assert session_data.results == results

    def test_get_session_none_for_nonexistent(self):
        """Test get_session returns None for non-existent session."""
        store = SessionStore()

        session_data = get_session("nonexistent", store)

        assert session_data is None


class TestGlobalSessionStore:
    """Tests for the global session_store instance."""

    def test_global_store_persists(self):
        """Test that global store persists across calls."""
        from src.web.services.session import session_store

        results = generate_sample_results()
        session_id = create_session()

        session_store.store(session_id, results)
        retrieved = session_store.get(session_id)

        assert retrieved is not None
        assert retrieved.results == results

        # Cleanup
        session_store.delete(session_id)