"""Initialize and register all tools."""

from typing import Dict, Any, List
import os
import logging
import importlib.util
import asyncio

from .registry.tool_registry import ToolRegistry
from .tool_utils import create_tool_node_func

# Setup logging
logger = logging.getLogger(__name__)

# Global registry instance
_registry = None

def get_registry() -> ToolRegistry:
    """
    Get or create the tool registry singleton.
    
    Returns:
        ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


async def discover_and_initialize_tools(auto_approve: bool = False, prompt_handler=None) -> List[str]:
    """
    Discover and initialize tools, optionally prompting for approval.
    
    Args:
        auto_approve: Whether to automatically approve all discovered tools
        prompt_handler: Optional callback for prompting user about tool approval
            Function signature: async def handler(tool_name: str, tool_info: dict) -> bool
            
    Returns:
        List of newly approved tool names
    """
    registry = get_registry()
    
    # Discover tools
    new_tools = await registry.discover_tools(auto_approve=auto_approve)
    newly_approved = []
    
    # If we have new tools and a prompt handler, ask for approval
    if new_tools and prompt_handler and not auto_approve:
        for tool_name in new_tools:
            tool_info = registry.get_config(tool_name)
            if not tool_info:
                continue
                
            # Format tool info for display
            description = tool_info.get("description", "No description available")
            version = tool_info.get("version", "unknown")
            capabilities = tool_info.get("capabilities", [])
            capabilities_str = ", ".join(capabilities) if capabilities else "none specified"
            
            # Prompt for approval
            should_approve = await prompt_handler(
                tool_name, 
                {
                    "description": description,
                    "version": version,
                    "capabilities": capabilities_str
                }
            )
            
            if should_approve:
                registry.approve_tool(tool_name)
                newly_approved.append(tool_name)
                logger.info(f"User approved tool: {tool_name}")
            else:
                logger.info(f"User declined tool: {tool_name}")
    
    # Log summary
    all_tools = registry.list_all_discovered_tools()
    approved_count = sum(1 for approved in all_tools.values() if approved)
    logger.info(f"Tools initialized: {approved_count} approved out of {len(all_tools)} discovered")
    
    return newly_approved


async def initialize_tools() -> Dict[str, Any]:
    """
    Initialize all approved tools using dynamic discovery.
    
    Returns:
        Dict containing tool nodes and metadata
    """
    # Get registry instance
    registry = get_registry()
    
    # Make sure tools are discovered
    await registry.discover_tools()
    
    # Create tool nodes for all discovered and approved tools
    tool_nodes = {}
    for tool_name in registry.list_tools():
        tool_class = registry.get_tool(tool_name)
        tool_config = registry.get_config(tool_name)
        
        if tool_class and tool_config:
            # Create executable tool node function
            tool_nodes[tool_name] = create_tool_node_func(
                tool_name,
                tool_class
            )
            logger.info(f"Created tool node for: {tool_name}")
    
    logger.info(f"Initialized {len(tool_nodes)} tool nodes")
    return tool_nodes


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
            prompt_section += f"""
## {tool_name}
{description}

Example: `{{"name": "{tool_name}", "args": {{"task": "Example task"}}}}`
"""
    
    prompt_section += """
When you need to use a tool, you can use either format:
1. Simple format: "tool, [tool name], [task]"
2. Standard format: "I'll use the [tool name] tool to [task]"

For example:
- "tool, librarian, research pydantic"
- "I'll use the librarian tool to research pydantic"
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
        spec = importlib.util.find_spec('openai')
        if spec is not None:
            logger.debug("OpenAI module is available for the librarian tool")
            initializations["librarian"] = True
        else:
            logger.warning("OpenAI module not installed - librarian tool may have limited functionality")
            initializations["librarian"] = False
    except ImportError:
        logger.debug("OpenAI module not available")
        initializations["librarian"] = False

    # Initialize MCP client if available
    # try:
    #     from src.tools.mcp_tools import initialize_mcp_client
    #     mcp_initialized = initialize_mcp_client()
    #     logger.debug(f"MCP client initialized: {mcp_initialized}")
    #     initializations["mcp_client"] = mcp_initialized
    # except ImportError:
    #     logger.debug("MCP client not available")
    #     initializations["mcp_client"] = False
    
    
    # Log initialization summary
    initialized = sum(1 for status in initializations.values() if status)
    total = len(initializations)
    logger.debug(f"Tool dependencies initialization: {initialized}/{total} successful")
    
    return initializations 


# Console-based prompt handler for approving tools (for testing)
async def console_prompt_handler(tool_name: str, tool_info: Dict[str, Any]) -> bool:
    """
    Command-line handler for tool approval prompts.
    
    Args:
        tool_name: Name of the tool
        tool_info: Tool information dictionary
        
    Returns:
        True if the tool should be approved, False otherwise
    """
    print("\n=== New Tool Discovered ===")
    print(f"Name: {tool_name}")
    print(f"Description: {tool_info['description']}")
    print(f"Version: {tool_info['version']}")
    print(f"Capabilities: {tool_info['capabilities']}")
    print("==========================")
    
    while True:
        response = input("Approve this tool? (yes/no): ").lower()
        if response in ("yes", "y"):
            return True
        elif response in ("no", "n"):
            return False
        else:
            print("Please enter 'yes' or 'no'")


# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Run discovery and initialization
    asyncio.run(discover_and_initialize_tools(prompt_handler=console_prompt_handler))
    tool_nodes = asyncio.run(initialize_tools())
    
    print(f"Initialized {len(tool_nodes)} tool nodes:")
    for name in tool_nodes:
        print(f"- {name}")
        
    # Print tool prompt section
    print("\nTool Prompt Section:")
    print(get_tool_prompt_section()) 