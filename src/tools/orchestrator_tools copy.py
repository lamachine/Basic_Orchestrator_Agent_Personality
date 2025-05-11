"""Tools integration for the orchestrator agent. Simplified."""

from typing import Dict, Any, Optional
import json
import re
import uuid
import logging
from src.tools.initialize_tools import get_registry
from src.state.state_models import MessageRole

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
    # Make sure tools are discovered
    if not registry.list_tools():
        await registry.discover_tools()
    
    # Reset definitions
    TOOL_DEFINITIONS = {}
    
    # Build tool definitions from registry
    for tool_name in registry.list_tools():
        config = registry.get_config(tool_name)
        if not config:
            continue
        # Try to load description and examples from config (tool_config.yaml)
        description = config.get("description", f"Tool for {tool_name}")
        usage_examples = []
        # Look for usage_examples in config (may be under metadata)
        if "usage_examples" in config:
            usage_examples = config["usage_examples"]
        elif "metadata" in config and "usage_examples" in config["metadata"]:
            usage_examples = config["metadata"]["usage_examples"]
        # Format examples for prompt
        examples = [
            f'`{{"name": "{tool_name}", "args": {{"task": "{ex}"}}}}`' for ex in usage_examples
        ] if usage_examples else [
            f'`{{"name": "{tool_name}", "args": {{"task": "Example task for {tool_name}"}}}}`',
            f'`{{"name": "{tool_name}", "args": {{"task": "Another example for {tool_name}"}}}}`'
        ]
        TOOL_DEFINITIONS[tool_name] = {
            "description": description,
            "examples": examples,
        }
    logger.debug(f"Initialized {len(TOOL_DEFINITIONS)} tool definitions")
    return TOOL_DEFINITIONS

def add_tools_to_prompt(prompt: str) -> str:
    """Add tool definitions to prompt."""
    if not TOOL_DEFINITIONS:
        return prompt + "\n\nNo tools available at this time."
    
    tools_desc = "\n\n# AVAILABLE TOOLS\n\n"
    tools_desc += (
        "IMPORTANT: For any user request, ALWAYS call the appropriate tool. Pass the user's request as the 'task' argument in the tool call.\n"
        "Do NOT reference or call sub-tools (like email, tasks, calendar) directly. The personal_assistant tool will handle all routing and interpretation.\n"
        "For EVERY user request, you MUST output a tool call in the required backtick-JSON format below.\n"
        "You MUST ensure the tool call is valid JSON (no trailing commas, correct syntax). Double-check your output for correct JSON syntax before submitting. If the tool call is not valid JSON, the request will fail.\n"
        "If you do not use the tool call, the user will not receive real results.\n"
        "If you do not see a relevant tool, reply: 'No tool available for this request.'\n"
        "\nTo use a tool, output a JSON object in backticks with the following format:\n"
        '`{"name": "<tool_name>", "args": {"task": "user request here"}}`\n\n'
    )
    for tool_name, tool_info in TOOL_DEFINITIONS.items():
        tools_desc += f"## {tool_name}\n{tool_info['description']}\n\nExamples:\n"
        for example in tool_info['examples']:
            tools_desc += f"- {example}\n"
        tools_desc += "\n"
    return prompt + tools_desc

async def handle_tool_calls(response_text: str, user_input: Optional[str] = None, session_state=None) -> Dict[str, Any]:
    """Extract and execute tool calls from response text."""
    from src.services.message_service import log_and_persist_message  # Lazy import to avoid circular import
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
            
            if tool_name not in TOOL_DEFINITIONS:
                execution_results.append({
                    "name": tool_name, 
                    "args": args, 
                    "result": {
                        "status": "error", 
                        "message": f"Unknown tool '{tool_name}'"
                    }, 
                    "request_id": None
                })
                continue
                
            request_id = get_next_request_id()
            
            if session_state:
                # DRY logging for tool call
                await log_and_persist_message(
                    session_state["conversation_state"],
                    MessageRole.TOOL,
                    f"Tool call: {tool_name} with args: {args}",
                    metadata={"tool": tool_name, "args": args, "request_id": request_id},
                    sender="orchestrator",
                    target=tool_name
                )
            
            result = await execute_tool(tool_name, args, request_id, session_state=session_state)
            execution_results.append({
                "name": tool_name, 
                "args": args, 
                "result": result, 
                "request_id": request_id
            })
            
        except Exception as e:
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

async def execute_tool(tool_name: str, task: Dict[str, Any], request_id: str = None, session_state=None) -> Dict[str, Any]:
    """Execute a tool using the registry."""
    from src.services.message_service import log_and_persist_message  # Lazy import to avoid circular import
    task_str = task.get("task") or task.get("message", "")
    
    if not task_str or not isinstance(task_str, str) or not task_str.strip():
        return {"status": "error", "message": "Task must be a non-empty string"}
        
    args = {"task": task_str.strip()}
    
    if request_id:
        PENDING_TOOL_REQUESTS[request_id] = {
            "name": tool_name, 
            "args": args, 
            "status": "in_progress"
        }
        
    try:
        # Get tool from registry
        registry = get_registry()
        tool_class = registry.get_tool(tool_name)
        
        if not tool_class:
            return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
            
        # Initialize tool with config if needed
        tool_config = registry.get_config(tool_name)
        tool = tool_class(config=tool_config) if tool_config else tool_class()
        
        # Execute tool
        result = await tool.execute(args)
        
        if request_id:
            PENDING_TOOL_REQUESTS[request_id]["status"] = result.get("status", "completed")
            PENDING_TOOL_REQUESTS[request_id]["response"] = result
        
        if session_state:
            # DRY logging for tool result
            await log_and_persist_message(
                session_state["conversation_state"],
                MessageRole.TOOL,
                f"Tool result: {tool_name} returned: {result}",
                metadata={"tool": tool_name, "result": result, "request_id": request_id},
                sender=tool_name,
                target="orchestrator"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        
        if request_id:
            PENDING_TOOL_REQUESTS[request_id]["status"] = "error"
            PENDING_TOOL_REQUESTS[request_id]["response"] = {
                "status": "error", 
                "message": str(e)
            }
        
        if session_state:
            await log_and_persist_message(
                session_state["conversation_state"],
                MessageRole.TOOL,
                f"Tool result: {tool_name} error: {str(e)}",
                metadata={"tool": tool_name, "error": str(e), "request_id": request_id},
                sender=tool_name,
                target="orchestrator"
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
    
    prompt = f"""You are a helpful AI assistant.\n\nThe user previously asked: \"{user_input}\"\nHere are the results from the {tool_name} tool:\n\n====== BEGIN TOOL RESULTS ======\n{response_message}\n====== END TOOL RESULTS ======\n\nOnly use these results to answer.\n"""
    
    PENDING_TOOL_REQUESTS[request_id]["processed_by_agent"] = True
    return prompt

def check_completed_tool_requests() -> Optional[Dict[str, Any]]:
    """Check for completed tool requests."""
    for request_id, request_data in list(PENDING_TOOL_REQUESTS.items()):
        if request_data.get("status") in ["completed", "error"] and not request_data.get("processed", False):
            PENDING_TOOL_REQUESTS[request_id]["processed"] = True
            return {"request_id": request_id, "data": request_data}
    return None