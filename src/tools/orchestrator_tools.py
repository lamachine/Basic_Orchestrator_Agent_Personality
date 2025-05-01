"""Tools integration for the orchestrator agent. Simplified."""

from typing import Dict, Any, Optional
import json
import re
import uuid
from src.sub_graphs.valet_agent.valet_tool import valet_tool
from src.sub_graphs.librarian_agent.librarian_tool import librarian_tool
from src.sub_graphs.personal_assistant_agent.personal_assistant_tool import PersonalAssistantTool
# from src.sub_graph_personal_assistant.config.config import PersonalAssistantConfig  # (disabled for minimal orchestrator)
from src.state.state_models import MessageRole

# Centralized tool request tracking
TOOL_REQUESTS = {"pending": {}}
PENDING_TOOL_REQUESTS = TOOL_REQUESTS["pending"]

TOOL_DEFINITIONS = {
    "valet": {
        "description": "Manages household staff, daily schedule, and personal affairs.",
        "examples": [
            '`{"name": "valet", "args": {"task": "Check my staff tasks"}}`',
            '`{"name": "valet", "args": {"task": "See if I have any messages"}}`'
        ],
    },
    "personal_assistant": {
        "description": "Handles communications, task lists, calendar, and personal productivity. Includes Gmail integration.",
        "examples": [
            '`{"name": "personal_assistant", "args": {"task": "Send email", "to": "john@example.com", "subject": "Meeting", "body": "Let\'s meet tomorrow"}}`',
            '`{"name": "personal_assistant", "args": {"task": "search_email", "query": "project updates"}}`',
            '`{"name": "personal_assistant", "args": {"task": "list_email", "limit": 5}}`'
        ],
    },
    "librarian": {
        "description": "Performs research, documentation, and knowledge management.",
        "examples": [
            '`{"name": "librarian", "args": {"task": "Research Pydantic agents"}}`',
            '`{"name": "librarian", "args": {"task": "Find information about AI tools"}}`'
        ],
    }
}

def get_next_request_id() -> str:
    return str(uuid.uuid4())

def add_tools_to_prompt(prompt: str) -> str:
    tools_desc = "\n\n# AVAILABLE TOOLS\n\n"
    tools_desc += "To use a tool, output a JSON object in backticks with the following format:\n"
    tools_desc += '`{"name": "tool_name", "args": {"task": "what to do", ...other args}}`\n\n'
    for tool_name, tool_info in TOOL_DEFINITIONS.items():
        tools_desc += f"## {tool_name}\n{tool_info['description']}\n\nExamples:\n"
        for example in tool_info['examples']:
            tools_desc += f"- {example}\n"
        tools_desc += "\n"
    return prompt + tools_desc

async def handle_tool_calls(response_text: str, user_input: Optional[str] = None, session_state=None) -> Dict[str, Any]:
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
                execution_results.append({"name": tool_name, "args": args, "result": {"status": "error", "message": f"Unknown tool '{tool_name}'"}, "request_id": None})
                continue
            request_id = get_next_request_id()
            if session_state:
                await session_state.add_message(
                    MessageRole.TOOL,
                    f"Tool call: {tool_name} with args: {args}",
                    metadata={"tool": tool_name, "args": args, "request_id": request_id}
                )
            result = await execute_tool(tool_name, args, request_id, session_state=session_state)
            execution_results.append({"name": tool_name, "args": args, "result": result, "request_id": request_id})
        except Exception as e:
            execution_results.append({"name": "unknown", "args": {}, "result": {"status": "error", "message": str(e)}, "request_id": None})
    return {"execution_results": execution_results}

async def execute_tool(tool_name: str, task: Dict[str, Any], request_id: str = None, session_state=None) -> Dict[str, Any]:
    task_str = task.get("task") or task.get("message", "")
    if not task_str or not isinstance(task_str, str) or not task_str.strip():
        return {"status": "error", "message": "Task must be a non-empty string"}
    args = {"task": task_str.strip()}
    if request_id:
        PENDING_TOOL_REQUESTS[request_id] = {"name": tool_name, "args": args, "status": "in_progress"}
    try:
        if tool_name == "valet":
            result = valet_tool(task=args["task"], request_id=request_id)
        elif tool_name == "personal_assistant":
            config = PersonalAssistantConfig()
            tool = PersonalAssistantTool(config=config)
            result = await tool.execute(args)
        elif tool_name == "librarian":
            result = librarian_tool(task=args["task"], request_id=request_id)
        else:
            return {"status": "error", "message": f"Unknown tool '{tool_name}'"}
        if request_id:
            PENDING_TOOL_REQUESTS[request_id]["status"] = result.get("status", "completed")
            PENDING_TOOL_REQUESTS[request_id]["response"] = result
        if session_state:
            await session_state.add_message(
                MessageRole.TOOL,
                f"Tool result: {tool_name} returned: {result}",
                metadata={"tool": tool_name, "result": result, "request_id": request_id}
            )
        return result
    except Exception as e:
        if request_id:
            PENDING_TOOL_REQUESTS[request_id]["status"] = "error"
            PENDING_TOOL_REQUESTS[request_id]["response"] = {"status": "error", "message": str(e)}
        if session_state:
            await session_state.add_message(
                MessageRole.TOOL,
                f"Tool result: {tool_name} error: {str(e)}",
                metadata={"tool": tool_name, "error": str(e), "request_id": request_id}
            )
        return {"status": "error", "message": str(e)}

def format_tool_results(processing_result: Dict[str, Any]) -> str:
    if not processing_result.get("execution_results"):
        return ""
    result_text = "\n\n### TOOL RESULTS ###\n\n"
    for result in processing_result["execution_results"]:
        tool_name = result["name"]
        message = result["result"]["message"]
        result_text += f"{tool_name}: {message}\n\n"
    return result_text

def format_completed_tools_prompt(request_id: str, user_input: str) -> str:
    if request_id not in PENDING_TOOL_REQUESTS:
        return "I'm sorry, I couldn't find the results for your previous request."
    request = PENDING_TOOL_REQUESTS[request_id]
    tool_name = request.get("name", "unknown")
    response_message = request.get("response", {}).get("message", json.dumps(request, indent=2))
    prompt = f"""You are a helpful AI assistant.\n\nThe user previously asked: \"{user_input}\"\nHere are the results from the {tool_name} tool:\n\n====== BEGIN TOOL RESULTS ======\n{response_message}\n====== END TOOL RESULTS ======\n\nOnly use these results to answer.\n"""
    PENDING_TOOL_REQUESTS[request_id]["processed_by_agent"] = True
    return prompt

def check_completed_tool_requests() -> Optional[Dict[str, Any]]:
    for request_id, request_data in list(PENDING_TOOL_REQUESTS.items()):
        if request_data.get("status") in ["completed", "error"] and not request_data.get("processed", False):
            PENDING_TOOL_REQUESTS[request_id]["processed"] = True
            return {"request_id": request_id, "data": request_data}
    return None