"""
Unit tests for the session service.
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest

from ...src.common.config import SessionServiceConfig
from ...src.common.services.session_service import SessionService
from ...src.common.state.state_models import Message, MessageStatus, MessageType


@pytest.fixture
def config() -> SessionServiceConfig:
    """Create a test configuration."""
    return SessionServiceConfig(
        name="test_session_service",
        enabled=True,
        config={"max_sessions": 100, "session_timeout": 3600},
    )


@pytest.fixture
def mock_db_service(mocker):
    """Create a mock database service."""
    mock_service = mocker.Mock()
    mock_service.get_next_id = mocker.AsyncMock(return_value=1)
    mock_service.insert = mocker.AsyncMock()
    mock_service.select = mocker.AsyncMock()
    mock_service.update = mocker.AsyncMock()
    mock_service.delete_records = mocker.AsyncMock()
    return mock_service


@pytest.fixture
def session_service(config: SessionServiceConfig, mock_db_service):
    """Create a test session service."""
    return SessionService(config, mock_db_service)


def test_initialization(session_service: SessionService):
    """Test service initialization."""
    assert session_service.is_connected
    assert session_service.active_sessions == {}
    assert session_service.session_count == 0


@pytest.mark.asyncio
async def test_create_session(session_service: SessionService, mock_db_service):
    """Test creating a new session."""
    # Mock database responses
    mock_db_service.insert.return_value = {
        "id": 1,
        "session_id": "test_session",
        "user_id": "test_user",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    # Create session
    session = await session_service.create_session("test_user")
    assert session["session_id"] == "test_session"
    assert session["user_id"] == "test_user"
    assert "created_at" in session
    assert "updated_at" in session

    # Check database calls
    mock_db_service.get_next_id.assert_called_once()
    assert mock_db_service.insert.call_count == 2  # Session and initial message


@pytest.mark.asyncio
async def test_get_recent_sessions(session_service: SessionService, mock_db_service):
    """Test getting recent sessions."""
    # Mock database response
    mock_db_service.select.return_value = [
        {
            "id": 1,
            "session_id": "test_session",
            "user_id": "test_user",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    ]

    # Get sessions
    sessions = await session_service.get_recent_sessions("test_user", limit=10)
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "test_session"

    # Check database call
    mock_db_service.select.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_details(session_service: SessionService, mock_db_service):
    """Test getting session details."""
    # Mock database response
    mock_db_service.select.return_value = [
        {
            "id": 1,
            "session_id": "test_session",
            "user_id": "test_user",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    ]

    # Get session details
    session = await session_service.get_session_details("test_session")
    assert session["session_id"] == "test_session"
    assert session["user_id"] == "test_user"

    # Check database call
    mock_db_service.select.assert_called_once()


@pytest.mark.asyncio
async def test_search_sessions(session_service: SessionService, mock_db_service):
    """Test searching sessions."""
    # Mock database response
    mock_db_service.select.return_value = [
        {
            "id": 1,
            "session_id": "test_session",
            "user_id": "test_user",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    ]

    # Search sessions
    sessions = await session_service.search_sessions(query="test", user_id="test_user")
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "test_session"

    # Check database call
    mock_db_service.select.assert_called_once()


@pytest.mark.asyncio
async def test_rename_session(session_service: SessionService, mock_db_service):
    """Test renaming a session."""
    # Mock database response
    mock_db_service.update.return_value = [
        {
            "id": 1,
            "session_id": "test_session",
            "user_id": "test_user",
            "name": "New Name",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    ]

    # Rename session
    session = await session_service.rename_session("test_session", "New Name")
    assert session["name"] == "New Name"

    # Check database call
    mock_db_service.update.assert_called_once()


@pytest.mark.asyncio
async def test_end_session(session_service: SessionService, mock_db_service):
    """Test ending a session."""
    # Mock database response
    mock_db_service.update.return_value = [
        {
            "id": 1,
            "session_id": "test_session",
            "user_id": "test_user",
            "ended_at": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    ]

    # End session
    session = await session_service.end_session("test_session")
    assert "ended_at" in session

    # Check database call
    mock_db_service.update.assert_called_once()


@pytest.mark.asyncio
async def test_delete_session(session_service: SessionService, mock_db_service):
    """Test deleting a session."""
    # Mock database response
    mock_db_service.delete_records.return_value = [{"id": 1}]

    # Delete session
    result = await session_service.delete_session("test_session")
    assert result == [{"id": 1}]

    # Check database call
    mock_db_service.delete_records.assert_called_once()


@pytest.mark.asyncio
async def test_get_stats(session_service: SessionService):
    """Test getting service statistics."""
    stats = session_service.get_stats()
    assert isinstance(stats, dict)
    assert "active_sessions" in stats
    assert "session_count" in stats
    assert "max_sessions" in stats
    assert "session_timeout" in stats
