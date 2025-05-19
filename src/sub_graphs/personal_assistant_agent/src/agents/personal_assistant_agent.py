"""Personal Assistant Agent implementation.

This module contains the core logic for the Personal Assistant agent.
It handles the business logic for processing requests and delegates to tools.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

# Set up logger
logger = logging.getLogger(__name__)


class PersonalAssistantAgent:
    """
    Core Personal Assistant agent implementation.

    This class contains the business logic for the Personal Assistant
    and delegates to specific tools for different capabilities.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Personal Assistant agent.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.name = "personal_assistant"

        # Import tool implementations
        try:
            from src.sub_graphs.personal_assistant_agent.src.tools.personal_assistant_tool import (
                PersonalAssistantTool,
            )

            self.email_tool = PersonalAssistantTool(config=self.config)
            logger.debug("Successfully initialized Personal Assistant agent with tools")
        except ImportError as e:
            logger.error(f"Failed to import Personal Assistant tools: {e}")
            self.email_tool = None
        except Exception as e:
            logger.error(f"Error initializing Personal Assistant tools: {e}")
            self.email_tool = None

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a request with the Personal Assistant agent.

        This method contains the core business logic to process the request,
        analyze the task, and delegate to the appropriate tools.

        Args:
            args: Dictionary of arguments for the request

        Returns:
            Dictionary with response data
        """
        if not self.email_tool:
            return {
                "status": "error",
                "message": "Personal Assistant tools not properly initialized",
                "data": None,
            }

        # Process the request and determine which tool to use
        task = args.get("task", "")
        if not task:
            return {"status": "error", "message": "No task specified", "data": None}

        logger.debug(f"Personal Assistant agent processing task: {task}")

        # For now, delegate all tasks to the general tool
        # In a real implementation, we would have logic to route to different tools
        try:
            result = await self.email_tool.execute(args)
            return result
        except Exception as e:
            logger.error(f"Error in Personal Assistant agent: {e}")
            return {
                "status": "error",
                "message": f"Error processing task: {str(e)}",
                "data": None,
            }


def handle_personal_assistant_task(
    task: str,
    parameters: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handles a personal assistant task, propagating request_id and logging.

    Args:
        task (str): The task description or command for the personal assistant.
        parameters (Optional[Dict[str, Any]]): Optional parameters for the task.
        request_id (Optional[str]): Unique request identifier for tracking.

    Returns:
        Dict[str, Any]: Standardized response from the agent, always includes request_id and timestamp.
    """
    logger.info(f"Personal assistant processing task: {task} (request_id={request_id})")
    logger.debug(f"Task parameters: {parameters}")
    try:
        agent = PersonalAssistantAgent()
        args = parameters or {}
        args["task"] = task
        args["request_id"] = request_id

        # Handle sync vs async execution
        import asyncio

        if asyncio.iscoroutinefunction(agent.execute):
            # We're in a function that's being called from an async context
            # Return a "processing" response and start the execution as a background task
            # This is much safer than trying to use run_until_complete in an existing event loop
            asyncio.create_task(
                _execute_personal_assistant_and_update_result(agent, args, request_id)
            )

            # Return an immediate processing response
            return {
                "status": "processing",
                "message": f"Processing personal assistant task: {task}",
                "data": None,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            # Sync execution
            response = agent.execute(args)
            response["request_id"] = request_id
            response["timestamp"] = response.get("timestamp", datetime.utcnow().isoformat())
            return response

    except Exception as e:
        logger.error(f"Error in handle_personal_assistant_task (request_id={request_id}): {e}")
        return {
            "status": "error",
            "message": f"Error in handle_personal_assistant_task: {str(e)}",
            "data": None,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }


async def _execute_personal_assistant_and_update_result(agent, args, request_id):
    """Execute the personal assistant task in the background and update the result."""
    try:
        from src.tools.orchestrator_tools import PENDING_TOOL_REQUESTS

        # Execute the task
        response = await agent.execute(args)

        # Make sure the response has the required fields
        response["request_id"] = request_id
        response["timestamp"] = response.get("timestamp", datetime.utcnow().isoformat())

        # Update the pending requests with the result
        if request_id in PENDING_TOOL_REQUESTS:
            PENDING_TOOL_REQUESTS[request_id] = response
            logger.debug(f"Updated pending tool request with result: {request_id}")
    except Exception as e:
        logger.error(f"Error in background personal assistant task (request_id={request_id}): {e}")

        # Update with error response
        error_response = {
            "status": "error",
            "message": f"Error in background personal assistant task: {str(e)}",
            "data": None,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if request_id in PENDING_TOOL_REQUESTS:
            PENDING_TOOL_REQUESTS[request_id] = error_response
