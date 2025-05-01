"""Initialize and register all tools."""

from typing import Dict, Any
import os
import logging
import importlib.util

from .tool_registry import ToolRegistry, ToolDescription
# from .valet import valet_tool  # (disabled for minimal orchestrator)
# from .librarian_tool import librarian_tool  # (disabled for minimal orchestrator)
# from .file_upload_tool import file_upload_tool  # (disabled for minimal orchestrator)
# from .scrape_web_tool import scrape_web_tool
from src.tools.tool_utils import create_tool_node_func
# from .personal_assistant_tool import PersonalAssistantTool  # (disabled for minimal orchestrator)

# Setup logging
logger = logging.getLogger(__name__)


def initialize_tools() -> Dict[str, Any]:
    """
    Initialize all tools.
    
    Returns:
        Dict containing tool nodes and metadata
    """
    # Create tool nodes
    tool_nodes = {
        # "valet": create_tool_node_func(
        #     name="valet",
        #     function=valet_tool,
        #     example="valet(task='Check my schedule for today')"
        # ),
        # "personal_assistant": create_tool_node_func(
        #     name="personal_assistant",
        #     function=PersonalAssistantTool,
        #     example="personal_assistant(task='Send email to mom about Sunday plans')"
        # ),
        # "librarian": create_tool_node_func(
        #     name="librarian",
        #     function=librarian_tool,
        #     example="librarian(task='Research Pydantic agents')"
        # )
    }
    
    return tool_nodes


def get_tool_prompt_section() -> str:
    """
    Generate a prompt section describing available tools.
    
    Returns:
        String containing tool descriptions formatted for inclusion in prompts
    """
    registry = initialize_tools()
    tools = registry.list_tools()
    
    prompt_section = """
# AVAILABLE TOOLS

You have access to the following tools to help with your tasks. Use the appropriate tool when needed:

"""
    
    for tool in tools:
        prompt_section += f"""
## {tool.name}
{tool.description}

Example: `{tool.example}`
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


def initialize_tool_dependencies(llm_agent=None) -> Dict[str, bool]:
    """
    Initialize dependencies for specialized tools.
    
    Args:
        llm_agent: The LLM agent instance to pass to tools that need it
        
    Returns:
        Dictionary with status of each tool initialization
    """
    initializations = {}
    
    # Initialize GitHub adapter if available
    # try:
    #     from src.utils.github_adapter import set_llm_agent
    #     if llm_agent:
    #         set_llm_agent(llm_agent)
    #         logger.debug("GitHub adapter initialized with LLM agent")
    #         initializations["github_adapter"] = True
    #     else:
    #         logger.warning("GitHub adapter initialization skipped - no LLM agent provided")
    #         initializations["github_adapter"] = False
    # except ImportError as e:
    #     logger.debug(f"GitHub adapter not available: {e}")
    #     initializations["github_adapter"] = False

    # Initialize librarian dependencies
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
    
    # Check for GitHub token for scraping repos
    # if os.getenv("GITHUB_TOKEN"):
    #     logger.debug("GitHub token found for repository scraping")
    #     initializations["github_token"] = True
    # else:
    #     logger.warning("No GitHub token found - repository scraping may be limited")
    #     initializations["github_token"] = False
    
    # Log initialization summary
    initialized = sum(1 for status in initializations.values() if status)
    total = len(initializations)
    logger.debug(f"Tool dependencies initialization: {initialized}/{total} successful")
    
    return initializations 