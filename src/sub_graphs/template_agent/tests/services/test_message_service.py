"""
Unit tests for the message service.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from ...src.common.services.message_service import MessageService
from ...src.common.models.state_models import Message, MessageType, MessageStatus
from ...src.common.models.service_models import ServiceConfig

@pytest.fixture
def config() -> ServiceConfig:
    """Create a test configuration."""
    return ServiceConfig(
        name="test_message_service",
        enabled=True,
        config={}
    )

@pytest.fixture
def db_service(mocker):
    """Create a mock database service."""
    mock = mocker.Mock()
    mock.insert = mocker.AsyncMock()
    mock.select = mocker.AsyncMock()
    mock.delete_records = mocker.AsyncMock()
    return mock

@pytest.fixture
def llm_service(mocker):
    """Create a mock LLM service."""
    mock = mocker.Mock()
    mock.get_embedding = mocker.AsyncMock(return_value=[0.0] * 768)
    return mock

@pytest.fixture
def message_service(config: ServiceConfig, db_service, llm_service) -> MessageService:
    """Create a test message service."""
    return MessageService(config, db_service, llm_service)

def test_get_next_uuid(message_service: MessageService):
    """Test generating UUID."""
    uuid1 = message_service.get_next_uuid()
    uuid2 = message_service.get_next_uuid()
    
    assert isinstance(uuid1, str)
    assert isinstance(uuid2, str)
    assert uuid1 != uuid2

@pytest.mark.asyncio
async def test_add_message(message_service: MessageService, db_service, llm_service):
    """Test adding a message."""
    # Create test message
    message = Message(
        request_id="test_request",
        type=MessageType.REQUEST,
        status=MessageStatus.PENDING,
        timestamp=datetime.now(),
        content="Test message",
        metadata={"test": "value"}
    )
    
    # Mock database response
    db_service.insert.return_value = {"id": 1}
    
    # Add message
    result = await message_service.add_message(
        session_id="test_session",
        message=message,
        user_id="test_user",
        sender="test_sender",
        target="test_target"
    )
    
    assert result == {"id": 1}
    
    # Check LLM service call
    llm_service.get_embedding.assert_called_once_with("Test message")
    
    # Check database call
    db_service.insert.assert_called_once()
    call_args = db_service.insert.call_args[1]
    assert call_args["table_name"] == "swarm_messages"
    assert call_args["data"]["session_id"] == "test_session"
    assert call_args["data"]["content"] == "Test message"
    assert call_args["data"]["user_id"] == "test_user"
    assert call_args["data"]["sender"] == "test_sender"
    assert call_args["data"]["target"] == "test_target"

@pytest.mark.asyncio
async def test_get_messages(message_service: MessageService, db_service):
    """Test getting messages."""
    # Mock database response
    test_message = {
        "request_id": "test_request",
        "type": MessageType.REQUEST.value,
        "status": MessageStatus.COMPLETED.value,
        "timestamp": datetime.now().isoformat(),
        "content": "Test message",
        "data": {},
        "metadata": {"test": "value"}
    }
    
    db_service.select.return_value = [test_message]
    
    # Get messages
    messages = await message_service.get_messages("test_session", "test_user")
    
    assert len(messages) == 1
    assert isinstance(messages[0], Message)
    assert messages[0].content == "Test message"
    assert messages[0].metadata["test"] == "value"
    
    # Check database call
    db_service.select.assert_called_once()
    call_args = db_service.select.call_args[1]
    assert call_args["table_name"] == "messages"
    assert call_args["filters"]["session_id"] == "test_session"
    assert call_args["filters"]["user_id"] == "test_user"

@pytest.mark.asyncio
async def test_search_messages(message_service: MessageService, db_service):
    """Test searching messages."""
    # Mock database response
    test_message = {
        "request_id": "test_request",
        "type": MessageType.REQUEST.value,
        "status": MessageStatus.COMPLETED.value,
        "timestamp": datetime.now().isoformat(),
        "content": "Test message",
        "data": {},
        "metadata": {"test": "value"}
    }
    
    db_service.select.return_value = [test_message]
    
    # Search messages
    messages = await message_service.search_messages(
        query="test",
        session_id="test_session",
        user_id="test_user"
    )
    
    assert len(messages) == 1
    assert isinstance(messages[0], Message)
    assert messages[0].content == "Test message"
    
    # Check database call
    db_service.select.assert_called_once()
    call_args = db_service.select.call_args[1]
    assert call_args["table_name"] == "messages"
    assert call_args["filters"]["session_id"] == "test_session"
    assert call_args["filters"]["user_id"] == "test_user"

@pytest.mark.asyncio
async def test_delete_messages(message_service: MessageService, db_service):
    """Test deleting messages."""
    # Mock database response
    db_service.delete_records.return_value = [{"id": 1}]
    
    # Delete messages
    success = await message_service.delete_messages("test_session", "test_user")
    assert success
    
    # Check database call
    db_service.delete_records.assert_called_once()
    call_args = db_service.delete_records.call_args[1]
    assert call_args["table_name"] == "swarm_messages"
    assert call_args["filters"]["session_id"] == "test_session"
    assert call_args["filters"]["user_id"] == "test_user"

def test_pending_message_management(message_service: MessageService):
    """Test pending message management."""
    # Test getting non-existent pending message
    assert message_service.get_pending_message("test_request") is None
    
    # Test setting and getting pending message
    test_message = {"content": "Test message"}
    message_service._pending_messages["test_request"] = test_message
    assert message_service.get_pending_message("test_request") == test_message
    
    # Test clearing pending message
    message_service.clear_pending_message("test_request")
    assert message_service.get_pending_message("test_request") is None 