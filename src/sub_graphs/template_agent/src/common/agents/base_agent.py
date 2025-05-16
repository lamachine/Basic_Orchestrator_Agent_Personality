"""
Base Agent - Core functionality for all agent types.

This module provides the BaseAgent class which serves as the foundation for all
specialized agents in the system. It implements core functionality needed by any agent:

1. Configuration Management - Loading and validating agent settings
2. Database Integration - Connecting to and querying persistent storage
3. Conversation Management - Tracking and updating conversation state 
4. Session Handling - Managing unique user sessions and context
5. Tool Registration - Standardized interface for tool discovery and execution
6. Error Handling - Common error handling and logging patterns
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from ...common.messages.message_models import Message, MessageType, MessageStatus
from ...common.tools.tool_registry import ToolRegistry
from ...common.services.llm_service import LLMService
from ...common.services.logging_service import get_logger
from ...common.state.state_models import MessageRole

logger = get_logger(__name__)

class BaseAgentConfig(BaseModel):
    """Configuration for base agent using Pydantic."""
    name: str
    prompt_section: str = ""
    api_url: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    user_id: Optional[str] = None
    enable_history: bool = True
    enable_logging: bool = True
    graph_name: str = "unknown"

    def __init__(self, **data):
        super().__init__(**data)
        if self.user_id is None:
            self.user_id = "developer"
        if self.max_tokens is None:
            self.max_tokens = 2000
        if self.context_window is None:
            self.context_window = 4096

class BaseAgent:
    """Base class for all agents, encapsulating core functionality."""
    
    def __init__(self, config: BaseAgentConfig):
        """Initialize with validated config."""
        self.config = config
        self.name = config.name
        self.logger = get_logger(f"agent.{config.name}")
        self.tool_registry = ToolRegistry()
        
        # Initialize LLM service if configured
        if config.api_url and config.model:
            self.logger.debug(f"Initializing LLM service for {config.name}")
            self.llm = LLMService.get_instance(
                api_url=config.api_url, 
                model=config.model,
                max_tokens=config.max_tokens
            )
        else:
            self.llm = None
            self.logger.warning(f"LLM service not initialized in {config.name}")

        # Initialize conversation tracking
        self.conversation_history = [] if config.enable_history else None

    @property
    def model(self) -> str:
        """Get the model name."""
        return self.config.model

    async def query_llm(self, prompt: str) -> str:
        """
        Basic LLM query with error handling.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            str: LLM response or error message
        """
        if not self.llm:
            return "Error: LLM service not initialized"
            
        try:
            return await self.llm.generate(prompt)
        except Exception as e:
            self.logger.error(f"Error querying LLM: {e}")
            return f"Error: {str(e)}" 

    async def create_message(
        self,
        content: str,
        type: MessageType,
        parent_message: Optional[Message] = None,
        **kwargs
    ) -> Message:
        """Create a new message with proper context."""
        message_data = {
            "content": content,
            "type": type,
            "metadata": {
                "agent_name": self.name,
                "graph_name": self.config.graph_name,
                "model": self.config.model
            },
            **kwargs
        }
        
        if parent_message:
            message_data["parent_request_id"] = parent_message.request_id
            message_data["metadata"].update({
                "parent_context": parent_message.metadata
            })
            
        return Message(**message_data)

    async def log_message(self, message: Message) -> None:
        """Log a message if logging is enabled."""
        if not self.config.enable_logging:
            return
            
        if hasattr(self, 'graph_state') and "conversation_state" in self.graph_state:
            await self.graph_state["conversation_state"].add_message(
                message=message,
                sender=f"{self.config.graph_name}.{self.name}",
                target=f"{self.config.graph_name}.system"
            )

    async def update_message_status(
        self,
        message: Message,
        new_status: MessageStatus,
        **kwargs
    ) -> Message:
        """Update message status and metadata."""
        message.status = new_status
        message.metadata.update({
            "status_updated_at": datetime.now().isoformat(),
            **kwargs
        })
        await self.log_message(message)
        return message

    async def chat(self, user_input: str) -> Dict[str, Any]:
        """
        Enhanced chat implementation with logging and history.
        
        Args:
            user_input: The user's message
            
        Returns:
            Dict[str, Any]: Response containing status and message
        """
        try:
            # Create system message about sending to LLM
            system_message = await self.create_message(
                content=f"Sending query to LLM",
                type=MessageType.STATUS,
                metadata={
                    "message_type": "llm_query",
                    "model": self.model,
                    "session_id": getattr(self, 'session_id', None)
                }
            )
            await self.log_message(system_message)

            # Get response from LLM
            response = await self.query_llm(user_input)

            # Create assistant message with LLM response
            assistant_message = await self.create_message(
                content=response,
                type=MessageType.RESPONSE,
                metadata={
                    "message_type": "llm_response",
                    "model": self.model,
                    "session_id": getattr(self, 'session_id', None)
                }
            )
            await self.log_message(assistant_message)

            # Update conversation history if enabled
            if self.conversation_history is not None:
                self.conversation_history.append({
                    'user': user_input,
                    'assistant': response,
                    'timestamp': datetime.now().isoformat()
                })

            return {"response": response, "status": "success"}
        except Exception as e:
            self.logger.error(f"Error in chat: {e}")
            error_message = await self.create_message(
                content=f"Error: {str(e)}",
                type=MessageType.ERROR
            )
            await self.log_message(error_message)
            return {"response": f"Error: {str(e)}", "status": "error"} 