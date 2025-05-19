"""
Test template flow.

This module tests the template flow, including:
1. Tool execution
2. State management
3. Error handling
"""

import os
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from src.sub_graphs.template_agent.src import template_tool
from src.sub_graphs.template_agent.src.state.state_models import (
    BaseMessage,
    MessageState,
    MessageStatus,
)

# Debug: Print MessageState class and its methods
print(f"[DEBUG] MessageState class: {MessageState}")
print(f"[DEBUG] MessageState methods: {dir(MessageState)}")

# Update tool config to enable parent inheritance
config_path = Path(__file__).parent.parent / "src" / "config" / "tool_config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)
config["tool_settings"]["inherit_from_parent"] = True
with open(config_path, "w") as f:
    yaml.dump(config, f)


def make_session_state():
    base_msg = BaseMessage(
        id="test_id",
        role="user",
        content="test content",
        timestamp=datetime.now(),
        metadata={},
        sender="tester",
        target="agent",
    )
    msg_state = MessageState(message=base_msg, status=MessageStatus.PENDING, metadata={})
    return {"conversation_state": msg_state}


@pytest.mark.asyncio
async def test_template_flow():
    """Test the template flow."""
    # Test data
    test_input = {
        "task": "test_task",
        "parameters": {"param1": "value1"},
        "request_id": "test_request_123",
        "timestamp": datetime.now().isoformat(),
    }

    # Execute tool
    result = await template_tool.execute(**test_input, session_state=make_session_state())

    # Verify result
    assert result["status"] == "success"
    assert "message" in result
    assert result["message"] == "Template tool executed successfully"


@pytest.mark.asyncio
async def test_template_tool_to_agent():
    """Test the basic flow from template_tool to template_agent."""

    # Create test input
    test_input = {
        "task": "run test tool 1",
        "parameters": {"tool_name": "test_tool_1", "input": "test input"},
        "request_id": "test-123",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Execute template tool
    result = await template_tool.execute(**test_input, session_state=make_session_state())

    # Verify result
    assert result["status"] == "success"
    assert "test_tool_1" in result["data"]["tool_name"]
    assert "test input" in result["data"]["test_input"]
    assert "test_file" in result["data"]

    # Verify test file was created
    test_file = result["data"]["test_file"]
    with open(test_file, "r") as f:
        content = f.read()
        assert "test_tool_1" in content
        assert "test input" in content
        assert "test-123" in content  # request_id
