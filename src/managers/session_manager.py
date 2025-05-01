"""
Session Manager Module

This module implements a session manager for handling user sessions and conversation history.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

from src.managers.db_manager import DBService
from src.services.logging_service import get_logger
from src.services.session_service import SessionService
from src.utils.datetime_utils import format_datetime, parse_datetime, now

# Initialize logger
logger = get_logger(__name__)

class SessionManager:
    def __init__(self, session_service: 'SessionService'):
        self.session_service = session_service
        self.current_session: Optional[SessionState] = None  # Holds the current session state or None if no session is active

    @property
    def session_name(self) -> Optional[str]:
        return self.current_session.name if self.current_session else None

    @property
    def current_session_id(self) -> Optional[str]:
        return self.current_session.session_id if self.current_session else None
    
    async def get_recent_sessions(self, limit: int = 10, user_id: str = "developer"):
        """Get recent sessions from the session service."""
        return await self.session_service.get_recent_sessions(limit=limit, user_id=user_id)

    async def create_session(self, name: Optional[str] = None, user_id: str = "developer") -> str:
        """Create a new session using the session service."""
        session_id = await self.session_service.create_session(name=name, user_id=user_id)
        # Update current session state
        self.current_session = SessionState(
            session_id=str(session_id),
            name=name,
            user_id=user_id
        )
        return session_id

    async def restore_session(self, session_id: Union[str, int], user_id: str = "developer") -> bool:
        """Restore an existing session using the session service."""
        success = await self.session_service.restore_session(session_id=session_id, user_id=user_id)
        if success:
            # Get session info and update current state
            session_info = await self.session_service.get_session_info(session_id)
            self.current_session = SessionState(
                session_id=str(session_id),
                name=session_info.get('name'),
                user_id=user_id,
                messages=session_info.get('messages', [])
            )
        return success

class SessionState:
    """Class representing the state of a session."""
    
    def __init__(self, 
                session_id: Optional[str] = None, 
                name: Optional[str] = None, 
                user_id: str = "developer",
                messages: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize a new session state.
        
        Args:
            session_id: Optional session ID (None for a new session)
            name: Optional session name
            user_id: User ID (default: "developer")
            messages: Optional list of messages
        """
        self.session_id = session_id
        self.name = name
        self.user_id = user_id
        self.messages = messages or []
        self.created_at = now()
        self.updated_at = now()
        self.active = True
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session state to a dictionary.
        
        Returns:
            Dict representation of the session state
        """
        return {
            "session_id": self.session_id,
            "name": self.name,
            "user_id": self.user_id,
            "messages": self.messages,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
            "active": self.active
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """
        Create a session state from a dictionary.
        
        Args:
            data: Dictionary containing session state data
            
        Returns:
            SessionState object
        """
        state = cls(
            session_id=data.get("session_id"),
            name=data.get("name"),
            user_id=data.get("user_id", "developer"),
            messages=data.get("messages", [])
        )
        
        if "created_at" in data:
            state.created_at = parse_datetime(data["created_at"])
            
        if "updated_at" in data:
            state.updated_at = parse_datetime(data["updated_at"])
            
        state.active = data.get("active", True)
        
        return state

