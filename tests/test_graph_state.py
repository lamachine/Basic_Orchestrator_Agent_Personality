"""Tests for the graph state components."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import uuid
from typing import Dict, Any, List

from src.graphs.orchestrator_graph import (
    MessageRole, TaskStatus, Message, ConversationState,
    GraphState, StateError, ValidationError, StateUpdateError,
    StateTransitionError, StateValidator, StateManager,
    create_initial_state, update_agent_state, add_task_to_history
)

def test_message_role_enum():
    """Test MessageRole enum values."""
    assert MessageRole.USER == "user"
    assert MessageRole.ASSISTANT == "assistant" 
    assert MessageRole.SYSTEM == "system"
    assert MessageRole.TOOL == "tool"

def test_task_status_enum():
    """Test TaskStatus enum values."""
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.IN_PROGRESS == "in_progress"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"

def test_message_model():
    """Test Message model creation and validation."""
    # Test basic creation
    msg = Message(role=MessageRole.USER, content="Test message")
    assert msg.role == MessageRole.USER
    assert msg.content == "Test message"
    assert isinstance(msg.created_at, datetime)
    assert isinstance(msg.metadata, dict)
    assert msg.metadata == {}
    
    # Test with metadata
    metadata = {"user_id": "123", "source": "web"}
    msg = Message(role=MessageRole.ASSISTANT, content="Response", metadata=metadata)
    assert msg.metadata == metadata
    
    # Test content validation
    with pytest.raises(ValueError):
        Message(role=MessageRole.USER, content="")
    
    with pytest.raises(ValueError):
        Message(role=MessageRole.USER, content="   ")
    
    # Test content stripping
    msg = Message(role=MessageRole.USER, content="  Hello  ")
    assert msg.content == "Hello"
    
    # Test metadata validation
    msg = Message(role=MessageRole.USER, content="Hello", metadata=None)
    assert msg.metadata == {}

def test_conversation_state():
    """Test ConversationState model."""
    # Test creation
    conv = ConversationState()
    assert isinstance(conv.conversation_id, str)
    assert conv.messages == []
    assert isinstance(conv.last_updated, datetime)
    assert conv.current_task_status == TaskStatus.PENDING
    
    # Test add_message
    message = conv.add_message(MessageRole.USER, "Hello")
    assert len(conv.messages) == 1
    assert conv.messages[0] == message
    assert message.role == MessageRole.USER
    assert message.content == "Hello"
    
    # Test last_updated gets updated
    old_timestamp = conv.last_updated
    import time
    time.sleep(0.001)  # Ensure time difference
    conv.add_message(MessageRole.ASSISTANT, "Hi there")
    assert conv.last_updated > old_timestamp
    
    # Test get_last_message
    last_msg = conv.get_last_message()
    assert last_msg.role == MessageRole.ASSISTANT
    assert last_msg.content == "Hi there"
    
    # Test get_context_window
    for i in range(10):
        conv.add_message(MessageRole.USER, f"Message {i}")
    
    context = conv.get_context_window(n=5)
    assert len(context) == 5
    assert context[0].content == "Message 6"
    assert context[4].content == "Message 10"

def test_state_validator():
    """Test StateValidator methods."""
    validator = StateValidator()
    
    # Test task transition validation
    assert validator.validate_task_transition(TaskStatus.PENDING, TaskStatus.IN_PROGRESS) is True
    assert validator.validate_task_transition(TaskStatus.PENDING, TaskStatus.FAILED) is True
    assert validator.validate_task_transition(TaskStatus.PENDING, TaskStatus.COMPLETED) is False
    
    assert validator.validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED) is True
    assert validator.validate_task_transition(TaskStatus.IN_PROGRESS, TaskStatus.FAILED) is True
    
    assert validator.validate_task_transition(TaskStatus.COMPLETED, TaskStatus.PENDING) is False
    assert validator.validate_task_transition(TaskStatus.FAILED, TaskStatus.PENDING) is True
    
    # Test message sequence validation
    now = datetime.now()
    msgs = [
        Message(role=MessageRole.USER, content="First", created_at=now),
        Message(role=MessageRole.ASSISTANT, content="Second", created_at=now + timedelta(seconds=1)),
        Message(role=MessageRole.USER, content="Third", created_at=now + timedelta(seconds=2))
    ]
    assert validator.validate_message_sequence(msgs) is True
    
    # Test out of order messages
    msgs_out_of_order = [
        Message(role=MessageRole.USER, content="First", created_at=now),
        Message(role=MessageRole.ASSISTANT, content="Second", created_at=now - timedelta(seconds=1)),
    ]
    assert validator.validate_message_sequence(msgs_out_of_order) is False
    
    # Test agent state validation
    valid_state = {"status": "running", "progress": 50}
    assert validator.validate_agent_state("agent1", valid_state) is True
    
    invalid_state = {"progress": 50}  # Missing 'status'
    assert validator.validate_agent_state("agent2", invalid_state) is False

def test_create_initial_state():
    """Test creation of initial GraphState."""
    state = create_initial_state()
    
    assert state["messages"] == []
    assert isinstance(state["conversation_state"], ConversationState)
    assert state["agent_states"] == {}
    assert state["current_task"] is None
    assert state["task_history"] == []
    assert state["agent_results"] == {}
    assert state["final_result"] is None

def test_update_agent_state():
    """Test updating agent state in GraphState."""
    state = create_initial_state()
    agent_id = "test_agent"
    agent_state = {"status": "running", "progress": 0}
    
    # Initial update
    updated_state = update_agent_state(state, agent_id, agent_state)
    assert updated_state["agent_states"][agent_id] == agent_state
    
    # Update existing
    new_update = {"progress": 50}
    updated_state = update_agent_state(updated_state, agent_id, new_update)
    assert updated_state["agent_states"][agent_id]["status"] == "running"
    assert updated_state["agent_states"][agent_id]["progress"] == 50

def test_add_task_to_history():
    """Test adding task to history."""
    state = create_initial_state()
    task = "test_task"
    
    updated_state = add_task_to_history(state, task)
    assert len(updated_state["task_history"]) == 1
    assert task in updated_state["task_history"][0]
    
    # Check timestamp format
    task_entry = updated_state["task_history"][0]
    timestamp = task_entry.split(": ")[0]
    try:
        datetime.fromisoformat(timestamp)
    except ValueError:
        pytest.fail("Task history timestamp is not in ISO format")

def test_state_manager_update_conversation():
    """Test StateManager.update_conversation method."""
    state = create_initial_state()
    manager = StateManager(state)
    
    # Add a valid message
    message = manager.update_conversation(MessageRole.USER, "Hello")
    assert message in manager.state["messages"]
    assert message in manager.state["conversation_state"].messages
    assert message.role == MessageRole.USER
    assert message.content == "Hello"
    
    # Add another message
    manager.update_conversation(MessageRole.ASSISTANT, "Hi there")
    assert len(manager.state["messages"]) == 2
    assert len(manager.state["conversation_state"].messages) == 2
    
    # Test with metadata
    metadata = {"source": "web"}
    message = manager.update_conversation(MessageRole.USER, "Another message", metadata)
    assert message.metadata == metadata

def test_state_manager_update_agent_state():
    """Test StateManager.update_agent_state method."""
    state = create_initial_state()
    manager = StateManager(state)
    
    # Update agent state
    agent_id = "test_agent"
    status = {"status": "running", "progress": 0}
    manager.update_agent_state(agent_id, status)
    
    assert agent_id in manager.state["agent_states"]
    assert manager.state["agent_states"][agent_id] == status
    
    # Update existing agent
    manager.update_agent_state(agent_id, {"progress": 50})
    assert manager.state["agent_states"][agent_id]["status"] == "running"
    assert manager.state["agent_states"][agent_id]["progress"] == 50
    
    # Test invalid agent state
    with pytest.raises(ValidationError):
        manager.update_agent_state(agent_id, {})  # Missing required 'status'

def test_state_manager_set_task():
    """Test StateManager.set_task method."""
    state = create_initial_state()
    manager = StateManager(state)
    
    # Set a task
    task = "test_task"
    manager.set_task(task)
    
    assert manager.state["current_task"] == task
    assert len(manager.state["task_history"]) == 1
    assert task in manager.state["task_history"][0]
    assert manager.state["conversation_state"].current_task_status == TaskStatus.IN_PROGRESS
    
    # Test invalid transition
    manager.state["conversation_state"].current_task_status = TaskStatus.COMPLETED
    with pytest.raises(StateTransitionError):
        manager.set_task("another_task")

def test_state_manager_complete_task():
    """Test StateManager.complete_task method."""
    state = create_initial_state()
    manager = StateManager(state)
    
    # Setup test
    task = "test_task"
    manager.set_task(task)
    result = "task result"
    
    # Complete the task
    manager.complete_task(result)
    
    assert manager.state["current_task"] is None
    assert manager.state["conversation_state"].current_task_status == TaskStatus.COMPLETED
    assert manager.state["agent_results"][task] == result
    
    # Test completing without active task
    with pytest.raises(StateError):
        manager.complete_task("another result")

def test_state_manager_fail_task():
    """Test StateManager.fail_task method."""
    state = create_initial_state()
    manager = StateManager(state)
    
    # Setup test
    task = "test_task"
    manager.set_task(task)
    error = "task error"
    
    # Fail the task
    manager.fail_task(error)
    
    assert manager.state["current_task"] is None
    assert manager.state["conversation_state"].current_task_status == TaskStatus.FAILED
    assert manager.state["agent_results"][task]["error"] == error
    
    # Test failing without active task
    with pytest.raises(StateError):
        manager.fail_task("another error")

def test_state_manager_rate_limiting():
    """Test StateManager rate limiting."""
    state = create_initial_state()
    manager = StateManager(state)
    
    # Test rapid updates (this should not trigger rate limit)
    for i in range(5):
        manager.update_conversation(MessageRole.USER, f"Message {i}")
    
    # Force rate limit triggering by manipulating internal state
    manager._update_count = 101
    manager._last_update = datetime.now()
    
    # This should raise a rate limit error
    with pytest.raises(StateUpdateError):
        manager.update_conversation(MessageRole.USER, "Rate limited message")

def test_state_manager_get_methods():
    """Test StateManager getter methods."""
    state = create_initial_state()
    manager = StateManager(state)
    
    # Setup test data
    agent_id = "test_agent"
    manager.update_agent_state(agent_id, {"status": "running"})
    manager.update_conversation(MessageRole.USER, "Message 1")
    manager.update_conversation(MessageRole.ASSISTANT, "Response 1")
    
    # Test get_agent_state
    agent_state = manager.get_agent_state(agent_id)
    assert agent_state["status"] == "running"
    
    # Test get_conversation_context
    context = manager.get_conversation_context(2)
    assert len(context) == 2
    assert context[0].content == "Message 1"
    assert context[1].content == "Response 1"
    
    # Test get_task_history
    manager.set_task("test_task")
    history = manager.get_task_history()
    assert len(history) == 1
    assert "test_task" in history[0]
    
    # Test get_error_stats
    stats = manager.get_error_stats()
    assert "error_count" in stats
    assert "update_count" in stats
    
    # Test get_current_state
    current_state = manager.get_current_state()
    assert current_state == manager.state 