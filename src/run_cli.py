"""
CLI-specific entry point for the orchestrator system.

This script is a thin wrapper that calls the main orchestrator
with the CLI interface selected.
"""

# Import and call setup_logging first to initialize logging before any other imports
from src.config.logging_config import setup_logging

setup_logging()

import asyncio

from src.main import run_with_interface

if __name__ == "__main__":
    asyncio.run(run_with_interface("cli"))
