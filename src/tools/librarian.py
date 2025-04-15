"""Librarian tool implementation."""

from typing import Dict, Any, Optional
import logging
import time
import json
import sys
import threading

# Setup logger
logger = logging.getLogger(__name__)

# Track pending requests
PENDING_LIBRARIAN_REQUESTS = {}

def _process_librarian_task(task: str, request_id: int):
    """Process a librarian task asynchronously."""
    print(f"*** LIBRARIAN TOOL PROCESSING: Waiting 10 seconds for request_id={request_id} ***", file=sys.stderr)
    time.sleep(10)
    
    # Mock response after processing
    response = {
        "status": "success",
        "message": "Web search and documentation crawl for 'Pydantic agents' complete. 24 sources analyzed and 15 documents processed. Would you like to review the summary or email it to yourself?",
        "data": {
            "sources": 24,
            "documents": 15,
            "topics": ["Pydantic", "Agents", "FastAPI integration", "Type validation"],
            "actions": ["review summary", "email summary", "download sources"]
        },
        "request_id": request_id
    }
    
    # Store completed response
    PENDING_LIBRARIAN_REQUESTS[request_id] = response
    
    # Log and print completion
    logger.debug(f"librarian_tool async task completed with response: {json.dumps(response, indent=2)}")
    print(f"*** LIBRARIAN TOOL COMPLETED: response={response['message']} ***", file=sys.stderr)

def librarian_tool(task: Optional[str] = None, request_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Librarian tool for research, documentation, and knowledge management.
    
    Args:
        task: Optional task description or query
        request_id: Optional request ID for tracking
        
    Returns:
        Dict with status and response message indicating the request is processing
    """
    # Print directly to console to bypass logging
    print(f"*** LIBRARIAN TOOL CALLED: task={task}, request_id={request_id} ***", file=sys.stderr)

    # Log incoming request with full content
    logger.debug(f"librarian_tool received task: {task}, request_id: {request_id}")
    
    # Start a background thread to process the request
    task_thread = threading.Thread(
        target=_process_librarian_task,
        args=(task, request_id)
    )
    task_thread.daemon = True  # Thread will exit when main program exits
    task_thread.start()
    
    # Return immediate acknowledgment
    return {
        "status": "pending",
        "message": f"I'll research information about '{task}' for you. Please check back in a moment for results.",
        "data": {
            "estimated_time": "10 seconds",
            "request_id": request_id
        },
        "request_id": request_id
    } 