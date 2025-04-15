"""Valet tool implementation."""

from typing import Dict, Any, Optional
import logging
import asyncio

from src.graphs.valet_graph import ValetGraph

# Setup logger
logger = logging.getLogger(__name__)

# Global graph instance
_valet_graph = None

def get_valet_graph() -> ValetGraph:
    """Get or create the valet graph instance."""
    global _valet_graph
    if _valet_graph is None:
        _valet_graph = ValetGraph()
    return _valet_graph

async def _process_valet_request(task: str) -> Dict[str, Any]:
    """Process a request through the valet graph.
    
    Args:
        task: The task or query for the valet
        
    Returns:
        Dict with the response
    """
    graph = get_valet_graph()
    
    # Start graph if not running
    if graph.status != "running":
        await graph.start()
        
    # Process the message
    return await graph.process_message(task)

def valet_tool(task: Optional[str] = None) -> Dict[str, Any]:
    """
    Tool for managing household staff, daily schedule, and personal affairs.
    
    Args:
        task: Optional task or query for the valet
        
    Returns:
        Dict with the response
    """
    if task is None:
        task = "Hello"  # Default greeting
        
    try:
        # Run async function in sync context
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(_process_valet_request(task))
        return response
    except Exception as e:
        logger.error(f"Error in valet tool: {e}")
        return {
            "status": "error",
            "message": f"Error processing valet request: {str(e)}"
        } 