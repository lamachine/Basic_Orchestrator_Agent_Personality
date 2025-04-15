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
    # Original tools are commented out but preserved in the code
    # "valet": {
    #     "description": "Manages household staff, daily schedule, and personal affairs.",
    #     "examples": ["Check my staff tasks", "See if I have any messages"],
    # },
    # "personal_assistant": {
    #     "description": "Handles communications, task lists, calendar, and personal productivity.",
    #     "examples": ["Check my schedule", "Send an email", "What's on my to-do list"],
    # },
    # "librarian": {
    #     "description": "Performs research, documentation, and knowledge management.",
    #     "examples": ["Research Pydantic agents", "Find information about AI tools"],
    # }
    
    # New knowledge management and RAG tools
    "scrape_repo": {
        "description": "Downloads and analyzes GitHub repositories to store their code for later analysis. You MUST use the FULL GitHub URL as the task parameter. This tool runs asynchronously and takes 1-3 minutes to complete.",
        "examples": ["https://github.com/tiangolo/fastapi", 
                     "https://github.com/pydantic/pydantic",
                     "https://github.com/user/repo",
                     "https://github.com/some-org/project"],
        "when_to_use": "When the user explicitly asks to get, scrape, download, or analyze a GitHub repository. Only use with complete GitHub URLs."
    },
    "scrape_web": {
        "description": "Scrapes and analyzes web pages or websites for knowledge capture. You MUST use the FULL URL as the task parameter. This tool runs asynchronously and takes 1-3 minutes to complete.",
        "examples": ["https://www.example.com/docs", 
                     "https://blog.example.com/article",
                     "Analyze the content at https://docs.example.com"],
        "when_to_use": "When the user wants to scrape, analyze, or capture knowledge from a general website. Only use with complete URLs."
    },
    "scrape_docs": {
        "description": "Scrapes documentation websites and stores their contents for analysis. Use this when the user wants to import or analyze documentation from a website.",
        "examples": ["https://pydantic-docs.helpmanual.io/",
                     "Get the FastAPI documentation at https://fastapi.tiangolo.com",
                     "Import the docs from the website docs.python.org"],
        "when_to_use": "When the user explicitly asks to get documentation from a website."
    },
    "vectorize_and_store": {
        "description": "Vectorizes content (files, scraped repos, or documentation) and stores in the database for semantic search. Use this after scraping to process the content.",
        "examples": ["Process the scraped FastAPI docs for searching", 
                     "Store the repo content in the vector database"],
        "when_to_use": "When the user wants to process already scraped content for searching or analysis."
    }
}

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

def handle_tool_calls(response_text: str) -> Dict[str, Any]:
    """Extract and process tool calls from the response text."""
    logger.debug(f"ATTEMPTING TO PROCESS RESPONSE FOR TOOL CALLS")
    logger.debug(f"Processing response for tool calls: {response_text[:100]}...")
    
    # Log the full response at DEBUG level
    logger.debug(f"Full LLM response to check for tool calls: {response_text}")
    
    # Log key parts of the response to help with debugging
    if len(response_text) > 0:
        lines = response_text.split('\n')
        logger.debug(f"Response has {len(lines)} lines, first 3 lines (if available):")
        for i in range(min(3, len(lines))):
            logger.debug(f"Line {i+1}: {lines[i]}")
    
    # More flexible regex to extract tool calls using various patterns
    # Add patterns to match more variations including ones without backticks
    # and the proper format scrape_repo_tool(task="URL")
    tool_patterns = [
        # Exact patterns for specific tools with "_tool" suffix
        r'`?([a-zA-Z_]+_tool)\s*\(\s*task\s*=\s*[\'"](.+?)[\'"]\s*\)`?',  # With _tool suffix
        r'`([a-zA-Z_]+)\s*\(\s*task\s*=\s*[\'"](.+?)[\'"]\s*\)`',  # Standard format with backticks
        r'([a-zA-Z_]+)\s*\(\s*task\s*=\s*[\'"](.+?)[\'"]\s*\)',     # Without backticks
        r'`([a-zA-Z_]+)\s*\([\'"](.+?)[\'"]\)`',                    # Without "task="
        r'([a-zA-Z_]+)\s*\([\'"](.+?)[\'"]\)',                      # Most permissive
    ]
    
    # Try each pattern
    tool_matches = []
    for pattern in tool_patterns:
        matches = re.findall(pattern, response_text)
        if matches:
            logger.debug(f"Found {len(matches)} tool matches with pattern {pattern}")
            tool_matches.extend(matches)
            break  # Stop at first successful pattern
    
    # If no matches, log clearly with detailed examples of correct formats
    if not tool_matches:
        logger.debug("NO TOOL CALLS DETECTED IN LLM RESPONSE")
        logger.debug("Check formatting in LLM output - needs to use format: `tool_name(task=\"description\")`")
        logger.debug("Examples of correct formats:")
        logger.debug("  `scrape_repo(task=\"https://github.com/username/repo\")`")
        logger.debug("  `scrape_docs(task=\"https://fastapi.tiangolo.com\")`")
        logger.debug("  `vectorize_and_store(task=\"Process the FastAPI documentation\")`")
        logger.debug("Tool names must exactly match one of: " + ", ".join(TOOL_DEFINITIONS.keys()))
    
    # Log all matches found
    logger.debug(f"Tool matches found: {tool_matches}")
    
    tool_calls = []
    
    # Process each potential match
    for tool_match in tool_matches:
        # Check if the tool name has a _tool suffix, remove it for matching
        tool_name = tool_match[0].strip()
        if tool_name.endswith('_tool'):
            base_tool_name = tool_name[:-5]  # Remove _tool suffix
            logger.debug(f"Tool name '{tool_name}' has _tool suffix, checking for base name '{base_tool_name}'")
            if base_tool_name in TOOL_DEFINITIONS:
                tool_name = base_tool_name
                logger.debug(f"Using base tool name '{tool_name}' after removing _tool suffix")
        
        task_value = tool_match[1].strip()
        
        # Check if it's a recognized tool (including MCP tools)
        if tool_name in TOOL_DEFINITIONS:
            # Create args dictionary
            args = {'task': task_value}
            
            tool_calls.append({
                "name": tool_name,
                "args": args
            })
            logger.debug(f"VALID TOOL CALL: '{tool_name}' with task='{task_value}'")
        else:
            logger.debug(f"INVALID TOOL: '{tool_name}' is not a recognized tool")
            logger.debug(f"Available tools: {list(TOOL_DEFINITIONS.keys())}")
    
    # Create tool requests and execute them immediately
    execution_results = []
    for call in tool_calls:
        try:
            # Generate a simple request ID
            request_id = get_next_request_id()
            
            # Store the request in our pending requests
            PENDING_TOOL_REQUESTS[request_id] = {
                "name": call["name"],
                "args": call["args"],
                "created_at": datetime.now().isoformat(),
                "status": "pending"
            }
            
            # Execute the tool directly and get the real response
            logger.debug(f"Executing tool: {call['name']} with request_id: {request_id}")
            result = execute_tool(call["name"], call["args"], request_id)
            
            # Add to execution results
            execution_results.append({
                "name": call["name"],
                "args": call["args"],
                "result": result,
                "request_id": request_id
            })
        except Exception as e:
            logger.critical(f"Failed to process tool call: {e}")
            import traceback
            logger.critical(f"Traceback: {traceback.format_exc()}")
    
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
    logger.debug(f"*** EXECUTE_TOOL DIRECT PRINT: Starting execution of '{tool_name}' (request_id: {request_id}) ***")
    
    logger.debug(f"*** TOOL EXECUTION START: '{tool_name}' (request_id: {request_id}) ***")
    logger.debug(f"Tool arguments: {json.dumps(args, indent=2)}")
    
    # Add request_id to args for tools that track them
    args_with_request_id = {**args, "request_id": request_id}

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
                result = loop.run_until_complete(mcp_tool_function(**args_with_request_id))
                loop.close()
                
                # Handle async MCP tool
                if result and result.get("status") == "pending":
                    logger.debug(f"MCP tool request is pending asynchronous execution")
                    # Store the pending request
                    PENDING_TOOL_REQUESTS[request_id] = {
                        "name": tool_name,
                        "args": args,
                        "created_at": datetime.now().isoformat(),
                        "status": "pending",
                        "pending_response": result
                    }
                
                return result
            except Exception as e:
                error_msg = f"Error executing MCP tool {tool_name}: {str(e)}"
                logger.error(error_msg)
                return {
                    "status": "error", 
                    "message": error_msg,
                    "request_id": request_id
                }
        
        # New tools implementations
        elif tool_name == "scrape_repo":
            logger.debug(f"*** DIRECT PRINT: About to import scrape_repo_tool ***")
            logger.debug(f"Importing scrape_repo_tool...")
            from src.tools.scrape_repo_tool import scrape_repo_tool
            logger.debug(f"*** DIRECT PRINT: About to call scrape_repo_tool with {args_with_request_id} ***")
            logger.debug(f"Calling scrape_repo_tool with {args_with_request_id}")
            result = scrape_repo_tool(**args_with_request_id)
            
            # Handle async scrape_repo tool
            if result and result.get("status") == "pending":
                logger.debug(f"*** DIRECT PRINT: Scrape repo request is pending asynchronous execution ***")
                # Store the pending request
                PENDING_TOOL_REQUESTS[request_id] = {
                    "name": "scrape_repo",
                    "args": args,
                    "created_at": datetime.now().isoformat(),
                    "status": "pending",
                    "pending_response": result
                }
                
        elif tool_name == "scrape_web":
            logger.debug(f"*** DIRECT PRINT: About to import scrape_web_tool ***")
            logger.info(f"Importing scrape_web_tool...")
            from src.tools.scrape_web_tool import scrape_web_tool
            logger.debug(f"*** DIRECT PRINT: About to call scrape_web_tool with {args_with_request_id} ***")
            logger.debug(f"Calling scrape_web_tool with {args_with_request_id}")
            result = scrape_web_tool(**args_with_request_id)
            
            # Handle async scrape_web tool
            if result and result.get("status") == "pending":
                logger.debug(f"*** DIRECT PRINT: Scrape web request is pending asynchronous execution ***")
                # Store the pending request
                PENDING_TOOL_REQUESTS[request_id] = {
                    "name": "scrape_web",
                    "args": args,
                    "created_at": datetime.now().isoformat(),
                    "status": "pending",
                    "pending_response": result
                }
        
        elif tool_name == "scrape_docs":
            logger.debug(f"*** DIRECT PRINT: About to import scrape_docs_tool ***")
            logger.info(f"Importing scrape_docs_tool...")
            from src.tools.scrape_docs_tool import scrape_docs_tool
            logger.debug(f"*** DIRECT PRINT: About to call scrape_docs_tool with {args_with_request_id} ***")
            logger.debug(f"Calling scrape_docs_tool with {args_with_request_id}")
            result = scrape_docs_tool(**args_with_request_id)
            
            # Handle async scrape_docs tool
            if result and result.get("status") == "pending":
                logger.debug(f"*** DIRECT PRINT: Scrape docs request is pending asynchronous execution ***")
                # Store the pending request
                PENDING_TOOL_REQUESTS[request_id] = {
                    "name": "scrape_docs",
                    "args": args,
                    "created_at": datetime.now().isoformat(),
                    "status": "pending",
                    "pending_response": result
                }
        
        elif tool_name == "vectorize_and_store":
            logger.debug(f"*** DIRECT PRINT: About to import vectorize_and_store_tool ***")
            logger.debug(f"Importing vectorize_and_store_tool...")
            from src.tools.vectorize_and_store_tool import vectorize_and_store_tool
            logger.debug(f"*** DIRECT PRINT: About to call vectorize_and_store_tool with {json.dumps(args_with_request_id, indent=2)} ***")
            logger.debug(f"Calling vectorize_and_store_tool with {json.dumps(args_with_request_id, indent=2)}")
            result = vectorize_and_store_tool(**args_with_request_id)
            
            # Handle async vectorize_and_store tool
            if result and result.get("status") == "pending":
                logger.debug(f"*** DIRECT PRINT: Vectorize and store request is pending asynchronous execution ***")
                # Store the pending request
                PENDING_TOOL_REQUESTS[request_id] = {
                    "name": "vectorize_and_store",
                    "args": args,
                    "created_at": datetime.now().isoformat(),
                    "status": "pending",
                    "pending_response": result
                }
        else:
            logger.error(f"Unknown tool '{tool_name}' requested")
            return {
                "status": "error",
                "message": f"Unknown tool: {tool_name}",
                "request_id": request_id
            }
        
        # Verify we got a result
        if result is None:
            logger.error(f"Tool {tool_name} returned None")
            result = {
                "status": "error",
                "message": f"Tool {tool_name} returned None",
                "request_id": request_id
            }
        
        # For immediate responses, update pending request with the response
        if result.get("status") != "pending" and request_id in PENDING_TOOL_REQUESTS:
            PENDING_TOOL_REQUESTS[request_id] = {
                **PENDING_TOOL_REQUESTS[request_id],
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "response": result
            }
        
        logger.debug(f"*** EXECUTE_TOOL DIRECT PRINT: Completed execution of '{tool_name}' with status: {result.get('status', 'unknown')} ***")
        logger.debug(f"*** TOOL EXECUTION COMPLETE: '{tool_name}' (status: {result.get('status', 'unknown')}) ***")
        logger.debug(f"Full response: {json.dumps(result, indent=2)}")
        
        return result
    
    except ImportError as e:
        error_msg = f"Import error executing tool '{tool_name}': {str(e)}"
        logger.critical(error_msg)
        logger.debug(f"*** TOOL EXECUTION FAILED: '{tool_name}' (ImportError) ***")
        return {
            "status": "error",
            "message": f"Tool '{tool_name}' not found: {str(e)}",
            "request_id": request_id
        }
    except Exception as e:
        error_msg = f"Error executing tool '{tool_name}': {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.debug(f"*** TOOL EXECUTION FAILED: '{tool_name}' (Exception) ***")
        
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
    tool_name = request["name"]
    response = request.get("response", "No response available")
    
    prompt = f"""You are Ronan, an intelligent assistant.

IMPORTANT INSTRUCTIONS:
1. The user previously asked: "{user_input}"
2. I have RECEIVED THE EXACT RESULTS from the {tool_name} tool
3. You MUST use ONLY these results to answer - DO NOT MAKE UP ANY INFORMATION
4. If these results don't fully answer the query, simply state what IS available
5. DO NOT hallucinate features, capabilities, or information not in the results

Here are the EXACT results received:

====== BEGIN TOOL RESULTS ======
{response}
====== END TOOL RESULTS ======

Provide ONLY information contained in these results to the user.
Be direct and to the point.

Agent:"""

    return prompt 

def check_completed_tool_requests():
    """Check for completed tool requests from all relevant tools."""
    try:
        # Track which modules we've already checked to avoid repeated import attempts
        checked_modules = {}
        
        # Only check for modules that have pending requests
        pending_request_tools = set()
        for request_id, request_info in PENDING_TOOL_REQUESTS.items():
            if request_info.get("status") == "pending":
                tool_name = request_info.get("name", "")
                if tool_name:
                    pending_request_tools.add(tool_name)
        
        # Check for completed MCP requests - these are always checked first
        if not checked_modules.get("mcp", False):
            try:
                # Check MCP completed requests
                check_completed_mcp_requests()
                checked_modules["mcp"] = True
                
                # Direct import for testing specific MCP requests
                from src.services.mcp_services.mcp_adapter import PENDING_MCP_REQUESTS
                for request_id, response in list(PENDING_MCP_REQUESTS.items()):
                    if request_id in PENDING_TOOL_REQUESTS and PENDING_TOOL_REQUESTS[request_id].get("status") != "completed":
                        status = response.get("status")
                        if status in ["completed", "error"]:
                            logger.debug(f"*** DIRECT PRINT: Found completed MCP request: {request_id} ***")
                            logger.info(f"Found completed MCP request: {request_id} with status: {status}")
                            
                            # For errors, include the error message in the response
                            if status == "error":
                                error_msg = response.get("error", "Unknown error")
                                logger.error(f"MCP request {request_id} failed: {error_msg}")
                                response = {
                                    "status": "error",
                                    "message": f"The request failed: {error_msg}",
                                    "error": error_msg
                                }
                            
                            # Update the pending request with the result
                            PENDING_TOOL_REQUESTS[request_id] = {
                                **PENDING_TOOL_REQUESTS[request_id],
                                "status": status,
                                "completed_at": datetime.now().isoformat(),
                                "response": response
                            }
                            
                            # Remove from MCP's pending requests
                            del PENDING_MCP_REQUESTS[request_id]
            except ImportError:
                checked_modules["mcp"] = False
                if not hasattr(check_completed_tool_requests, "logged_mcp"):
                    logger.debug("MCP services not available for checking completed requests")
                    check_completed_tool_requests.logged_mcp = True
            except Exception as e:
                logger.error(f"Error checking MCP requests: {e}")
            
        # Track which modules we've already checked to avoid repeated import attempts
        checked_modules = {}
        
        # Only check for modules that have pending requests
        pending_request_tools = set()
        for request_id, request_info in PENDING_TOOL_REQUESTS.items():
            if request_info.get("status") == "pending":
                tool_name = request_info.get("name", "")
                if tool_name:
                    pending_request_tools.add(tool_name)
        
        # Only log about imports the first time we run
        if not hasattr(check_completed_tool_requests, "has_run"):
            logger.debug(f"Available tools to check: {pending_request_tools}")
            check_completed_tool_requests.has_run = True
            
        # Check for completed scrape_repo requests if we have any pending
        if "scrape_repo" in pending_request_tools and "scrape_repo" not in checked_modules:
            try:
                from src.tools.scrape_repo_tool import PENDING_SCRAPE_REPO_REQUESTS
                checked_modules["scrape_repo"] = True
                
                for request_id, response in list(PENDING_SCRAPE_REPO_REQUESTS.items()):
                    if request_id in PENDING_TOOL_REQUESTS and PENDING_TOOL_REQUESTS[request_id].get("status") != "completed":
                        logger.debug(f"*** DIRECT PRINT: Found completed scrape_repo request: {request_id} ***")
                        logger.debug(f"Found completed scrape_repo request: {request_id}")
                        
                        PENDING_TOOL_REQUESTS[request_id] = {
                            **PENDING_TOOL_REQUESTS[request_id],
                            "status": "completed",
                            "completed_at": datetime.now().isoformat(),
                            "response": response
                        }
                        
                        # Remove from tool's pending requests
                        del PENDING_SCRAPE_REPO_REQUESTS[request_id]
            except ImportError:
                checked_modules["scrape_repo"] = False
                if not hasattr(check_completed_tool_requests, "logged_scrape_repo"):
                    logger.debug("scrape_repo_tool module not available for checking completed requests")
                    check_completed_tool_requests.logged_scrape_repo = True
        
        # Check for completed scrape_docs requests if we have any pending
        if "scrape_docs" in pending_request_tools and "scrape_docs" not in checked_modules:
            try:
                from src.tools.scrape_docs_tool import PENDING_SCRAPE_DOCS_REQUESTS
                checked_modules["scrape_docs"] = True
                
                for request_id, response in list(PENDING_SCRAPE_DOCS_REQUESTS.items()):
                    if request_id in PENDING_TOOL_REQUESTS and PENDING_TOOL_REQUESTS[request_id].get("status") != "completed":
                        logger.debug(f"*** DIRECT PRINT: Found completed scrape_docs request: {request_id} ***")
                        logger.info(f"Found completed scrape_docs request: {request_id}")
                        
                        PENDING_TOOL_REQUESTS[request_id] = {
                            **PENDING_TOOL_REQUESTS[request_id],
                            "status": "completed",
                            "completed_at": datetime.now().isoformat(),
                            "response": response
                        }
                        
                        # Remove from tool's pending requests
                        del PENDING_SCRAPE_DOCS_REQUESTS[request_id]
            except ImportError:
                checked_modules["scrape_docs"] = False
                if not hasattr(check_completed_tool_requests, "logged_scrape_docs"):
                    logger.debug("scrape_docs_tool module not available for checking completed requests")
                    check_completed_tool_requests.logged_scrape_docs = True
        
        # Check for completed vectorize_and_store requests if we have any pending
        if "vectorize_and_store" in pending_request_tools and "vectorize_and_store" not in checked_modules:
            try:
                from src.tools.vectorize_and_store_tool import PENDING_VECTORIZE_REQUESTS
                checked_modules["vectorize_and_store"] = True
                
                for request_id, response in list(PENDING_VECTORIZE_REQUESTS.items()):
                    if request_id in PENDING_TOOL_REQUESTS and PENDING_TOOL_REQUESTS[request_id].get("status") != "completed":
                        logger.debug(f"*** DIRECT PRINT: Found completed vectorize_and_store request: {request_id} ***")
                        logger.info(f"Found completed vectorize_and_store request: {request_id}")
                        
                        PENDING_TOOL_REQUESTS[request_id] = {
                            **PENDING_TOOL_REQUESTS[request_id],
                            "status": "completed",
                            "completed_at": datetime.now().isoformat(),
                            "response": response
                        }
                        
                        # Remove from tool's pending requests
                        del PENDING_VECTORIZE_REQUESTS[request_id]
            except ImportError:
                checked_modules["vectorize_and_store"] = False
                if not hasattr(check_completed_tool_requests, "logged_vectorize"):
                    logger.debug("vectorize_and_store_tool module not available for checking completed requests")
                    check_completed_tool_requests.logged_vectorize = True
            
        # Keep the librarian checker in case it's needed in the future
        if "librarian" in pending_request_tools and "librarian" not in checked_modules:
            try:
                from src.tools.librarian import PENDING_LIBRARIAN_REQUESTS
                checked_modules["librarian"] = True
                
                for request_id, response in list(PENDING_LIBRARIAN_REQUESTS.items()):
                    if request_id in PENDING_TOOL_REQUESTS and PENDING_TOOL_REQUESTS[request_id].get("status") != "completed":
                        logger.debug(f"*** DIRECT PRINT: Found completed librarian request: {request_id} ***")
                        logger.info(f"Found completed librarian request: {request_id}")
                        
                        PENDING_TOOL_REQUESTS[request_id] = {
                            **PENDING_TOOL_REQUESTS[request_id],
                            "status": "completed",
                            "completed_at": datetime.now().isoformat(),
                            "response": response
                        }
                        
                        # Remove from librarian's pending requests
                        del PENDING_LIBRARIAN_REQUESTS[request_id]
            except ImportError:
                checked_modules["librarian"] = False
                if not hasattr(check_completed_tool_requests, "logged_librarian"):
                    logger.debug("Librarian module not available for checking completed requests")
                    check_completed_tool_requests.logged_librarian = True
        
    except Exception as e:
        logger.error(f"Error checking completed tool requests: {e}")

# Start a background thread to periodically check for completed tool requests
def start_tool_checker():
    """Start a background thread to check for completed tool requests."""
    def check_loop():
        # Track when we last checked each module to avoid too frequent logging
        last_checked = {}
        check_interval = 5  # Log availability every 5 seconds at most
        
        while True:
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
                check_completed_tool_requests()
            finally:
                # Restore original level
                logger.setLevel(original_level)
                
            time.sleep(1)  # Check every second
            
    checker_thread = threading.Thread(target=check_loop)
    checker_thread.daemon = True
    checker_thread.start()
    logger.info("Started background thread to check for completed tool requests")

# Start the checker thread when the module is imported
start_tool_checker() 