from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"
    TOOL = "tool"


class MessageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    COMPLETED = "completed"


class Message(BaseModel):
    """Base message model for all communications."""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_request_id: Optional[str] = None
    type: MessageType
    status: MessageStatus = MessageStatus.PENDING
    timestamp: datetime = Field(default_factory=datetime.now)
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def create_child(self, content: str, type: MessageType = None) -> "Message":
        """Create a child message inheriting context."""
        return Message(
            parent_request_id=self.request_id,
            type=type or self.type,
            content=content,
            metadata={**self.metadata, "parent_message": self.request_id},
        )
