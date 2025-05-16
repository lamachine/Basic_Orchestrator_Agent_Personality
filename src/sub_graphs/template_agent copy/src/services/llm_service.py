"""
Template Agent LLM Service.

This service provides LLM functionality for the template agent,
inheriting core functionality from the orchestrator's LLM service
but using template-specific prompts and conversation history.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from src.services.llm_service import LLMService as BaseLLMService
from src.state.state_models import MessageRole
from .logging_service import get_logger

logger = get_logger(__name__)

class LLMService(BaseLLMService):
    """
    Template agent LLM service.
    
    This service extends the base LLM service with template-specific
    prompts and conversation history management.
    """
    
    def __init__(self):
        """Initialize the template LLM service."""
        super().__init__()
        self.source_prefix = "template"
        self.conversation_history: List[Dict[str, Any]] = []
        logger.debug("Initialized template LLM service")
    
    async def create_prompt(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a prompt with template-specific context.
        
        Args:
            user_input: The user's input
            context: Optional context information
            
        Returns:
            str: The formatted prompt
        """
        # Add template-specific context
        if context is None:
            context = {}
        
        # Add template-specific system message
        system_message = (
            "You are a template agent, a specialized sub-graph of the main orchestrator. "
            "You have access to specific tools and capabilities defined in your configuration. "
            "Always maintain the context of being a sub-graph and communicate appropriately "
            "with the parent orchestrator when needed."
        )
        
        # Create prompt using base service with template context
        prompt = await super().create_prompt(
            user_input,
            {
                **context,
                "system_message": system_message,
                "source": f"{self.source_prefix}.llm_service"
            }
        )
        
        logger.debug(f"Created prompt with template context: {prompt[:100]}...")
        return prompt
    
    async def process_response(
        self,
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an LLM response with template-specific handling.
        
        Args:
            response: The LLM's response
            context: Optional context information
            
        Returns:
            Dict containing the processed response
        """
        # Add template-specific context
        if context is None:
            context = {}
        
        # Process response using base service
        result = await super().process_response(
            response,
            {
                **context,
                "source": f"{self.source_prefix}.llm_service"
            }
        )
        
        # Update conversation history
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": MessageRole.ASSISTANT,
            "content": response,
            "metadata": {
                "source": f"{self.source_prefix}.llm_service",
                "context": context
            }
        })
        
        logger.debug(f"Processed LLM response: {result.get('status')}")
        return result
    
    def get_conversation_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the template-specific conversation history.
        
        Args:
            limit: Optional limit on number of messages to return
            
        Returns:
            List of conversation messages
        """
        if limit is None:
            return self.conversation_history
        return self.conversation_history[-limit:]
    
    def clear_conversation_history(self) -> None:
        """Clear the template-specific conversation history."""
        self.conversation_history = []
        logger.debug("Cleared template conversation history") 