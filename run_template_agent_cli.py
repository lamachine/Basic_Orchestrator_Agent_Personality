"""
Run the template agent with CLI interface.

This script provides a simple way to run the template agent
with the CLI interface from the project root.
"""

import os
import sys
import logging
import asyncio
import traceback
import importlib.util

# Configure basic logging first with more verbose output
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more verbose output
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Print Python version and path info for debugging
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")

# Add directories to sys.path
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
logger.info(f"Added {root_dir} to sys.path")

# Try to load the main_cli module
try:
    # Get the main_cli.py path
    main_cli_path = os.path.join(root_dir, "src", "sub_graphs", "template_agent", "src", "main_cli.py")
    if os.path.exists(main_cli_path):
        logger.info(f"Found main_cli.py at {main_cli_path}")
        
        # First check for null bytes
        try:
            with open(main_cli_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '\0' in content:
                    logger.error("Found null bytes in main_cli.py!")
                    cleaned_content = content.replace('\0', '')
                    # Write cleaned file
                    clean_path = main_cli_path + '.clean'
                    with open(clean_path, 'w', encoding='utf-8') as clean_f:
                        clean_f.write(cleaned_content)
                    logger.info(f"Wrote cleaned file to {clean_path}")
                    main_cli_path = clean_path
                else:
                    logger.info("No null bytes found in main_cli.py")
        except Exception as e:
            logger.error(f"Error checking for null bytes: {e}")
            logger.error(traceback.format_exc())
        
        # Import the module using spec
        try:
            logger.info("Importing main_cli.py using spec...")
            spec = importlib.util.spec_from_file_location("main_cli", main_cli_path)
            main_cli = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_cli)
            
            # Execute the main function
            logger.info("Executing main() function from main_cli.py...")
            exit_code = main_cli.main()
            sys.exit(exit_code)
        except Exception as e:
            logger.error(f"Error importing main_cli.py: {e}")
            logger.error(traceback.format_exc())
            raise ImportError("Failed to import main_cli.py")
    else:
        logger.error(f"Could not find main_cli.py at {main_cli_path}")
        raise FileNotFoundError(f"main_cli.py not found at {main_cli_path}")

except Exception as e:
    logger.error(f"Failed to run template agent: {e}")
    logger.error(traceback.format_exc())
    
    # Fallback to a simple agent
    logger.info("Falling back to simple agent implementation...")
    
    class SimpleAgent:
        def __init__(self):
            self.graph_state = {}
            logger.info("Initialized SimpleAgent")
        
        async def process_message(self, message, session_state=None):
            logger.info(f"Processing message: {message}")
            return {
                "status": "success",
                "response": f"Echo: {message} (from simple fallback agent)"
            }
    
    class SimpleSessionManager:
        def __init__(self):
            logger.info("Initialized SimpleSessionManager")
    
    async def run_simple_cli():
        """Run a simple agent CLI interface as fallback."""
        try:
            agent = SimpleAgent()
            
            print("\nSimple Agent CLI Interface (Fallback)")
            print("Type 'exit' to quit\n")
            
            while True:
                try:
                    user_input = input("You: ")
                    if user_input.lower() in ['exit', 'quit']:
                        break
                    
                    response = await agent.process_message(user_input)
                    print(f"Agent: {response.get('response', '')}")
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error processing input: {e}")
                    print(f"Error: {str(e)}")
            
            print("\nExiting CLI interface")
            return 0
            
        except Exception as e:
            logger.error(f"Error running simple CLI: {e}")
            logger.error(traceback.format_exc())
            return 1

    if __name__ == "__main__":
        exit_code = asyncio.run(run_simple_cli())
        sys.exit(exit_code) 