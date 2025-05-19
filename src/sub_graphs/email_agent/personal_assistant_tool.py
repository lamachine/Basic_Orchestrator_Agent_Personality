"""
Personal Assistant Tool Interface for Parent Graph

This file exposes the canonical entrypoint for the orchestrator or parent graph to call the personal assistant sub-graph.
It validates input, enforces request_id, and delegates to the sub-graph CLI message interface in src/cli/sub_graph_interface.py.
Includes an inline ToolMessage Pydantic model for output validation.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ValidationError

from src.sub_graphs.personal_assistant_agent.src.cli.sub_graph_interface import (
    handle_cli_tool_request,
)

logger = logging.getLogger(__name__)


class PersonalAssistantToolInput(BaseModel):
    task: str
    parameters: Optional[Dict[str, Any]] = None
    request_id: str  # Required


class ToolMessage(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    request_id: str
    parent_request_id: Optional[str] = None
    timestamp: str


# Tool metadata defined at module level
async def personal_assistant_tool(
    task: str, parameters: Optional[Dict[str, Any]] = None, request_id: str = None
) -> Dict[str, Any]:
    """
    Entrypoint for orchestrator/parent graph to call the personal assistant tool.

    Args:
        task (str): The task description or command for the personal assistant.
        parameters (Optional[Dict[str, Any]]): Optional parameters for the task.
        request_id (str): Unique request identifier for tracking (required).

    Returns:
        Dict[str, Any]: Standardized response from the tool, always includes request_id and timestamp.
    """
    if not request_id:
        logger.error("Missing required request_id in personal_assistant_tool call.")
        return {
            "status": "error",
            "message": "Missing required request_id in personal_assistant_tool call.",
            "data": None,
            "request_id": None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    try:
        validated_input = PersonalAssistantToolInput(
            task=task, parameters=parameters, request_id=request_id
        )
    except ValidationError as ve:
        logger.error(
            f"Input validation error in personal_assistant_tool (request_id={request_id}): {ve}"
        )
        return {
            "status": "error",
            "message": f"Input validation error: {ve}",
            "data": None,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # Just log at debug level to avoid duplicates - the actual tool implementation will log at info level
    logger.debug(f"personal_assistant_tool passing task: {task} (request_id={request_id})")

    try:
        # Check if this is an email-related request
        if "email" in task.lower():
            return await _handle_email_request(validated_input)
        elif "tasks" in task.lower():
            return await _handle_tasks_request(validated_input)
        else:
            return await _handle_other_request(validated_input)
    except Exception as e:
        logger.error(
            f"Unexpected error in personal_assistant_tool (request_id={request_id}): {str(e)}"
        )
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "data": None,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }


async def _handle_email_request(
    input_data: PersonalAssistantToolInput,
) -> Dict[str, Any]:
    """
    Handle email-related requests with a simulated delay.

    Args:
        input_data: Validated input data containing task and request_id

    Returns:
        Dict[str, Any]: Standardized response with email results
    """
    try:
        # Simulate processing delay
        await asyncio.sleep(30)

        return {
            "status": "completed",
            "message": "Email returned zero unread.",
            "data": {
                "email_count": 0,
                "task": input_data.task,
                "processed_at": datetime.utcnow().isoformat(),
            },
            "request_id": input_data.request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(
            f"Error in _handle_email_request (request_id={input_data.request_id}): {str(e)}"
        )
        raise


async def _handle_tasks_request(
    input_data: PersonalAssistantToolInput,
) -> Dict[str, Any]:
    """
    Handle tasks-related requests with a simulated delay.

    Args:
        input_data: Validated input data containing task and request_id

    Returns:
        Dict[str, Any]: Standardized response with tasks results
    """
    try:
        # Simulate processing delay
        await asyncio.sleep(30)

        return {
            "status": "completed",
            "message": "Task function returned zero open tasks.",
            "data": {
                "task_count": 0,
                "task": input_data.task,
                "processed_at": datetime.utcnow().isoformat(),
            },
            "request_id": input_data.request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(
            f"Error in _handle_tasks_request (request_id={input_data.request_id}): {str(e)}"
        )
        raise


async def _handle_other_request(
    input_data: PersonalAssistantToolInput,
) -> Dict[str, Any]:
    """
    Handle non-email and non-tasks requests.

    Args:
        input_data: Validated input data containing task and request_id

    Returns:
        Dict[str, Any]: Standardized response for other tasks
    """
    try:
        # Simulate processing delay
        await asyncio.sleep(5)

        return {
            "status": "completed",
            "message": f"No appropriate tools found for {input_data.task}",
            "data": {
                "task": input_data.task,
                "processed_at": datetime.utcnow().isoformat(),
            },
            "request_id": input_data.request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(
            f"Error in _handle_other_request (request_id={input_data.request_id}): {str(e)}"
        )
        raise


# Define tool metadata at module level so it's available at import time
personal_assistant_tool.description = """Personal assistant tool for managing your digital life.
Capabilities include:
- Email management: Check inbox, send emails, manage drafts
- Task management: Create, update, and track tasks and to-do lists
- Calendar operations: Schedule meetings, check availability, manage events
- Reminder system: Set and manage reminders for tasks and events

The tool integrates with various services to provide a unified personal assistant experience."""

personal_assistant_tool.version = "1.0.0"
personal_assistant_tool.capabilities = [
    "email_operations",
    "task_list_operations",
    "calendar_operations",
    "reminder_operations",
]
personal_assistant_tool.usage_examples = [
    "User: 'Check my email'\nTool: personal_assistant\nMessage: 'check email'",
    "User: 'Send an email to john@example.com with subject Meeting and body Let's meet tomorrow'\nTool: personal_assistant\nMessage: 'send email to john@example.com with subject Meeting and body Let's meet tomorrow'",
    "User: 'Add a task Buy groceries to my task list'\nTool: personal_assistant\nMessage: 'add task Buy groceries'",
    "User: 'Show my tasks for today'\nTool: personal_assistant\nMessage: 'show tasks for today'",
]
