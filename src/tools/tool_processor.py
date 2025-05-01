"""
Tool Processor Module - Manages the execution and lifecycle of tools within the agent system.

This module provides the ToolProcessor class which orchestrates the registration, execution, 
and result handling of tools that agents can use to accomplish tasks. Key responsibilities include:

1. Tool Registration - Allows agents to register available tools with metadata
2. Tool Execution - Processes tool requests by routing to the appropriate implementation
3. Asynchronous Handling - Manages background tool execution and result collection
4. State Management - Tracks tool request status and stores results
5. Standardized Interface - Provides a consistent API for all tool interactions

The ToolProcessor works closely with the BaseAgent and specialized agents to enable
a modular, extensible system where new capabilities can be added as tools without
modifying the core agent logic. This design follows the principle of separation of concerns,
allowing tools to evolve independently of the agents that use them.

Each tool request is tracked with a unique ID, allowing for asynchronous execution and
result retrieval, which is especially important for long-running operations or tools
that require external resources.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from src.state.state_models import MessageRole

# Setup logging
from src.services.logging_service import get_logger
logger = get_logger(__name__)

def process_completed_tool_request(request: Dict[str, Any]) -> str:
    """
    Process a completed tool request and format the result for display.
    
    Args:
        request: Dictionary containing the tool request data
        
    Returns:
        Formatted string result for display
    """
    logger.debug(f"Processing completed tool request: {request}")
    
    # Extract request details
    request_id = request.get('request_id', 'unknown')
    tool_details = request.get('response', {})
    
    # Extract tool name and result message
    tool_name = tool_details.get('name', 'unknown')
    
    # Try to get the message from various possible locations
    message = None
    logger.debug(f"Looking for message in tool response. Keys: {list(tool_details.keys())}")
    
    if 'message' in tool_details:
        message = tool_details['message']
        logger.debug(f"Found message directly in response: {message[:100]}")
    elif 'response' in tool_details and isinstance(tool_details['response'], dict):
        response_obj = tool_details['response']
        logger.debug(f"Looking in nested response object. Keys: {list(response_obj.keys())}")
        if 'message' in response_obj:
            message = response_obj['message']
            logger.debug(f"Found message in nested response: {message[:100]}")
    elif isinstance(tool_details, dict) and 'result' in tool_details:
        result = tool_details['result']
        logger.debug(f"Looking in result object. Keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
        if isinstance(result, dict) and 'message' in result:
            message = result['message']
            logger.debug(f"Found message in result object: {message[:100]}")
    
    # Fallback to a generic message if we couldn't find one
    if not message:
        message = f"Request {request_id} completed with status: {tool_details.get('status', 'unknown')}"
        logger.warning(f"Could not find message in response. Using fallback message: {message}")
    
    # Add the tool name to the request for reference in the caller
    request['tool_name'] = tool_name
    
    return message

def format_tool_result_for_llm(result: Dict[str, Any]) -> str:
    """
    Format a tool result for inclusion in an LLM prompt.
    
    Args:
        result: The tool result to format
        
    Returns:
        Formatted string for the LLM prompt
    """
    tool_name = result.get('tool_name', 'unknown_tool')
    request_id = result.get('request_id', 'unknown')
    
    # Get the message or use a default
    if 'message' in result:
        message = result['message']
    else:
        message = process_completed_tool_request(result)
    
    formatted_result = f"""TOOL RESULT:
Tool: {tool_name}
Request ID: {request_id}
Result: {message}
"""
    return formatted_result

def normalize_tool_response(response: Any) -> Dict[str, Any]:
    """
    Normalize tool responses into a consistent format.
    
    Args:
        response: The raw tool response (could be dict, string, etc.)
        
    Returns:
        Normalized dictionary with standard keys
    """
    if isinstance(response, str):
        return {
            "status": "completed",
            "message": response,
            "data": None
        }
    elif isinstance(response, dict):
        # Already a dict, make sure it has our standard keys
        normalized = {
            "status": response.get("status", "completed"),
            "message": response.get("message", str(response)),
            "data": response.get("data", None)
        }
        
        # If there's no message but there is a result, use that
        if "message" not in response and "result" in response:
            result = response["result"]
            if isinstance(result, dict) and "message" in result:
                normalized["message"] = result["message"]
            elif isinstance(result, str):
                normalized["message"] = result
        
        return normalized
    else:
        # Some other type, convert to string
        return {
            "status": "completed",
            "message": str(response),
            "data": None
        }

class ToolProcessor:
    """Manages tool execution and registration for agents."""
    def __init__(self, tool_registry=None):
        from src.tools.tool_registry import ToolRegistry
        self.registry = tool_registry or ToolRegistry()

    async def execute_tools(self, tool_calls: list[dict], graph_state=None) -> list[dict]:
        """
        Execute a list of tool calls asynchronously.

        Args:
            tool_calls (list[dict]): List of tool call specifications.
            graph_state: Optional graph state for message logging

        Returns:
            list[dict]: List of tool execution results.
        """
        results = []
        for call in tool_calls:
            tool_name = call.get("name")
            params = call.get("parameters", {})
            
            # Log tool call if we have graph state
            if graph_state and "conversation_state" in graph_state:
                await graph_state["conversation_state"].add_message(
                    role=MessageRole.TOOL,
                    content=f"Executing tool {tool_name} with parameters: {params}",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "tool_name": tool_name,
                        "tool_args": params,
                        "message_type": "tool_execution"
                    },
                    sender="orchestrator_graph.tool_processor",
                    target=f"orchestrator_graph.{tool_name}"
                )
            
            # If the tool is async, await it; otherwise, call directly
            tool = self.registry.get_tool(tool_name)
            if not tool:
                error_result = {"tool": tool_name, "error": f"Tool '{tool_name}' not found"}
                results.append(error_result)
                
                # Log error if we have graph state
                if graph_state and "conversation_state" in graph_state:
                    await graph_state["conversation_state"].add_message(
                        role=MessageRole.TOOL,
                        content=f"Tool execution failed: {error_result['error']}",
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "tool_name": tool_name,
                            "message_type": "tool_error",
                            "error": error_result['error']
                        },
                        sender=f"orchestrator_graph.{tool_name}",
                        target="orchestrator_graph.tool_processor"
                    )
                continue
                
            func = tool.function
            try:
                if hasattr(func, "__call__") and hasattr(func, "__code__") and func.__code__.co_flags & 0x80:
                    # Coroutine function
                    result = await func(**params)
                else:
                    result = func(**params)
                    
                execution_result = {"tool": tool_name, "result": result}
                results.append(execution_result)
                
                # Log successful result if we have graph state
                if graph_state and "conversation_state" in graph_state:
                    await graph_state["conversation_state"].add_message(
                        role=MessageRole.TOOL,
                        content=f"Tool execution completed: {result}",
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "tool_name": tool_name,
                            "message_type": "tool_result",
                            "result": result
                        },
                        sender=f"orchestrator_graph.{tool_name}",
                        target="orchestrator_graph.tool_processor"
                    )
                    
            except Exception as e:
                error_result = {"tool": tool_name, "error": str(e)}
                results.append(error_result)
                
                # Log error if we have graph state
                if graph_state and "conversation_state" in graph_state:
                    await graph_state["conversation_state"].add_message(
                        role=MessageRole.TOOL,
                        content=f"Tool execution failed: {str(e)}",
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "tool_name": tool_name,
                            "message_type": "tool_error",
                            "error": str(e)
                        },
                        sender=f"orchestrator_graph.{tool_name}",
                        target="orchestrator_graph.tool_processor"
                    )
                    
        return results 