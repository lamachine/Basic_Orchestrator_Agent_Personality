"""Librarian tool implementation.

This tool handles research, documentation, and knowledge management.
It routes requests to the librarian sub-graph for processing.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from src.services.logging_service import get_logger
from src.state.state_models import MessageRole

# Setup logger
logger = get_logger(__name__)


async def librarian_tool(
    task: str,
    request_id: Optional[str] = None,
    session_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tool for research, documentation, and knowledge management.
    Routes requests to the librarian sub-graph for processing.

    Args:
        task: The research or documentation task
        request_id: Optional request ID for tracking
        session_state: Optional session state for tracking

    Returns:
        Dict with the response from the librarian graph
    """
    try:
        # Log the request
        if session_state and "conversation_state" in session_state:
            await session_state["conversation_state"].add_message(
                role=MessageRole.TOOL,
                content=f"Librarian request: {task}",
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                    "task": task,
                },
                sender="orchestrator_graph.librarian",
                target="librarian_graph.system",
            )

        # Import the librarian graph here to avoid circular imports
        from src.sub_graphs.librarian_agent.graphs.librarian_graph import librarian_graph

        # Create the request for the librarian graph
        request = {
            "task": task,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
        }

        # Execute in the librarian graph
        result = await librarian_graph(session_state, request)

        # Log the result
        if session_state and "conversation_state" in session_state:
            await session_state["conversation_state"].add_message(
                role=MessageRole.TOOL,
                content=f"Librarian result: {result}",
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                    "result": result,
                },
                sender="librarian_graph.system",
                target="orchestrator_graph.librarian",
            )

        return {
            "status": "success",
            "message": result.get("message", "Research completed successfully"),
            "data": result,
        }

    except Exception as e:
        error_msg = f"Error in librarian tool: {str(e)}"
        logger.error(error_msg)

        # Log the error
        if session_state and "conversation_state" in session_state:
            await session_state["conversation_state"].add_message(
                role=MessageRole.TOOL,
                content=error_msg,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                    "error": str(e),
                },
                sender="librarian_graph.system",
                target="orchestrator_graph.librarian",
            )

        return {"status": "error", "message": error_msg}
