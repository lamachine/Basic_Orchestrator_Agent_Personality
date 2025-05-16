"""
Message Service Module

This module implements message management functionality as a service layer. It provides:
1. Message creation and storage
2. Message retrieval and search
3. Message formatting and standardization
4. Message persistence and logging
"""

import time
import random
import uuid
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime

from .logging_service import get_logger
from .db_service import DBService
from .llm_service import LLMService
from ..models.state_models import Message, MessageType, MessageStatus
from ..models.service_models import ServiceConfig

logger = get_logger(__name__)

class MessageService:
    """
    Service for managing messages in the database.
    
    This class provides methods for:
    1. Adding messages to the database
    2. Retrieving messages for a session
    3. Searching messages
    4. Deleting messages
    5. Managing pending messages
    """
    
    def __init__(self, config: ServiceConfig, db_service: Optional[DBService] = None, llm_service: Optional[LLMService] = None):
        """
        Initialize the message service.

        Args:
            config: Service configuration
            db_service: Optional database service instance
            llm_service: Optional LLM service instance
        """
        self.config = config
        self.db_service = db_service
        self.llm_service = llm_service
        self._error_count = 0
        self._pending_messages: Dict[str, Dict[str, Any]] = {}
        
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
        message: Message,
        user_id: str,
        sender: str,
        target: str
    ) -> Dict[str, Any]:
        """
        Add a message to the swarm_messages table.
        
        Args:
            session_id: Session ID
            message: Message to add
            user_id: User ID
            sender: Sender identifier
            target: Target identifier
            
        Returns:
            The inserted record dict
            
        Raises:
            RuntimeError if insert fails
        """
        logger.debug(f"add_message called with: session_id={session_id}, message={message}, user_id={user_id}, sender={sender}, target={target}")
        try:
            # Generate embedding from content using LLM service
            try:
                if self.llm_service:
                    embedding = await self.llm_service.get_embedding(message.content)
                    logger.debug(f"Generated embedding for message: {len(embedding)} dimensions")
                else:
                    embedding = [0.0] * 768  # Default embedding if no LLM service
            except Exception as e:
                logger.error(f"Error generating embedding, using default: {e}")
                embedding = [0.0] * 768  # Fallback to default if embedding generation fails
            
            # Add user_id and character_name to metadata
            metadata = message.metadata.copy() if message.metadata else {}
            metadata['user_id'] = user_id
            if message.type == MessageType.RESPONSE:
                metadata['character_name'] = target
            elif message.type == MessageType.REQUEST:
                metadata['user_id'] = user_id
            
            record = {
                "session_id": session_id,
                "content": message.content,
                "metadata": metadata,
                "user_id": user_id,
                "timestamp": message.timestamp.isoformat(),
                "sender": sender,
                "target": target,
                "embedding_nomic": embedding,
                "request_id": message.request_id,
                "parent_request_id": message.parent_request_id,
                "type": message.type,
                "status": message.status
            }
                
            if self.db_service:
                result = await self.db_service.insert("swarm_messages", record)
                logger.debug(f"add_message DB response: {result}")
                return result
            else:
                logger.warning("No DB service available, returning record without persistence")
                return record
            
        except Exception as e:
            logger.error(f"Error inserting message into swarm_messages: {e}")
            logger.debug(f"add_message exception details:", exc_info=True)
            raise
    
    async def get_messages(self, 
                   session_id: Union[str, int], 
                   user_id: str = "developer") -> List[Message]:
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
        
        if not self.db_service:
            logger.warning("No DB service available, returning empty list")
            return []
            
        result = await self.db_service.get_messages(
            session_id=session_id_int,
            user_id=user_id
        )
        logger.debug(f"get_messages DB response: {result}")
        
        # Convert DB records to Message objects
        messages = []
        for record in result:
            message = Message(
                request_id=record.get("request_id"),
                parent_request_id=record.get("parent_request_id"),
                type=record.get("type", MessageType.REQUEST),
                status=record.get("status", MessageStatus.PENDING),
                timestamp=datetime.fromisoformat(record.get("timestamp")),
                content=record.get("content", ""),
                data=record.get("data", {}),
                metadata=record.get("metadata", {})
            )
            messages.append(message)
            
        return messages
    
    async def search_messages(self, 
                      query: str,
                      session_id: Optional[Union[str, int]] = None,
                      user_id: str = "developer") -> List[Message]:
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
        
        if not self.db_service:
            logger.warning("No DB service available, returning empty list")
            return []
            
        result = await self.db_service.search_messages(
            query=query,
            session_id=session_id_int,
            user_id=user_id
        )
        logger.debug(f"search_messages DB response: {result}")
        
        # Convert DB records to Message objects
        messages = []
        for record in result:
            message = Message(
                request_id=record.get("request_id"),
                parent_request_id=record.get("parent_request_id"),
                type=record.get("type", MessageType.REQUEST),
                status=record.get("status", MessageStatus.PENDING),
                timestamp=datetime.fromisoformat(record.get("timestamp")),
                content=record.get("content", ""),
                data=record.get("data", {}),
                metadata=record.get("metadata", {})
            )
            messages.append(message)
            
        return messages
    
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
        
        if not self.db_service:
            logger.warning("No DB service available, returning False")
            return False
            
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
            return False

    def get_pending_message(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a pending message by request ID."""
        return self._pending_messages.get(request_id)

    def clear_pending_message(self, request_id: str) -> None:
        """Clear a pending message by request ID."""
        self._pending_messages.pop(request_id, None)

async def log_and_persist_message(
    session_state: MessageState,
    role: MessageRole,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    sender: Optional[str] = None,
    target: Optional[str] = None
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
            logger.error(f"[log_and_persist_message] Invalid session_state type: {type(session_state)}")
            raise TypeError(f"session_state must be MessageState, got {type(session_state)}")
            
        if not sender or not target:
            logger.error(f"[log_and_persist_message] Missing sender or target: sender={sender}, target={target}")
            raise ValueError("Both sender and target must be provided")
            
        # Add message to session state
        session_state.add_message(role, content, metadata)
        
        # Persist message to database
        await session_state.message_service.add_message(
            session_id=session_state.id,
            role=role.value,
            content=content,
            metadata=metadata or {},
            user_id=session_state.user_id,
            sender=sender,
            target=target
        )
        
    except Exception as e:
        logger.error(f"[log_and_persist_message] Error: {e}")
        logger.debug(f"[log_and_persist_message] Exception details:", exc_info=True)
        raise 