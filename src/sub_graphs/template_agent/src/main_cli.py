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
import importlib
import logging

# Configure basic logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
basic_logger = logging.getLogger(__name__)

# Configure paths
current_dir = os.path.dirname(os.path.abspath(__file__))
template_agent_dir = os.path.dirname(current_dir)
sys.path.insert(0, template_agent_dir)
sys.path.insert(0, os.path.dirname(template_agent_dir))  # Add parent of template_agent to path

basic_logger.info(f"Python path: {sys.path}")
basic_logger.info(f"Current directory: {os.getcwd()}")
basic_logger.info(f"Script directory: {current_dir}")

# Define the modules we need
modules_to_import = {
    "logging_service": "common.services.logging_service",
    "cli_interface": "common.ui.adapters.cli.interface",
    "template_agent": "specialty.agents.template_agent",
    "session_manager": "common.managers.session_manager",
    "session_service": "common.services.session_service",
    "db_service": "common.services.db_service",
    "state_models": "common.state.state_models",
    "memory_manager": "common.managers.memory_manager",
    "service_models": "common.models.service_models"
}

# Dynamic import of the modules
imported_modules = {}
import_method = None

# Try different import strategies
try:
    # First try using importlib directly
    for name, module_path in modules_to_import.items():
        try:
            imported_modules[name] = importlib.import_module(module_path)
            basic_logger.info(f"Successfully imported {module_path} as {name}")
        except ImportError as e:
            basic_logger.warning(f"Could not import {module_path}: {e}")
            raise ImportError(f"Failed to import {module_path}")

    import_method = "importlib"
except ImportError:
    try:
        # Try relative imports
        modules_to_import_relative = {
            "logging_service": ".common.services.logging_service",
            "cli_interface": ".common.ui.adapters.cli.interface",
            "template_agent": ".specialty.agents.template_agent",
            "session_manager": ".common.managers.session_manager",
            "session_service": ".common.services.session_service",
            "db_service": ".common.services.db_service",
            "state_models": ".common.state.state_models",
            "memory_manager": ".common.managers.memory_manager",
            "service_models": ".common.models.service_models"
        }

        package = __package__ or "src.sub_graphs.template_agent.src"
        for name, module_path in modules_to_import_relative.items():
            try:
                imported_modules[name] = importlib.import_module(module_path, package=package)
                basic_logger.info(f"Successfully imported {module_path} as {name}")
            except ImportError as e:
                basic_logger.warning(f"Could not import {module_path}: {e}")
                raise ImportError(f"Failed to import {module_path}")
                
        import_method = "relative importlib"
    except ImportError:
        try:
            # Finally try absolute imports from project root
            modules_to_import_absolute = {
                "logging_service": "src.sub_graphs.template_agent.src.common.services.logging_service",
                "cli_interface": "src.sub_graphs.template_agent.src.common.ui.adapters.cli.interface",
                "template_agent": "src.sub_graphs.template_agent.src.specialty.agents.template_agent",
                "session_manager": "src.sub_graphs.template_agent.src.common.managers.session_manager",
                "session_service": "src.sub_graphs.template_agent.src.common.services.session_service",
                "db_service": "src.sub_graphs.template_agent.src.common.services.db_service",
                "state_models": "src.sub_graphs.template_agent.src.common.state.state_models",
                "memory_manager": "src.sub_graphs.template_agent.src.common.managers.memory_manager",
                "service_models": "src.sub_graphs.template_agent.src.common.models.service_models"
            }

            for name, module_path in modules_to_import_absolute.items():
                try:
                    imported_modules[name] = importlib.import_module(module_path)
                    basic_logger.info(f"Successfully imported {module_path} as {name}")
                except ImportError as e:
                    basic_logger.warning(f"Could not import {module_path}: {e}")
                    raise ImportError(f"Failed to import {module_path}")
                    
            import_method = "absolute importlib"
        except ImportError:
            basic_logger.error("All import strategies failed")
            raise ImportError("Could not import required modules")

# Extract the needed components from imported modules
get_logger = imported_modules["logging_service"].get_logger
setup_logging = imported_modules["logging_service"].setup_logging
CLIInterface = imported_modules["cli_interface"].CLIInterface
TemplateAgent = imported_modules["template_agent"].TemplateAgent
SessionManager = imported_modules["session_manager"].SessionManager
SessionService = imported_modules["session_service"].SessionService
DBService = imported_modules["db_service"].DBService
MessageState = imported_modules["state_models"].MessageState
Mem0Memory = imported_modules["memory_manager"].Mem0Memory
DBServiceConfig = imported_modules["service_models"].DBServiceConfig
ServiceConfig = imported_modules["service_models"].ServiceConfig

# Setup logging
setup_logging()
logger = get_logger(__name__)
logger.info(f"Successfully imported modules using {import_method} imports")

def load_db_config():
    """
    Load database configuration from environment or default values.
    
    Returns:
        DBServiceConfig instance from dynamically imported module
    """
    # Try to get values from environment variables
    connection_string = os.environ.get("DB_CONNECTION_STRING", "postgresql://postgres:postgres@localhost:5432/agent_db")
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    
    logger.info(f"Creating DB config with connection: {connection_string}")
    if supabase_url:
        logger.info(f"Supabase URL: {supabase_url[:10]}... (truncated)")
    else:
        logger.info("No Supabase URL configured")
    
    # Create config with default values using the dynamically imported class
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

def check_environment():
    """
    Verify that all required components were properly imported.
    Raises an informative exception if any component is missing.
    """
    required_components = [
        ("get_logger", "logging service"),
        ("setup_logging", "logging service"),
        ("CLIInterface", "CLI interface"),
        ("TemplateAgent", "template agent"),
        ("SessionManager", "session manager"),
        ("SessionService", "session service"),
        ("DBService", "database service"),
        ("MessageState", "message state"),
        ("Mem0Memory", "memory manager"),
        ("DBServiceConfig", "database configuration"),
        ("ServiceConfig", "service configuration")
    ]
    
    missing = []
    for component, description in required_components:
        if not globals().get(component):
            missing.append(f"{component} ({description})")
    
    if missing:
        raise ImportError(f"Missing required components: {', '.join(missing)}")
    
    basic_logger.info("Environment check passed - all components are available")

async def run_with_cli_interface(session_id: Optional[str] = None) -> int:
    """
    Run the template agent with the CLI interface.
    
    Args:
        session_id: Optional session ID to continue
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Verify all required components are available
        check_environment()
        
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
    """
    Main entry point for running the CLI interface.
    Parse command line arguments and run the application.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(description="Run the template agent with CLI interface")
    parser.add_argument(
        "--session", "-s",
        help="Session ID to continue an existing conversation"
    )
    
    args = parser.parse_args()
    return asyncio.run(run_with_cli_interface(
        session_id=args.session
    ))

# Only run the application if this script is executed directly
if __name__ == "__main__":
    sys.exit(main()) 