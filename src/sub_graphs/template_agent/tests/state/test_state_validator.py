"""
Tests for state_validator.py

This module tests the validation functions for state operations, including:
1. Task status transition validation
2. Message sequence validation
3. Agent state validation
4. Message status transition validation
5. Message type validation for roles
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest

from ...src.common.state.state_models import (
    Message,
    MessageRole,
    MessageStatus,
    MessageType,
    TaskStatus,
)
from ...src.common.state.state_validator import StateValidator


@pytest.fixture
def validator():
    """Create a StateValidator instance for testing."""
    return StateValidator()


def test_validate_task_transition(validator):
    """Test task status transition validation."""
    # Test case: Normal operation - valid transitions should pass
    assert validator.validate_task_transition(TaskStatus.PENDING, TaskStatus.IN_PROGRESS) is True
    assert validator.validate_task_transition(TaskStatus.PENDING, TaskStatus.FAILED) is True
    assert validator.validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED) is True
    assert validator.validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.FAILED) is True
    assert validator.validate_task_transition(TaskStatus.FAILED, TaskStatus.PENDING) is True

    # Test case: Error condition - invalid transitions should fail
    assert validator.validate_task_transition(TaskStatus.PENDING, TaskStatus.COMPLETED) is False
    assert validator.validate_task_transition(TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS) is False
    assert validator.validate_task_transition(TaskStatus.COMPLETED, TaskStatus.FAILED) is False
    assert validator.validate_task_transition(TaskStatus.FAILED, TaskStatus.COMPLETED) is False


def test_validate_message_sequence(validator):
    """Test message sequence validation."""
    # Create test messages with increasing timestamps
    now = datetime.now()
    messages = [
        Message(
            role=MessageRole.USER,
            type=MessageType.REQUEST,
            status=MessageStatus.PENDING,
            content=f"Message {i}",
            timestamp=now + timedelta(seconds=i),
        )
        for i in range(5)
    ]

    # Test case: Normal operation - ordered timestamps should pass
    assert validator.validate_message_sequence(messages) is True

    # Test case: Error condition - out of order timestamps should fail
    messages[2].timestamp = now + timedelta(seconds=10)  # Make one timestamp later
    assert validator.validate_message_sequence(messages) is False

    # Test case: Edge case - empty message list should pass
    assert validator.validate_message_sequence([]) is True

    # Test case: Edge case - single message should pass
    assert validator.validate_message_sequence([messages[0]]) is True

    # Test case: Edge case - identical timestamps should pass
    messages = [
        Message(
            role=MessageRole.USER,
            type=MessageType.REQUEST,
            status=MessageStatus.PENDING,
            content=f"Message {i}",
            timestamp=now,  # Same timestamp for all
        )
        for i in range(3)
    ]
    assert validator.validate_message_sequence(messages) is True


def test_validate_agent_state(validator):
    """Test agent state validation."""
    # Test case: Normal operation - valid state structure should pass
    valid_state = {"status": "active"}
    assert validator.validate_agent_state("agent1", valid_state) is True

    # Test with additional fields
    valid_state_with_extras = {
        "status": "idle",
        "last_action": "query",
        "memory": {"key": "value"},
    }
    assert validator.validate_agent_state("agent2", valid_state_with_extras) is True

    # Test case: Error condition - missing required fields should fail
    invalid_state = {"last_action": "query"}  # Missing status
    assert validator.validate_agent_state("agent3", invalid_state) is False

    # Test case: Edge case - empty state should fail
    empty_state = {}
    assert validator.validate_agent_state("agent4", empty_state) is False

    # Test case: Edge case - None state should fail
    with pytest.raises(TypeError):
        validator.validate_agent_state("agent5", None)


def test_validate_message_status_transition(validator):
    """Test message status transition validation."""
    # Test case: Normal operation - valid transitions should pass
    assert (
        validator.validate_message_status_transition(MessageStatus.PENDING, MessageStatus.RUNNING)
        is True
    )
    assert (
        validator.validate_message_status_transition(MessageStatus.RUNNING, MessageStatus.SUCCESS)
        is True
    )
    assert (
        validator.validate_message_status_transition(MessageStatus.RUNNING, MessageStatus.ERROR)
        is True
    )
    assert (
        validator.validate_message_status_transition(MessageStatus.RUNNING, MessageStatus.PARTIAL)
        is True
    )
    assert (
        validator.validate_message_status_transition(MessageStatus.PARTIAL, MessageStatus.SUCCESS)
        is True
    )
    assert (
        validator.validate_message_status_transition(MessageStatus.ERROR, MessageStatus.PENDING)
        is True
    )

    # Test case: Error condition - invalid transitions should fail
    assert (
        validator.validate_message_status_transition(MessageStatus.PENDING, MessageStatus.SUCCESS)
        is False
    )
    assert (
        validator.validate_message_status_transition(MessageStatus.SUCCESS, MessageStatus.RUNNING)
        is False
    )
    assert (
        validator.validate_message_status_transition(MessageStatus.SUCCESS, MessageStatus.ERROR)
        is False
    )
    assert (
        validator.validate_message_status_transition(MessageStatus.COMPLETED, MessageStatus.PARTIAL)
        is False
    )


def test_validate_message_type_for_role(validator):
    """Test message type validation for roles."""
    # Test case: Normal operation - valid types for roles should pass
    assert validator.validate_message_type_for_role("user", MessageType.USER_INPUT) is True
    assert validator.validate_message_type_for_role("user", MessageType.REQUEST) is True
    assert validator.validate_message_type_for_role("assistant", MessageType.RESPONSE) is True
    assert validator.validate_message_type_for_role("assistant", MessageType.LLM_RESPONSE) is True
    assert validator.validate_message_type_for_role("assistant", MessageType.TOOL_CALL) is True
    assert validator.validate_message_type_for_role("system", MessageType.SYSTEM_PROMPT) is True
    assert validator.validate_message_type_for_role("system", MessageType.STATUS) is True
    assert validator.validate_message_type_for_role("tool", MessageType.TOOL_RESULT) is True
    assert validator.validate_message_type_for_role("tool", MessageType.TOOL_CALL) is True

    # Test case: Error condition - invalid types for roles should fail
    assert validator.validate_message_type_for_role("user", MessageType.RESPONSE) is False
    assert validator.validate_message_type_for_role("assistant", MessageType.USER_INPUT) is False
    assert validator.validate_message_type_for_role("system", MessageType.TOOL_RESULT) is False
    assert validator.validate_message_type_for_role("tool", MessageType.SYSTEM_PROMPT) is False

    # Test case: Edge case - unknown role should return False
    assert validator.validate_message_type_for_role("unknown_role", MessageType.REQUEST) is False

    # Test case: Edge case - empty role should return False
    assert validator.validate_message_type_for_role("", MessageType.REQUEST) is False
