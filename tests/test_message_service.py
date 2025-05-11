"""
Tests for the message service.

These tests validate the message service's ability to handle message persistence,
retrieval, and state management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, Optional

from src.services.message_service import DatabaseMessageService, log_and_persist_message
from src.state.state_models import MessageState, MessageRole
from src.managers.db_manager import DBService

# Test fixtures
@pytest.fixture
def mock_db_service():
    """Create a mock database service."""
    db_service = MagicMock(spec=DBService)
    db_service.insert = AsyncMock(return_value={"id": 1, "status": "success"})
    db_service.get_messages = AsyncMock(return_value=[
        {
            "id": 1,
            "role": "user",
            "content": "test message",
            "metadata": {"user_id": "test_user"},
            "timestamp": datetime.now().isoformat()
        }
    ])
    db_service.search_messages = AsyncMock(return_value=[
        {
            "id": 1,
            "role": "user",
            "content": "test message",
            "metadata": {"user_id": "test_user"},
            "timestamp": datetime.now().isoformat()
        }
    ])
    db_service.delete_records = AsyncMock(return_value=True)
    return db_service

@pytest.fixture
def message_service(mock_db_service):
    """Create a message service instance with mock dependencies."""
    return DatabaseMessageService(db_service=mock_db_service)

@pytest.fixture
def mock_message_state():
    """Create a mock message state."""
    state = MagicMock(spec=MessageState)
    state.add_message = AsyncMock()
    return state

# Tests for DatabaseMessageService
@pytest.mark.asyncio
async def test_add_message(message_service, mock_db_service):
    """Test adding a message."""
    # Arrange
    session_id = "test_session"
    role = "user"
    content = "test message"
    metadata = {"user_id": "test_user"}
    user_id = "test_user"
    sender = "user"
    target = "assistant"
    
    # Act
    result = await message_service.add_message(
        session_id=session_id,
        role=role,
        content=content,
        metadata=metadata,
        user_id=user_id,
        sender=sender,
        target=target
    )
    
    # Assert
    assert result["status"] == "success"
    mock_db_service.insert.assert_called_once()
    call_args = mock_db_service.insert.call_args[1]
    assert call_args["table"] == "swarm_messages"
    assert call_args["record"]["session_id"] == session_id
    assert call_args["record"]["content"] == content
    assert call_args["record"]["metadata"] == metadata

@pytest.mark.asyncio
async def test_get_messages(message_service, mock_db_service):
    """Test getting messages."""
    # Arrange
    session_id = "test_session"
    user_id = "test_user"
    
    # Act
    messages = await message_service.get_messages(session_id=session_id, user_id=user_id)
    
    # Assert
    assert len(messages) == 1
    assert messages[0]["content"] == "test message"
    mock_db_service.get_messages.assert_called_once_with(
        session_id=int(session_id),
        user_id=user_id
    )

@pytest.mark.asyncio
async def test_search_messages(message_service, mock_db_service):
    """Test searching messages."""
    # Arrange
    query = "test"
    session_id = "test_session"
    user_id = "test_user"
    
    # Act
    messages = await message_service.search_messages(
        query=query,
        session_id=session_id,
        user_id=user_id
    )
    
    # Assert
    assert len(messages) == 1
    assert messages[0]["content"] == "test message"
    mock_db_service.search_messages.assert_called_once_with(
        query=query,
        session_id=int(session_id),
        user_id=user_id
    )

@pytest.mark.asyncio
async def test_delete_messages(message_service, mock_db_service):
    """Test deleting messages."""
    # Arrange
    session_id = "test_session"
    user_id = "test_user"
    
    # Act
    result = await message_service.delete_messages(session_id=session_id, user_id=user_id)
    
    # Assert
    assert result is True
    mock_db_service.delete_records.assert_called_once_with(
        "swarm_messages",
        {"session_id": session_id, "user_id": user_id}
    )

# Tests for log_and_persist_message
@pytest.mark.asyncio
async def test_log_and_persist_message(mock_message_state):
    """Test logging and persisting a message."""
    # Arrange
    role = MessageRole.USER
    content = "test message"
    metadata = {"user_id": "test_user"}
    sender = "user"
    target = "assistant"
    
    # Act
    await log_and_persist_message(
        session_state=mock_message_state,
        role=role,
        content=content,
        metadata=metadata,
        sender=sender,
        target=target
    )
    
    # Assert
    mock_message_state.add_message.assert_called_once_with(
        role=role,
        content=content,
        metadata=metadata,
        sender=sender,
        target=target
    )

@pytest.mark.asyncio
async def test_log_and_persist_message_invalid_state():
    """Test logging and persisting a message with invalid state."""
    # Arrange
    invalid_state = "not a MessageState"
    role = MessageRole.USER
    content = "test message"
    
    # Act & Assert
    with pytest.raises(TypeError):
        await log_and_persist_message(
            session_state=invalid_state,
            role=role,
            content=content,
            sender="user",
            target="assistant"
        )

@pytest.mark.asyncio
async def test_log_and_persist_message_missing_sender_target(mock_message_state):
    """Test logging and persisting a message with missing sender/target."""
    # Arrange
    role = MessageRole.USER
    content = "test message"
    
    # Act & Assert
    with pytest.raises(ValueError):
        await log_and_persist_message(
            session_state=mock_message_state,
            role=role,
            content=content,
            sender=None,
            target=None
        ) 