"""Script to run the template agent directly.

This script demonstrates how to:
1. Initialize and run a sub-graph agent
2. Set up proper logging
3. Create and manage state
4. Process requests through the graph
5. Handle responses and errors

To use this template:
1. Copy this file to your agent's directory
2. Rename it to run_<your_agent>.py
3. Update the imports to use your graph
4. Modify the example request to match your agent's capabilities
5. Add any agent-specific initialization or cleanup
"""

import asyncio
import json
import logging
from typing import Dict, Any
from datetime import datetime

# Update these imports to match your agent's structure
from graphs.template_graph import template_graph
from state.state_models import GraphState
from services.logging_service import get_logger, setup_logging

# Set up logging with debug level for both file and console
setup_logging({
    'file_level': 'DEBUG',
    'console_level': 'DEBUG',
})

logger = get_logger(__name__)

async def initialize_state() -> GraphState:
    """
    Initialize the graph state with default values.
    
    Returns:
        GraphState: Initialized state object
    """
    return GraphState(
        messages=[],
        conversation_state={},
        agent_states={},
        current_task=None,
        task_history=[],
        agent_results={},
        final_result=None
    )

async def create_example_request() -> Dict[str, Any]:
    """
    Create an example request for testing.
    
    Returns:
        Dict[str, Any]: Example request parameters
    """
    # Example parameters - modify these for your agent
    example_params = {
        "action": "example_action",
        "parameter1": "value1",
        "parameter2": "value2",
        "timestamp": datetime.utcnow().isoformat()
    }

    return {
        "task": json.dumps(example_params)
    }

async def process_result(result: Dict[str, Any]) -> None:
    """
    Process and log the result from the graph.
    
    Args:
        result: The result dictionary from the graph
    """
    if result.get("success"):
        logger.debug("Request processed successfully")
        logger.debug(f"Result: {result}")
    else:
        logger.error(f"Failed to process request: {result.get('error')}")

async def main():
    """Run the template agent with example request."""
    try:
        # Initialize state
        state = await initialize_state()
        
        # Create example request
        request = await create_example_request()
        
        logger.debug(f"Processing request with parameters: {request}")

        # Process request through graph
        result = await template_graph(state, request)
        
        # Process and log result
        await process_result(result)
        
        return result

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    asyncio.run(main()) 