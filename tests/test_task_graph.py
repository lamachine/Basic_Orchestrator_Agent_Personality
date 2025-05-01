"""Task agent graph implementation."""

from typing import Dict, Any, Optional
import logging

from .local_graph import LocalGraph

logger = logging.getLogger(__name__)

class TaskGraph(LocalGraph):
    """Task agent graph implementation."""
    
    def __init__(self, parent_graph_id: Optional[str] = None):
        """Initialize the task graph.
        
        Args:
            parent_graph_id: Optional ID of parent graph (usually orchestrator)
        """
        # Simple test prompt for now
        system_prompt = """You are a task assistant. You help manage and track tasks.
        
For testing purposes:
- If the user says "new task", respond with "Task created"
- Otherwise, be conversational and helpful about task management topics

Remember: This is just for testing the graph structure. The real prompt will be added later."""

        super().__init__(
            name="task",
            system_prompt=system_prompt,
            parent_graph_id=parent_graph_id
        )
        
    async def process_message(self, message: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a message through the task graph.
        
        Args:
            message: The message to process
            request_id: Optional request ID for tracking
            
        Returns:
            Dict with response information
        """
        # For now, just use the base implementation
        return await super().process_message(message, request_id) 