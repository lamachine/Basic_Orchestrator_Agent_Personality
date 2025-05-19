"""
Tests for the modular agent structure.

These tests validate that the modular structure works correctly, with proper
abstraction between layers and clean interfaces.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel


# Test fixtures
@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator that interacts with tools."""

    class OrchestratorMock:
        def __init__(self):
            self.tools = {}
            self.tool_calls = []
            self.tool_results = {}

        def register_tool(self, tool_name, tool_interface):
            """Register a tool with the orchestrator."""
            self.tools[tool_name] = tool_interface

        async def call_tool(self, tool_name, task_id, parameters):
            """Call a tool and store the result."""
            if tool_name not in self.tools:
                return {"status": "error", "message": f"Tool {tool_name} not found"}

            # Record the call
            self.tool_calls.append(
                {"tool_name": tool_name, "task_id": task_id, "parameters": parameters}
            )

            # Call the tool
            tool = self.tools[tool_name]
            result = await tool.execute(task_id=task_id, parameters=parameters)

            # Store the result
            self.tool_results[task_id] = result

            return result

    return OrchestratorMock()


@pytest.fixture
def mock_personal_assistant():
    """Create a mock personal assistant tool."""

    class PersonalAssistantMock(BaseModel):
        name: str = "personal_assistant"
        description: str = "Handles messages, emails, calendar, and tasks"

        # Behind the scenes implementation (should be hidden from orchestrator)
        _internal_state: Dict[str, Any] = {
            "tasks": [
                {"id": "1", "title": "Test the interface", "due": "today"},
                {"id": "2", "title": "Implement task list", "due": "tomorrow"},
            ]
        }

        async def execute(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
            """Execute a task with the personal assistant."""
            print(f"DEBUG: PA executing task {task_id} with parameters {parameters}")

            action = parameters.get("action", "")

            if action == "read_tasks":
                # Simulate internal processing
                filter_param = parameters.get("filter", "all")

                # This logic would normally be in an internal implementation class
                tasks = self._internal_state["tasks"]
                if filter_param != "all":
                    tasks = [t for t in tasks if t["due"] == filter_param]

                return {
                    "status": "success",
                    "message": f"Found {len(tasks)} tasks",
                    "data": {"tasks": tasks},
                    "task_id": task_id,
                    "tool_name": self.name,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "task_id": task_id,
                    "tool_name": self.name,
                }

    return PersonalAssistantMock()


# Tests that should pass
@pytest.mark.asyncio
async def test_orchestrator_tool_abstraction(mock_orchestrator, mock_personal_assistant):
    """Test that the orchestrator can use tools without knowing implementation details."""
    # Arrange
    mock_orchestrator.register_tool(mock_personal_assistant.name, mock_personal_assistant)

    # Act - orchestrator calls the tool
    result = await mock_orchestrator.call_tool(
        tool_name="personal_assistant",
        task_id="test-abstraction",
        parameters={"action": "read_tasks", "filter": "today"},
    )

    # Assert - orchestrator gets proper result without knowing internal details
    assert result["status"] == "success"
    assert "tasks" in result["data"]

    # The orchestrator should not have direct access to the tool's internal state
    assert not hasattr(mock_orchestrator, "_internal_state")

    # The tool call should be recorded
    assert len(mock_orchestrator.tool_calls) == 1
    assert mock_orchestrator.tool_calls[0]["tool_name"] == "personal_assistant"
    assert mock_orchestrator.tool_calls[0]["task_id"] == "test-abstraction"


# Test that should fail
@pytest.mark.asyncio
async def test_orchestrator_with_missing_tool(mock_orchestrator):
    """Test that the orchestrator handles missing tools appropriately."""
    # Act - try to call a tool that doesn't exist
    result = await mock_orchestrator.call_tool(
        tool_name="nonexistent_tool",
        task_id="test-missing",
        parameters={"action": "something"},
    )

    # Assert - should get an error response
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


# Edge cases
@pytest.mark.asyncio
async def test_tool_internal_complexity_hidden(mock_orchestrator, mock_personal_assistant):
    """Test that complex internal tool logic is hidden from the orchestrator."""
    # Arrange - modify internal state of the tool
    original_tasks = mock_personal_assistant._internal_state["tasks"].copy()
    mock_personal_assistant._internal_state["tasks"].append(
        {"id": "3", "title": "Secret task", "due": "today"}
    )
    mock_orchestrator.register_tool(mock_personal_assistant.name, mock_personal_assistant)

    # Act - orchestrator calls the tool
    result = await mock_orchestrator.call_tool(
        tool_name="personal_assistant",
        task_id="test-complexity",
        parameters={"action": "read_tasks", "filter": "today"},
    )

    # Assert - orchestrator gets the updated results but knows nothing about how it's stored
    assert result["status"] == "success"
    assert len(result["data"]["tasks"]) == 2  # Should now have 2 tasks for today

    # The orchestrator should not be able to directly access or modify the tool's state
    with pytest.raises(AttributeError):
        mock_orchestrator.tools["personal_assistant"]._internal_state = {}

    # Clean up
    mock_personal_assistant._internal_state["tasks"] = original_tasks


@pytest.mark.asyncio
async def test_tool_handles_unknown_actions(mock_orchestrator, mock_personal_assistant):
    """Test that tools properly handle unknown actions without breaking abstraction."""
    # Arrange
    mock_orchestrator.register_tool(mock_personal_assistant.name, mock_personal_assistant)

    # Act - call with an action the tool doesn't support
    result = await mock_orchestrator.call_tool(
        tool_name="personal_assistant",
        task_id="test-unknown",
        parameters={"action": "fly_to_moon"},
    )

    # Assert - should get an error but maintain the interface
    assert result["status"] == "error"
    assert "unknown action" in result["message"].lower()
    assert result["task_id"] == "test-unknown"
    assert result["tool_name"] == "personal_assistant"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
