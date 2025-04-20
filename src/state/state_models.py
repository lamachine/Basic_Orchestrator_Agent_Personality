"""
State model classes for representing conversation state and messages.

This module defines the data models used for state management throughout 
the application, with validation and helper methods.
"""

import uuid
from enum import Enum
from typing import Annotated, Dict, List, Any, Optional, Union
from typing_extensions import TypedDict
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

class MessageRole(str, Enum):
    """
    Enumeration of possible message roles in a conversation.
    """
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class TaskStatus(str, Enum):
    """
    Enumeration of possible task statuses.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Message(BaseModel):
    """
    Represents a single message in a conversation with validation.
    
    In the system architecture:
    - A 'Message' is the full object containing state changes passed around the system internally
    - 'content' is the actual text/data being communicated (e.g., tool call details, 
       database queries, LLM prompts, or LLM responses)
    - 'content' is also the name of the database column in 'swarm_messages' table where
       the actual message text/data is stored
       
    The 'content' field contains the most recent user input or system output, while the
    full Message object contains metadata and state information for internal processing.
    """
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        """Validate that message content is not empty."""
        # Trim whitespace to prevent spaces-only messages
        trimmed = v.strip() if isinstance(v, str) else ''
        
        # Check if the content is empty after trimming
        if not trimmed:
            raise ValueError('Content cannot be empty')
            
        # Return the trimmed content
        return trimmed

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Ensure metadata is a dictionary."""
        return v or {}

class ConversationState(BaseModel):
    """
    Represents the state of a conversation including messages and task status.
    """
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)
    current_task_status: TaskStatus = Field(default=TaskStatus.PENDING)
    
    # For database compatibility
    session_id: Optional[int] = None
    current_request_id: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def update_timestamp(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Update the last_updated timestamp on any modification."""
        values['last_updated'] = datetime.now()
        return values

    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Add a new message to the conversation with validation."""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_updated = datetime.now()
        return message

    def get_last_message(self) -> Optional[Message]:
        """Get the last message in the conversation."""
        return self.messages[-1] if self.messages else None

    def get_context_window(self, n: int = 5) -> List[Message]:
        """Get the last n messages for context."""
        return self.messages[-n:] if self.messages else []

class GraphState(TypedDict):
    """
    Represents the full state of the conversation graph including all agents.
    """
    messages: Annotated[List[Message], lambda x, y: x + y]
    conversation_state: ConversationState
    agent_states: Dict[str, Any]
    current_task: Optional[str]
    task_history: List[str]
    agent_results: Dict[str, Any]
    final_result: Optional[str] 