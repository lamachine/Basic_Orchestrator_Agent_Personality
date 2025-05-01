"""
Base implementation of the user interface.

This module provides a base implementation for user interfaces,
implementing common functionality that can be reused across different UI types.
"""

import time
import logging
import traceback
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime
from abc import ABC, abstractmethod

from src.tools.tool_processor import process_completed_tool_request
from src.tools.orchestrator_tools import check_completed_tool_requests, PENDING_TOOL_REQUESTS
from src.utils.datetime_utils import timestamp, now

# Setup logging
from src.services.logging_service import get_logger
logger = get_logger(__name__)

class BaseUserInterface(ABC):
    """
    Abstract base class for user interfaces.
    
    This class defines the interface that all UI implementations must follow,
    ensuring consistent interaction patterns regardless of the specific UI 
    (CLI, web, API, etc).
    
    Standard interface class for user interactions with the agent.
    This class provides common implementation details for all interface types (CLI, web, API, etc).
    """
    
    def __init__(self, agent):
        """
        Initialize the interface with a reference to the agent.
        
        Args:
            agent: The agent instance that will handle requests
        """
        self.agent = agent
        self.running = False
        self.session_id = None
        self.session_name = f"Session-{now().strftime('%Y%m%d-%H%M%S')}"
        self.initialized = False
        
        # Threading control for asynchronous operations
        self.stop_event = threading.Event()
        self.tool_checker_thread = None
        
    @abstractmethod
    def start(self) -> None:
        """
        Start the interface and begin handling user input.
        
        Implementations should initialize any necessary resources and
        enter their main input/output loop.
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """
        Stop the interface and clean up resources.
        
        Implementations should gracefully shut down and release any
        resources they've acquired.
        """
        pass
        
    @abstractmethod
    def display_message(self, message: str) -> None:
        """
        Display a message to the user.
        
        Args:
            message: The message to display
        """
        pass
        
    @abstractmethod
    def get_user_input(self) -> str:
        """
        Get input from the user.
        
        Returns:
            The user's input as a string
        """
        pass
        
    @abstractmethod
    def display_error(self, message: str) -> None:
        """
        Display an error message to the user.
        
        Args:
            message: The error message to display
        """
        pass
    
    @abstractmethod
    def process_agent_response(self, response: Dict[str, Any]) -> None:
        """
        Process and display a response from the agent.
        
        Args:
            response: The agent's response
        """
        pass
    
    @abstractmethod
    def display_tool_result(self, result: Dict[str, Any]) -> None:
        """
        Display a tool result to the user.
        
        Args:
            result: The tool result to display
        """
        pass
    
    @abstractmethod
    def check_tool_completions(self) -> None:
        """
        Check for completed tool requests and handle them.
        
        This method should be called periodically to check if any
        asynchronous tool requests have completed.
        """
        pass
    
    def process_user_command(self, command: str) -> bool:
        """
        Process a special user command (like 'exit', 'rename', etc).
        
        Args:
            command: The command to process
            
        Returns:
            True if the command was handled, False otherwise
        """
        command = command.strip().lower()
        
        if command == 'exit':
            self.display_message("Exiting...")
            self.stop()
            return True
        
        # For other commands, subclasses should override this method
        # or implement their own command handling
        return False
        
    def display_thinking(self) -> None:
        """Display a thinking/working indicator."""
        pass
        
    def clear_thinking(self) -> None:
        """Clear the thinking/working indicator."""
        pass
        
    def initialize(self) -> bool:
        """
        Initialize the interface. Override to add custom initialization.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        self.initialized = True
        return True
        
    def shutdown(self) -> None:
        """Clean up resources. Override to add custom cleanup."""
        pass
        
    def handle_session_start(self, session_id: Optional[str] = None) -> None:
        """
        Handle the start of a new session.
        
        Args:
            session_id: Optional session ID to use
        """
        if session_id:
            self.session_id = session_id
            
    def set_session_id(self, session_id: str) -> None:
        """
        Set the current session ID.
        
        Args:
            session_id: The session ID to set
        """
        self.session_id = session_id
        
    def display_formatted(self, content: Union[str, Dict, List], format_type: str = "default") -> None:
        """
        Display formatted content.
        
        Args:
            content: The content to display
            format_type: The type of formatting to use
        """
        # Default implementation just converts to string
        if isinstance(content, (dict, list)):
            import json
            self.display_message(json.dumps(content, indent=2))
        else:
            self.display_message(str(content))
            
    def confirm(self, message: str) -> bool:
        """
        Ask for user confirmation.
        
        Args:
            message: The confirmation message to display
            
        Returns:
            True if confirmed, False otherwise
        """
        response = self.get_user_input().strip().lower()
        return response in ("y", "yes")

    def check_pending_completions(self) -> None:
        """
        Check for any pending tool completions that happened while offline.
        
        This is useful when starting or resuming a session to process any
        tool completions that occurred while the interface was not running.
        """
        try:
            logger.debug("Checking for pending tool completions from previous sessions")
            completions = check_completed_tool_requests()
            if completions:
                logger.debug(f"Found {len(completions)} pending tool completions from previous sessions")
                for request_id, completion in completions.items():
                    try:
                        # Only process if not already processed
                        if not completion.get("processed_by_agent", False):
                            logger.debug(f"Processing pending completion for request {request_id}")
                            self.display_tool_result({
                                "request_id": request_id,
                                "name": completion.get("name", "unknown"),
                                "response": completion.get("response", {})
                            })
                    except Exception as e:
                        logger.error(f"Error processing pending completion {request_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking pending tool completions: {e}")
            logger.error(traceback.format_exc())

    def _process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input through the agent.
        
        Args:
            user_input: The input from the user
            
        Returns:
            Dict containing the agent's response
        """
        try:
            logger.debug(f"base_interface._process_user_input: Processing user input: {user_input}")
            # Add debug info about the agent
            logger.debug(f"base_interface._process_user_input: self.agent.chat: {self.agent.__class__.__name__} instance {id(self.agent)}")
            # Call the agent's chat method without timestamp
            return self.agent.chat(user_input)
        except Exception as e:
            self.display_error(f"Error processing input: {str(e)}")
            return {"response": f"An error occurred: {str(e)}"} 