"""Librarian tool implementation."""

from typing import Dict, Any, Optional
import logging
import time
import json
import sys
import threading
from datetime import datetime
import uuid

# Setup logger
logger = logging.getLogger(__name__)

# Import orchestrator's request tracking
from src.agents.orchestrator_tools import PENDING_TOOL_REQUESTS

def _process_task(task: str, request_id: str):
    """
    Simulates task processing by waiting for 5 seconds.
    
    Args:
        task: The task to process
        request_id: The request ID for tracking
        
    Returns:
        Dict containing the processed task result
    """
    try:
        start_time = datetime.now()
        logger.debug(f"[{start_time.isoformat()}] Librarian tool processing: Waiting 5 seconds for request_id={request_id}")
        
        # Simulated processing time with a synthetic 5 second delay
        time.sleep(5)
        
        # Simulate task completion
        completion_time = datetime.now()
        logger.info(f"[{completion_time.isoformat()}] Librarian task processing completed after {(completion_time-start_time).total_seconds():.2f} seconds")

        # Generate a response
        response = {
            "status": "success",
            "message": f"Completed research on: '{task}' [Request ID: {request_id}]",
            "timestamp": completion_time.isoformat(),
            "request_id": request_id
        }
        
        # Update the global requests dictionary
        try:
            logger.debug(f"[{completion_time.isoformat()}] Updating PENDING_TOOL_REQUESTS[{request_id}] with completed response")
            PENDING_TOOL_REQUESTS[request_id] = {
                "name": "librarian",
                "status": "completed",
                "message": response["message"],
                "completed_at": completion_time.isoformat(),
                "response": response
            }
            logger.info(f"[{completion_time.isoformat()}] Librarian tool completed: response for request_id={request_id}")
        
        except Exception as e:
            logger.error(f"[{completion_time.isoformat()}] Error updating PENDING_TOOL_REQUESTS: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing librarian task: {e}")
        return {
            "status": "error",
            "message": f"Failed to process librarian task: {str(e)}",
            "request_id": request_id
        }

def librarian_tool(task: str, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Processes a research or knowledge management task.
    
    Args:
        task: The task to process
        request_id: Optional request ID for tracking
        
    Returns:
        Dict with the tool response
    """
    try:
        # Record the current time
        current_time = datetime.now()
        logger.debug(f"[{current_time.isoformat()}] Librarian tool called with task: {task}, request_id: {request_id}")
        
        # Generate a request ID if none provided
        if request_id is None:
            request_id = str(uuid.uuid4())
            logger.debug(f"[{current_time.isoformat()}] Generated new request_id: {request_id}")
        else:
            logger.debug(f"[{current_time.isoformat()}] Using provided request_id: {request_id}")
        
        # Add to pending requests
        PENDING_TOOL_REQUESTS[request_id] = {
            "name": "librarian",
            "status": "pending",
            "created_at": current_time.isoformat(),
            "request_id": request_id,
            "task": task
        }
        
        # Start a background thread to process the request
        task_thread = threading.Thread(
            target=_process_task,
            args=(task, request_id)
        )
        task_thread.daemon = True
        task_thread.start()
        logger.debug(f"[{current_time.isoformat()}] Started background processing thread for request_id={request_id}")
        
        # Return immediate acknowledgment - stored directly in the PENDING_TOOL_REQUESTS
        # with the same request_id that was passed in
        response = {
            "status": "pending",
            "message": f"I'll research information about '{task}' for you. Please check back in a moment for results.",
            "data": {
                "estimated_time": "5 seconds", 
                "request_id": request_id
            },
            "name": "librarian",
            "request_id": request_id
        }
        
        # Store initial pending response
        logger.debug(f"[{current_time.isoformat()}] Storing initial pending response for request_id={request_id}")
        PENDING_TOOL_REQUESTS[request_id] = response
        
        logger.debug(f"[{current_time.isoformat()}] Returning initial response for request_id={request_id}: {json.dumps(response)}")
        return response
        
    except Exception as e:
        error_msg = f"Error initializing librarian tool: {str(e)}"
        logger.error(f"[{current_time.isoformat()}] {error_msg}")
        error_response = {
            "status": "error",
            "message": error_msg,
            "request_id": request_id,
            "name": "librarian"
        }
        PENDING_TOOL_REQUESTS[request_id] = error_response
        return error_response 