import random
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
from supabase import Client, create_client

from src.managers.db_manager import DBService
from src.services.llm_service import LLMService
from src.services.logging_service import get_logger
from src.state.state_models import MessageRole
from src.utils.datetime_utils import format_datetime, now, parse_datetime, timestamp

logger = get_logger(__name__)


class DatabaseMessageService:
    """
    Service for managing messages in the database.
    """

    def __init__(self, db_service: DBService):
        """
        Initialize the message service.

        Args:
            db_service: Database service instance
        """
        self.db_service = db_service
        self._error_count = 0
        self._pending_messages: Dict[str, Dict[str, Any]] = {}
        self.llm_service = LLMService()  # Initialize LLM service for embeddings

    def get_next_uuid(self) -> str:
        """Generate a unique UUID for request tracking."""
        try:
            return str(uuid.uuid4())
        except Exception as e:
            logger.error(f"Error generating UUID: {e}")
            self._error_count += 1
            return f"id-{int(time.time())}-{random.randint(1000, 9999)}"

    async def add_message(
        self,
        session_id: Union[str, int],
        role: str,
        content: str,
        metadata: Dict[str, Any],
        user_id: str,
        sender: str,
        target: str,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a message to the swarm_messages table.
        Args:
            session_id: Session ID
            role: Message role (user, assistant, etc)
            content: Message content
            metadata: Metadata dict
            user_id: User ID
            sender: Sender identifier (required)
            target: Target identifier (required)
            request_id: Optional request ID (for tool requests)
        Returns:
            The inserted record dict
        Raises:
            RuntimeError if insert fails
        """
        logger.debug(
            f"add_message called with: session_id={session_id}, role={role}, content={content}, metadata={metadata}, user_id={user_id}, sender={sender}, target={target}, request_id={request_id}"
        )
        try:
            # Generate embedding from content using LLM service
            try:
                embedding = await self.llm_service.get_embedding(content)
                logger.debug(f"Generated embedding for message: {len(embedding)} dimensions")
            except Exception as e:
                logger.error(f"Error generating embedding, using default: {e}")
                embedding = [0.0] * 768  # Fallback to default if embedding generation fails

            # Add user_id and character_name to metadata
            metadata = metadata.copy() if metadata else {}
            metadata["user_id"] = user_id
            if role == "assistant":
                metadata["character_name"] = target
            elif role == "user":
                metadata["user_id"] = user_id

            record = {
                "session_id": session_id,
                "content": content,
                "metadata": metadata,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "sender": sender,
                "target": target,
                "embedding_nomic": embedding,
            }
            if request_id is not None:
                record["request_id"] = request_id
            # logger.debug(f"add_message payload: {record}")
            result = await self.db_service.insert("swarm_messages", record)
            logger.debug(f"add_message DB response: {result}")
            # logger.debug(f"Inserted message into swarm_messages: {result}")
            return result
        except Exception as e:
            logger.error(f"Error inserting message into swarm_messages: {e}")
            logger.debug(f"add_message exception details:", exc_info=True)
            raise

    async def get_messages(
        self, session_id: Union[str, int], user_id: str = "developer"
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation.

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            List of messages
        """
        # Ensure session_id is an integer
        session_id_int = int(session_id) if isinstance(session_id, str) else session_id
        logger.debug(f"get_messages called with: session_id={session_id_int}, user_id={user_id}")
        result = await self.db_service.get_messages(session_id=session_id_int, user_id=user_id)
        logger.debug(f"get_messages DB response: {result}")
        return result

    async def search_messages(
        self,
        query: str,
        session_id: Optional[Union[str, int]] = None,
        user_id: str = "developer",
    ) -> List[Dict[str, Any]]:
        """
        Search for messages containing a query.

        Args:
            query: Search query
            session_id: Optional session ID filter
            user_id: User ID

        Returns:
            List of matching messages
        """
        # Convert session_id to int if provided
        session_id_int = None
        if session_id is not None:
            session_id_int = int(session_id) if isinstance(session_id, str) else session_id
        logger.debug(
            f"search_messages called with: query={query}, session_id={session_id_int}, user_id={user_id}"
        )
        result = await self.db_service.search_messages(
            query=query, session_id=session_id_int, user_id=user_id
        )
        logger.debug(f"search_messages DB response: {result}")
        return result

    async def delete_messages(
        self, session_id: Union[str, int], user_id: str = "developer"
    ) -> bool:
        """
        Delete all messages for a session.
        Args:
            session_id: Session ID
            user_id: User ID
        Returns:
            bool: Success status
        """
        logger.debug(f"delete_messages called with: session_id={session_id}, user_id={user_id}")
        try:
            filters = {"session_id": session_id, "user_id": user_id}
            logger.debug(f"delete_messages filters: {filters}")
            result = await self.db_service.delete_records("swarm_messages", filters)
            logger.debug(f"delete_messages DB response: {result}")
            logger.debug(f"Deleted messages for session {session_id}, user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting messages: {e}")
            logger.debug(f"delete_messages exception details:", exc_info=True)
            return False

    def _format_message_standard(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a message in the standard format.

        Args:
            message: Raw message from database

        Returns:
            Formatted message
        """
        return {
            "id": message.get("id"),
            "role": message.get("role"),
            "content": message.get("content"),
            "metadata": message.get("metadata", {}),
            "conversation_id": message.get("conversation_id"),
            "timestamp": message.get("created_at") or message.get("metadata", {}).get("timestamp"),
        }

    def get_pending_message(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a pending message by request ID."""
        return self._pending_messages.get(request_id)

    def clear_pending_message(self, request_id: str) -> None:
        """Clear a pending message by request ID."""
        self._pending_messages.pop(request_id, None)


# DRY message logging utility - lazily import MessageState to avoid circular imports
from src.state.state_models import MessageState


async def log_and_persist_message(
    session_state: MessageState,
    role: MessageRole,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    sender: Optional[str] = None,
    target: Optional[str] = None,
) -> None:
    """
    Log and persist a message using the session state.

    Args:
        session_state: MessageState instance
        role: Message role
        content: Message content
        metadata: Optional metadata
        sender: Optional sender identifier
        target: Optional target identifier
    """
    logger.debug(f"[log_and_persist_message] Starting with:")
    logger.debug(f"[log_and_persist_message] session_state type: {type(session_state)}")
    logger.debug(f"[log_and_persist_message] role: {role}")
    logger.debug(f"[log_and_persist_message] content length: {len(content)}")
    logger.debug(f"[log_and_persist_message] metadata: {metadata}")
    logger.debug(f"[log_and_persist_message] sender: {sender}")
    logger.debug(f"[log_and_persist_message] target: {target}")

    try:
        if not isinstance(session_state, MessageState):
            logger.error(
                f"[log_and_persist_message] Invalid session_state type: {type(session_state)}"
            )
            raise TypeError(f"session_state must be MessageState, got {type(session_state)}")

        if not sender or not target:
            logger.error(
                f"[log_and_persist_message] Missing sender or target: sender={sender}, target={target}"
            )
            raise ValueError("Both sender and target must be provided")

        # Add user_id and character_name to metadata
        metadata = metadata.copy() if metadata else {}
        if role == MessageRole.USER:
            metadata["user_id"] = "user"  # Default user ID
            logger.debug(f"[log_and_persist_message] Added user_id to metadata: {metadata}")
        elif role == MessageRole.ASSISTANT:
            metadata["character_name"] = "Assistant"  # Default character name
            logger.debug(f"[log_and_persist_message] Added default character_name: Assistant")

        logger.debug(f"[log_and_persist_message] Final metadata: {metadata}")
        logger.debug(f"[log_and_persist_message] Calling add_message on MessageState")

        # Use the add_message method directly on the MessageState object
        await session_state.add_message(
            role=role,
            content=content,
            metadata=metadata or {},
            sender=sender,
            target=target,
        )
        logger.debug("[log_and_persist_message] Successfully added message")

    except Exception as e:
        logger.error(f"[log_and_persist_message] Error: {str(e)}", exc_info=True)
        raise


# Export only what's needed
__all__ = ["DatabaseMessageService", "log_and_persist_message"]
