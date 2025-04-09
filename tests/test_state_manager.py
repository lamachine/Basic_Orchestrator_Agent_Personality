"""Tests for the state manager component."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import asyncio
from typing import Dict, Any, List, Optional

from src.state.state_manager import (
    StateManager,
    ConversationState,
    MessageEntry,
    StateNotFoundError
)

# Sample conversation data for testing
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
        },
        {
            "role": "assistant",
            "content": "Hi there! How can I help you today?"
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
def mock_db_manager():
    """Create a mock database manager."""
    mock_db = MagicMock()
    mock_db.get_conversation = AsyncMock(return_value=SAMPLE_CONVERSATION)
    mock_db.save_conversation = AsyncMock(return_value=True)
    mock_db.list_conversations = AsyncMock(return_value=["test-conversation-id"])
    mock_db.delete_conversation = AsyncMock(return_value=True)
    return mock_db

@pytest.fixture
def state_manager(mock_db_manager):
    """Create a state manager with a mock database."""
    return StateManager(db_manager=mock_db_manager)

@pytest.fixture
def sample_conversation_state():
    """Create a sample conversation state object."""
    messages = [
        MessageEntry(role="system", content="You are a helpful assistant."),
        MessageEntry(role="user", content="Hello!"),
        MessageEntry(role="assistant", content="Hi there! How can I help you today?")
    ]
    
    return ConversationState(
        conversation_id="test-conversation-id",
        user_id="test-user-id",
        messages=messages,
        metadata={
            "personality": "default",
            "created_at": "2023-06-01T12:00:00Z",
            "last_updated": "2023-06-01T12:01:00Z"
        },
        current_node="greeting_node"
    )

def test_message_entry_creation():
    """Test creating a MessageEntry object."""
    message = MessageEntry(role="user", content="Hello!")
    
    assert message.role == "user"
    assert message.content == "Hello!"
    
    # Test creating with metadata
    message_with_meta = MessageEntry(
        role="assistant", 
        content="Hi!", 
        metadata={"tokens": 10, "model": "test-model"}
    )
    
    assert message_with_meta.role == "assistant"
    assert message_with_meta.content == "Hi!"
    assert message_with_meta.metadata["tokens"] == 10
    assert message_with_meta.metadata["model"] == "test-model"

def test_conversation_state_creation(sample_conversation_state):
    """Test creating a ConversationState object."""
    state = sample_conversation_state
    
    assert state.conversation_id == "test-conversation-id"
    assert state.user_id == "test-user-id"
    assert len(state.messages) == 3
    assert state.messages[0].role == "system"
    assert state.messages[1].role == "user"
    assert state.messages[2].role == "assistant"
    assert state.metadata["personality"] == "default"
    assert state.current_node == "greeting_node"

def test_conversation_state_add_message(sample_conversation_state):
    """Test adding messages to a conversation state."""
    state = sample_conversation_state
    
    # Initial message count
    assert len(state.messages) == 3
    
    # Add a new user message
    state.add_message(role="user", content="How are you?")
    
    # Check message was added
    assert len(state.messages) == 4
    assert state.messages[3].role == "user"
    assert state.messages[3].content == "How are you?"
    
    # Add a message with metadata
    state.add_message(
        role="assistant", 
        content="I'm doing well!", 
        metadata={"tokens": 15}
    )
    
    # Check message with metadata
    assert len(state.messages) == 5
    assert state.messages[4].role == "assistant"
    assert state.messages[4].content == "I'm doing well!"
    assert state.messages[4].metadata["tokens"] == 15

def test_conversation_state_get_last_message(sample_conversation_state):
    """Test getting the last message of a conversation."""
    state = sample_conversation_state
    
    last_message = state.get_last_message()
    assert last_message.role == "assistant"
    assert last_message.content == "Hi there! How can I help you today?"
    
    # Add a new message and check again
    state.add_message(role="user", content="How are you?")
    last_message = state.get_last_message()
    assert last_message.role == "user"
    assert last_message.content == "How are you?"

def test_conversation_state_get_message_history(sample_conversation_state):
    """Test getting message history as a list of dicts."""
    state = sample_conversation_state
    
    history = state.get_message_history()
    
    assert len(history) == 3
    assert history[0]["role"] == "system"
    assert history[1]["role"] == "user"
    assert history[2]["role"] == "assistant"
    assert history[1]["content"] == "Hello!"

def test_conversation_state_to_dict(sample_conversation_state):
    """Test converting conversation state to a dictionary."""
    state = sample_conversation_state
    
    state_dict = state.to_dict()
    
    assert state_dict["conversation_id"] == "test-conversation-id"
    assert state_dict["user_id"] == "test-user-id"
    assert len(state_dict["messages"]) == 3
    assert state_dict["messages"][0]["role"] == "system"
    assert state_dict["metadata"]["personality"] == "default"
    assert state_dict["current_node"] == "greeting_node"

def test_conversation_state_from_dict():
    """Test creating a conversation state from a dictionary."""
    state_dict = {
        "conversation_id": "dict-conv-id",
        "user_id": "dict-user-id",
        "messages": [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Testing!"}
        ],
        "metadata": {
            "personality": "test",
            "created_at": "2023-06-02T12:00:00Z"
        },
        "current_node": "test_node"
    }
    
    state = ConversationState.from_dict(state_dict)
    
    assert state.conversation_id == "dict-conv-id"
    assert state.user_id == "dict-user-id"
    assert len(state.messages) == 2
    assert state.messages[0].role == "system"
    assert state.messages[1].content == "Testing!"
    assert state.metadata["personality"] == "test"
    assert state.current_node == "test_node"

@pytest.mark.asyncio
async def test_state_manager_create_conversation(state_manager, mock_db_manager):
    """Test creating a new conversation."""
    # Create conversation with minimal information
    conversation_id = await state_manager.create_conversation(
        user_id="new-user",
        personality="friendly"
    )
    
    # Verify a conversation ID was returned
    assert conversation_id is not None
    
    # Verify the save method was called
    mock_db_manager.save_conversation.assert_called_once()
    saved_data = mock_db_manager.save_conversation.call_args[0][0]
    
    # Check the saved data
    assert saved_data["user_id"] == "new-user"
    assert saved_data["metadata"]["personality"] == "friendly"
    assert len(saved_data["messages"]) >= 1  # Should at least have a system message
    assert saved_data["messages"][0]["role"] == "system"

@pytest.mark.asyncio
async def test_state_manager_get_conversation(state_manager, mock_db_manager):
    """Test retrieving a conversation."""
    # Get an existing conversation
    state = await state_manager.get_conversation("test-conversation-id")
    
    # Verify the database get method was called
    mock_db_manager.get_conversation.assert_called_once_with("test-conversation-id")
    
    # Check the state object
    assert state.conversation_id == "test-conversation-id"
    assert state.user_id == "test-user-id"
    assert len(state.messages) == 3
    assert state.current_node == "greeting_node"

@pytest.mark.asyncio
async def test_state_manager_get_nonexistent_conversation(state_manager, mock_db_manager):
    """Test retrieving a conversation that doesn't exist."""
    # Make the mock return None to simulate a missing conversation
    mock_db_manager.get_conversation.return_value = None
    
    # Attempt to get a nonexistent conversation - should raise an exception
    with pytest.raises(StateNotFoundError):
        await state_manager.get_conversation("nonexistent-id")

@pytest.mark.asyncio
async def test_state_manager_save_conversation(state_manager, mock_db_manager, sample_conversation_state):
    """Test saving a conversation."""
    # Save the conversation
    success = await state_manager.save_conversation(sample_conversation_state)
    
    # Verify the operation was successful
    assert success is True
    
    # Verify the database save method was called
    mock_db_manager.save_conversation.assert_called_once()
    saved_data = mock_db_manager.save_conversation.call_args[0][0]
    
    # Check the saved data
    assert saved_data["conversation_id"] == "test-conversation-id"
    assert saved_data["user_id"] == "test-user-id"
    assert len(saved_data["messages"]) == 3
    assert saved_data["current_node"] == "greeting_node"

@pytest.mark.asyncio
async def test_state_manager_update_conversation(state_manager, mock_db_manager):
    """Test updating a conversation with new messages."""
    # First get the conversation
    state = await state_manager.get_conversation("test-conversation-id")
    
    # Add a new message
    state.add_message(role="user", content="New message for testing")
    
    # Change the current node
    state.current_node = "response_node"
    
    # Save the updated conversation
    success = await state_manager.save_conversation(state)
    
    # Verify the operation was successful
    assert success is True
    
    # Verify the database save method was called
    mock_db_manager.save_conversation.assert_called_once()
    saved_data = mock_db_manager.save_conversation.call_args[0][0]
    
    # Check the saved data
    assert saved_data["conversation_id"] == "test-conversation-id"
    assert len(saved_data["messages"]) == 4  # One more than the original
    assert saved_data["messages"][3]["content"] == "New message for testing"
    assert saved_data["current_node"] == "response_node"

@pytest.mark.asyncio
async def test_state_manager_add_message(state_manager, mock_db_manager):
    """Test adding a message to a conversation."""
    # First get the conversation
    state = await state_manager.get_conversation("test-conversation-id")
    
    # Initial message count
    assert len(state.messages) == 3
    
    # Add a message through the state manager
    await state_manager.add_message(
        conversation_id="test-conversation-id",
        role="user",
        content="Adding through state manager",
        metadata={"test": "metadata"}
    )
    
    # Verify the database get and save methods were called
    assert mock_db_manager.get_conversation.call_count == 2  # Called twice
    assert mock_db_manager.save_conversation.call_count == 1
    
    # Get the saved data
    saved_data = mock_db_manager.save_conversation.call_args[0][0]
    
    # Check the saved data
    assert len(saved_data["messages"]) == 4  # One more than the original
    assert saved_data["messages"][3]["role"] == "user"
    assert saved_data["messages"][3]["content"] == "Adding through state manager"
    assert saved_data["messages"][3]["metadata"]["test"] == "metadata"

@pytest.mark.asyncio
async def test_state_manager_add_message_nonexistent(state_manager, mock_db_manager):
    """Test adding a message to a nonexistent conversation."""
    # Make the mock return None to simulate a missing conversation
    mock_db_manager.get_conversation.return_value = None
    
    # Attempt to add a message to a nonexistent conversation
    with pytest.raises(StateNotFoundError):
        await state_manager.add_message(
            conversation_id="nonexistent-id",
            role="user",
            content="This won't work"
        )

@pytest.mark.asyncio
async def test_state_manager_delete_conversation(state_manager, mock_db_manager):
    """Test deleting a conversation."""
    # Delete the conversation
    success = await state_manager.delete_conversation("test-conversation-id")
    
    # Verify the operation was successful
    assert success is True
    
    # Verify the database delete method was called
    mock_db_manager.delete_conversation.assert_called_once_with("test-conversation-id")

@pytest.mark.asyncio
async def test_state_manager_list_conversations(state_manager, mock_db_manager):
    """Test listing all conversations for a user."""
    # List conversations for a user
    conversations = await state_manager.list_conversations(user_id="test-user-id")
    
    # Verify the database list method was called
    mock_db_manager.list_conversations.assert_called_once_with(user_id="test-user-id")
    
    # Check the returned data
    assert len(conversations) == 1
    assert conversations[0] == "test-conversation-id"

@pytest.mark.asyncio
async def test_state_manager_update_current_node(state_manager, mock_db_manager):
    """Test updating the current node of a conversation."""
    # Update the current node
    await state_manager.update_current_node(
        conversation_id="test-conversation-id",
        node_id="new_node"
    )
    
    # Verify the database get and save methods were called
    assert mock_db_manager.get_conversation.call_count == 1
    assert mock_db_manager.save_conversation.call_count == 1
    
    # Get the saved data
    saved_data = mock_db_manager.save_conversation.call_args[0][0]
    
    # Check the saved data
    assert saved_data["current_node"] == "new_node"

@pytest.mark.asyncio
async def test_state_manager_update_metadata(state_manager, mock_db_manager):
    """Test updating the metadata of a conversation."""
    # Update the metadata
    await state_manager.update_metadata(
        conversation_id="test-conversation-id",
        metadata_updates={
            "personality": "updated",
            "new_field": "new_value"
        }
    )
    
    # Verify the database get and save methods were called
    assert mock_db_manager.get_conversation.call_count == 1
    assert mock_db_manager.save_conversation.call_count == 1
    
    # Get the saved data
    saved_data = mock_db_manager.save_conversation.call_args[0][0]
    
    # Check the saved data
    assert saved_data["metadata"]["personality"] == "updated"
    assert saved_data["metadata"]["new_field"] == "new_value"
    # Original fields should still be there
    assert "created_at" in saved_data["metadata"]
    assert "last_updated" in saved_data["metadata"]

@pytest.mark.asyncio
async def test_state_manager_get_conversation_history(state_manager, mock_db_manager):
    """Test getting the message history of a conversation."""
    # Get the message history
    history = await state_manager.get_conversation_history("test-conversation-id")
    
    # Verify the database get method was called
    mock_db_manager.get_conversation.assert_called_once_with("test-conversation-id")
    
    # Check the returned data
    assert len(history) == 3
    assert history[0]["role"] == "system"
    assert history[1]["role"] == "user"
    assert history[2]["role"] == "assistant"

@pytest.mark.asyncio
async def test_state_manager_get_current_node(state_manager, mock_db_manager):
    """Test getting the current node of a conversation."""
    # Get the current node
    node = await state_manager.get_current_node("test-conversation-id")
    
    # Verify the database get method was called
    mock_db_manager.get_conversation.assert_called_once_with("test-conversation-id")
    
    # Check the returned data
    assert node == "greeting_node"

@pytest.mark.asyncio
async def test_state_manager_get_metadata(state_manager, mock_db_manager):
    """Test getting the metadata of a conversation."""
    # Get the metadata
    metadata = await state_manager.get_metadata("test-conversation-id")
    
    # Verify the database get method was called
    mock_db_manager.get_conversation.assert_called_once_with("test-conversation-id")
    
    # Check the returned data
    assert metadata["personality"] == "default"
    assert "created_at" in metadata
    assert "last_updated" in metadata 