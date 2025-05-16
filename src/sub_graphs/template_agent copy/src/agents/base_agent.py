"""
Template Base Agent - Core functionality for all agent types.

This module provides the BaseAgent class which serves as the foundation for all
specialized agents in the system. It implements core functionality needed by any agent:

1. Configuration Management - Loading and validating agent settings
2. Database Integration - Connecting to and querying persistent storage
3. Conversation Management - Tracking and updating conversation state 
4. Session Handling - Managing unique user sessions and context
5. Tool Registration - Standardized interface for tool discovery and execution
6. Error Handling - Common error handling and logging patterns

To use this template:
1. Copy this file to your agent's directory
2. Rename it to base_agent.py
3. Update the imports to match your project structure
4. Modify any agent-specific functionality
5. Add your custom methods and properties
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

# Update these imports to match your project structure
from ..tools.tool_registry import ToolRegistry
from ..services.llm_service import LLMService
from ..services.logging_service import get_logger
from ..state.state_models import MessageRole, MessageState

logger = get_logger(__name__)

class AgentConfig(BaseModel):
    """Configuration model for agent initialization."""
    name: str
    api_url: Optional[str] = None
    model: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    prompt_section: str = ""

class BaseAgent:
    """
    Base class for all agents, providing core functionality.
    
    This class implements:
    1. Basic agent initialization and configuration
    2. LLM service integration
    3. Tool registry management
    4. Conversation state tracking
    5. Message logging and persistence
    6. Error handling and logging
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize the base agent.
        
        Args:
            config: AgentConfig object containing initialization parameters
        """
        self.name = config.name
        self.logger = logging.getLogger(f"agent.{config.name}")
        self.tool_registry = ToolRegistry()
        self.prompt_section = config.prompt_section
        self._model = config.model
        self.config = config.config

        # Initialize LLM service if URL and model provided
        if config.api_url and config.model:
            logger.debug(f"Initializing LLM service for {config.name} with {config.api_url} and {config.model}")
            self.llm = LLMService.get_instance(config.api_url, config.model)
        else:
            self.llm = None
            logger.warning(f"LLM service not initialized in {config.name} - api_url and model required")

        # Basic state tracking
        self.conversation_id = str(uuid.uuid4())
        self.session_id = self.conversation_id
        self.user_id = "developer"
        self.conversation_history: List[Dict[str, Any]] = []

    @property
    def model(self) -> Optional[str]:
        """Get the model name."""
        return self._model

    async def query_llm(self, prompt: str) -> str:
        """
        Query the LLM with a prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            str: The LLM's response
            
        Raises:
            Exception: If LLM service is not initialized or query fails
        """
        if not self.llm:
            raise Exception("LLM service not initialized")
            
        try:
            return await self.llm.generate(prompt)
        except Exception as e:
            self.logger.error(f"Error querying LLM: {e}")
            raise

    async def process_message(self, message: str, session_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process an incoming message.
        
        Args:
            message: The message to process
            session_state: Optional session state dictionary
            
        Returns:
            Dict[str, Any]: Response containing status and message
            
        Raises:
            Exception: If message processing fails
        """
        try:
            # Log user message
            if session_state and "conversation_state" in session_state:
                await self._log_message(
                    session_state["conversation_state"],
                    MessageRole.USER,
                    message,
                    sender=f"{self.name}.cli",
                    target=f"{self.name}.agent"
                )

            # Create and send prompt to LLM
            prompt = await self._create_prompt(message)
            response = await self.query_llm(prompt)

            # Log LLM response
            if session_state and "conversation_state" in session_state:
                await self._log_message(
                    session_state["conversation_state"],
                    MessageRole.ASSISTANT,
                    response,
                    sender=f"{self.name}.llm",
                    target=f"{self.name}.agent"
                )

            # Update conversation history
            self._update_history(message, response)

            return {"response": response, "status": "success"}

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return {"response": f"Error: {str(e)}", "status": "error"}

    async def _create_prompt(self, message: str) -> str:
        """
        Create a prompt for the LLM.
        
        Args:
            message: The user's message
            
        Returns:
            str: The formatted prompt
            
        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _create_prompt")

    async def _log_message(
        self,
        conversation_state: MessageState,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        sender: Optional[str] = None,
        target: Optional[str] = None
    ) -> None:
        """
        Log a message to the conversation state.
        
        Args:
            conversation_state: The conversation state to log to
            role: The role of the message sender
            content: The message content
            metadata: Optional metadata about the message
            sender: Optional sender identifier
            target: Optional target identifier
        """
        try:
            await conversation_state.add_message(
                role=role,
                content=content,
                metadata=metadata or {},
                sender=sender or f"{self.name}.system",
                target=target or f"{self.name}.system"
            )
        except Exception as e:
            self.logger.error(f"Error logging message: {e}")
            raise

    def _update_history(self, user_message: str, assistant_response: str) -> None:
        """
        Update the conversation history.
        
        Args:
            user_message: The user's message
            assistant_response: The assistant's response
        """
        self.conversation_history.append({
            "user": user_message,
            "assistant": assistant_response,
            "timestamp": datetime.now().isoformat(),
            "user_id": self.user_id
        })
        # Keep only last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:] 