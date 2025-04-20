"""
Interface module for user interactions with the orchestrator.

This module defines the UserInterface class that provides common functionality
for all UI implementations and extends the BaseUserInterface class.
"""

import abc
from typing import Dict, Any, Optional, List, Callable

from src.ui.base_interface import BaseUserInterface
from src.utils.datetime_utils import now, timestamp

class UserInterface(BaseUserInterface):
    """
    Standard interface class for user interactions with the agent.
    
    This class extends BaseUserInterface and provides common implementation details
    for all interface types (CLI, web, API, etc).
    """
    
    def __init__(self, agent):
        """
        Initialize the interface with a reference to the agent.
        
        Args:
            agent: The agent instance that will handle requests
        """
        super().__init__(agent)
        self.running = False
    
    @abc.abstractmethod
    def start(self) -> None:
        """
        Start the interface and begin handling user input.
        
        Implementations should initialize any necessary resources and
        enter their main input/output loop.
        """
        pass
    
    @abc.abstractmethod
    def stop(self) -> None:
        """
        Stop the interface and clean up resources.
        
        Implementations should gracefully shut down and release any
        resources they've acquired.
        """
        pass
    
    @abc.abstractmethod
    def display_message(self, message: str) -> None:
        """
        Display a message to the user.
        
        Args:
            message: The message to display
        """
        pass
    
    @abc.abstractmethod
    def display_error(self, error: str) -> None:
        """
        Display an error message to the user.
        
        Args:
            error: The error message to display
        """
        pass
    
    @abc.abstractmethod
    def get_user_input(self) -> str:
        """
        Get input from the user.
        
        Returns:
            The user's input as a string
        """
        pass
    
    @abc.abstractmethod
    def process_agent_response(self, response: Dict[str, Any]) -> None:
        """
        Process and display a response from the agent.
        
        Args:
            response: The agent's response
        """
        pass
    
    @abc.abstractmethod
    def display_tool_result(self, result: Dict[str, Any]) -> None:
        """
        Display a tool result to the user.
        
        Args:
            result: The tool result to display
        """
        pass
    
    @abc.abstractmethod
    def check_tool_completions(self) -> None:
        """
        Check for completed tool requests and handle them.
        
        This method should be called periodically to check if any
        asynchronous tool requests have completed.
        """
        pass
    
    @abc.abstractmethod
    def handle_conversation_selection(self) -> None:
        """
        Handle the selection of a conversation (new or existing).
        
        This method should prompt the user to create a new conversation
        or continue an existing one.
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