"""CLI display and user interaction functionality."""

import os
import sys
import uuid
from typing import Any, Dict, List, Union

from src.sub_graphs.template_agent.src.common.config import Configuration

from ....services.logging_service import get_logger
from ...base_interface import MessageFormat

logger = get_logger(__name__)


class CLIDisplay:
    """Handles all CLI display and user interaction functionality."""

    def __init__(self):
        """Initialize the display handler with config."""
        self.config = Configuration()
        self.user_id = getattr(self.config, "user_id", "developer")
        self._last_input = ""  # Store last user input
        self._should_restore_input = False  # Flag to control input restoration

    def display_message(self, message: Dict[str, Any]) -> None:
        """
        Display a message to the user.

        Args:
            message: Message dictionary containing role and content
        """
        try:
            # Extract content from message
            content = message.get("content", "")
            if isinstance(content, dict):
                content = content.get("message", str(content))

            # Handle different message types
            role = message.get("role", "assistant")
            metadata = message.get("metadata", {})

            # Print a newline before any message
            print()

            if role == "system":
                # Handle tool completion messages specially
                if "Tool Completion" in content:
                    print("--- Tool Completion ---", flush=True)
                    # Extract and display tool name and result
                    lines = content.split("\n")
                    for line in lines:
                        if line.strip() and "Tool:" in line:
                            print(f"Tool: {line.split('Tool:')[1].strip()}", flush=True)
                        elif line.strip() and "Result:" in line:
                            print(
                                f"Result: {line.split('Result:')[1].strip()}",
                                flush=True,
                            )
                    print("--------------------", flush=True)
                    self._should_restore_input = True  # Only restore input after tool completion
                else:
                    print(f"System: {content}", flush=True)
            elif role == "assistant":
                character_name = metadata.get("character_name", "Assistant")
                print(f"{character_name}: {content}", flush=True)
            elif role == "user":
                user_id = metadata.get("user_id", self.user_id)
                print(f"<{user_id}>: {content}", flush=True)
            else:
                print(content, flush=True)

            # Print a newline after any message
            print()

            # Only restore input if it's a tool completion message
            if self._should_restore_input and self._last_input:
                print(f"<{self.user_id}>: {self._last_input}", end="", flush=True)
                self._should_restore_input = False  # Reset the flag
            elif role == "system" and "Tool Completion" in content:
                # Add prompt after tool completion if no input to restore
                print(f"<{self.user_id}>: ", end="", flush=True)

        except Exception as e:
            logger.error(f"Error displaying message: {e}")
            print(f"\nError displaying message: {str(e)}\n", flush=True)

    def get_user_input(self) -> Dict[str, Any]:
        """Get input from the user."""
        try:
            # Check if input is being piped
            if not sys.stdin.isatty():
                user_input = sys.stdin.read().strip()
                logger.debug(f"Received piped input: {user_input}")
            else:
                user_input = input(f"<{self.user_id}>: ").strip()
                logger.debug(f"Received interactive input: {user_input}")
                self._last_input = user_input  # Store the input

            return MessageFormat.create_request(method="user_input", params={"message": user_input})
        except Exception as e:
            logger.error(f"Error getting user input: {e}")
            return MessageFormat.create_request(method="user_input", params={"message": ""})

    @staticmethod
    def display_error(message: Dict[str, Any]) -> None:
        """Display an error message to the user."""
        if "error" in message:
            error_msg = message["error"]["message"]
        else:
            error_msg = str(message)
        print(f"[ERROR] {error_msg}", flush=True)

    @staticmethod
    def display_tool_result(result: Dict[str, Any]) -> None:
        """Display a tool result to the user."""
        if "result" in result:
            content = result["result"]
            print(f"[TOOL RESULT] {content}", flush=True)
        else:
            print(f"[TOOL RESULT] {str(result)}", flush=True)

    @staticmethod
    def display_thinking() -> None:
        """Display a thinking/working indicator."""
        print("Thinking...", end="", flush=True)

    @staticmethod
    def clear_thinking() -> None:
        """Clear the thinking/working indicator."""
        print("\r" + " " * 20 + "\r", end="", flush=True)

    @staticmethod
    def display_formatted(
        content: Union[str, Dict, List], format_type: str = "default"
    ) -> Dict[str, Any]:
        """Create a formatted message."""
        return MessageFormat.create_response(
            request_id=str(uuid.uuid4()),
            result={"content": content, "format_type": format_type},
        )

    @staticmethod
    def confirm(message: str) -> Dict[str, Any]:
        """Create a confirmation request."""
        return MessageFormat.create_request(method="confirm", params={"message": message})
