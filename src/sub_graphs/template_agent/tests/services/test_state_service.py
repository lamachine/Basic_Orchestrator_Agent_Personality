"""
Unit tests for the state service.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from ...src.common.services.state_service import StateService
from ...src.common.models.state_models import GraphState, Message, MessageType, MessageStatus
from ...src.common.models.service_models import StateServiceConfig

@pytest.fixture
def config() -> StateServiceConfig:
    """Create a test configuration."""
    return StateServiceConfig(
        name="test_state_service",
        enabled=True,
        config={
            "max_state_history": 5
        }
    )

@pytest.fixture
def db_service(mocker):
    """Create a mock database service."""
    mock = mocker.Mock()
    mock.insert = mocker.AsyncMock()
    mock.select = mocker.AsyncMock()
    return mock

@pytest.fixture
def state_service(config: StateServiceConfig, db_service) -> StateService:
    """Create a test state service."""
    return StateService(config, db_service)

def test_create_state(state_service: StateService):
    """Test creating a new state."""
    state = state_service.create_state("test_session", "test_user")
    
    assert isinstance(state, GraphState)
    assert state.session_id == "test_session"
    assert state.user_id == "test_user"
    assert len(state.messages) == 0
    assert isinstance(state.created_at, datetime)
    assert isinstance(state.updated_at, datetime)
    
    # Check that state was set as current
    assert state_service.get_current_state() == state
    assert len(state_service.get_state_history()) == 1

def test_update_state(state_service: StateService):
    """Test updating state."""
    # Create initial state
    initial_state = state_service.create_state("test_session")
    
    # Create new state with a message
    message = Message(
        request_id="test_request",
        type=MessageType.REQUEST,
        status=MessageStatus.COMPLETED,
        timestamp=datetime.now(),
        content="Test message"
    )
    
    new_state = GraphState(
        session_id="test_session",
        user_id="test_user",
        messages=[message],
        metadata={"test": "value"},
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    state_service.update_state(new_state)
    
    # Check that state was updated
    current_state = state_service.get_current_state()
    assert current_state == new_state
    assert len(current_state.messages) == 1
    assert current_state.messages[0].content == "Test message"
    assert current_state.metadata["test"] == "value"
    
    # Check history
    history = state_service.get_state_history()
    assert len(history) == 2
    assert history[0] == initial_state
    assert history[1] == new_state

def test_state_history_limit(state_service: StateService):
    """Test state history limit."""
    # Create more states than the limit
    for i in range(10):
        state = state_service.create_state(f"test_session_{i}")
        state_service.update_state(state)
    
    # Check that history is limited
    history = state_service.get_state_history()
    assert len(history) == 5  # From config fixture
    
    # Check that oldest states were removed
    session_ids = [state.session_id for state in history]
    assert "test_session_0" not in session_ids
    assert "test_session_9" in session_ids

@pytest.mark.asyncio
async def test_persist_state(state_service: StateService, db_service):
    """Test persisting state."""
    # Create test state
    state = state_service.create_state("test_session")
    
    # Mock database response
    db_service.insert.return_value = {"id": 1}
    
    # Persist state
    success = await state_service.persist_state()
    assert success
    
    # Check database call
    db_service.insert.assert_called_once()
    call_args = db_service.insert.call_args[1]
    assert call_args["table_name"] == "graph_states"
    assert call_args["data"]["session_id"] == "test_session"

@pytest.mark.asyncio
async def test_restore_state(state_service: StateService, db_service):
    """Test restoring state."""
    # Mock database response
    test_message = {
        "request_id": "test_request",
        "type": MessageType.REQUEST.value,
        "status": MessageStatus.COMPLETED.value,
        "timestamp": datetime.now().isoformat(),
        "content": "Test message",
        "data": {},
        "metadata": {}
    }
    
    db_service.select.return_value = [{
        "session_id": "test_session",
        "user_id": "test_user",
        "messages": [test_message],
        "metadata": {"test": "value"},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }]
    
    # Restore state
    state = await state_service.restore_state("test_session")
    assert state is not None
    assert state.session_id == "test_session"
    assert state.user_id == "test_user"
    assert len(state.messages) == 1
    assert state.messages[0].content == "Test message"
    assert state.metadata["test"] == "value"
    
    # Check database call
    db_service.select.assert_called_once()
    call_args = db_service.select.call_args[1]
    assert call_args["table_name"] == "graph_states"
    assert call_args["filters"]["session_id"] == "test_session"

def test_get_stats(state_service: StateService):
    """Test getting service statistics."""
    stats = state_service.get_stats()
    assert isinstance(stats, dict)
    assert "has_current_state" in stats
    assert "history_size" in stats
    assert "max_history" in stats
    assert stats["max_history"] == 5  # From config fixture 