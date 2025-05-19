"""
Unit tests for the tool utilities module.

This module contains tests for the utility functions used by tools
across the orchestrator system.
"""

import json
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.state.state_models import Message, MessageRole, TaskStatus
from src.tools.tool_utils import (
    create_tool_node_func,
    execute_tool_with_state,
    format_session_history,
    should_use_tool,
)


class TestExecuteToolWithState(unittest.TestCase):
    """Test cases for the execute_tool_with_state function."""

    def setUp(self):
        """Set up test fixtures for each test."""
        self.state_manager = MagicMock()
        self.tool_name = "test_tool"
        self.task = "Test task description"

        # Configure state_manager mock
        self.state_manager.set_task = MagicMock()
        self.state_manager.update_agent_state = MagicMock()
        self.state_manager.update_session = MagicMock()
        self.state_manager.complete_task = MagicMock()

    def test_successful_execution(self):
        """Test successful tool execution with state updates."""
        # Arrange
        tool_func = MagicMock(
            return_value={
                "status": "success",
                "message": "Test succeeded",
                "data": {"key": "value"},
            }
        )

        # Act
        result = execute_tool_with_state(
            state_manager=self.state_manager,
            tool_name=self.tool_name,
            tool_func=tool_func,
            task=self.task,
        )

        # Assert
        tool_func.assert_called_once_with(self.task)
        self.state_manager.set_task.assert_called_once()
        self.assertEqual(self.state_manager.update_agent_state.call_count, 2)
        self.assertEqual(self.state_manager.update_session.call_count, 2)
        self.state_manager.complete_task.assert_called_once()

        # Check result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Test succeeded")
        self.assertEqual(result["data"], {"key": "value"})

    def test_execution_with_error(self):
        """Test tool execution that raises an exception."""
        # Arrange
        error_message = "Test error"
        tool_func = MagicMock(side_effect=ValueError(error_message))

        # Act
        result = execute_tool_with_state(
            state_manager=self.state_manager,
            tool_name=self.tool_name,
            tool_func=tool_func,
            task=self.task,
        )

        # Assert
        tool_func.assert_called_once_with(self.task)
        self.state_manager.update_agent_state.assert_called_with(
            self.tool_name,
            {
                "status": TaskStatus.FAILED,
                "error": error_message,
                "end_time": unittest.mock.ANY,
            },
        )
        self.state_manager.fail_task.assert_called_once()

        # Check result
        self.assertEqual(result["status"], "error")
        self.assertIn(error_message, result["message"])
        self.assertEqual(result["data"]["error"], error_message)

    def test_state_update_error(self):
        """Test handling of an error during state update."""
        # Arrange
        self.state_manager.update_agent_state.side_effect = Exception("State update failed")
        tool_func = MagicMock(side_effect=ValueError("Original error"))

        # Act
        result = execute_tool_with_state(
            state_manager=self.state_manager,
            tool_name=self.tool_name,
            tool_func=tool_func,
            task=self.task,
        )

        # Assert - should handle the state update error gracefully
        self.assertEqual(result["status"], "error")
        self.assertIn("Original error", result["message"])


class TestFormatSessionHistory(unittest.TestCase):
    """Test cases for the format_session_history function."""

    def test_format_normal_history(self):
        """Test formatting a normal session history."""
        # Arrange
        state_manager = MagicMock()
        messages = [
            Message(
                id="1",
                role=MessageRole.USER,
                content="Hello, I need help",
                metadata={},
                timestamp=datetime.now(),
            ),
            Message(
                id="2",
                role=MessageRole.ASSISTANT,
                content="How can I assist you?",
                metadata={},
                timestamp=datetime.now(),
            ),
            Message(
                id="3",
                role=MessageRole.TOOL,
                content="Tool executed successfully",
                metadata={"tool": "search_tool"},
                timestamp=datetime.now(),
            ),
        ]
        state_manager.get_session_context.return_value = messages

        # Act
        result = format_session_history(state_manager)

        # Assert
        state_manager.get_session_context.assert_called_once()
        self.assertIn("User: Hello, I need help", result)
        self.assertIn("Assistant: How can I assist you?", result)
        self.assertIn("Tool [search_tool]: Tool executed successfully", result)

    def test_format_empty_history(self):
        """Test formatting an empty session history."""
        # Arrange
        state_manager = MagicMock()
        state_manager.get_session_context.return_value = []

        # Act
        result = format_session_history(state_manager)

        # Assert
        self.assertEqual(result, "")

    def test_format_history_max_messages(self):
        """Test formatting with max_messages parameter."""
        # Arrange
        state_manager = MagicMock()
        messages = [
            Message(
                id=str(i),
                role=MessageRole.USER,
                content=f"Message {i}",
                metadata={},
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]
        state_manager.get_session_context.return_value = messages

        # Act
        result = format_session_history(state_manager, max_messages=3)

        # Assert
        state_manager.get_session_context.assert_called_once_with(3)


class TestCreateToolNodeFunc(unittest.TestCase):
    """Test cases for the create_tool_node_func function."""

    @patch("src.tools.tool_utils.StateManager")
    @pytest.mark.asyncio
    async def test_tool_node_success(self, mock_state_manager_class):
        """Test the created tool node function with successful execution."""
        # Arrange
        tool_name = "test_tool"
        tool_func = MagicMock(
            return_value={
                "status": "success",
                "message": "Test tool executed successfully",
                "data": {"result": "data"},
            }
        )

        mock_state_manager = MagicMock()
        mock_state_manager_class.return_value = mock_state_manager
        mock_state_manager.get_current_state.return_value = {"updated": True}

        state = {"current_task": "Test task"}
        writer = MagicMock()

        # Create tool node function
        tool_node = create_tool_node_func(tool_name, tool_func)

        # Act
        result = await tool_node(state, writer)

        # Assert
        mock_state_manager_class.assert_called_once_with(state)
        self.assertEqual(result, {"updated": True})
        writer.assert_called()

    @patch("src.tools.tool_utils.StateManager")
    @pytest.mark.asyncio
    async def test_tool_node_with_exception(self, mock_state_manager_class):
        """Test the created tool node function with an exception."""
        # Arrange
        tool_name = "test_tool"
        tool_func = MagicMock(side_effect=Exception("Test error"))

        mock_state_manager = MagicMock()
        mock_state_manager_class.return_value = mock_state_manager
        mock_state_manager.get_current_state.return_value = {"error": True}

        state = {"current_task": "Test task"}
        writer = MagicMock()

        # Create tool node function
        tool_node = create_tool_node_func(tool_name, tool_func)

        # Act
        result = await tool_node(state, writer)

        # Assert
        mock_state_manager.fail_task.assert_called_once()
        self.assertEqual(result, {"error": True})
        writer.assert_called()

    @patch("src.tools.tool_utils.StateManager")
    @pytest.mark.asyncio
    async def test_tool_node_no_task(self, mock_state_manager_class):
        """Test the created tool node function with no current task."""
        # Arrange
        tool_name = "test_tool"
        tool_func = MagicMock()

        mock_state_manager = MagicMock()
        mock_state_manager_class.return_value = mock_state_manager

        # Create a last user message for task extraction
        mock_state_manager.get_session_context.return_value = [
            Message(
                id="1",
                role=MessageRole.USER,
                content="Do something",
                metadata={},
                timestamp=datetime.now(),
            )
        ]

        state = {}  # No current_task
        writer = MagicMock()

        # Create tool node function
        tool_node = create_tool_node_func(tool_name, tool_func)

        # Act
        await tool_node(state, writer)

        # Assert - should use last user message as task
        mock_state_manager.get_session_context.assert_called_once_with(1)


class TestShouldUseTool(unittest.TestCase):
    """Test cases for the should_use_tool function."""

    @patch("src.tools.llm_integration.ToolParser.extract_tool_calls")
    def test_should_use_tool_true(self, mock_extract_tool_calls):
        """Test that should_use_tool returns True when a tool is found."""
        # Arrange
        message = "Use the search tool to find information"
        available_tools = ["search", "calculator"]

        mock_extract_tool_calls.return_value = [
            {"tool_name": "search", "parameters": {"query": "test"}}
        ]

        # Act
        result = should_use_tool(message, available_tools)

        # Assert
        self.assertTrue(result)
        mock_extract_tool_calls.assert_called_once_with(message)

    @patch("src.tools.llm_integration.ToolParser.extract_tool_calls")
    def test_should_use_tool_false_no_tools(self, mock_extract_tool_calls):
        """Test that should_use_tool returns False when no tools are found."""
        # Arrange
        message = "Just a normal message"
        available_tools = ["search", "calculator"]

        mock_extract_tool_calls.return_value = []

        # Act
        result = should_use_tool(message, available_tools)

        # Assert
        self.assertFalse(result)

    @patch("src.tools.llm_integration.ToolParser.extract_tool_calls")
    def test_should_use_tool_false_unavailable(self, mock_extract_tool_calls):
        """Test that should_use_tool returns False when tool is not available."""
        # Arrange
        message = "Use the weather tool to check the forecast"
        available_tools = ["search", "calculator"]  # weather not in available tools

        mock_extract_tool_calls.return_value = [
            {"tool_name": "weather", "parameters": {"location": "New York"}}
        ]

        # Act
        result = should_use_tool(message, available_tools)

        # Assert
        self.assertFalse(result)
