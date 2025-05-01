"""Personal assistant tool implementation.

This tool handles communications, task lists, calendar, and personal productivity.
It routes requests to the personal assistant sub-graph for processing.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from src.state.state_models import MessageRole
from src.services.logging_service import get_logger

# Setup logger
logger = get_logger(__name__)

class PersonalAssistantTool:
    """
    Personal assistant tool handling all communications, task lists, calendar, and personal productivity.
    This tool acts as the single entry point for all personal assistant sub-graph capabilities.
    """
    name = "personal_assistant"
    description = (
        "Handles communications, task lists, calendar, and personal productivity. "
        "Includes Gmail integration. Acts as the single entry point for all personal assistant sub-graph capabilities."
    )

    async def execute(self, args: Dict[str, Any], request_id: Optional[str] = None, session_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a personal assistant task by routing to the personal assistant sub-graph.
        
        Args:
            args: Task arguments including the task description
            request_id: Optional request ID for tracking
            session_state: Optional session state for tracking
            
        Returns:
            Dict with the response from the personal assistant graph
        """
        try:
            task = args.get("task")
            if not task:
                raise ValueError("Task argument is required")
                
            # Log the request
            if session_state and "conversation_state" in session_state:
                await session_state["conversation_state"].add_message(
                    role=MessageRole.TOOL,
                    content=f"Personal assistant request: {task}",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "request_id": request_id,
                        "task": task,
                        "args": args
                    },
                    sender="orchestrator_graph.personal_assistant",
                    target="personal_assistant_graph.system"
                )
                
            # Import the personal assistant graph here to avoid circular imports
            from src.sub_graphs.personal_assistant_agent.graphs.personal_assistant_graph import personal_assistant_graph
            
            # Create the request for the personal assistant graph
            request = {
                "task": task,
                "args": args,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Execute in the personal assistant graph
            result = await personal_assistant_graph(session_state, request)
            
            # Log the result
            if session_state and "conversation_state" in session_state:
                await session_state["conversation_state"].add_message(
                    role=MessageRole.TOOL,
                    content=f"Personal assistant result: {result}",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "request_id": request_id,
                        "result": result
                    },
                    sender="personal_assistant_graph.system",
                    target="orchestrator_graph.personal_assistant"
                )
                
            return {
                "status": "success",
                "message": result.get("message", "Task completed successfully"),
                "data": result
            }
            
        except Exception as e:
            error_msg = f"Error in personal assistant tool: {str(e)}"
            logger.error(error_msg)
            
            # Log the error
            if session_state and "conversation_state" in session_state:
                await session_state["conversation_state"].add_message(
                    role=MessageRole.TOOL,
                    content=error_msg,
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "request_id": request_id,
                        "error": str(e)
                    },
                    sender="personal_assistant_graph.system",
                    target="orchestrator_graph.personal_assistant"
                )
                
            return {
                "status": "error",
                "message": error_msg
            }
            
    @classmethod
    def get_tool_metadata(cls) -> Dict[str, Any]:
        """
        Returns all metadata needed for orchestrator tool registration and discovery.

        Returns:
            Dict[str, Any]: Tool metadata including name, description, and example usage.
        """
        return {
            "name": cls.name,
            "description": cls.description,
            "examples": [
                {
                    "task": "Send email to john@example.com with subject 'Meeting' and body 'Let's meet tomorrow.'"
                },
                {
                    "task": "Search email for 'project updates' from last week"
                },
                {
                    "task": "List my calendar events for the next 3 days"
                },
                {
                    "task": "Add a task to call the dentist tomorrow at 10am"
                }
            ]
        } 