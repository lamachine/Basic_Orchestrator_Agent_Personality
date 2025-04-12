# Standard library imports
import asyncio
import os
from typing import Annotated, Dict, List, Any, Optional, Union, Type
from typing_extensions import TypedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid
from enum import Enum

# Third-party imports
from pydantic import ValidationError as PydanticValidationError, BaseModel, Field, field_validator, model_validator

# LangGraph imports
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

# Remove duplicate imports and sys.path manipulation
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter

# Import from state module instead of defining here
from src.state.state_models import (
    MessageRole,
    TaskStatus,
    Message,
    ConversationState,
    GraphState
)

from src.state.state_errors import (
    StateError,
    ValidationError,
    StateUpdateError,
    StateTransitionError
)

from src.state.state_validator import StateValidator

from src.state.state_manager import (
    StateManager,
    create_initial_state,
    update_agent_state,
    add_task_to_history
)

# Build the graph
def build_orchestrator_graph() -> StateGraph:
    """
    Build and return the orchestrator graph.
    
    Returns:
        A configured StateGraph for the orchestrator
    """
    # Create the graph
    graph = StateGraph(GraphState)
    
    # Add nodes
    # TODO: Implement actual graph nodes
    
    # Add edges
    # TODO: Implement graph edges
    
    return graph.compile()

# Main function for testing
def main():
    """
    Main function for testing the orchestrator graph.
    """
    # Create initial state
    state = create_initial_state()
    
    # Create state manager
    manager = StateManager(state)
    
    # Test adding messages
    try:
        manager.update_conversation(MessageRole.SYSTEM, "System initialization")
        manager.update_conversation(MessageRole.USER, "Hello, can you help me?")
        manager.update_conversation(MessageRole.ASSISTANT, "Yes, I can help you!")
        
        print("Conversation history:")
        for message in manager.get_conversation_context():
            print(f"{message.role}: {message.content}")
            
        # Test task management
        manager.set_task("Help the user")
        manager.complete_task("User has been helped")
        
        print("\nTask history:")
        for task in manager.get_task_history():
            print(f"- {task}")
            
        # Test agent state updates
        manager.update_agent_state("librarian", {"status": "ready"})
        manager.update_agent_state("personal_assistant", {"status": "busy"})
        
        print("\nAgent states:")
        for agent_id, state in manager.state['agent_states'].items():
            print(f"- {agent_id}: {state}")
        
    except Exception as e:
        print(f"Error: {e}")
        
    print("\nState manager test complete.")

if __name__ == "__main__":
    main()
