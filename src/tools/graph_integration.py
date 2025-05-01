"""Integration of tools with the graph orchestration system."""

from typing import Dict, Any, List, Optional, Callable
import logging

from src.state.state_manager import StateManager
from src.state.state_models import Message, MessageRole

from src.sub_graphs.valet_agent.valet_tool import valet_tool
from src.sub_graphs.librarian_agent.librarian_tool import librarian_tool
from src.sub_graphs.personal_assistant_agent.personal_assistant_tool import PersonalAssistantTool
# from src.sub_graph_personal_assistant.agents.personal_assistant_agent import PersonalAssistantAgent  # (disabled for minimal orchestrator)
from src.tools.tool_utils import (
    create_tool_node_func,
    should_use_tool
)

# Setup logging
logger = logging.getLogger(__name__)

# Define standard tools with lazy loading for personal_assistant
# def get_personal_assistant_tool():
#     """Lazy load the personal assistant tool."""
#     from src.sub_graph_personal_assistant.agents.personal_assistant_agent import PersonalAssistantAgent
#     return PersonalAssistantAgent

STANDARD_TOOLS = {
    "valet": valet_tool,
    "personal_assistant": PersonalAssistantTool,
    "librarian": librarian_tool
}

def get_available_tools() -> Dict[str, Callable]:
    """
    Get the dictionary of available tools.
    
    Returns:
        Dictionary mapping tool names to their functions
    """
    return STANDARD_TOOLS


def create_tool_nodes() -> Dict[str, Callable]:
    """
    Create graph node functions for all standard tools.
    
    Returns:
        Dictionary mapping tool names to their node functions
    """
    nodes = {}
    for tool_name, tool_func in STANDARD_TOOLS.items():
        nodes[tool_name] = create_tool_node_func(tool_name, tool_func)
    return nodes


def route_to_tool(state: Dict[str, Any]) -> str:
    """
    Determine which tool to route to based on conversation state.
    This is used as a router function in the graph.
    
    Args:
        state: The current graph state dictionary
        
    Returns:
        Name of the tool to route to, or "llm" if no tool is needed
    """
    state_manager = StateManager(state)
    
    # Get the latest message
    context = state_manager.get_conversation_context(1)
    if not context:
        return "llm"  # Default to LLM if no conversation context
    
    latest_message = context[0]
    
    # Only route based on assistant messages
    if latest_message.role != MessageRole.ASSISTANT:
        return "llm"
    
    # Check if the message contains a tool call
    tool_info = should_use_tool(latest_message, list(STANDARD_TOOLS.keys()))
    
    if tool_info:
        return tool_info["tool"]
    
    return "llm"


def setup_graph_routing(graph, llm_node_name="llm") -> None:
    """
    Set up the routing for tools in a StateGraph.
    
    Args:
        graph: The StateGraph to set up routing for
        llm_node_name: The name of the LLM node (default 'llm')
    """
    # Create tool nodes
    tool_nodes = create_tool_nodes()
    
    # Add tool nodes to graph
    for tool_name, node_func in tool_nodes.items():
        graph.add_node(tool_name, node_func)
    
    # Set up routing from llm node
    graph.add_conditional_edges(
        llm_node_name,
        route_to_tool,
        {
            **{tool_name: tool_name for tool_name in tool_nodes.keys()},
            "llm": llm_node_name
        }
    )
    
    # Route all tool nodes back to llm node
    for tool_name in tool_nodes.keys():
        graph.add_edge(tool_name, llm_node_name) 