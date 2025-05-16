"""
Session Service Module

This module implements session management functionality as a service layer. It provides:
1. Session creation and management
2. Session state persistence
3. Session history tracking
4. Session search capabilities
"""

import os
import json
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime

from .logging_service import get_logger
from .db_service import DBService
from ..models.state_models import Message, MessageType, MessageStatus
from ..models.service_models import SessionServiceConfig

logger = get_logger(__name__)

class SessionService:
    """
    Service for managing user sessions and conversation history.
    
    This class provides methods for:
    1. Creating new sessions
    2. Restoring existing sessions
    3. Getting recent sessions
    4. Managing session state and history
    """
    
    def __init__(self, config: SessionServiceConfig, db_service: DBService):
        """
        Initialize the session service.
        
        Args:
            config: Session service configuration
            db_service: Database service instance
        """
        self.config = config
        self.db_service = db_service
        self.current_session: Optional[str] = None
        
    async def get_recent_sessions(self, limit: int = 10, user_id: str = "developer") -> Dict[str, Dict[str, Any]]:
        """
        Get recent sessions with their metadata, optionally filtered by user ID.
        
        Args:
            limit: Maximum number of sessions to return
            user_id: User ID to filter sessions by
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping session IDs to session metadata
        """
        try:
            # Query all system messages to find session starts
            response = await self.db_service.select(
                table_name="messages",
                columns="session_id, metadata, created_at, user_id",
                order_by="created_at",
                order_desc=True
            )
            
            sessions = {}
            # First pass - collect all unique session IDs
            unique_sessions = set()
            for item in response:
                session_id = item.get("session_id")
                if session_id and session_id not in unique_sessions:
                    unique_sessions.add(session_id)
                    
                    if len(unique_sessions) >= limit:
                        break
            
            # Process each unique session
            for session_id in unique_sessions:
                # Find the first message (likely system) for this session
                init_message = await self.db_service.select(
                    table_name="messages",
                    columns="metadata, created_at, user_id",
                    filters={"session_id": session_id},
                    order_by="created_at",
                    limit=1
                )
                
                if not init_message:
                    continue
                    
                item = init_message[0]
                
                # Get metadata
                metadata = item.get("metadata", {})
                
                # Get title from metadata
                name = metadata.get("title")
                
                # Get created timestamp
                created_at = item.get("created_at")
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                # Make sure it's timezone-naive
                if created_at and created_at.tzinfo:
                    created_at = created_at.replace(tzinfo=None)
                
                # Find the most recent message for this session_id
                latest_message = await self.db_service.select(
                    table_name="messages",
                    columns="created_at",
                    filters={"session_id": session_id},
                    order_by="created_at",
                    order_desc=True,
                    limit=1
                )
                
                # Set updated_at to the latest message timestamp or created_at as fallback
                if latest_message:
                    updated_at = latest_message[0].get("created_at")
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at)
                    # Make sure it's timezone-naive
                    if updated_at and updated_at.tzinfo:
                        updated_at = updated_at.replace(tzinfo=None)
                else:
                    updated_at = created_at
                
                # Get user ID from item or metadata
                item_user_id = item.get("user_id", "developer")
                metadata_user_id = metadata.get("user_id")
                session_user_id = metadata_user_id or item_user_id
                
                # Skip if filtering by user_id and this session doesn't belong to the user
                if user_id and session_user_id != user_id:
                    continue
                
                sessions[str(session_id)] = {
                    "id": session_id,
                    "name": name,
                    "description": metadata.get("description", ""),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "user_id": session_user_id
                }
                
                # Log for debugging
                logger.debug(f"Found session: ID={session_id}, Name={name}, User={session_user_id}, Updated={updated_at}")
            
            user_filter_msg = f" for user '{user_id}'" if user_id else ""
            logger.debug(f"Retrieved {len(sessions)} sessions{user_filter_msg}")
            return sessions
            
        except Exception as e:
            logger.error(f"Error retrieving recent sessions: {e}")
            return {}

    async def list_sessions(self, user_id: str) -> Dict[str, Any]:
        """
        List last 10 sessions for a user.
        
        Args:
            user_id: User ID to filter sessions by
            
        Returns:
            Dict[str, Any]: Dictionary of sessions
        """
        try:
            response = await self.db_service.select(
                "sessions",
                filters={"user_id": user_id},
                limit=10
            )
            return {str(session["id"]): session for session in response} if response else {}
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return {}

    async def create_session(self, user_id: str, name: Optional[str] = None) -> Optional[str]:
        """
        Create a new session with initial system message.
        
        Args:
            user_id: The user ID for this session
            name: Optional name for the session
            
        Returns:
            Optional[str]: The session ID if successful, None otherwise
        """
        try:
            if not user_id:
                user_id = "developer"
            
            # Get the next session ID
            next_session_id = await self.db_service.get_next_id("id", "sessions")
            logger.debug(f"Generated next session ID: {next_session_id}")
            
            # Create session record
            session_data = {
                "id": next_session_id,
                "name": name or f"Session {next_session_id}",
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            await self.db_service.insert("sessions", session_data)
            
            # Create initial system message
            message = Message(
                id=await self.db_service.get_next_id("id", "messages"),
                type=MessageType.SYSTEM,
                content="User starting new session",
                status=MessageStatus.COMPLETED,
                metadata={
                    "title": name,
                    "is_session_start": True
                },
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Convert message to dict for DB
            message_data = {
                "id": message.id,
                "session_id": next_session_id,
                "type": message.type.value,
                "content": message.content,
                "status": message.status.value,
                "metadata": message.metadata,
                "user_id": user_id,
                "created_at": message.created_at.isoformat(),
                "updated_at": message.updated_at.isoformat()
            }
            
            await self.db_service.insert("messages", message_data)
            
            logger.debug(f"Successfully created session with ID: {next_session_id}")
            return str(next_session_id)
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return None

    async def continue_session(self, session_id: Union[str, int], user_id: str = "developer") -> Dict[str, Any]:
        """
        Continue an existing session. Verifies it exists and returns metadata.
        
        Args:
            session_id: The session ID to continue
            user_id: The user ID requesting the session
            
        Returns:
            Dict[str, Any]: Session metadata or empty dict if not found/accessible
        """
        try:
            # Convert session_id to integer if appropriate
            if isinstance(session_id, str):
                try:
                    session_id = int(session_id)
                except ValueError:
                    pass  # Keep as string if not convertible
                    
            # Get session details
            session = await self.db_service.select(
                "sessions",
                filters={"id": session_id}
            )
            
            if not session:
                logger.warning(f"Session {session_id} not found")
                return {}
                
            session = session[0]
            
            # Check if user has access
            if session.get("user_id") != user_id:
                logger.warning(f"User {user_id} does not have access to session {session_id}")
                return {}
                
            # Update last accessed time
            await self.db_service.update(
                "sessions",
                {"updated_at": datetime.now().isoformat()},
                {"id": session_id}
            )
            
            # Set as current session
            self.current_session = str(session_id)
            
            return session
            
        except Exception as e:
            logger.error(f"Error continuing session: {e}")
            return {}

    async def get_session(self, session_id: Union[int, str]) -> Dict[str, Any]:
        """
        Get session details.
        
        Args:
            session_id: Session ID to get
            
        Returns:
            Dict[str, Any]: Session details or empty dict if not found
        """
        try:
            response = await self.db_service.select(
                "sessions",
                filters={"id": session_id}
            )
            return response[0] if response else {}
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return {}

    async def search_sessions(self, query: str, user_id: str = "developer") -> Dict[str, Dict[str, Any]]:
        """
        Search sessions by name or description.
        
        Args:
            query: Search query
            user_id: User ID to filter by
            
        Returns:
            Dict[str, Dict[str, Any]]: Matching sessions
        """
        try:
            # Get all sessions for user
            sessions = await self.get_recent_sessions(limit=100, user_id=user_id)
            
            # Filter by query
            matches = {}
            query = query.lower()
            for session_id, session in sessions.items():
                if (query in session["name"].lower() or 
                    query in session.get("description", "").lower()):
                    matches[session_id] = session
                    
            return matches
            
        except Exception as e:
            logger.error(f"Error searching sessions: {e}")
            return {}

    async def rename_session(self, session_id: Union[str, int], new_name: str) -> bool:
        """
        Rename a session.
        
        Args:
            session_id: Session ID to rename
            new_name: New name for session
            
        Returns:
            bool: True if successful
        """
        try:
            # Update session name
            await self.db_service.update(
                "sessions",
                {"name": new_name, "updated_at": datetime.now().isoformat()},
                {"id": session_id}
            )
            
            # Update metadata in first message
            messages = await self.db_service.select(
                "messages",
                filters={"session_id": session_id},
                order_by="created_at",
                limit=1
            )
            
            if messages:
                message = messages[0]
                metadata = message.get("metadata", {})
                metadata["title"] = new_name
                
                await self.db_service.update(
                    "messages",
                    {"metadata": metadata},
                    {"id": message["id"]}
                )
                
            return True
            
        except Exception as e:
            logger.error(f"Error renaming session: {e}")
            return False

    def end_session(self) -> bool:
        """
        End the current session.
        
        Returns:
            bool: True if successful
        """
        try:
            if not self.current_session:
                return True
                
            self.current_session = None
            return True
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False

    async def delete_session(self, session_id: Union[str, int]) -> bool:
        """
        Delete a session and all its messages.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            bool: True if successful
        """
        try:
            # Delete all messages
            await self.db_service.delete_records(
                "messages",
                {"session_id": session_id}
            )
            
            # Delete session
            await self.db_service.delete_records(
                "sessions",
                {"id": session_id}
            )
            
            # Clear current session if it was this one
            if self.current_session == str(session_id):
                self.current_session = None
                
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False 