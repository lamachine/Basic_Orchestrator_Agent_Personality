"""Integration of tools with the graph orchestration system."""

from typing import Dict, Any, List, Optional, Callable
import logging

from src.state.state_manager import StateManager
from src.state.state_models import Message, MessageRole
from src.tools.initialize_tools import get_registry
from src.tools.tool_utils import should_use_tool, create_tool_node_func

# Setup logging
logger = logging.getLogger(__name__)

async def get_available_tools() -> Dict[str, Callable]:
    """
    Get the dictionary of available tools from the registry.
    
    Returns:
        Dictionary mapping tool names to their functions
    """
    registry = get_registry()
    # Make sure tools are discovered
    if not registry.list_tools():
        await registry.discover_tools()
    
    tools = {}
    for tool_name in registry.list_tools():
        tools[tool_name] = registry.get_tool(tool_name)
    
    return tools


async def create_tool_nodes() -> Dict[str, Callable]:
    """
    Create graph node functions for all discovered tools.
    
    Returns:
        Dictionary mapping tool names to their node functions
    """
    nodes = {}
    registry = get_registry()
    
    # Make sure tools are discovered
    if not registry.list_tools():
        await registry.discover_tools()
    
    for tool_name in registry.list_tools():
        tool_class = registry.get_tool(tool_name)
        if tool_class:
            nodes[tool_name] = create_tool_node_func(tool_name, tool_class)
            logger.debug(f"Created node function for tool: {tool_name}")
    
    return nodes


async def route_to_tool(state: Dict[str, Any]) -> str:
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
    
    # Get available tools
    registry = get_registry()
    available_tools = registry.list_tools()
    
    # Check if the message contains a tool call
    tool_info = should_use_tool(latest_message, available_tools)
    
    if tool_info:
        return tool_info["tool"]
    
    return "llm"


async def setup_graph_routing(graph, llm_node_name="llm") -> None:
    """
    Set up the routing for tools in a StateGraph.
    
    Args:
        graph: The StateGraph to set up routing for
        llm_node_name: The name of the LLM node (default 'llm')
    """
    # Create tool nodes
    tool_nodes = await create_tool_nodes()
    
    # Add tool nodes to graph
    for tool_name, node_func in tool_nodes.items():
        graph.add_node(tool_name, node_func)
        logger.debug(f"Added tool node to graph: {tool_name}")
    
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
        logger.debug(f"Added edge from {tool_name} back to {llm_node_name}") 