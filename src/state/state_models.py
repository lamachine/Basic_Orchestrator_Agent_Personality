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

from src.services.logging_service import get_logger
logger = get_logger(__name__)

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
        trimmed = v.strip() if isinstance(v, str) else ''
        if not trimmed:
            raise ValueError('Content cannot be empty')
        return trimmed

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Ensure metadata is a dictionary."""
        return v or {}

class MessageState(BaseModel):
    """
    Represents the state of a session's messages and task status.
    """
    session_id: int
    messages: List[Message] = Field(default_factory=list)
    current_task: Optional[str] = None
    current_task_status: Optional[TaskStatus] = None
    last_updated: datetime = Field(default_factory=datetime.now)
    db_manager: Optional[Any] = None

    @model_validator(mode='before')
    @classmethod
    def update_timestamp(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Update the last_updated timestamp on any modification."""
        values['last_updated'] = datetime.now()
        return values

    async def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None, sender: str = None, target: str = None) -> Message:
        """Add a new message to the session with validation and optional persistence.
        
        Args:
            role: The role of the message sender
            content: The message content
            metadata: Optional metadata for the message
            sender: Required sender string
            target: Required target string
        
        Returns:
            The created message object
        
        Note:
            If db_manager is set, this will also persist the message to the database.
        """
        if not sender or not target:
            raise ValueError("Both sender and target must be provided for message persistence.")
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_updated = datetime.now()
        if self.db_manager and hasattr(self.db_manager, 'message_manager'):
            try:
                await self.db_manager.message_manager.add_message(
                    session_id=self.session_id,
                    role=role,
                    content=content,
                    metadata=metadata or {},
                    user_id="developer",
                    sender=sender,
                    target=target
                )
            except Exception as e:
                logger.warning(f"Failed to persist message to database: {e}")
                # Continue even if database persistence fails
        return message

    def get_last_message(self) -> Optional[Message]:
        """Get the last message in the session."""
        return self.messages[-1] if self.messages else None

    def get_context_window(self, n: int = 5) -> List[Message]:
        """Get the last n messages for context."""
        return self.messages[-n:] if self.messages else []

class GraphState(TypedDict):
    """
    Represents the full state of the conversation graph including all agents.
    """
    messages: List[Message]  # Direct list of messages
    conversation_state: Dict[str, Any]  # Simple dict for conversation state
    agent_states: Dict[str, Any]  # State for each agent
    current_task: Optional[str]  # Current task being processed
    task_history: List[str]  # History of tasks
    agent_results: Dict[str, Any]  # Results from each agent
    final_result: Optional[str]  # Final result of processing 