"""
Error classes for state management.

This module defines specialized exceptions for handling state-related errors,
allowing for more specific error handling throughout the application.
"""

class StateError(Exception):
    """Base class for state-related errors."""
    pass

class ValidationError(StateError):
    """Raised when state validation fails."""
    pass

class StateUpdateError(StateError):
    """Raised when state update fails."""
    pass

class StateTransitionError(StateError):
    """Raised when state transition is invalid."""
    pass 