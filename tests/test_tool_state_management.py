"""
Tests for tool state management and persistence.

These tests validate that tool state is properly managed and persisted,
conversation history is tracked, and state can be restored after restart.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel


class TaskState(BaseModel):
    """Model for task state storage."""

    task_id: str
    status: str = "pending"
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    parameters: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None


class ConversationEntry(BaseModel):
    """Model for a conversation entry."""

    message_id: str
    timestamp: str
    sender: str  # "user" or "assistant" or "tool"
    content: str
    tool_calls: List[Dict[str, Any]] = []
    tool_results: List[Dict[str, Any]] = []


class ToolState(BaseModel):
    """Model for tool state storage."""

    tool_name: str
    tasks: Dict[str, TaskState] = {}
    conversation_history: List[ConversationEntry] = []
    custom_state: Dict[str, Any] = {}


# Test fixtures
@pytest.fixture
def temp_state_dir():
    """Create a temporary directory for state files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_tool_with_state(temp_state_dir):
    """Create a mock tool with state management."""

    class PersonalAssistantWithState(BaseModel):
        name: str = "personal_assistant"
        description: str = "Handles messages, emails, calendar, and tasks"
        state_file: str = os.path.join(temp_state_dir, "personal_assistant_state.json")
        state: ToolState = ToolState(tool_name="personal_assistant")

        def __init__(self, **data):
            super().__init__(**data)
            self.load_state()

        def save_state(self):
            """Save state to disk."""
            print(f"DEBUG: Saving state to {self.state_file}")
            state_dict = self.state.dict()
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(state_dict, f, indent=2)

        def load_state(self):
            """Load state from disk if it exists."""
            if os.path.exists(self.state_file):
                print(f"DEBUG: Loading state from {self.state_file}")
                with open(self.state_file, "r") as f:
                    state_dict = json.load(f)
                self.state = ToolState(**state_dict)
            else:
                print(f"DEBUG: No state file found at {self.state_file}")
                self.state = ToolState(tool_name=self.name)

        def add_to_conversation(self, entry: Dict[str, Any]):
            """Add an entry to the conversation history."""
            self.state.conversation_history.append(ConversationEntry(**entry))
            self.save_state()

        def add_task(self, task_id: str, parameters: Dict[str, Any]):
            """Add a task to the state."""
            from datetime import datetime

            self.state.tasks[task_id] = TaskState(
                task_id=task_id,
                created_at=datetime.now().isoformat(),
                parameters=parameters,
            )
            self.save_state()

        def update_task(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None):
            """Update a task in the state."""
            from datetime import datetime

            if task_id in self.state.tasks:
                task = self.state.tasks[task_id]
                task.status = status
                if status == "completed":
                    task.completed_at = datetime.now().isoformat()
                if result:
                    task.result = result
                self.save_state()

        def get_task(self, task_id: str) -> Optional[TaskState]:
            """Get a task from the state."""
            return self.state.tasks.get(task_id)

        async def execute(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
            """Execute a task and update state."""
            from datetime import datetime

            # Record the task
            self.add_task(task_id, parameters)

            # Process the task
            action = parameters.get("action", "")

            if action == "add_task":
                # Add a user task to our state
                task_title = parameters.get("title", "Untitled Task")
                task_due = parameters.get("due", "today")

                new_task = {
                    "id": f"task-{len(self.state.custom_state.get('tasks', []))+1}",
                    "title": task_title,
                    "due": task_due,
                }

                # Initialize tasks if not present
                if "tasks" not in self.state.custom_state:
                    self.state.custom_state["tasks"] = []

                self.state.custom_state["tasks"].append(new_task)
                self.save_state()

                result = {
                    "status": "success",
                    "message": f"Added task: {task_title}",
                    "data": {"task": new_task},
                    "task_id": task_id,
                    "tool_name": self.name,
                }

            elif action == "list_tasks":
                # List tasks from our state
                tasks = self.state.custom_state.get("tasks", [])
                filter_param = parameters.get("filter", "all")

                if filter_param != "all":
                    tasks = [t for t in tasks if t["due"] == filter_param]

                result = {
                    "status": "success",
                    "message": f"Found {len(tasks)} tasks",
                    "data": {"tasks": tasks},
                    "task_id": task_id,
                    "tool_name": self.name,
                }

            else:
                result = {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "task_id": task_id,
                    "tool_name": self.name,
                }

            # Record the result
            self.update_task(task_id, "completed", result)

            # Add to conversation history
            self.add_to_conversation(
                {
                    "message_id": f"msg-{len(self.state.conversation_history)+1}",
                    "timestamp": datetime.now().isoformat(),
                    "sender": "tool",
                    "content": result["message"],
                    "tool_results": [result],
                }
            )

            return result

    return PersonalAssistantWithState()


# Tests that should pass
@pytest.mark.asyncio
async def test_tool_state_persistence(mock_tool_with_state):
    """Test that tool state is properly persisted."""
    # Arrange - make sure we start with clean state
    assert len(mock_tool_with_state.state.tasks) == 0
    assert len(mock_tool_with_state.state.conversation_history) == 0

    # Act - execute a task
    result = await mock_tool_with_state.execute(
        task_id="test-state-1",
        parameters={
            "action": "add_task",
            "title": "Test state persistence",
            "due": "today",
        },
    )

    # Assert - state should be updated and persisted
    assert result["status"] == "success"
    assert "test-state-1" in mock_tool_with_state.state.tasks
    assert len(mock_tool_with_state.state.conversation_history) == 1
    assert len(mock_tool_with_state.state.custom_state["tasks"]) == 1

    # Verify the file exists and has content
    assert os.path.exists(mock_tool_with_state.state_file)
    with open(mock_tool_with_state.state_file, "r") as f:
        saved_state = json.load(f)

    assert saved_state["tool_name"] == "personal_assistant"
    assert "test-state-1" in saved_state["tasks"]
    assert len(saved_state["conversation_history"]) == 1


@pytest.mark.asyncio
async def test_tool_state_restoration(mock_tool_with_state):
    """Test that tool state can be restored after restart."""
    # Arrange - create some state
    await mock_tool_with_state.execute(
        task_id="test-state-2",
        parameters={
            "action": "add_task",
            "title": "Task before restart",
            "due": "today",
        },
    )

    # Get the state file path
    state_file = mock_tool_with_state.state_file

    # Act - "restart" the tool by creating a new instance
    restarted_tool = type(mock_tool_with_state)(state_file=state_file)

    # Assert - state should be restored
    assert len(restarted_tool.state.tasks) > 0
    assert "test-state-2" in restarted_tool.state.tasks
    assert len(restarted_tool.state.conversation_history) > 0
    assert len(restarted_tool.state.custom_state["tasks"]) > 0

    # Should be able to continue adding tasks
    result = await restarted_tool.execute(
        task_id="test-state-3",
        parameters={
            "action": "add_task",
            "title": "Task after restart",
            "due": "tomorrow",
        },
    )

    assert result["status"] == "success"
    assert len(restarted_tool.state.custom_state["tasks"]) == 2


# Test that should fail
@pytest.mark.asyncio
async def test_state_management_with_invalid_task(mock_tool_with_state):
    """Test that the tool properly handles invalid tasks in state management."""
    # Act - execute a task with invalid action
    result = await mock_tool_with_state.execute(
        task_id="test-invalid", parameters={"action": "invalid_action"}
    )

    # Assert - should get error but state should still be updated
    assert result["status"] == "error"
    assert "Unknown action" in result["message"]

    # The task should still be recorded in state
    assert "test-invalid" in mock_tool_with_state.state.tasks
    assert mock_tool_with_state.state.tasks["test-invalid"].status == "completed"

    # And should be in conversation history
    found = False
    for entry in mock_tool_with_state.state.conversation_history:
        if "Unknown action" in entry.content:
            found = True
            break
    assert found


# Edge cases
@pytest.mark.asyncio
async def test_state_with_conversation_tracking(mock_tool_with_state):
    """Test that conversation history is properly tracked."""
    # Arrange - clear conversation history
    mock_tool_with_state.state.conversation_history = []
    mock_tool_with_state.save_state()

    # Act - execute multiple tasks
    await mock_tool_with_state.execute(
        task_id="test-convo-1",
        parameters={
            "action": "add_task",
            "title": "First conversation task",
            "due": "today",
        },
    )

    await mock_tool_with_state.execute(task_id="test-convo-2", parameters={"action": "list_tasks"})

    # Assert - conversation history should contain all interactions
    assert len(mock_tool_with_state.state.conversation_history) == 2

    # First entry should be about adding a task
    assert "Added task" in mock_tool_with_state.state.conversation_history[0].content

    # Second entry should be about listing tasks
    assert "Found" in mock_tool_with_state.state.conversation_history[1].content


@pytest.mark.asyncio
async def test_state_handles_missing_state_file(temp_state_dir):
    """Test that the tool can initialize with missing state file."""
    # Arrange - specify a non-existent state file
    non_existent_file = os.path.join(temp_state_dir, "does_not_exist.json")
    assert not os.path.exists(non_existent_file)

    # Act - create tool with non-existent state file
    tool = PersonalAssistantWithState = type(
        "PersonalAssistantWithState",
        (BaseModel,),
        {
            "__annotations__": {
                "name": str,
                "description": str,
                "state_file": str,
                "state": ToolState,
            },
            "name": "personal_assistant",
            "description": "Handles messages, emails, calendar, and tasks",
            "state_file": non_existent_file,
            "state": ToolState(tool_name="personal_assistant"),
            "load_state": mock_tool_with_state.load_state,
            "save_state": mock_tool_with_state.save_state,
            "add_to_conversation": mock_tool_with_state.add_to_conversation,
            "add_task": mock_tool_with_state.add_task,
            "update_task": mock_tool_with_state.update_task,
            "get_task": mock_tool_with_state.get_task,
            "execute": mock_tool_with_state.execute,
            "__init__": mock_tool_with_state.__init__,
        },
    )()

    # Assert - should initialize with empty state
    assert tool.state.tool_name == "personal_assistant"
    assert len(tool.state.tasks) == 0
    assert len(tool.state.conversation_history) == 0

    # Should be able to execute tasks and create state
    result = await tool.execute(
        task_id="test-missing-state",
        parameters={
            "action": "add_task",
            "title": "New task with missing state",
            "due": "today",
        },
    )

    assert result["status"] == "success"
    assert os.path.exists(non_existent_file)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
