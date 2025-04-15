"""
MCP Tool Integration

This module provides integration between the Multi-agent Communication Protocol (MCP)
and the orchestrator's tool system, allowing MCP endpoints to be used as tools.
"""

import os
import sys
import time
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from dotenv import load_dotenv

# Add project path for imports
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from src.services.mcp_services.mcp_adapter import MCPAdapter, PENDING_MCP_REQUESTS, check_mcp_status

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize variables
mcp_adapter = None
MCP_TOOL_REGISTRY = {}
MCP_TOOL_DEFINITIONS = {}

def initialize_mcp_client() -> bool:
    """
    Initialize the MCP client and register tools.
    This is called lazily when needed rather than at import time.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global mcp_adapter, MCP_TOOL_DEFINITIONS
    
    try:
        # Load environment variables first
        load_dotenv(override=True)
        
        # Initialize the MCP adapter
        mcp_adapter = MCPAdapter()
        
        # Register MCP tools
        MCP_TOOL_DEFINITIONS = register_mcp_tools()
        
        return True
    except Exception as e:
        logger.error(f"Error initializing MCP client: {e}")
        return False

def register_mcp_tools():
    """
    Register all MCP tools in the tool registry.
    
    This function dynamically creates tool functions for each MCP endpoint
    and capability combination, and registers them in the MCP_TOOL_REGISTRY.
    
    Returns:
        Dictionary of tool definitions for registered MCP tools
    """
    tool_definitions = {}
    
    # Get available endpoints from adapter config
    endpoints = mcp_adapter.config.get("endpoints", {})
    
    # Iterate through configured endpoints and their capabilities
    for endpoint_name, endpoint_config in endpoints.items():
        # Skip endpoints that don't have required configuration
        if endpoint_name == "brave_search" and not os.environ.get("BRAVE_API_KEY"):
            logger.warning(f"Skipping {endpoint_name} registration - missing API key")
            continue
            
        capabilities = endpoint_config.get("capabilities", [])
        for capability in capabilities:
            # Create a unique tool name
            tool_name = f"mcp_{endpoint_name}_{capability}"
            
            # Create a tool function that calls the MCP adapter
            tool_function = create_mcp_tool_function(endpoint_name, capability)
            
            # Register the tool function
            MCP_TOOL_REGISTRY[tool_name] = tool_function
            
            # Create a tool definition
            description = generate_tool_description(endpoint_name, capability)
            examples = generate_tool_examples(endpoint_name, capability)
            
            tool_definitions[tool_name] = {
                "description": description,
                "examples": examples,
                "endpoint": endpoint_name,
                "capability": capability
            }
    
    logger.debug(f"Registered {len(tool_definitions)} MCP tools")
    return tool_definitions

def create_mcp_tool_function(endpoint_name: str, capability: str) -> Callable:
    """
    Create a tool function for a specific MCP endpoint and capability.
    
    Args:
        endpoint_name: The name of the MCP endpoint
        capability: The specific capability to invoke
        
    Returns:
        A function that calls the MCP adapter with the specified endpoint and capability
    """
    async def mcp_tool_function(**kwargs) -> Dict[str, Any]:
        """
        Call an MCP endpoint with the given parameters.
        
        Args:
            **kwargs: Parameters to pass to the MCP endpoint
            
        Returns:
            Response from the MCP endpoint
        """
        # Extract request_id if present
        request_id = kwargs.pop("request_id", None)
        
        # Call the MCP adapter
        try:
            result = await mcp_adapter.call_mcp(
                endpoint_name=endpoint_name,
                capability=capability,
                parameters=kwargs,
                task_id=request_id
            )
            return result
        except Exception as e:
            error_msg = f"Error calling MCP endpoint {endpoint_name}.{capability}: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "request_id": request_id
            }
    
    return mcp_tool_function

def generate_tool_description(endpoint_name: str, capability: str) -> str:
    """
    Generate a description for an MCP tool.
    
    Args:
        endpoint_name: The name of the MCP endpoint
        capability: The specific capability
        
    Returns:
        A human-readable description of the tool
    """
    descriptions = {
        # Brave Search descriptions
        "brave_search": {
            "brave_web_search": "Performs a web search using the Brave Search API, ideal for general queries, news, articles, and online content. Use this for broad information gathering, recent events, or when you need diverse web sources. Supports pagination, content filtering, and freshness controls. Maximum 20 results per request, with offset for pagination. ",
            "brave_local_search": "Searches for local businesses and places using Brave's Local Search API. Best for queries related to physical locations, businesses, restaurants, services, etc. Returns detailed information including:\n- Business names and addresses\n- Ratings and review counts\n- Phone numbers and opening hours\nUse this when the query implies 'near me' or mentions specific locations. Automatically falls back to web search if no local results are found."
        },
        # Git descriptions
        "git": {
            "git_status": "Shows the working tree status",
            "git_diff_unstaged": "Shows changes in the working directory that are not yet staged",
            "git_diff_staged": "Shows changes that are staged for commit",
            "git_diff": "Shows differences between branches or commits",
            "git_commit": "Records changes to the repository",
            "git_add": "Adds file contents to the staging area",
            "git_reset": "Unstages all staged changes",
            "git_log": "Shows the commit logs",
            "git_create_branch": "Creates a new branch from an optional base branch",
            "git_checkout": "Switches branches",
            "git_show": "Shows the contents of a commit",
            "git_init": "Initialize a new Git repository"
        },
        # Postgres descriptions
        "postgres": {
            "query": "Run a read-only SQL query"
        }
    }
    
    # Get the description from our map, or use a generic one
    if endpoint_name in descriptions and capability in descriptions[endpoint_name]:
        return descriptions[endpoint_name][capability]
    else:
        return f"Calls the {capability} capability of the {endpoint_name} MCP endpoint."

def generate_tool_examples(endpoint_name: str, capability: str) -> List[str]:
    """
    Generate examples for an MCP tool.
    
    Args:
        endpoint_name: The name of the MCP endpoint
        capability: The specific capability
        
    Returns:
        A list of example usages for the tool
    """
    examples = {
        # Brave Search examples
        "brave_search": {
            "brave_web_search": [
                "Search for 'climate change solutions'",
                "Find recent news about artificial intelligence",
                "Look up information about Python programming language"
            ],
            "brave_local_search": [
                "Find restaurants near me",
                "Search for coffee shops in New York",
                "Look for hotels in San Francisco"
            ]
        },
        # Git examples
        "git": {
            "git_status": ["Check the status of the git repository"],
            "git_diff_unstaged": ["Show unstaged changes"],
            "git_diff_staged": ["Show staged changes"],
            "git_diff": ["Show differences between main and develop branches"],
            "git_commit": ["Commit changes with message 'Fix bug in user authentication'"],
            "git_add": ["Stage modified files in the src directory"],
            "git_reset": ["Unstage all changes"],
            "git_log": ["Show recent commit history"],
            "git_create_branch": ["Create a new 'feature/user-profile' branch"],
            "git_checkout": ["Switch to the 'develop' branch"],
            "git_show": ["Show details of the latest commit"],
            "git_init": ["Initialize a new git repository"]
        },
        # Postgres examples
        "postgres": {
            "query": [
                "Run query 'SELECT * FROM users LIMIT 10'",
                "Get the count of active users with 'SELECT COUNT(*) FROM users WHERE status = \"active\"'"
            ]
        }
    }
    
    # Get examples from our map, or use generic ones
    if endpoint_name in examples and capability in examples[endpoint_name]:
        return examples[endpoint_name][capability]
    else:
        return [f"Call the {capability} capability of the {endpoint_name} MCP endpoint"]

def check_completed_mcp_requests():
    """
    Check for completed MCP requests.
    
    This function should be called periodically to check for completed MCP requests
    and update the orchestrator's pending tool requests.
    """
    from src.agents.orchestrator_tools import PENDING_TOOL_REQUESTS
    
    try:
        # Look for completed MCP requests
        for task_id, response in list(PENDING_MCP_REQUESTS.items()):
            status = response.get("status")
            
            # Only process completed or error requests that haven't been processed yet
            if status in ["completed", "error"] and task_id in PENDING_TOOL_REQUESTS:
                # Skip if already marked as completed in PENDING_TOOL_REQUESTS
                if PENDING_TOOL_REQUESTS[task_id].get("status") in ["completed", "error"]:
                    # Clean up the MCP request since it's already been processed
                    del PENDING_MCP_REQUESTS[task_id]
                    continue
                    
                logger.debug(f"Found completed MCP request: {task_id}")
                
                # Update the tool request with the MCP response
                PENDING_TOOL_REQUESTS[task_id] = {
                    **PENDING_TOOL_REQUESTS[task_id],
                    "status": status,
                    "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "response": response.get("result", response)
                }
                
                # Remove from MCP's pending requests
                del PENDING_MCP_REQUESTS[task_id]
    except Exception as e:
        logger.error(f"Error checking completed MCP requests: {str(e)}") 