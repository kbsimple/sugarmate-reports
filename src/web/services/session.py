"""Session management for CGM Insights web application.

Provides in-memory session storage for MVP. Sessions store analysis results
keyed by unique session IDs.
"""

import uuid
from typing import Optional

from cgm_insights.models import AnalysisResults


class SessionStore:
    """In-memory session storage for analysis results.

    For MVP, sessions are stored in memory. In production,
    this would be replaced with Redis or database storage.
    """

    def __init__(self):
        self._sessions: dict[str, AnalysisResults] = {}

    def store(self, session_id: str, results: AnalysisResults) -> None:
        """Store analysis results for a session.

        Args:
            session_id: Unique session identifier
            results: Analysis results to store
        """
        self._sessions[session_id] = results

    def get(self, session_id: str) -> Optional[AnalysisResults]:
        """Retrieve analysis results for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            AnalysisResults if found, None otherwise
        """
        return self._sessions.get(session_id)

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


def get_session(session_id: str, store: SessionStore) -> Optional[AnalysisResults]:
    """Convenience function to get session results.

    Args:
        session_id: Unique session identifier
        store: Session store instance

    Returns:
        AnalysisResults if found, None otherwise
    """
    return store.get(session_id)


# Global session store instance
session_store = SessionStore()