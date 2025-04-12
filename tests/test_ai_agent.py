"""Tests for the AI agent module."""

import pytest
import logging
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
from src.agents.ai_agent import LLMQueryAgent, main
from src.config import Configuration
from src.services.db_services.db_manager import (
    ConversationState, 
    ConversationMetadata,
    MessageRole,
    TaskStatus
)

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return Configuration(
        ollama_api_url='http://test:11434',
        ollama_model='test-model',
        file_level='DEBUG',
        console_level='INFO'
    )

@pytest.fixture
def mock_requests_post():
    """Fixture to mock requests.post"""
    with patch('requests.post') as mock_post:
        yield mock_post

@pytest.fixture
def mock_db_manager():
    """Fixture to mock DatabaseManager"""
    with patch('src.agents.ai_agent.DatabaseManager') as mock_db:
        mock_instance = MagicMock()
        mock_db.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_logger():
    """Fixture to mock the logger"""
    with patch('src.agents.ai_agent.logger') as mock_log:
        yield mock_log

@pytest.fixture
def sample_conversation_state():
    """Create a sample conversation state for testing."""
    return ConversationState(
        session_id=123,
        metadata=ConversationMetadata(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id="developer",
            title="Test Conversation"
        ),
        current_task_status=TaskStatus.PENDING
    )

def test_agent_initialization(mock_config, mock_db_manager, mock_logger):
    """Test agent initialization with configuration."""
    agent = LLMQueryAgent(config=mock_config)
    
    # Check configuration was used
    assert agent.api_url == 'http://test:11434/api/generate'
    assert agent.model == 'test-model'
    
    # Check database was initialized
    assert agent.has_db is True
    
    # Check default user ID
    assert agent.user_id == "developer"
    
    # Check conversation state is initialized to None
    assert agent.conversation_state is None
    
    # Check logging was used
    mock_logger.info.assert_any_call("Database initialized successfully")

def test_session_id_property(mock_config):
    """Test the session_id property with and without conversation state."""
    agent = LLMQueryAgent(config=mock_config)
    
    # Without conversation state
    with patch.object(agent, 'has_db', False):
        assert agent.session_id is None
    
    # With conversation state
    conversation = MagicMock(spec=ConversationState)
    conversation.session_id = 123
    agent.conversation_state = conversation
    assert agent.session_id == 123

def test_generate_prompt(mock_config, mock_logger):
    """Test prompt generation"""
    agent = LLMQueryAgent(config=mock_config)
    with patch.object(agent, 'has_db', False):  # Ensure DB doesn't interfere with test
        user_input = "Hello, how are you?"
        prompt = agent.generate_prompt(user_input)
        
        # Check the prompt contains user input
        assert "Hello, how are you?" in prompt
        
        # Check logging occurred
        mock_logger.debug.assert_called_once()

def test_query_llm_success(mock_config, mock_requests_post, mock_logger):
    """Test successful LLM query"""
    agent = LLMQueryAgent(config=mock_config)
    with patch.object(agent, 'has_db', False):  # Ensure DB doesn't interfere with test
        mock_response = Mock()
        mock_response.json.return_value = {'response': 'I am fine, thank you.'}
        mock_response.raise_for_status = Mock()
        mock_requests_post.return_value = mock_response

        prompt = agent.generate_prompt("Hello, how are you?")
        response = agent.query_llm(prompt)
        assert response == 'I am fine, thank you.'
        
        # Check logging occurred
        mock_logger.info.assert_any_call(f"Querying LLM model: {agent.model}")
        mock_logger.info.assert_any_call("Received response from LLM (length: 19)")

def test_query_llm_failure(mock_config, mock_requests_post, mock_logger):
    """Test LLM query failure"""
    agent = LLMQueryAgent(config=mock_config)
    with patch.object(agent, 'has_db', False):  # Ensure DB doesn't interfere with test
        mock_requests_post.side_effect = Exception("Network error")

        prompt = agent.generate_prompt("Hello, how are you?")
        response = agent.query_llm(prompt)
        assert "Error querying LLM" in response
        
        # Check error was logged
        mock_logger.error.assert_called_once()
        assert "Network error" in mock_logger.error.call_args[0][0]

def test_start_conversation(mock_config, mock_db_manager, mock_logger, sample_conversation_state):
    """Test starting a conversation with database"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    mock_db_manager.create_conversation.return_value = sample_conversation_state
    
    result = agent.start_conversation(title="Test Title")
    
    assert result is True
    assert agent.conversation_state is sample_conversation_state
    assert agent.session_id == 123
    mock_db_manager.create_conversation.assert_called_once_with(agent.user_id, title="Test Title")
    
    # Check logging
    mock_logger.info.assert_any_call("Started conversation with session ID: 123")

def test_start_conversation_failure(mock_config, mock_db_manager, mock_logger):
    """Test handling a failure when starting a conversation"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    mock_db_manager.create_conversation.side_effect = Exception("Database error")
    
    result = agent.start_conversation()
    
    assert result is False
    assert agent.conversation_state is None
    
    # Check error was logged
    mock_logger.error.assert_called_once()
    assert "Failed to start conversation" in mock_logger.error.call_args[0][0]

def test_continue_conversation(mock_config, mock_db_manager, mock_logger, sample_conversation_state):
    """Test continuing an existing conversation"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    mock_db_manager.continue_conversation.return_value = sample_conversation_state
    
    result = agent.continue_conversation(123)
    
    assert result is True
    assert agent.conversation_state is sample_conversation_state
    assert agent.session_id == 123
    mock_db_manager.continue_conversation.assert_called_once_with(123)
    
    # Check logging
    mock_logger.info.assert_any_call("Continuing conversation with session ID: 123")

def test_continue_conversation_not_found(mock_config, mock_db_manager, mock_logger):
    """Test continuing a non-existent conversation"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    mock_db_manager.continue_conversation.return_value = None
    
    result = agent.continue_conversation(123)
    
    assert result is False
    assert agent.conversation_state is None
    
    # Check error was logged
    mock_logger.error.assert_called_once()
    assert "Failed to continue conversation: session 123 not found" in mock_logger.error.call_args[0][0]

def test_list_conversations(mock_config, mock_db_manager):
    """Test listing conversations"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    mock_conversations = [MagicMock(), MagicMock()]
    mock_db_manager.list_conversations.return_value = mock_conversations
    
    conversations = agent.list_conversations(limit=5)
    
    assert conversations == mock_conversations
    mock_db_manager.list_conversations.assert_called_once_with(agent.user_id, limit=5)

def test_update_task_status(mock_config, mock_db_manager, mock_logger, sample_conversation_state):
    """Test updating task status"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    agent.conversation_state = sample_conversation_state
    mock_db_manager.update_task_status.return_value = True
    
    result = agent.update_task_status(TaskStatus.IN_PROGRESS)
    
    assert result is True
    mock_db_manager.update_task_status.assert_called_once_with(sample_conversation_state, TaskStatus.IN_PROGRESS)
    
    # Check logging
    mock_logger.info.assert_called_with("Updated task status to in_progress")

def test_update_task_status_failure(mock_config, mock_db_manager, mock_logger, sample_conversation_state):
    """Test handling a failure when updating task status"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    agent.conversation_state = sample_conversation_state
    mock_db_manager.update_task_status.return_value = False
    
    result = agent.update_task_status(TaskStatus.IN_PROGRESS)
    
    assert result is False
    
    # Check error was logged
    mock_logger.error.assert_called_once()

def test_is_conversation_end(mock_config):
    """Test detecting the end of a conversation"""
    agent = LLMQueryAgent(config=mock_config)
    
    # Test positive cases
    assert agent._is_conversation_end("Goodbye, have a nice day!") is True
    assert agent._is_conversation_end("Thank you for chatting. See you later!") is True
    
    # Test negative cases
    assert agent._is_conversation_end("I'm still thinking about that.") is False
    assert agent._is_conversation_end("Let me help you with that question.") is False

def test_chat_with_conversation_state(mock_config, mock_db_manager, mock_logger, sample_conversation_state):
    """Test chat flow with conversation state management"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    agent.conversation_state = sample_conversation_state
    
    # Mock methods
    agent.generate_prompt = Mock(return_value="Test prompt")
    agent.query_llm = Mock(return_value="I am fine, thank you.")
    agent.process_response_with_tools = Mock(return_value={"tool_calls": [], "execution_results": []})
    mock_db_manager.update_task_status.return_value = True
    
    # Mock _is_conversation_end to detect the end of the conversation
    agent._is_conversation_end = Mock(return_value=True)
    
    response = agent.chat("Hello, how are you?")
    
    # Verify conversation state updates
    mock_db_manager.update_task_status.assert_called_with(sample_conversation_state, TaskStatus.COMPLETED)
    
    # Verify message was added to both conversation state and database
    assert sample_conversation_state.add_message.call_count >= 2  # User and assistant messages
    assert mock_db_manager.add_message.call_count >= 2  # User and assistant messages

def test_main_function_with_conversation_selection(mock_config, monkeypatch, mock_logger, sample_conversation_state):
    """Test the main function with conversation selection"""
    # Create a mock agent
    with patch('src.agents.ai_agent.LLMQueryAgent') as MockAgent:
        # Mock the agent instance
        mock_agent = Mock()
        MockAgent.return_value = mock_agent
        mock_agent.list_conversations.return_value = [
            MagicMock(session_id=1, title="Conv 1", message_count=5, updated_at=datetime.now()),
            MagicMock(session_id=2, title="Conv 2", message_count=10, updated_at=datetime.now())
        ]
        mock_agent.continue_conversation.return_value = True
        mock_agent.chat.return_value = {"response": "I am fine, thank you."}
        
        # Mock input and print functions to select option 2 (continue conversation) and then first conversation
        inputs = iter(["2", "1", "Hello", "exit"])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))
        monkeypatch.setattr('builtins.print', lambda *args, **kwargs: None)  # Suppress print output
        
        # Run the main function
        main()
        
        # Verify interactions
        mock_agent.list_conversations.assert_called_once()
        mock_agent.continue_conversation.assert_called_once_with(1)
        mock_agent.chat.assert_called_once_with("Hello")
        
        # Reset mocks and test starting a new conversation
        MockAgent.reset_mock()
        mock_agent.reset_mock()
        mock_agent.start_conversation.return_value = True
        
        # Mock input to select option 1 (new conversation) with a title
        inputs = iter(["1", "My New Conversation", "Hello", "exit"])
        
        # Run the main function again
        main()
        
        # Verify new conversation was started
        mock_agent.start_conversation.assert_called_once_with(title="My New Conversation")
        mock_agent.chat.assert_called_once_with("Hello")
