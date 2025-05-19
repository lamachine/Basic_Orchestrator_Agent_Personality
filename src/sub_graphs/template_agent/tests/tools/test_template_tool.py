"""Tests for template tool functionality."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from ..src.specialty.tools.template_tool import TemplateTool, ToolInput


@pytest.fixture
def template_tool():
    """Provide a template tool instance."""
    return TemplateTool()


def test_tool_initialization(template_tool):
    """Test tool initialization."""
    assert template_tool.name == "template_tool"
    assert template_tool.version == "1.0.0"
    assert "run_test_tool" in template_tool.capabilities
    assert template_tool.agent is not None


def test_tool_input_validation():
    """Test tool input validation."""
    # Valid input
    valid_input = {
        "task": "test task",
        "parameters": {"param": "value"},
        "request_id": "test-123",
        "timestamp": datetime.now().isoformat(),
    }
    input_model = ToolInput(**valid_input)
    assert input_model.task == valid_input["task"]
    assert input_model.parameters == valid_input["parameters"]

    # Invalid input (missing required field)
    with pytest.raises(Exception):  # Should raise validation error
        ToolInput(
            parameters={"param": "value"},
            request_id="test-123",
            timestamp=datetime.now().isoformat(),
        )


@pytest.mark.asyncio
async def test_execute_success(template_tool, mock_session_state):
    """Test successful tool execution."""
    # Mock agent's process_message
    template_tool.agent.process_message = Mock(
        return_value={"status": "success", "response": "test response"}
    )

    result = await template_tool.execute(
        session_state=mock_session_state,
        task="test task",
        parameters={},
        request_id="test-123",
        timestamp=datetime.now().isoformat(),
    )

    assert result["status"] == "success"
    assert result["response"] == "test response"
    template_tool.agent.process_message.assert_called_once()


@pytest.mark.asyncio
async def test_execute_validation_error(template_tool, mock_session_state):
    """Test tool execution with invalid input."""
    # Missing required fields
    result = await template_tool.execute(
        session_state=mock_session_state,
        task="test task",  # Missing other required fields
    )

    assert result["status"] == "error"
    assert "validation error" in result["message"].lower()


@pytest.mark.asyncio
async def test_execute_processing_error(template_tool, mock_session_state):
    """Test tool execution with processing error."""
    # Mock agent to raise an exception
    template_tool.agent.process_message = Mock(side_effect=Exception("Processing error"))

    result = await template_tool.execute(
        session_state=mock_session_state,
        task="test task",
        parameters={},
        request_id="test-123",
        timestamp=datetime.now().isoformat(),
    )

    assert result["status"] == "error"
    assert "Processing error" in result["message"]


@pytest.mark.asyncio
async def test_execute_with_session_state(template_tool, mock_session_state):
    """Test tool execution with session state handling."""
    # Mock agent's process_message
    template_tool.agent.process_message = Mock(
        return_value={"status": "success", "response": "test response"}
    )

    await template_tool.execute(
        session_state=mock_session_state,
        task="test task",
        parameters={},
        request_id="test-123",
        timestamp=datetime.now().isoformat(),
    )

    # Verify session state was passed to agent
    template_tool.agent.process_message.assert_called_once_with(
        "test task", session_state=mock_session_state
    )
