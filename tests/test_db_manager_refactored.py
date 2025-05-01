"""
Test module for the DatabaseManager class after refactoring.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

from src.managers.db_manager import DatabaseManager, MessageManagerDB, ConversationManagerDB
from src.services.record_service import DatabaseService

@pytest.fixture
def mock_db_service():
    """Create a mock DatabaseService."""
    mock_service = MagicMock(spec=DatabaseService)
    
    # Setup common method responses
    mock_service.insert_message.return_value = {"id": 1}
    mock_service.get_messages.return_value = [
        {"id": 1, "role": "user", "content": "Hello", "conversation_id": 1, "metadata": {}}
    ]
    mock_service.insert_conversation.return_value = 1
    mock_service.get_conversations.return_value = [
        {"id": 1, "name": "Test Conversation", "user_id": "developer"}
    ]
    
    return mock_service

@pytest.fixture
def db_manager(mock_db_service):
    """Create a DatabaseManager with a mock service."""
    return DatabaseManager(db_service=mock_db_service)

class TestMessageManagerDB:
    """Test case for the MessageManagerDB class."""
    
    def test_add_message_success(self, mock_db_service):
        """Test adding a message successfully."""
        message_manager = MessageManagerDB(mock_db_service)
        result = message_manager.add_message(
            session_id=1,
            role="user",
            content="Hello",
            metadata={},
            user_id="developer"
        )
        
        assert result is True
        mock_db_service.insert_message.assert_called_once()
        
    def test_add_message_failure(self, mock_db_service):
        """Test adding a message with failure."""
        mock_db_service.insert_message.return_value = None
        
        message_manager = MessageManagerDB(mock_db_service)
        result = message_manager.add_message(
            session_id=1,
            role="user",
            content="Hello",
            metadata={},
            user_id="developer"
        )
        
        assert result is False
        
    def test_get_messages(self, mock_db_service):
        """Test getting messages."""
        message_manager = MessageManagerDB(mock_db_service)
        messages = message_manager.get_messages(
            session_id=1,
            user_id="developer"
        )
        
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        mock_db_service.get_messages.assert_called_once()
        
    def test_search_messages(self, mock_db_service):
        """Test searching messages."""
        mock_db_service.search_messages.return_value = [
            {"id": 1, "role": "user", "content": "Search term", "conversation_id": 1}
        ]
        
        message_manager = MessageManagerDB(mock_db_service)
        messages = message_manager.search_messages(
            query="search",
            session_id=1,
            user_id="developer"
        )
        
        assert len(messages) == 1
        mock_db_service.search_messages.assert_called_once()
        
    def test_delete_messages(self, mock_db_service):
        """Test deleting messages."""
        mock_db_service.delete_messages.return_value = True
        
        message_manager = MessageManagerDB(mock_db_service)
        result = message_manager.delete_messages(
            session_id=1,
            user_id="developer"
        )
        
        assert result is True
        mock_db_service.delete_messages.assert_called_once()

class TestConversationManagerDB:
    """Test case for the ConversationManagerDB class."""
    
    def test_create_conversation(self, mock_db_service):
        """Test creating a conversation."""
        conversation_manager = ConversationManagerDB(mock_db_service)
        result = conversation_manager.create_conversation(
            user_id="developer",
            name="Test Conversation"
        )
        
        assert result == 1
        mock_db_service.insert_conversation.assert_called_once()
        
    def test_get_conversation(self, mock_db_service):
        """Test getting a conversation."""
        conversation_manager = ConversationManagerDB(mock_db_service)
        conversation = conversation_manager.get_conversation(
            conversation_id=1,
            user_id="developer"
        )
        
        assert conversation is not None
        assert conversation["id"] == 1
        assert conversation["name"] == "Test Conversation"
        mock_db_service.get_conversations.assert_called_once()
        
    def test_get_recent_conversations(self, mock_db_service):
        """Test getting recent conversations."""
        conversation_manager = ConversationManagerDB(mock_db_service)
        conversations = conversation_manager.get_recent_conversations(
            user_id="developer",
            limit=10
        )
        
        assert len(conversations) == 1
        mock_db_service.get_conversations.assert_called_once()
        
    def test_update_conversation_success(self, mock_db_service):
        """Test updating a conversation successfully."""
        mock_db_service.update_conversation.return_value = {"id": 1}
        
        conversation_manager = ConversationManagerDB(mock_db_service)
        result = conversation_manager.update_conversation(
            conversation_id=1,
            data={"name": "Updated Conversation"},
            user_id="developer"
        )
        
        assert result is True
        
    def test_update_conversation_not_found(self, mock_db_service):
        """Test updating a conversation that doesn't exist."""
        mock_db_service.get_conversations.return_value = []
        
        conversation_manager = ConversationManagerDB(mock_db_service)
        result = conversation_manager.update_conversation(
            conversation_id=999,
            data={"name": "Updated Conversation"},
            user_id="developer"
        )
        
        assert result is False
        mock_db_service.update_conversation.assert_not_called()
        
    def test_delete_conversation_success(self, mock_db_service):
        """Test deleting a conversation successfully."""
        mock_db_service.delete_conversation.return_value = True
        
        conversation_manager = ConversationManagerDB(mock_db_service)
        result = conversation_manager.delete_conversation(
            conversation_id=1,
            user_id="developer"
        )
        
        assert result is True
        
    def test_delete_conversation_not_found(self, mock_db_service):
        """Test deleting a conversation that doesn't exist."""
        mock_db_service.get_conversations.return_value = []
        
        conversation_manager = ConversationManagerDB(mock_db_service)
        result = conversation_manager.delete_conversation(
            conversation_id=999,
            user_id="developer"
        )
        
        assert result is False
        mock_db_service.delete_conversation.assert_not_called()
        
    def test_search_conversations(self, mock_db_service):
        """Test searching conversations."""
        mock_db_service.search_conversations.return_value = [
            {"id": 1, "name": "Test Search", "user_id": "developer"}
        ]
        
        conversation_manager = ConversationManagerDB(mock_db_service)
        conversations = conversation_manager.search_conversations(
            query="test",
            user_id="developer"
        )
        
        assert len(conversations) == 1
        mock_db_service.search_conversations.assert_called_once()

class TestDatabaseManager:
    """Test case for the DatabaseManager class."""
    
    def test_add_message(self, db_manager, mock_db_service):
        """Test adding a message through the DatabaseManager."""
        with patch.object(db_manager.message_manager, 'add_message') as mock_add_message:
            mock_add_message.return_value = True
            
            result = db_manager.add_message(
                session_id="1",
                role="user",
                content="Hello",
                user_id="developer"
            )
            
            assert result is True
            mock_add_message.assert_called_once_with(
                session_id=1,
                role="user",
                content="Hello",
                metadata={},
                user_id="developer"
            )
    
    def test_get_messages(self, db_manager, mock_db_service):
        """Test getting messages through the DatabaseManager."""
        with patch.object(db_manager.message_manager, 'get_messages') as mock_get_messages:
            mock_get_messages.return_value = [
                {"id": 1, "role": "user", "content": "Hello", "conversation_id": 1}
            ]
            
            messages = db_manager.get_messages(
                session_id="1",
                user_id="developer"
            )
            
            assert len(messages) == 1
            mock_get_messages.assert_called_once_with(
                session_id=1,
                user_id="developer"
            )
    
    def test_search_messages(self, db_manager, mock_db_service):
        """Test searching messages through the DatabaseManager."""
        with patch.object(db_manager.message_manager, 'search_messages') as mock_search_messages:
            mock_search_messages.return_value = [
                {"id": 1, "role": "user", "content": "Search term", "conversation_id": 1}
            ]
            
            messages = db_manager.search_messages(
                query="search",
                session_id="1",
                user_id="developer"
            )
            
            assert len(messages) == 1
            mock_search_messages.assert_called_once_with(
                query="search",
                session_id=1,
                user_id="developer"
            )
    
    def test_create_conversation(self, db_manager, mock_db_service):
        """Test creating a conversation through the DatabaseManager."""
        with patch.object(db_manager.conversation_manager, 'create_conversation') as mock_create:
            mock_create.return_value = 1
            
            result = db_manager.create_conversation(
                user_id="developer",
                name="Test Conversation"
            )
            
            assert result == 1
            mock_create.assert_called_once_with(
                user_id="developer",
                name="Test Conversation"
            )
    
    def test_get_conversation(self, db_manager, mock_db_service):
        """Test getting a conversation through the DatabaseManager."""
        with patch.object(db_manager.conversation_manager, 'get_conversation') as mock_get:
            mock_get.return_value = {"id": 1, "name": "Test Conversation"}
            
            conversation = db_manager.get_conversation(
                conversation_id="1",
                user_id="developer"
            )
            
            assert conversation is not None
            assert conversation["id"] == 1
            mock_get.assert_called_once_with(
                conversation_id=1,
                user_id="developer"
            )
    
    def test_continue_conversation(self, db_manager, mock_db_service):
        """Test continuing a conversation through the DatabaseManager."""
        with patch.object(db_manager, 'get_conversation') as mock_get:
            mock_get.return_value = {"id": 1, "name": "Test Conversation"}
            
            with patch.object(db_manager, 'update_conversation') as mock_update:
                mock_update.return_value = True
                
                conversation = db_manager.continue_conversation(
                    conversation_id="1",
                    user_id="developer"
                )
                
                assert conversation is not None
                assert conversation["id"] == 1
                mock_get.assert_called_once()
                mock_update.assert_called_once()
    
    def test_get_recent_conversations(self, db_manager, mock_db_service):
        """Test getting recent conversations through the DatabaseManager."""
        with patch.object(db_manager.conversation_manager, 'get_recent_conversations') as mock_get_recent:
            mock_get_recent.return_value = [{"id": 1, "name": "Test Conversation"}]
            
            conversations = db_manager.get_recent_conversations(
                user_id="developer",
                limit=10
            )
            
            assert len(conversations) == 1
            mock_get_recent.assert_called_once_with(
                user_id="developer",
                limit=10
            )
    
    def test_update_conversation(self, db_manager, mock_db_service):
        """Test updating a conversation through the DatabaseManager."""
        with patch.object(db_manager.conversation_manager, 'update_conversation') as mock_update:
            mock_update.return_value = True
            
            result = db_manager.update_conversation(
                conversation_id="1",
                data={"name": "Updated Conversation"},
                user_id="developer"
            )
            
            assert result is True
            mock_update.assert_called_once_with(
                conversation_id=1,
                data={"name": "Updated Conversation"},
                user_id="developer"
            )
    
    def test_rename_conversation(self, db_manager, mock_db_service):
        """Test renaming a conversation through the DatabaseManager."""
        with patch.object(db_manager, 'update_conversation') as mock_update:
            mock_update.return_value = True
            
            result = db_manager.rename_conversation(
                conversation_id="1",
                name="New Name",
                user_id="developer"
            )
            
            assert result is True
            mock_update.assert_called_once_with(
                conversation_id="1",
                data={"name": "New Name"},
                user_id="developer"
            )
    
    def test_delete_conversation(self, db_manager, mock_db_service):
        """Test deleting a conversation through the DatabaseManager."""
        with patch.object(db_manager.message_manager, 'delete_messages') as mock_delete_messages:
            mock_delete_messages.return_value = True
            
            with patch.object(db_manager.conversation_manager, 'delete_conversation') as mock_delete_conv:
                mock_delete_conv.return_value = True
                
                result = db_manager.delete_conversation(
                    conversation_id="1",
                    user_id="developer"
                )
                
                assert result is True
                mock_delete_messages.assert_called_once()
                mock_delete_conv.assert_called_once()
    
    def test_search_conversations(self, db_manager, mock_db_service):
        """Test searching conversations through the DatabaseManager."""
        with patch.object(db_manager.conversation_manager, 'search_conversations') as mock_search:
            mock_search.return_value = [{"id": 1, "name": "Test Search"}]
            
            conversations = db_manager.search_conversations(
                query="test",
                user_id="developer"
            )
            
            assert len(conversations) == 1
            mock_search.assert_called_once_with(
                query="test",
                user_id="developer"
            ) 