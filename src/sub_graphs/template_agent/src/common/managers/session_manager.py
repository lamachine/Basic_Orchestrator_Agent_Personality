"""
Session Manager Module

This module implements a session manager for handling user sessions and conversation history.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from ..config.base_config import SessionConfig, load_config
from ..services.session_service import SessionService
from ..state.state_models import Message, MessageStatus, MessageType
from .base_manager import BaseManager, ManagerState


class SessionStats(BaseModel):
    """Track session statistics."""

    total_sessions: int = 0
    active_sessions: int = 0
    expired_sessions: int = 0
    last_cleanup: Optional[datetime] = None
    session_history: List[Dict[str, Any]] = Field(default_factory=list)


class SessionState(ManagerState):
    """State model for session management."""

    current_session: Optional[Dict[str, Any]] = None
    session_locks: Dict[str, asyncio.Lock] = Field(default_factory=dict)
    stats: SessionStats = Field(default_factory=SessionStats)


class SessionManager(BaseManager[SessionConfig, SessionState]):
    """Manager for handling user sessions and conversation history."""

    def __init__(self, config: Optional[SessionConfig] = None):
        """Initialize the session manager.

        Args:
            config: Optional session configuration. If not provided, loads from base_config.yaml
        """
        if config is None:
            config = load_config("base_config.yaml").session
        super().__init__(config)
        self.service = SessionService(config)
        self._cleanup_task = None

    async def initialize(self) -> None:
        """Initialize the session manager."""
        await super().initialize()
        # Start cleanup task if auto_cleanup is enabled
        if self.config.auto_cleanup:
            self._cleanup_task = asyncio.create_task(self._cleanup_task())

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        await super().cleanup()

    async def _cleanup_task(self) -> None:
        """Background task for cleaning up expired sessions."""
        while True:
            try:
                await self.cleanup_expired_sessions()
                await asyncio.sleep(self.config.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create a lock for a session.

        Args:
            session_id: Session ID

        Returns:
            Lock for the session
        """
        if session_id not in self._state.session_locks:
            self._state.session_locks[session_id] = asyncio.Lock()
        return self._state.session_locks[session_id]

    @property
    def session_name(self) -> Optional[str]:
        """Get the current session name."""
        return self._state.current_session.get("name") if self._state.current_session else None

    @property
    def current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._state.current_session.get("id") if self._state.current_session else None

    async def get_recent_sessions(
        self, limit: int = 10, user_id: str = "developer"
    ) -> List[Dict[str, Any]]:
        """Get recent sessions.

        Args:
            limit: Maximum number of sessions to return
            user_id: User ID to filter sessions

        Returns:
            List of recent sessions
        """
        try:
            sessions = await self.service.get_recent_sessions(limit=limit, user_id=user_id)
            self._state.stats.total_sessions = len(sessions)
            return sessions
        except Exception as e:
            self.logger.error(f"Error getting recent sessions: {e}")
            return []

    async def create_session(self, name: str, user_id: str = "developer") -> Dict[str, Any]:
        """Create a new session.

        Args:
            name: Session name
            user_id: User ID

        Returns:
            Created session data
        """
        try:
            session = await self.service.create_session(name=name, user_id=user_id)
            self._state.current_session = session
            self._state.stats.active_sessions += 1
            return session
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            raise

    async def continue_session(self, session_id: str) -> Dict[str, Any]:
        """Continue an existing session.

        Args:
            session_id: Session ID

        Returns:
            Session data
        """
        try:
            session = await self.service.get_session(session_id)
            self._state.current_session = session
            return session
        except Exception as e:
            self.logger.error(f"Error continuing session: {e}")
            raise

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session data.

        Args:
            session_id: Session ID

        Returns:
            Session data
        """
        try:
            return await self.service.get_session(session_id)
        except Exception as e:
            self.logger.error(f"Error getting session: {e}")
            raise

    async def search_sessions(self, query: str, user_id: str = "developer") -> List[Dict[str, Any]]:
        """Search sessions.

        Args:
            query: Search query
            user_id: User ID to filter sessions

        Returns:
            List of matching sessions
        """
        try:
            return await self.service.search_sessions(query=query, user_id=user_id)
        except Exception as e:
            self.logger.error(f"Error searching sessions: {e}")
            return []

    async def rename_session(self, session_id: str, new_name: str) -> Dict[str, Any]:
        """Rename a session.

        Args:
            session_id: Session ID
            new_name: New session name

        Returns:
            Updated session data
        """
        try:
            session = await self.service.rename_session(session_id=session_id, new_name=new_name)
            if self._state.current_session and self._state.current_session.get("id") == session_id:
                self._state.current_session = session
            return session
        except Exception as e:
            self.logger.error(f"Error renaming session: {e}")
            raise

    async def end_session(self, session_id: str) -> None:
        """End a session.

        Args:
            session_id: Session ID
        """
        try:
            await self.service.end_session(session_id)
            if self._state.current_session and self._state.current_session.get("id") == session_id:
                self._state.current_session = None
            self._state.stats.active_sessions -= 1
        except Exception as e:
            self.logger.error(f"Error ending session: {e}")
            raise

    async def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session ID
        """
        try:
            await self.service.delete_session(session_id)
            if self._state.current_session and self._state.current_session.get("id") == session_id:
                self._state.current_session = None
            self._state.stats.active_sessions -= 1
        except Exception as e:
            self.logger.error(f"Error deleting session: {e}")
            raise

    async def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        try:
            expired = await self.service.cleanup_expired_sessions()
            self._state.stats.expired_sessions += len(expired)
            self._state.stats.active_sessions -= len(expired)
            self._state.stats.last_cleanup = datetime.now()
        except Exception as e:
            self.logger.error(f"Error cleaning up expired sessions: {e}")
            raise

    async def persist_state(self) -> None:
        """Persist the current state."""
        try:
            # Persist all sessions
            for session_id, session in self._state.sessions.items():
                async with self._get_session_lock(session_id):
                    await self.service.save_session(session)
        except Exception as e:
            self.logger.error(f"Error persisting state: {e}")

    async def load_state(self) -> None:
        """Load state from storage."""
        try:
            # Load all sessions
            sessions = await self.service.get_all_sessions()
            for session in sessions:
                session_id = session["id"]
                self._state.sessions[session_id] = session
                self._state.session_locks[session_id] = asyncio.Lock()
                self._state.stats.active_sessions += 1
                self._state.stats.total_sessions += 1
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics.

        Returns:
            Dictionary of session statistics
        """
        return {
            "total_sessions": self._state.stats.total_sessions,
            "active_sessions": self._state.stats.active_sessions,
            "expired_sessions": self._state.stats.expired_sessions,
            "last_cleanup": self._state.stats.last_cleanup,
            "session_history": self._state.stats.session_history[-100:],  # Keep last 100 entries
        }
