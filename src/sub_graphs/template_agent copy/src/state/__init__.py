"""
Template Agent State Module.

This module provides state management for the template agent, including:
- State models for messages, updates, and snapshots
- State validation with template-specific rules
- State error handling
"""

from .state_models import (
    TemplateMessage,
    TemplateStateUpdate,
    TemplateStateSnapshot,
    TemplateState,
    TemplateMessageType,
    TemplateMessageStatus
)
from .state_validator import StateValidator
from .state_errors import (
    TemplateStateError,
    TemplateMessageError,
    TemplateStateUpdateError,
    TemplateStateSnapshotError,
    TemplateStateValidationError,
    TemplateStateSyncError
)

__all__ = [
    'TemplateMessage',
    'TemplateStateUpdate',
    'TemplateStateSnapshot',
    'TemplateState',
    'TemplateMessageType',
    'TemplateMessageStatus',
    'StateValidator',
    'TemplateStateError',
    'TemplateMessageError',
    'TemplateStateUpdateError',
    'TemplateStateSnapshotError',
    'TemplateStateValidationError',
    'TemplateStateSyncError'
] 