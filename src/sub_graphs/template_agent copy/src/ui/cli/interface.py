"""
Template Agent CLI Interface.

This module provides the CLI interface implementation for the template agent,
inheriting core functionality from the orchestrator's CLI interface
but adding template-specific command handling.
"""

import asyncio
import threading
from typing import Dict, Any, Optional
import uuid
import traceback

from src.ui.cli.interface import CLIInterface as OrchestratorCLIInterface
from src.ui.cli.display import CLIDisplay
from src.ui.cli.tool_handler import CLIToolHandler
from src.ui.cli.session_handler import CLISessionHandler
from src.ui.cli.commands import CLICommandProcessor
from ..base_interface import MessageFormat
from ...services.logging_service import get_logger

logger = get_logger(__name__)

class CLIInterface(OrchestratorCLIInterface):
    """
    Template agent CLI interface.
    
    This class extends the orchestrator's CLI interface with template-specific
    command handling and message routing.
    """
    
    def __init__(self, agent, session_manager):
        """Initialize the template CLI interface."""
        super().__init__(agent, session_manager)
        self.source_prefix = "template"
        logger.debug("Initialized template CLI interface")
    
    async def _process_user_input(self, user_input: Dict[str, Any]) -> None:
        """Process user input with template-specific handling."""
        try:
            # Get response from template agent
            logger.debug(f"Getting response from template agent for input: {user_input}")
            input_text = user_input.get("params", {}).get("message", "")
            
            # Add template-specific context
            context = {
                "source": f"{self.source_prefix}.cli",
                "session_id": self.session_id,
                "session_name": self.session_name
            }
            
            # Process through template agent
            response = await self.agent.process_message(
                input_text,
                session_state=self.agent.graph_state,
                context=context
            )
            logger.debug(f"Raw template agent response: {response}")
            
            # Process the response
            await self.process_agent_response(response)
            
        except Exception as e:
            logger.error(f"Error processing template user input: {str(e)}")
            self.display.display_error(str(e))
    
    async def process_agent_response(self, response: Dict[str, Any]) -> None:
        """
        Process a response from the template agent.
        
        Args:
            response: The agent's response dictionary
        """
        try:
            logger.debug("Processing template agent response: %s", response)
            
            # Extract message from response
            message = response.get("response", {})
            if isinstance(message, dict):
                message = message.get("message", str(message))
            
            # Handle processing status
            if response.get("status") == "processing":
                logger.debug("Response is processing, request ID: %s", response.get('request_id'))
                self.display.display_message({
                    "role": "assistant",
                    "content": f"Template agent is processing your request... (ID: {response.get('request_id')})"
                })
                return
            
            # Add template-specific metadata
            metadata = {
                "source": self.source_prefix,
                "session_id": self.session_id,
                "session_name": self.session_name
            }
            
            # Display the message
            logger.debug("Displaying template agent response: %s", message)
            self.display.display_message({
                "role": "assistant",
                "content": message,
                "metadata": metadata
            })
            
        except Exception as e:
            logger.error("Error processing template agent response: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            self.display.display_message({
                "role": "system",
                "content": f"Error processing template response: {str(e)}"
            }) 