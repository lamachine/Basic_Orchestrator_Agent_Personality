"""
Main entry point for the orchestrator system.

This module provides functions to initialize the agent and
start the appropriate interface based on configuration settings.
"""

import sys
import logging

# Setup logging first thing
from src.config.logging_config import setup_logging
setup_logging()

# Get logger
from src.services.logging_services.logging_service import get_logger
logger = get_logger(__name__)

# Import configuration
from src.config import Configuration

def run_with_interface(interface_type="cli", session_id=None):
    """
    Run the orchestrator with the specified interface.
    
    Args:
        interface_type: The type of interface to use (cli, api, web, graph)
        session_id: Optional session ID to continue an existing conversation
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Load configuration
        config = Configuration()
        
        # Initialize the orchestrator agent
        logger.debug("Initializing orchestrator agent...")
        from src.agents.orchestrator_agent import OrchestratorAgent
        agent = OrchestratorAgent(config)
        
        # Initialize the appropriate interface
        logger.debug(f"Starting {interface_type} interface...")
        
        if interface_type == "cli":
            from src.ui.cli import CLIInterface
            interface = CLIInterface(agent)
        # These should be commented out until implemented
        # elif interface_type == "api":
        #     from src.ui.api_server import APIInterface
        #     interface = APIInterface(agent)
        # elif interface_type == "web":
        #     from src.ui.web import WebInterface
        #     interface = WebInterface(agent)
        # elif interface_type == "graph":
        #     from src.ui.graph_adapter import GraphInterface
        #     interface = GraphInterface(agent)
        else:
            # Fallback to CLI
            logger.warning(f"Interface '{interface_type}' not recognized, falling back to CLI")
            from src.ui.cli import CLIInterface
            interface = CLIInterface(agent)
        
        # If a session ID was provided, continue that session
        if session_id:
            # Get conversation directly from database
            conversation = agent.db.continue_conversation(session_id, agent.user_id)
            if conversation:
                # Set agent's conversation ID directly
                agent.conversation_id = session_id
                agent.session_id = session_id  # Alias for compatibility
                
                # Update state manager if available
                if hasattr(agent, 'state_manager') and agent.state_manager:
                    try:
                        # Get messages for this conversation from the database
                        messages = agent.db.message_manager.get_messages_by_session(
                            session_id, format_type="standard"
                        )
                        for msg in messages:
                            role = msg.get('role')
                            content = msg.get('content')
                            agent.state_manager.update_conversation(role, content)
                    except Exception as e:
                        logger.warning(f"Could not load messages for conversation {session_id}: {e}")
                
                logger.debug(f"Continued session {session_id}")
            else:
                logger.error(f"Failed to continue session {session_id}")
                return 1
        
        # Start the interface
        interface.start()
        
        return 0
    except ImportError as e:
        logger.error(f"Failed to import module: {e}")
        print(f"Error: The selected interface is not available. {e}")
        return 1
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1

def main():
    """
    Legacy main entry point that uses command-line arguments.
    Kept for backward compatibility.
    """
    logger.warning("Using legacy main() with command-line arguments. Consider using run_with_interface() instead.")
    
    # Initialize with default settings
    return run_with_interface()

if __name__ == "__main__":
    sys.exit(main()) 