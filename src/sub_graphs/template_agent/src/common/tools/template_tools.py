"""
Template-specific tool handling functionality.

This module provides functions for managing tool requests and completions
specific to the template agent implementation.
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Dictionary to store pending tool requests
PENDING_TOOL_REQUESTS = {}


def check_completed_tool_requests() -> Dict[str, Dict[str, Any]]:
    """
    Check for completed tool requests.

    Returns:
        Dictionary of completed tool requests with their results
    """
    completed = {}
    for request_id, request in PENDING_TOOL_REQUESTS.items():
        if request.get("status") == "completed":
            completed[request_id] = request
    return completed


def cleanup_processed_request(request_id: str) -> None:
    """
    Clean up a processed tool request.

    Args:
        request_id: ID of the request to clean up
    """
    if request_id in PENDING_TOOL_REQUESTS:
        del PENDING_TOOL_REQUESTS[request_id]


def create_tool_request(
    tool_name: str, params: Dict[str, Any], original_query: Optional[str] = None
) -> str:
    """
    Create a new tool request.

    Args:
        tool_name: Name of the tool to execute
        params: Parameters for the tool
        original_query: Original user query that triggered the tool

    Returns:
        ID of the created request
    """
    request_id = str(uuid.uuid4())
    PENDING_TOOL_REQUESTS[request_id] = {
        "request_id": request_id,
        "name": tool_name,
        "params": params,
        "original_query": original_query,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    return request_id


def update_tool_request(
    request_id: str,
    status: str,
    response: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """
    Update a tool request with its result.

    Args:
        request_id: ID of the request to update
        status: New status of the request
        response: Optional response data
        error: Optional error message
    """
    if request_id in PENDING_TOOL_REQUESTS:
        request = PENDING_TOOL_REQUESTS[request_id]
        request["status"] = status
        request["updated_at"] = datetime.now().isoformat()
        if response is not None:
            request["response"] = response
        if error is not None:
            request["error"] = error


def get_tool_request(request_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a tool request by ID.

    Args:
        request_id: ID of the request to get

    Returns:
        Request data if found, None otherwise
    """
    return PENDING_TOOL_REQUESTS.get(request_id)


def list_pending_requests() -> Dict[str, Dict[str, Any]]:
    """
    List all pending tool requests.

    Returns:
        Dictionary of pending requests
    """
    return {
        rid: req for rid, req in PENDING_TOOL_REQUESTS.items() if req.get("status") == "pending"
    }


def clear_all_requests() -> None:
    """Clear all tool requests."""
    PENDING_TOOL_REQUESTS.clear()
