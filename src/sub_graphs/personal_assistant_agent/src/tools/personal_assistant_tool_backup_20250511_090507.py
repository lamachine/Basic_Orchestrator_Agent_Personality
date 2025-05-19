"""Personal Assistant tool implementation."""

import asyncio
import json
import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional

from src.services.message_service import MessageRole, log_and_persist_message
from src.sub_graphs.personal_assistant_agent.src.tools.google import google_tasks_tools
from src.tools.orchestrator_tools import PENDING_TOOL_REQUESTS

# Set up logger
logger = logging.getLogger(__name__)


class PersonalAssistantTool:
    """Personal Assistant tool for handling emails, calendar, and tasks."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Personal Assistant tool.

        Args:
            config: Optional configuration dictionary loaded from tool_config.yaml
        """
        self.config = config or {}
        self.name = "personal_assistant"
        self.description = "Handles emails, messages, to-do lists, and calendar integration"
        logger.debug(f"Initialized {self.name} tool")

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a personal assistant task.

        Args:
            args: Dictionary containing task parameters
                task: The task string to process
                request_id: Optional request ID for tracking

        Returns:
            Dictionary with response data
        """
        task = args.get("task", "")
        request_id = args.get("request_id", f"req-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        session_state = args.get("session_state")

        logger.debug(f"[PA.execute] Start: request_id={request_id}, task={task}")

        # Log acknowledgement to LLM
        if session_state:
            await log_and_persist_message(
                session_state,
                MessageRole.ASSISTANT,
                "Valid tool request acknowledged.",
                metadata={"tool": self.name, "args": args, "request_id": request_id},
                sender="personal_assistant.graph",
                target="personal_assistant.llm",
            )

        # Determine which sub-tool to use based on the task string
        task_lower = task.lower()
        if any(word in task_lower for word in ["email", "inbox", "mail"]):
            logger.debug(
                f"[PA.execute] Routing to EMAIL_TOOL: request_id={request_id}, args={args}"
            )
            from src.sub_graphs.personal_assistant_agent.src.tools.personal_assistant_tool import (
                EMAIL_TOOL,
            )

            try:
                # Start the email operation in the background
                asyncio.create_task(self._handle_email_operation(EMAIL_TOOL, args, request_id))
                # Return immediately with a status message
                return {
                    "status": "processing",
                    "message": "Email operation started",
                    "request_id": request_id,
                }
            except Exception as e:
                logger.error(
                    f"[PA.execute] Error in EMAIL_TOOL: request_id={request_id}, error={e}"
                )
                return {"status": "error", "message": str(e), "request_id": request_id}
        if any(word in task_lower for word in ["task list", "task", "todo", "to-do"]):
            logger.debug(
                f"[PA.execute] Routing to TASKS_TOOL: request_id={request_id}, args={args}"
            )
            from src.sub_graphs.personal_assistant_agent.src.tools.personal_assistant_tool import (
                TASKS_TOOL,
            )

            try:
                # Start the task operation in the background
                asyncio.create_task(self._handle_task_operation(TASKS_TOOL, args, request_id))
                # Return immediately with a status message
                return {
                    "status": "processing",
                    "message": "Task list operation started",
                    "request_id": request_id,
                }
            except Exception as e:
                logger.error(
                    f"[PA.execute] Error in TASKS_TOOL: request_id={request_id}, error={e}"
                )
                return {"status": "error", "message": str(e), "request_id": request_id}
        # Fallback: handle 'task list' requests directly
        if "task list" in task_lower or ("task" in task_lower and "check" in task_lower):
            logger.debug(
                f"[PA.execute] Handling fallback dummy task list: request_id={request_id}, task={task}"
            )
            dummy_response = {
                "type": "result",
                "status": "success",
                "tool": self.name,
                "message": "Your task list: 1. Finish report, 2. Meet with team, 3. Book travel.",
                "data": {"tasks": ["Finish report", "Meet with team", "Book travel"]},
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
            }
            if session_state:
                await log_and_persist_message(
                    session_state,
                    MessageRole.ASSISTANT,
                    f"Returning dummy task list to orchestrator: {dummy_response}",
                    metadata={
                        "tool": self.name,
                        "response": dummy_response,
                        "request_id": request_id,
                    },
                    sender="personal_assistant.graph",
                    target="orchestrator.personal_assistant",
                )
            logger.debug(f"[PA.execute] Exit: request_id={request_id}, result={dummy_response}")
            return dummy_response
        logger.warning(
            f"[PA.execute] Unknown or unimplemented tool: request_id={request_id}, task={task}"
        )
        result = {
            "type": "error",
            "status": "error",
            "tool": self.name,
            "request_id": request_id,
            "message": f"Unknown or unimplemented tool for task: {task}",
            "timestamp": datetime.now().isoformat(),
        }
        logger.debug(f"[PA.execute] Exit: request_id={request_id}, result={result}")
        return result

    async def _handle_email_operation(self, email_tool, args: Dict[str, Any], request_id: str):
        """Handle email operations in the background."""
        try:
            email_response = await email_tool.execute(args)
            logger.debug(
                f"[PA.execute] Email tool response: request_id={request_id}, response={email_response}"
            )
            # Update the pending requests with the result
            if request_id in PENDING_TOOL_REQUESTS:
                PENDING_TOOL_REQUESTS[request_id] = email_response
        except Exception as e:
            logger.error(
                f"[PA.execute] Error in email operation: request_id={request_id}, error={e}"
            )
            if request_id in PENDING_TOOL_REQUESTS:
                PENDING_TOOL_REQUESTS[request_id] = {
                    "status": "error",
                    "message": str(e),
                    "request_id": request_id,
                }

    async def _handle_task_operation(self, task_tool, args: Dict[str, Any], request_id: str):
        """Handle task operations in the background."""
        try:
            task_response = await task_tool.execute(args)
            logger.debug(
                f"[PA.execute] Task tool response: request_id={request_id}, response={task_response}"
            )
            # Update the pending requests with the result
            if request_id in PENDING_TOOL_REQUESTS:
                PENDING_TOOL_REQUESTS[request_id] = task_response
        except Exception as e:
            logger.error(
                f"[PA.execute] Error in task operation: request_id={request_id}, error={e}"
            )
            if request_id in PENDING_TOOL_REQUESTS:
                PENDING_TOOL_REQUESTS[request_id] = {
                    "status": "error",
                    "message": str(e),
                    "request_id": request_id,
                }

    async def _handle_email_task(self, task: str) -> Dict[str, Any]:
        """Handle email-related tasks."""
        await asyncio.sleep(1)  # Simulate API call

        return {
            "status": "success",
            "message": f"Email task processed: '{task}'",
            "data": {
                "task_type": "email",
                "email_account": self.config.get("default_email", "user@example.com"),
                "details": "This is a simulated email response. In a real implementation, this would connect to an email API.",
            },
        }

    async def _handle_calendar_task(self, task: str) -> Dict[str, Any]:
        """Handle calendar-related tasks."""
        await asyncio.sleep(1.5)  # Simulate API call

        return {
            "status": "success",
            "message": f"Calendar task processed: '{task}'",
            "data": {
                "task_type": "calendar",
                "timezone": self.config.get("default_timezone", "UTC"),
                "details": "This is a simulated calendar response. In a real implementation, this would connect to a calendar API.",
            },
        }

    async def _handle_task_management(self, task: str) -> Dict[str, Any]:
        """Handle task management."""
        await asyncio.sleep(0.5)  # Simulate API call

        return {
            "status": "success",
            "message": f"Task management request processed: '{task}'",
            "data": {
                "task_type": "task_management",
                "details": "This is a simulated task management response. In a real implementation, this would connect to a task management API.",
            },
        }

    async def _handle_reminder(self, task: str) -> Dict[str, Any]:
        """Handle reminders."""
        await asyncio.sleep(0.5)  # Simulate API call

        return {
            "status": "success",
            "message": f"Reminder set: '{task}'",
            "data": {
                "task_type": "reminder",
                "details": "This is a simulated reminder response. In a real implementation, this would connect to a reminder/calendar API.",
            },
        }


class DummyEmailTool:
    """Dummy tool for checking new email."""

    name = "email"

    def __init__(self, **kwargs):
        pass

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio

        await asyncio.sleep(5)  # Simulate delay
        task = args.get("task", "")
        request_id = args.get("request_id", "unknown")
        if "check" in task and "email" in task:
            return {
                "type": "result",
                "status": "success",
                "tool": self.name,
                "message": "Dummy: No new email found (dummy response).",
                "data": {
                    "emails": [
                        {
                            "id": "dummy123",
                            "threadId": "dummy-thread-1",
                            "labelIds": ["INBOX", "IMPORTANT"],
                            "snippet": "This is a dummy email snippet.",
                            "historyId": "dummy-history-1",
                            "internalDate": "1650000000000",
                        }
                    ],
                    "dummy": True,
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
            }
        return {
            "type": "error",
            "status": "error",
            "tool": self.name,
            "message": f"Unknown or unsupported email task: {task}",
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
        }


class GoogleTasksTool:
    """Tool for reading tasks from Google Tasks using google_tasks_tools."""

    name = "tasks"

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        task = args.get("task", "")
        if "read" in task and "task" in task:
            try:
                # Get the default tasklist (first one)
                tasklists_json = google_tasks_tools.tasks_tasklists_list()
                tasklists = json.loads(tasklists_json)
                if not tasklists:
                    return {
                        "type": "result",
                        "status": "success",
                        "tool": self.name,
                        "message": "No task lists found.",
                        "data": {"tasks": []},
                        "timestamp": datetime.now().isoformat(),
                    }
                default_tasklist_id = tasklists[0]["id"]
                tasks_json = google_tasks_tools.tasks_list(default_tasklist_id)
                tasks = json.loads(tasks_json)
                return {
                    "type": "result",
                    "status": "success",
                    "tool": self.name,
                    "message": f"Read {tasks.get('task_count', 0)} tasks from Google Tasks.",
                    "data": tasks,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                logger.error(f"Error reading tasks: {e}")
                return {
                    "type": "error",
                    "status": "error",
                    "tool": self.name,
                    "message": f"Error reading tasks: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
        return {
            "type": "error",
            "status": "error",
            "tool": self.name,
            "message": f"Unknown or unsupported tasks command: {task}",
            "timestamp": datetime.now().isoformat(),
        }


# Export tools for sub-graph access
EMAIL_TOOL = DummyEmailTool()
TASKS_TOOL = GoogleTasksTool()
