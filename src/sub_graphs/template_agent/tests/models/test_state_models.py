"""
Tests for state_models.py

This module tests the state models, including:
1. MessageType and MessageStatus enums
2. Message model validation
3. GraphState model validation
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytest
from pydantic import ValidationError

from ...src.common.state.state_models import GraphState, Message, MessageStatus, MessageType


def test_message_type_enum():
    """Test MessageType enum."""
    # Test case: Normal operation - should pass
    assert MessageType.REQUEST == "request"
    assert MessageType.RESPONSE == "response"
    assert MessageType.ERROR == "error"
    assert MessageType.STATUS == "status"

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


def test_message_validation():
    """Test Message model validation."""
    # Test case: Normal operation - should pass
    message = Message(
        type=MessageType.REQUEST, status=MessageStatus.PENDING, content="Test message"
    )

    assert message.request_id is not None
    assert message.parent_request_id is None
    assert message.type == MessageType.REQUEST
    assert message.status == MessageStatus.PENDING
    assert isinstance(message.timestamp, datetime)
    assert message.content == "Test message"
    assert message.data == {}
    assert message.metadata == {}

    # Test with custom values
    custom_id = str(uuid.uuid4())
    parent_id = str(uuid.uuid4())
    custom_time = datetime.now() - timedelta(hours=1)

    message = Message(
        request_id=custom_id,
        parent_request_id=parent_id,
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
        timestamp=custom_time,
        content="Custom message",
        data={"result": "test_result"},
        metadata={"source": "test"},
    )

    assert message.request_id == custom_id
    assert message.parent_request_id == parent_id
    assert message.type == MessageType.RESPONSE
    assert message.status == MessageStatus.SUCCESS
    assert message.timestamp == custom_time
    assert message.content == "Custom message"
    assert message.data["result"] == "test_result"
    assert message.metadata["source"] == "test"


def test_message_validation_error():
    """Test Message model validation errors."""
    # Test case: Error condition - missing required fields
    with pytest.raises(ValidationError):
        Message(status=MessageStatus.PENDING, content="Test message")  # Missing type

    with pytest.raises(ValidationError):
        Message(type=MessageType.REQUEST, content="Test message")  # Missing status

    with pytest.raises(ValidationError):
        Message(type=MessageType.REQUEST, status=MessageStatus.PENDING)  # Missing content

    # Test case: Error condition - invalid type value
    with pytest.raises(ValidationError):
        Message(
            type="invalid_type",  # Not a valid MessageType
            status=MessageStatus.PENDING,
            content="Test message",
        )

    # Test case: Error condition - invalid status value
    with pytest.raises(ValidationError):
        Message(
            type=MessageType.REQUEST,
            status="invalid_status",  # Not a valid MessageStatus
            content="Test message",
        )

    # Test case: Error condition - content too large
    with pytest.raises(ValueError, match="Content length exceeds 1MB limit"):
        Message(
            type=MessageType.REQUEST,
            status=MessageStatus.PENDING,
            content="A" * 1000001,  # Over 1MB of content
        )

    # Test case: Error condition - metadata too large
    large_metadata = {"key": "value" * 3000}  # Over 10KB
    with pytest.raises(ValueError, match="Metadata size exceeds 10KB limit"):
        Message(
            type=MessageType.REQUEST,
            status=MessageStatus.PENDING,
            content="Test message",
            metadata=large_metadata,
        )


def test_message_edge_cases():
    """Test Message edge cases."""
    # Test case: Edge case - empty content
    message = Message(
        type=MessageType.REQUEST,
        status=MessageStatus.PENDING,
        content="",  # Empty content (but not missing)
    )
    assert message.content == ""

    # Test case: Edge case - large but valid content
    large_content = "A" * 999999  # Just under 1MB
    message = Message(type=MessageType.REQUEST, status=MessageStatus.PENDING, content=large_content)
    assert len(message.content) == 999999

    # Test case: Edge case - complex data and metadata
    complex_data = {
        "results": [{"id": 1, "name": "Result 1"}, {"id": 2, "name": "Result 2"}],
        "pagination": {"page": 1, "per_page": 10, "total": 2},
    }

    complex_metadata = {
        "source": "test",
        "tags": ["tag1", "tag2"],
        "processing": {"time_ms": 150, "steps": ["step1", "step2", "step3"]},
    }

    message = Message(
        type=MessageType.RESPONSE,
        status=MessageStatus.SUCCESS,
        content="Complex data test",
        data=complex_data,
        metadata=complex_metadata,
    )

    assert message.data["results"][1]["name"] == "Result 2"
    assert message.data["pagination"]["total"] == 2
    assert message.metadata["tags"][0] == "tag1"
    assert message.metadata["processing"]["steps"][2] == "step3"


def test_create_child_message():
    """Test creating a child message."""
    # Test case: Normal operation - should pass
    parent = Message(
        type=MessageType.REQUEST,
        status=MessageStatus.SUCCESS,
        content="Parent message",
        metadata={"source": "test"},
    )

    child = parent.create_child_message("Child message")

    assert child.parent_request_id == parent.request_id
    assert child.type == parent.type
    assert child.status == MessageStatus.PENDING
    assert child.content == "Child message"
    assert child.data == {}
    assert child.metadata == parent.metadata

    # Test with custom data
    custom_data = {"param1": "value1", "param2": 42}
    child = parent.create_child_message("Child with data", custom_data)

    assert child.parent_request_id == parent.request_id
    assert child.data["param1"] == "value1"
    assert child.data["param2"] == 42


def test_graph_state_validation():
    """Test GraphState model validation."""
    # Test case: Normal operation - should pass
    graph_state = GraphState()

    assert graph_state.messages == []
    assert graph_state.conversation_state == {}
    assert graph_state.agent_states == {}
    assert graph_state.current_task is None
    assert graph_state.task_history == []
    assert graph_state.agent_results == {}
    assert graph_state.final_result is None

    # Test with custom values
    message1 = Message(type=MessageType.REQUEST, status=MessageStatus.PENDING, content="Message 1")

    message2 = Message(type=MessageType.RESPONSE, status=MessageStatus.SUCCESS, content="Message 2")

    graph_state = GraphState(
        messages=[message1, message2],
        conversation_state={"context": "test context"},
        agent_states={"agent1": {"status": "active"}},
        current_task="test_task",
        task_history=["previous_task", "test_task"],
        agent_results={"agent1": "result1"},
        final_result="Final test result",
    )

    assert len(graph_state.messages) == 2
    assert graph_state.messages[0].content == "Message 1"
    assert graph_state.messages[1].content == "Message 2"
    assert graph_state.conversation_state["context"] == "test context"
    assert graph_state.agent_states["agent1"]["status"] == "active"
    assert graph_state.current_task == "test_task"
    assert graph_state.task_history == ["previous_task", "test_task"]
    assert graph_state.agent_results["agent1"] == "result1"
    assert graph_state.final_result == "Final test result"


def test_graph_state_validation_error():
    """Test GraphState validation errors."""
    # Test case: Error condition - messages too large
    large_messages = []
    for i in range(11):  # 11 messages with ~1MB content each
        large_messages.append(
            Message(
                type=MessageType.REQUEST,
                status=MessageStatus.PENDING,
                content="A" * 999999,  # Just under 1MB
            )
        )

    with pytest.raises(ValueError, match="Total messages size exceeds 10MB limit"):
        GraphState(messages=large_messages)


def test_graph_state_edge_cases():
    """Test GraphState edge cases."""
    # Test case: Edge case - single message
    message = Message(
        type=MessageType.REQUEST, status=MessageStatus.PENDING, content="Single message"
    )

    graph_state = GraphState(messages=[message])
    assert len(graph_state.messages) == 1
    assert graph_state.messages[0].content == "Single message"

    # Test case: Edge case - large but valid messages
    valid_large_messages = []
    for i in range(10):  # 10 messages with ~1MB content each (just under limit)
        valid_large_messages.append(
            Message(
                type=MessageType.REQUEST,
                status=MessageStatus.PENDING,
                content="A" * 999000,  # Just under 1MB
            )
        )

    graph_state = GraphState(messages=valid_large_messages)
    assert len(graph_state.messages) == 10

    # Test case: Edge case - complex nested structures
    complex_conversation_state = {
        "user": {
            "id": "user123",
            "preferences": {"theme": "dark", "notifications": True},
        },
        "session": {
            "started_at": datetime.now(),
            "context": {
                "previous_topics": ["topic1", "topic2"],
                "sentiment": "positive",
            },
        },
    }

    complex_agent_states = {
        "agent1": {
            "status": "active",
            "memory": {
                "items": [
                    {"key": "fact1", "value": "value1"},
                    {"key": "fact2", "value": "value2"},
                ]
            },
        },
        "agent2": {
            "status": "idle",
            "last_action": "query",
            "action_history": ["start", "process", "query"],
        },
    }

    graph_state = GraphState(
        conversation_state=complex_conversation_state, agent_states=complex_agent_states
    )

    assert graph_state.conversation_state["user"]["preferences"]["theme"] == "dark"
    assert graph_state.agent_states["agent1"]["memory"]["items"][1]["value"] == "value2"
    assert graph_state.agent_states["agent2"]["action_history"][0] == "start"
