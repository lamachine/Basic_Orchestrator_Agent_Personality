"""Base agent class for orchestrator and agent handlers."""

import logging
from typing import Optional, Any, Dict
from src.tools.tool_registry import ToolRegistry
from src.services.db_services.db_manager import DatabaseManager
from src.services.llm_services.llm_service import LLMService

class BaseAgent:
    """Base class for all agents, encapsulating logging, tool registry, db, llm, and prompt logic."""
    def __init__(self, name: str, prompt_section: str = "", api_url: str = None, model: str = None):
        self.name = name
        self.logger = logging.getLogger(f"orchestrator.{name}")
        self.tool_registry = ToolRegistry()
        self.db = DatabaseManager()
        self.prompt_section = prompt_section
        self.conversation_state = None  # Optional: for session/stateful agents
        if api_url is None or model is None:
            raise ValueError("api_url and model must be provided to BaseAgent for LLMService.")
        self.llm = LLMService(api_url, model)
        self._model = model  # Store model name

    @property
    def model_name(self) -> str:
        """Get the agent's model name."""
        return self._model

    def log_message(self, message: str, level: str = "info"):
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
        return self.llm.get_response(system_prompt=self.prompt_section, conversation_history=[{"role": "user", "content": prompt}])

    def handle_request(self, user_input: str) -> Any:
        """Default request handler: override in subclasses."""
        self.log_message(f"Handling request: {user_input}")
        return {"status": "not_implemented", "message": "Override handle_request in subclass."} 