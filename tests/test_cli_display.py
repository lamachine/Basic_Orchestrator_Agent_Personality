"""
Unit tests for the CLI display module.

This module contains tests for the command-line interface's display functionality.
"""

import io
import sys
import unittest
import uuid
from unittest.mock import MagicMock, call, patch

# Use patch to mock the import since the actual path might not be in the system path during testing
with (
    patch("src.sub_graphs.template_agent.src.common.services.logging_service.get_logger"),
    patch("src.sub_graphs.template_agent.src.common.config.Configuration"),
):
    from src.sub_graphs.template_agent.src.common.ui.adapters.base_interface import MessageFormat
    from src.sub_graphs.template_agent.src.common.ui.adapters.cli.display import CLIDisplay


class TestCLIDisplay(unittest.TestCase):
    """Test cases for the CLIDisplay class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.display = CLIDisplay()
        # Mock the config
        self.display.config = MagicMock()
        self.display.user_id = "test_user"

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_message_assistant(self, mock_stdout):
        """Test displaying an assistant message."""
        # Arrange
        message = {
            "role": "assistant",
            "content": "This is a test message",
            "metadata": {"character_name": "TestBot"},
        }

        # Act
        self.display.display_message(message)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("TestBot: This is a test message", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_message_user(self, mock_stdout):
        """Test displaying a user message."""
        # Arrange
        message = {
            "role": "user",
            "content": "User test message",
            "metadata": {"user_id": "test_user"},
        }

        # Act
        self.display.display_message(message)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("<test_user>: User test message", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_message_system(self, mock_stdout):
        """Test displaying a system message."""
        # Arrange
        message = {"role": "system", "content": "System notification", "metadata": {}}

        # Act
        self.display.display_message(message)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("System: System notification", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_message_tool_completion(self, mock_stdout):
        """Test displaying a tool completion message."""
        # Arrange
        message = {
            "role": "system",
            "content": "Tool Completion\nTool: test_tool\nResult: success",
            "metadata": {},
        }

        # Act
        self.display.display_message(message)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("--- Tool Completion ---", output)
        self.assertIn("Tool: test_tool", output)
        self.assertIn("Result: success", output)
        self.assertIn("--------------------", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_message_with_dict_content(self, mock_stdout):
        """Test displaying a message with dictionary content."""
        # Arrange
        message = {
            "role": "assistant",
            "content": {"message": "Nested message"},
            "metadata": {},
        }

        # Act
        self.display.display_message(message)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("Assistant: Nested message", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_message_error_handling(self, mock_stdout):
        """Test error handling when displaying a message."""
        # Arrange
        # Create a message that will cause an error when accessed
        message = MagicMock()
        message.get.side_effect = Exception("Test error")

        # Act
        self.display.display_message(message)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("Error displaying message: Test error", output)

    @patch("builtins.input", return_value="Test input")
    def test_get_user_input(self, mock_input):
        """Test getting user input."""
        # Arrange
        expected_method = "user_input"
        expected_message = "Test input"

        # Act
        result = self.display.get_user_input()

        # Assert
        self.assertEqual(result["method"], expected_method)
        self.assertEqual(result["params"]["message"], expected_message)
        self.assertEqual(self.display._last_input, expected_message)
        mock_input.assert_called_once_with("<test_user>: ")

    @patch("sys.stdin")
    def test_get_user_input_piped(self, mock_stdin):
        """Test getting piped user input."""
        # Arrange
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "Piped input"

        # Act
        result = self.display.get_user_input()

        # Assert
        self.assertEqual(result["params"]["message"], "Piped input")
        mock_stdin.read.assert_called_once()

    @patch("builtins.input")
    def test_get_user_input_error(self, mock_input):
        """Test handling errors when getting user input."""
        # Arrange
        mock_input.side_effect = Exception("Input error")

        # Act
        result = self.display.get_user_input()

        # Assert
        self.assertEqual(result["params"]["message"], "")  # Should return empty string on error

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_error_with_error_object(self, mock_stdout):
        """Test displaying an error message with an error object."""
        # Arrange
        error_message = {"error": {"message": "Test error message"}}

        # Act
        self.display.display_error(error_message)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("[ERROR] Test error message", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_error_with_string(self, mock_stdout):
        """Test displaying an error message with a string."""
        # Arrange
        error_message = "Simple error string"

        # Act
        self.display.display_error(error_message)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("[ERROR] Simple error string", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_tool_result_with_result(self, mock_stdout):
        """Test displaying a tool result with a result field."""
        # Arrange
        tool_result = {"result": "Tool execution successful"}

        # Act
        self.display.display_tool_result(tool_result)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("[TOOL RESULT] Tool execution successful", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_tool_result_without_result(self, mock_stdout):
        """Test displaying a tool result without a result field."""
        # Arrange
        tool_result = {"status": "success", "message": "Operation completed"}

        # Act
        self.display.display_tool_result(tool_result)

        # Assert
        output = mock_stdout.getvalue()
        # Should display the string representation of the entire dict
        self.assertIn("[TOOL RESULT]", output)
        self.assertIn("'status': 'success'", output)
        self.assertIn("'message': 'Operation completed'", output)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_thinking(self, mock_stdout):
        """Test displaying the thinking indicator."""
        # Act
        self.display.display_thinking()

        # Assert
        output = mock_stdout.getvalue()
        self.assertEqual(output, "Thinking...")

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_clear_thinking(self, mock_stdout):
        """Test clearing the thinking indicator."""
        # Act
        self.display.clear_thinking()

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("\r", output)  # Should contain carriage returns
        self.assertIn(" " * 20, output)  # Should contain spaces to clear the line

    @patch("uuid.uuid4")
    def test_display_formatted_string(self, mock_uuid):
        """Test creating a formatted message with a string."""
        # Arrange
        mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
        content = "This is formatted content"
        format_type = "markdown"

        # Act
        result = self.display.display_formatted(content, format_type)

        # Assert
        self.assertEqual(result["id"], "12345678-1234-5678-1234-567812345678")
        self.assertEqual(result["result"]["content"], content)
        self.assertEqual(result["result"]["format_type"], format_type)

    @patch("uuid.uuid4")
    def test_display_formatted_dict(self, mock_uuid):
        """Test creating a formatted message with a dictionary."""
        # Arrange
        mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
        content = {"key": "value", "nested": {"inner": "data"}}

        # Act
        result = self.display.display_formatted(content)

        # Assert
        self.assertEqual(result["result"]["content"], content)
        self.assertEqual(result["result"]["format_type"], "default")  # Should use default

    @patch("uuid.uuid4")
    def test_confirm(self, mock_uuid):
        """Test creating a confirmation request."""
        # Arrange
        mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
        message = "Are you sure?"

        # Act
        result = self.display.confirm(message)

        # Assert
        self.assertEqual(result["id"], "12345678-1234-5678-1234-567812345678")
        self.assertEqual(result["method"], "confirm")
        self.assertEqual(result["params"]["message"], message)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_message_with_input_restoration(self, mock_stdout):
        """Test input restoration after a tool completion message."""
        # Arrange
        self.display._last_input = "User was typing this"
        self.display._should_restore_input = False

        message = {
            "role": "system",
            "content": "Tool Completion\nTool: test_tool\nResult: success",
            "metadata": {},
        }

        # Act
        self.display.display_message(message)

        # Assert
        output = mock_stdout.getvalue()
        self.assertIn("<test_user>: User was typing this", output)
        self.assertFalse(self.display._should_restore_input)  # Should be reset to False
