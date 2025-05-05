"""
Personal Assistant Tool Interface for Parent Graph

This file exposes the canonical entrypoint for the orchestrator or parent graph to call the personal assistant sub-graph.
It validates input, enforces request_id, and delegates to the sub-graph CLI message interface in src/cli/sub_graph_interface.py.
Includes an inline ToolMessage Pydantic model for output validation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, ValidationError

from src.sub_graphs.personal_assistant_agent.src.cli.sub_graph_interface import handle_cli_tool_request

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

def personal_assistant_tool(task: str, parameters: Optional[Dict[str, Any]] = None, request_id: str = None) -> Dict[str, Any]:
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
            "timestamp": datetime.utcnow().isoformat()
        }
    try:
        validated_input = PersonalAssistantToolInput(task=task, parameters=parameters, request_id=request_id)
    except ValidationError as ve:
        logger.error(f"Input validation error in personal_assistant_tool (request_id={request_id}): {ve}")
        return {
            "status": "error",
            "message": f"Input validation error: {ve}",
            "data": None,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    logger.info(f"personal_assistant_tool received task: {task} (request_id={request_id})")
    logger.debug(f"personal_assistant_tool parameters: {parameters} (request_id={request_id})")
    try:
        response = handle_cli_tool_request(validated_input.task, validated_input.parameters, validated_input.request_id)
        ToolMessage.parse_obj(response)
        response["request_id"] = request_id
        response["timestamp"] = response.get("timestamp", datetime.utcnow().isoformat())
        return response
    except ValidationError as ve:
        logger.error(f"Output validation error in personal_assistant_tool (request_id={request_id}): {ve}")
        return {
            "status": "error",
            "message": f"Output validation error: {ve}",
            "data": None,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in personal_assistant_tool (request_id={request_id}): {e}")
        return {
            "status": "error",
            "message": f"Error in personal_assistant_tool: {str(e)}",
            "data": None,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        } 