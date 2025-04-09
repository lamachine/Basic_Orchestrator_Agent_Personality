"""Tests for the AI agent module."""

import pytest
import logging
from unittest.mock import patch, Mock, MagicMock
from src.agents.ai_agent import LLMQueryAgent, main
from src.config import Configuration

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

def test_agent_initialization(mock_config, mock_db_manager, mock_logger):
    """Test agent initialization with configuration."""
    agent = LLMQueryAgent(config=mock_config)
    
    # Check configuration was used
    assert agent.api_url == 'http://test:11434/api/generate'
    assert agent.model == 'test-model'
    
    # Check database was initialized
    assert agent.has_db is True
    
    # Check logging was used
    mock_logger.info.assert_any_call("Database initialized successfully")

def test_generate_prompt(mock_config, mock_logger):
    """Test prompt generation"""
    agent = LLMQueryAgent(config=mock_config)
    with patch.object(agent, 'has_db', False):  # Ensure DB doesn't interfere with test
        user_input = "Hello, how are you?"
        expected_prompt = "User: Hello, how are you?\nAgent:"
        assert agent.generate_prompt(user_input) == expected_prompt
        
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

def test_start_conversation(mock_config, mock_db_manager, mock_logger):
    """Test starting a conversation with database"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    mock_db_manager.create_conversation.return_value = "test-session-id"
    
    result = agent.start_conversation()
    
    assert result is True
    assert agent.session_id == "test-session-id"
    mock_db_manager.create_conversation.assert_called_once_with(agent.user_id)
    
    # Check logging
    mock_logger.info.assert_any_call("Started conversation with session ID: test-session-id")

def test_start_conversation_failure(mock_config, mock_db_manager, mock_logger):
    """Test handling a failure when starting a conversation"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    mock_db_manager.create_conversation.side_effect = Exception("Database error")
    
    result = agent.start_conversation()
    
    assert result is False
    assert agent.session_id is None
    
    # Check error was logged
    mock_logger.error.assert_called_once()
    assert "Failed to start conversation" in mock_logger.error.call_args[0][0]

def test_get_conversation_context(mock_config, mock_db_manager, mock_logger):
    """Test getting conversation context from database"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    agent.session_id = "test-session"
    
    mock_db_manager.get_recent_messages.return_value = [
        {"role": "user", "message": "Hello"},
        {"role": "assistant", "message": "Hi there"}
    ]
    
    context = agent.get_conversation_context()
    
    assert context == "user: Hello\nassistant: Hi there"
    mock_db_manager.get_recent_messages.assert_called_once_with("test-session")
    
    # Check logging
    mock_logger.debug.assert_any_call("Retrieved 2 messages for context")

def test_chat_with_db(mock_config, mock_db_manager, mock_logger):
    """Test chat flow with database integration"""
    agent = LLMQueryAgent(config=mock_config)
    agent.has_db = True
    agent.session_id = "test-session"
    
    # Mock query_llm to return a fixed response
    with patch.object(agent, 'query_llm', return_value="I am fine, thank you."):
        response = agent.chat("Hello, how are you?")
        
        # Verify DB interactions
        mock_db_manager.add_message.assert_any_call(
            "test-session", 
            "user", 
            "Hello, how are you?", 
            metadata={
                "type": "user_message", 
                "timestamp": mock.ANY,
                "agent_id": "llm_query_agent",
                "session": "test-session"
            }
        )
        
        mock_db_manager.add_message.assert_any_call(
            "test-session", 
            "assistant", 
            "I am fine, thank you.", 
            metadata={
                "type": "assistant_response", 
                "timestamp": mock.ANY,
                "agent_id": "llm_query_agent",
                "model": "test-model",
                "session": "test-session"
            }
        )
        
        assert response == "I am fine, thank you."
        
        # Check logging
        mock_logger.info.assert_any_call("Processing chat input (length: 19)")
        mock_logger.info.assert_any_call("Stored user message in database")
        mock_logger.info.assert_any_call("Stored assistant response in database")

def test_main_function(mock_config, monkeypatch, mock_logger):
    """Test the main function CLI interaction"""
    # Create a mock agent
    with patch('src.agents.ai_agent.LLMQueryAgent') as MockAgent:
        # Mock the agent instance
        mock_agent = Mock()
        MockAgent.return_value = mock_agent
        mock_agent.chat.return_value = "I am fine, thank you."
        
        # Mock input and print functions
        inputs = iter(["Hello", "exit"])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))
        monkeypatch.setattr('builtins.print', lambda *args, **kwargs: None)  # Suppress print output
        
        # Run the main function
        main()
        
        # Verify interactions
        assert mock_agent.chat.called
        mock_logger.info.assert_any_call("Starting LLM Agent CLI")
        mock_logger.info.assert_any_call("User requested exit. Shutting down.")
