"""Personal Assistant Agent implementation.

This module contains the core logic for the Personal Assistant agent.
It handles the business logic for processing requests and delegates to tools.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

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
            from src.sub_graphs.personal_assistant_agent.src.tools.personal_assistant_tool import PersonalAssistantTool
            self.email_tool = PersonalAssistantTool(config=self.config)
            logger.info("Successfully initialized Personal Assistant agent with tools")
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
                "data": None
            }
        
        # Process the request and determine which tool to use
        task = args.get("task", "")
        if not task:
            return {
                "status": "error",
                "message": "No task specified",
                "data": None
            }
        
        logger.info(f"Personal Assistant agent processing task: {task}")
        
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
                "data": None
            } 

def handle_personal_assistant_task(task: str, parameters: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Handles a personal assistant task, propagating request_id and logging.

    Args:
        task (str): The task description or command for the personal assistant.
        parameters (Optional[Dict[str, Any]]): Optional parameters for the task.
        request_id (Optional[str]): Unique request identifier for tracking.

    Returns:
        Dict[str, Any]: Standardized response from the agent, always includes request_id and timestamp.
    """
    logger.info(f"handle_personal_assistant_task received task: {task} (request_id={request_id})")
    logger.debug(f"handle_personal_assistant_task parameters: {parameters} (request_id={request_id})")
    try:
        agent = PersonalAssistantAgent()
        args = parameters or {}
        args["task"] = task
        args["request_id"] = request_id
        # If agent.execute is async, run it in an event loop
        import asyncio
        if asyncio.iscoroutinefunction(agent.execute):
            response = asyncio.run(agent.execute(args))
        else:
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
            "timestamp": datetime.utcnow().isoformat()
        } 