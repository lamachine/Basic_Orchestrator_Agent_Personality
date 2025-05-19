"""
Tests for state_manager.py

This module tests the StateManager class, including:
1. Session management
2. Message handling
3. Task management
4. Agent state management
5. Persistence operations
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ...src.common.state.state_errors import (
    AgentStateError,
    MessageError,
    PersistenceError,
    StateError,
    StateTransitionError,
    StateUpdateError,
    TaskError,
    ValidationError,
)
from ...src.common.state.state_manager import StateManager
from ...src.common.state.state_models import (
    GraphState,
    Message,
    MessageRole,
    MessageState,
    MessageStatus,
    MessageType,
    TaskStatus,
)


@pytest.fixture
async def state_manager():
    """Create a StateManager instance for testing."""
    manager = StateManager()
    yield manager


@pytest.fixture
async def state_manager_with_db():
    """Create a StateManager instance with mock DB for testing."""
    mock_db = MagicMock()
    mock_db.message_manager = AsyncMock()
    mock_db.message_manager.add_message = AsyncMock()
    mock_db.save_session = AsyncMock()
    mock_db.get_all_sessions = AsyncMock(return_value=[])

    manager = StateManager(db_manager=mock_db)
    yield manager, mock_db


@pytest.mark.asyncio
async def test_get_session(state_manager):
    """Test getting a session."""
    # Test case: Normal operation - should create and return a session
    session = await state_manager.get_session("1")

    assert isinstance(session, MessageState)
    assert session.session_id == 1
    assert session.messages == []
    assert session.current_task is None
    assert session.current_task_status is None

    # Verify the session is stored
    assert 1 in state_manager.sessions

    # Test case: Normal operation - should return existing session
    same_session = await state_manager.get_session("1")
    assert same_session is session  # Should be the same object


@pytest.mark.asyncio
async def test_update_session(state_manager):
    """Test updating a session with a new message."""
    # Test case: Normal operation - should add a message
    session = await state_manager.update_session(
        session_id="1",
        role=MessageRole.USER,
        content="Test message",
        metadata={"source": "test"},
        sender="user",
        target="assistant",
    )

    assert len(session.messages) == 1
    assert session.messages[0].role == MessageRole.USER
    assert session.messages[0].content == "Test message"
    assert session.messages[0].metadata == {"source": "test"}

    # Test case: Normal operation - should add an assistant message
    session = await state_manager.update_session(
        session_id="1",
        role=MessageRole.ASSISTANT,
        content="Response message",
        sender="assistant",
        target="user",
    )

    assert len(session.messages) == 2
    assert session.messages[1].role == MessageRole.ASSISTANT
    assert session.messages[1].content == "Response message"

    # Test case: Error condition - consecutive user messages should fail
    with pytest.raises(StateUpdateError, match="Cannot have two consecutive user messages"):
        await state_manager.update_session(
            session_id="2",
            role=MessageRole.USER,
            content="First user message",
            sender="user",
            target="assistant",
        )

        await state_manager.update_session(
            session_id="2",
            role=MessageRole.USER,
            content="Second user message",
            sender="user",
            target="assistant",
        )

    # Test case: Error condition - consecutive assistant messages should fail
    with pytest.raises(StateUpdateError, match="Cannot have two consecutive assistant messages"):
        await state_manager.update_session(
            session_id="3",
            role=MessageRole.ASSISTANT,
            content="First assistant message",
            sender="assistant",
            target="user",
        )

        await state_manager.update_session(
            session_id="3",
            role=MessageRole.ASSISTANT,
            content="Second assistant message",
            sender="assistant",
            target="user",
        )


@pytest.mark.asyncio
async def test_get_all_sessions(state_manager):
    """Test getting all sessions."""
    # Create a few sessions
    await state_manager.get_session("1")
    await state_manager.get_session("2")
    await state_manager.get_session("3")

    # Test case: Normal operation - should return all sessions
    sessions = await state_manager.get_all_sessions()

    assert len(sessions) == 3
    assert all(isinstance(session, MessageState) for session in sessions)
    assert {session.session_id for session in sessions} == {1, 2, 3}


@pytest.mark.asyncio
async def test_update_agent_state(state_manager):
    """Test updating agent state."""
    # Test case: Normal operation - should update agent state
    await state_manager.update_agent_state(
        session_id="1", agent_id="agent1", status={"status": "active"}
    )

    session = await state_manager.get_session("1")
    assert "agent_states" in session.conversation_state
    assert "agent1" in session.conversation_state["agent_states"]
    assert session.conversation_state["agent_states"]["agent1"]["status"] == "active"

    # Test case: Normal operation - should update existing agent state
    await state_manager.update_agent_state(
        session_id="1",
        agent_id="agent1",
        status={"status": "idle", "last_action": "query"},
    )

    session = await state_manager.get_session("1")
    assert session.conversation_state["agent_states"]["agent1"]["status"] == "idle"
    assert session.conversation_state["agent_states"]["agent1"]["last_action"] == "query"

    # Test case: Error condition - invalid agent state should fail
    with pytest.raises(ValidationError, match="Invalid agent state structure"):
        await state_manager.update_agent_state(
            session_id="1",
            agent_id="agent2",
            status={"not_status": "invalid"},  # Missing required 'status' field
        )


@pytest.mark.asyncio
async def test_task_management(state_manager):
    """Test task management."""
    # Prepare a session
    session = await state_manager.get_session("1")

    # Test case: Normal operation - should start a task
    await state_manager.start_task(session_id="1", task="test_task")

    session = await state_manager.get_session("1")
    assert session.current_task == "test_task"
    assert session.current_task_status == TaskStatus.IN_PROGRESS

    # Test case: Normal operation - should complete a task
    await state_manager.complete_task(session_id="1", result={"success": True})

    session = await state_manager.get_session("1")
    assert session.current_task_status == TaskStatus.COMPLETED
    assert session.conversation_state["task_results"] == {"success": True}

    # Test case: Error condition - starting a task from COMPLETED should fail
    with pytest.raises(StateTransitionError, match="Invalid task transition"):
        await state_manager.start_task(session_id="1", task="another_task")

    # Test case: Error condition - completing a task without starting one should fail
    await state_manager.get_session("2")  # Create a new session without tasks
    with pytest.raises(TaskError, match="No active task to complete"):
        await state_manager.complete_task(session_id="2", result={"success": True})

    # Test case: Start new task, then fail it
    await state_manager.get_session("3")  # Create a new session
    await state_manager.start_task(session_id="3", task="failing_task")

    # Test case: Normal operation - should fail a task
    await state_manager.fail_task(session_id="3", error="Something went wrong")

    session = await state_manager.get_session("3")
    assert session.current_task_status == TaskStatus.FAILED
    assert session.conversation_state["task_error"] == "Something went wrong"


@pytest.mark.asyncio
async def test_rate_limiting(state_manager):
    """Test rate limiting."""
    # Test case: Edge case - rapid updates should eventually fail
    state_manager._update_count = 99  # Set close to limit

    # One more should work
    await state_manager.get_session("1")

    # Force _last_update to be recent
    state_manager._last_update = datetime.now()

    # Next one should fail due to rate limiting
    with pytest.raises(StateUpdateError, match="Too many rapid state updates"):
        await state_manager.get_session("2")


@pytest.mark.asyncio
async def test_get_error_stats(state_manager):
    """Test getting error statistics."""
    # Initialize with some error counts
    state_manager._error_count = 5
    state_manager._update_count = 10

    # Test case: Normal operation - should return error stats
    stats = await state_manager.get_error_stats()

    assert stats["error_count"] == 5
    assert stats["update_count"] == 10


@pytest.mark.asyncio
async def test_get_agent_state(state_manager):
    """Test getting agent state."""
    # Set up agent state
    await state_manager.update_agent_state(
        session_id="1", agent_id="agent1", status={"status": "active", "data": "test"}
    )

    # Test case: Normal operation - should get agent state
    agent_state = await state_manager.get_agent_state(session_id="1", agent_id="agent1")

    assert agent_state["status"] == "active"
    assert agent_state["data"] == "test"

    # Test case: Edge case - nonexistent agent should return empty dict
    agent_state = await state_manager.get_agent_state(session_id="1", agent_id="nonexistent")

    assert agent_state == {}


@pytest.mark.asyncio
async def test_get_session_context(state_manager):
    """Test getting session context."""
    # Create a session with messages
    session = await state_manager.get_session("1")
    for i in range(10):
        await session.add_message(
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {i}",
            sender="user" if i % 2 == 0 else "assistant",
            target="assistant" if i % 2 == 0 else "user",
        )

    # Test case: Normal operation - should get default context window (5 messages)
    context = await state_manager.get_session_context(session_id="1")

    assert len(context) == 5
    assert context[0].content == "Message 5"
    assert context[4].content == "Message 9"

    # Test case: Normal operation - should get custom context window
    context = await state_manager.get_session_context(session_id="1", window_size=3)

    assert len(context) == 3
    assert context[0].content == "Message 7"
    assert context[2].content == "Message 9"


@pytest.mark.asyncio
async def test_persistence(state_manager_with_db):
    """Test state persistence."""
    state_manager, mock_db = state_manager_with_db

    # Create and populate a session
    await state_manager.get_session("1")

    # Test case: Normal operation - should persist state
    await state_manager.persist_state()

    # Verify DB manager was called
    mock_db.save_session.assert_called_once()

    # Test case: Normal operation - should load state
    await state_manager.load_state()

    # Verify DB manager was called
    mock_db.get_all_sessions.assert_called_once()

    # Test case: Error condition - persistence failure should raise PersistenceError
    mock_db.save_session.side_effect = Exception("DB error")

    with pytest.raises(PersistenceError, match="Failed to persist state"):
        await state_manager.persist_state()


@pytest.mark.asyncio
async def test_edge_cases(state_manager):
    """Test edge cases for state manager."""
    # Test case: Edge case - empty content
    session = await state_manager.update_session(
        session_id="1",
        role=MessageRole.USER,
        content="",  # Empty but valid
        sender="user",
        target="assistant",
    )
    assert session.messages[0].content == ""

    # Test case: Edge case - very long message
    long_content = "A" * 10000  # 10KB content
    session = await state_manager.update_session(
        session_id="2",
        role=MessageRole.USER,
        content=long_content,
        sender="user",
        target="assistant",
    )
    assert len(session.messages[0].content) == 10000

    # Test case: Edge case - complex metadata
    complex_metadata = {
        "user": {
            "id": "user123",
            "preferences": {"theme": "dark", "notifications": True},
        },
        "request": {
            "id": "req456",
            "timestamp": datetime.now().isoformat(),
            "parameters": ["param1", "param2", "param3"],
        },
    }

    session = await state_manager.update_session(
        session_id="3",
        role=MessageRole.USER,
        content="Test message",
        metadata=complex_metadata,
        sender="user",
        target="assistant",
    )
    assert session.messages[0].metadata["user"]["preferences"]["theme"] == "dark"
    assert session.messages[0].metadata["request"]["parameters"][1] == "param2"
