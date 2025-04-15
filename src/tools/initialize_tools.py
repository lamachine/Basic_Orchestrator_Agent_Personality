"""Initialize and register all tools."""

from typing import Dict, Any
import os
import logging
import importlib.util

from .tool_registry import ToolRegistry, ToolDescription
from .valet import valet_tool
from .personal_assistant import personal_assistant_tool
from .librarian import librarian_tool
# from .scrape_web_tool import scrape_web_tool

# Setup logging
logger = logging.getLogger(__name__)


def initialize_tools() -> ToolRegistry:
    """
    Initialize and register all tools in a new registry.
    
    Returns:
        Populated ToolRegistry instance
    """
    registry = ToolRegistry()
    
    # Register Valet tool
    registry.register_tool(
        ToolDescription(
            name="valet",
            description=(
                "Manages household staff, daily schedule, and personal affairs. "
                "Use this tool to check on staff tasks, your appointments, "
                "and important personal messages."
            ),
            parameters={"task": "Optional[str] - The task or query for the valet"},
            function=valet_tool,
            example="valet(task='Check my schedule for today')"
        )
    )
    
    # Register Personal Assistant tool
    registry.register_tool(
        ToolDescription(
            name="personal_assistant",
            description=(
                "Handles communications, task lists, and personal productivity. "
                "Use this tool to send emails, check messages, and manage to-do lists."
            ),
            parameters={"task": "Optional[str] - The task or query for the personal assistant"},
            function=personal_assistant_tool,
            example="personal_assistant(task='Send email to mom about Sunday plans')"
        )
    )
    
    # Register Librarian tool
    registry.register_tool(
        ToolDescription(
            name="librarian",
            description=(
                "Performs research, documentation crawling, and knowledge management. "
                "Use this tool to research topics, gather information, and organize knowledge."
            ),
            parameters={"task": "Optional[str] - The research task or query for the librarian"},
            function=librarian_tool,
            example="librarian(task='Research Pydantic agents and save the results')"
        )
    )

    # Register Web Scraping tool
    # registry.register_tool(
    #     ToolDescription(
    #         name="scrape_web",
    #         description=(
    #             "Scrapes websites and web pages for knowledge capture and analysis. "
    #             "Use this tool to extract information from web pages and store it in the database."
    #         ),
    #         parameters={
    #             "task": "Optional[str] - The URL or description of the web scraping task",
    #             "request_id": "Optional[int] - Request ID for tracking the scraping operation"
    #         },
    #         function=scrape_web_tool,
    #         example="scrape_web(task='https://example.com/docs')"
    #     )
    # )
    
    return registry


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
When you need to use a tool, say "I'll use the [tool name] tool to [brief description of task]" 
followed by the tool call using the proper syntax.
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