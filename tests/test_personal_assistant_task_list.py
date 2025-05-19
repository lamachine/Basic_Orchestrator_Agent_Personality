"""
Tests for the personal assistant task list functionality.

These tests validate the implementation of basic task list functionality
directly in the personal assistant tool.
"""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, Field


# Models for task list functionality
class Task(BaseModel):
    """Model for a task."""

    id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = []
    priority: str = "medium"  # low, medium, high


class TaskListManager:
    """Simple task list manager implementation."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the task list manager."""
        self.tasks: Dict[str, Task] = {}
        self.storage_path = storage_path
        if storage_path:
            self.load_tasks()

    def load_tasks(self):
        """Load tasks from storage."""
        if not self.storage_path or not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, "r") as f:
                task_dicts = json.load(f)

            for task_dict in task_dicts:
                # Convert date strings to date objects
                if "due_date" in task_dict and task_dict["due_date"]:
                    task_dict["due_date"] = date.fromisoformat(task_dict["due_date"])
                if "created_at" in task_dict and task_dict["created_at"]:
                    task_dict["created_at"] = datetime.fromisoformat(task_dict["created_at"])
                if "completed_at" in task_dict and task_dict["completed_at"]:
                    task_dict["completed_at"] = datetime.fromisoformat(task_dict["completed_at"])

                task = Task(**task_dict)
                self.tasks[task.id] = task
        except Exception as e:
            print(f"Error loading tasks: {e}")

    def save_tasks(self):
        """Save tasks to storage."""
        if not self.storage_path:
            return

        try:
            # Convert tasks to dict for serialization
            task_dicts = []
            for task in self.tasks.values():
                task_dict = task.dict()
                # Convert date objects to strings
                if task_dict["due_date"]:
                    task_dict["due_date"] = task_dict["due_date"].isoformat()
                if task_dict["created_at"]:
                    task_dict["created_at"] = task_dict["created_at"].isoformat()
                if task_dict["completed_at"]:
                    task_dict["completed_at"] = task_dict["completed_at"].isoformat()

                task_dicts.append(task_dict)

            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump(task_dicts, f, indent=2)
        except Exception as e:
            print(f"Error saving tasks: {e}")

    def add_task(self, title: str, **kwargs) -> Task:
        """Add a new task."""
        task_id = f"task-{len(self.tasks) + 1}"
        task = Task(id=task_id, title=title, **kwargs)
        self.tasks[task_id] = task
        self.save_tasks()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """Update a task."""
        if task_id not in self.tasks:
            return None

        task_dict = self.tasks[task_id].dict()
        task_dict.update(kwargs)

        # Handle special case of completion
        if "completed" in kwargs and kwargs["completed"] and not self.tasks[task_id].completed:
            task_dict["completed_at"] = datetime.now()

        self.tasks[task_id] = Task(**task_dict)
        self.save_tasks()
        return self.tasks[task_id]

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id not in self.tasks:
            return False

        del self.tasks[task_id]
        self.save_tasks()
        return True

    def list_tasks(self, filter_params: Optional[Dict[str, Any]] = None) -> List[Task]:
        """List tasks with optional filtering."""
        if not filter_params:
            return list(self.tasks.values())

        filtered_tasks = []
        for task in self.tasks.values():
            include = True

            # Filter by completion status
            if "completed" in filter_params:
                if task.completed != filter_params["completed"]:
                    include = False

            # Filter by due date
            if "due_date" in filter_params:
                due_filter = filter_params["due_date"]
                today = date.today()

                if due_filter == "today" and task.due_date != today:
                    include = False
                elif due_filter == "tomorrow" and task.due_date != (today + timedelta(days=1)):
                    include = False
                elif due_filter == "this_week":
                    start_of_week = today - timedelta(days=today.weekday())
                    end_of_week = start_of_week + timedelta(days=6)
                    if not (task.due_date and start_of_week <= task.due_date <= end_of_week):
                        include = False

            # Filter by priority
            if "priority" in filter_params and task.priority != filter_params["priority"]:
                include = False

            # Filter by tags
            if "tags" in filter_params:
                if not set(filter_params["tags"]).issubset(set(task.tags)):
                    include = False

            if include:
                filtered_tasks.append(task)

        return filtered_tasks


# Test fixtures
@pytest.fixture
def temp_task_file():
    """Create a temporary file for task storage."""
    import tempfile

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)


@pytest.fixture
def task_manager(temp_task_file):
    """Create a task manager with temporary storage."""
    return TaskListManager(storage_path=temp_task_file)


@pytest.fixture
def mock_personal_assistant_with_tasks(temp_task_file):
    """Create a mock personal assistant with task functionality."""

    class PersonalAssistantWithTasks(BaseModel):
        name: str = "personal_assistant"
        description: str = "Handles tasks and other personal assistant functions"
        task_manager: TaskListManager = TaskListManager(storage_path=temp_task_file)

        async def execute(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
            """Execute a task with the personal assistant."""
            print(f"DEBUG: Executing task {task_id} with parameters {parameters}")
            action = parameters.get("action", "")

            try:
                if action == "add_task":
                    # Add a new task
                    title = parameters.get("title")
                    if not title:
                        return {
                            "status": "error",
                            "message": "Task title is required",
                            "task_id": task_id,
                            "tool_name": self.name,
                        }

                    # Optional parameters
                    description = parameters.get("description")
                    due_date_str = parameters.get("due_date")
                    due_date = None
                    if due_date_str:
                        if due_date_str == "today":
                            due_date = date.today()
                        elif due_date_str == "tomorrow":
                            due_date = date.today() + timedelta(days=1)
                        else:
                            try:
                                due_date = date.fromisoformat(due_date_str)
                            except ValueError:
                                return {
                                    "status": "error",
                                    "message": f"Invalid due date format: {due_date_str}",
                                    "task_id": task_id,
                                    "tool_name": self.name,
                                }

                    priority = parameters.get("priority", "medium")
                    tags = parameters.get("tags", [])

                    # Create the task
                    task = self.task_manager.add_task(
                        title=title,
                        description=description,
                        due_date=due_date,
                        priority=priority,
                        tags=tags,
                    )

                    return {
                        "status": "success",
                        "message": f"Task added: {title}",
                        "data": {
                            "task": {
                                "id": task.id,
                                "title": task.title,
                                "due_date": (task.due_date.isoformat() if task.due_date else None),
                                "priority": task.priority,
                            }
                        },
                        "task_id": task_id,
                        "tool_name": self.name,
                    }

                elif action == "list_tasks":
                    # List tasks with optional filtering
                    filter_params = {}
                    if "completed" in parameters:
                        filter_params["completed"] = parameters["completed"]
                    if "due_date" in parameters:
                        filter_params["due_date"] = parameters["due_date"]
                    if "priority" in parameters:
                        filter_params["priority"] = parameters["priority"]
                    if "tags" in parameters:
                        filter_params["tags"] = parameters["tags"]

                    tasks = self.task_manager.list_tasks(filter_params)

                    # Format tasks for response
                    task_list = []
                    for task in tasks:
                        task_list.append(
                            {
                                "id": task.id,
                                "title": task.title,
                                "due_date": (task.due_date.isoformat() if task.due_date else None),
                                "completed": task.completed,
                                "priority": task.priority,
                            }
                        )

                    return {
                        "status": "success",
                        "message": f"Found {len(tasks)} tasks",
                        "data": {"tasks": task_list},
                        "task_id": task_id,
                        "tool_name": self.name,
                    }

                elif action == "update_task":
                    # Update an existing task
                    task_id_to_update = parameters.get("task_id")
                    if not task_id_to_update:
                        return {
                            "status": "error",
                            "message": "Task ID is required for update",
                            "task_id": task_id,
                            "tool_name": self.name,
                        }

                    # Get parameters to update
                    update_params = {}
                    for field in [
                        "title",
                        "description",
                        "priority",
                        "tags",
                        "completed",
                    ]:
                        if field in parameters:
                            update_params[field] = parameters[field]

                    if "due_date" in parameters:
                        due_date_str = parameters["due_date"]
                        if due_date_str == "today":
                            update_params["due_date"] = date.today()
                        elif due_date_str == "tomorrow":
                            update_params["due_date"] = date.today() + timedelta(days=1)
                        elif due_date_str:
                            try:
                                update_params["due_date"] = date.fromisoformat(due_date_str)
                            except ValueError:
                                return {
                                    "status": "error",
                                    "message": f"Invalid due date format: {due_date_str}",
                                    "task_id": task_id,
                                    "tool_name": self.name,
                                }

                    updated_task = self.task_manager.update_task(task_id_to_update, **update_params)
                    if not updated_task:
                        return {
                            "status": "error",
                            "message": f"Task not found: {task_id_to_update}",
                            "task_id": task_id,
                            "tool_name": self.name,
                        }

                    return {
                        "status": "success",
                        "message": "Task updated successfully",
                        "data": {
                            "task": {
                                "id": updated_task.id,
                                "title": updated_task.title,
                                "due_date": (
                                    updated_task.due_date.isoformat()
                                    if updated_task.due_date
                                    else None
                                ),
                                "completed": updated_task.completed,
                                "priority": updated_task.priority,
                            }
                        },
                        "task_id": task_id,
                        "tool_name": self.name,
                    }

                elif action == "delete_task":
                    # Delete a task
                    task_id_to_delete = parameters.get("task_id")
                    if not task_id_to_delete:
                        return {
                            "status": "error",
                            "message": "Task ID is required for deletion",
                            "task_id": task_id,
                            "tool_name": self.name,
                        }

                    success = self.task_manager.delete_task(task_id_to_delete)
                    if not success:
                        return {
                            "status": "error",
                            "message": f"Task not found: {task_id_to_delete}",
                            "task_id": task_id,
                            "tool_name": self.name,
                        }

                    return {
                        "status": "success",
                        "message": "Task deleted successfully",
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

            except Exception as e:
                print(f"ERROR: Exception in task execution: {e}")
                return {
                    "status": "error",
                    "message": f"Error executing {action}: {str(e)}",
                    "task_id": task_id,
                    "tool_name": self.name,
                }

    return PersonalAssistantWithTasks()


# Tests that should pass
@pytest.mark.asyncio
async def test_add_task(mock_personal_assistant_with_tasks):
    """Test adding a task."""
    # Act
    result = await mock_personal_assistant_with_tasks.execute(
        task_id="test-add-1",
        parameters={
            "action": "add_task",
            "title": "Test task creation",
            "description": "This is a test task",
            "due_date": "today",
            "priority": "high",
        },
    )

    # Assert
    assert result["status"] == "success"
    assert "Task added" in result["message"]
    assert "task" in result["data"]
    assert result["data"]["task"]["title"] == "Test task creation"
    assert result["data"]["task"]["priority"] == "high"

    # Verify task was actually added to the manager
    task_id = result["data"]["task"]["id"]
    task = mock_personal_assistant_with_tasks.task_manager.get_task(task_id)
    assert task is not None
    assert task.title == "Test task creation"
    assert task.due_date == date.today()


@pytest.mark.asyncio
async def test_list_tasks(mock_personal_assistant_with_tasks):
    """Test listing tasks."""
    # Arrange - add some tasks
    await mock_personal_assistant_with_tasks.execute(
        task_id="test-list-setup-1",
        parameters={
            "action": "add_task",
            "title": "Task for today",
            "due_date": "today",
        },
    )

    await mock_personal_assistant_with_tasks.execute(
        task_id="test-list-setup-2",
        parameters={
            "action": "add_task",
            "title": "Task for tomorrow",
            "due_date": "tomorrow",
        },
    )

    # Act - list all tasks
    result = await mock_personal_assistant_with_tasks.execute(
        task_id="test-list-1", parameters={"action": "list_tasks"}
    )

    # Assert
    assert result["status"] == "success"
    assert "tasks" in result["data"]
    assert len(result["data"]["tasks"]) == 2

    # Act - list tasks due today
    result = await mock_personal_assistant_with_tasks.execute(
        task_id="test-list-2", parameters={"action": "list_tasks", "due_date": "today"}
    )

    # Assert
    assert result["status"] == "success"
    assert len(result["data"]["tasks"]) == 1
    assert result["data"]["tasks"][0]["title"] == "Task for today"


# Test that should fail
@pytest.mark.asyncio
async def test_add_task_without_title(mock_personal_assistant_with_tasks):
    """Test that adding a task without a title fails."""
    # Act
    result = await mock_personal_assistant_with_tasks.execute(
        task_id="test-add-no-title",
        parameters={"action": "add_task", "description": "This task has no title"},
    )

    # Assert
    assert result["status"] == "error"
    assert "title is required" in result["message"].lower()


# Edge cases
@pytest.mark.asyncio
async def test_update_task(mock_personal_assistant_with_tasks):
    """Test updating a task."""
    # Arrange - add a task
    add_result = await mock_personal_assistant_with_tasks.execute(
        task_id="test-update-setup",
        parameters={
            "action": "add_task",
            "title": "Original task title",
            "priority": "low",
        },
    )
    task_id_to_update = add_result["data"]["task"]["id"]

    # Act - update the task
    update_result = await mock_personal_assistant_with_tasks.execute(
        task_id="test-update-1",
        parameters={
            "action": "update_task",
            "task_id": task_id_to_update,
            "title": "Updated task title",
            "priority": "high",
            "completed": True,
        },
    )

    # Assert
    assert update_result["status"] == "success"
    assert update_result["data"]["task"]["title"] == "Updated task title"
    assert update_result["data"]["task"]["priority"] == "high"
    assert update_result["data"]["task"]["completed"] is True

    # Verify in manager
    task = mock_personal_assistant_with_tasks.task_manager.get_task(task_id_to_update)
    assert task.title == "Updated task title"
    assert task.completed is True
    assert task.completed_at is not None  # Should record completion time


@pytest.mark.asyncio
async def test_delete_task(mock_personal_assistant_with_tasks):
    """Test deleting a task."""
    # Arrange - add a task
    add_result = await mock_personal_assistant_with_tasks.execute(
        task_id="test-delete-setup",
        parameters={"action": "add_task", "title": "Task to delete"},
    )
    task_id_to_delete = add_result["data"]["task"]["id"]

    # Act - delete the task
    delete_result = await mock_personal_assistant_with_tasks.execute(
        task_id="test-delete-1",
        parameters={"action": "delete_task", "task_id": task_id_to_delete},
    )

    # Assert
    assert delete_result["status"] == "success"

    # Verify task was deleted
    list_result = await mock_personal_assistant_with_tasks.execute(
        task_id="test-delete-verify", parameters={"action": "list_tasks"}
    )

    assert len(list_result["data"]["tasks"]) == 0


@pytest.mark.asyncio
async def test_task_persistence(mock_personal_assistant_with_tasks, temp_task_file):
    """Test that tasks are persisted to storage."""
    # Arrange - add a task
    await mock_personal_assistant_with_tasks.execute(
        task_id="test-persistence-1",
        parameters={"action": "add_task", "title": "Persistent task"},
    )

    # Act - create a new manager with the same storage
    new_manager = TaskListManager(storage_path=temp_task_file)

    # Assert - task should be loaded
    assert len(new_manager.tasks) == 1
    task = list(new_manager.tasks.values())[0]
    assert task.title == "Persistent task"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
