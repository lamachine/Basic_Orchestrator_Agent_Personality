"""
Template Agent Message Manager.

This manager handles message routing for the template agent,
inheriting core functionality from the orchestrator's message manager
but adding template-specific message handling and routing.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from src.managers.message_manager import MessageManager as BaseMessageManager
from src.state.state_models import MessageRole
from ..services.logging_service import get_logger

logger = get_logger(__name__)

class MessageManager(BaseMessageManager):
    """
    Template agent message manager.
    
    This manager extends the base message manager with template-specific
    message handling and routing.
    """
    
    def __init__(self):
        """Initialize the template message manager."""
        super().__init__()
        self.source_prefix = "template"
        self._message_history: List[Dict[str, Any]] = []
        logger.debug("Initialized template message manager")
    
    async def route_message(
        self,
        message: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route a message with template-specific handling.
        
        Args:
            message: The message to route
            context: Optional context information
            
        Returns:
            Dict containing the routing result
        """
        # Add template-specific context
        if context is None:
            context = {}
        
        # Add template-specific metadata
        message["metadata"] = {
            **(message.get("metadata", {})),
            "source": f"{self.source_prefix}.message_manager"
        }
        
        # Track message
        self._message_history.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "context": context
        })
        
        # Route message using base manager
        result = await super().route_message(
            message,
            {
                **context,
                "source": f"{self.source_prefix}.message_manager"
            }
        )
        
        logger.debug(
            f"Routed message from {message.get('source')} "
            f"to {message.get('target')}"
        )
        return result
    
    async def handle_message(
        self,
        message: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle a message with template-specific processing.
        
        Args:
            message: The message to handle
            context: Optional context information
            
        Returns:
            Dict containing the handling result
        """
        # Add template-specific context
        if context is None:
            context = {}
        
        # Add template-specific metadata
        message["metadata"] = {
            **(message.get("metadata", {})),
            "source": f"{self.source_prefix}.message_manager"
        }
        
        # Handle message using base manager
        result = await super().handle_message(
            message,
            {
                **context,
                "source": f"{self.source_prefix}.message_manager"
            }
        )
        
        logger.debug(
            f"Handled message from {message.get('source')} "
            f"to {message.get('target')}"
        )
        return result
    
    def get_message_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get template-specific message history.
        
        Args:
            limit: Optional limit on number of messages to return
            
        Returns:
            List of messages
        """
        if limit is None:
            return self._message_history
        return self._message_history[-limit:]
    
    def clear_message_history(self) -> None:
        """Clear the template-specific message history."""
        self._message_history = []
        logger.debug("Cleared template message history") 