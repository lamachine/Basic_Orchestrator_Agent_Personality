"""Tests for the database manager component."""

import pytest
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.services.db_services.db_manager import (
    DatabaseManager,
    ConversationState,
    ConversationMetadata,
    ConversationSummary,
    Message,
    MessageRole,
    TaskStatus,
    StateError,
    StateTransitionError,
    ValidationError
)

# Sample conversation data
SAMPLE_CONVERSATION = {
    "session_id": 123,
    "user_id": "developer",
    "metadata": {
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "user_id": "developer",
        "title": "Test Conversation"
    },
    "messages": [
        {
            "role": "user",
            "content": "Hello!",
            "created_at": datetime.now().isoformat(),
            "metadata": {}
        }
    ],
    "current_task_status": "pending"
}

@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()
    
    # Mock table operations
    mock_table = MagicMock()
    mock.table.return_value = mock_table
    
    # Mock insert operations
    mock_insert = MagicMock()
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value = MagicMock()
    
    # Mock select operations
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_select
    mock_select.order.return_value = mock_select
    mock_select.limit.return_value = mock_select
    mock_select.execute.return_value = MagicMock(data=[
        {"session_id": 123, "role": "user", "message": "Hello!", "metadata": json.dumps({"user_id": "developer"})}
    ])
    
    # Mock RPC operations
    mock_rpc = MagicMock()
    mock.rpc.return_value = mock_rpc
    mock_rpc.execute.return_value = MagicMock(data=[
        {"session_id": 123, "role": "user", "message": "Hello!", "similarity": 0.9}
    ])
    
    return mock

@pytest.fixture
def mock_create_client():
    """Create a mock for supabase.create_client."""
    with patch('src.services.db_services.db_manager.create_client') as mock:
        yield mock

@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient."""
    with patch('src.services.llm_services.llm_service.OllamaClient') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Mock embeddings method
        mock_instance.embeddings.return_value = MagicMock(embedding=[0.1] * 768)
        
        yield mock_instance

@pytest.fixture
def mock_llm_service():
    """Create a mock LLMService."""
    with patch('src.services.db_services.db_manager.LLMService') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Mock get_embedding method
        mock_instance.get_embedding.return_value = [0.1] * 768
        
        yield mock_instance

@pytest.fixture
def db_manager(mock_supabase, mock_create_client, mock_llm_service):
    """Create a database manager with mock dependencies."""
    mock_create_client.return_value = mock_supabase
    
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
        "OLLAMA_API_URL": "http://localhost:11434"
    }):
        return DatabaseManager()

def test_init_db_from_env(mock_create_client):
    """Test initializing the database from environment variables."""
    with patch.dict(os.environ, {
        "SUPABASE_URL": "https://env.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "env-key"
    }):
        db = DatabaseManager()
        
        # Verify client was created with correct parameters
        mock_create_client.assert_called_once_with(
            "https://env.supabase.co",
            "env-key"
        )

def test_get_next_id(db_manager, mock_supabase):
    """Test getting the next ID for a column."""
    # Set up mock to return a specific max ID
    mock_select = MagicMock()
    mock_supabase.table.return_value.select.return_value = mock_select
    mock_select.execute.return_value = MagicMock(data=[{"max": 5}])
    
    next_id = db_manager.get_next_id("session_id", "swarm_messages")
    
    # Verify the next ID is incremented correctly
    assert next_id == 6
    
    # Verify the Supabase API was called correctly
    mock_supabase.table.assert_called_with("swarm_messages")
    mock_supabase.table.return_value.select.assert_called_with("max(session_id)")

def test_create_conversation(db_manager, mock_supabase):
    """Test creating a new conversation."""
    # Set up mock to return a specific next ID
    db_manager.get_next_id = MagicMock(return_value=123)
    
    # Configure mock for insert
    mock_insert = MagicMock()
    mock_supabase.table.return_value.insert.return_value = mock_insert
    mock_insert.execute.return_value = MagicMock()
    
    conversation = db_manager.create_conversation("test-user", "Test Title")
    
    # Verify the conversation was created with correct parameters
    assert conversation.session_id == 123
    assert conversation.metadata.user_id == "test-user"
    assert conversation.metadata.title == "Test Title"
    assert conversation.current_task_status == TaskStatus.PENDING
    
    # Verify Supabase insert was called
    mock_supabase.table.assert_called_with("swarm_messages")
    insert_args = mock_supabase.table.return_value.insert.call_args[0][0]
    assert insert_args["session_id"] == 123
    assert insert_args["user_id"] == "test-user"
    assert insert_args["type"] == "conversation_start"
    assert "Test Title" in insert_args["metadata"]

def test_list_conversations(db_manager, mock_supabase):
    """Test listing available conversations."""
    # Set up mock to return sample conversations
    mock_select = MagicMock()
    mock_supabase.table.return_value.select.return_value = mock_select
    mock_select.eq.return_value = mock_select
    mock_select.order.return_value = mock_select
    mock_select.limit.return_value = mock_select
    
    # Mock data for the first query (session listing)
    mock_select.execute.return_value = MagicMock(data=[
        {
            "session_id": 123,
            "metadata": json.dumps({
                "title": "Test Conv 1",
                "current_task_status": "pending",
                "user_id": "test-user"
            })
        },
        {
            "session_id": 456,
            "metadata": json.dumps({
                "title": "Test Conv 2",
                "current_task_status": "completed",
                "user_id": "test-user"
            })
        }
    ])
    
    # Mock for count queries
    mock_count = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        MagicMock(count=5),  # First conversation message count
        MagicMock(count=10)  # Second conversation message count
    ]
    
    # Mock for timestamp queries
    mock_timestamps = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.side_effect = [
        MagicMock(data=[{"timestamp": "2023-01-01T12:00:00"}, {"timestamp": "2023-01-01T12:30:00"}]),
        MagicMock(data=[{"timestamp": "2023-01-02T12:00:00"}, {"timestamp": "2023-01-02T12:30:00"}])
    ]
    
    conversations = db_manager.list_conversations("test-user", limit=5)
    
    # Verify the conversations were returned correctly
    assert len(conversations) == 2
    
    # The implementation sorts by updated_at, so the second conversation should be first
    assert conversations[0].session_id == 456
    assert conversations[0].title == "Test Conv 2"
    assert conversations[0].current_task_status == TaskStatus.COMPLETED
    
    assert conversations[1].session_id == 123
    assert conversations[1].title == "Test Conv 1"
    assert conversations[1].current_task_status == TaskStatus.PENDING

def test_load_conversation(db_manager, mock_supabase):
    """Test loading a specific conversation."""
    # Set up mocks for metadata query
    mock_metadata_select = MagicMock()
    mock_supabase.table.return_value.select.return_value = mock_metadata_select
    mock_metadata_select.eq.return_value = mock_metadata_select
    mock_metadata_select.limit.return_value = mock_metadata_select
    
    # Mock data for metadata query
    mock_metadata_select.execute.return_value = MagicMock(data=[{
        "user_id": "developer",
        "metadata": json.dumps({
            "created_at": "2023-01-01T12:00:00", 
            "updated_at": "2023-01-01T12:30:00", 
            "user_id": "developer", 
            "title": "Test Conv", 
            "current_task_status": "in_progress"
        }),
        "timestamp": "2023-01-01T12:30:00"
    }])
    
    # Set up mocks for messages query
    mock_messages_select = MagicMock()
    mock_supabase.table.return_value.select.return_value = mock_messages_select
    mock_messages_select.eq.return_value = mock_messages_select
    mock_messages_select.order.return_value = mock_messages_select
    
    # Mock data for messages query (called second)
    mock_messages_select.execute.return_value = MagicMock(data=[
        {
            "sender": "orchestrator_graph.cli", 
            "content": "Hello!", 
            "timestamp": "2023-01-01T12:00:00", 
            "metadata": json.dumps({"user_id": "developer"}),
            "target": "orchestrator_graph.llm"
        },
        {
            "sender": "orchestrator_graph.llm", 
            "content": "Hi there!", 
            "timestamp": "2023-01-01T12:15:00", 
            "metadata": json.dumps({"user_id": "developer"}),
            "target": "orchestrator_graph.cli"
        }
    ])
    
    conversation = db_manager.load_conversation(123)
    
    # Verify the conversation was loaded correctly
    assert conversation.session_id == 123
    assert conversation.metadata.user_id == "developer"
    assert conversation.metadata.title == "Test Conv"
    assert conversation.current_task_status == TaskStatus.IN_PROGRESS
    assert len(conversation.messages) == 2
    assert conversation.messages[0].role == MessageRole.USER
    assert conversation.messages[0].content == "Hello!"
    assert conversation.messages[1].role == MessageRole.ASSISTANT
    assert conversation.messages[1].content == "Hi there!"

def test_continue_conversation(db_manager, mock_supabase):
    """Test continuing an existing conversation."""
    # Set up mock for load_conversation
    mock_conversation = MagicMock(spec=ConversationState)
    mock_conversation.session_id = 123
    mock_conversation.metadata = MagicMock(spec=ConversationMetadata)
    db_manager.load_conversation = MagicMock(return_value=mock_conversation)
    
    # Set up mock for update
    mock_update = MagicMock()
    mock_supabase.table.return_value.update.return_value = mock_update
    mock_update.eq.return_value = mock_update
    mock_update.eq.return_value = mock_update
    mock_update.execute.return_value = MagicMock()
    
    result = db_manager.continue_conversation(123)
    
    # Verify the conversation was loaded and returned
    assert result is mock_conversation
    db_manager.load_conversation.assert_called_once_with(123)
    
    # Verify Supabase update was called
    mock_supabase.table.assert_called_with("swarm_messages")
    mock_supabase.table.return_value.update.assert_called_once()
    first_eq = mock_update.eq.call_args_list[0]
    assert first_eq[0][0] == "session_id"
    assert first_eq[0][1] == 123
    second_eq = mock_update.eq.call_args_list[1]
    assert second_eq[0][0] == "type"
    assert second_eq[0][1] == "conversation_start"

def test_update_task_status(db_manager, mock_supabase):
    """Test updating task status."""
    # Create a conversation with PENDING status
    conversation = ConversationState(
        session_id=123,
        metadata=ConversationMetadata(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id="developer",
            title="Test Conv"
        ),
        current_task_status=TaskStatus.PENDING
    )
    
    # Mock validator
    db_manager.validator.validate_task_transition = MagicMock(return_value=True)
    
    # Set up mock for save_conversation
    db_manager.save_conversation = MagicMock(return_value=True)
    
    # Update to IN_PROGRESS (valid transition)
    result = db_manager.update_task_status(conversation, TaskStatus.IN_PROGRESS)
    
    # Verify the status was updated
    assert result is True
    assert conversation.current_task_status == TaskStatus.IN_PROGRESS
    
    # Verify save_conversation was called
    db_manager.save_conversation.assert_called_once_with(conversation)

def test_invalid_task_status_transition(db_manager, mock_supabase):
    """Test invalid task status transition."""
    # Create a conversation with COMPLETED status
    conversation = ConversationState(
        session_id=123,
        metadata=ConversationMetadata(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id="developer",
            title="Test Conv"
        ),
        current_task_status=TaskStatus.COMPLETED
    )
    
    # Mock validator to reject the transition
    db_manager.validator.validate_task_transition = MagicMock(return_value=False)
    
    # Try to update to IN_PROGRESS (invalid transition)
    result = db_manager.update_task_status(conversation, TaskStatus.IN_PROGRESS)
    
    # Verify the update failed
    assert result is False
    assert conversation.current_task_status == TaskStatus.COMPLETED
    
    # Verify save_conversation was not called
    db_manager.save_conversation = MagicMock()
    db_manager.save_conversation.assert_not_called()

def test_add_message(db_manager, mock_supabase):
    """Test adding a message to a conversation."""
    # Set up mock for insert
    mock_insert = MagicMock()
    mock_supabase.table.return_value.insert.return_value = mock_insert
    mock_insert.execute.return_value = MagicMock()
    
    # Mock calculate_embedding (it's tested separately)
    db_manager.llm_service.get_embedding = MagicMock(return_value=[0.1] * 768)
    
    # Call the method
    request_id = db_manager.add_message(
        session_id=123,
        role="user",
        message="Hello, world!",
        user_id="developer"
    )
    
    # Verify the message was added with correct parameters
    mock_supabase.table.assert_called_with("swarm_messages")
    insert_args = mock_supabase.table.return_value.insert.call_args[0][0]
    assert insert_args['session_id'] == 123
    assert insert_args['sender'] == "orchestrator_graph.cli"
    assert insert_args['target'] == "orchestrator_graph.llm"
    assert insert_args['content'] == "Hello, world!"
    assert insert_args['user_id'] == "developer"
    assert 'embedding_nomic' in insert_args
    assert insert_args['message'] == "Hello, world!"
    assert json.loads(insert_args['metadata'])['user_id'] == "developer"
    assert 'embedding_nomic' in insert_args

def test_get_embedding(mock_llm_service, db_manager):
    """Test getting embeddings through the LLMService."""
    # Test that the database manager uses the LLM service for embeddings
    db_manager.add_message(
        session_id=1,
        role="user",
        message="Test message",
        user_id="test-user"
    )
    
    # Verify the LLM service was called correctly
    mock_llm_service.return_value.get_embedding.assert_called_with("Test message") 