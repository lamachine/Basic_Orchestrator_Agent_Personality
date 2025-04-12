"""Tools integration for the orchestrator agent."""

from typing import Dict, Any, Optional, List
import re
import json
import logging
import os
import uuid
from datetime import datetime

from src.tools import (
    ToolParser,
    initialize_tools,
    get_tool_prompt_section
)

# Setup logging
logger = logging.getLogger(__name__)

# Track pending tool requests
PENDING_TOOL_REQUESTS = {}

# Define tool schemas and descriptions
TOOL_DEFINITIONS = {
    "valet": {
        "description": "Manages household staff, daily schedule, and personal affairs.",
        "examples": ["Check my staff tasks", "See if I have any messages"],
        "response": "All staff tasks are either complete or in process, you have no appointments today, and your wife sent a new message in slack."
    },
    "personal_assistant": {
        "description": "Handles communications, task lists, calendar, and personal productivity.",
        "examples": ["Check my schedule", "Send an email", "What's on my to-do list"],
        "response": "Your schedule for today is clear. You have no meetings or appointments scheduled. There are three items on your to-do list: 1) Review quarterly report draft, 2) Call back client Johnson, and 3) Schedule dentist appointment."
    },
    "librarian": {
        "description": "Performs research, documentation, and knowledge management.",
        "examples": ["Research Pydantic agents", "Find information about AI tools"],
        "response": "Web search and documentation crawl complete for Pydantic agents, it is now accessible through standard database tools. Summary of task can be emailed or reviewed now."
    }
}

def add_tools_to_prompt(prompt: str) -> str:
    """Add tool descriptions to the prompt."""
    tools_desc = "\n\n# AVAILABLE TOOLS\n\n"
    
    for tool_name, tool_info in TOOL_DEFINITIONS.items():
        tools_desc += f"## {tool_name}\n"
        tools_desc += f"{tool_info['description']}\n\n"
        
        # Add example usage
        tools_desc += "Example: "
        example = tool_info['examples'][0] if tool_info['examples'] else "Check status"
        tools_desc += f"`{tool_name}(task='{example}')`\n\n"
    
    tools_desc += "To use a tool, write its name followed by the parameters in parentheses.\n"
    tools_desc += "Example: `tool_name(parameter='value')`\n"
    
    return prompt + tools_desc

def handle_tool_calls(response_text: str) -> Dict[str, Any]:
    """Extract and process tool calls from the response text."""
    logger.debug(f"Processing response for tool calls: {response_text[:100]}...")
    
    # Simple regex to extract tool calls in the standard format: `tool_name(param='value')`
    tool_pattern = r'`([a-zA-Z_]+)\((.*?)\)`'
    
    # Extract all potential tool calls
    tool_matches = re.findall(tool_pattern, response_text)
    tool_calls = []
    
    # Process each potential match
    for tool_match in tool_matches:
        tool_name = tool_match[0].strip()
        args_str = tool_match[1].strip()
        
        # Only process if it's a recognized tool
        if tool_name in TOOL_DEFINITIONS:
            # Parse arguments
            args = {}
            if args_str:
                # Simple parameter=value parsing
                arg_pattern = r"(\w+)=['\"](.*?)['\"]"
                arg_matches = re.findall(arg_pattern, args_str)
                
                if arg_matches:
                    for arg_match in arg_matches:
                        args[arg_match[0]] = arg_match[1]
                else:
                    # Handle simple string case
                    args['task'] = args_str.strip("'\"")
            
            tool_calls.append({
                "name": tool_name,
                "args": args
            })
            logger.debug(f"Found tool call: {tool_name} with args: {args}")
    
    # Alternative: Check for direct mentions of tool names in user request
    if not tool_calls:
        # Look for the last user query in the conversation
        user_query_match = re.search(r'user:.*?([^\n]+)|User:.*?([^\n]+)', response_text, re.IGNORECASE)
        
        if user_query_match:
            user_query = user_query_match.group(1) or user_query_match.group(2)
            user_query = user_query.lower()
            
            # Check for direct tool mentions
            if "librarian" in user_query:
                tool_calls.append({
                    "name": "librarian",
                    "args": {"task": "Check status"}
                })
            elif "personal assistant" in user_query or "schedule" in user_query:
                tool_calls.append({
                    "name": "personal_assistant",
                    "args": {"task": "Check schedule"}
                })
            elif "valet" in user_query:
                tool_calls.append({
                    "name": "valet",
                    "args": {"task": "Check staff status"}
                })
    
    # Create tool requests and acknowledgment responses
    execution_results = []
    for call in tool_calls:
        # Generate a request ID
        request_id = str(uuid.uuid4())
        
        # Create a pending tool request
        PENDING_TOOL_REQUESTS[request_id] = {
            "name": call["name"],
            "args": call["args"],
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # Create an acknowledgment message - ONLY an acknowledgment, no fake results
        tool_name = call["name"]
        acknowledgment = {
            "status": "pending",
            "message": f"I've forwarded your request to the {tool_name} tool. Your request has been queued and will be processed as soon as possible. (Request ID: {request_id})",
            "request_id": request_id
        }
        
        execution_results.append({
            "name": call["name"],
            "args": call["args"],
            "result": acknowledgment,
            "request_id": request_id
        })
    
    return {
        "tool_calls": tool_calls,
        "execution_results": execution_results
    }

def execute_tool(tool_name: str, args: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a tool call and return the result.
    
    In a real implementation, this might submit the request to a queue or external service.
    For demo purposes, we'll simulate the tool executing instantly.
    """
    logger.debug(f"Executing tool: {tool_name} with args: {args}")
    
    # Get the predefined response for this tool
    if tool_name in TOOL_DEFINITIONS:
        response = TOOL_DEFINITIONS[tool_name]["response"]
        
        # If we have a request ID, update the pending request with the result
        if request_id and request_id in PENDING_TOOL_REQUESTS:
            PENDING_TOOL_REQUESTS[request_id] = {
                **PENDING_TOOL_REQUESTS[request_id],
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "response": response
            }
        
        return {
            "status": "success",
            "message": response,
            "request_id": request_id
        }
    else:
        return {
            "status": "error",
            "message": f"Unknown tool: {tool_name}",
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
        status = result["result"]["status"]
        
        if status == "pending":
            result_text += f"{tool_name} (Request ID: {request_id}): {message}\n\n"
        else:
            result_text += f"{tool_name}: {message}\n\n"
    
    return result_text

def check_pending_tool_requests() -> List[Dict[str, Any]]:
    """
    Check for any pending tool requests that have been completed.
    
    In a real implementation, this would poll an external service or queue.
    For demo purposes, we'll simulate completing requests after a delay.
    """
    completed_requests = []
    current_time = datetime.now()
    
    # Process each pending request
    for request_id, request in list(PENDING_TOOL_REQUESTS.items()):
        if request["status"] == "pending":
            # Only complete requests that are at least 10 seconds old
            created_time = datetime.fromisoformat(request["created_at"])
            elapsed_seconds = (current_time - created_time).total_seconds()
            
            if elapsed_seconds < 10:
                # Request is still "processing"
                logger.debug(f"Request {request_id} is still processing ({elapsed_seconds:.1f} seconds elapsed)")
                continue
                
            # The request has "completed" after the delay
            logger.debug(f"Completing request {request_id} after {elapsed_seconds:.1f} seconds")
            
            # Execute the tool and get the response
            tool_name = request["name"]
            args = request["args"]
            result = execute_tool(tool_name, args, request_id)
            
            # Add to completed requests
            completed_requests.append({
                "request_id": request_id,
                "name": tool_name,
                "args": args,
                "result": result
            })
    
    return completed_requests

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