"""Tool initialization and discovery."""

import asyncio
import importlib
import logging
from typing import Any, Dict, List, Optional

from src.tools.registry.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

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


async def initialize_tools() -> List[str]:
    """
    Initialize all tools using dynamic discovery.
    Single entry point for tool initialization.

    Returns:
        List of initialized tool names
    """
    logger.debug("Initializing tools...")

    # Get registry (creates if needed)
    registry = get_registry()

    # Discover and register tools
    await registry.discover_tools()

    # Get list of initialized tools
    initialized_tools = registry.list_tools()

    # Log only the count of discovered tools
    if initialized_tools:
        logger.debug(
            f"Discovered and registered {len(initialized_tools)} tools: {', '.join(initialized_tools)}"
        )
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
    tool_names = registry.list_tools()

    if not tool_names:
        return "\n\n# AVAILABLE TOOLS\n\nNo tools are currently available."

    prompt_section = """
# AVAILABLE TOOLS

You have access to the following tools to help with your tasks. Use the appropriate tool when needed:

"""

    for tool_name in tool_names:
        tool_config = registry.get_config(tool_name)
        if tool_config:
            description = tool_config.get("description", "No description available")
            capabilities = tool_config.get("capabilities", [])
            examples = tool_config.get("examples", [])

            prompt_section += f"""
## {tool_name}
{description}

Capabilities:
{chr(10).join(f"- {cap}" for cap in capabilities)}

Examples:
{chr(10).join(f"- {ex}" for ex in examples)}

To use this tool, format your response as:
`{{"name": "{tool_name}", "args": {{"task": "your task here", "parameters": {{}}, "request_id": "auto-generated"}}}}`
"""

    prompt_section += """
IMPORTANT: When using tools:
1. Always include the task parameter with a clear description of what you want the tool to do
2. The request_id will be automatically generated
3. Use the exact tool name as shown above
4. Ensure your tool call is valid JSON (no trailing commas, correct syntax)
"""

    return prompt_section


async def initialize_tool_dependencies(llm_agent=None) -> Dict[str, bool]:
    """
    Initialize dependencies for specialized tools.

    Args:
        llm_agent: The LLM agent instance to pass to tools that need it

    Returns:
        Dictionary with status of each tool initialization
    """
    initializations = {}

    # Initialize OpenAI dependency for librarian tools
    try:
        spec = importlib.util.find_spec("openai")
        if spec is not None:
            logger.debug("OpenAI module is available for the librarian tool")
            initializations["librarian"] = True
        else:
            logger.warning(
                "OpenAI module not installed - librarian tool may have limited functionality"
            )
            initializations["librarian"] = False
    except ImportError:
        logger.debug("OpenAI module not available")
        initializations["librarian"] = False

    # Log initialization summary
    initialized = sum(1 for status in initializations.values() if status)
    total = len(initializations)
    logger.debug(f"Tool dependencies initialization: {initialized}/{total} successful")

    return initializations


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)

    # Run initialization
    initialized = asyncio.run(initialize_tools())

    # Print tool prompt section
    print("\nTool Prompt Section:")
    print(get_tool_prompt_section())
