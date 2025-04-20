"""
Base Agent Module - Core functionality for all agent types.

This module provides the BaseAgent class which serves as the foundation for all
specialized agents in the system. It implements core functionality needed by any agent:

1. Configuration Management - Loading and validating agent settings
2. Database Integration - Connecting to and querying persistent storage
3. Conversation Management - Tracking and updating conversation state 
4. Session Handling - Managing unique user sessions and context
5. Tool Registration - Standardized interface for tool discovery and execution
6. Error Handling - Common error handling and logging patterns

By extracting these common capabilities into BaseAgent, specialized agents can
focus on their unique responsibilities without duplicating boilerplate code. This
promotes code reuse, consistency, and modularity across the agent ecosystem.

The architecture follows a composition pattern where specialized agents inherit from
BaseAgent and add their domain-specific functionality, while the OrchestratorAgent
coordinates their interactions in a flexible workflow.
"""

import logging
import uuid
from typing import Optional, Any, Dict, List
from datetime import datetime

from src.tools.tool_registry import ToolRegistry
from src.services.db_services.db_manager import DatabaseManager
from src.services.llm_services.llm_service import LLMService
from src.tools.orchestrator_tools import check_completed_tool_requests
from src.utils.datetime_utils import timestamp, format_datetime

# Import state management if available
try:
    from src.graphs.orchestrator_graph import GraphState, StateManager, MessageRole, Message
    HAS_STATE_MANAGER = True
except ImportError:
    HAS_STATE_MANAGER = False
    # Define fallback classes if needed
    class MessageRole:
        USER = "user"
        ASSISTANT = "assistant"

# Setup logging
from src.services.logging_services.logging_service import get_logger
logger = get_logger(__name__)

class BaseAgent:
    """Base class for all agents, encapsulating logging, tool registry, db, llm, and prompt logic."""
    def __init__(self, name: str, prompt_section: str = "", api_url: str = None, model: str = None, config=None):
        self.name = name
        self.logger = logging.getLogger(f"orchestrator.{name}")
        self.tool_registry = ToolRegistry()
        self.prompt_section = prompt_section
        self._model = model  # Store model name
        self.config = config

        # Initialize database connection
        try:
            self.db = DatabaseManager()
            self.has_db = True
            logger.debug(f"Database initialized successfully in {name}")
        except Exception as e:
            error_msg = f"Database initialization failed in {name}: {e}"
            logger.critical(error_msg)
            self.has_db = False
            self.db = None

        # Initialize LLM service if URL and model provided
        if api_url is not None and model is not None:
            self.llm = LLMService(api_url, model)
        else:
            self.llm = None
            logger.warning(f"LLM service not initialized in {name} - api_url and model required")

        # Initialize state management if available
        if HAS_STATE_MANAGER:
            from src.state.state_manager import create_initial_state
            self.graph_state = create_initial_state()
            self.state_manager = StateManager(self.graph_state)
        else:
            self.graph_state = None
            self.state_manager = None
            logger.warning(f"State manager not available in {name}")

        # Session tracking
        self.conversation_id = None
        self.session_id = None  # Alias for conversation_id for compatibility
        self.user_id = "developer"  # Default user ID
        
        # Tool request tracking
        self.pending_requests = {}

    @property
    def model_name(self) -> str:
        """Get the agent's model name."""
        return self._model

    @property
    def model(self) -> str:
        """Get the agent's model name (alias for compatibility)."""
        return self._model

    def log_message(self, message: str, level: str = "info"):
        """Log a message with the specified level."""
        if level == "debug":
            self.logger.debug(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        else:
            self.logger.info(message)

    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call a tool by name from the registry."""
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            self.logger.error(f"Tool '{tool_name}' not found in registry.")
            return {"status": "error", "message": f"Tool '{tool_name}' not found."}
        return tool.function(**kwargs)

    def query_llm(self, prompt: str) -> str:
        """Query the LLM service with a prompt."""
        if self.llm is None:
            logger.error("LLM service not initialized")
            return "Error: LLM service not initialized"
        return self.llm.get_response(system_prompt=self.prompt_section, conversation_history=[{"role": "user", "content": prompt}])

    def handle_tool_completion(self, request_id: str, original_query: str) -> Dict[str, str]:
        """
        Handle a completed tool request.
        
        Args:
            request_id: The ID of the completed request
            original_query: The original user query that initiated the tool request
            
        Returns:
            Dictionary with the response and status
        """
        try:
            # Default implementation - subclasses should override with specific logic
            logger.warning(f"Default tool completion handler called for {request_id}")
            return {
                "response": f"Tool request {request_id} completed, but no specific handler implemented.",
                "status": "warning"
            }
            
        except Exception as e:
            error_msg = f"Error handling tool completion: {e}"
            logger.error(error_msg)
            return {"response": f"Error: {error_msg}", "status": "error"}

    def check_pending_tools(self) -> Optional[Dict[str, Any]]:
        """
        Check for pending tool requests.
        
        Returns:
            Dictionary of completed tool requests or None
        """
        try:
            # Call the global tool checker
            return check_completed_tool_requests()
            
        except Exception as e:
            logger.error(f"Error checking pending tools: {e}")
            return None

    def handle_request(self, user_input: str) -> Any:
        """Default request handler: override in subclasses."""
        self.log_message(f"Handling request: {user_input}")
        return {"status": "not_implemented", "message": "Override handle_request in subclass."}
        
    def chat(self, user_input: str) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            user_input: The user's input message
            
        Returns:
            Dictionary with the response and any other relevant data
        """
        try:
            # Try to store the user message, but don't fail if it can't be stored
            try:
                if self.has_db and self.conversation_id:
                    # Use message_manager directly
                    self.db.message_manager.store_message(
                        session_id=self.conversation_id,
                        role=MessageRole.USER,
                        content=user_input,
                        sender=f"orchestrator_graph.cli",
                        target=f"orchestrator_graph.{self.name}",
                        user_id=self.user_id
                    )
                    
                    # Update state manager if available
                    if self.state_manager:
                        self.state_manager.update_conversation(MessageRole.USER, user_input)
            except Exception as e:
                logger.warning(f"Could not store user message: {e}")
                (f"session_id: {self.conversation_id}, "
                            f"role: {MessageRole.USER}, "
                            f"content: {user_input}, "
                            f"sender: orchestrator_graph.cli, "
                            f"target: orchestrator_graph.{self.name}, "
                            f"user_id: {self.user_id}")
                # Continue with processing even if message storage fails
            
            # Default implementation - subclasses should override with specific logic
            logger.warning("Default chat implementation called")
            response = self.query_llm(user_input)
            
            # Try to store the assistant message, but don't fail if it can't be stored
            try:
                if self.has_db and self.conversation_id:
                    # Use message_manager directly
                    self.db.message_manager.store_message(
                        session_id=self.conversation_id,
                        role=MessageRole.ASSISTANT,
                        content=response,
                        sender=f"orchestrator_graph.{self.name}",
                        target="orchestrator_graph.cli",
                        user_id=self.user_id
                    )
                    
                    # Update state manager if available
                    if self.state_manager:
                        self.state_manager.update_conversation(MessageRole.ASSISTANT, response)
            except Exception as e:
                logger.warning(f"Could not store assistant message: {e}")
                # Continue with processing even if message storage fails
                
            return {"response": response, "status": "success"}
        except Exception as e:
            error_msg = f"Error in base chat method: {e}"
            logger.error(error_msg)
            return {"response": f"Error: {error_msg}", "status": "error"} 