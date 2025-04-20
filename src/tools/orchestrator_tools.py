"""Tools integration for the orchestrator agent."""

from typing import Dict, Any, Optional, List
import re
import json
import logging
from datetime import datetime, timedelta
import importlib
import sys
import time
import threading
import os
import uuid

# Setup logging using the central LoggingService
from src.services.logging_services.logging_service import get_logger
from src.utils.datetime_utils import now, timestamp

# Initialize logger
logger = get_logger(__name__)

# Centralized tool request tracking system
TOOL_REQUESTS = {
    "pending": {},  # All pending requests regardless of tool type
    "completed": {},  # Completed requests ready for processing
    "failed": {}  # Failed requests with error information
}

# For backward compatibility - points to the same data structure
PENDING_TOOL_REQUESTS = TOOL_REQUESTS["pending"]

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
# from src.tools.valet import valet_tool
# from src.tools.personal_assistant import personal_assistant_tool
# from src.tools.librarian import librarian_tool
# from src.tools.mcp_tools import MCP_TOOL_DEFINITIONS, MCP_TOOL_REGISTRY, check_completed_mcp_requests
# from src.tools.scrape_repo_tool import scrape_repo_tool
# from src.tools.scrape_web_tool import scrape_web_tool
# from src.tools.scrape_docs_tool import scrape_docs_tool
# from src.tools.vectorize_and_store_tool import vectorize_and_store_tool

# Import pending request trackers
# from src.tools.scrape_repo_tool import PENDING_SCRAPE_REPO_REQUESTS
# from src.tools.scrape_docs_tool import PENDING_SCRAPE_DOCS_REQUESTS
# from src.tools.vectorize_and_store_tool import PENDING_VECTORIZE_REQUESTS

def get_next_request_id() -> str:
    """
    Generate a unique request ID.
    
    Returns:
        str: A unique request ID
    """
    # Use UUID for unique ID generation
    return str(uuid.uuid4())

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
    
    # We don't need to repeat the HOW TO USE TOOLS section since it's already in the base prompt
    
    return prompt + tools_desc

def handle_tool_calls(response_text: str, user_input: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse tool calls from response text and execute them.
    
    Args:
        response_text: The text to parse for tool calls
        user_input: Optional original user input (not used directly now that the direct tool path is removed)
        
    Returns:
        Dict containing tool calls and execution results
    """
    logger.debug(f"Processing response text for tool calls: {response_text}")
    tool_calls = []
    execution_results = []
    
    # Look for standard tool call format in LLM response
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
        request_id = get_next_request_id()
        logger.debug(f"Executing tool '{call['name']}' with task: {call['args']['task']}")
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

def execute_tool(tool_name: str, args: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
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
    logger.debug(f"[TOOL REQUEST] Received request for '{tool_name}' with request_id: {request_id}")
    
    # Store initial request status
    if request_id is not None:
        logger.debug(f"TRACKING: Storing request {request_id} in PENDING_TOOL_REQUESTS")
        PENDING_TOOL_REQUESTS[request_id] = {
            "name": tool_name,
            "args": args,
            "created_at": timestamp(),
            "status": "received"
        }
    
    # Log start of execution
    logger.debug(f"[TOOL EXECUTION] Starting execution of '{tool_name}' with args: {args} (request_id: {request_id})")
    logger.debug(f"Tool arguments: {json.dumps(args, indent=2)}")
    
    # Update status to in_progress
    if request_id is not None:
        PENDING_TOOL_REQUESTS[request_id]["status"] = "in_progress"
        PENDING_TOOL_REQUESTS[request_id]["execution_started_at"] = timestamp()
        logger.debug(f"TRACKING: Updated request {request_id} status to in_progress")
    
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
                        PENDING_TOOL_REQUESTS[request_id]["completed_at"] = timestamp()
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
                # Import tool modules here to avoid circular imports
                if tool_name == "valet":
                    from src.tools.valet import valet_tool
                    tool_function = valet_tool
                elif tool_name == "personal_assistant":
                    from src.tools.personal_assistant import personal_assistant_tool
                    tool_function = personal_assistant_tool
                elif tool_name == "librarian":
                    from src.tools.librarian import librarian_tool
                    tool_function = librarian_tool
                else:
                    # This should never happen due to the if check above
                    raise ValueError(f"Unknown tool name: {tool_name}")
                
                # Execute the tool
                result = tool_function(task=task, request_id=request_id)
                
                # Update request status based on result
                if request_id is not None:
                    if result and isinstance(result, dict):
                        status = result.get("status", "completed")
                        PENDING_TOOL_REQUESTS[request_id]["status"] = status
                        if status == "completed":
                            PENDING_TOOL_REQUESTS[request_id]["completed_at"] = timestamp()
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
    logger.debug(f"[{timestamp()}] Extracted tool response message: {response_message[:100]}...")
    
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

    # Mark the request as processed to prevent it being found repeatedly in check_completed_tool_requests
    PENDING_TOOL_REQUESTS[request_id]["processed_by_agent"] = True
    logger.debug(f"[{timestamp()}] Marked request {request_id} as processed after generating prompt")

    return prompt

def check_completed_tool_requests() -> Optional[Dict[str, Any]]:
    """
    Check for completed tool requests.
    
    Returns:
        Dict with completed request info or None if no requests are complete
    """
    # Check if there are any completed requests
    for request_id, request_data in list(PENDING_TOOL_REQUESTS.items()):
        if request_data.get("status") in ["completed", "error"] and not request_data.get("processed", False):
            # Mark as processed
            PENDING_TOOL_REQUESTS[request_id]["processed"] = True
            
            # Return the completed request
            return {
                "request_id": request_id,
                "data": request_data
            }
    
    # No completed requests
    return None

def start_tool_checker():
    """Start a background thread to check for completed tool requests."""
    
    def check_loop():
        # Track when we last checked each module to avoid too frequent logging
        last_check_time = now()
        
        while True:
            try:
                # Only log every 60 seconds to avoid spamming logs
                now_time = now()
                if (now_time - last_check_time).total_seconds() > 60:
                    logger.debug("Tool checker thread running")
                    last_check_time = now_time
                
                # Check for completed tool requests
                check_completed_tool_requests()
                
                # Sleep to avoid consuming too much CPU
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error in tool checker thread: {e}")
                # Sleep a bit longer on error
                time.sleep(5)
    
    # Start the thread
    checker_thread = threading.Thread(target=check_loop, daemon=True)
    checker_thread.start()
    logger.debug("Started tool checker thread")

# Start the checker thread when the module is imported
start_tool_checker()