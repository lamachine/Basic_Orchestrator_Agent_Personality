"""
Command-line interface for interacting with the orchestrator.

This module provides a CLI implementation of the UserInterface abstract base class,
with non-blocking input for checking tool completions while waiting for user input.

CLI Tool Request Polling Architecture
------------------------------------

In a command-line interface application, we face a fundamental challenge with asynchronous 
operations due to the inherently synchronous nature of terminal I/O:

1. User input through the terminal's `input()` function is blocking and event-driven. 
   When a user types and presses Enter, the program receives this input as a discrete event.

2. However, background processes (like our tools executing asynchronously) have no native way 
   to interrupt and insert their response into this I/O flow. Unlike GUI applications with 
   event loops or web servers with websockets, a CLI application has no built-in mechanism 
   for background events to notify the foreground process.

3. Therefore, we implement polling as a simple solution - regularly checking if any background 
   tool operations have completed while maintaining a responsive CLI experience.

In more sophisticated applications, this limitation might be addressed with:
- Event queues with proper event loops
- Signal handlers
- Dedicated worker processes with IPC
- WebSocket-based communication for real-time events

For our CLI application, polling provides a straightforward way to simulate asynchronous 
events without requiring complex threading or event handling architectures.


"""

import os
import sys
import time
import logging
import traceback
import threading
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum, auto

# Platform-specific imports for non-blocking input
if os.name == 'nt':  # Windows
    import msvcrt
else:  # Unix/Linux/MacOS
    import select
    import termios
    import tty

# Local imports
from src.ui.base_interface import BaseUserInterface
from src.tools.orchestrator_tools import (
    start_tool_checker, 
    check_completed_tool_requests,
    PENDING_TOOL_REQUESTS
)
from src.agents.base_agent import BaseAgent
from src.services.db_services.db_manager import DatabaseManager
from src.ui.interface import UserInterface
from src.utils.datetime_utils import now, timestamp

# Setup logging
from src.services.logging_services.logging_service import get_logger
logger = get_logger(__name__)

class DisplayMode(Enum):
    """Display modes for the CLI interface."""
    NORMAL = auto()
    THINKING = auto()
    TOOL_WAIT = auto()
    MULTILINE = auto()

class CLIInterface(BaseUserInterface):
    """
    Command-line interface for interacting with agents.
    
    This class provides a CLI that supports:
    - Basic chat interactions
    - Session management
    - History viewing and searching
    - Help and command documentation
    """
    
    def __init__(self, agent):
        """
        Initialize the CLI interface.
        
        Args:
            agent: The agent to interact with
        """
        super().__init__(agent)
        self.current_session_id = None
        self.display_mode = DisplayMode.NORMAL
        self.config = agent or {}
        self.history_index = 0
        self.history = []
        self.current_input = ""
        # State for multiline input
        self.multiline_input = False
        self.multiline_buffer = []
        self.db = DatabaseManager() if agent and hasattr(agent, 'has_db') and agent.has_db else None
        self.session_name = f"CLI-session-{now().strftime('%Y%m%d-%H%M%S')}"
        
        # Get the orchestrator if it exists
        self.orchestrator = None
        if agent:
            # Try to get orchestrator directly from the agent
            if hasattr(agent, 'orchestrator'):
                self.orchestrator = agent.orchestrator
                logger.debug("Got orchestrator from agent")
        
        # Display settings
        self.display_thinking_indicator = True
        self.thinking_animation = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        self.thinking_frame = 0
    
    def _main_loop(self) -> None:
        """Run the main interaction loop."""
        self.display_message("\nWelcome to the CLI interface. Type 'help' for available commands or 'exit' to quit.\n")
        self.display_message(f"Starting new session: {self.session_name}\n")
        
        self.running = True
        while self.running:
            # Get user input using the implemented method
            user_input = self.get_user_input()
            logger.debug(f"Got user input: {user_input}")
            # Handle special commands
            if not user_input:
                continue
            elif user_input.lower() in ['exit', 'quit']:
                self.running = False
                self.display_message("Goodbye!")
                break
            elif user_input.lower() == 'help':
                self._display_help()
                continue
            elif user_input.lower().startswith('history'):
                self._display_history(user_input)
                continue
            elif user_input.lower().startswith('sessions'):
                self._display_sessions(user_input)
                continue
            elif user_input.lower().startswith('continue'):
                self._continue_session(user_input)
                continue
            elif user_input.lower().startswith('rename'):
                self._rename_session(user_input)
                continue
            
            # Add to history
            logger.debug(f"cli._main_loop: Adding to history: {user_input}")
            logger.debug(f"cli._main_loop: History: {self.history}")
            self.history.append(user_input)
            
            
            # Process the input through the agent
            logger.debug(f"Processing user input: {user_input}")
            response_data = self._process_user_input(user_input)
            
            
            # Display the response
            if response_data and "response" in response_data:
                self.display_message(f"\n{response_data['response']}\n")
            else:
                self.display_message("\nNo response from agent.\n")
    
    def _display_help(self) -> None:
        """Display help information."""
        help_text = """
Available commands:
  exit, quit       - Exit the CLI
  help             - Display this help information
  history          - Show command history
  sessions         - List available sessions
  continue <id>    - Continue a previous session
  rename <title>   - Rename the current session
"""
        self.display_message(help_text)
    
    def _display_history(self, command: str) -> None:
        """Display command history."""
        parts = command.split()
        limit = 10  # Default limit
        
        if len(parts) > 1:
            try:
                limit = int(parts[1])
            except ValueError:
                self.display_message("Invalid limit, using default of 10")
        
        self.display_message("\nCommand history:")
        for i, cmd in enumerate(self.history[-limit:], 1):
            self.display_message(f"{i}. {cmd}")
        self.display_message("")
    
    def _display_sessions(self, command: str) -> None:
        """Display available sessions."""
        try:
            parts = command.split()
            limit = 10  # Default limit
            
            if len(parts) > 1:
                try:
                    limit = int(parts[1])
                except ValueError:
                    self.display_message("Invalid limit, using default of 10")
            
            sessions = self._get_sessions(limit=limit)
            
            if not sessions:
                self.display_message("No sessions found")
                return
            
            # Display sessions
            self.display_message("\nRecent sessions (sorted by last activity):")
            for i, (session_id, session_info) in enumerate(sessions.items(), 1):
                if i > limit:
                    break
                    
                name = session_info.get("name") or f"Session {session_id}"
                updated = session_info.get("updated_at", "Unknown")
                
                # Format datetime if needed
                if isinstance(updated, datetime):
                    updated = updated.strftime("%Y-%m-%d %H:%M:%S")
                    
                self.display_message(f"{i}. {name} (last activity: {updated})")
            
            self.display_message("")
        except Exception as e:
            self.display_message(f"Error listing sessions: {str(e)}")
            logger.error(f"Error listing sessions: {e}", exc_info=True)
    
    def _continue_session(self, command: str) -> None:
        """Continue an existing session."""
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            self.display_message("Please specify a session ID to continue")
            return
        
        try:
            session_id = parts[1].strip()
            success = self._do_continue_session(session_id)
            
            if not success:
                self.display_message(f"Failed to continue session: {session_id}")
        except Exception as e:
            self.display_message(f"Error continuing session: {str(e)}")
            logger.error(f"Error continuing session: {e}", exc_info=True)
    
    def _rename_session(self, command: str) -> None:
        """Rename the current session."""
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            self.display_message("Please specify a new title for the session")
            return
        
        try:
            new_title = parts[1].strip()
            
            # Get the current conversation ID
            conversation_id = getattr(self.agent, 'conversation_id', None)
            
            if not conversation_id:
                self.display_message("No active session to rename")
                return
            
            # Attempt to rename using available methods
            success = False
            
            # Try agent's method first if available
            if hasattr(self.agent, 'rename_conversation'):
                logger.debug("Using agent.rename_conversation")
                success = self.agent.rename_conversation(new_title)
            # Then try database method if available
            elif self.db and hasattr(self.db, 'rename_conversation'):
                logger.debug("Using db.rename_conversation")
                success = self.db.rename_conversation(conversation_id, new_title)
            elif hasattr(self.agent, 'db') and hasattr(self.agent.db, 'rename_conversation'):
                logger.debug("Using agent.db.rename_conversation")
                success = self.agent.db.rename_conversation(conversation_id, new_title)
            else:
                self.display_message("Cannot rename session: no rename method available")
                return
            
            if success:
                old_name = self.session_name
                self.session_name = new_title
                self.display_message(f"Renamed session from '{old_name}' to: '{new_title}'")
            else:
                self.display_message("Failed to rename session")
        except Exception as e:
            self.display_message(f"Error renaming session: {str(e)}")
            logger.error(f"Error renaming session: {e}", exc_info=True)
    
    def display_message(self, message: str) -> None:
        """
        Display a message to the user.
        
        Args:
            message: The message to display
        """
        print(message)
    
    def display_error(self, message: str) -> None:
        """
        Display an error message to the user.
        
        Args:
            message: The error message to display
        """
        print(f"ERROR: {message}")
    
    def get_user_input(self) -> str:
        """
        Get input from the user.
        
        Returns:
            The user's input as a string
        """
        return input("> ").strip()
    
    def check_tool_completions(self) -> None:
        """
        Check for completed tool requests and handle them.
        
        This method is called periodically to check if any
        asynchronous tool requests have completed.
        """
        try:
            # Check for completed tools
            completions = check_completed_tool_requests()
            if completions:
                for request_id, completion in completions.items():
                    # Process each completed tool request
                    if not completion.get("processed_by_agent", False):
                        self.display_tool_result({
                            "request_id": request_id,
                            "name": completion.get("name", "unknown"),
                            "response": completion.get("response", {})
                        })
        except Exception as e:
            logger.error(f"Error checking tool completions: {e}")
    
    def display_tool_result(self, result: Dict[str, Any]) -> None:
        """
        Display a tool result to the user.
        
        Args:
            result: The tool result to display
        """
        try:
            request_id = result.get("request_id", "unknown")
            tool_name = result.get("name", "unknown")
            response = result.get("response", {})
            
            # Format the response
            if isinstance(response, dict):
                response_text = json.dumps(response, indent=2)
            else:
                response_text = str(response)
                
            self.display_message(f"\nTool result from '{tool_name}' (ID: {request_id}):\n{response_text}\n")
            
            # Mark as displayed
            if request_id in PENDING_TOOL_REQUESTS:
                PENDING_TOOL_REQUESTS[request_id]["displayed"] = True
                
        except Exception as e:
            logger.error(f"Error displaying tool result: {e}")
    
    def display_thinking(self) -> None:
        """Display a thinking animation."""
        self.thinking_frame = (self.thinking_frame + 1) % len(self.thinking_animation)
        frame = self.thinking_animation[self.thinking_frame]
        print(f"\rThinking {frame}", end="", flush=True)
        time.sleep(0.1)
    
    def clear_thinking(self) -> None:
        """Clear the thinking animation."""
        print("\r" + " " * 20 + "\r", end="", flush=True)

    def start(self) -> None:
        """
        Start the CLI interface and begin handling user input.
        """
        # Initialize the base interface
        super().start()
        
        try:
            # Start the tool checker thread from the orchestrator_tools
            start_tool_checker()
            
            # Start our own dedicated background thread for checking tool completions
            self.stop_event.clear()
            self.tool_checker_thread = threading.Thread(
                target=self._background_tool_checker,
                daemon=True  # Make it a daemon so it exits when the main thread exits
            )
            self.tool_checker_thread.start()
            logger.debug("Started background tool checker thread")
            
            # Show welcome message
            self.display_message("\nWelcome to the CLI interface. Type 'help' for available commands or 'exit' to quit.\n")
            
            # Offer to continue a previous session or start a new one
            try:
                if self._offer_continue_previous_session():
                    # A previous session was continued, no need to rename the current one
                    logger.debug("Continuing previous session")
                else:
                    # Start a new conversation
                    logger.debug("Starting a new conversation")
                    self._start_new_conversation()
                    
                    # Prompt for session name
                    logger.debug("Offering to name new session")
                    self._prompt_for_session_name()
            except Exception as e:
                logger.error(f"Error during session initialization: {e}", exc_info=True)
                self.display_message(f"Could not initialize conversation: {str(e)}")
                
            # Main input loop
            self._main_loop()
        except Exception as e:
            logger.error(f"Error starting CLI interface: {e}", exc_info=True)
            self.display_message(f"Error starting interface: {str(e)}")
            raise
    
    def stop(self) -> None:
        """
        Stop the CLI interface and clean up resources.
        """
        # Signal the tool checker thread to stop
        self.stop_event.set()
        
        # Wait for the thread to finish if it's running
        if self.tool_checker_thread is not None:
            self.tool_checker_thread.join(timeout=2.0)  # Wait up to 2 seconds
            logger.debug("Tool checker thread joined")
        
        # Stop the base interface
        super().stop()
        logger.debug("CLI interface stopped")
    
    def _background_tool_checker(self):
        """
        Background thread that periodically checks for completed tool runs.
        """
        logger.debug("Background tool checker thread started")
        while not self.stop_event.is_set():
            try:
                # Get the session ID from any available source
                session_id = None
                
                # First try the explicit current_session_id
                if self.current_session_id:
                    session_id = self.current_session_id
                # Next try the agent's conversation_id
                elif hasattr(self.agent, 'conversation_id') and self.agent.conversation_id:
                    session_id = self.agent.conversation_id
                # Next try the agent's session_id (alternative name)
                elif hasattr(self.agent, 'session_id') and self.agent.session_id:
                    session_id = self.agent.session_id
                
                # Check for pending tools if we have both the orchestrator and a session ID
                if self.orchestrator and session_id:
                    logger.debug(f"Checking pending tools for session: {session_id}")
                    self.orchestrator.check_pending_tools(session_id)
                elif session_id:
                    # If we have a session ID but no orchestrator, check directly
                    logger.debug(f"Checking pending tools with global function for session: {session_id}")
                    check_completed_tool_requests()
                    
                # Wait a bit before checking again
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error in background tool checker: {e}")
                time.sleep(1.0)  # Wait longer on error
                
        logger.debug("Background tool checker thread exiting")
    
    def process_agent_response(self, response: Dict[str, Any]) -> None:
        """
        Process and display a response from the agent.
        
        Args:
            response: The response dictionary from the agent
        """
        # Default implementation - display the response content with "Agent:" prefix
        if isinstance(response, dict):
            if 'response' in response:
                self.display_message(f"Agent: {response['response']}")
            else:
                self.display_message(f"Agent: {response}")
        else:
            self.display_message(f"Agent: {response}")
            
        # Display prompt for next user input
        self.display_message("\nYou: ", end='')

    def _get_sessions(self, limit=10) -> Dict:
        """
        Get available sessions.
        
        Args:
            limit: Maximum number of sessions to retrieve
            
        Returns:
            Dictionary of sessions
        """
        try:
            sessions = None
            user_id = getattr(self.agent, 'user_id', 'developer')
            logger.debug(f"Attempting to get sessions for user: {user_id}")
            
            # Try different methods to get sessions
            if hasattr(self.db, 'list_conversations'):
                logger.debug("Using db.list_conversations to get sessions")
                sessions = self.db.list_conversations(user_id)
            elif hasattr(self.agent, 'list_conversations'):
                logger.debug("Using agent.list_conversations to get sessions")
                sessions = self.agent.list_conversations()
            elif hasattr(self.agent, 'db') and hasattr(self.agent.db, 'list_conversations'):
                logger.debug("Using agent.db.list_conversations to get sessions")
                sessions = self.agent.db.list_conversations(user_id)
                
            # Limit the number of sessions if needed
            if sessions and limit and len(sessions) > limit:
                try:
                    # Sort by updated_at timestamp (most recent first)
                    from src.utils.datetime_utils import parse_datetime
                    
                    def get_updated_time(session_tuple):
                        """Extract the updated_at time from a session tuple for sorting."""
                        session_id, session_info = session_tuple
                        updated_at = session_info.get('updated_at')
                        # Convert string timestamps to datetime objects for comparison
                        if updated_at:
                            if isinstance(updated_at, str):
                                updated_at = parse_datetime(updated_at)
                            elif isinstance(updated_at, datetime) and updated_at.tzinfo:
                                # Ensure timezone-naive for comparison
                                updated_at = updated_at.replace(tzinfo=None)
                            return updated_at
                        return datetime.min  # Default for sorting

                    sorted_sessions = sorted(
                        sessions.items(),
                        key=get_updated_time,  # Use updated_at time for sorting
                        reverse=True
                    )[:limit]
                    sessions = dict(sorted_sessions)
                except Exception as e:
                    logger.warning(f"Error sorting sessions: {e}")
                
            logger.debug(f"Found {len(sessions) if sessions else 0} sessions")
            return sessions or {}
        except Exception as e:
            logger.error(f"Error getting sessions: {e}", exc_info=True)
            return {}

    def _offer_continue_previous_session(self) -> bool:
        """
        Offer to continue a previous session.
        
        Returns:
            True if a previous session was continued, False otherwise
        """
        try:
            # Check if we have sessions to continue
            sessions = self._get_sessions(limit=10)  # Explicitly limit to 10 sessions max
            if not sessions:
                self.display_message("Starting a new session...")
                return False
                
            # Display recent sessions (max 10)
            self.display_message("\nRecent sessions (sorted by last activity):")
            indexed_sessions = []
            
            for i, (session_id, session_info) in enumerate(sessions.items(), 1):
                if i > 10:  # Hard limit of 10 sessions
                    break
                    
                name = session_info.get("name") or f"Session {session_id}"
                updated = session_info.get("updated_at", "Unknown")
                
                # Format datetime if needed
                if isinstance(updated, datetime):
                    updated = updated.strftime("%Y-%m-%d %H:%M:%S")
                    
                self.display_message(f"{i}. {name} (last activity: {updated})")
                indexed_sessions.append((session_id, name))
            
            # Ask if user wants to continue or start new
            self.display_message("\nWould you like to continue a previous session? Enter the number, or 'n' for a new session:")
            choice = self.get_user_input().strip().lower()
            
            if choice in ('n', 'no', 'new'):
                self.display_message("Starting a new session...")
                return False
                
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(indexed_sessions):
                    session_id, session_name = indexed_sessions[choice_idx]
                    self.display_message(f"Continuing session: {session_name}...")
                    
                    # Continue the selected session
                    success = self._do_continue_session(session_id)
                    if success:
                        return True
                    else:
                        self.display_message("Failed to continue session. Starting a new one instead.")
                        return False
                else:
                    self.display_message("Invalid selection. Starting a new session...")
                    return False
            except ValueError:
                self.display_message("Invalid selection. Starting a new session...")
                return False
                
        except Exception as e:
            logger.error(f"Error offering to continue previous session: {e}", exc_info=True)
            self.display_message("Error checking previous sessions. Starting a new session...")
            return False

    def _do_continue_session(self, session_id: str) -> bool:
        """
        Continue an existing session by ID.
        
        Args:
            session_id: The ID of the session to continue
            
        Returns:
            True if the session was continued successfully, False otherwise
        """
        try:
            logger.debug(f"Attempting to continue session: {session_id}")
            conversation = None
            
            # Try different methods to continue the conversation
            if hasattr(self.agent, 'continue_conversation'):
                logger.debug("Using agent.continue_conversation")
                conversation = self.agent.continue_conversation(session_id)
            elif hasattr(self.db, 'continue_conversation'):
                logger.debug("Using db.continue_conversation")
                user_id = getattr(self.agent, 'user_id', 'developer')
                conversation = self.db.continue_conversation(session_id, user_id)
            elif hasattr(self.agent, 'db') and hasattr(self.agent.db, 'continue_conversation'):
                logger.debug("Using agent.db.continue_conversation")
                user_id = getattr(self.agent, 'user_id', 'developer')
                conversation = self.agent.db.continue_conversation(session_id, user_id)
            else:
                logger.error("No method found to continue conversation")
                self.display_message("Cannot continue session: no continuation method available")
                return False
            
            if not conversation:
                logger.error(f"Failed to continue conversation: {session_id}")
                return False
                
            # Use set_conversation_id method if available (this will handle all sub-processors)
            if hasattr(self.agent, 'set_conversation_id'):
                logger.debug(f"Using agent.set_conversation_id({session_id})")
                self.agent.set_conversation_id(session_id)
            else:
                # Fall back to individually setting IDs
                if hasattr(self.agent, 'conversation_id'):
                    self.agent.conversation_id = session_id
                    logger.debug(f"Set agent.conversation_id to {session_id}")
                if hasattr(self.agent, 'session_id'):
                    self.agent.session_id = session_id  # Alias for compatibility
                    logger.debug(f"Set agent.session_id to {session_id}")
            
            # Also store locally
            self.current_session_id = session_id
            
            # Set on orchestrator if it exists
            if hasattr(self, 'orchestrator') and self.orchestrator:
                if hasattr(self.orchestrator, 'set_conversation_id'):
                    logger.debug(f"Using orchestrator.set_conversation_id({session_id})")
                    self.orchestrator.set_conversation_id(session_id)
                else:
                    self.orchestrator.conversation_id = session_id
                    logger.debug(f"Set orchestrator.conversation_id to {session_id}")
                
            # If agent has an orchestrator, set it there too
            if hasattr(self.agent, 'orchestrator') and self.agent.orchestrator:
                if hasattr(self.agent.orchestrator, 'set_conversation_id'):
                    logger.debug(f"Using agent.orchestrator.set_conversation_id({session_id})")
                    self.agent.orchestrator.set_conversation_id(session_id)
                else:
                    self.agent.orchestrator.conversation_id = session_id
                    logger.debug(f"Set agent.orchestrator.conversation_id to {session_id}")
            
            # Update state manager if available
            if hasattr(self.agent, 'state_manager') and self.agent.state_manager:
                try:
                    # Get messages for this conversation
                    messages = []
                    
                    # Try different methods to get messages
                    if hasattr(self.db, 'message_manager') and hasattr(self.db.message_manager, 'get_messages_by_session'):
                        logger.debug("Using db.message_manager.get_messages_by_session")
                        messages = self.db.message_manager.get_messages_by_session(
                            session_id, format_type="standard"
                        )
                    elif hasattr(self.db, 'get_conversation_messages'):
                        logger.debug("Using db.get_conversation_messages")
                        messages = self.db.get_conversation_messages(session_id)
                    elif hasattr(self.agent, 'db') and hasattr(self.agent.db, 'get_conversation_messages'):
                        logger.debug("Using agent.db.get_conversation_messages")
                        messages = self.agent.db.get_conversation_messages(session_id)
                    
                    # Update conversation state with messages
                    if messages:
                        logger.debug(f"Updating state with {len(messages)} messages")
                        for msg in messages:
                            role = msg.get('role')
                            content = msg.get('content')
                            if role and content:
                                self.agent.state_manager.update_conversation(role, content)
                    else:
                        logger.warning("No messages found for conversation")
                except Exception as e:
                    logger.warning(f"Could not load messages for conversation {session_id}: {e}")
            
            # Rename the CLI session to match
            try:
                sessions = self._get_sessions()
                if session_id in sessions:
                    session_name = sessions[session_id].get("name")
                    if session_name:
                        self.session_name = session_name
                        logger.debug(f"Updated session name to: {session_name}")
            except Exception as e:
                logger.warning(f"Could not update session name: {e}")
                
            self.display_message(f"Continued session: {self.session_name} (ID: {session_id})")
            return True
        except Exception as e:
            logger.error(f"Error continuing session: {e}", exc_info=True)
            self.display_message(f"Error continuing session: {str(e)}")
            return False

    def _prompt_for_session_name(self) -> None:
        """Prompt the user to name the current session."""
        try:
            self.display_message(f"Starting new session with default name: {self.session_name}")
            self.display_message("Would you like to give it a custom name? (y/n)")
            
            choice = self.get_user_input().strip().lower()
            if choice in ('y', 'yes'):
                self.display_message("Enter a name for this session:")
                new_name = self.get_user_input().strip()
                
                if new_name:
                    try:
                        # Store the new name
                        old_name = self.session_name
                        self.session_name = new_name
                        
                        # Try to update the name in the database
                        success = False
                        conversation_id = getattr(self.agent, 'conversation_id', None)
                        
                        if hasattr(self.agent, 'rename_conversation'):
                            logger.debug("Using agent.rename_conversation")
                            success = self.agent.rename_conversation(new_name)
                        elif self.db and hasattr(self.db, 'rename_conversation') and conversation_id:
                            logger.debug("Using db.rename_conversation")
                            success = self.db.rename_conversation(conversation_id, new_name)
                        elif hasattr(self.agent, 'db') and hasattr(self.agent.db, 'rename_conversation') and conversation_id:
                            logger.debug("Using agent.db.rename_conversation")
                            success = self.agent.db.rename_conversation(conversation_id, new_name)
                        else:
                            # Just update local name if we can't update in database
                            logger.debug("No rename method found, using local rename only")
                            success = True
                            
                        if success:
                            self.display_message(f"Session renamed to: {new_name}")
                        else:
                            self.display_message(f"Failed to rename session in database, using local name: {new_name}")
                    except Exception as e:
                        logger.error(f"Error renaming session: {e}", exc_info=True)
                        self.session_name = old_name
                        self.display_message(f"Error renaming session. Using default name: {old_name}")
            
            self.display_message(f"\nSession: {self.session_name}\n")
        except Exception as e:
            logger.error(f"Error prompting for session name: {e}", exc_info=True)
            self.display_message("Error setting session name. Using default name.") 

    def _start_new_conversation(self) -> None:
        """
        Start a new conversation in the database and set the conversation ID.
        """
        try:
            # Try starting a new conversation using available methods
            conversation_id = None
            user_id = getattr(self.agent, 'user_id', 'developer')
            
            if hasattr(self.agent, 'start_conversation'):
                logger.debug("Using agent.start_conversation")
                conversation_id = self.agent.start_conversation(user_id, self.session_name)
            elif self.db and hasattr(self.db, 'start_conversation'):
                logger.debug("Using db.start_conversation")
                conversation_id = self.db.start_conversation(user_id, self.session_name)
            elif hasattr(self.agent, 'db') and hasattr(self.agent.db, 'start_conversation'):
                logger.debug("Using agent.db.start_conversation")
                conversation_id = self.agent.db.start_conversation(user_id, self.session_name)
            
            if conversation_id:
                # Use set_conversation_id method if available (this will handle all sub-processors)
                if hasattr(self.agent, 'set_conversation_id'):
                    logger.debug(f"Using agent.set_conversation_id({conversation_id})")
                    self.agent.set_conversation_id(conversation_id)
                else:
                    # Fall back to individually setting IDs
                    if hasattr(self.agent, 'conversation_id'):
                        self.agent.conversation_id = conversation_id
                        logger.debug(f"Set agent.conversation_id to {conversation_id}")
                    if hasattr(self.agent, 'session_id'):
                        self.agent.session_id = conversation_id
                        logger.debug(f"Set agent.session_id to {conversation_id}")
                
                # Also store locally
                self.current_session_id = conversation_id
                
                # Set on orchestrator if it exists
                if hasattr(self, 'orchestrator') and self.orchestrator:
                    if hasattr(self.orchestrator, 'set_conversation_id'):
                        logger.debug(f"Using orchestrator.set_conversation_id({conversation_id})")
                        self.orchestrator.set_conversation_id(conversation_id)
                    else:
                        self.orchestrator.conversation_id = conversation_id
                        logger.debug(f"Set orchestrator.conversation_id to {conversation_id}")
                    
                # If agent has an orchestrator, set it there too
                if hasattr(self.agent, 'orchestrator') and self.agent.orchestrator:
                    if hasattr(self.agent.orchestrator, 'set_conversation_id'):
                        logger.debug(f"Using agent.orchestrator.set_conversation_id({conversation_id})")
                        self.agent.orchestrator.set_conversation_id(conversation_id)
                    else:
                        self.agent.orchestrator.conversation_id = conversation_id 
                        logger.debug(f"Set agent.orchestrator.conversation_id to {conversation_id}")
                
                logger.debug(f"Started new conversation with ID: {conversation_id}")
                self.display_message(f"Starting new session: {self.session_name} (ID: {conversation_id})")
            else:
                logger.warning("Could not start a new conversation")
        except Exception as e:
            logger.error(f"Error starting new conversation: {e}", exc_info=True) 