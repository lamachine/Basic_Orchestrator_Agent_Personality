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
from src.ui.cli.interface import CLIInterface
from src.managers.session_manager import SessionManager
from src.services.session_service import SessionService
from src.managers.db_manager import DBService
from src.services.message_service import DatabaseMessageService, log_and_persist_message
from src.services.logging_service import get_logger
from src.state.state_models import MessageState
from src.tools.initialize_tools import initialize_tools, get_registry

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
                logger.error(f"Personality file not found: {file_path} (absolute: {file_path.absolute()})")
                return None
            logger.debug(f"Using explicitly provided personality file: {file_path} (exists: {file_path.exists()})")
            return str(file_path)
            
        # Use default from config
        if config.personality_file_path:
            file_path = Path(config.personality_file_path)
            # Check if file exists as specified
            if file_path.exists():
                logger.debug(f"Using default personality file from config: {file_path}")
                return str(file_path)
            
            # Try with src/ prefix if not found directly
            if not file_path.is_absolute() and not str(file_path).startswith('src/'):
                alt_path = Path("src") / file_path
                if alt_path.exists():
                    logger.debug(f"Found personality file with src/ prefix: {alt_path}")
                    return str(alt_path)
                
            logger.error(f"Default personality file not found: {file_path} (absolute: {file_path.absolute()})")
            logger.error(f"Current working directory: {Path.cwd()}")
            return None
            
        logger.warning("No personality file specified in config")
        return None
        
    except Exception as e:
        logger.error(f"Error finding personality file: {e}", exc_info=True)
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
        # Initialize tools (this handles discovery and registration internally)
        await initialize_tools()
        
        # Get final state of registered tools
        registry = get_registry()
        available_tools = registry.list_tools()
        
        # Also initialize tool definitions for prompt generation
        from src.tools.orchestrator_tools import initialize_tool_definitions
        await initialize_tool_definitions()
        
        if available_tools:
            logger.debug(f"Available tools: {', '.join(available_tools)}")
        else:
            logger.debug("No tools were initialized")
        
        # Initialize core components
        personality_path = find_personality_file(config, personality_file)
        agent, llm_agent = initialize_agents(config, personality_path)
        
        # Initialize database and session services
        db_service = DBService()
        # Initialize message service and assign to db_service.message_manager
        db_message_service = DatabaseMessageService(db_service)
        db_service.message_manager = db_message_service
        logger.debug("Initialized database and message services")
        session_service = SessionService(db_service)
        session_manager = SessionManager(session_service)

        # Ensure agent's graph_state['conversation_state'] uses MessageState with db_manager
        if not hasattr(agent, 'graph_state') or agent.graph_state is None:
            agent.graph_state = {}
        
        # Create session and initialize conversation state
        session_id = await session_service.create_session(user_id="developer")
        logger.debug(f"Created new session with ID: {session_id}")
        
        # Initialize MessageState with db_manager and connect to agent's graph state
        message_state = MessageState(
            session_id=int(session_id),
            db_manager=db_service
        )
        agent.graph_state['conversation_state'] = message_state
        logger.debug("Initialized conversation state in agent's graph state")

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