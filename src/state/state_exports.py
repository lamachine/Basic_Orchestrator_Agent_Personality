"""State module exports and public API."""

from src.state.state_errors import (
    StateError,
    StateTransitionError,
    StateUpdateError,
    ValidationError,
)
from src.state.state_manager import StateManager, add_task_to_history, update_agent_state
from src.state.state_models import GraphState, Message, MessageRole, MessageState, TaskStatus
from src.state.state_validator import StateValidator

# Alias for backward compatibility
SessionState = MessageState

__all__ = [
    "Message",
    "MessageRole",
    "MessageState",
    "SessionState",
    "TaskStatus",
    "GraphState",
    "StateManager",
    "update_agent_state",
    "add_task_to_history",
    "StateError",
    "ValidationError",
    "StateUpdateError",
    "StateTransitionError",
    "StateValidator",
]
