"""
Personal assistant graph implementation.

This module implements the graph for the personal assistant sub-graph,
handling tool requests, managing agent state, and returning results in
standard JSON tool format using the state messaging system.

Next essential steps:
- replace the dummy response with the actual tool call for google tasks
- test an actual tool call down through chain

THEN finish the template
- auto-insantiate sub-graphs
- create sub agents for email, calendar and tasks
- give sub-sub-agents direct tools
- test the entire stack again
"""

from typing import Dict, Any, Optional
from datetime import datetime
from src.state.state_manager import StateManager
from src.state.state_models import MessageRole
from src.services.logging_service import get_logger
import asyncio
from src.sub_graphs.personal_assistant_agent.src.tools.personal_assistant_tool import EMAIL_TOOL, TASKS_TOOL

logger = get_logger(__name__)

# Standard JSON tool response format
# {
#     "type": "status|result|error",
#     "status": "in_progress|success|error",
#     "message": "...",
#     "data": {...},
#     ...
# }

# Placeholder for personality logic (not used in sub-graph, but structure is here)
def apply_personality(message: str, personality: Optional[str] = None) -> str:
    # In a sub-graph, personality is not applied, but this function is here for compatibility
    return message

async def personal_assistant_graph(state: Dict[str, Any], tool_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a tool request in the personal assistant sub-graph.
    Responds in standard JSON tool format and uses state messaging.
    Handles 'tasks' and 'email' tools, and dummy fallback for others.
    """
    try:
        session_id = state.get('session_id', 'personal_assistant')
        state_manager = StateManager()
        request_id = tool_request.get('request_id', f"req-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        tool_name = tool_request.get('tool', tool_request.get('name', 'unknown'))
        args = tool_request.get('args', {})
        args['task'] = tool_request.get('task', args.get('task', ''))
        # Route to the correct tool
        if tool_name == 'tasks':
            result = await TASKS_TOOL.execute(args)
            await state_manager.update_session(
                session_id=session_id,
                role=MessageRole.SYSTEM,
                content=result.get("message", str(result)),
                metadata=result
            )
            return result
        if tool_name == 'email':
            result = await EMAIL_TOOL.execute(args)
            await state_manager.update_session(
                session_id=session_id,
                role=MessageRole.SYSTEM,
                content=result.get("message", str(result)),
                metadata=result
            )
            return result
        # Dummy tool: fallback for unknown tools
        # Simulate async status update if requested
        if tool_request.get('action') == 'status' or tool_request.get('status_request'):
            status_msg = {
                "type": "status",
                "status": "in_progress",
                "tool": tool_name,
                "request_id": request_id,
                "message": f"Task '{args['task']}' is in progress.",
                "timestamp": datetime.now().isoformat()
            }
            await state_manager.update_session(
                session_id=session_id,
                role=MessageRole.SYSTEM,
                content=status_msg["message"],
                metadata=status_msg
            )
            return status_msg
        # Simulate error if requested
        if tool_request.get('action') == 'error':
            error_msg = {
                "type": "error",
                "status": "error",
                "tool": tool_name,
                "request_id": request_id,
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
            return error_msg
        # Simulate result (success)
        await asyncio.sleep(1)  # Simulate async work
        result_msg = {
            "type": "result",
            "status": "success",
            "tool": tool_name,
            "request_id": request_id,
            "message": f"Task '{args['task']}' completed successfully.",
            "data": {"task": args['task'], "result": "Dummy result for testing."},
            "timestamp": datetime.now().isoformat()
        }
        await state_manager.update_session(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=result_msg["message"],
            metadata=result_msg
        )
        return result_msg
    except Exception as e:
        error_msg = {
            "type": "error",
            "status": "error",
            "tool": tool_request.get('tool', 'unknown'),
            "request_id": tool_request.get('request_id'),
            "message": f"Exception in personal_assistant_graph: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        logger.error(error_msg["message"])
        return error_msg

# --- Legacy/Advanced sub-graph logic (commented out for now, to be refactored/restored) ---
#         # --- Sub-graph (sub-agent) auto-instantiation and approval ---
#         sub_graphs = state.setdefault('sub_graphs', {})
#         approved_sub_graphs = state.setdefault('approved_sub_graphs', set())
#         requested_sub_graph = tool_request.get('sub_graph')
#         if requested_sub_graph and requested_sub_graph not in approved_sub_graphs:
#             # Request approval from parent graph
#             approval_message = {
#                 "status": "pending_approval",
#                 "message": f"Sub-graph '{requested_sub_graph}' requires approval. Please approve to continue.",
#                 "sub_graph": requested_sub_graph,
#                 "request_type": "sub_graph_approval",
#                 "timestamp": datetime.now().isoformat()
#             }
#             logger.info(f"Requesting approval for sub-graph: {requested_sub_graph}")
#             return approval_message
#         if requested_sub_graph and requested_sub_graph not in sub_graphs:
#             # Auto-instantiate sub-graph (placeholder logic)
#             sub_graphs[requested_sub_graph] = {"initialized_at": datetime.now().isoformat()}
#             logger.info(f"Auto-instantiated sub-graph: {requested_sub_graph}")
#         # --- End sub-graph instantiation/approval ---
#
#         # --- StateManager instantiation and request ID chaining ---
#         parent_request_id = tool_request.get('parent_request_id')
#         request_id = tool_request.get('request_id')
#         # Chain request IDs if parent_request_id is present
#         if parent_request_id:
#             chained_request_id = f"{parent_request_id}.{request_id}" if request_id else parent_request_id
#         else:
#             chained_request_id = request_id or f"req-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
#         # --- End StateManager and request ID chaining ---
#
#         # Log request receipt using StateManager
#         await state_manager.update_session(
#             session_id=session_id,
#             role=MessageRole.SYSTEM,
#             content=f"Personal assistant graph processing request: {tool_request.get('task')}",
#             metadata={
#                 "timestamp": datetime.now().isoformat(),
#                 "request_id": chained_request_id,
#                 "parent_request_id": parent_request_id,
#                 "task": tool_request.get('task'),
#                 "args": tool_request.get('args', {}),
#                 "sender": "personal_assistant.sub_graph_interface",
#                 "target": "personal_assistant.personal_assistant_graph"
#             }
#         )
#         # Placeholder for actual personal assistant functionality
#         result = {
#             "status": "success",
#             "message": apply_personality(f"[Placeholder] Personal assistant handled task: {tool_request.get('task')}", None),
#             "data": {
#                 "task": tool_request.get('task'),
#                 "args": tool_request.get('args', {}),
#                 "request_id": chained_request_id,
#                 "parent_request_id": parent_request_id,
#                 "timestamp": datetime.now().isoformat()
#             }
#         }
#         # Log result using StateManager
#         await state_manager.update_session(
#             session_id=session_id,
#             role=MessageRole.SYSTEM,
#             content=f"Personal assistant graph completed request: {result}",
#             metadata={
#                 "timestamp": datetime.now().isoformat(),
#                 "request_id": chained_request_id,
#                 "parent_request_id": parent_request_id,
#                 "result": result,
#                 "sender": "personal_assistant.personal_assistant_graph",
#                 "target": "personal_assistant.sub_graph_interface"
#             }
#         )
#         return result 