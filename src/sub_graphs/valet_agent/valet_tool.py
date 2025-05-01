"""Valet tool implementation.

This tool handles household management, daily schedules, and personal affairs.
It routes requests to the valet sub-graph for processing.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from src.state.state_models import MessageRole
from src.services.logging_service import get_logger

# Setup logger
logger = get_logger(__name__)

async def valet_tool(task: str, request_id: Optional[str] = None, session_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Tool for managing household staff, daily schedule, and personal affairs.
    Routes requests to the valet sub-graph for processing.
    
    Args:
        task: The task or query for the valet
        request_id: Optional request ID for tracking
        session_state: Optional session state for tracking
        
    Returns:
        Dict with the response from the valet graph
    """
    try:
        # Log the request
        if session_state and "conversation_state" in session_state:
            await session_state["conversation_state"].add_message(
                role=MessageRole.TOOL,
                content=f"Valet request: {task}",
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                    "task": task
                },
                sender="orchestrator_graph.valet",
                target="valet_graph.system"
            )
            
        # Import the valet graph here to avoid circular imports
        from src.sub_graphs.valet_agent.graphs.valet_graph import valet_graph
        
        # Create the request for the valet graph
        request = {
            "task": task,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Execute in the valet graph
        result = await valet_graph(session_state, request)
        
        # Log the result
        if session_state and "conversation_state" in session_state:
            await session_state["conversation_state"].add_message(
                role=MessageRole.TOOL,
                content=f"Valet result: {result}",
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                    "result": result
                },
                sender="valet_graph.system",
                target="orchestrator_graph.valet"
            )
            
        return {
            "status": "success",
            "message": result.get("message", "Task completed successfully"),
            "data": result
        }
        
    except Exception as e:
        error_msg = f"Error in valet tool: {str(e)}"
        logger.error(error_msg)
        
        # Log the error
        if session_state and "conversation_state" in session_state:
            await session_state["conversation_state"].add_message(
                role=MessageRole.TOOL,
                content=error_msg,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                    "error": str(e)
                },
                sender="valet_graph.system",
                target="orchestrator_graph.valet"
            )
            
        return {
            "status": "error",
            "message": error_msg
        } 