"""Example orchestrator graph that demonstrates tool integration."""

import asyncio
from typing import Dict, Any, List, Optional, Callable, TypeVar, Union
import logging
import os
from datetime import datetime

# Orchestrator graph imports
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer

# Local imports
from src.graphs.orchestrator_graph import (
    GraphState,
    StateManager,
    Message,
    MessageRole,
    create_initial_state
)
from src.tools.graph_integration import (
    setup_graph_routing,
    get_available_tools
)
from src.tools.tool_utils import (
    format_conversation_history
)

# Setup logging
logger = logging.getLogger(__name__)


async def llm_node(state: GraphState, writer) -> GraphState:
    """
    LLM node that processes user input and generates assistant responses.
    
    Args:
        state: The current graph state
        writer: Stream writer for outputting messages
        
    Returns:
        Updated graph state
    """
    state_manager = StateManager(state)
    
    try:
        # For demo purposes, simulate LLM processing
        writer("\n#### Processing with LLM...\n")
        
        # Get last user message
        context = state_manager.get_conversation_context(5)
        last_user_msg = None
        
        for msg in reversed(context):
            if msg.role == MessageRole.USER:
                last_user_msg = msg
                break
        
        if not last_user_msg:
            writer("\n#### No user message found\n")
            return state
        
        user_input = last_user_msg.content
        writer(f"\n#### User input: {user_input}\n")
        
        # Check for tool-related keywords and generate responses
        response = ""
        available_tools = get_available_tools()
        
        if "schedule" in user_input.lower() or "appointment" in user_input.lower():
            response = "I'll use the valet tool to check your schedule and appointments.\nvalet(task='Check schedule and appointments')"
        elif "email" in user_input.lower() or "task" in user_input.lower() or "todo" in user_input.lower():
            response = "I'll use the personal_assistant tool to manage your emails and tasks.\npersonal_assistant(task='Handle emails and tasks')"
        elif "research" in user_input.lower() or "information" in user_input.lower():
            response = "I'll use the librarian tool to research that for you.\nlibrarian(task='Research information')"
        else:
            # Direct response for general queries
            if "joke" in user_input.lower():
                response = "Why don't scientists trust atoms? Because they make up everything!"
            elif "hello" in user_input.lower() or "hi" in user_input.lower():
                response = "Hello! I'm Ronan, your AI assistant. How can I help you today?"
            else:
                response = "I understand your request. Could you provide more details about what you need help with? I can assist with schedules, emails, tasks, or research."
        
        # Add the assistant response to the conversation
        state_manager.update_conversation(
            role=MessageRole.ASSISTANT,
            content=response,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "type": "llm_response"
            }
        )
        
        writer(f"\n#### Assistant response: {response}\n")
        
        return state_manager.get_current_state()
    except Exception as e:
        error_msg = f"Error in LLM node: {str(e)}"
        logger.error(error_msg)
        writer(f"\n#### {error_msg}\n")
        
        # Add error message to conversation
        try:
            state_manager.update_conversation(
                role=MessageRole.SYSTEM,
                content=f"Error processing request: {str(e)}",
                metadata={"error": True, "timestamp": datetime.now().isoformat()}
            )
        except Exception:
            pass
        
        return state_manager.get_current_state()


def create_graph() -> StateGraph:
    """
    Create the orchestrator graph with tool integration.
    
    Returns:
        Configured StateGraph instance
    """
    # Create the graph with the initial state
    graph = StateGraph(create_initial_state)
    
    # Add the LLM node
    graph.add_node("llm", llm_node)
    
    # Setup tool routing
    setup_graph_routing(graph, llm_node_name="llm")
    
    # Set the entry point
    graph.set_entry_point("llm")
    
    return graph


async def process_message(graph, state: GraphState, user_message: str) -> GraphState:
    """
    Process a user message through the graph.
    
    Args:
        graph: The StateGraph instance
        state: The current state
        user_message: The user's message
        
    Returns:
        Updated state after processing
    """
    # Create a state manager for the current state
    state_manager = StateManager(state)
    
    # Add the user message to the conversation
    state_manager.update_conversation(
        role=MessageRole.USER,
        content=user_message,
        metadata={"timestamp": datetime.now().isoformat()}
    )
    
    # Get the updated state
    updated_state = state_manager.get_current_state()
    
    # Process the message through the graph
    writer = get_stream_writer()
    config = {"configurable": {"thread_id": "demo"}}
    
    for chunk in graph.stream(updated_state, config, writer=writer):
        # Just use the final state
        final_state = chunk
    
    return final_state


async def main():
    """Run a demo conversation with the orchestrator graph."""
    print("=== Orchestrator Graph Demo ===")
    print("Type 'exit' to end the conversation")
    
    # Create the graph
    graph = create_graph()
    
    # Initialize state
    state = create_initial_state()
    
    while True:
        # Get user input
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break
        
        # Process the message
        state = await process_message(graph, state, user_input)
        
        # Display the conversation
        state_manager = StateManager(state)
        context = state_manager.get_conversation_context(2)
        
        if len(context) >= 1 and context[-1].role == MessageRole.ASSISTANT:
            print(f"\nAssistant: {context[-1].content}")
        
        # Display tool results if any
        for msg in context:
            if msg.role == MessageRole.TOOL and msg.metadata.get("type") == "tool_result":
                tool_name = msg.metadata.get("tool", "unknown")
                print(f"\nTool Result [{tool_name}]: {msg.content}")


if __name__ == "__main__":
    asyncio.run(main()) 