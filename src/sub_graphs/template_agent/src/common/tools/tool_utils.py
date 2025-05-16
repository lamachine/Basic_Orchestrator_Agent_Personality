"""
Tool utilities for template agent.

This module provides utility functions for tool handling in the template agent.
It maintains orchestrator functionality while being generic enough to be reused
in different agent contexts.
"""

from typing import Dict, Any, Optional, List, Union
import json
import re
import uuid
import logging
import asyncio
from datetime import datetime
from ..state.state_models import MessageRole, Message, MessageType, MessageStatus

# Setup logging
logger = logging.getLogger(__name__)

# Centralized tool request tracking
TOOL_REQUESTS = {"pending": {}}
PENDING_TOOL_REQUESTS = TOOL_REQUESTS["pending"]

def get_next_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())

async def handle_tool_calls(response_text: str, graph_state=None, agent_name: str = "template_agent") -> Dict[str, Any]:
    """Extract and execute tool calls from response text."""
    tool_call_pattern = r"`\{[^`]+\}`"
    matches = re.finditer(tool_call_pattern, response_text)
    execution_results = []
    
    for match in matches:
        try:
            tool_call_json = match.group(0).strip('`')
            tool_call = json.loads(tool_call_json)
            
            if "name" not in tool_call or "args" not in tool_call:
                continue
                
            tool_name = tool_call["name"]
            args = tool_call["args"]
            request_id = get_next_request_id()
            
            # Log the tool call
            if graph_state:
                try:
                    message = Message(
                        role=MessageRole.TOOL,
                        type=MessageType.TOOL_CALL,
                        status=MessageStatus.PENDING,
                        content=f"Tool call: {tool_name} with args: {args}",
                        metadata={
                            "tool": tool_name,
                            "args": args,
                            "request_id": request_id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "agent": agent_name
                        }
                    )
                    graph_state.messages.append(message)
                    logger.debug(f"[{agent_name}] Logged tool call: {tool_name}")
                except Exception as e:
                    logger.error(f"[{agent_name}] Failed to log tool call: {str(e)}", exc_info=True)
            
            # Schedule tool execution asynchronously
            asyncio.create_task(execute_tool(tool_name, args, request_id, graph_state, agent_name))
            execution_results.append({
                "name": tool_name,
                "args": args,
                "request_id": request_id,
                "status": "pending"
            })
            
        except Exception as e:
            logger.error(f"[{agent_name}] Error processing tool call: {str(e)}", exc_info=True)
            execution_results.append({
                "name": "unknown",
                "args": {},
                "result": {
                    "status": "error",
                    "message": str(e)
                },
                "request_id": None
            })
            
    return {"execution_results": execution_results}

async def execute_tool(tool_name: str, task: Dict[str, Any], request_id: str = None, graph_state=None, agent_name: str = "template_agent") -> Dict[str, Any]:
    """Execute a tool using the registry."""
    logger.debug(f"[{agent_name}] Starting tool execution for {tool_name}")
    
    # Make sure we have a valid request_id
    if not request_id:
        request_id = get_next_request_id()
        logger.debug(f"[{agent_name}] Generated new request_id: {request_id}")
    
    # Extract task string
    task_str = task.get("task") or task.get("message", "")
    
    if not task_str or not isinstance(task_str, str) or not task_str.strip():
        logger.warning(f"[{agent_name}] Invalid task string")
        return {"status": "error", "message": "Task must be a non-empty string"}
    
    # Build clean args with request_id
    args = {
        "task": task_str.strip(),
        "request_id": request_id,
        "agent_name": agent_name
    }
    
    # Copy any parameters if provided
    if "parameters" in task and isinstance(task["parameters"], dict):
        args["parameters"] = task["parameters"]
    
    # Store in pending requests
    PENDING_TOOL_REQUESTS[request_id] = {
        "name": tool_name,
        "args": args,
        "status": "in_progress",
        "agent": agent_name,
        "started_at": datetime.utcnow().isoformat()
    }
    
    try:
        # Get tool from registry
        from .tool_registry import get_registry
        registry = get_registry()
        tool = registry.get_tool(tool_name)
        
        if not tool:
            logger.warning(f"[{agent_name}] Unknown tool: {tool_name}")
            return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
        
        # Execute tool
        result = await tool.execute(args)
        logger.debug(f"[{agent_name}] Tool execution result: {result}")
        
        if request_id:
            PENDING_TOOL_REQUESTS[request_id].update({
                "status": result.get("status", "completed"),
                "response": result,
                "completed_at": datetime.utcnow().isoformat()
            })
        
        if graph_state:
            try:
                message = Message(
                    role=MessageRole.TOOL,
                    type=MessageType.TOOL_RESULT,
                    status=MessageStatus.COMPLETED,
                    content=f"Tool result: {tool_name} returned: {result}",
                    metadata={
                        "tool": tool_name,
                        "result": result,
                        "request_id": request_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent": agent_name
                    }
                )
                graph_state.messages.append(message)
                logger.debug(f"[{agent_name}] Logged tool result")
            except Exception as e:
                logger.error(f"[{agent_name}] Failed to log tool result: {str(e)}", exc_info=True)
        
        return result
        
    except Exception as e:
        logger.error(f"[{agent_name}] Error executing tool {tool_name}: {str(e)}", exc_info=True)
        
        if request_id:
            PENDING_TOOL_REQUESTS[request_id].update({
                "status": "error",
                "response": {
                    "status": "error",
                    "message": str(e)
                },
                "completed_at": datetime.utcnow().isoformat()
            })
        
        if graph_state:
            try:
                message = Message(
                    role=MessageRole.TOOL,
                    type=MessageType.ERROR_MESSAGE,
                    status=MessageStatus.ERROR,
                    content=f"Tool error: {tool_name} failed: {str(e)}",
                    metadata={
                        "tool": tool_name,
                        "error": str(e),
                        "request_id": request_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent": agent_name
                    }
                )
                graph_state.messages.append(message)
                logger.debug(f"[{agent_name}] Logged tool error")
            except Exception as log_error:
                logger.error(f"[{agent_name}] Failed to log tool error: {str(log_error)}", exc_info=True)
        
        return {"status": "error", "message": str(e)}

def format_tool_results(processing_result: Dict[str, Any], agent_name: str = "template_agent") -> str:
    """Format tool results for display to user."""
    if not processing_result.get("execution_results"):
        return ""
        
    result_text = f"\n\n### {agent_name.upper()} TOOL RESULTS ###\n\n"
    
    for result in processing_result["execution_results"]:
        tool_name = result["name"]
        message = result.get("result", {}).get("message", "No result message")
        status = result.get("status", "unknown")
        result_text += f"{tool_name} ({status}): {message}\n\n"
        
    return result_text

def cleanup_processed_request(request_id: str, agent_name: str = "template_agent") -> None:
    """Remove a processed request from PENDING_TOOL_REQUESTS."""
    if request_id in PENDING_TOOL_REQUESTS:
        logger.debug(f"[{agent_name}] Cleaning up processed request: {request_id}")
        del PENDING_TOOL_REQUESTS[request_id]

def check_completed_tool_requests(agent_name: str = "template_agent") -> Optional[Dict[str, Any]]:
    """Check for completed tool requests."""
    completed = {}
    
    for request_id, request_data in list(PENDING_TOOL_REQUESTS.items()):
        # Only check requests for this agent
        if request_data.get("agent") != agent_name:
            continue
            
        if request_data.get("status") in ["completed", "error", "success"] and not request_data.get("processed", False):
            PENDING_TOOL_REQUESTS[request_id]["processed"] = True
            completed[request_id] = {
                "name": request_data.get("name", "Unknown Tool"),
                "response": request_data.get("response", request_data),
                "displayed": False,
                "original_query": request_data.get("args", {}).get("task", ""),
                "started_at": request_data.get("started_at"),
                "completed_at": request_data.get("completed_at")
            }
    
    return completed if completed else None 