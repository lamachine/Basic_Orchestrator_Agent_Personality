"""Tests for the database manager component."""

import pytest
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from typing import Dict, Any, List, Optional

from src.services.db_services.db_manager import (
    DatabaseManager,
    DatabaseError,
    ConversationNotFoundError
)

# Sample database configuration
SAMPLE_DB_CONFIG = {
    "host": "localhost",
    "database": "test_db",
    "user": "test_user",
    "password": "test_password",
    "port": 5432
}

# Sample conversation data
SAMPLE_CONVERSATION = {
    "conversation_id": "test-conversation-id",
    "user_id": "test-user-id",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Hello!"
        }
    ],
    "metadata": {
        "personality": "default",
        "created_at": "2023-06-01T12:00:00Z",
        "last_updated": "2023-06-01T12:01:00Z"
    },
    "current_node": "greeting_node"
}

@pytest.fixture
def mock_pool():
    """Create a mock connection pool."""
    mock = MagicMock()
    
    # Mock connection context manager
    conn_context = MagicMock()
    mock.__aenter__.return_value = conn_context
    
    # Mock cursor context manager
    cursor_context = MagicMock()
    conn_context.cursor.return_value.__aenter__.return_value = cursor_context
    
    # Mock query methods
    cursor_context.execute = AsyncMock()
    cursor_context.fetchone = AsyncMock(return_value=(json.dumps(SAMPLE_CONVERSATION),))
    cursor_context.fetchall = AsyncMock(return_value=[
        ("test-conversation-id-1",),
        ("test-conversation-id-2",)
    ])
    
    return mock

@pytest.fixture
def mock_create_pool():
    """Create a mock for asyncpg.create_pool."""
    with patch('asyncpg.create_pool') as mock:
        yield mock

@pytest.fixture
def db_manager(mock_pool, mock_create_pool):
    """Create a database manager with a mock pool."""
    mock_create_pool.return_value = mock_pool
    
    with patch.dict(os.environ, {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "test_db",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password"
    }):
        manager = DatabaseManager()
        return manager

@pytest.mark.asyncio
async def test_init_db_from_env(mock_create_pool):
    """Test initializing the database from environment variables."""
    mock_create_pool.return_value = MagicMock()
    
    with patch.dict(os.environ, {
        "DB_HOST": "env_host",
        "DB_PORT": "1234",
        "DB_NAME": "env_db",
        "DB_USER": "env_user",
        "DB_PASSWORD": "env_pass"
    }):
        db = DatabaseManager()
        
        # Verify pool was created with correct parameters
        mock_create_pool.assert_called_once()
        call_kwargs = mock_create_pool.call_args[1]
        
        assert call_kwargs["host"] == "env_host"
        assert call_kwargs["port"] == 1234
        assert call_kwargs["database"] == "env_db"
        assert call_kwargs["user"] == "env_user"
        assert call_kwargs["password"] == "env_pass"

@pytest.mark.asyncio
async def test_init_db_from_config(mock_create_pool):
    """Test initializing the database from a config dictionary."""
    mock_create_pool.return_value = MagicMock()
    
    config = {
        "host": "config_host",
        "port": 5678,
        "database": "config_db",
        "user": "config_user",
        "password": "config_pass"
    }
    
    db = DatabaseManager(config=config)
    
    # Verify pool was created with correct parameters
    mock_create_pool.assert_called_once()
    call_kwargs = mock_create_pool.call_args[1]
    
    assert call_kwargs["host"] == "config_host"
    assert call_kwargs["port"] == 5678
    assert call_kwargs["database"] == "config_db"
    assert call_kwargs["user"] == "config_user"
    assert call_kwargs["password"] == "config_pass"

@pytest.mark.asyncio
async def test_init_db_pool_error(mock_create_pool):
    """Test handling error during pool creation."""
    mock_create_pool.side_effect = Exception("Connection error")
    
    with pytest.raises(DatabaseError):
        db = DatabaseManager(config=SAMPLE_DB_CONFIG)

@pytest.mark.asyncio
async def test_get_conversation(db_manager, mock_pool):
    """Test retrieving a conversation."""
    conversation = await db_manager.get_conversation("test-conversation-id")
    
    # Verify the query was executed with the correct parameters
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.execute.assert_called_once()
    
    # Check query contains conversation ID
    query_args = cursor.execute.call_args[0]
    assert "test-conversation-id" in query_args[1]
    
    # Verify the returned data
    assert conversation["conversation_id"] == "test-conversation-id"
    assert conversation["user_id"] == "test-user-id"
    assert len(conversation["messages"]) == 2
    assert conversation["metadata"]["personality"] == "default"

@pytest.mark.asyncio
async def test_get_conversation_not_found(db_manager, mock_pool):
    """Test retrieving a non-existent conversation."""
    # Set up mock to return None (no conversation found)
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.fetchone.return_value = None
    
    # Conversation should be None
    result = await db_manager.get_conversation("nonexistent-id")
    assert result is None

@pytest.mark.asyncio
async def test_save_conversation_new(db_manager, mock_pool):
    """Test saving a new conversation."""
    # Set fetchone to return None to simulate no existing conversation
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.fetchone.return_value = None
    
    # Save the conversation
    success = await db_manager.save_conversation(SAMPLE_CONVERSATION)
    
    # Verify success
    assert success is True
    
    # Verify execute was called twice: once to check existence and once to insert
    assert cursor.execute.call_count == 2
    
    # Check the second call contains INSERT
    insert_call = cursor.execute.call_args_list[1]
    assert "INSERT INTO" in insert_call[0][0].upper()

@pytest.mark.asyncio
async def test_save_conversation_update(db_manager, mock_pool):
    """Test updating an existing conversation."""
    # Set fetchone to return something to simulate existing conversation
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.fetchone.return_value = (json.dumps({"old": "data"}),)
    
    # Save the conversation
    success = await db_manager.save_conversation(SAMPLE_CONVERSATION)
    
    # Verify success
    assert success is True
    
    # Verify execute was called twice: once to check existence and once to update
    assert cursor.execute.call_count == 2
    
    # Check the second call contains UPDATE
    update_call = cursor.execute.call_args_list[1]
    assert "UPDATE" in update_call[0][0].upper()

@pytest.mark.asyncio
async def test_save_conversation_error(db_manager, mock_pool):
    """Test handling an error during save operation."""
    # Set execute to raise an exception
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.execute.side_effect = Exception("Database error")
    
    # Save should raise DatabaseError
    with pytest.raises(DatabaseError):
        await db_manager.save_conversation(SAMPLE_CONVERSATION)

@pytest.mark.asyncio
async def test_delete_conversation(db_manager, mock_pool):
    """Test deleting a conversation."""
    # Set fetchone to return something to simulate existing conversation
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.fetchone.return_value = (json.dumps(SAMPLE_CONVERSATION),)
    
    # Delete the conversation
    success = await db_manager.delete_conversation("test-conversation-id")
    
    # Verify success
    assert success is True
    
    # Verify execute was called twice: once to check existence and once to delete
    assert cursor.execute.call_count == 2
    
    # Check the second call contains DELETE
    delete_call = cursor.execute.call_args_list[1]
    assert "DELETE" in delete_call[0][0].upper()

@pytest.mark.asyncio
async def test_delete_nonexistent_conversation(db_manager, mock_pool):
    """Test deleting a non-existent conversation."""
    # Set fetchone to return None to simulate no existing conversation
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.fetchone.return_value = None
    
    # Delete should raise ConversationNotFoundError
    with pytest.raises(ConversationNotFoundError):
        await db_manager.delete_conversation("nonexistent-id")

@pytest.mark.asyncio
async def test_list_conversations(db_manager, mock_pool):
    """Test listing all conversations."""
    # List all conversations
    conversations = await db_manager.list_conversations()
    
    # Verify the query was executed
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.execute.assert_called_once()
    
    # Check the returned data
    assert len(conversations) == 2
    assert "test-conversation-id-1" in conversations
    assert "test-conversation-id-2" in conversations

@pytest.mark.asyncio
async def test_list_conversations_by_user(db_manager, mock_pool):
    """Test listing conversations for a specific user."""
    # List conversations for user
    conversations = await db_manager.list_conversations(user_id="test-user-id")
    
    # Verify the query was executed with the correct parameters
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.execute.assert_called_once()
    
    # Check query contains user ID
    query_args = cursor.execute.call_args[0]
    assert "test-user-id" in query_args[1]
    
    # Check the returned data
    assert len(conversations) == 2

@pytest.mark.asyncio
async def test_init_tables(db_manager, mock_pool):
    """Test initializing database tables."""
    # Initialize tables
    await db_manager.init_tables()
    
    # Verify the query was executed
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.execute.assert_called_once()
    
    # Check the query contains CREATE TABLE
    query = cursor.execute.call_args[0][0]
    assert "CREATE TABLE" in query.upper()

@pytest.mark.asyncio
async def test_close(db_manager, mock_pool):
    """Test closing the database connection."""
    # Close the connection
    await db_manager.close()
    
    # Verify the pool's close method was called
    mock_pool.close.assert_called_once()

@pytest.mark.asyncio
async def test_search_conversations(db_manager, mock_pool):
    """Test searching conversations by keyword."""
    # Mock the search results
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.fetchall.return_value = [
        ("test-conversation-id-1",),
    ]
    
    # Search conversations
    results = await db_manager.search_conversations(keyword="hello")
    
    # Verify the query was executed with the correct parameters
    cursor.execute.assert_called_once()
    
    # Check query contains the keyword
    query_args = cursor.execute.call_args[0]
    assert "hello" in query_args[1]
    
    # Check the returned data
    assert len(results) == 1
    assert "test-conversation-id-1" in results

@pytest.mark.asyncio
async def test_get_conversation_by_user(db_manager, mock_pool):
    """Test retrieving a specific conversation for a user."""
    # Get conversation for user
    conversation = await db_manager.get_conversation("test-conversation-id", user_id="test-user-id")
    
    # Verify the query was executed with the correct parameters
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.execute.assert_called_once()
    
    # Check query contains both IDs
    query_args = cursor.execute.call_args[0]
    assert "test-conversation-id" in query_args[1]
    assert "test-user-id" in query_args[1]
    
    # Verify the returned data
    assert conversation["conversation_id"] == "test-conversation-id"
    assert conversation["user_id"] == "test-user-id"

@pytest.mark.asyncio
async def test_get_conversations_after_date(db_manager, mock_pool):
    """Test retrieving conversations after a specific date."""
    # Mock the date search results
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.fetchall.return_value = [
        ("test-conversation-id-1",),
    ]
    
    # Get conversations after date
    results = await db_manager.get_conversations_after_date("2023-06-01")
    
    # Verify the query was executed with the correct parameters
    cursor.execute.assert_called_once()
    
    # Check query contains the date
    query_args = cursor.execute.call_args[0]
    assert "2023-06-01" in query_args[1]
    
    # Check the returned data
    assert len(results) == 1
    assert "test-conversation-id-1" in results

@pytest.mark.asyncio
async def test_backup_conversations(db_manager, mock_pool, tmp_path):
    """Test backing up conversations to a file."""
    # Mock the get all conversations
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    cursor.fetchall.return_value = [
        (json.dumps(SAMPLE_CONVERSATION),),
    ]
    
    # Create backup file path
    backup_file = tmp_path / "backup.json"
    
    # Backup conversations
    await db_manager.backup_conversations(str(backup_file))
    
    # Verify the query was executed
    cursor.execute.assert_called_once()
    
    # Check the backup file exists
    assert backup_file.exists()
    
    # Check the backup file contents
    with open(backup_file, 'r') as f:
        backup_data = json.load(f)
    
    assert len(backup_data) == 1
    assert backup_data[0]["conversation_id"] == "test-conversation-id"

@pytest.mark.asyncio
async def test_restore_conversations(db_manager, mock_pool, tmp_path):
    """Test restoring conversations from a backup file."""
    # Create backup data
    backup_data = [SAMPLE_CONVERSATION]
    
    # Create backup file
    backup_file = tmp_path / "backup.json"
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f)
    
    # Restore conversations
    await db_manager.restore_conversations(str(backup_file))
    
    # Verify the queries were executed (one per conversation)
    cursor = mock_pool.__aenter__.return_value.cursor.return_value.__aenter__.return_value
    assert cursor.execute.call_count == 1
    
    # Check the save query contains the conversation data
    save_call = cursor.execute.call_args
    assert "test-conversation-id" in str(save_call) 