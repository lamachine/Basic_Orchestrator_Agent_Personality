"""
Template graph implementation.

This module implements the base template graph that can be extended by specialty graphs.
The template graph includes sub-graph capabilities like:
- Parent request ID tracking in metadata
- Local request ID generation and management
- Response preparation for parent graph communication
- Sub-graph specific state management
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph

from ...services.logging_service import get_logger
from ...state.state_models import GraphState, MessageRole

logger = get_logger(__name__)


def get_next_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


async def template_graph(state: Dict[str, Any], tool_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a tool request in the template sub-graph.
    - Handles tool requests and responses in standard JSON format
    - Manages state and session information
    - Provides logging and error handling
    - Supports request ID chaining for traceability

    Args:
        state: The current graph state dictionary
        tool_request: The tool request to process

    Returns:
        Dict containing the execution results or error information
    """
    try:
        # Extract parent request ID if present
        parent_request_id = tool_request.get("request_id")

        # Generate new request ID for this sub-graph operation
        request_id = get_next_request_id()

        # Extract tool information
        tool_name = tool_request.get("tool", tool_request.get("name", "unknown"))
        args = tool_request.get("args", {})
        args["task"] = tool_request.get("task", args.get("task", ""))

        # Add metadata with parent request ID
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "parent_request_id": parent_request_id,
            "task": tool_request.get("task"),
            "args": tool_request.get("args", {}),
            "sender": "template.sub_graph_interface",
            "target": "template.template_graph",
        }

        # Log request receipt
        logger.debug(f"Template graph processing request: {tool_request.get('task')}")
        logger.debug(f"Request metadata: {metadata}")

        # Execute tool with metadata
        result = await execute_tool(
            tool_name=tool_name,
            task={"task": args["task"], "metadata": metadata},
            request_id=request_id,
            graph_state=state,
        )

        # If this is a response to a parent request, use parent's request_id
        if parent_request_id:
            result["request_id"] = parent_request_id
            # Clear parent_request_id from metadata
            if "metadata" in result:
                result["metadata"].pop("parent_request_id", None)

        return result

    except Exception as e:
        logger.error(f"Error in template graph: {str(e)}")
        error_result = {"status": "error", "message": str(e)}

        # If this is a response to a parent request, use parent's request_id
        if parent_request_id:
            error_result["request_id"] = parent_request_id
        else:
            error_result["request_id"] = request_id

        return error_result


def build_template_graph() -> StateGraph:
    """
    Build and return the template graph.

    Returns:
        StateGraph: A configured StateGraph for the template agent
    """
    graph = StateGraph(GraphState)
    # TODO: Add nodes and edges as needed
    return graph.compile()
