import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from src.managers.db_manager import DBService
from src.services.logging_service import get_logger
from src.state.state_exports import SessionState
from src.utils.datetime_utils import (
    DateTimeEncoder,
    format_datetime,
    now,
    parse_datetime,
    timestamp,
)

logger = get_logger(__name__)


class SessionService:
    """
    Manager for user sessions and conversation history.

    This class provides methods for:
    1. Creating new sessions
    2. Restoring existing sessions
    3. Getting recent sessions
    4. Managing session state and history
    """

    def __init__(self, db_service: DBService):
        """
        Initialize the session manager.

        Args:
            db_manager: Optional database manager instance
        """
        self.db_service = db_service
        self.current_session: Optional[SessionState] = None

    async def get_recent_sessions(
        self, limit: int = 10, user_id: str = "developer"
    ) -> Dict[str, Dict[str, Any]]:
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
                table_name="swarm_messages",
                columns="session_id, metadata, timestamp, user_id",
                order_by="timestamp",
                order_desc=True,
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
                    table_name="swarm_messages",
                    columns="metadata, timestamp, user_id",
                    filters={"session_id": session_id},
                    order_by="timestamp",
                    limit=1,
                )

                if not init_message:
                    continue

                item = init_message[0]

                # Get metadata
                metadata_str = item.get("metadata", "{}")
                try:
                    metadata = (
                        json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                    )
                except json.JSONDecodeError:
                    metadata = {}

                # Get title from metadata
                name = metadata.get("title")

                # Get created timestamp
                timestamp_str = item.get("timestamp")
                created_at = parse_datetime(timestamp_str)

                # Make sure it's timezone-naive
                if created_at and created_at.tzinfo:
                    created_at = created_at.replace(tzinfo=None)

                # Find the most recent message for this session_id
                latest_message = await self.db_service.select(
                    table_name="swarm_messages",
                    columns="timestamp",
                    filters={"session_id": session_id},
                    order_by="timestamp",
                    order_desc=True,
                    limit=1,
                )

                # Set updated_at to the latest message timestamp or created_at as fallback
                if latest_message:
                    updated_at = parse_datetime(latest_message[0].get("timestamp"))
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
                    "user_id": session_user_id,
                }

                # Log for debugging
                logger.debug(
                    f"Found session: ID={session_id}, Name={name}, User={session_user_id}, Updated={updated_at}"
                )

            user_filter_msg = f" for user '{user_id}'" if user_id else ""
            logger.debug(f"Retrieved {len(sessions)} sessions{user_filter_msg}")
            return sessions

        except Exception as e:
            logger.error(f"Error retrieving recent sessions: {e}")
            return {}

    async def list_sessions(self, user_id: str) -> Dict[str, Any]:
        """List last 10 sessions for a user."""
        try:
            response = await self.db_service.select_records(
                "sessions", filters={"user_id": user_id}
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

            # Get the next session ID by finding the max and adding 1
            response = await self.db_service.select(
                table_name="swarm_messages",
                columns="session_id",
                order_by="session_id",
                order_desc=True,
                limit=1,
            )
            next_session_id = (response[0].get("session_id", 0) + 1) if response else 1
            logger.debug(f"Generated next session ID: {next_session_id}")

            now_str = timestamp()
            default_embedding = [0.0] * 768
            metadata = {
                "title": name,
                "created_at": now_str,
                "updated_at": now_str,
                "user_id": user_id,
                "is_session_start": True,
                "role": "system",
            }
            message_data = {
                "session_id": next_session_id,
                "content": "User starting new session",
                "metadata": metadata,
                "user_id": user_id,
                "timestamp": now_str,
                "sender": "system",
                "target": "system",
                "embedding_nomic": default_embedding,
            }
            response = await self.db_service.insert("swarm_messages", message_data)

            if response:
                logger.debug(f"Successfully created session with ID: {next_session_id}")
                return str(next_session_id)
            else:
                logger.error("Failed to create session: No response from DB")
                return None
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return None

    async def continue_session(
        self, session_id: Union[str, int], user_id: str = "developer"
    ) -> Dict[str, Any]:
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

            # Get session details from recent sessions
            sessions = await self.get_recent_sessions(user_id=user_id)
            session = sessions.get(str(session_id))

            if not session:
                logger.error(f"Session {session_id} not found or not accessible by user {user_id}")
                return {}

            # Update the session's last activity timestamp
            now_str = timestamp()

            # Find the system message that contains the session metadata
            init_message = await self.db_service.select(
                table_name="swarm_messages",
                columns="id, metadata",
                filters={"session_id": session_id, "sender": "system"},
                order_by="timestamp",
                limit=1,
            )

            if init_message and len(init_message) > 0:
                message_id = init_message[0].get("id")
                metadata_str = init_message[0].get("metadata", "{}")

                try:
                    current_metadata = (
                        json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                    )
                except json.JSONDecodeError:
                    current_metadata = {}

                # Update the metadata with new timestamp
                current_metadata["updated_at"] = now_str

                # Update the metadata in the database
                await self.db_service.update(
                    table_name="swarm_messages",
                    record_id=message_id,
                    data={"metadata": json.dumps(current_metadata, cls=DateTimeEncoder)},
                    id_column="id",
                )

            logger.debug(f"Continued session with ID: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Error continuing session: {e}")
            return {}

    async def get_session(self, session_id: Union[int, str]) -> Dict[str, Any]:
        """
        Get a session by ID.

        Args:
            session_id: The ID of the session to get

        Returns:
            Dict with session metadata or empty dict if not found
        """
        try:
            # Convert session_id to integer if it's a string
            if isinstance(session_id, str):
                try:
                    session_id = int(session_id)
                except ValueError:
                    pass  # Keep as string if not convertible

            # Use get_recent_sessions but filter for just this ID
            sessions = await self.get_recent_sessions()
            return sessions.get(str(session_id), {})
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return {}

    async def _restore_message_history(self) -> List[Dict[str, Any]]:
        """
        Retrieve and update message history for the current session.

        Returns:
            List of messages for the current session

        Raises:
            RuntimeError: If session is not active
        """
        if not self.current_session or not self.current_session.session_id:
            raise RuntimeError("No active session")
        try:
            # Fetch all messages for the current session using the message manager
            messages = await self.db_service.message_manager.get_messages(
                session_id=self.current_session.session_id,
                user_id=self.current_session.user_id,
            )
            # Update session state
            self.current_session.messages = messages
            return messages
        except Exception as e:
            logger.error(f"Error retrieving message history: {e}")
            return []

    async def search_sessions(
        self, query: str, user_id: str = "developer"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Search for sessions containing a query in title or description.

        Args:
            query: Search query
            user_id: User ID

        Returns:
            Dict of matching sessions keyed by session ID
        """
        try:
            # Fetch all sessions for the user
            sessions = await self.get_recent_sessions(user_id=user_id)

            # Simple case-insensitive search in title or description
            query_lower = query.lower()
            results = {}
            for session_id, session in sessions.items():
                title = (session.get("name") or "").lower()
                description = (session.get("description") or "").lower()
                if query_lower in title or query_lower in description:
                    results[session_id] = session
            logger.debug(
                f"Found {len(results)} sessions matching query '{query}' for user '{user_id}'"
            )
            return results
        except Exception as e:
            logger.error(f"Error searching sessions: {e}")
            return {}

    async def rename_session(self, new_name: str) -> bool:
        """
        Rename the current session.

        Args:
            new_name: New session name

        Returns:
            bool: True if successful

        Raises:
            RuntimeError: If no active session
        """
        if not self.current_session or not self.current_session.session_id:
            raise RuntimeError("No active session")
        try:
            session_id = self.current_session.session_id
            # Find the system message for this session
            init_message = await self.db_service.select(
                table_name="swarm_messages",
                columns="id, metadata",
                filters={"session_id": session_id, "sender": "system"},
                order_by="timestamp",
                limit=1,
            )
            if init_message and len(init_message) > 0:
                message_id = init_message[0].get("id")
                metadata_str = init_message[0].get("metadata", "{}")
                try:
                    current_metadata = (
                        json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                    )
                except json.JSONDecodeError:
                    current_metadata = {}
                # Update the metadata with the new title
                current_metadata["title"] = new_name
                current_metadata["updated_at"] = timestamp()
                # Update the metadata in the database
                await self.db_service.update(
                    table_name="swarm_messages",
                    record_id=message_id,
                    data={"metadata": json.dumps(current_metadata, cls=DateTimeEncoder)},
                    id_column="id",
                )
                # Update session state
                self.current_session.name = new_name
                self.current_session.updated_at = now()
                logger.debug(f"Successfully renamed session {session_id} to '{new_name}'")
                return True
            else:
                logger.error(f"Cannot rename session {session_id}: start message not found")
                return False
        except Exception as e:
            logger.error(f"Error renaming session: {e}")
            return False

    def end_session(self) -> bool:
        """
        End the current session (but don't delete it).

        Returns:
            bool: True if successful
        """
        if not self.current_session:
            # No active session, so nothing to end
            return True

        try:
            # Just clear the current session state
            session_id = self.current_session.session_id
            self.current_session = None

            logger.debug(f"Ended session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False

    async def delete_session(self) -> bool:
        """
        Delete the current session and all its messages.

        Returns:
            bool: True if successful

        Raises:
            RuntimeError: If no active session
        """
        if not self.current_session or not self.current_session.session_id:
            raise RuntimeError("No active session")
        try:
            session_id = self.current_session.session_id
            # Delete all messages for this session
            await self.db_service.delete(
                table_name="swarm_messages", filters={"session_id": session_id}
            )
            # Clear current session
            self.current_session = None
            logger.debug(f"Deleted session and all messages with ID: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False
