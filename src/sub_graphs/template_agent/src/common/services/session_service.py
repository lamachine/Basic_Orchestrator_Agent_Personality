"""
Session Service Module

This module implements session management functionality as a service layer. It provides:
1. Session creation and management
2. Session state persistence
3. Session history tracking
4. Session search capabilities
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..config.base_config import SessionConfig
from ..config.service_config import ServiceConfig
from ..state.state_models import Message, MessageStatus, MessageType
from ..utils.logging_utils import get_logger
from .db_service import DBService

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

    def __init__(self, config: SessionConfig, db_service: Optional[DBService] = None):
        """
        Initialize the session service.

        Args:
            config: Session configuration
            db_service: Optional database service instance
        """
        self.config = config
        self.db_service = db_service
        self._session_dir = Path(config.session_dir)
        self._session_file = self._session_dir / config.session_file

        # Ensure session directory exists
        if not self._session_dir.exists():
            self._session_dir.mkdir(parents=True)

    async def get_recent_sessions(
        self, limit: int = 10, user_id: str = "developer"
    ) -> List[Dict[str, Any]]:
        """
        Get recent sessions with their metadata, optionally filtered by user ID.

        Args:
            limit: Maximum number of sessions to return
            user_id: User ID to filter sessions by

        Returns:
            List of session metadata dictionaries
        """
        try:
            if not self.db_service:
                logger.warning("No DB service available, returning empty list")
                return []

            # Query all system messages to find session starts
            response = await self.db_service.select(
                table_name="messages",
                columns="session_id, metadata, created_at, user_id",
                order_by="created_at",
                order_desc=True,
            )

            sessions = []
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
                    limit=1,
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
                    limit=1,
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

                sessions.append(
                    {
                        "id": session_id,
                        "name": name,
                        "description": metadata.get("description", ""),
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "user_id": session_user_id,
                    }
                )

                # Log for debugging
                logger.debug(
                    f"Found session: ID={session_id}, Name={name}, User={session_user_id}, Updated={updated_at}"
                )

            user_filter_msg = f" for user '{user_id}'" if user_id else ""
            logger.debug(f"Retrieved {len(sessions)} sessions{user_filter_msg}")
            return sessions

        except Exception as e:
            logger.error(f"Error retrieving recent sessions: {e}")
            return []

    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all sessions.

        Returns:
            List of all session metadata dictionaries
        """
        try:
            if not self.db_service:
                logger.warning("No DB service available, returning empty list")
                return []

            response = await self.db_service.select(
                table_name="sessions", order_by="created_at", order_desc=True
            )

            return response if response else []

        except Exception as e:
            logger.error(f"Error getting all sessions: {e}")
            return []

    async def save_session(self, session: Dict[str, Any]) -> bool:
        """
        Save session data.

        Args:
            session: Session data to save

        Returns:
            bool: Success status
        """
        try:
            if not self.db_service:
                logger.warning("No DB service available, returning False")
                return False

            # Update or insert session
            await self.db_service.upsert(table_name="sessions", data=session, unique_columns=["id"])

            logger.debug(f"Saved session {session.get('id')}")
            return True

        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return False

    async def delete_session(self, session_id: Union[str, int]) -> bool:
        """
        Delete a session and all its messages.

        Args:
            session_id: Session ID to delete

        Returns:
            bool: Success status
        """
        try:
            if not self.db_service:
                logger.warning("No DB service available, returning False")
                return False

            # Delete all messages
            await self.db_service.delete_records("messages", {"session_id": session_id})

            # Delete session
            await self.db_service.delete_records("sessions", {"id": session_id})

            logger.debug(f"Deleted session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

    async def search_sessions(self, query: str, user_id: str = "developer") -> List[Dict[str, Any]]:
        """
        Search sessions by name or description.

        Args:
            query: Search query
            user_id: User ID to filter by

        Returns:
            List of matching session metadata dictionaries
        """
        try:
            if not self.db_service:
                logger.warning("No DB service available, returning empty list")
                return []

            # Get all sessions for user
            sessions = await self.get_recent_sessions(limit=100, user_id=user_id)

            # Filter by query
            matches = []
            query = query.lower()
            for session in sessions:
                if (
                    query in session["name"].lower()
                    or query in session.get("description", "").lower()
                ):
                    matches.append(session)

            return matches

        except Exception as e:
            logger.error(f"Error searching sessions: {e}")
            return []

    async def rename_session(self, session_id: Union[str, int], new_name: str) -> bool:
        """
        Rename a session.

        Args:
            session_id: Session ID to rename
            new_name: New name for session

        Returns:
            bool: Success status
        """
        try:
            if not self.db_service:
                logger.warning("No DB service available, returning False")
                return False

            # Update session name
            await self.db_service.update(
                "sessions",
                {"name": new_name, "updated_at": datetime.now().isoformat()},
                {"id": session_id},
            )

            # Update metadata in first message
            messages = await self.db_service.select(
                "messages",
                filters={"session_id": session_id},
                order_by="created_at",
                limit=1,
            )

            if messages:
                message = messages[0]
                metadata = message.get("metadata", {})
                metadata["title"] = new_name

                await self.db_service.update(
                    "messages", {"metadata": metadata}, {"id": message["id"]}
                )

            logger.debug(f"Renamed session {session_id} to {new_name}")
            return True

        except Exception as e:
            logger.error(f"Error renaming session: {e}")
            return False
