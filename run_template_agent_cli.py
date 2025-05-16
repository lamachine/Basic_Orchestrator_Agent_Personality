"""
Run the template agent with CLI interface.

This script provides a simple way to run the template agent
with the CLI interface from the project root.
"""

import os
import sys
import logging
import asyncio

# Configure basic logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the template agent directory to sys.path
template_agent_dir = os.path.join("src", "sub_graphs", "template_agent")
if os.path.exists(template_agent_dir):
    if template_agent_dir not in sys.path:
        sys.path.append(os.path.abspath(template_agent_dir))
    logger.info(f"Added {template_agent_dir} to sys.path")
else:
    logger.error(f"Template agent directory not found at {template_agent_dir}")
    sys.exit(1)

try:
    # Import template agent components using relative imports from its structure
    from src.specialty.agents.template_agent import TemplateAgent
    from src.common.ui.adapters.cli.interface import CLIInterface
    from src.common.managers.session_manager import SessionManager
    from src.common.services.session_service import SessionService
    from src.common.managers.memory_manager import Mem0Memory
    
    # Try to use project's logging configuration
    try:
        from src.config.logging_config import setup_logging
        file_handler, console_handler = setup_logging()
        logger.info("Using project logging configuration")
    except Exception as e:
        logger.warning(f"Could not use project logging config: {e}. Using basic logging.")

    async def run_template_agent():
        """Run the template agent with CLI interface."""
        try:
            # Initialize memory manager
            mem0_config_path = os.path.join("mem0.config.json")
            try:
                memory_manager = Mem0Memory(config_path=mem0_config_path)
                logger.info(f"Initialized memory manager with config: {mem0_config_path}")
            except Exception as e:
                logger.warning(f"Failed to initialize Mem0Memory, running without memory: {e}")
                memory_manager = None
            
            # Initialize template agent
            agent = TemplateAgent(memory_manager=memory_manager)
            
            # Initialize graph state
            agent.graph_state = {}
            
            # Initialize simple session manager (without database)
            session_manager = SessionManager(SessionService(None))
            
            # Initialize CLI interface
            interface = CLIInterface(agent, session_manager)
            
            # Start the interface
            logger.info("Starting template agent CLI interface")
            await interface.start()
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error running template agent: {e}", exc_info=True)
            return 1
        
        return 0

    if __name__ == "__main__":
        exit_code = asyncio.run(run_template_agent())
        sys.exit(exit_code)
        
except Exception as e:
    logger.error(f"Failed to initialize template agent: {e}", exc_info=True)
    sys.exit(1) 