#!/usr/bin/env python
"""Test script for tool discovery and initialization."""

import asyncio
import logging
import sys

from src.tools.initialize_tools import (
    console_prompt_handler,
    discover_and_initialize_tools,
    get_registry,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more information
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_tool_discovery")

# Enable debug logging for the tool registry
logging.getLogger("src.tools.registry.tool_registry").setLevel(logging.DEBUG)


async def main():
    """Run the tool discovery test."""
    logger.debug("Starting tool discovery test...")

    # Get registry reference
    registry = get_registry()

    # Log current state before discovery
    logger.debug(
        f"Registry state before discovery: approved_tools={registry.approved_tools}, tools={registry.tools.keys() if registry.tools else 'none'}"
    )

    # Discover and initialize tools with console prompting and auto-approve
    newly_approved = await discover_and_initialize_tools(
        auto_approve=True,  # Auto-approve to simplify testing
        prompt_handler=console_prompt_handler,
    )

    # Log state after discovery
    logger.debug(
        f"Registry state after discovery: approved_tools={registry.approved_tools}, tools={registry.tools.keys() if registry.tools else 'none'}"
    )

    # Print discovered tools
    all_tools = registry.list_all_discovered_tools()
    logger.debug(f"All discovered tools: {all_tools}")
    logger.debug(f"Newly approved tools: {newly_approved}")

    # Print approved tools and check actual loaded tools
    approved_tools = registry.list_tools()
    logger.debug(f"Approved and loaded tools: {approved_tools}")
    logger.debug(f"Raw approved_tools set: {registry.approved_tools}")
    logger.debug(f"Raw tools dict keys: {list(registry.tools.keys())}")

    # Check file paths
    import os

    src_path = os.path.join("src", "sub_graphs", "personal_assistant_agent")
    api_path = os.path.join(src_path, "personal_assistant_tool.py")
    config_path = os.path.join(src_path, "src", "config", "tool_config.yaml")

    logger.debug(f"API file exists: {os.path.exists(api_path)}")
    logger.debug(f"Config file exists: {os.path.exists(config_path)}")

    # Try to manually import the API class
    try:
        logger.debug("Attempting manual import of PersonalAssistantTool")
        from src.sub_graphs.personal_assistant_agent.personal_assistant_tool import (
            PersonalAssistantTool,
        )

        logger.debug(f"Manual import succeeded: {PersonalAssistantTool}")

        # Try to manually initialize and use the API
        api = PersonalAssistantTool()
        logger.debug(f"API initialized: {api}")
        result = await api.execute({"task": "Manual test task"})
        logger.debug(f"API execution result: {result}")
    except Exception as e:
        logger.error(f"Error with manual import/execution: {e}", exc_info=True)

    logger.debug("Tool discovery test complete!")


if __name__ == "__main__":
    asyncio.run(main())
