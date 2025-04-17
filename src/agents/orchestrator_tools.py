"""Tools integration for the orchestrator agent."""

from typing import Dict, Any, Optional, List
import re
import json
import logging
from datetime import datetime
import importlib
import sys
import time
import threading
import os

# Setup logging
logger = logging.getLogger(__name__)

# Track tool requests
PENDING_TOOL_REQUESTS = {}

# Define tool schemas and descriptions
TOOL_DEFINITIONS = {
    "valet": {
        "description": "Manages household staff, daily schedule, and personal affairs.",
        "examples": ["Check my staff tasks", "See if I have any messages"],
    },
    "personal_assistant": {
        "description": "Handles communications, task lists, calendar, and personal productivity.",
        "examples": ["Check my schedule", "Send an email", "What's on my to-do list"],
    },
    "librarian": {
        "description": "Performs research, documentation, and knowledge management.",
        "examples": ["Research Pydantic agents", "Find information about AI tools"],
    }
}

# Additional tools to be implemented later
# KNOWLEDGE_TOOLS = {
#     "scrape_repo": {
#         "description": "Downloads and analyzes GitHub repositories to store their code for later analysis. You MUST use the FULL GitHub URL as the task parameter. This tool runs asynchronously and takes 1-3 minutes to complete.",
#         "examples": ["https://github.com/tiangolo/fastapi", 
#                     "https://github.com/pydantic/pydantic",
#                     "https://github.com/user/repo",
#                     "https://github.com/some-org/project"],
#         "when_to_use": "When the user explicitly asks to get, scrape, download, or analyze a GitHub repository. Only use with complete GitHub URLs."
#     },
#     "scrape_web": {
#         "description": "Scrapes and analyzes web pages or websites for knowledge capture. You MUST use the FULL URL as the task parameter. This tool runs asynchronously and takes 1-3 minutes to complete.",
#         "examples": ["https://www.example.com/docs", 
#                     "https://blog.example.com/article",
#                     "Analyze the content at https://docs.example.com"],
#         "when_to_use": "When the user wants to scrape, analyze, or capture knowledge from a general website. Only use with complete URLs."
#     },
#     "scrape_docs": {
#         "description": "Scrapes documentation websites and stores their contents for analysis. Use this when the user wants to import or analyze documentation from a website.",
#         "examples": ["https://pydantic-docs.helpmanual.io/",
#                     "Get the FastAPI documentation at https://fastapi.tiangolo.com",
#                     "Import the docs from the website docs.python.org"],
#         "when_to_use": "When the user explicitly asks to get documentation from a website."
#     },
#     "vectorize_and_store": {
#         "description": "Vectorizes content (files, scraped repos, or documentation) and stores in the database for semantic search. Use this after scraping to process the content.",
#         "examples": ["Process the scraped FastAPI docs for searching", 
#                     "Store the repo content in the vector database"],
#         "when_to_use": "When the user wants to process already scraped content for searching or analysis."
#     }
# }

# Try to import and register MCP tools
try:
    from src.tools.mcp_tools import MCP_TOOL_DEFINITIONS, MCP_TOOL_REGISTRY, check_completed_mcp_requests
    # Add MCP tools to tool definitions
    TOOL_DEFINITIONS.update(MCP_TOOL_DEFINITIONS)
    logger.debug(f"Added {len(MCP_TOOL_DEFINITIONS)} MCP tools to the tool registry")
except ImportError as e:
    logger.warning(f"MCP tools not available: {e}")
    check_completed_mcp_requests = lambda: None  # No-op function
    MCP_TOOL_REGISTRY = {}

# Tool imports
from src.tools.valet import valet_tool
from src.tools.personal_assistant import personal_assistant_tool
from src.tools.librarian import librarian_tool
# from src.tools.mcp_tools import MCP_TOOL_DEFINITIONS, MCP_TOOL_REGISTRY, check_completed_mcp_requests
# from src.tools.scrape_repo_tool import scrape_repo_tool
# from src.tools.scrape_web_tool import scrape_web_tool
# from src.tools.scrape_docs_tool import scrape_docs_tool
# from src.tools.vectorize_and_store_tool import vectorize_and_store_tool

# Import pending request trackers
# from src.tools.scrape_repo_tool import PENDING_SCRAPE_REPO_REQUESTS
# from src.tools.scrape_docs_tool import PENDING_SCRAPE_DOCS_REQUESTS
# from src.tools.vectorize_and_store_tool import PENDING_VECTORIZE_REQUESTS

def get_next_request_id() -> int:
    """
    Get the next request ID from the database.
    Will raise an exception if database access fails.
    
    Returns:
        int: The next request ID
        
    Raises:
        Exception: If database access fails
    """
    # Dynamically import the database manager to avoid circular imports
    db_module = importlib.import_module("src.services.db_services.db_manager")
    db_manager = db_module.DatabaseManager()
    
    # Get the next ID from the database
    return db_manager.get_next_id('request_id', 'swarm_messages')

def add_tools_to_prompt(prompt: str) -> str:
    """Add tool descriptions to the prompt."""
    tools_desc = "\n\n# AVAILABLE TOOLS\n\n"
    
    for tool_name, tool_info in TOOL_DEFINITIONS.items():
        tools_desc += f"## {tool_name}\n"
        tools_desc += f"{tool_info['description']}\n\n"
        
        # Add when to use this tool
        if "when_to_use" in tool_info:
            tools_desc += f"When to use: {tool_info['when_to_use']}\n\n"
        
        # Add examples in a more readable format
        tools_desc += "Examples:\n"
        for example in tool_info['examples']:
            tools_desc += f"- `{tool_name}(task=\"{example}\")`\n"
        tools_desc += "\n"
    
    tools_desc += "# HOW TO USE TOOLS\n"
    tools_desc += "1. For most questions, just answer directly without using tools.\n"
    tools_desc += "2. Use tools ONLY when the user's request specifically requires one.\n"
    tools_desc += "3. To use a tool, write in EXACTLY this format: `tool_name(task=\"your request\")`\n"
    tools_desc += "4. After using a tool, wait for its actual response - never make up tool results.\n"
    
    return prompt + tools_desc

def handle_tool_calls(response_text: str, user_input: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse tool calls from response text and execute them.
    Also checks user input for direct tool calls using keyword format.
    
    Args:
        response_text: The text to parse for tool calls
        user_input: Optional original user input to check for keyword format
        
    Returns:
        Dict containing tool calls and execution results
    """
    logger.debug(f"Processing response text for tool calls: {response_text}")
    tool_calls = []
    execution_results = []
    
    # First check user input for keyword format: "tool, name, message"
    if user_input:
        keyword_match = re.match(r'^tool,\s*(\w+),\s*(.+)$', user_input.strip())
        if keyword_match:
            logger.info("Found keyword format tool call in user input")
            tool_name = keyword_match.group(1).strip().lower()
            message = keyword_match.group(2).strip()
            logger.debug(f"Parsed tool name: {tool_name}, message: {message}")
            
            # Validate tool exists before proceeding
            if tool_name not in TOOL_DEFINITIONS:
                error_msg = f"Unknown tool '{tool_name}'. Available tools: {list(TOOL_DEFINITIONS.keys())}"
                logger.error(error_msg)
                return {
                    "tool_calls": [],
                    "execution_results": [{
                        "name": tool_name,
                        "args": {"task": message},
                        "result": {"status": "error", "message": error_msg},
                        "request_id": None
                    }]
                }
            
            # Generate a unique request ID
            request_id = len(PENDING_TOOL_REQUESTS) + 1
            logger.debug(f"Generated request_id: {request_id}")
            
            # Add to tool calls
            tool_calls.append({
                "name": tool_name,
                "args": {"task": message}
            })
            
            # Execute the tool
            logger.info(f"Executing tool '{tool_name}' with message: {message}")
            result = execute_tool(
                tool_name=tool_name,
                args={"task": message},
                request_id=request_id
            )
            logger.debug(f"Tool execution result: {result}")
            
            # Add to execution results
            execution_results.append({
                "name": tool_name,
                "args": {"task": message},
                "result": result,
                "request_id": request_id
            })
            
            return {
                "tool_calls": tool_calls,
                "execution_results": execution_results
            }
    
    # Otherwise look for standard tool call format in LLM response
    # Look for tool calls in the format: "I'll use the [tool] tool to [task]"
    logger.debug("Looking for standard format tool calls in LLM response")
    tool_matches = re.finditer(
        r"I'll use the (\w+) tool to (.+?)(?=\n|$|I'll use the \w+ tool)",
        response_text,
        re.IGNORECASE | re.MULTILINE
    )
    
    for match in tool_matches:
        tool_name = match.group(1).strip().lower()
        task = match.group(2).strip()
        logger.debug(f"Found standard format tool call: {tool_name} with task: {task}")
        
        # Validate tool exists
        if tool_name not in TOOL_DEFINITIONS:
            error_msg = f"Unknown tool '{tool_name}'. Available tools: {list(TOOL_DEFINITIONS.keys())}"
            logger.error(error_msg)
            execution_results.append({
                "name": tool_name,
                "args": {"task": task},
                "result": {"status": "error", "message": error_msg},
                "request_id": None
            })
            continue
            
        tool_calls.append({
            "name": tool_name,
            "args": {"task": task}
        })
    
    # Execute each tool call
    for i, call in enumerate(tool_calls):
        request_id = len(PENDING_TOOL_REQUESTS) + i + 1
        logger.info(f"Executing tool '{call['name']}' with task: {call['args']['task']}")
        result = execute_tool(
            tool_name=call["name"],
            args=call["args"],
            request_id=request_id
        )
        logger.debug(f"Tool execution result: {result}")
        execution_results.append({
            "name": call["name"],
            "args": call["args"],
            "result": result,
            "request_id": request_id
        })
    
    if not tool_calls:
        logger.warning("No valid tool calls found in response text")
        
    return {
        "tool_calls": tool_calls,
        "execution_results": execution_results
    }

def execute_tool(tool_name: str, args: Dict[str, Any], request_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a tool call and return the result.
    
    Args:
        tool_name: The name of the tool to execute
        args: Arguments to pass to the tool
        request_id: Optional request ID for tracking
        
    Returns:
        Dict with the tool result
    """
    # Validate inputs
    if not tool_name or not isinstance(tool_name, str):
        error_msg = "Tool name must be a non-empty string"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
        
    # Ensure we have a task argument and it's not empty
    task = args.get("task") or args.get("message", "")
    if not task or not isinstance(task, str):
        error_msg = "Task must be a non-empty string"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
    
    # Clean and validate task content
    task = task.strip()
    if not task:
        error_msg = "Task cannot be empty or just whitespace"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
        
    # Update args with cleaned task
    args = {"task": task}
    
    # Log initial tool request receipt
    logger.info(f"[TOOL REQUEST] Received request for '{tool_name}' with request_id: {request_id}")
    
    # Store initial request status
    if request_id is not None:
        PENDING_TOOL_REQUESTS[request_id] = {
            "name": tool_name,
            "args": args,
            "created_at": datetime.now().isoformat(),
            "status": "received"
        }
    
    # Log start of execution
    logger.debug(f"[TOOL EXECUTION] Starting execution of '{tool_name}' with args: {args} (request_id: {request_id})")
    logger.debug(f"Tool arguments: {json.dumps(args, indent=2)}")
    
    # Update status to in_progress
    if request_id is not None:
        PENDING_TOOL_REQUESTS[request_id]["status"] = "in_progress"
        PENDING_TOOL_REQUESTS[request_id]["execution_started_at"] = datetime.now().isoformat()
    
    try:
        # First check if it's an MCP tool
        if tool_name.startswith("mcp_") and tool_name in MCP_TOOL_REGISTRY:
            logger.debug(f"Executing MCP tool '{tool_name}'")
            
            # Get tool definition
            tool_def = MCP_TOOL_DEFINITIONS.get(tool_name, {})
            endpoint = tool_def.get("endpoint")
            
            # Check if endpoint has required configuration
            if endpoint == "brave_search" and not os.environ.get("BRAVE_API_KEY"):
                error_msg = f"Cannot execute {tool_name} - missing BRAVE_API_KEY environment variable"
                logger.error(error_msg)
                if request_id is not None:
                    PENDING_TOOL_REQUESTS[request_id]["status"] = "error"
                    PENDING_TOOL_REQUESTS[request_id]["error"] = error_msg
                return {
                    "status": "error",
                    "message": error_msg,
                    "request_id": request_id
                }
            
            # Get the MCP tool function
            mcp_tool_function = MCP_TOOL_REGISTRY[tool_name]
            
            try:
                # Call it (may be async)
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(mcp_tool_function(**args))
                loop.close()
                
                # Handle async MCP tool
                if result and result.get("status") == "pending":
                    logger.debug(f"MCP tool request is pending asynchronous execution")
                    # Update request status to pending
                    if request_id is not None:
                        PENDING_TOOL_REQUESTS[request_id]["status"] = "pending"
                        PENDING_TOOL_REQUESTS[request_id]["pending_response"] = result
                else:
                    # Update request status to completed
                    if request_id is not None:
                        PENDING_TOOL_REQUESTS[request_id]["status"] = "completed"
                        PENDING_TOOL_REQUESTS[request_id]["completed_at"] = datetime.now().isoformat()
                        PENDING_TOOL_REQUESTS[request_id]["response"] = result
                
                return result
            except Exception as e:
                error_msg = f"Error executing MCP tool {tool_name}: {str(e)}"
                logger.error(error_msg)
                if request_id is not None:
                    PENDING_TOOL_REQUESTS[request_id]["status"] = "error"
                    PENDING_TOOL_REQUESTS[request_id]["error"] = error_msg
                return {
                    "status": "error", 
                    "message": error_msg,
                    "request_id": request_id
                }
        
        # Handle the three main agent tools
        elif tool_name in ["valet", "personal_assistant", "librarian"]:
            try:
                # Get the appropriate tool function
                tool_function = {
                    "valet": valet_tool,
                    "personal_assistant": personal_assistant_tool,
                    "librarian": librarian_tool
                }[tool_name]
                
                # Execute the tool
                result = tool_function(task=task, request_id=request_id)
                
                # Update request status based on result
                if request_id is not None:
                    if result and isinstance(result, dict):
                        status = result.get("status", "completed")
                        PENDING_TOOL_REQUESTS[request_id]["status"] = status
                        if status == "completed":
                            PENDING_TOOL_REQUESTS[request_id]["completed_at"] = datetime.now().isoformat()
                        PENDING_TOOL_REQUESTS[request_id]["response"] = result
                    else:
                        PENDING_TOOL_REQUESTS[request_id]["status"] = "error"
                        PENDING_TOOL_REQUESTS[request_id]["error"] = "Tool returned invalid result"
                        result = {
                            "status": "error",
                            "message": "Tool returned invalid result",
                            "request_id": request_id
                        }
                
                return result
                
            except Exception as e:
                error_msg = f"Error executing {tool_name} tool: {str(e)}"
                logger.error(error_msg)
                if request_id is not None:
                    PENDING_TOOL_REQUESTS[request_id]["status"] = "error"
                    PENDING_TOOL_REQUESTS[request_id]["error"] = error_msg
                return {
                    "status": "error",
                    "message": error_msg,
                    "request_id": request_id
                }
        
        else:
            error_msg = f"Unknown tool '{tool_name}' requested"
            logger.error(error_msg)
            if request_id is not None:
                PENDING_TOOL_REQUESTS[request_id]["status"] = "error"
                PENDING_TOOL_REQUESTS[request_id]["error"] = error_msg
            return {
                "status": "error",
                "message": error_msg,
                "request_id": request_id
            }
    
    except Exception as e:
        error_msg = f"Unexpected error executing tool '{tool_name}': {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        if request_id is not None:
            PENDING_TOOL_REQUESTS[request_id]["status"] = "error"
            PENDING_TOOL_REQUESTS[request_id]["error"] = error_msg
        return {
            "status": "error",
            "message": error_msg,
            "request_id": request_id
        }

def format_tool_results(processing_result: Dict[str, Any]) -> str:
    """Format tool results for inclusion in the next prompt."""
    if not processing_result.get("execution_results"):
        return ""
    
    result_text = "\n\n### TOOL RESULTS ###\n\n"
    
    for result in processing_result["execution_results"]:
        tool_name = result["name"]
        message = result["result"]["message"]
        request_id = result["result"].get("request_id", "")
        
        result_text += f"{tool_name}: {message}\n\n"
    
    return result_text

def format_completed_tools_prompt(request_id: str, user_input: str) -> str:
    """
    Generate a prompt for handling tool request completions.
    
    Args:
        request_id: The ID of the completed request
        user_input: The original user query that triggered the tool
        
    Returns:
        A prompt for the LLM with the tool results
    """
    if request_id not in PENDING_TOOL_REQUESTS:
        return "I'm sorry, I couldn't find the results for your previous request."
    
    request = PENDING_TOOL_REQUESTS[request_id]
    tool_name = request.get("name", "unknown")
    
    # Extract the response message - can be either directly in the request 
    # or in a nested response field
    if "message" in request:
        response_message = request["message"]
    elif "response" in request and isinstance(request["response"], dict) and "message" in request["response"]:
        response_message = request["response"]["message"]
    else:
        # Fallback to the entire request as JSON string
        response_message = json.dumps(request, indent=2)
    
    # Log the extracted message
    logger.debug(f"[{datetime.now().isoformat()}] Extracted tool response message: {response_message[:100]}...")
    
    prompt = f"""You are Ronan, an intelligent assistant.

IMPORTANT INSTRUCTIONS:
1. The user previously asked: "{user_input}"
2. I have RECEIVED THE EXACT RESULTS from the {tool_name} tool
3. You MUST use ONLY these results to answer - DO NOT MAKE UP ANY INFORMATION
4. If these results don't fully answer the query, simply state what IS available
5. DO NOT hallucinate features, capabilities, or information not in the results

Here are the EXACT results received:

====== BEGIN TOOL RESULTS ======
{response_message}
====== END TOOL RESULTS ======

Provide ONLY information contained in these results to the user.
Be direct and to the point.

Agent:"""

    return prompt

def check_completed_tool_requests():
    """Check for completed tool requests and return their results."""
    check_time = datetime.now()
    logger.debug(f"[{check_time.isoformat()}] Checking for completed tool requests")
    
    completed_requests = {}
    
    # Check PENDING_TOOL_REQUESTS for completed tasks
    for request_id, response in list(PENDING_TOOL_REQUESTS.items()):
        status = response.get("status")
        logger.debug(f"[{check_time.isoformat()}] Request {request_id} has status: {status}")
        
        if status in ["success", "error"]:
            logger.debug(f"[{check_time.isoformat()}] Found completed request: {request_id} with status: {status}")
            logger.info(f"[{check_time.isoformat()}] Found completed request: {request_id}")
            
            # Update status to 'completed' to signal to the agent that processing is done
            response["status"] = "completed"
            response["marked_completed_at"] = check_time.isoformat()
            PENDING_TOOL_REQUESTS[request_id] = response
            logger.debug(f"[{check_time.isoformat()}] Updated request {request_id} status to 'completed'")
            
            # Add to completed requests
            completed_requests[request_id] = response
    
    # Check MCP tool requests if available
    if "check_completed_mcp_requests" in globals():
        mcp_completed = check_completed_mcp_requests()
        if mcp_completed:
            completed_requests.update(mcp_completed)
    
    if completed_requests:
        logger.info(f"[{check_time.isoformat()}] Returning {len(completed_requests)} completed requests")
        
    return completed_requests if completed_requests else None

def start_tool_checker():
    """Start a background thread to check for completed tool requests."""
    def check_loop():
        # Track when we last checked each module to avoid too frequent logging
        last_checked = {}
        check_interval = 10  # Log availability every 10 seconds at most
        check_count = 0
        
        while True:
            # Get current time for this check
            check_time = datetime.now()
            check_count += 1
            
            # Always log every 10th check at INFO level
            if check_count % 10 == 0:
                logger.debug(f"[{check_time.isoformat()}] Running check #{check_count} for completed tool requests")
            else:
                logger.debug(f"[{check_time.isoformat()}] Running check #{check_count} for completed tool requests")
            
            # Record current time for interval tracking
            now = time.time()
            
            # Only log availability at INFO level occasionally
            should_log = False
            if 'last_overall_log' not in last_checked or now - last_checked.get('last_overall_log', 0) > check_interval:
                should_log = True
                last_checked['last_overall_log'] = now
            
            # For each important module, set its logging flag based on check interval
            for module in ['scrape_repo', 'scrape_docs', 'vectorize', 'librarian', 'mcp']:
                if module not in last_checked or now - last_checked.get(module, 0) > check_interval:
                    # This will cause the module to log its availability this cycle
                    setattr(check_completed_tool_requests, f"logged_{module}", False)
                    last_checked[module] = now

            # Temporarily set the logger level higher for the check to reduce noise
            original_level = logger.level
            if not should_log:
                logger.setLevel(logging.WARNING)  # Suppress INFO logs during most checks
                
            try:
                completed = check_completed_tool_requests()
                if completed:
                    logger.info(f"[{check_time.isoformat()}] Found {len(completed)} completed requests in check #{check_count}")
            finally:
                # Restore original level
                logger.setLevel(original_level)
            
            # Sleep for a short time between checks (0.5 second)
            time.sleep(0.5)
            
    # Create thread with a meaningful name for easier debugging
    checker_thread = threading.Thread(target=check_loop, name="ToolCompletionChecker")
    checker_thread.daemon = True
    checker_thread.start()
    logger.info(f"[{datetime.now().isoformat()}] Started background thread to check for completed tool requests")

# Start the checker thread when the module is imported
start_tool_checker() 