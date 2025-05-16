"""
Session Manager Module

This module implements a session manager for handling user sessions and conversation history.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from pathlib import Path
from uuid import uuid4
import asyncio

from .base_manager import BaseManager, ManagerState
from ..services.session_service import SessionService
from .state_models import Message, MessageType, MessageStatus
from .service_models import SessionServiceConfig

class SessionState(ManagerState):
    """State model for session management."""
    session_id: Optional[str] = None
    name: Optional[str] = None
    user_id: str = "developer"
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    active: bool = True

class SessionManager(BaseManager):
    """Manager for handling user sessions and conversation history."""
    
    def __init__(self, config: SessionServiceConfig):
        """Initialize the session manager.
        
        Args:
            config: Session service configuration
        """
        super().__init__(config)
        self.session_timeout = config.session_timeout
        self.max_sessions = config.max_sessions
        self.cleanup_interval = config.cleanup_interval
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self.current_session: Optional[SessionState] = None
        self._session_locks: Dict[str, asyncio.Lock] = {}

    async def initialize(self) -> None:
        """Initialize the session manager."""
        await super().initialize()
        # Start cleanup task
        asyncio.create_task(self._cleanup_task())

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Cancel cleanup task
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
        await super().cleanup()

    async def _cleanup_task(self) -> None:
        """Background task for cleaning up expired sessions."""
        while True:
            try:
                await self.cleanup_expired_sessions()
                await asyncio.sleep(self.cleanup_interval)
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
        if session_id not in self._session_locks:
            self._session_locks[session_id] = asyncio.Lock()
        return self._session_locks[session_id]

    @property
    def session_name(self) -> Optional[str]:
        """Get the current session name."""
        return self.current_session.name if self.current_session else None

    @property
    def current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self.current_session.session_id if self.current_session else None
    
    async def get_recent_sessions(self, limit: int = 10, user_id: str = "developer") -> List[Dict[str, Any]]:
        """
        Get recent sessions from the session service.
        
        Args:
            limit: Maximum number of sessions to return
            user_id: User ID to filter sessions
            
        Returns:
            List of recent sessions
        """
        try:
            return await self.session_service.get_recent_sessions(limit=limit, user_id=user_id)
        except Exception as e:
            self.logger.error(f"Error getting recent sessions: {e}")
            return []

    async def create_session(self, 
                           session_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Create a new session.
        
        Args:
            session_id: Optional session ID
            metadata: Optional session metadata
            
        Returns:
            Message containing the session info
        """
        try:
            # Check if we've hit the session limit
            if len(self._sessions) >= self.max_sessions:
                error_msg = self.create_error_message(
                    content="Maximum number of sessions reached",
                    error_data={"max_sessions": self.max_sessions}
                )
                self.update_state(error_msg)
                return error_msg

            # Create session
            session_id = session_id or str(uuid4())
            session = {
                "id": session_id,
                "created_at": datetime.now(),
                "last_active": datetime.now(),
                "metadata": metadata or {},
                "messages": []
            }

            # Use lock for session creation
            async with self._get_session_lock(session_id):
                self._sessions[session_id] = session

                # Create success message
                message = self.create_message(
                    content=f"Session {session_id} created",
                    message_type=MessageType.RESPONSE,
                    status=MessageStatus.SUCCESS,
                    data={"session": session}
                )
                self.update_state(message)

                # Update current session state
                self.current_session = SessionState(
                    session_id=str(session_id),
                    name=metadata.get('name'),
                    user_id=metadata.get('user_id', "developer"),
                    messages=session.get('messages', [])
                )
                
                # Ensure agent's graph_state has the correct MessageState
                if hasattr(self, 'agent') and self.agent:
                    if not hasattr(self.agent, 'graph_state'):
                        self.agent.graph_state = {}
                    self.agent.graph_state['conversation_state'] = MessageState(
                        session_id=int(session_id),
                        db_manager=self.session_service.db_service
                    )
                    self.logger.debug(f"Initialized session state in agent's graph_state for session ID: {session_id}")
                
                return message

        except Exception as e:
            error_msg = self.create_error_message(
                content=f"Error creating session: {str(e)}",
                error_data={"error": str(e)}
            )
            self.update_state(error_msg)
            return error_msg

    async def get_session(self, session_id: str) -> Message:
        """Get session information.
        
        Args:
            session_id: Session ID
            
        Returns:
            Message containing the session info
        """
        try:
            async with self._get_session_lock(session_id):
                if session_id not in self._sessions:
                    error_msg = self.create_error_message(
                        content=f"Session {session_id} not found",
                        error_data={"session_id": session_id}
                    )
                    self.update_state(error_msg)
                    return error_msg

                session = self._sessions[session_id]
                session["last_active"] = datetime.now()

                message = self.create_message(
                    content=f"Retrieved session {session_id}",
                    message_type=MessageType.RESPONSE,
                    status=MessageStatus.SUCCESS,
                    data={"session": session}
                )
                self.update_state(message)
                return message

        except Exception as e:
            error_msg = self.create_error_message(
                content=f"Error getting session: {str(e)}",
                error_data={"error": str(e)}
            )
            self.update_state(error_msg)
            return error_msg

    async def update_session(self,
                           session_id: str,
                           updates: Dict[str, Any]) -> Message:
        """Update session information.
        
        Args:
            session_id: Session ID
            updates: Dictionary of updates
            
        Returns:
            Message containing the updated session info
        """
        try:
            async with self._get_session_lock(session_id):
                if session_id not in self._sessions:
                    error_msg = self.create_error_message(
                        content=f"Session {session_id} not found",
                        error_data={"session_id": session_id}
                    )
                    self.update_state(error_msg)
                    return error_msg

                session = self._sessions[session_id]
                session.update(updates)
                session["last_active"] = datetime.now()

                message = self.create_message(
                    content=f"Updated session {session_id}",
                    message_type=MessageType.RESPONSE,
                    status=MessageStatus.SUCCESS,
                    data={"session": session}
                )
                self.update_state(message)
                return message

        except Exception as e:
            error_msg = self.create_error_message(
                content=f"Error updating session: {str(e)}",
                error_data={"error": str(e)}
            )
            self.update_state(error_msg)
            return error_msg

    async def delete_session(self, session_id: str) -> Message:
        """Delete a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Message confirming deletion
        """
        try:
            async with self._get_session_lock(session_id):
                if session_id not in self._sessions:
                    error_msg = self.create_error_message(
                        content=f"Session {session_id} not found",
                        error_data={"session_id": session_id}
                    )
                    self.update_state(error_msg)
                    return error_msg

                del self._sessions[session_id]
                del self._session_locks[session_id]

                message = self.create_message(
                    content=f"Deleted session {session_id}",
                    message_type=MessageType.RESPONSE,
                    status=MessageStatus.SUCCESS
                )
                self.update_state(message)
                return message

        except Exception as e:
            error_msg = self.create_error_message(
                content=f"Error deleting session: {str(e)}",
                error_data={"error": str(e)}
            )
            self.update_state(error_msg)
            return error_msg

    async def cleanup_expired_sessions(self) -> Message:
        """Clean up expired sessions.
        
        Returns:
            Message containing cleanup results
        """
        try:
            now = datetime.now()
            expired_sessions = []
            
            # Find expired sessions
            for session_id, session in self._sessions.items():
                last_active = session["last_active"]
                if isinstance(last_active, str):
                    last_active = datetime.fromisoformat(last_active)
                if now - last_active > timedelta(seconds=self.session_timeout):
                    expired_sessions.append(session_id)
            
            # Delete expired sessions
            for session_id in expired_sessions:
                async with self._get_session_lock(session_id):
                    if session_id in self._sessions:
                        del self._sessions[session_id]
                        del self._session_locks[session_id]
            
            message = self.create_message(
                content=f"Cleaned up {len(expired_sessions)} expired sessions",
                message_type=MessageType.RESPONSE,
                status=MessageStatus.SUCCESS,
                data={"expired_sessions": expired_sessions}
            )
            self.update_state(message)
            return message

        except Exception as e:
            error_msg = self.create_error_message(
                content=f"Error cleaning up sessions: {str(e)}",
                error_data={"error": str(e)}
            )
            self.update_state(error_msg)
            return error_msg

    async def persist_state(self) -> None:
        """Persist the current state."""
        try:
            # Persist all sessions
            for session_id, session in self._sessions.items():
                async with self._get_session_lock(session_id):
                    await self.session_service.save_session(session)
        except Exception as e:
            self.logger.error(f"Error persisting state: {e}")

    async def load_state(self) -> None:
        """Load state from storage."""
        try:
            # Load all sessions
            sessions = await self.session_service.get_all_sessions()
            for session in sessions:
                session_id = session["id"]
                self._sessions[session_id] = session
                self._session_locks[session_id] = asyncio.Lock()
        except Exception as e:
            self.logger.error(f"Error loading state: {e}") 