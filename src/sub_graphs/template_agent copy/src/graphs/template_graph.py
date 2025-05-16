"""
Template graph implementation.

This module implements the graph for the template sub-graph,
handling tool requests, managing agent state, and returning results in
standard JSON tool format using the state messaging system.

The template graph provides a foundation for creating new sub-graphs by:
1. Handling tool requests and responses in a standardized format
2. Managing state and session information
3. Providing logging and error handling
4. Supporting request ID chaining for traceability
5. Implementing a dummy tool system for testing

Request ID Handling:
- Parent request IDs are stored in metadata
- Internal tool calls use their own request IDs
- Responses to parent include original request ID
"""

from typing import Dict, Any, Optional
from datetime import datetime
from src.state.state_manager import StateManager
from src.state.state_models import MessageRole
from src.services.logging_service import get_logger
import asyncio

logger = get_logger(__name__)

# Standard JSON tool response format
# {
#     "type": "status|result|error",
#     "status": "in_progress|success|error",
#     "message": "...",
#     "data": {...},
#     ...
# }

def apply_personality(message: str, personality: Optional[str] = None) -> str:
    """
    Apply personality to a message.
    
    Args:
        message (str): The message to apply personality to
        personality (Optional[str]): The personality to apply
        
    Returns:
        str: The message with personality applied
    """
    # In a sub-graph, personality is not applied, but this function is here for compatibility
    return message

def _prepare_response(response: Dict[str, Any], parent_request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Prepare a response for sending back to the parent graph.
    - Removes local request ID
    - Restores parent request ID
    - Cleans up metadata
    
    Args:
        response: The response to prepare
        parent_request_id: The parent request ID to restore
        
    Returns:
        Dict: The prepared response
    """
    if parent_request_id:
        # Store current request ID in metadata
        metadata = response.get('metadata', {})
        metadata['local_request_id'] = response.get('request_id')
        
        # Restore parent request ID
        response['request_id'] = parent_request_id
        
        # Update metadata
        response['metadata'] = metadata
    
    return response

async def template_graph(state: Dict[str, Any], tool_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a tool request in the template sub-graph.
    - Handles tool requests and responses in standard JSON format
    - Manages state and session information
    - Provides logging and error handling
    - Supports request ID chaining for traceability
    - Implements a dummy tool system for testing
    
    Args:
        state: The current graph state dictionary
        tool_request: The tool request to process
        
    Returns:
        Dict containing the execution results or error information
    """
    try:
        # --- State and Request Management ---
        session_id = state.get('session_id', 'template_agent')
        state_manager = StateManager()
        
        # Extract and store parent request ID
        parent_request_id = tool_request.get('parent_request_id')
        
        # Generate new request ID for this sub-graph operation
        request_id = f"req-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Extract tool information
        tool_name = tool_request.get('tool', tool_request.get('name', 'unknown'))
        args = tool_request.get('args', {})
        args['task'] = tool_request.get('task', args.get('task', ''))
        
        # Log request receipt with parent request ID in metadata
        await state_manager.update_session(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=f"Template graph processing request: {tool_request.get('task')}",
            metadata={
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "parent_request_id": parent_request_id,  # Store parent ID in metadata
                "task": tool_request.get('task'),
                "args": tool_request.get('args', {}),
                "sender": "template.sub_graph_interface",
                "target": "template.template_graph"
            }
        )
        
        # --- Tool Execution ---
        # TODO: Replace with actual tool execution logic
        # For now, implement dummy tool system for testing
        
        # Handle status requests
        if tool_request.get('action') == 'status' or tool_request.get('status_request'):
            status_msg = {
                "type": "status",
                "status": "in_progress",
                "tool": tool_name,
                "request_id": request_id,  # Use local request ID
                "message": f"Task '{args['task']}' is in progress.",
                "timestamp": datetime.now().isoformat()
            }
            await state_manager.update_session(
                session_id=session_id,
                role=MessageRole.SYSTEM,
                content=status_msg["message"],
                metadata=status_msg
            )
            return _prepare_response(status_msg, parent_request_id)
            
        # Handle error requests
        if tool_request.get('action') == 'error':
            error_msg = {
                "type": "error",
                "status": "error",
                "tool": tool_name,
                "request_id": request_id,  # Use local request ID
                "message": f"Error processing task '{args['task']}'.",
                "details": {"reason": "Dummy error for testing."},
                "timestamp": datetime.now().isoformat()
            }
            await state_manager.update_session(
                session_id=session_id,
                role=MessageRole.SYSTEM,
                content=error_msg["message"],
                metadata=error_msg
            )
            return _prepare_response(error_msg, parent_request_id)
            
        # Simulate successful execution
        await asyncio.sleep(1)  # Simulate async work
        result_msg = {
            "type": "result",
            "status": "success",
            "tool": tool_name,
            "request_id": request_id,  # Use local request ID
            "message": f"Task '{args['task']}' completed successfully.",
            "data": {
                "task": args['task'],
                "result": "Dummy result for testing.",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # Log result
        await state_manager.update_session(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=result_msg["message"],
            metadata=result_msg
        )
        return _prepare_response(result_msg, parent_request_id)
        
    except Exception as e:
        error_msg = f"Error in template graph: {str(e)}"
        logger.error(error_msg)
        
        # Log error
        session_id = state.get('session_id', 'template_agent')
        state_manager = StateManager()
        await state_manager.update_session(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=error_msg,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,  # Use local request ID
                "parent_request_id": parent_request_id,  # Store parent ID in metadata
                "error": str(e),
                "sender": "template.template_graph",
                "target": "template.sub_graph_interface"
            }
        )
        error_response = {
            "type": "error",
            "status": "error",
            "tool": tool_request.get('tool', 'unknown'),
            "request_id": request_id,  # Use local request ID
            "message": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        return _prepare_response(error_response, parent_request_id) 