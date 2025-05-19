"""Tools integration for the orchestrator agent. Simplified."""

import asyncio
import json
import logging
import re
import uuid
from typing import Any, Dict, Optional

from src.state.state_models import MessageRole
from src.tools.initialize_tools import get_registry

# Setup logging
logger = logging.getLogger(__name__)

# Centralized tool request tracking
TOOL_REQUESTS = {"pending": {}}
PENDING_TOOL_REQUESTS = TOOL_REQUESTS["pending"]

# Dynamic tool definitions - will be populated during initialization
TOOL_DEFINITIONS = {}


def get_next_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


async def initialize_tool_definitions():
    """Initialize tool definitions from registry."""
    global TOOL_DEFINITIONS

    registry = get_registry()
    # No need to re-discover tools since this should be called after initialize_tools()
    # Reset definitions
    TOOL_DEFINITIONS = {}

    # Build tool definitions from registry
    tool_count = 0
    for tool_name in registry.list_tools():
        tool_count += 1
        config = registry.get_config(tool_name)
        if not config:
            continue
        # Try to load description and examples from config
        description = config.get("description", f"Tool for {tool_name}")
        usage_examples = []
        if "usage_examples" in config:
            usage_examples = config["usage_examples"]
        elif "metadata" in config and "usage_examples" in config["metadata"]:
            usage_examples = config["metadata"]["usage_examples"]
        # Format examples for prompt
        examples = (
            [f'`{{"name": "{tool_name}", "args": {{"task": "{ex}"}}}}`' for ex in usage_examples]
            if usage_examples
            else [
                f'`{{"name": "{tool_name}", "args": {{"task": "Example task for {tool_name}"}}}}`'
            ]
        )
        TOOL_DEFINITIONS[tool_name] = {
            "description": description,
            "examples": examples,
        }
    # Use debug level instead of info to avoid duplicate logging
    logger.debug(f"Initialized {len(TOOL_DEFINITIONS)} tool definitions")
    return TOOL_DEFINITIONS


async def add_tools_to_prompt(prompt: str) -> str:
    """Add tool definitions to prompt."""
    # Get tools directly from registry instead of reinitializing
    registry = get_registry()
    tool_names = registry.list_tools()

    if not tool_names:
        logger.warning("No tools available in registry")
        return prompt + "\n\nNo tools available at this time."

    tools_desc = "\n\n# AVAILABLE TOOLS\n\n"
    tools_desc += (
        "IMPORTANT: You have access to the following tools.\n"
        "If the user request requires a tool call, you MUST output a tool call in the required backtick-JSON format below.\n"
        "You MUST ensure the tool call is valid JSON (no trailing commas, correct syntax).\n"
        "If you do not use the tool call, the user will not receive real results.\n"
        "If you do not see a relevant tool, reply: 'No tool available for this request.'\n\n"
        "To use a tool, output a JSON object in backticks with the following format:\n"
        '`{"name": "tool_name", "args": {"task": "user request here", "parameters": {}, "request_id": "auto-generated"}}`\n\n'
    )

    # Build tool descriptions from registry information
    for tool_name in tool_names:
        # Get both tool wrapper and config
        tool_wrapper = registry.get_tool(tool_name)
        tool_config = registry.get_config(tool_name)

        if not tool_wrapper or not tool_config:
            logger.warning(f"Tool {tool_name} missing wrapper or config")
            continue

        # Log what we're getting to help diagnose issues
        logger.debug(f"Tool {tool_name} config: {tool_config}")

        # Get description from config (which was copied from the function during discovery)
        description = tool_config.get("description", f"Tool for {tool_name}")
        capabilities = tool_config.get("capabilities", [])

        # Format tool description
        tools_desc += f"## {tool_name}\n{description}\n\n"

        # Add capabilities if available
        if capabilities:
            tools_desc += "Capabilities:\n"
            for cap in capabilities:
                tools_desc += f"- {cap}\n"
            tools_desc += "\n"

        # Try to get usage examples directly from the function
        func = tool_wrapper.func
        usage_examples = []

        # Check if usage_examples is set on the function
        if hasattr(func, "usage_examples") and func.usage_examples:
            usage_examples = func.usage_examples
            logger.debug(f"Found {len(usage_examples)} usage examples on {tool_name} function")

        # Add usage examples if available
        if usage_examples:
            tools_desc += "Examples:\n"
            for example in usage_examples[:3]:  # Limit to 3 examples to keep prompt size reasonable
                tools_desc += f"- {example}\n"
            tools_desc += "\n"
        else:
            # Fallback to example from config if no usage examples found
            example = tool_config.get("example")
            if example:
                tools_desc += f"Example: {example}\n\n"

        # Add standard tool usage format
        tools_desc += f'To use this tool, format your response as:\n`{{"name": "{tool_name}", "args": {{"task": "your task here", "parameters": {{}}, "request_id": "auto-generated"}}}}`\n\n'

    tools_desc += "\nIMPORTANT: When using tools:\n"
    tools_desc += "1. Always include the task parameter with a clear description of what you want the tool to do\n"
    tools_desc += "2. The request_id will be automatically generated\n"
    tools_desc += "3. Use the exact tool name as shown above\n"
    tools_desc += "4. Ensure your tool call is valid JSON (no trailing commas, correct syntax)\n"

    full_prompt = prompt + tools_desc
    logger.debug(f"Added tool descriptions for {len(tool_names)} tools to prompt")
    return full_prompt


async def handle_tool_calls(
    response_text: str, user_input: Optional[str] = None, session_state=None
) -> Dict[str, Any]:
    """Extract and execute tool calls from response text."""
    from src.services.message_service import (
        log_and_persist_message,  # Lazy import to avoid circular import
    )

    logger.debug(
        f"[handle_tool_calls] Starting tool call handling. Session state type: {type(session_state)}"
    )
    if session_state:
        logger.debug(f"[handle_tool_calls] Session state keys: {session_state.keys()}")
        if "conversation_state" in session_state:
            logger.debug(
                f"[handle_tool_calls] Conversation state type: {type(session_state['conversation_state'])}"
            )

    tool_call_pattern = r"`\{[^`]+\}`"
    matches = re.finditer(tool_call_pattern, response_text)
    execution_results = []

    for match in matches:
        try:
            tool_call_json = match.group(0).strip("`")
            tool_call = json.loads(tool_call_json)
            logger.debug(f"[handle_tool_calls] Processing tool call: {tool_call}")

            if "name" not in tool_call or "args" not in tool_call:
                logger.warning(f"[handle_tool_calls] Invalid tool call format: {tool_call}")
                continue

            tool_name = tool_call["name"]
            args = tool_call["args"]

            if tool_name not in TOOL_DEFINITIONS:
                logger.warning(f"[handle_tool_calls] Unknown tool: {tool_name}")
                execution_results.append(
                    {
                        "name": tool_name,
                        "args": args,
                        "result": {
                            "status": "error",
                            "message": f"Unknown tool '{tool_name}'",
                        },
                        "request_id": None,
                    }
                )
                continue

            request_id = get_next_request_id()
            logger.debug(f"[handle_tool_calls] Generated request_id: {request_id}")

            # Add request_id to args if not present
            if "request_id" not in args:
                args["request_id"] = request_id

            # Log the tool call
            if session_state and "conversation_state" in session_state:
                logger.debug(
                    f"[handle_tool_calls] Attempting to log tool call with conversation_state"
                )
                # DRY logging for tool call
                try:
                    await log_and_persist_message(
                        session_state["conversation_state"],
                        MessageRole.TOOL,
                        f"Tool call: {tool_name} with args: {args}",
                        metadata={
                            "tool": tool_name,
                            "args": args,
                            "request_id": request_id,
                        },
                        sender="orchestrator",
                        target=tool_name,
                    )
                    logger.debug("[handle_tool_calls] Successfully logged tool call")
                except Exception as e:
                    logger.error(
                        f"[handle_tool_calls] Failed to log tool call: {str(e)}",
                        exc_info=True,
                    )

            result = await execute_tool(tool_name, args, request_id, session_state=session_state)
            execution_results.append(
                {
                    "name": tool_name,
                    "args": args,
                    "result": result,
                    "request_id": request_id,
                }
            )

        except Exception as e:
            logger.error(
                f"[handle_tool_calls] Error processing tool call: {str(e)}",
                exc_info=True,
            )
            execution_results.append(
                {
                    "name": "unknown",
                    "args": {},
                    "result": {"status": "error", "message": str(e)},
                    "request_id": None,
                }
            )

    return {"execution_results": execution_results}


async def execute_tool(
    tool_name: str, task: Dict[str, Any], request_id: str = None, session_state=None
) -> Dict[str, Any]:
    """Execute a tool using the registry."""
    from src.services.message_service import (
        log_and_persist_message,  # Lazy import to avoid circular import
    )

    logger.debug(f"[execute_tool] Starting tool execution for {tool_name}")
    logger.debug(f"[execute_tool] Session state type: {type(session_state)}")
    if session_state:
        logger.debug(f"[execute_tool] Session state keys: {session_state.keys()}")
        if "conversation_state" in session_state:
            logger.debug(
                f"[execute_tool] Conversation state type: {type(session_state['conversation_state'])}"
            )

    # Make sure we have a valid request_id
    if not request_id:
        request_id = get_next_request_id()
        logger.debug(f"[execute_tool] Generated new request_id: {request_id}")

    # Extract task string
    task_str = task.get("task") or task.get("message", "")

    if not task_str or not isinstance(task_str, str) or not task_str.strip():
        logger.warning("[execute_tool] Invalid task string")
        return {"status": "error", "message": "Task must be a non-empty string"}

    # Build clean args with request_id
    args = {
        "task": task_str.strip(),
        "request_id": request_id,  # Always include request_id
    }

    # Copy any parameters if provided
    if "parameters" in task and isinstance(task["parameters"], dict):
        args["parameters"] = task["parameters"]

    # Replace any "auto-generated" request_id
    if task.get("request_id") == "auto-generated":
        logger.debug(f"[execute_tool] Replacing 'auto-generated' request_id with: {request_id}")
    elif "request_id" in task and task["request_id"] != request_id:
        logger.warning(
            f"[execute_tool] Overriding provided request_id {task['request_id']} with {request_id}"
        )

    # Store in pending requests
    PENDING_TOOL_REQUESTS[request_id] = {
        "name": tool_name,
        "args": args,
        "status": "in_progress",
    }

    try:
        # Get tool from registry
        registry = get_registry()
        tool = registry.get_tool(tool_name)

        if not tool:
            logger.warning(f"[execute_tool] Unknown tool: {tool_name}")
            return {"status": "error", "message": f"Unknown tool '{tool_name}'"}

        # Debug log before execution
        logger.debug(f"[execute_tool] Executing tool {tool_name} with args: {args}")

        # Execute tool
        result = await tool.execute(args)
        logger.debug(f"[execute_tool] Tool execution result: {result}")

        if request_id:
            PENDING_TOOL_REQUESTS[request_id]["status"] = result.get("status", "completed")
            PENDING_TOOL_REQUESTS[request_id]["response"] = result

        if session_state and "conversation_state" in session_state:
            logger.debug("[execute_tool] Attempting to log tool result")
            try:
                # DRY logging for tool result
                await log_and_persist_message(
                    session_state["conversation_state"],
                    MessageRole.TOOL,
                    f"Tool result: {tool_name} returned: {result}",
                    metadata={
                        "tool": tool_name,
                        "result": result,
                        "request_id": request_id,
                    },
                    sender=tool_name,
                    target="orchestrator",
                )
                logger.debug("[execute_tool] Successfully logged tool result")
            except Exception as e:
                logger.error(f"[execute_tool] Failed to log tool result: {str(e)}", exc_info=True)

        return result

    except Exception as e:
        logger.error(f"[execute_tool] Error executing tool {tool_name}: {str(e)}", exc_info=True)

        if request_id:
            PENDING_TOOL_REQUESTS[request_id]["status"] = "error"
            PENDING_TOOL_REQUESTS[request_id]["response"] = {
                "status": "error",
                "message": str(e),
            }

        if session_state and "conversation_state" in session_state:
            logger.debug("[execute_tool] Attempting to log tool error")
            try:
                await log_and_persist_message(
                    session_state["conversation_state"],
                    MessageRole.TOOL,
                    f"Tool result: {tool_name} error: {str(e)}",
                    metadata={
                        "tool": tool_name,
                        "error": str(e),
                        "request_id": request_id,
                    },
                    sender=tool_name,
                    target="orchestrator",
                )
                logger.debug("[execute_tool] Successfully logged tool error")
            except Exception as log_error:
                logger.error(
                    f"[execute_tool] Failed to log tool error: {str(log_error)}",
                    exc_info=True,
                )

        return {"status": "error", "message": str(e)}


def format_tool_results(processing_result: Dict[str, Any]) -> str:
    """Format tool results for display to user."""
    if not processing_result.get("execution_results"):
        return ""

    result_text = "\n\n### TOOL RESULTS ###\n\n"

    for result in processing_result["execution_results"]:
        tool_name = result["name"]
        message = result["result"]["message"]
        result_text += f"{tool_name}: {message}\n\n"

    return result_text


def format_completed_tools_prompt(request_id: str, user_input: str) -> str:
    """Format completed tool results for LLM prompt."""
    if request_id not in PENDING_TOOL_REQUESTS:
        return "I'm sorry, I couldn't find the results for your previous request."

    request = PENDING_TOOL_REQUESTS[request_id]
    tool_name = request.get("name", "unknown")
    response_message = request.get("response", {}).get("message", json.dumps(request, indent=2))

    prompt = f"""The user previously asked: \"{user_input}\"\nHere are the results from the {tool_name} tool:\n\n====== BEGIN TOOL RESULTS ======\n{response_message}\n====== END TOOL RESULTS ======\n\nOnly use these results to answer.\n"""

    PENDING_TOOL_REQUESTS[request_id]["processed_by_agent"] = True
    return prompt


def cleanup_processed_request(request_id: str) -> None:
    """Remove a processed request from PENDING_TOOL_REQUESTS.

    Args:
        request_id: The ID of the request to clean up
    """
    if request_id in PENDING_TOOL_REQUESTS:
        logger.debug(f"Cleaning up processed request: {request_id}")
        del PENDING_TOOL_REQUESTS[request_id]


def check_completed_tool_requests() -> Optional[Dict[str, Any]]:
    """Check for completed tool requests.

    Returns:
        Dict with request_id as key and request data as value, or None if no completed requests
    """
    completed = {}

    for request_id, request_data in list(PENDING_TOOL_REQUESTS.items()):
        # Check if the request is completed or has an error status
        if request_data.get("status") in [
            "completed",
            "error",
            "success",
        ] and not request_data.get("processed", False):
            # Mark as processed
            PENDING_TOOL_REQUESTS[request_id]["processed"] = True
            # Add to completed dict
            completed[request_id] = {
                "name": request_data.get("name", "Unknown Tool"),
                "response": request_data.get(
                    "response", request_data
                ),  # Use response if available, otherwise use the whole request_data
                "displayed": False,
                "original_query": request_data.get("args", {}).get(
                    "task", ""
                ),  # Include original query for agent processing
            }
            # Don't clean up here - wait for agent to process it

    return completed if completed else None
