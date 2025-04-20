"""
CLI-specific entry point for the orchestrator system.

This script is a thin wrapper that calls the main orchestrator
with the CLI interface selected.
"""

from src.main import run_with_interface

if __name__ == "__main__":
    # Call the main orchestrator function with CLI interface
    run_with_interface("cli") 