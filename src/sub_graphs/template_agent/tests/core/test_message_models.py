"""
Tests for message models.
"""

from datetime import datetime, timezone

import pytest

from src.common.messages.message_models import Message, MessageRole, MessageStatus, MessageType


def test_message_creation():
    """Test basic message creation."""
    msg = Message(content="Test message", role=MessageRole.USER, message_type=MessageType.TEXT)
    assert msg.content == "Test message"
    assert msg.role == MessageRole.USER
    assert msg.message_type == MessageType.TEXT
    assert msg.status == MessageStatus.PENDING
    assert isinstance(msg.timestamp, datetime)
    assert msg.timestamp.tzinfo == timezone.utc


def test_message_with_metadata():
    """Test message creation with metadata."""
    metadata = {"key": "value"}
    msg = Message(
        content="Test message",
        role=MessageRole.ASSISTANT,
        message_type=MessageType.TEXT,
        metadata=metadata,
    )
    assert msg.metadata == metadata


def test_message_status_transitions():
    """Test message status transitions."""
    msg = Message(content="Test message", role=MessageRole.USER, message_type=MessageType.TEXT)
    assert msg.status == MessageStatus.PENDING

    msg.status = MessageStatus.PROCESSING
    assert msg.status == MessageStatus.PROCESSING

    msg.status = MessageStatus.COMPLETED
    assert msg.status == MessageStatus.COMPLETED

    msg.status = MessageStatus.FAILED
    assert msg.status == MessageStatus.FAILED


def test_message_types():
    """Test different message types."""
    msg = Message(content="Test message", role=MessageRole.USER, message_type=MessageType.TEXT)
    assert msg.message_type == MessageType.TEXT

    msg = Message(content="Test code", role=MessageRole.ASSISTANT, message_type=MessageType.CODE)
    assert msg.message_type == MessageType.CODE

    msg = Message(content="Test error", role=MessageRole.SYSTEM, message_type=MessageType.ERROR)
    assert msg.message_type == MessageType.ERROR


def test_message_roles():
    """Test different message roles."""
    msg = Message(content="Test message", role=MessageRole.USER, message_type=MessageType.TEXT)
    assert msg.role == MessageRole.USER

    msg = Message(
        content="Test message",
        role=MessageRole.ASSISTANT,
        message_type=MessageType.TEXT,
    )
    assert msg.role == MessageRole.ASSISTANT

    msg = Message(content="Test message", role=MessageRole.SYSTEM, message_type=MessageType.TEXT)
    assert msg.role == MessageRole.SYSTEM


def test_message_validation():
    """Test message validation."""
    with pytest.raises(ValueError):
        Message(content="", role=MessageRole.USER, message_type=MessageType.TEXT)

    with pytest.raises(ValueError):
        Message(content="Test message", role="invalid_role", message_type=MessageType.TEXT)

    with pytest.raises(ValueError):
        Message(content="Test message", role=MessageRole.USER, message_type="invalid_type")


def test_message_serialization():
    """Test message serialization."""
    msg = Message(
        content="Test message",
        role=MessageRole.USER,
        message_type=MessageType.TEXT,
        metadata={"key": "value"},
    )
    msg_dict = msg.dict()
    assert msg_dict["content"] == "Test message"
    assert msg_dict["role"] == "user"
    assert msg_dict["message_type"] == "text"
    assert msg_dict["metadata"] == {"key": "value"}
    assert "timestamp" in msg_dict
    assert "status" in msg_dict
