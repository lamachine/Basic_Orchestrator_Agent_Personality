"""
State models for the template agent.

This module provides unified state models using Pydantic for type safety and validation.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field, validator

class MessageType(str, Enum):
    """Types of messages in the system."""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"

class MessageStatus(str, Enum):
    """Status values for messages."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    COMPLETED = "completed"

class Message(BaseModel):
    """Unified message structure for all communications."""
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_request_id: Optional[str] = None
    type: MessageType
    status: MessageStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    content: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('content')
    def validate_content_length(cls, v):
        """Validate content length."""
        if len(v) > 1000000:  # 1MB limit
            raise ValueError('Content length exceeds 1MB limit')
        return v

    @validator('metadata')
    def validate_metadata_size(cls, v):
        """Validate metadata size."""
        if len(str(v)) > 10000:  # 10KB limit
            raise ValueError('Metadata size exceeds 10KB limit')
        return v

    def create_child_message(self, content: str, data: Dict[str, Any] = None) -> 'Message':
        """Create a child message for sub-requests."""
        return Message(
            parent_request_id=self.request_id,
            type=self.type,
            status=MessageStatus.PENDING,
            content=content,
            data=data or {},
            metadata=self.metadata
        )

class GraphState(BaseModel):
    """Unified state model using Pydantic."""
    messages: List[Message] = Field(default_factory=list)
    conversation_state: Dict[str, Any] = Field(default_factory=dict)
    agent_states: Dict[str, Any] = Field(default_factory=dict)
    current_task: Optional[str] = None
    task_history: List[str] = Field(default_factory=list)
    agent_results: Dict[str, Any] = Field(default_factory=dict)
    final_result: Optional[str] = None

    @validator('messages')
    def validate_messages_size(cls, v):
        """Validate total messages size."""
        total_size = sum(len(msg.content) for msg in v)
        if total_size > 10000000:  # 10MB limit
            raise ValueError('Total messages size exceeds 10MB limit')
        return v

    class Config:
        arbitrary_types_allowed = True 