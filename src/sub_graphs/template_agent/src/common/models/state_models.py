"""
State Models Module

This module defines the core state models used throughout the application.
These models represent the fundamental data structures for managing:
1. Graph state and transitions
2. Message handling and routing
3. Session management
4. State persistence
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages in the system."""

    REQUEST = "request"
    RESPONSE = "response"
    SYSTEM = "system"
    ERROR = "error"
    DEBUG = "debug"


class MessageStatus(str, Enum):
    """Status of a message in the system."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageRole(str, Enum):
    """Role of a message sender/recipient."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """Model for a message in the system."""

    request_id: str = Field(..., description="Unique identifier for the request")
    parent_request_id: Optional[str] = Field(None, description="ID of the parent request")
    type: MessageType = Field(..., description="Type of message")
    status: MessageStatus = Field(default=MessageStatus.PENDING, description="Current status")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the message was created"
    )
    content: str = Field(..., description="Message content")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")


class GraphState(BaseModel):
    """Model for the current state of the graph."""

    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    messages: List[Message] = Field(default_factory=list, description="List of messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="State metadata")
    created_at: datetime = Field(
        default_factory=datetime.now, description="When the state was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="When the state was last updated"
    )


class StateTransition(BaseModel):
    """Model for a state transition."""

    from_state: str = Field(..., description="Source state")
    to_state: str = Field(..., description="Target state")
    trigger: str = Field(..., description="What triggered the transition")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the transition occurred"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Transition metadata")
