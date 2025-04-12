"""Integration of tools with the graph orchestration system."""

from typing import Dict, Any, List, Optional, Callable
import logging

from src.graphs.orchestrator_graph import (
    GraphState,
    StateManager,
    Message,
    MessageRole
)

from src.tools.valet import valet_tool
from src.tools.personal_assistant import personal_assistant_tool
from src.tools.librarian import librarian_tool
from src.tools.tool_utils import (
    create_tool_node_func,
    extract_tool_call_from_message,
    should_use_tool
)

# Setup logging
logger = logging.getLogger(__name__)

# Define standard tools
STANDARD_TOOLS = {
    "valet": valet_tool,
    "personal_assistant": personal_assistant_tool,
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


def route_to_tool(state: GraphState) -> str:
    """
    Determine which tool to route to based on conversation state.
    This is used as a router function in the graph.
    
    Args:
        state: The current graph state
        
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