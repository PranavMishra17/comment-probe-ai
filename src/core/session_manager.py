"""
Session management for persisting and loading analysis sessions.

Allows reusing embeddings and analysis results across sessions.
"""

import logging
import json
import pickle
import os
from typing import Optional, Dict, List
from datetime import datetime

from src.core.models import Video, Comment, AnalyticsResult, ProcessingMetadata

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages saving and loading of analysis sessions.

    Persists embeddings, videos, and analysis results for reuse.
    """

    def __init__(self, base_dir: str = "output"):
        """
        Initialize session manager.

        Args:
            base_dir: Base directory for session storage
        """
        self.base_dir = base_dir
        logger.info(f"[SessionManager] Initialized with base dir: {base_dir}")

    def save_session(
        self,
        run_id: str,
        videos: List[Video],
        analytics: Dict[str, AnalyticsResult],
        metadata: ProcessingMetadata
    ) -> str:
        """
        Saves complete session for later reuse.

        Args:
            run_id: Run identifier
            videos: List of analyzed videos
            analytics: Analytics results
            metadata: Processing metadata

        Returns:
            Path to saved session
        """
        logger.info(f"[SessionManager] Saving session {run_id}")

        session_dir = os.path.join(self.base_dir, f"run-{run_id}")
        session_file = os.path.join(session_dir, "session.pkl")

        try:
            # Create session data
            session_data = {
                'run_id': run_id,
                'videos': videos,
                'analytics': analytics,
                'metadata': metadata,
                'saved_at': datetime.utcnow().isoformat()
            }

            # Save as pickle for easy loading
            with open(session_file, 'wb') as f:
                pickle.dump(session_data, f)

            logger.info(f"[SessionManager] Session saved to {session_file}")
            return session_file

        except Exception as e:
            logger.error(f"[SessionManager] Failed to save session: {e}", exc_info=True)
            raise

    def load_session(self, run_id: str) -> Optional[Dict]:
        """
        Loads a previous session.

        Args:
            run_id: Run identifier to load

        Returns:
            Session data dictionary or None if not found
        """
        logger.info(f"[SessionManager] Loading session {run_id}")

        session_file = os.path.join(self.base_dir, f"run-{run_id}", "session.pkl")

        if not os.path.exists(session_file):
            logger.warning(f"[SessionManager] Session file not found: {session_file}")
            return None

        try:
            with open(session_file, 'rb') as f:
                session_data = pickle.load(f)

            logger.info(f"[SessionManager] Session loaded successfully")
            return session_data

        except Exception as e:
            logger.error(f"[SessionManager] Failed to load session: {e}", exc_info=True)
            return None

    def get_session_embeddings(self, run_id: str) -> Optional[Dict[str, List[float]]]:
        """
        Extracts embeddings from a session.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary mapping comment IDs to embeddings
        """
        session = self.load_session(run_id)
        if not session:
            return None

        embeddings = {}
        videos = session.get('videos', [])

        for video in videos:
            for comment in video.comments:
                if comment.embedding:
                    embeddings[comment.id] = comment.embedding

        logger.info(f"[SessionManager] Extracted {len(embeddings)} embeddings from session")
        return embeddings

    def list_sessions(self) -> List[str]:
        """
        Lists all available sessions.

        Returns:
            List of run IDs
        """
        if not os.path.exists(self.base_dir):
            return []

        sessions = []
        for item in os.listdir(self.base_dir):
            if item.startswith('run-') and os.path.isdir(os.path.join(self.base_dir, item)):
                run_id = item.replace('run-', '')
                sessions.append(run_id)

        sessions.sort(reverse=True)
        return sessions

    def get_session_info(self, run_id: str) -> Optional[Dict]:
        """
        Gets metadata about a session.

        Args:
            run_id: Run identifier

        Returns:
            Session info dictionary
        """
        metadata_file = os.path.join(self.base_dir, f"run-{run_id}", "metadata.json")

        if not os.path.exists(metadata_file):
            return None

        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[SessionManager] Failed to load metadata: {e}")
            return None
