"""
Template Agent State Models.

This module defines the state models for the template agent,
including both base models and template-specific extensions.
It supports both independent operation and parent inheritance.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import importlib
import os
import yaml
from pathlib import Path
from ..services.logging_service import get_logger

logger = get_logger(__name__)

def load_tool_config() -> Dict[str, Any]:
    """Load tool configuration from YAML file."""
    config_path = Path(__file__).parent.parent / "config" / "tool_config.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            logger.debug(f"Loaded tool config: {config}")
            return config
    except Exception as e:
        logger.error(f"Could not load tool config: {e}")
        return {}

# Load config and check inheritance setting
config = load_tool_config()
INHERIT_FROM_PARENT = config.get('tool_settings', {}).get('inherit_from_parent', False)
logger.debug(f"INHERIT_FROM_PARENT set to: {INHERIT_FROM_PARENT}")

if INHERIT_FROM_PARENT:
    try:
        # Try to import from parent's state_models
        logger.debug("Attempting to import from parent's state_models")
        from ...state.state_models import (
            MessageRole, MessageType, MessageStatus, BaseMessage,
            StateUpdate, StateSnapshot, MessageState as ParentMessageState
        )
        logger.debug("Successfully imported parent's state_models")
    except ImportError as e:
        # If parent import fails, use local definitions
        logger.error(f"Failed to import parent's state_models: {e}")
        INHERIT_FROM_PARENT = False

if not INHERIT_FROM_PARENT:
    # Local definitions when running independently or if parent import fails
    class MessageRole(str, Enum):
        """Message roles."""
        USER = "user"
        ASSISTANT = "assistant"
        SYSTEM = "system"
        TOOL = "tool"

    class MessageType(str, Enum):
        """Message types."""
        TEXT = "text"
        TOOL_CALL = "tool_call"
        TOOL_RESULT = "tool_result"
        ERROR = "error"

    class MessageStatus(str, Enum):
        """Message statuses."""
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"

    class BaseMessage(BaseModel):
        """Base message model."""
        id: str = Field(..., description="Message identifier")
        role: MessageRole = Field(..., description="Message role")
        content: str = Field(..., description="Message content")
        timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")
        sender: Optional[str] = Field(None, description="Message sender")
        target: Optional[str] = Field(None, description="Message target")

    class StateUpdate(BaseModel):
        """Base state update model."""
        timestamp: datetime = Field(default_factory=datetime.now, description="Update timestamp")
        updates: Dict[str, Any] = Field(default_factory=dict, description="State updates")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="Update metadata")

    class StateSnapshot(BaseModel):
        """Base state snapshot model."""
        timestamp: datetime = Field(default_factory=datetime.now, description="Snapshot timestamp")
        state: Dict[str, Any] = Field(default_factory=dict, description="State snapshot")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="Snapshot metadata")

    class MessageState(BaseModel):
        """Message state model."""
        message: BaseMessage = Field(..., description="The message")
        status: MessageStatus = Field(default=MessageStatus.PENDING, description="Message status")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="State metadata")

# Template-specific extensions (always local)
class TemplateMessageType(str, Enum):
    """Template-specific message types."""
    TOOL_REQUEST = "tool_request"
    TOOL_RESPONSE = "tool_response"
    STATE_UPDATE = "state_update"
    STATE_QUERY = "state_query"
    ERROR = "error"

class TemplateMessageStatus(str, Enum):
    """Template-specific message statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TemplateMessage(BaseMessage):
    """
    Template-specific message model.
    
    Extends the base message model with template-specific fields
    and validation.
    """
    template_type: TemplateMessageType = Field(
        default=TemplateMessageType.TOOL_REQUEST,
        description="Template-specific message type"
    )
    template_status: TemplateMessageStatus = Field(
        default=TemplateMessageStatus.PENDING,
        description="Template-specific message status"
    )
    template_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Template-specific metadata"
    )

class TemplateStateUpdate(StateUpdate):
    """
    Template-specific state update model.
    
    Extends the base state update model with template-specific fields
    and validation.
    """
    template_updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Template-specific state updates"
    )
    template_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Template-specific metadata"
    )

class TemplateStateSnapshot(StateSnapshot):
    """
    Template-specific state snapshot model.
    
    Extends the base state snapshot model with template-specific fields
    and validation.
    """
    template_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Template-specific state"
    )
    template_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Template-specific metadata"
    )

class TemplateState(BaseModel):
    """
    Template-specific state model.
    
    This model represents the complete state of the template agent,
    including both inherited and template-specific state.
    """
    session_id: str = Field(
        ...,
        description="Session identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="State timestamp"
    )
    parent_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="State inherited from parent graph"
    )
    template_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Template-specific state"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="State metadata"
    )

# If inheriting from parent, use ParentMessageState as the base class
if INHERIT_FROM_PARENT:
    MessageState = ParentMessageState 