#!/usr/bin/env python
"""
Integration script to add tool discovery to the main CLI.

This is a modified version of src/run_cli.py that adds tool discovery
before launching the CLI interface.
"""

import asyncio
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("integrate_tools")

# Import the tool initialization system
from src.tools.initialize_tools import discover_and_initialize_tools, console_prompt_handler

async def run_with_tools():
    """Run the CLI with tool discovery integrated."""
    logger.info("Starting tool discovery process...")
    
    # First, discover and initialize tools
    newly_approved = await discover_and_initialize_tools(
        auto_approve=False,
        prompt_handler=console_prompt_handler
    )
    
    if newly_approved:
        logger.info(f"Newly approved tools: {newly_approved}")
    
    # Then run the main CLI
    logger.info("Tool discovery complete, starting CLI...")
    from src.main import run_with_interface
    await run_with_interface("cli")

if __name__ == "__main__":
    asyncio.run(run_with_tools()) 