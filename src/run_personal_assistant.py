"""Script to run the personal assistant directly."""

import asyncio
import json
import logging
from src.sub_graph_personal_assistant.graphs.personal_assistant_graph import personal_assistant_graph
from src.state.state_models import GraphState
from src.services.logging_service import get_logger, setup_logging

# Set up logging with debug level for both file and console
setup_logging({
    'log_level': 'DEBUG',
    'console_log_level': 'DEBUG',
    'file_log_level': 'DEBUG'
})

logger = get_logger(__name__)

async def main():
    """Run the personal assistant."""
    try:
        # Create initial state
        state = GraphState(
            messages=[],
            conversation_state={},
            agent_states={},
            current_task=None,
            task_history=[],
            agent_results={},
            final_result=None
        )

        # Create email parameters
        email_params = {
            "action": "send",
            "to": "test@example.com",
            "subject": "Test Email",
            "body": "This is a test email from the personal assistant."
        }

        # Create request in the format expected by personal_assistant_graph
        request = {
            "task": json.dumps(email_params)
        }
        
        logger.debug(f"Processing email request with parameters: {request}")

        # Process request through personal assistant graph
        result = await personal_assistant_graph(state, request)
        
        if result.get("success"):
            logger.debug("Email request processed successfully")
            logger.debug(f"Result: {result}")
        else:
            logger.error(f"Failed to process email request: {result.get('error')}")
            
        return result

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    asyncio.run(main()) 