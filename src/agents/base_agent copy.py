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
from typing import Optional, Dict, Any
from datetime import datetime
from src.tools.tool_registry import ToolRegistry
from src.services.llm_service import LLMService
from src.services.logging_service import get_logger
from src.state.state_models import MessageRole

logger = get_logger(__name__)

class BaseAgent:
    """Base class for all agents, encapsulating logging, tool registry, db, llm, and prompt logic."""
    def __init__(self, 
                 name: str, 
                 prompt_section: str = "", 
                 api_url: str = None, 
                 model: str = None, 
                 config=None
                 ):
        self.name = name
        self.logger = logging.getLogger(f"orchestrator.{name}")
        self.tool_registry = ToolRegistry()
        self.prompt_section = prompt_section
        self._model = model
        self.config = config

        # Initialize LLM service if URL and model provided
        if api_url is not None and model is not None:
            logger.debug(f"base_agent.py:BaseAgent: Getting LLM service instance for {name} with {api_url} and {model}")
            self.llm = LLMService.get_instance(api_url, model)
        else:
            self.llm = None
            logger.warning(f"LLM service not initialized in {name} - api_url and model required")

        # Basic state tracking
        self.conversation_id = str(uuid.uuid4())
        self.session_id = self.conversation_id
        self.user_id = "developer"

    @property
    def model(self) -> str:
        """Get the model name."""
        return self._model

    async def query_llm(self, prompt: str) -> str:
        """Basic LLM query with error handling."""
        if not self.llm:
            return "Error: LLM service not initialized"
            
        try:
            return await self.llm.generate(prompt)
        except Exception as e:
            self.logger.error(f"Error querying LLM: {e}")
            return f"Error: {str(e)}"

    async def chat(self, user_input: str) -> Dict[str, Any]:
        """Basic chat implementation that subclasses can override."""
        try:
            # Log that we're sending to LLM
            if hasattr(self, 'graph_state') and "conversation_state" in self.graph_state:
                await self.graph_state["conversation_state"].add_message(
                    role=MessageRole.SYSTEM,
                    content=f"Sending query to LLM",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "llm_query",
                        "model": self.model,
                        "session_id": self.session_id
                    },
                    sender=f"orchestrator_graph.{self.name}",
                    target="orchestrator_graph.llm"
                )

            # Get response from LLM
            response = await self.query_llm(user_input)

            # Log LLM's response
            if hasattr(self, 'graph_state') and "conversation_state" in self.graph_state:
                await self.graph_state["conversation_state"].add_message(
                    role=MessageRole.ASSISTANT,
                    content=response,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "message_type": "llm_response",
                        "model": self.model,
                        "session_id": self.session_id
                    },
                    sender="orchestrator_graph.llm",
                    target=f"orchestrator_graph.{self.name}"
                )

            return {"response": response, "status": "success"}
        except Exception as e:
            self.logger.error(f"Error in chat: {e}")
            return {"response": f"Error: {str(e)}", "status": "error"} 