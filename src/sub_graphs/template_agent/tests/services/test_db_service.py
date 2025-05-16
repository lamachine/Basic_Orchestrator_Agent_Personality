"""
Unit tests for the database service.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from ...src.common.services.db_service import DBService
from ...src.common.models.state_models import Message, MessageType, MessageStatus
from ...src.common.models.service_models import DBServiceConfig

@pytest.fixture
def config() -> DBServiceConfig:
    """Create a test configuration."""
    return DBServiceConfig(
        name="test_db_service",
        enabled=True,
        config={
            "supabase_url": "http://localhost:54321",
            "supabase_key": "test_key"
        }
    )

@pytest.fixture
def db_service(config: DBServiceConfig, mocker):
    """Create a test database service."""
    # Mock Supabase client
    mock_client = mocker.Mock()
    mock_client.from_ = mocker.Mock()
    mock_client.table = mocker.Mock()
    mock_client.rpc = mocker.Mock()
    
    return DBService(config, mock_client)

def test_initialization(db_service: DBService):
    """Test service initialization."""
    assert db_service.is_connected
    assert isinstance(db_service.last_query_time, datetime)
    assert db_service.query_count == 0
    assert db_service.error_count == 0

@pytest.mark.asyncio
async def test_get_next_id(db_service: DBService):
    """Test getting next ID."""
    # Mock response
    mock_response = mocker.Mock()
    mock_response.data = [{"id": 1}, {"id": 2}, {"id": 3}]
    db_service.client.from_.return_value.select.return_value.execute.return_value = mock_response
    
    # Get next ID
    next_id = await db_service.get_next_id("id", "test_table")
    assert next_id == 4
    
    # Check client call
    db_service.client.from_.assert_called_once_with("test_table")
    db_service.client.from_.return_value.select.assert_called_once_with("id")

@pytest.mark.asyncio
async def test_insert(db_service: DBService):
    """Test inserting record."""
    # Mock response
    mock_response = mocker.Mock()
    mock_response.data = [{"id": 1, "name": "test"}]
    db_service.client.table.return_value.insert.return_value.execute.return_value = mock_response
    
    # Insert record
    result = await db_service.insert("test_table", {"name": "test"})
    assert result == {"id": 1, "name": "test"}
    
    # Check client call
    db_service.client.table.assert_called_once_with("test_table")
    db_service.client.table.return_value.insert.assert_called_once_with({"name": "test"})

@pytest.mark.asyncio
async def test_select(db_service: DBService):
    """Test selecting records."""
    # Mock response
    mock_response = mocker.Mock()
    mock_response.data = [{"id": 1, "name": "test"}]
    db_service.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
    
    # Select records
    result = await db_service.select(
        "test_table",
        columns="id, name",
        filters={"name": "test"},
        order_by="id",
        order_desc=True,
        limit=10
    )
    assert result == [{"id": 1, "name": "test"}]
    
    # Check client call
    db_service.client.table.assert_called_once_with("test_table")
    db_service.client.table.return_value.select.assert_called_once_with("id, name")
    db_service.client.table.return_value.select.return_value.eq.assert_called_once_with("name", "test")

@pytest.mark.asyncio
async def test_update(db_service: DBService):
    """Test updating records."""
    # Mock response
    mock_response = mocker.Mock()
    mock_response.data = [{"id": 1, "name": "updated"}]
    db_service.client.table.return_value.eq.return_value.update.return_value.execute.return_value = mock_response
    
    # Update records
    result = await db_service.update(
        "test_table",
        {"name": "updated"},
        {"id": 1}
    )
    assert result == [{"id": 1, "name": "updated"}]
    
    # Check client call
    db_service.client.table.assert_called_once_with("test_table")
    db_service.client.table.return_value.eq.assert_called_once_with("id", 1)

@pytest.mark.asyncio
async def test_delete_records(db_service: DBService):
    """Test deleting records."""
    # Mock response
    mock_response = mocker.Mock()
    mock_response.data = [{"id": 1}]
    db_service.client.table.return_value.eq.return_value.delete.return_value.execute.return_value = mock_response
    
    # Delete records
    result = await db_service.delete_records(
        "test_table",
        {"id": 1}
    )
    assert result == [{"id": 1}]
    
    # Check client call
    db_service.client.table.assert_called_once_with("test_table")
    db_service.client.table.return_value.eq.assert_called_once_with("id", 1)

@pytest.mark.asyncio
async def test_get_messages(db_service: DBService):
    """Test getting messages."""
    # Mock response
    mock_response = mocker.Mock()
    mock_response.data = [{
        "id": 1,
        "type": MessageType.REQUEST.value,
        "content": "Test message",
        "status": MessageStatus.COMPLETED.value,
        "metadata": {"test": "value"},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }]
    db_service.client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
    
    # Get messages
    messages = await db_service.get_messages("test_session", "test_user")
    assert len(messages) == 1
    assert isinstance(messages[0], Message)
    assert messages[0].content == "Test message"
    assert messages[0].metadata["test"] == "value"
    
    # Check client call
    db_service.client.table.assert_called_once_with("messages")
    db_service.client.table.return_value.select.assert_called_once()
    db_service.client.table.return_value.select.return_value.eq.assert_called()

@pytest.mark.asyncio
async def test_search_messages(db_service: DBService):
    """Test searching messages."""
    # Mock response
    mock_response = mocker.Mock()
    mock_response.data = [{
        "id": 1,
        "type": MessageType.REQUEST.value,
        "content": "Test message",
        "status": MessageStatus.COMPLETED.value,
        "metadata": {"test": "value"},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }]
    db_service.client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
    
    # Search messages
    messages = await db_service.search_messages(
        query="test",
        session_id="test_session",
        user_id="test_user"
    )
    assert len(messages) == 1
    assert isinstance(messages[0], Message)
    assert messages[0].content == "Test message"
    
    # Check client call
    db_service.client.table.assert_called_once_with("messages")
    db_service.client.table.return_value.select.assert_called_once()
    db_service.client.table.return_value.select.return_value.eq.assert_called()

@pytest.mark.asyncio
async def test_semantic_message_search(db_service: DBService):
    """Test semantic message search."""
    # Mock response
    mock_response = mocker.Mock()
    mock_response.data = [{
        "id": 1,
        "type": MessageType.REQUEST.value,
        "content": "Test message",
        "status": MessageStatus.COMPLETED.value,
        "metadata": {"test": "value"},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }]
    db_service.client.rpc.return_value.execute.return_value = mock_response
    
    # Search messages
    messages = await db_service.semantic_message_search(
        query="test",
        embedding=[0.1, 0.2, 0.3],
        limit=5
    )
    assert len(messages) == 1
    assert isinstance(messages[0], Message)
    assert messages[0].content == "Test message"
    
    # Check client call
    db_service.client.rpc.assert_called_once_with(
        "match_documents",
        {
            "query_embedding": [0.1, 0.2, 0.3],
            "match_count": 5,
            "filter": None
        }
    )

@pytest.mark.asyncio
async def test_health_check(db_service: DBService):
    """Test health check."""
    # Mock response
    mock_response = mocker.Mock()
    mock_response.data = [{"1": 1}]
    db_service.client.from_.return_value.select.return_value.limit.return_value.execute.return_value = mock_response
    
    # Check health
    health = await db_service.health_check()
    assert isinstance(health, dict)
    assert health["connected"] == True
    assert health["status"] == "healthy"
    assert "last_query" in health
    assert "query_count" in health
    assert "error_count" in health
    
    # Check client call
    db_service.client.from_.assert_called_once_with("health_check")
    db_service.client.from_.return_value.select.assert_called_once_with("1") 