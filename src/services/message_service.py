import time
import random
import uuid
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client, Client

from src.services.logging_service import get_logger
from src.managers.db_manager import DBService
from src.utils.datetime_utils import format_datetime, parse_datetime, now, timestamp
from src.services.llm_service import LLMService

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
        request_id: Optional[str] = None
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
        logger.debug(f"add_message called with: session_id={session_id}, role={role}, content={content}, metadata={metadata}, user_id={user_id}, sender={sender}, target={target}, request_id={request_id}")
        try:
            # Generate embedding from content using LLM service
            try:
                embedding = await self.llm_service.get_embedding(content)
                logger.debug(f"Generated embedding for message: {len(embedding)} dimensions")
            except Exception as e:
                logger.error(f"Error generating embedding, using default: {e}")
                embedding = [0.0] * 768  # Fallback to default if embedding generation fails
            
            record = {
                "session_id": session_id,
                "content": content,
                "metadata": metadata,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "sender": sender,
                "target": target,
                "embedding_nomic": embedding
            }
            if request_id is not None:
                record["request_id"] = request_id
            logger.debug(f"add_message payload: {record}")
            result = await self.db_service.insert("swarm_messages", record)
            logger.debug(f"add_message DB response: {result}")
            logger.debug(f"Inserted message into swarm_messages: {result}")
            return result
        except Exception as e:
            logger.error(f"Error inserting message into swarm_messages: {e}")
            logger.debug(f"add_message exception details:", exc_info=True)
            raise
    
    async def get_messages(self, 
                   session_id: Union[str, int], 
                   user_id: str = "developer") -> List[Dict[str, Any]]:
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
        result = await self.db_service.get_messages(
            session_id=session_id_int,
            user_id=user_id
        )
        logger.debug(f"get_messages DB response: {result}")
        return result
    
    async def search_messages(self, 
                      query: str,
                      session_id: Optional[Union[str, int]] = None,
                      user_id: str = "developer") -> List[Dict[str, Any]]:
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
        logger.debug(f"search_messages called with: query={query}, session_id={session_id_int}, user_id={user_id}")
        result = await self.db_service.search_messages(
            query=query,
            session_id=session_id_int,
            user_id=user_id
        )
        logger.debug(f"search_messages DB response: {result}")
        return result
    
    async def delete_messages(self, session_id: Union[str, int], user_id: str = "developer") -> bool:
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
            filters = {
                'session_id': session_id,
                'user_id': user_id
            }
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
            'id': message.get('id'),
            'role': message.get('role'),
            'content': message.get('content'),
            'metadata': message.get('metadata', {}),
            'conversation_id': message.get('conversation_id'),
            'timestamp': message.get('created_at') or message.get('metadata', {}).get('timestamp')
        }

    def get_pending_message(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a pending message by request ID."""
        return self._pending_messages.get(request_id)
        
    def clear_pending_message(self, request_id: str) -> None:
        """Clear a pending message by request ID."""
        self._pending_messages.pop(request_id, None)