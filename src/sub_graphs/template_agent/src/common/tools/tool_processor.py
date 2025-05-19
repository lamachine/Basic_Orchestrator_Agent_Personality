"""
Tool Processor Module - Manages the execution and lifecycle of tools within the template agent system.

This module provides the ToolProcessor class which orchestrates the registration, execution,
and result handling of tools that the template agent can use to accomplish tasks. Key responsibilities include:

1. Tool Registration - Allows the template agent to register available tools with metadata
2. Tool Execution - Processes tool requests by routing to the appropriate implementation
3. Asynchronous Handling - Manages background tool execution and result collection
4. State Management - Tracks tool request status and stores results
5. Standardized Interface - Provides a consistent API for all tool interactions
6. Response Analysis - Evaluates tool responses to determine if user request is satisfied

The ToolProcessor works closely with the template agent to enable a modular, extensible system
where new capabilities can be added as tools without modifying the core agent logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from ..services.llm_service import get_llm_service
from ..services.logging_service import get_logger
from ..state.state_models import MessageRole

# Setup logging
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
    request_id = request.get("request_id", "unknown")
    tool_details = request.get("response", {})

    # Extract tool name and result message
    tool_name = tool_details.get("name", "unknown")

    # Try to get the message from various possible locations
    message = None
    logger.debug(f"Looking for message in tool response. Keys: {list(tool_details.keys())}")

    if "message" in tool_details:
        message = tool_details["message"]
        logger.debug(f"Found message directly in response: {message[:100]}")
    elif "response" in tool_details and isinstance(tool_details["response"], dict):
        response_obj = tool_details["response"]
        logger.debug(f"Looking in nested response object. Keys: {list(response_obj.keys())}")
        if "message" in response_obj:
            message = response_obj["message"]
            logger.debug(f"Found message in nested response: {message[:100]}")
    elif isinstance(tool_details, dict) and "result" in tool_details:
        result = tool_details["result"]
        logger.debug(
            f"Looking in result object. Keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}"
        )
        if isinstance(result, dict) and "message" in result:
            message = result["message"]
            logger.debug(f"Found message in result object: {message[:100]}")

    # Fallback to a generic message if we couldn't find one
    if not message:
        message = (
            f"Request {request_id} completed with status: {tool_details.get('status', 'unknown')}"
        )
        logger.warning(f"Could not find message in response. Using fallback message: {message}")

    # Add the tool name to the request for reference in the caller
    request["tool_name"] = tool_name

    return message


def format_tool_result_for_llm(result: Dict[str, Any]) -> str:
    """
    Format a tool result for inclusion in an LLM prompt.

    Args:
        result: The tool result to format

    Returns:
        Formatted string for the LLM prompt
    """
    tool_name = result.get("tool_name", "unknown_tool")
    request_id = result.get("request_id", "unknown")

    # Get the message or use a default
    if "message" in result:
        message = result["message"]
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
        return {"status": "completed", "message": response, "data": None}
    elif isinstance(response, dict):
        # Already a dict, make sure it has our standard keys
        normalized = {
            "status": response.get("status", "completed"),
            "message": response.get("message", str(response)),
            "data": response.get("data", None),
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
        return {"status": "completed", "message": str(response), "data": None}


async def analyze_tool_response(
    original_request: str, tool_results: List[Dict[str, Any]], llm_service=None
) -> Dict[str, Any]:
    """
    Analyze tool responses to determine if the user's request has been satisfied.
    The LLM will determine if additional tool calls are needed and format them
    according to the standard message pattern.

    Args:
        original_request: The original user request
        tool_results: List of tool execution results
        llm_service: Optional LLM service instance

    Returns:
        Dict containing:
        - is_satisfied: Whether the request is satisfied
        - explanation: Explanation of the analysis
        - next_action: Either "complete", "need_more_tools", or "need_user_input"
    """
    if not llm_service:
        llm_service = get_llm_service()

    # Format the analysis prompt
    prompt = f"""Analyze if the following tool results satisfy the user's request.

Original Request: {original_request}

Tool Results:
{chr(10).join(format_tool_result_for_llm(result) for result in tool_results)}

Determine if:
1. The user's request has been fully satisfied
2. Additional tool calls are needed (specify which tools and why)
3. User input is needed to proceed
4. The request cannot be satisfied with available tools

Respond in JSON format:
{{
    "is_satisfied": bool,
    "explanation": "Detailed explanation of your analysis",
    "next_action": "complete" | "need_more_tools" | "need_user_input",
    "reason": "Explanation of why this action is needed"
}}"""

    try:
        # Get LLM analysis
        analysis = await llm_service.analyze(prompt)

        # Parse the response
        if isinstance(analysis, str):
            # Try to parse JSON from string
            import json

            try:
                analysis = json.loads(analysis)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {analysis}")
                return {
                    "is_satisfied": False,
                    "explanation": "Failed to analyze tool results",
                    "next_action": "need_user_input",
                    "reason": "Error in analysis",
                }

        # Extract results
        return {
            "is_satisfied": analysis.get("is_satisfied", False),
            "explanation": analysis.get("explanation", "No explanation provided"),
            "next_action": analysis.get("next_action", "need_user_input"),
            "reason": analysis.get("reason", "No reason provided"),
        }

    except Exception as e:
        logger.error(f"Error analyzing tool response: {e}")
        return {
            "is_satisfied": False,
            "explanation": f"Error analyzing results: {str(e)}",
            "next_action": "need_user_input",
            "reason": "Error in analysis",
        }


class ToolProcessor:
    """Manages tool execution and registration for the template agent."""

    def __init__(self, tool_registry=None, llm_service=None):
        from .tool_registry import ToolRegistry

        self.registry = tool_registry or ToolRegistry()
        self.llm_service = llm_service

    async def execute_tools(
        self,
        tool_calls: list[dict],
        graph_state=None,
        original_request: Optional[str] = None,
    ) -> list[dict]:
        """
        Execute a list of tool calls asynchronously.

        Args:
            tool_calls (list[dict]): List of tool call specifications.
            graph_state: Optional graph state for message logging
            original_request: Optional original user request for response analysis

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
                        "message_type": "tool_execution",
                    },
                    sender="template_agent.tool_processor",
                    target=f"template_agent.{tool_name}",
                )

            # If the tool is async, await it; otherwise, call directly
            tool = self.registry.get_tool(tool_name)
            if not tool:
                error_result = {
                    "tool": tool_name,
                    "error": f"Tool '{tool_name}' not found",
                }
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
                            "error": error_result["error"],
                        },
                        sender="template_agent.tool_processor",
                        target=f"template_agent.{tool_name}",
                    )
                continue

            try:
                # Execute the tool
                if hasattr(tool.function, "__await__"):
                    result = await tool.function(**params)
                else:
                    result = tool.function(**params)

                # Normalize the response
                normalized_result = normalize_tool_response(result)
                normalized_result["tool"] = tool_name
                results.append(normalized_result)

                # Log success if we have graph state
                if graph_state and "conversation_state" in graph_state:
                    await graph_state["conversation_state"].add_message(
                        role=MessageRole.TOOL,
                        content=f"Tool execution completed: {normalized_result['message']}",
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "tool_name": tool_name,
                            "message_type": "tool_success",
                            "result": normalized_result,
                        },
                        sender="template_agent.tool_processor",
                        target=f"template_agent.{tool_name}",
                    )
            except Exception as e:
                error_result = {"tool": tool_name, "error": str(e), "status": "error"}
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
                            "error": str(e),
                        },
                        sender="template_agent.tool_processor",
                        target=f"template_agent.{tool_name}",
                    )

        # If we have the original request, analyze the results
        if original_request:
            analysis = await analyze_tool_response(original_request, results, self.llm_service)

            # Add analysis to results
            results.append({"type": "analysis", **analysis})

        return results
