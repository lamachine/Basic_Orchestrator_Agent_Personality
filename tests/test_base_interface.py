"""
Unit tests for the base user interface module.

This module contains tests for the base user interface implementation,
including the MessageFormat utilities and the abstract BaseUserInterface class.
"""

import json
import unittest
import uuid
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Use patch to mock the import since the actual path might not be in the system path during testing
with patch("src.sub_graphs.template_agent.src.common.services.logging_service.get_logger"):
    from src.sub_graphs.template_agent.src.common.ui.base_interface import (
        BaseUserInterface,
        MessageFormat,
    )


class TestMessageFormat(unittest.TestCase):
    """Test cases for the MessageFormat utility class."""

    @patch("uuid.uuid4")
    def test_create_request_normal(self, mock_uuid):
        """Test creating a normal request message."""
        # Arrange
        mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
        method = "test_method"
        params = {"key": "value"}

        # Act
        result = MessageFormat.create_request(method, params)

        # Assert
        self.assertEqual(result["id"], "12345678-1234-5678-1234-567812345678")
        self.assertEqual(result["method"], method)
        self.assertEqual(result["params"], params)

    @patch("uuid.uuid4")
    def test_create_request_no_params(self, mock_uuid):
        """Test creating a request with no parameters."""
        # Arrange
        mock_uuid.return_value = uuid.UUID("12345678-1234-5678-1234-567812345678")
        method = "test_method"

        # Act
        result = MessageFormat.create_request(method)

        # Assert
        self.assertEqual(result["id"], "12345678-1234-5678-1234-567812345678")
        self.assertEqual(result["method"], method)
        self.assertEqual(result["params"], {})  # Should default to empty dict

    def test_create_response_normal(self):
        """Test creating a normal response message."""
        # Arrange
        request_id = "test-id-123"
        result_data = {"status": "success", "data": "test_data"}

        # Act
        response = MessageFormat.create_response(request_id, result_data)

        # Assert
        self.assertEqual(response["id"], request_id)
        self.assertEqual(response["result"], result_data)

    def test_create_response_no_result(self):
        """Test creating a response with no result data."""
        # Arrange
        request_id = "test-id-123"

        # Act
        response = MessageFormat.create_response(request_id)

        # Assert
        self.assertEqual(response["id"], request_id)
        self.assertEqual(response["result"], {})  # Should default to empty dict

    def test_create_error_normal(self):
        """Test creating a normal error message."""
        # Arrange
        request_id = "test-id-123"
        code = 404
        message = "Not found"
        data = {"details": "Item doesn't exist"}

        # Act
        error = MessageFormat.create_error(request_id, code, message, data)

        # Assert
        self.assertEqual(error["id"], request_id)
        self.assertEqual(error["error"]["code"], code)
        self.assertEqual(error["error"]["message"], message)
        self.assertEqual(error["error"]["data"], data)

    def test_create_error_no_data(self):
        """Test creating an error message with no additional data."""
        # Arrange
        request_id = "test-id-123"
        code = 500
        message = "Server error"

        # Act
        error = MessageFormat.create_error(request_id, code, message)

        # Assert
        self.assertEqual(error["id"], request_id)
        self.assertEqual(error["error"]["code"], code)
        self.assertEqual(error["error"]["message"], message)
        self.assertIsNone(error["error"]["data"])


# Create a concrete implementation of BaseUserInterface for testing
class TestableUserInterface(BaseUserInterface):
    """Concrete implementation of BaseUserInterface for testing."""

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def display_message(self, message):
        self.last_message = message

    def get_user_input(self):
        return {"id": "test-id", "params": {"message": "test input"}}

    def display_error(self, message):
        self.last_error = message

    def process_agent_response(self, response):
        self.last_response = response

    def display_tool_result(self, result):
        self.last_tool_result = result

    def check_tool_completions(self):
        self.tool_completions_checked = True


class TestBaseUserInterface(unittest.TestCase):
    """Test cases for the BaseUserInterface abstract base class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.agent = MagicMock()
        self.interface = TestableUserInterface(self.agent)

    def test_initialization(self):
        """Test initialization of the user interface."""
        # Assert
        self.assertEqual(self.interface.agent, self.agent)
        self.assertIsNone(self.interface.session_id)
        self.assertIsNone(self.interface.session_name)

    def test_process_user_command_exit(self):
        """Test processing an exit command."""
        # Arrange
        command = {"id": "test-id", "method": "exit"}

        # Act
        result = self.interface.process_user_command(command)

        # Assert
        self.assertTrue(result)  # Should return True for exit
        self.assertTrue(self.interface.stopped)  # Should call stop()
        self.assertEqual(self.interface.last_message["result"]["message"], "Exiting...")

    def test_process_user_command_unknown(self):
        """Test processing an unknown command."""
        # Arrange
        command = {"id": "test-id", "method": "unknown_command"}

        # Act
        result = self.interface.process_user_command(command)

        # Assert
        self.assertFalse(result)  # Should return False for non-exit commands

    def test_process_user_input_normal(self):
        """Test processing normal user input."""
        # Arrange
        user_input = {"id": "test-id", "params": {"message": "Hello, agent!"}}
        self.agent.chat.return_value = {"response": "Hello, user!", "status": "success"}

        # Act
        response = self.interface._process_user_input(user_input)

        # Assert
        self.agent.chat.assert_called_once_with("Hello, agent!")
        self.assertEqual(response["id"], "test-id")
        self.assertEqual(response["result"]["response"], "Hello, user!")
        self.assertEqual(response["result"]["status"], "success")

    def test_process_user_input_error(self):
        """Test processing user input that causes an error."""
        # Arrange
        user_input = {"id": "test-id", "params": {"message": "Cause an error"}}
        self.agent.chat.side_effect = ValueError("Test error")

        # Act
        response = self.interface._process_user_input(user_input)

        # Assert
        self.assertEqual(response["id"], "test-id")
        self.assertEqual(response["error"]["code"], -32000)
        self.assertTrue("Error processing input" in response["error"]["message"])

    def test_process_user_input_edge_case_empty(self):
        """Test processing empty user input."""
        # Arrange
        user_input = {"id": "test-id", "params": {"message": ""}}
        self.agent.chat.return_value = {
            "response": "I didn't get any input",
            "status": "success",
        }

        # Act
        response = self.interface._process_user_input(user_input)

        # Assert
        self.agent.chat.assert_called_once_with("")
        self.assertEqual(response["result"]["response"], "I didn't get any input")

    def test_process_user_input_edge_case_missing_params(self):
        """Test processing user input with missing params field."""
        # Arrange
        user_input = {
            "id": "test-id"
            # No params field
        }
        self.agent.chat.return_value = {
            "response": "Empty message",
            "status": "success",
        }

        # Act
        response = self.interface._process_user_input(user_input)

        # Assert
        # Should call agent with empty string
        self.agent.chat.assert_called_once_with("")
        self.assertEqual(response["result"]["response"], "Empty message")
