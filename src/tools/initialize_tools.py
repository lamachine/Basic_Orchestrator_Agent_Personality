"""Initialize and register all tools."""

from typing import Dict, Any

from .tool_registry import ToolRegistry, ToolDescription
from .valet import valet_tool
from .personal_assistant import personal_assistant_tool
from .librarian import librarian_tool


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