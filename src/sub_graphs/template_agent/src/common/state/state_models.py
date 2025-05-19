"""
State models for the template agent.

This module provides unified state models using Pydantic for type safety and validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class MessageRole(str, Enum):
    """Types of message roles in the system."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(str, Enum):
    """Types of messages in the system."""

    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"
    USER_INPUT = "user_input"
    SYSTEM_PROMPT = "system_prompt"
    LLM_RESPONSE = "llm_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_STATE = "agent_state"
    LOG_MESSAGE = "log_message"
    ERROR_MESSAGE = "error_message"


class MessageStatus(str, Enum):
    """Status values for messages."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    COMPLETED = "completed"


class TaskStatus(str, Enum):
    """Status values for tasks."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Message(BaseModel):
    """Unified message structure for all communications."""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_request_id: Optional[str] = None
    role: MessageRole
    type: MessageType
    status: MessageStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    content: str
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content length."""
        if len(v) > 1000000:  # 1MB limit
            raise ValueError("Content length exceeds 1MB limit")
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata size."""
        if len(str(v)) > 10000:  # 10KB limit
            raise ValueError("Metadata size exceeds 10KB limit")
        return v

    def create_child_message(self, content: str, data: Dict[str, Any] = None) -> "Message":
        """Create a child message for sub-requests."""
        return Message(
            parent_request_id=self.request_id,
            role=self.role,
            type=self.type,
            status=MessageStatus.PENDING,
            content=content,
            data=data or {},
            metadata=self.metadata,
        )


class MessageState(BaseModel):
    """Represents the state of a session's messages and task status."""

    session_id: int
    messages: List[Message] = Field(default_factory=list)
    current_task: Optional[str] = None
    current_task_status: Optional[TaskStatus] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    db_manager: Optional[Any] = None

    @field_validator("messages")
    @classmethod
    def validate_messages_size(cls, v: List[Message]) -> List[Message]:
        """Validate total messages size."""
        total_size = sum(len(msg.content) for msg in v)
        if total_size > 10000000:  # 10MB limit
            raise ValueError("Total messages size exceeds 10MB limit")
        return v

    async def add_message(
        self,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        sender: str = None,
        target: str = None,
    ) -> Message:
        """Add a new message to the session with validation and optional persistence."""
        if not sender or not target:
            raise ValueError("Both sender and target must be provided for message persistence.")

        message = Message(
            role=role,
            type=(MessageType.USER_INPUT if role == MessageRole.USER else MessageType.RESPONSE),
            status=MessageStatus.PENDING,
            content=content,
            metadata=metadata or {},
        )

        self.messages.append(message)
        self.last_updated = datetime.now()

        if self.db_manager and hasattr(self.db_manager, "message_manager"):
            try:
                await self.db_manager.message_manager.add_message(
                    session_id=self.session_id,
                    role=role,
                    content=content,
                    metadata=metadata or {},
                    user_id="developer",
                    sender=sender,
                    target=target,
                )
            except Exception as e:
                # Log error but continue
                pass

        return message

    def get_last_message(self) -> Optional[Message]:
        """Get the last message in the session."""
        return self.messages[-1] if self.messages else None

    def get_context_window(self, n: int = 5) -> List[Message]:
        """Get the last n messages for context."""
        return self.messages[-n:] if self.messages else []


class GraphState(BaseModel):
    """Unified state model using Pydantic."""

    messages: List[Message] = Field(default_factory=list)
    conversation_state: Dict[str, Any] = Field(default_factory=dict)
    agent_states: Dict[str, Any] = Field(default_factory=dict)
    current_task: Optional[str] = None
    task_history: List[str] = Field(default_factory=list)
    agent_results: Dict[str, Any] = Field(default_factory=dict)
    final_result: Optional[str] = None

    @field_validator("messages")
    @classmethod
    def validate_messages_size(cls, v: List[Message]) -> List[Message]:
        """Validate total messages size."""
        total_size = sum(len(msg.content) for msg in v)
        if total_size > 10000000:  # 10MB limit
            raise ValueError("Total messages size exceeds 10MB limit")
        return v

    class Config:
        arbitrary_types_allowed = True
