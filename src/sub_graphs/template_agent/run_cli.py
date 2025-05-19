"""
CLI-specific entry point for the template agent.

This script is a thin wrapper that calls the main template agent
with the CLI interface selected.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from src.main import run_with_interface

if __name__ == "__main__":
    asyncio.run(run_with_interface("cli"))
