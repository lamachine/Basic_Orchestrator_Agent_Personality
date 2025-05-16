"""
CLI-specific entry point for the template agent.

This script serves as a thin wrapper that initializes and runs the template agent
with the CLI interface.
"""

import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env file
root_dir = Path(__file__).parent.parent.parent.parent
dotenv_path = root_dir / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"Loaded environment variables from {dotenv_path}")
else:
    print(f"Warning: No .env file found at {dotenv_path}")

# Ensure template_agent src directory is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import logging setup first
from src.common.services.logging_service import setup_logging
setup_logging()

# Import the main function that handles CLI setup
from src.main_cli import run_with_cli_interface

if __name__ == "__main__":
    asyncio.run(run_with_cli_interface()) 