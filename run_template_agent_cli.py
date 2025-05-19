"""
Run the template agent with CLI interface.

This script provides a simple way to run the template agent
with the CLI interface from the project root.
"""

import asyncio
import importlib.util
import logging
import os
import sys

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to path
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Add src directory to path
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Load and run the main_cli module
main_cli_path = os.path.join(root_dir, "src", "sub_graphs", "template_agent", "src", "main_cli.py")
if os.path.exists(main_cli_path):
    # Import the module using spec
    spec = importlib.util.spec_from_file_location("main_cli", main_cli_path)
    main_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_cli)

    # Execute the main function
    if hasattr(main_cli, "main"):
        exit_code = main_cli.main()
        sys.exit(exit_code)
    elif hasattr(main_cli, "run_with_cli_interface"):
        exit_code = asyncio.run(main_cli.run_with_cli_interface())
        sys.exit(exit_code)
    else:
        logger.error("No suitable entry point found in main_cli.py")
        sys.exit(1)
else:
    logger.error(f"Could not find main_cli.py at {main_cli_path}")
    sys.exit(1)
