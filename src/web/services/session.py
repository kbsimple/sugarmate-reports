"""Session management for CGM Insights web application.

Provides in-memory session storage for MVP. Sessions store analysis results
keyed by unique session IDs.
"""

import uuid
from typing import Optional
from dataclasses import dataclass, field

from cgm_insights.models import AnalysisResults
from cgm_insights.analytics import PatternResult


@dataclass
class SessionData:
    """Container for session data including results and patterns.

    Attributes:
        results: Analysis results from file processing
        patterns: Detected patterns (time-of-day, day-of-week)
        raw_readings: Raw CGM readings for chart generation
        behavioral_patterns: Behavioral pattern analysis result dict, or None
    """

    results: AnalysisResults
    patterns: list[PatternResult] = field(default_factory=list)
    raw_readings: list[dict] = field(default_factory=list)
    behavioral_patterns: Optional[dict] = field(default=None)


class SessionStore:
    """In-memory session storage for analysis results.

    For MVP, sessions are stored in memory. In production,
    this would be replaced with Redis or database storage.
    """

    def __init__(self):
        self._sessions: dict[str, SessionData] = {}

    def store(
        self,
        session_id: str,
        results: AnalysisResults,
        patterns: Optional[list[PatternResult]] = None,
        raw_readings: Optional[list[dict]] = None,
        behavioral_patterns: Optional[dict] = None,
    ) -> None:
        """Store analysis results for a session.

        Args:
            session_id: Unique session identifier
            results: Analysis results to store
            patterns: Optional detected patterns
            raw_readings: Optional raw readings for charts
            behavioral_patterns: Optional behavioral analysis result (serialized dict)
        """
        self._sessions[session_id] = SessionData(
            results=results,
            patterns=patterns or [],
            raw_readings=raw_readings or [],
            behavioral_patterns=behavioral_patterns,
        )

    def get(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session data for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            SessionData if found, None otherwise
        """
        return self._sessions.get(session_id)

    def get_results(self, session_id: str) -> Optional[AnalysisResults]:
        """Retrieve analysis results for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            AnalysisResults if found, None otherwise
        """
        session_data = self._sessions.get(session_id)
        return session_data.results if session_data else None

    def get_patterns(self, session_id: str) -> Optional[list[PatternResult]]:
        """Retrieve detected patterns for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            List of PatternResult if found, None otherwise
        """
        session_data = self._sessions.get(session_id)
        return session_data.patterns if session_data else None

    def get_raw_readings(self, session_id: str) -> Optional[list[dict]]:
        """Retrieve raw readings for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            List of raw reading dicts if found, None otherwise
        """
        session_data = self._sessions.get(session_id)
        return session_data.raw_readings if session_data else None

    def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session exists, False otherwise
        """
        return session_id in self._sessions


def create_session() -> str:
    """Generate a new unique session ID.

    Uses UUID v4 for cryptographically random session IDs
    to prevent session hijacking.

    Returns:
        Unique session identifier string
    """
    return str(uuid.uuid4())


def get_session(session_id: str, store: SessionStore) -> Optional[SessionData]:
    """Convenience function to get session data.

    Args:
        session_id: Unique session identifier
        store: Session store instance

    Returns:
        SessionData if found, None otherwise
    """
    return store.get(session_id)


# Global session store instance
session_store = SessionStore()