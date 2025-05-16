"""
Template Agent State Errors.

This module defines state-related errors for the template agent,
inheriting core errors from the orchestrator but adding
template-specific error types.
"""

from typing import Optional
from src.state.state_errors import StateError as BaseStateError

class TemplateStateError(BaseStateError):
    """Base class for template-specific state errors."""
    pass

class TemplateMessageError(TemplateStateError):
    """Error related to template message handling."""
    pass

class TemplateStateUpdateError(TemplateStateError):
    """Error related to template state updates."""
    pass

class TemplateStateSnapshotError(TemplateStateError):
    """Error related to template state snapshots."""
    pass

class TemplateStateValidationError(TemplateStateError):
    """Error related to template state validation."""
    pass

class TemplateStateSyncError(TemplateStateError):
    """Error related to template state synchronization with parent."""
    pass 