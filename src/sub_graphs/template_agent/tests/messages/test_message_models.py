"""
Tests for message_models.py

This module tests the message models, including:
1. Message type and status enums
2. Message model validation
3. Creating child messages
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pytest
from pydantic import ValidationError

from ...src.common.messages.message_models import Message, MessageStatus, MessageType


def test_message_type_enum():
    """Test MessageType enum."""
    # Test case: Normal operation - should pass
    assert MessageType.REQUEST == "request"
    assert MessageType.RESPONSE == "response"
    assert MessageType.ERROR == "error"
    assert MessageType.STATUS == "status"
    assert MessageType.TOOL == "tool"

    # Test case: All enum values are strings
    for type_value in MessageType:
        assert isinstance(type_value, str)


def test_message_status_enum():
    """Test MessageStatus enum."""
    # Test case: Normal operation - should pass
    assert MessageStatus.PENDING == "pending"
    assert MessageStatus.RUNNING == "running"
    assert MessageStatus.SUCCESS == "success"
    assert MessageStatus.PARTIAL == "partial"
    assert MessageStatus.ERROR == "error"
    assert MessageStatus.COMPLETED == "completed"

    # Test case: All enum values are strings
    for status_value in MessageStatus:
        assert isinstance(status_value, str)


def test_message_model_validation():
    """Test Message model validation."""
    # Test case: Normal operation - should pass
    message = Message(type=MessageType.REQUEST, content="Test message")

    # Verify default values
    assert message.status == MessageStatus.PENDING
    assert message.request_id is not None
    assert message.parent_request_id is None
    assert isinstance(message.timestamp, datetime)
    assert message.metadata == {}

    # Test with custom values
    custom_request_id = str(uuid.uuid4())
    custom_time = datetime.now() - timedelta(hours=1)

    message = Message(
        request_id=custom_request_id,
        parent_request_id="parent-id",
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
        timestamp=custom_time,
        content="Custom message",
        metadata={"source": "test"},
    )

    assert message.request_id == custom_request_id
    assert message.parent_request_id == "parent-id"
    assert message.type == MessageType.RESPONSE
    assert message.status == MessageStatus.SUCCESS
    assert message.timestamp == custom_time
    assert message.content == "Custom message"
    assert message.metadata["source"] == "test"


def test_message_model_validation_error():
    """Test Message model validation errors."""
    # Test case: Error condition - missing required fields
    with pytest.raises(ValidationError):
        Message(content="Missing type field")

    with pytest.raises(ValidationError):
        Message(type=MessageType.REQUEST)  # Missing content field

    # Test invalid type
    with pytest.raises(ValidationError):
        Message(type="invalid_type", content="Test message")  # Not a valid MessageType

    # Test invalid status
    with pytest.raises(ValidationError):
        Message(
            type=MessageType.REQUEST,
            status="invalid_status",  # Not a valid MessageStatus
            content="Test message",
        )

    # Test invalid timestamp
    with pytest.raises(ValidationError):
        Message(
            type=MessageType.REQUEST,
            timestamp="not_a_datetime",  # Not a valid datetime
            content="Test message",
        )


def test_message_model_edge_cases():
    """Test Message model edge cases."""
    # Test case: Edge case - empty content
    message = Message(type=MessageType.REQUEST, content="")  # Empty content is valid
    assert message.content == ""

    # Test case: Edge case - metadata with nested structure
    nested_metadata = {
        "source": "test",
        "tags": ["tag1", "tag2"],
        "details": {"priority": "high", "category": "test"},
    }

    message = Message(type=MessageType.REQUEST, content="Test message", metadata=nested_metadata)

    assert message.metadata["tags"][0] == "tag1"
    assert message.metadata["details"]["priority"] == "high"

    # Test case: Edge case - unicode content
    unicode_content = "テスト メッセージ 😊 🚀"
    message = Message(type=MessageType.REQUEST, content=unicode_content)
    assert message.content == unicode_content


def test_create_child_message():
    """Test creating a child message."""
    # Test case: Normal operation - should pass
    parent = Message(
        type=MessageType.REQUEST, content="Parent message", metadata={"source": "test"}
    )

    # Create child message
    child = parent.create_child("Child message")

    # Verify child message
    assert child.parent_request_id == parent.request_id
    assert child.type == parent.type  # Inherits type from parent
    assert child.content == "Child message"
    assert "parent_message" in child.metadata
    assert child.metadata["parent_message"] == parent.request_id
    assert child.metadata["source"] == "test"  # Inherits metadata from parent

    # Test with custom message type
    child_with_type = parent.create_child("Child with type", MessageType.RESPONSE)
    assert child_with_type.type == MessageType.RESPONSE
    assert child_with_type.parent_request_id == parent.request_id


def test_message_model_serialization():
    """Test Message model serialization."""
    # Test case: Normal operation - serialization to dict
    timestamp = datetime.now()
    message = Message(
        request_id="test-id",
        type=MessageType.REQUEST,
        timestamp=timestamp,
        content="Test message",
    )

    # Convert to dict
    message_dict = message.model_dump()

    # Verify serialization
    assert message_dict["request_id"] == "test-id"
    assert message_dict["type"] == "request"
    assert message_dict["status"] == "pending"
    assert message_dict["timestamp"] == timestamp
    assert message_dict["content"] == "Test message"

    # Verify serialization with advanced metadata
    message.metadata = {"nested": {"value": 123}}
    message_dict = message.model_dump()
    assert message_dict["metadata"]["nested"]["value"] == 123
