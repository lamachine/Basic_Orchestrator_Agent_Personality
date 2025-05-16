"""
State management module for the template agent.

This module provides classes and functions for managing stateful interactions 
including session state, message history, and task tracking.
"""

from .state_models import (
    Message,
    MessageRole,
    MessageType,
    MessageStatus,
    TaskStatus,
    MessageState,
    GraphState
)

from .state_manager import StateManager

from .state_errors import (
    StateError,
    ValidationError,
    StateUpdateError,
    StateTransitionError,
    MessageError,
    TaskError,
    AgentStateError,
    PersistenceError
)

from .state_validator import StateValidator

# Alias for backward compatibility
SessionState = MessageState

__all__ = [
    'Message',
    'MessageRole',
    'MessageType',
    'MessageStatus',
    'TaskStatus',
    'MessageState',
    'SessionState',
    'GraphState',
    'StateManager',
    'StateError',
    'ValidationError',
    'StateUpdateError',
    'StateTransitionError',
    'MessageError',
    'TaskError',
    'AgentStateError',
    'PersistenceError',
    'StateValidator'
] 