"""
State management module for maintaining session and agent state.

This module provides classes and functions for managing stateful interactions 
including session state, message history, and task tracking.
"""

from src.state.state_models import (
    Message,
    MessageRole, 
    MessageState,
    TaskStatus,
    GraphState
)

from src.state.state_manager import (
    StateManager,
    update_agent_state,
    add_task_to_history
)

from src.state.state_errors import (
    StateError,
    ValidationError,
    StateUpdateError,
    StateTransitionError
)

from src.state.state_validator import StateValidator

SessionState = MessageState

__all__ = [
    'Message',
    'MessageRole',
    'MessageState',
    'SessionState',
    'TaskStatus',
    'GraphState',
    'StateManager',
    'update_agent_state',
    'add_task_to_history',
    'StateError',
    'ValidationError',
    'StateUpdateError',
    'StateTransitionError',
    'StateValidator'
] 