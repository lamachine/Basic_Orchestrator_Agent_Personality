"""
Main CLI interface for the template agent.

This module initializes the template agent with CLI interface
for standalone operation without requiring the orchestrator.
"""

import sys
import os
import argparse
import asyncio
from typing import Optional, Dict, Any
import json

from .common.services.logging_service import get_logger, setup_logging
from .common.ui.adapters.cli.interface import CLIInterface
from .specialty.agents.template_agent import TemplateAgent
from .common.managers.session_manager import SessionManager
from .common.services.session_service import SessionService
from .common.services.db_service import DBService
from .common.state.state_models import MessageState
from .common.managers.memory_manager import Mem0Memory
from .common.models.service_models import DBServiceConfig, ServiceConfig

logger = get_logger(__name__)

def load_db_config() -> DBServiceConfig:
    """
    Load database configuration from environment or default values.
    
    Returns:
        DBServiceConfig instance
    """
    # Try to get values from environment variables
    connection_string = os.environ.get("DB_CONNECTION_STRING", "postgresql://postgres:postgres@localhost:5432/agent_db")
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    
    # Create config with default values
    config = DBServiceConfig(
        name="db_service",
        enabled=True,
        connection_string=connection_string,
        config={
            "supabase_url": supabase_url,
            "supabase_key": supabase_key
        }
    )
    
    return config

async def run_with_cli_interface(session_id: Optional[str] = None) -> int:
    """
    Run the template agent with the CLI interface.
    
    Args:
        session_id: Optional session ID to continue
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        logger.info("Initializing template agent with CLI interface")
        
        # Initialize database and session services
        db_config = load_db_config()
        try:
            db_service = DBService(config=db_config)
            session_service = SessionService(db_service)
            session_manager = SessionManager(session_service)
            logger.info("Database services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database services: {e}")
            logger.warning("Running without database support")
            db_service = None
            session_service = None
            session_manager = None
        
        # Initialize memory manager with Mem0
        try:
            mem0_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))), "mem0.config.json")
            memory_manager = Mem0Memory(config_path=mem0_config_path)
            logger.info(f"Initialized memory manager with config: {mem0_config_path}")
        except Exception as e:
            logger.warning(f"Failed to initialize Mem0Memory, running without memory: {e}")
            memory_manager = None
        
        # Initialize template agent
        agent = TemplateAgent(memory_manager=memory_manager)
        
        # Initialize graph state and conversation state
        agent.graph_state = {}
        
        # Create session if not provided and if session service is available
        if session_service:
            if not session_id:
                session_id = await session_service.create_session(user_id="developer")
                logger.info(f"Created new session with ID: {session_id}")
            else:
                logger.info(f"Using provided session ID: {session_id}")
            
            # Initialize message state
            message_state = MessageState(
                session_id=int(session_id),
                db_manager=db_service
            )
            agent.graph_state['conversation_state'] = message_state
        
        # Initialize CLI interface
        interface = CLIInterface(agent, session_manager)
        
        # Start the interface (this will block until the user exits)
        logger.info("Starting CLI interface")
        await interface.start()
        
        logger.info("CLI interface stopped")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error running template agent: {e}", exc_info=True)
        return 1

def main() -> int:
    """Parse command line arguments and run the application."""
    parser = argparse.ArgumentParser(description="Run the template agent with CLI interface")
    parser.add_argument(
        "--session", "-s",
        help="Session ID to continue an existing conversation"
    )
    
    args = parser.parse_args()
    return asyncio.run(run_with_cli_interface(
        session_id=args.session
    ))

if __name__ == "__main__":
    sys.exit(main()) 