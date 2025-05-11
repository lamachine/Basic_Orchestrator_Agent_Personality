"""
Main entry point for the orchestrator system.

This module initializes core components and starts the interface.
It demonstrates the distinction between managers and services by:
1. Using services for utility functions (database, logging)
2. Using managers for state and coordination (session, state)
"""

from src.config.logging_config import setup_logging
setup_logging()

from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from src.config import Configuration
from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.llm_query_agent import LLMQueryAgent
from src.agents.personality_agent import PersonalityAgent
from src.ui.cli import CLIInterface
from src.managers.session_manager import SessionManager
from src.services.session_service import SessionService
from src.managers.db_manager import DBService
from src.services.message_service import DatabaseMessageService
from src.services.logging_service import get_logger
from src.state.state_models import MessageState
from src.tools.initialize_tools import discover_and_initialize_tools, get_registry, initialize_tools

logger = get_logger(__name__)

def find_personality_file(config: Configuration, personality_file: Optional[str] = None) -> Optional[str]:
    """
    Find the personality file to use.
    
    Args:
        config: Configuration instance
        personality_file: Optional path to personality file
        
    Returns:
        Path to personality file or None if not found/enabled
    """
    try:
        # Check if personality is enabled
        if not config.personality_enabled:
            logger.debug("Personality system disabled in config")
            return None
            
        # Use provided file if specified
        if personality_file:
            file_path = Path(personality_file)
            if not file_path.exists():
                logger.error(f"Personality file not found: {file_path}")
                return None
            return str(file_path)
            
        # Use default from config
        if config.personality_file_path:
            file_path = Path(config.personality_file_path)
            if not file_path.exists():
                logger.error(f"Default personality file not found: {file_path}")
                return None
            return str(file_path)
            
        return None
        
    except Exception as e:
        logger.error(f"Error finding personality file: {e}")
        return None

def initialize_agents(config: Configuration, personality_file: Optional[str] = None) -> Tuple[OrchestratorAgent, LLMQueryAgent]:
    """
    Initialize the agent system.
    
    Args:
        config: Configuration instance
        personality_file: Optional path to personality file
        
    Returns:
        Tuple of (OrchestratorAgent, LLMQueryAgent)
        
    Raises:
        RuntimeError: If agent initialization fails
    """
    try:
        # Initialize LLM query agent first
        llm_agent = LLMQueryAgent(config, personality_file)
        # If personality_file is provided, wrap with PersonalityAgent
        if personality_file:
            llm_agent = PersonalityAgent(llm_agent, personality_file)
        # Initialize orchestrator agent with personality file if provided
        agent = OrchestratorAgent(config, personality_file=personality_file)
        return agent, llm_agent
    except Exception as e:
        error_msg = f"Failed to initialize agents: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

async def run_with_interface(interface_type: str = "cli", session_id: Optional[str] = None, 
                      personality_file: Optional[str] = None) -> int:
    """
    Run the orchestrator with the specified interface.
    
    Args:
        interface_type: Type of interface to use (cli, api, web, graph)
        session_id: Optional session ID to continue
        personality_file: Optional path to personality file
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        config = Configuration()
        # Logging is already set up at the top
        log_config = config.user_config.get_logging_config() if hasattr(config, 'user_config') else {}
        console_level = log_config.get('console_level', 'INFO')
        logger.debug(f"Logging initialized at {console_level} level (console)")
        
        # --- TOOL DISCOVERY AND INITIALIZATION ---
        discovered = await discover_and_initialize_tools(auto_approve=True)
        logger.debug(f"Newly approved tools this run: {discovered}")
        registry = get_registry()
        approved_and_loaded = registry.list_tools()
        logger.debug(f"All approved and loaded tools: {approved_and_loaded}")
        # Optionally, build/install tool nodes (if needed for your workflow)
        await initialize_tools()
        
        # Initialize core components
        personality_path = find_personality_file(config, personality_file)
        agent, llm_agent = initialize_agents(config, personality_path)
        
        # Initialize database and session services
        db_service = DBService()
        # Initialize message service and assign to db_service.message_manager
        message_service = DatabaseMessageService(db_service)
        db_service.message_manager = message_service
        logger.debug("Initialized database and message services")
        session_service = SessionService(db_service)
        session_manager = SessionManager(session_service)

        # Ensure agent's graph_state['conversation_state'] uses MessageState with db_manager
        if not hasattr(agent, 'graph_state') or agent.graph_state is None:
            agent.graph_state = {}
        session_id = await session_service.create_session(user_id="developer")
        agent.graph_state['conversation_state'] = MessageState(session_id=int(session_id), db_manager=db_service)

        # Initialize interface (only CLI supported for now)
        if interface_type != "cli":
            logger.warning(f"Interface '{interface_type}' not supported, using CLI")
        interface = CLIInterface(agent, session_manager)
        
        # Start the interface
        await interface.start()
        return 0
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        return 1

def main() -> int:
    """Parse command line arguments and run the application."""
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Run the orchestrator agent system")
    parser.add_argument(
        "--interface", "-i",
        choices=["cli"],  # Only CLI supported for now
        default="cli",
        help="Interface type to use"
    )
    parser.add_argument(
        "--session", "-s",
        help="Session ID to continue an existing conversation"
    )
    parser.add_argument(
        "--personality", "-p",
        help="Path to a personality JSON file"
    )
    
    args = parser.parse_args()
    return asyncio.run(run_with_interface(
        interface_type=args.interface,
        session_id=args.session,
        personality_file=args.personality
    ))

if __name__ == "__main__":
    import sys
    sys.exit(main()) 