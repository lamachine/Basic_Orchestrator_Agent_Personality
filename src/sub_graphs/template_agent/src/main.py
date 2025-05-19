"""
Main entry point for the template agent system.

This module initializes core components and starts the interface.
It demonstrates the distinction between managers and services by:
1. Using services for utility functions (database, logging)
2. Using managers for state and coordination (session, state)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .common.agents.template_agent import TemplateAgent
from .common.config import DBServiceConfig, LoggingServiceConfig, ServiceConfig, StateServiceConfig
from .common.managers.memory_manager import Mem0Memory
from .common.managers.session_manager import SessionManager
from .common.services.db_service import DBService
from .common.services.session_service import SessionService
from .common.state.state_models import MessageState
from .common.ui.adapters.api.app import APIInterface
from .common.ui.adapters.cli.interface import CLIInterface
from .common.utils.logging_utils import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)


def load_db_config() -> DBServiceConfig:
    """
    Load database configuration from environment or default values.

    Returns:
        DBServiceConfig instance
    """
    # Try to get values from environment variables
    connection_string = os.environ.get(
        "DB_CONNECTION_STRING", "postgresql://postgres:postgres@localhost:5432/agent_db"
    )
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")

    logger.info(f"Creating DB config with connection: {connection_string}")

    # Create config with default values
    config = DBServiceConfig(
        service_name="db_service",
        enabled=True,
        provider="postgresql",
        connection_params={
            "connection_string": connection_string,
            "supabase_url": supabase_url,
            "supabase_key": supabase_key,
        },
    )
    return config


def find_personality_file(personality_file: Optional[str] = None) -> Optional[str]:
    """
    Find the personality file to use.

    Args:
        personality_file: Optional path to personality file

    Returns:
        Path to personality file or None if not found
    """
    try:
        # Use provided file if specified
        if personality_file:
            file_path = Path(personality_file)
            if not file_path.exists():
                logger.error(f"Personality file not found: {file_path}")
                return None
            logger.debug(f"Using provided personality file: {file_path}")
            return str(file_path)

        # Use default from config
        default_path = Path(
            "src/sub_graphs/template_agent/src/specialty/personalities/default.json"
        )
        if default_path.exists():
            logger.debug(f"Using default personality file: {default_path}")
            return str(default_path)

        logger.warning("No personality file found")
        return None

    except Exception as e:
        logger.error(f"Error finding personality file: {e}", exc_info=True)
        return None


def initialize_agent(personality_file: Optional[str] = None) -> TemplateAgent:
    """
    Initialize the template agent.

    Args:
        personality_file: Optional path to personality file

    Returns:
        TemplateAgent instance

    Raises:
        RuntimeError: If agent initialization fails
    """
    try:
        # Initialize memory manager
        memory_manager = Mem0Memory()

        # Initialize template agent
        agent = TemplateAgent(memory_manager=memory_manager)
        return agent
    except Exception as e:
        error_msg = f"Failed to initialize agent: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


async def run_with_interface(
    interface_type: str = "cli",
    session_id: Optional[str] = None,
    personality_file: Optional[str] = None,
) -> int:
    """
    Run the template agent with the specified interface.

    Args:
        interface_type: Type of interface to use (cli, api)
        session_id: Optional session ID to continue
        personality_file: Optional path to personality file

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Initialize core components
        personality_path = find_personality_file(personality_file)
        agent = initialize_agent(personality_path)

        # Initialize database and session services
        db_config = load_db_config()
        db_service = DBService(config=db_config)
        session_service = SessionService(db_service)
        session_manager = SessionManager(session_service)
        logger.debug("Initialized database and session services")

        # Initialize agent's graph state
        if not hasattr(agent, "graph_state") or agent.graph_state is None:
            agent.graph_state = {}

        # Create session if not provided
        if not session_id:
            session_id = await session_service.create_session(user_id="developer")
            logger.debug(f"Created new session with ID: {session_id}")

        # Initialize MessageState with db_manager and connect to agent's graph state
        message_state = MessageState(session_id=int(session_id), db_manager=db_service)
        agent.graph_state["conversation_state"] = message_state
        logger.debug("Initialized conversation state in agent's graph state")

        # Initialize interface
        if interface_type == "api":
            interface = APIInterface(agent, session_manager)
        else:
            interface = CLIInterface(agent, session_manager)

        # Start the interface
        await interface.start()
        return 0

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        return 1


def main() -> int:
    """Parse command line arguments and run the application."""
    parser = argparse.ArgumentParser(description="Run the template agent system")
    parser.add_argument(
        "--interface",
        "-i",
        choices=["cli", "api"],
        default="cli",
        help="Interface type to use",
    )
    parser.add_argument("--session", "-s", help="Session ID to continue an existing conversation")
    parser.add_argument("--personality", "-p", help="Path to personality file")

    args = parser.parse_args()
    return asyncio.run(
        run_with_interface(
            interface_type=args.interface,
            session_id=args.session,
            personality_file=args.personality,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
