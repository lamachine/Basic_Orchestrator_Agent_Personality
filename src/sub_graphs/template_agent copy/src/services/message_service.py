"""
Template Agent Message Service.

This module provides the message service for the template agent,
inheriting core functionality from the orchestrator's message service
but adding template-specific message handling.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from src.services.message_service import DatabaseMessageService as BaseMessageService
from src.state.state_models import MessageRole

from ..services.logging_service import get_logger

logger = get_logger(__name__)

class MessageService(BaseMessageService):
    """
    Template agent message service.
    
    This class extends the orchestrator's message service with template-specific
    functionality and validation.
    """
    
    def __init__(self, db_service):
        """
        Initialize the template message service.
        
        Args:
            db_service: Database service instance
        """
        super().__init__(db_service)
        logger.debug("Initialized template message service")
    
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
        Add a message with template-specific handling.
        
        Args:
            session_id: Session ID
            role: Message role
            content: Message content
            metadata: Message metadata
            user_id: User ID
            sender: Sender identifier
            target: Target identifier
            request_id: Optional request ID
            
        Returns:
            The inserted record dict
        """
        # Add template-specific metadata
        if metadata is None:
            metadata = {}
        metadata['source'] = 'template'
        
        # Add message using base service
        result = await super().add_message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
            user_id=user_id,
            sender=sender,
            target=target,
            request_id=request_id
        )
        
        logger.debug(f"Added template message: {result}")
        return result

    async def create_message(
        self,
        content: str,
        role: MessageRole,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a message with template-specific source/target.
        
        Args:
            content: The message content
            role: The message role
            metadata: Optional message metadata
            
        Returns:
            Dict containing the created message
        """
        # Add template-specific source/target to metadata
        if metadata is None:
            metadata = {}
        
        # Update source/target with template prefix
        if 'sender' in metadata:
            metadata['sender'] = f"{self.source_prefix}.{metadata['sender']}"
        if 'target' in metadata:
            metadata['target'] = f"{self.source_prefix}.{metadata['target']}"
            
        # Create message using base service
        message = await super().create_message(content, role, metadata)
        
        # Log message creation
        logger.debug(
            f"Created message: {message.get('id')} "
            f"from {metadata.get('sender', 'unknown')} "
            f"to {metadata.get('target', 'unknown')}"
        )
        
        return message
    
    async def process_message(
        self,
        message: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message with template-specific handling.
        
        Args:
            message: The message to process
            state: Optional state information
            
        Returns:
            Dict containing the processing result
        """
        # Log message processing
        logger.debug(
            f"Processing message: {message.get('id')} "
            f"from {message.get('metadata', {}).get('sender', 'unknown')} "
            f"to {message.get('metadata', {}).get('target', 'unknown')}"
        )
        
        # Process message using base service
        result = await super().process_message(message, state)
        
        # Log processing result
        logger.debug(f"Message processing result: {result.get('status')}")
        
        return result 