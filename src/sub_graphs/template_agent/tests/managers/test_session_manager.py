"""
Tests for session_manager.py

This module tests the session management functionality, including:
1. Session creation and initialization
2. Session validation
3. Session persistence and retrieval
4. Error handling
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from ...src.common.managers.session_manager import SessionManager
from ...src.common.managers.service_models import ServiceConfig
from ...src.common.services.db_service import DBService


@pytest.fixture
def service_config():
    """Create a service configuration for testing."""
    config = MagicMock(spec=ServiceConfig)
    config.enabled = True
    config.get_merged_config = MagicMock(return_value={
        "name": "session_service",
        "max_session_age_hours": 24,
        "cleanup_interval_minutes": 60
    })
    return config


@pytest.fixture
def mock_db_service():
    """Create a mock database service."""
    mock_db = AsyncMock(spec=DBService)
    mock_db.create = AsyncMock(return_value={"id": str(uuid.uuid4())})
    mock_db.get = AsyncMock(return_value={
        "id": "test-session-id",
        "user_id": "test-user",
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
        "metadata": {"source": "test"},
        "data": {"context": "test context"}
    })
    mock_db.update = AsyncMock(return_value={"id": "test-session-id", "updated": True})
    mock_db.delete = AsyncMock(return_value={"success": True})
    mock_db.query = AsyncMock(return_value={"data": [
        {
            "id": "session-1",
            "user_id": "user-1",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        },
        {
            "id": "session-2",
            "user_id": "user-2",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
    ]})
    return mock_db


@pytest.fixture
def session_manager(service_config, mock_db_service):
    """Create a session manager with mocked services."""
    manager = SessionManager(service_config, mock_db_service)
    return manager


@pytest.mark.asyncio
async def test_create_session(session_manager):
    """Test creating a new session."""
    # Test case: Normal operation - should pass
    session = await session_manager.create_session("test-user", {"source": "api"})
    
    # Verify session was created
    assert session is not None
    assert "id" in session
    
    # Verify db_service.create was called correctly
    session_manager.db_service.create.assert_called_once()
    call_args = session_manager.db_service.create.call_args[0][0]
    assert call_args == "sessions"
    call_data = session_manager.db_service.create.call_args[0][1]
    assert call_data["user_id"] == "test-user"
    assert call_data["metadata"]["source"] == "api"
    assert "created_at" in call_data
    assert "last_activity" in call_data


@pytest.mark.asyncio
async def test_get_session(session_manager):
    """Test retrieving a session."""
    # Test case: Normal operation - should pass
    session = await session_manager.get_session("test-session-id")
    
    # Verify session was retrieved
    assert session is not None
    assert session["id"] == "test-session-id"
    assert session["user_id"] == "test-user"
    assert "created_at" in session
    assert "last_activity" in session
    assert session["metadata"]["source"] == "test"
    assert session["data"]["context"] == "test context"
    
    # Verify db_service.get was called correctly
    session_manager.db_service.get.assert_called_once_with(
        "sessions", "test-session-id"
    )


@pytest.mark.asyncio
async def test_get_session_not_found(session_manager):
    """Test retrieving a non-existent session."""
    # Test case: Error condition - should fail but handle gracefully
    session_manager.db_service.get.return_value = None
    
    # Get session
    session = await session_manager.get_session("nonexistent-session")
    
    # Verify session is None
    assert session is None
    
    # Verify db_service.get was called
    session_manager.db_service.get.assert_called_once()


@pytest.mark.asyncio
async def test_update_session(session_manager):
    """Test updating a session."""
    # Test case: Normal operation - should pass
    result = await session_manager.update_session(
        "test-session-id",
        {"context": "updated context"}
    )
    
    # Verify update was successful
    assert result is not None
    assert result["id"] == "test-session-id"
    assert result["updated"] is True
    
    # Verify db_service.update was called correctly
    session_manager.db_service.update.assert_called_once()
    call_args = session_manager.db_service.update.call_args[0]
    assert call_args[0] == "sessions"
    assert call_args[1] == "test-session-id"
    assert "data" in call_args[2]
    assert call_args[2]["data"]["context"] == "updated context"
    assert "last_activity" in call_args[2]


@pytest.mark.asyncio
async def test_update_session_not_found(session_manager):
    """Test updating a non-existent session."""
    # Test case: Error condition - should fail but handle gracefully
    session_manager.db_service.update.return_value = None
    
    # Update session
    result = await session_manager.update_session(
        "nonexistent-session",
        {"context": "updated context"}
    )
    
    # Verify result is None
    assert result is None
    
    # Verify db_service.update was called
    session_manager.db_service.update.assert_called_once()


@pytest.mark.asyncio
async def test_delete_session(session_manager):
    """Test deleting a session."""
    # Test case: Normal operation - should pass
    result = await session_manager.delete_session("test-session-id")
    
    # Verify deletion was successful
    assert result is not None
    assert result["success"] is True
    
    # Verify db_service.delete was called correctly
    session_manager.db_service.delete.assert_called_once_with(
        "sessions", "test-session-id"
    )


@pytest.mark.asyncio
async def test_delete_session_not_found(session_manager):
    """Test deleting a non-existent session."""
    # Test case: Error condition - should fail but handle gracefully
    session_manager.db_service.delete.return_value = {"success": False, "error": "Session not found"}
    
    # Delete session
    result = await session_manager.delete_session("nonexistent-session")
    
    # Verify result indicates failure
    assert result is not None
    assert result["success"] is False
    assert "error" in result
    
    # Verify db_service.delete was called
    session_manager.db_service.delete.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_sessions(session_manager):
    """Test retrieving all sessions for a user."""
    # Test case: Normal operation - should pass
    sessions = await session_manager.get_user_sessions("user-1")
    
    # Verify sessions were retrieved
    assert sessions is not None
    assert len(sessions) > 0
    
    # Verify db_service.query was called correctly
    session_manager.db_service.query.assert_called_once()
    call_args = session_manager.db_service.query.call_args[0]
    assert call_args[0] == "sessions"
    assert "user_id" in call_args[1]
    assert call_args[1]["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_get_user_sessions_no_sessions(session_manager):
    """Test retrieving sessions for a user with no sessions."""
    # Test case: Edge case - user with no sessions
    session_manager.db_service.query.return_value = {"data": []}
    
    # Get sessions
    sessions = await session_manager.get_user_sessions("user-no-sessions")
    
    # Verify empty list was returned
    assert sessions is not None
    assert len(sessions) == 0
    
    # Verify db_service.query was called
    session_manager.db_service.query.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_sessions(session_manager):
    """Test retrieving all active sessions."""
    # Test case: Normal operation - should pass
    sessions = await session_manager.get_active_sessions()
    
    # Verify sessions were retrieved
    assert sessions is not None
    assert len(sessions) > 0
    
    # Verify db_service.query was called correctly
    session_manager.db_service.query.assert_called_once()
    call_args = session_manager.db_service.query.call_args[0]
    assert call_args[0] == "sessions"


@pytest.mark.asyncio
async def test_is_session_valid(session_manager):
    """Test validating a session."""
    # Create a mock session
    active_session = {
        "id": "active-session",
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat()
    }
    
    expired_session = {
        "id": "expired-session",
        "created_at": (datetime.now() - timedelta(hours=48)).isoformat(),
        "last_activity": (datetime.now() - timedelta(hours=48)).isoformat()
    }
    
    # Test case: Normal operation - valid session
    is_valid = session_manager.is_session_valid(active_session)
    assert is_valid is True
    
    # Test case: Error condition - expired session
    is_valid = session_manager.is_session_valid(expired_session)
    assert is_valid is False
    
    # Test case: Edge case - missing timestamps
    incomplete_session = {"id": "incomplete-session"}
    is_valid = session_manager.is_session_valid(incomplete_session)
    assert is_valid is False


@pytest.mark.asyncio
async def test_clean_expired_sessions(session_manager):
    """Test cleaning expired sessions."""
    # Mock expired sessions query result
    mock_expired_result = {"data": [
        {"id": "expired-1", "user_id": "user-1"},
        {"id": "expired-2", "user_id": "user-2"}
    ]}
    session_manager.db_service.query.return_value = mock_expired_result
    
    # Test case: Normal operation - should pass
    await session_manager.clean_expired_sessions()
    
    # Verify query was made to find expired sessions
    session_manager.db_service.query.assert_called_once()
    
    # Verify delete was called for each expired session
    assert session_manager.db_service.delete.call_count == 2
    session_manager.db_service.delete.assert_any_call("sessions", "expired-1")
    session_manager.db_service.delete.assert_any_call("sessions", "expired-2")


@pytest.mark.asyncio
async def test_clean_expired_sessions_none_expired(session_manager):
    """Test cleaning expired sessions when none are expired."""
    # Mock no expired sessions
    session_manager.db_service.query.return_value = {"data": []}
    
    # Test case: Edge case - no expired sessions
    await session_manager.clean_expired_sessions()
    
    # Verify query was made
    session_manager.db_service.query.assert_called_once()
    
    # Verify delete was not called
    session_manager.db_service.delete.assert_not_called()


@pytest.mark.asyncio
async def test_get_session_data(session_manager):
    """Test retrieving session data."""
    # Set up mock session with data
    mock_session = {
        "id": "test-session",
        "data": {
            "context": "test context",
            "messages": ["msg1", "msg2"],
            "nested": {"key": "value"}
        }
    }
    session_manager.get_session = AsyncMock(return_value=mock_session)
    
    # Test case: Normal operation - should pass
    data = await session_manager.get_session_data("test-session")
    
    # Verify data was retrieved correctly
    assert data is not None
    assert data["context"] == "test context"
    assert len(data["messages"]) == 2
    assert data["nested"]["key"] == "value"
    
    # Test case: Getting specific key
    context = await session_manager.get_session_data("test-session", "context")
    assert context == "test context"
    
    # Test case: Getting nested key
    nested_key = await session_manager.get_session_data("test-session", "nested.key")
    assert nested_key == "value"
    
    # Test case: Edge case - key not found
    missing_key = await session_manager.get_session_data("test-session", "missing_key")
    assert missing_key is None
    
    # Test case: Edge case - invalid nested key
    invalid_key = await session_manager.get_session_data("test-session", "context.invalid")
    assert invalid_key is None


@pytest.mark.asyncio
async def test_get_session_data_session_not_found(session_manager):
    """Test retrieving data for a non-existent session."""
    # Mock get_session to return None
    session_manager.get_session = AsyncMock(return_value=None)
    
    # Test case: Error condition - session not found
    data = await session_manager.get_session_data("nonexistent-session")
    
    # Verify None was returned
    assert data is None 