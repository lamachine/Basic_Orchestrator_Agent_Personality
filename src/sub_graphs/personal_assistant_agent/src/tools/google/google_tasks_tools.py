"""
Google Tasks API Tools
"""

import json
import logging
import os
import sys
from functools import lru_cache
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build

from .credentials import CredentialsHandler, get_credentials

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@lru_cache(maxsize=1)
def get_tasks_service():
    """Get and cache the Google Tasks service."""
    creds = get_credentials()
    return build("tasks", "v1", credentials=creds)


# Task List Functions
def tasks_tasklists_delete(tasklist_id: str) -> str:
    """Delete a task list."""
    try:
        service = get_tasks_service()
        service.tasklists().delete(tasklist=tasklist_id).execute()
        return "Task list deleted successfully"
    except Exception as e:
        return f"Error deleting task list: {str(e)}"


def tasks_tasklists_get(tasklist_id: str) -> str:
    """Get a specific task list."""
    try:
        service = get_tasks_service()
        result = service.tasklists().get(tasklist=tasklist_id).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting task list: {str(e)}"


def tasks_tasklists_insert(title: str) -> str:
    """Create a new task list."""
    try:
        service = get_tasks_service()
        result = service.tasklists().insert(body={"title": title}).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error creating task list: {str(e)}"


def tasks_tasklists_list() -> str:
    """List all task lists."""
    try:
        service = get_tasks_service()
        results = service.tasklists().list().execute()
        return json.dumps(results.get("items", []), indent=2)
    except Exception as e:
        return f"Error listing task lists: {str(e)}"


def tasks_tasklists_patch(tasklist_id: str, title: str) -> str:
    """Update a task list's metadata."""
    try:
        service = get_tasks_service()
        result = service.tasklists().patch(tasklist=tasklist_id, body={"title": title}).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error patching task list: {str(e)}"


def tasks_tasklists_update(tasklist_id: str, title: str) -> str:
    """Replace a task list's metadata."""
    try:
        service = get_tasks_service()
        result = service.tasklists().update(tasklist=tasklist_id, body={"title": title}).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error updating task list: {str(e)}"


# Task Functions
def tasks_clear(tasklist_id: str) -> str:
    """Clear all completed tasks."""
    try:
        service = get_tasks_service()
        service.tasks().clear(tasklist=tasklist_id).execute()
        return "Completed tasks cleared successfully"
    except Exception as e:
        return f"Error clearing tasks: {str(e)}"


def tasks_delete(tasklist_id: str, task_id: str) -> str:
    """Delete a task."""
    try:
        service = get_tasks_service()
        service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
        return json.dumps(
            {
                "status": "success",
                "message": f"Task {task_id} deleted successfully",
                "tasklist_id": tasklist_id,
                "task_id": task_id,
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "status": "error",
                "message": f"Error deleting task {task_id}: {str(e)}",
                "tasklist_id": tasklist_id,
                "task_id": task_id,
            }
        )


def tasks_get(tasklist_id: str, task_id: str) -> str:
    """Get a specific task."""
    try:
        service = get_tasks_service()
        result = service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error getting task: {str(e)}"


def tasks_insert(tasklist_id: str, title: str, notes: str = "", due: str = None) -> str:
    """Create a new task."""
    try:
        service = get_tasks_service()
        body = {"title": title, "notes": notes}
        if due:
            body["due"] = due

        result = service.tasks().insert(tasklist=tasklist_id, body=body).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error creating task: {str(e)}"


def tasks_list(tasklist_id: str, max_results: int = 100) -> str:
    """List tasks in a task list."""
    try:
        service = get_tasks_service()
        results = (
            service.tasks()
            .list(
                tasklist=tasklist_id,
                maxResults=max_results,
                showCompleted=True,
                showDeleted=False,
                showHidden=True,
            )
            .execute()
        )

        # Format tasks to ensure IDs are prominently displayed
        formatted_tasks = []
        for index, task in enumerate(results.get("items", []), 1):
            formatted_tasks.append(
                {
                    "index": index,
                    "task_id": task["id"],  # Make task ID prominently displayed
                    "title": task.get("title", "No Title"),
                    "notes": task.get("notes", ""),
                    "status": task.get("status", "needsAction"),
                    "due": task.get("due", "Not specified"),
                }
            )

        # Return a more structured response
        response = {
            "tasklist_id": tasklist_id,
            "task_count": len(formatted_tasks),
            "tasks": formatted_tasks,
        }

        return json.dumps(response, indent=2)
    except Exception as e:
        return f"Error listing tasks: {str(e)}"


def tasks_move(tasklist_id: str, task_id: str, parent: str = None, previous: str = None) -> str:
    """Move a task."""
    try:
        service = get_tasks_service()
        result = (
            service.tasks()
            .move(tasklist=tasklist_id, task=task_id, parent=parent, previous=previous)
            .execute()
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error moving task: {str(e)}"


def tasks_patch(tasklist_id: str, task_id: str, **kwargs) -> str:
    """Update specific fields of a task."""
    try:
        service = get_tasks_service()
        body = {}
        if "title" in kwargs:
            body["title"] = kwargs["title"]
        if "notes" in kwargs:
            body["notes"] = kwargs["notes"]
        if "due" in kwargs:
            body["due"] = kwargs["due"]

        result = service.tasks().patch(tasklist=tasklist_id, task=task_id, body=body).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error patching task: {str(e)}"


def tasks_update(
    tasklist_id: str, task_id: str, title: str, notes: str = "", due: str = None
) -> str:
    """Replace all fields of a task."""
    try:
        service = get_tasks_service()
        body = {"title": title, "notes": notes}
        if due:
            body["due"] = due

        result = service.tasks().update(tasklist=tasklist_id, task=task_id, body=body).execute()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error updating task: {str(e)}"


# Direct testing
if __name__ == "__main__":
    print("\nTesting Google Tasks API:")
    try:
        # Test listing task lists
        print("\n1. Testing tasks_tasklists_list():")
        lists = tasks_tasklists_list()
        print(lists)

        # Test creating a task list
        print("\n2. Testing tasks_tasklists_insert():")
        list_result = tasks_tasklists_insert("Test List")
        print(list_result)
        list_id = json.loads(list_result)["id"]

        # Test creating a task
        print("\n3. Testing tasks_insert():")
        task_result = tasks_insert(
            tasklist_id=list_id, title="Test Task", notes="This is a test task"
        )
        print(task_result)
        task_id = json.loads(task_result)["id"]

        # Test getting task
        print("\n4. Testing tasks_get():")
        print(tasks_get(list_id, task_id))

        # Test updating task
        print("\n5. Testing tasks_update():")
        print(tasks_update(tasklist_id=list_id, task_id=task_id, title="Updated Test Task"))

        # Clean up
        print("\n6. Cleaning up:")
        print(tasks_delete(list_id, task_id))
        print(tasks_tasklists_delete(list_id))

        print("\nAll tests completed successfully!")

    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback

        print("\nFull traceback:")
        print(traceback.format_exc())
