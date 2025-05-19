"""Tool initialization and discovery for template agent."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..services.logging_service import get_logger
from .tool_registry import ToolRegistry, ToolType

logger = get_logger(__name__)

# Singleton registry instance
_registry = None


def get_registry() -> ToolRegistry:
    """
    Get or create the singleton registry instance.

    Returns:
        ToolRegistry: The singleton registry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


async def initialize_tools() -> Dict[ToolType, List[str]]:
    """
    Initialize all tools using dynamic discovery.
    Single entry point for tool initialization.

    Returns:
        Dictionary mapping tool types to lists of initialized tool names
    """
    logger.debug("Initializing template agent tools...")

    # Get registry (creates if needed)
    registry = get_registry()

    # Discover and register tools
    await registry.discover_tools()

    # Get list of initialized tools by type
    initialized_tools = {tool_type: registry.list_tools(tool_type) for tool_type in ToolType}

    # Log discovery summary
    total_tools = sum(len(tools) for tools in initialized_tools.values())
    if total_tools > 0:
        logger.debug(f"Discovered and registered {total_tools} tools:")
        for tool_type, tools in initialized_tools.items():
            if tools:
                logger.debug(f"- {tool_type.value}: {', '.join(tools)}")
    else:
        logger.debug("No tools initialized")

    return initialized_tools


def get_tool_prompt_section() -> str:
    """
    Generate a prompt section describing available tools.

    Returns:
        String containing tool descriptions formatted for inclusion in prompts
    """
    registry = get_registry()
    tools_by_type = {tool_type: registry.list_tools(tool_type) for tool_type in ToolType}

    if not any(tools for tools in tools_by_type.values()):
        return "\n\n# AVAILABLE TOOLS\n\nNo tools are currently available."

    prompt_section = """
# AVAILABLE TOOLS

You have access to the following tools to help with your tasks. Use the appropriate tool when needed:

"""

    for tool_type, tools in tools_by_type.items():
        if not tools:
            continue

        prompt_section += f"\n## {tool_type.value.title()} Tools\n"

        for tool_name in tools:
            tool = registry.get_tool(tool_name)
            if not tool:
                continue

            prompt_section += f"""
### {tool.name}
{tool.description}

Parameters:
{chr(10).join(f"- {name}: {param.description} ({param.type.__name__})" for name, param in tool.parameters.items())}

Capabilities:
{chr(10).join(f"- {cap}" for cap in tool.capabilities)}

Example:
{tool.example if tool.example else "No example available"}

To use this tool, format your response as:
`{{"name": "{tool.name}", "args": {{"task": "your task here", "parameters": {{}}, "request_id": "auto-generated"}}}}`
"""

    prompt_section += """
IMPORTANT: When using tools:
1. Always include the task parameter with a clear description of what you want the tool to do
2. The request_id will be automatically generated
3. Use the exact tool name as shown above
4. Ensure your tool call is valid JSON (no trailing commas, correct syntax)
"""

    return prompt_section


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)

    # Run initialization
    initialized = asyncio.run(initialize_tools())

    # Print tool prompt section
    print("\nTool Prompt Section:")
    print(get_tool_prompt_section())
