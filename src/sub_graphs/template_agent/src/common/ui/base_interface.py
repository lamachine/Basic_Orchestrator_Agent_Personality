"""
Base interface module for the template agent.

This module provides the base interface class that all interfaces must implement.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.sub_graphs.template_agent.src.common.agents.base_agent import BaseAgent
from src.sub_graphs.template_agent.src.common.managers.session_manager import SessionManager

from ..services.logging_service import get_logger, setup_logging

logger = get_logger(__name__)


class MessageFormat:
    """Core message format implementation."""

    @staticmethod
    def create_request(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a request message."""
        request = {"id": str(uuid.uuid4()), "method": method, "params": params or {}}
        logger.debug(f"Created request message: {request}")
        return request

    @staticmethod
    def create_response(request_id: str, result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a response message."""
        response = {"id": request_id, "result": result or {}}
        logger.debug(f"Created response message: {response}")
        return response

    @staticmethod
    def create_error(
        request_id: str, code: int, message: str, data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Create an error message."""
        error = {
            "id": request_id,
            "error": {"code": code, "message": message, "data": data},
        }
        logger.debug(f"Created error message: {error}")
        return error


class BaseInterface(ABC):
    """Base interface class that all interfaces must implement."""

    def __init__(self, agent: BaseAgent, session_manager: SessionManager):
        """
        Initialize the interface.

        Args:
            agent: The agent instance
            session_manager: The session manager instance
        """
        self.agent = agent
        self.session_manager = session_manager
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging for the interface."""
        setup_logging()

    @abstractmethod
    async def start(self) -> None:
        """Start the interface."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the interface."""
        pass

    @abstractmethod
    async def handle_input(self, input_data: Any) -> Any:
        """
        Handle input from the user.

        Args:
            input_data: The input data

        Returns:
            The response data
        """
        pass

    @abstractmethod
    async def handle_output(self, output_data: Any) -> None:
        """
        Handle output to the user.

        Args:
            output_data: The output data
        """
        pass


class BaseUserInterface(ABC):
    """
    Abstract base class for user interfaces.

    This class defines the interface that all UI implementations must follow,
    ensuring consistent interaction patterns regardless of the specific UI
    (CLI, web, API, etc).
    """

    def __init__(self, agent):
        """Initialize the interface with a reference to the agent."""
        self.agent = agent
        self.session_id = None
        self.session_name = None
        logger.debug(f"Initialized base interface with agent: {agent}")

    @abstractmethod
    def start(self) -> None:
        """Start the interface and begin handling user input."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the interface and clean up resources."""
        pass

    @abstractmethod
    def display_message(self, message: Dict[str, Any]) -> None:
        """Display a message to the user."""
        pass

    @abstractmethod
    def get_user_input(self) -> Dict[str, Any]:
        """Get input from the user."""
        pass

    @abstractmethod
    def display_error(self, message: Dict[str, Any]) -> None:
        """Display an error message to the user."""
        pass

    @abstractmethod
    def process_agent_response(self, response: Dict[str, Any]) -> None:
        """Process and display a response from the agent."""
        pass

    @abstractmethod
    def display_tool_result(self, result: Dict[str, Any]) -> None:
        """Display a tool result to the user."""
        pass

    @abstractmethod
    def check_tool_completions(self) -> None:
        """Check for completed tool requests and handle them."""
        pass

    def process_user_command(self, command: Dict[str, Any]) -> bool:
        """Process a special user command."""
        logger.debug(f"Processing user command: {command}")
        method = command.get("method", "").lower()

        if method == "exit":
            self.display_message(
                MessageFormat.create_response(
                    request_id=command.get("id"), result={"message": "Exiting..."}
                )
            )
            self.stop()
            return True

        return False

    def _process_user_input(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process user input through the agent."""
        try:
            logger.debug(f"Processing user input: {user_input}")
            request_id = user_input.get("id")

            # Extract the actual input from the message
            input_text = user_input.get("params", {}).get("message", "")
            logger.debug(f"Extracted input text: {input_text}")

            # Process through agent
            logger.debug("Sending input to agent for processing")
            agent_response = self.agent.chat(input_text)
            logger.debug(f"Received agent response: {agent_response}")

            # Format response
            response = MessageFormat.create_response(
                request_id=request_id,
                result={
                    "response": agent_response.get("response", str(agent_response)),
                    "status": agent_response.get("status", "success"),
                },
            )
            logger.debug(f"Formatted response: {response}")
            return response

        except Exception as e:
            logger.error(f"Error processing input: {e}")
            error = MessageFormat.create_error(
                request_id=user_input.get("id", "unknown"),
                code=-32000,
                message=f"Error processing input: {str(e)}",
            )
            logger.debug(f"Created error response: {error}")
            return error
