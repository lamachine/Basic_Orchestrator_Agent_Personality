"""CLI command processing functionality."""

import asyncio
from typing import Dict, Any, Optional
import uuid
import sys

from src.ui.base_interface import MessageFormat
from src.services.logging_service import get_logger

logger = get_logger(__name__)

class CLICommandProcessor:
    """Handles command processing for the CLI."""
    
    def __init__(self, display_handler, agent):
        """Initialize the command processor."""
        self.display_handler = display_handler
        self.agent = agent
    
    async def process_command(self, command: str) -> bool:
        """Process a user command.
        
        Args:
            command: The command to process
            
        Returns:
            bool: True if command was processed, False otherwise
        """
        if command.lower() == "exit":
            self.display_handler.display_message(MessageFormat.create_response(
                request_id=str(uuid.uuid4()),
                result={"message": "Goodbye!"}
            ))
            sys.exit(0)  # Clean exit
            
        if command.lower() == "help":
            self.display_handler.display_message(MessageFormat.create_response(
                request_id=str(uuid.uuid4()),
                result={"message": "\nAvailable commands:"}
            ))
            self.display_handler.display_message(MessageFormat.create_response(
                request_id=str(uuid.uuid4()),
                result={"message": "  exit - Exit the program"}
            ))
            self.display_handler.display_message(MessageFormat.create_response(
                request_id=str(uuid.uuid4()),
                result={"message": "  help - Show this help message"}
            ))
            return True
            
        return False 