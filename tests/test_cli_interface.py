"""
Unit tests for the CLI interface.

This module contains tests for the command-line interface implementation.
"""

import io
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

from src.ui.cli.interface import CLIInterface


class TestCLIInterface(unittest.TestCase):
    """Test cases for the CLIInterface class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock the agent
        self.mock_agent = MagicMock()

        # Mock non-blocking input dependencies
        self.input_patcher = patch("src.ui.cli.msvcrt")
        self.mock_input = self.input_patcher.start()

        # Mock tool checker
        self.tool_checker_patcher = patch("src.ui.cli.start_tool_checker")
        self.mock_tool_checker = self.tool_checker_patcher.start()

        # Mock the check_completed_tool_requests function
        self.check_tools_patcher = patch("src.ui.cli.check_completed_tool_requests")
        self.mock_check_tools = self.check_tools_patcher.start()

        # Create the interface
        self.interface = CLIInterface(self.mock_agent)

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        self.input_patcher.stop()
        self.tool_checker_patcher.stop()
        self.check_tools_patcher.stop()

    def test_display_message(self):
        """Test displaying a message."""
        # Setup
        test_message = "This is a test message"

        # Mock stdout
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            # Exercise
            self.interface.display_message(test_message)

            # Verify
            self.assertEqual(mock_stdout.getvalue().strip(), test_message)

    def test_display_error(self):
        """Test displaying an error message."""
        # Setup
        test_error = "This is a test error"

        # Mock stdout
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            # Exercise
            self.interface.display_error(test_error)

            # Verify
            self.assertEqual(mock_stdout.getvalue().strip(), f"Error: {test_error}")

    def test_process_agent_response_success(self):
        """Test processing a successful agent response."""
        # Setup
        test_response = {"response": "This is the agent's response"}

        # Mock display_message
        with patch.object(self.interface, "display_message") as mock_display:
            # Exercise
            self.interface.process_agent_response(test_response)

            # Verify
            mock_display.assert_called_once_with("This is the agent's response")

    def test_process_agent_response_missing_response(self):
        """Test processing an agent response with no 'response' field."""
        # Setup
        test_response = {"status": "success", "data": {}}

        # Mock display_message
        with patch.object(self.interface, "display_message") as mock_display:
            # Exercise
            self.interface.process_agent_response(test_response)

            # Verify - display_message should not be called
            mock_display.assert_not_called()

    def test_display_tool_result(self):
        """Test displaying a tool result."""
        # Setup
        test_result = {
            "request_id": "test-123",
            "tool_name": "search",
            "response": {"message": "This is the tool result"},
        }

        # Mock process_completed_tool_request
        with patch("src.ui.cli.process_completed_tool_request") as mock_process:
            mock_process.return_value = "Processed tool result"

            # Mock display_message
            with patch.object(self.interface, "display_message") as mock_display:
                # Exercise
                self.interface.display_tool_result(test_result)

                # Verify
                mock_process.assert_called_once_with(test_result)
                mock_display.assert_has_calls(
                    [
                        call("\nTool 'search' completed with result:"),
                        call("Processed tool result"),
                    ]
                )

    def test_process_user_command_exit(self):
        """Test processing the 'exit' command."""
        # Setup
        test_command = "exit"

        # Mock stop method
        with patch.object(self.interface, "stop") as mock_stop:
            # Mock display_message
            with patch.object(self.interface, "display_message") as mock_display:
                # Exercise
                result = self.interface.process_user_command(test_command)

                # Verify
                self.assertTrue(result)
                mock_display.assert_called_once_with("Exiting...")
                mock_stop.assert_called_once()

    def test_process_user_command_rename_success(self):
        """Test processing the 'rename' command successfully."""
        # Setup
        test_command = "rename"
        new_name = "new-session-name"

        # Configure mock agent to return success
        self.mock_agent.rename_conversation.return_value = True

        # Mock display_message
        with patch.object(self.interface, "display_message") as mock_display:
            # Mock input to return the new name
            with patch("builtins.input", return_value=new_name):
                # Exercise
                result = self.interface.process_user_command(test_command)

                # Verify
                self.assertTrue(result)
                mock_display.assert_has_calls(
                    [
                        call("Enter new session name:"),
                        call(f"Session renamed to: {new_name}"),
                    ]
                )
                self.assertEqual(self.interface.session_name, new_name)
                self.mock_agent.rename_conversation.assert_called_once_with(new_name)

    def test_process_user_command_rename_failure(self):
        """Test processing the 'rename' command with a failure."""
        # Setup
        test_command = "rename"
        new_name = "new-session-name"

        # Configure mock agent to return failure
        self.mock_agent.rename_conversation.return_value = False

        # Mock display_message and display_error
        with patch.object(self.interface, "display_message") as mock_display:
            with patch.object(self.interface, "display_error") as mock_error:
                # Mock input to return the new name
                with patch("builtins.input", return_value=new_name):
                    # Exercise
                    result = self.interface.process_user_command(test_command)

                    # Verify
                    self.assertTrue(result)
                    mock_display.assert_called_once_with("Enter new session name:")
                    mock_error.assert_called_once_with("Failed to rename session")
                    self.assertNotEqual(self.interface.session_name, new_name)
                    self.mock_agent.rename_conversation.assert_called_once_with(new_name)

    def test_process_user_command_unknown(self):
        """Test processing an unknown command."""
        # Setup
        test_command = "unknown"

        # Exercise
        result = self.interface.process_user_command(test_command)

        # Verify - should return False for unhandled commands
        self.assertFalse(result)

    def test_process_character_enter(self):
        """Test processing an Enter key press."""
        # Setup
        self.interface.buffer = "test input"

        # Mock agent's chat method to return a response
        self.mock_agent.chat.return_value = {"response": "Agent response"}

        # Mock print
        with patch("builtins.print") as mock_print:
            # Mock process_agent_response
            with patch.object(self.interface, "process_agent_response") as mock_process:
                # Exercise
                self.interface._process_character("\r")

                # Verify
                mock_print.assert_called_once()
                self.assertEqual(self.interface.buffer, "")
                self.mock_agent.chat.assert_called_once_with("test input")
                mock_process.assert_called_once_with({"response": "Agent response"})

    def test_process_character_enter_empty_buffer(self):
        """Test processing an Enter key press with an empty buffer."""
        # Setup
        self.interface.buffer = "  "  # Just whitespace

        # Mock print
        with patch("builtins.print") as mock_print:
            # Mock agent's chat method
            with patch.object(self.mock_agent, "chat") as mock_chat:
                # Exercise
                self.interface._process_character("\r")

                # Verify
                mock_print.assert_called_once()
                self.assertEqual(self.interface.buffer, "")
                # Chat should not be called with an empty input
                mock_chat.assert_not_called()

    def test_process_character_backspace(self):
        """Test processing a Backspace key press."""
        # Setup
        self.interface.buffer = "test"

        # Mock refresh_input_line
        with patch.object(self.interface, "_refresh_input_line") as mock_refresh:
            # Exercise
            self.interface._process_character("\b")

            # Verify
            self.assertEqual(self.interface.buffer, "tes")
            mock_refresh.assert_called_once()

    def test_process_character_backspace_empty_buffer(self):
        """Test processing a Backspace key press with an empty buffer."""
        # Setup
        self.interface.buffer = ""

        # Mock refresh_input_line
        with patch.object(self.interface, "_refresh_input_line") as mock_refresh:
            # Exercise
            self.interface._process_character("\b")

            # Verify
            self.assertEqual(self.interface.buffer, "")
            # refresh_input_line should not be called for an empty buffer
            mock_refresh.assert_not_called()

    def test_process_character_regular(self):
        """Test processing a regular character."""
        # Setup
        self.interface.buffer = "tes"

        # Mock sys.stdout.write
        with patch("sys.stdout.write") as mock_write:
            # Mock sys.stdout.flush
            with patch("sys.stdout.flush") as mock_flush:
                # Exercise
                self.interface._process_character("t")

                # Verify
                self.assertEqual(self.interface.buffer, "test")
                mock_write.assert_called_once_with("t")
                mock_flush.assert_called_once()

    def test_display_tools_lists_registry_tools(self):
        """Test that the CLI 'tools' command lists tools from the registry, not a hardcoded list."""
        # Setup: Patch get_registry to return a mock registry
        with (
            patch("src.ui.cli.get_registry") as mock_get_registry,
            patch.object(self.interface, "display_message") as mock_display,
        ):
            mock_registry = MagicMock()
            mock_registry.list_tools.return_value = ["foo", "bar"]
            mock_registry.get_config.side_effect = lambda name: {"description": f"desc for {name}"}
            mock_get_registry.return_value = mock_registry

            # Exercise: Call the CLI's _display_tools method
            import asyncio

            asyncio.run(self.interface._display_tools())

            # Verify: Output matches the registry, not a hardcoded list
            mock_display.assert_any_call("\nAvailable Tools:")
            mock_display.assert_any_call("- foo: desc for foo")
            mock_display.assert_any_call("- bar: desc for bar")


if __name__ == "__main__":
    unittest.main()
