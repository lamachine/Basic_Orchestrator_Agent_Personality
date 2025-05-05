"""
Command-line interface for interacting with the orchestrator.

This module provides a simple CLI that focuses on core chat functionality
while maintaining extensibility for future features.
"""

import asyncio
import logging
import sys
from typing import Dict, Any, Optional, Set, List
from datetime import datetime
import os

from src.ui.base_interface import BaseUserInterface
from src.utils.datetime_utils import now, parse_datetime
from src.tools.orchestrator_tools import check_completed_tool_requests, PENDING_TOOL_REQUESTS
from src.state.state_models import MessageRole
from src.services.logging_service import get_logger

# from src.ui.adapters.io_adapter import OutputAdapter

# Setup logging
logger = get_logger(__name__)

# Comment indicating this file uses the singleton logger
'''
class TerminalOutputAdapter(OutputAdapter):
    """Concrete implementation of OutputAdapter for terminal output."""
    def write(self, text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()

    def clear_line(self) -> None:
        if os.name == 'nt':
            sys.stdout.write('\r' + ' ' * 80 + '\r')
        else:
            sys.stdout.write('\033[2K\r')
        sys.stdout.flush()

    def move_cursor(self, x: int, y: int) -> None:
        if os.name != 'nt':
            sys.stdout.write(f"\033[{y};{x}H")
            sys.stdout.flush()

    def set_title(self, title: str) -> None:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        else:
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()

    def set_color(self, foreground: int, background: int = None) -> None:
        if os.name != 'nt':
            if background is not None:
                sys.stdout.write(f"\033[{foreground};{background}m")
            else:
                sys.stdout.write(f"\033[{foreground}m")
            sys.stdout.flush()

    def reset_color(self) -> None:
        if os.name != 'nt':
            sys.stdout.write("\033[0m")
            sys.stdout.flush()
'''
class CLIInterface(BaseUserInterface):
    """Command-line interface for interacting with agents."""
    
    def __init__(self, agent, session_manager):
        """
        Initialize the CLI interface.
        
        Args:
            agent: The agent to interact with
            session_manager: The session manager for handling user sessions
        """
        super().__init__(agent)
        self.running = False
        self.tool_check_interval = 0.5  # Check every 500ms
        self.displayed_tools: Set[str] = set()  # Track displayed tool results
        self._tool_checker_task = None
        self.session_manager = session_manager
        self.session_name = None
        self.current_session_id = None
    
    async def start(self) -> None:
        """Start the CLI interface and tool checker."""
        try:
            # Start the tool checker as a background task
            self._tool_checker_task = asyncio.create_task(self._check_tool_completions())
            await self._main_loop()
        finally:
            if self._tool_checker_task:
                self._tool_checker_task.cancel()
                try:
                    await self._tool_checker_task
                except asyncio.CancelledError:
                    pass
    
    def stop(self) -> None:
        """Stop the CLI interface."""
        self.running = False
        if self._tool_checker_task:
            self._tool_checker_task.cancel()
    
    async def _check_tool_completions(self) -> None:
        """
        Background task that checks for completed tools and displays their results.
        Uses cooperative multitasking to avoid blocking the main input loop.
        """
        while self.running:
            try:
                # Check for completed tools
                completed_tools = check_completed_tool_requests()
                
                if completed_tools:
                    for request_id, completion in completed_tools.items():
                        # Robustness: skip or log if not a dict
                        if not isinstance(completion, dict):
                            logger.error(f"Tool completion for {request_id} is not a dict: {completion}")
                            continue
                        if (
                            not completion.get("displayed", False) 
                            and request_id not in self.displayed_tools
                        ):
                            # Format and display the result
                            tool_name = completion.get("name", "Unknown Tool")
                            result = completion.get("response", {})
                            # Display with a clear separator
                            self.display_message("\n--- Tool Completion ---")
                            self.display_message(f"Tool: {tool_name}")
                            self.display_message(f"Result: {result}")
                            self.display_message("--------------------\n")
                            self.display_message("You: ", end='')  # Restore prompt
                            # Mark as displayed
                            self.displayed_tools.add(request_id)
                            completion["displayed"] = True
                            # If agent has a tool completion handler, call it
                            if hasattr(self.agent, "handle_tool_completion"):
                                original_query = completion.get("original_query", "")
                                response = await self.agent.handle_tool_completion(
                                    request_id, 
                                    original_query
                                )
                                if response and response.get("status") == "success":
                                    await self.process_agent_response(response)
                await asyncio.sleep(self.tool_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in tool checker: {e}", exc_info=True)
                await asyncio.sleep(1.0)  # Wait longer on error
    
    def display_message(self, message: str, end: str = '\n') -> None:
        """
        Display a message to the user.
        
        Args:
            message: The message to display
            end: String to append (default newline)
        """
        print(message, end=end, flush=True)
    
    def get_user_input(self) -> str:
        """Get input from the user."""
        return input().strip()
    
    async def _main_loop(self) -> None:
        """Run the main interaction loop."""
        self.display_message("\nWelcome to the CLI interface. Type 'help' for commands or 'exit' to quit.\n")
        
        self.running = True
        while self.running:
            try:
                # Display prompt and get input
                self.display_message("You: ", end='')
                user_input = await asyncio.to_thread(self.get_user_input)
                
                if not user_input:
                    continue
                    
                # Handle commands
                if user_input.lower() in ['exit', 'quit']:
                    self.running = False
                    self.display_message("Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    self._display_help()
                    continue
                elif user_input.lower() in ['tools', 'list tools']:
                    await self._display_tools()
                    continue
                
                # Process input through agent
                if hasattr(self.agent, 'graph_state') and "conversation_state" in self.agent.graph_state:
                    await self.agent.graph_state["conversation_state"].add_message(
                        MessageRole.USER, 
                        user_input,
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "message_type": "user_input",
                            "session_id": self.agent.session_id,
                            "interface": "cli"
                        },
                        sender='orchestrator_graph.cli',
                        target='orchestrator_graph.orchestrator'
                    )
                response = await self._process_user_input(user_input)
                
                # Display response
                if response is not None:
                    await self.process_agent_response(response)
                else:
                    self.display_message("\nNo response from agent.\n")
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                self.display_message(f"Error: {str(e)}")
    
    def _display_help(self) -> None:
        """Display help information."""
        help_text = """
Available commands:
  exit, quit  - Exit the CLI
  help        - Display this help information
  tools       - List available tools
"""
        self.display_message(help_text)
    
    async def _process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and get agent response.
        
        Args:
            user_input: The user's input string
            
        Returns:
            Response dictionary from agent
        """
        try:
            # Process through agent
            if hasattr(self.agent, 'process_message'):
                session_state = None
                if hasattr(self.agent, 'graph_state') and "conversation_state" in self.agent.graph_state:
                    session_state = {"conversation_state": self.agent.graph_state["conversation_state"]}
                response = await self.agent.process_message(user_input, session_state=session_state)
            else:
                response = await self.agent.chat(user_input)
            
            # Ensure we return a dict
            if not isinstance(response, dict):
                return {
                    "response": str(response),
                    "status": "success"
                }
            return response

        except Exception as e:
            logger.error(f"Error processing user input: {e}", exc_info=True)
            return {
                "response": f"Error processing input: {str(e)}",
                "status": "error"
            }

    async def process_agent_response(self, response: Dict[str, Any]) -> None:
        """
        Process and display a response from the agent.
        
        Args:
            response: The response dictionary from the agent
        """
        try:
            if not isinstance(response, dict):
                logger.warning(f"Expected dict response, got {type(response)}")
                self.display_message(f"Agent: {str(response)}")
                return

            # Extract and display response content
            response_content = response.get('response', str(response))
            self.display_message(f"Agent: {response_content}")
            
        except Exception as e:
            logger.error(f"Error processing agent response: {e}", exc_info=True)
            self.display_message(f"Error displaying response: {str(e)}")

    def display_error(self, message: str) -> None:
        """Display an error message to the user."""
        print(f"[ERROR] {message}", flush=True)

    def display_tool_result(self, result: dict) -> None:
        """Display a tool result to the user."""
        print(f"[TOOL RESULT] {result}", flush=True)

    def check_tool_completions(self) -> None:
        """Check for completed tool requests and handle them."""
        # This is a synchronous wrapper for the async _check_tool_completions
        import asyncio
        asyncio.create_task(self._check_tool_completions()) 

    async def _get_recent_sessions(self):
        """Get recent sessions using SessionManager."""
        return await self.session_service.get_recent_sessions()

    async def _search_sessions(self):
        """Search sessions using SessionManager."""
        self.display_message("Enter search query: ", end='')
        query = await asyncio.to_thread(self.get_user_input)
        results = await self.session_manager.search_sessions(query)
        if not results:
            self.display_message("No sessions found matching your query.")
            return
        self.display_message("\nSearch results:")
        for i, (session_id, info) in enumerate(results.items(), 1):
            name = info.get('name', f"Session {session_id}")
            updated = info.get('updated_at', 'Unknown')
            if isinstance(updated, datetime):
                updated = updated.strftime("%Y-%m-%d %H:%M:%S")
            self.display_message(f"{i}. {name} (Last active: {updated})")
        self.display_message("\nEnter session number to continue or 'n' for new session: ")
        choice = await asyncio.to_thread(self.get_user_input)
        if choice.lower() != 'n':
            try:
                idx = int(choice) - 1
                session_id = list(results.keys())[idx]
                await self._continue_session(session_id)
                return
            except (ValueError, IndexError):
                self.display_message("Invalid choice, starting new session.")
        await self._start_new_session()

    async def _continue_session(self, session_id):
        """Continue a session using SessionManager."""
        await self.session_manager.restore_session(session_id)
        self.session_name = self.session_manager.session_name
        self.current_session_id = self.session_manager.current_session_id
        self.display_message(f"Resumed session: {self.session_name}")

    async def _start_new_session(self):
        """Start a new session using SessionManager."""
        # Prompt for a session name (optional)
        self.display_message("Enter a name for the new session (or leave blank): ", end='')
        name = await asyncio.to_thread(self.get_user_input)
        session_id = await self.session_manager.create_session(name=name or None)
        self.session_name = self.session_manager.session_name
        self.current_session_id = self.session_manager.current_session_id
        self.display_message(f"Started new session: {self.session_name}")

    async def _display_tools(self) -> None:
        """Display a list of available/approved tools from the registry."""
        try:
            from src.tools.initialize_tools import get_registry
            registry = get_registry()
            tool_names = registry.list_tools()
            if not tool_names:
                self.display_message("No tools are currently available.")
                return
            self.display_message("\nAvailable Tools:")
            for tool_name in tool_names:
                config = registry.get_config(tool_name)
                desc = config.get("description", "No description available.") if config else "No description available."
                self.display_message(f"- {tool_name}: {desc}")
        except Exception as e:
            self.display_message(f"Error retrieving tools: {e}") 