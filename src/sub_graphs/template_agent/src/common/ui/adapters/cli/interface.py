"""CLI interface implementation."""

import asyncio
import threading
from typing import Dict, Any, Optional
import uuid
import traceback

from ..base_interface import BaseUserInterface, MessageFormat
from src.sub_graphs.template_agent.src.common.services.logging_service import get_logger
from .display import CLIDisplay
from .tool_handler import CLIToolHandler
from .session_handler import CLISessionHandler
from .commands import CLICommandProcessor

logger = get_logger(__name__)

class CLIInterface(BaseUserInterface):
    """Command-line interface for interacting with agents."""
    
    def __init__(self, agent, session_manager):
        """Initialize the CLI interface."""
        super().__init__(agent)
        self.session_manager = session_manager
        
        # Initialize components
        self.display = CLIDisplay()
        self.tool_handler = CLIToolHandler(self.display, agent)
        self.session_handler = CLISessionHandler(self.display, session_manager)
        self.command_processor = CLICommandProcessor(self.display, agent)
        
        # Threading control
        self.stop_event = threading.Event()
        self.tool_checker_thread = None
        
        # Set user_id from agent if available
        if hasattr(agent, 'user_id'):
            self.display.user_id = agent.user_id
    
    def display_message(self, message: Dict[str, Any]) -> None:
        """Display a message to the user."""
        self.display.display_message(message)
    
    def get_user_input(self) -> Dict[str, Any]:
        """Get input from the user."""
        return self.display.get_user_input()
    
    def display_error(self, message: Dict[str, Any]) -> None:
        """Display an error message to the user."""
        self.display.display_error(message)
    
    def display_tool_result(self, result: Dict[str, Any]) -> None:
        """Display a tool result to the user."""
        self.display.display_tool_result(result)
    
    async def check_tool_completions(self) -> None:
        """Check for completed tool requests."""
        await self.tool_handler.check_tool_completions()
    
    async def start(self) -> None:
        """Start the CLI interface."""
        try:
            # Get the main event loop
            main_loop = asyncio.get_running_loop()
            
            # Start tool checker thread
            self.stop_event.clear()
            self.tool_checker_thread = threading.Thread(
                target=self._tool_checker_loop,
                args=(main_loop,),
                daemon=True
            )
            self.tool_checker_thread.start()
            
            # Initialize new session
            await self.session_handler.initialize_session()
            
            # Main interaction loop
            while not self.stop_event.is_set():
                # Get user input
                user_input = await asyncio.to_thread(self.display.get_user_input)
                if not user_input:
                    continue
                    
                # Process command if it's a command
                if user_input["params"]["message"].startswith("/"):
                    if await self.command_processor.process_command(user_input["params"]["message"][1:]):
                        continue
                
                # Process as normal input
                await self._process_user_input(user_input)
                
        except Exception as e:
            logger.error(f"Error in CLI interface: {str(e)}")
            raise
    
    def stop(self) -> None:
        """Stop the CLI interface."""
        self.stop_event.set()
        if self.tool_checker_thread:
            self.tool_checker_thread.join(timeout=1.0)
    
    def _tool_checker_loop(self, main_loop: asyncio.AbstractEventLoop) -> None:
        """Background thread for checking tool completions."""
        logger.debug("Starting tool checker loop")
        while not self.stop_event.is_set():
            try:
                #logger.debug("Checking for tool completions")
                future = asyncio.run_coroutine_threadsafe(
                    self.tool_handler.check_tool_completions(),
                    main_loop
                )
                future.result()  # Wait for completion
            except Exception as e:
                logger.error("Error in tool checker: %s", str(e))
                logger.error("Traceback: %s", traceback.format_exc())
            self.stop_event.wait(self.tool_handler.tool_check_interval)
    
    async def _process_user_input(self, user_input: Dict[str, Any]) -> None:
        """Process user input and get response from agent."""
        try:
            # Get response from agent first
            logger.debug(f"Getting response from agent for input: {user_input}")
            input_text = user_input.get("params", {}).get("message", "")
            
            # Pass the agent's graph_state to the process_message method
            # This ensures conversation_state is available for message logging
            response = await self.agent.process_message(input_text, session_state=self.agent.graph_state)
            logger.debug(f"Raw agent response: {response}")
            
            # Process the response
            await self.process_agent_response(response)
            
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}")
            self.display.display_error(str(e))
    
    async def process_agent_response(self, response: Dict[str, Any]) -> None:
        """
        Process a response from the agent.
        
        Args:
            response: The agent's response dictionary
        """
        try:
            logger.debug("Processing agent response: %s", response)
            # Extract message from response
            message = response.get("response", {})
            if isinstance(message, dict):
                message = message.get("message", str(message))
            
            # Handle processing status
            if response.get("status") == "processing":
                logger.debug("Response is processing, request ID: %s", response.get('request_id'))
                self.display.display_message({
                    "role": "assistant",
                    "content": f"Processing your request... (ID: {response.get('request_id')})"
                })
                return
            
            # Get character name from agent if available
            metadata = {}
            if hasattr(self.agent, 'personality_agent') and self.agent.personality_agent:
                metadata['character_name'] = self.agent.personality_agent.get_name()
            
            # Display the message
            logger.debug("Displaying final response: %s", message)
            self.display.display_message({
                "role": "assistant",
                "content": message,
                "metadata": metadata
            })
            
        except Exception as e:
            logger.error("Error processing agent response: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            self.display.display_message({
                "role": "system",
                "content": f"Error processing response: {str(e)}"
            }) 