"""
CLI-specific entry point for the orchestrator system.

This script is a thin wrapper that calls the main orchestrator
with the CLI interface selected.
"""

from src.main import run_with_interface
import asyncio

if __name__ == "__main__":
    asyncio.run(run_with_interface("cli")) 