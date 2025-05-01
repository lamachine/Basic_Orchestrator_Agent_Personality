"""
Multi-agent Communication Protocol (MCP) Adapter

This module provides an adapter layer for communicating with MCP-compliant agents,
allowing the orchestrator to use them as tools.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
import requests
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client, Client

from src.services.logging_service import get_logger
from src.services.db_services.query_service import execute_query

# Add project path for imports
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Configure logging
logger = get_logger(__name__)

# Dictionary to store pending MCP requests
PENDING_MCP_REQUESTS = {}

class MCPAdapter:
    """
    Adapter class for interacting with MCP-compliant agents.
    
    This class provides methods to call MCP endpoints, handle responses,
    and maintain state for asynchronous interactions.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the MCP adapter.
        
        Args:
            config_path: Optional path to an MCP configuration file
        """
        self.config = self._load_config(config_path)
        self.session = requests.Session()
        
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load MCP configuration from file or environment variables.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Dictionary containing MCP configuration
        """
        default_config = {
            "endpoints": {
                "brave_search": {
                    "url": "https://api.search.brave.com/search",
                    "auth": {"api_key": os.environ.get("BRAVE_API_KEY")},
                    "capabilities": ["brave_web_search", "brave_local_search"],
                    "headers": {
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": os.environ.get("BRAVE_API_KEY")
                    }
                },
                "git": {
                    "url": "local",
                    "capabilities": ["git_status", "git_diff", "git_commit", "git_add", 
                                    "git_reset", "git_log", "git_create_branch", 
                                    "git_checkout", "git_show", "git_init"]
                },
                "postgres": {
                    "url": os.environ.get("POSTGRES_URL", "local"),
                    "capabilities": ["query"]
                }
            },
            "timeout": int(os.environ.get("MCP_TIMEOUT", "30")),
            "retry_attempts": int(os.environ.get("MCP_RETRY_ATTEMPTS", "3"))
        }
        
        # If no config path provided, use default config
        if not config_path:
            return default_config
            
        try:
            with open(config_path, 'r') as f:
                custom_config = json.load(f)
                # Merge custom config with defaults
                return {**default_config, **custom_config}
        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")
            return default_config
    
    async def call_mcp(
        self,
        endpoint_name: str,
        capability: str,
        parameters: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call an MCP endpoint and return the response.
        
        Args:
            endpoint_name: Name of the MCP endpoint to call
            capability: Specific capability to invoke
            parameters: Parameters to pass to the capability
            task_id: Optional task ID for tracking the request
            
        Returns:
            Response from the MCP endpoint
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
            
        # Check if endpoint exists in config
        if endpoint_name not in self.config["endpoints"]:
            return {
                "status": "error",
                "task_id": task_id,
                "error": f"Unknown MCP endpoint: {endpoint_name}"
            }
            
        endpoint_config = self.config["endpoints"][endpoint_name]
        
        # Check if capability is supported by this endpoint
        if capability not in endpoint_config["capabilities"]:
            return {
                "status": "error",
                "task_id": task_id,
                "error": f"Capability '{capability}' not supported by endpoint '{endpoint_name}'"
            }
            
        # Initialize pending request
        PENDING_MCP_REQUESTS[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "endpoint": endpoint_name,
            "capability": capability,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # For local endpoints, handle differently
        if endpoint_config["url"] == "local":
            # Start processing in a background thread
            threading.Thread(
                target=self._process_local_mcp_request,
                args=(endpoint_name, capability, parameters, task_id),
                daemon=True
            ).start()
            
            # Return immediately with pending status
            return {
                "status": "pending",
                "task_id": task_id,
                "message": f"MCP request initiated for {endpoint_name}.{capability}",
                "check_command": f"Use check_mcp_status('{task_id}') to check the status of this task"
            }
        
        # For remote endpoints, prepare the request
        url = f"{endpoint_config['url']}/mcp/{capability}"
        headers = {"Content-Type": "application/json"}
        
        # Add authentication if configured
        if "auth" in endpoint_config:
            auth_config = endpoint_config["auth"]
            if "api_key" in auth_config:
                headers["Authorization"] = f"Bearer {auth_config['api_key']}"
        
        # Start processing in a background thread
        threading.Thread(
            target=self._process_remote_mcp_request,
            args=(url, headers, parameters, task_id, endpoint_name, capability),
            daemon=True
        ).start()
        
        # Return immediately with pending status
        return {
            "status": "pending",
            "task_id": task_id,
            "message": f"MCP request initiated for {endpoint_name}.{capability}",
            "check_command": f"Use check_mcp_status('{task_id}') to check the status of this task"
        }
    
    def _process_local_mcp_request(
        self,
        endpoint_name: str,
        capability: str,
        parameters: Dict[str, Any],
        task_id: str
    ) -> Dict[str, Any]:
        """
        Process a local MCP request.
        
        Args:
            endpoint_name: Name of the MCP endpoint
            capability: Specific capability to invoke
            parameters: Parameters to pass to the capability
            task_id: Task ID for tracking the request
            
        Returns:
            Result of the local MCP operation
        """
        try:
            logger.debug(f"Processing local MCP request: {endpoint_name}.{capability}")
            
            # Handle Git operations
            if endpoint_name == "git":
                # Git operations are disabled
                result = {
                    "status": "error",
                    "error": "Git operations not supported in local mode"
                }

            # Handle Postgres operations
            elif endpoint_name == "postgres":
                result = execute_query(parameters.get("sql", ""))
            
            # Unsupported local endpoint
            else:
                result = {
                    "status": "error",
                    "error": f"Unsupported local MCP endpoint: {endpoint_name}"
                }
            
            # Update the pending request with the result
            PENDING_MCP_REQUESTS[task_id] = {
                **PENDING_MCP_REQUESTS[task_id],
                "status": "completed" if result.get("status") != "error" else "error",
                "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "result": result
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing local MCP request: {str(e)}"
            logger.error(error_msg)
            
            # Update the pending request with the error
            PENDING_MCP_REQUESTS[task_id] = {
                **PENDING_MCP_REQUESTS[task_id],
                "status": "error",
                "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": error_msg
            }
            
            return {
                "status": "error",
                "error": error_msg
            }
    
    def _process_remote_mcp_request(
        self,
        url: str,
        headers: Dict[str, str],
        parameters: Dict[str, Any],
        task_id: str,
        endpoint_name: str,
        capability: str
    ) -> Dict[str, Any]:
        """
        Process a remote MCP request.
        
        Args:
            url: URL to send the request to
            headers: HTTP headers to include
            parameters: Parameters to pass in the request body
            task_id: Task ID for tracking the request
            endpoint_name: Name of the MCP endpoint
            capability: Specific capability being invoked
            
        Returns:
            Result of the remote MCP operation
        """
        try:
            logger.debug(f"Sending MCP request to {url}")
            
            # Make the API request
            response = self.session.post(
                url,
                headers=headers,
                json=parameters,
                timeout=self.config.get("timeout", 30)
            )
            
            # Parse the response
            if response.status_code == 200:
                result = response.json()
                
                # Update the pending request with the result
                PENDING_MCP_REQUESTS[task_id] = {
                    **PENDING_MCP_REQUESTS[task_id],
                    "status": "completed",
                    "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "result": result
                }
                
                return result
            else:
                # Create a more descriptive error message based on status code
                error_msg = ""
                if response.status_code == 403:
                    error_msg = "Access forbidden - API key may be missing or invalid"
                elif response.status_code == 401:
                    error_msg = "Unauthorized - authentication required"
                elif response.status_code == 429:
                    error_msg = "Too many requests - rate limit exceeded"
                else:
                    error_msg = f"Request failed with status {response.status_code}"
                
                if response.text:
                    error_msg += f": {response.text}"
                
                logger.error(error_msg)
                
                # Update the pending request with the error
                PENDING_MCP_REQUESTS[task_id] = {
                    **PENDING_MCP_REQUESTS[task_id],
                    "status": "error",
                    "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "error": error_msg
                }
                
                return {
                    "status": "error",
                    "error": error_msg,
                    "http_status": response.status_code
                }
                
        except requests.RequestException as e:
            error_msg = f"Error sending MCP request: {str(e)}"
            logger.error(error_msg)
            
            # Update the pending request with the error
            PENDING_MCP_REQUESTS[task_id] = {
                **PENDING_MCP_REQUESTS[task_id],
                "status": "error",
                "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": error_msg
            }
            
            return {
                "status": "error",
                "error": error_msg
            }

def check_mcp_status(task_id: str) -> Dict[str, Any]:
    """
    Check the status of an MCP request.
    
    Args:
        task_id: The ID of the task to check
        
    Returns:
        Dictionary with the current status of the task
    """
    if task_id not in PENDING_MCP_REQUESTS:
        return {
            "status": "error",
            "error": f"No MCP task found with ID {task_id}"
        }
    
    result = PENDING_MCP_REQUESTS[task_id]
    
    # If the task is completed, we could remove it from the dictionary
    # after a certain time period to keep memory usage down
    
    return result 