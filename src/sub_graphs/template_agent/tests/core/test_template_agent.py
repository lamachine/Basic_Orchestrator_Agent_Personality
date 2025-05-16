"""Tests for template agent functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from ..src.specialty.agents.template_agent import TemplateAgent
from ..src.common.state.state_models import MessageRole

@pytest.mark.asyncio
async def test_chat_basic_functionality(template_agent, mock_llm_response):
    """Test basic chat functionality without logging."""
    # Mock LLM response
    template_agent.query_llm = Mock(return_value=mock_llm_response)
    
    result = await template_agent.chat("test input")
    
    assert result["status"] == "success"
    assert result["response"] == mock_llm_response
    template_agent.query_llm.assert_called_once_with("test input")

@pytest.mark.asyncio
async def test_chat_with_logging(template_agent, mock_session_state, mock_llm_response):
    """Test chat functionality with logging enabled."""
    # Mock LLM response and logging
    template_agent.query_llm = Mock(return_value=mock_llm_response)
    template_agent.graph_state = mock_session_state
    
    # Create a mock for add_message to track calls
    message_log = []
    template_agent.graph_state["conversation_state"]["add_message"] = \
        Mock(side_effect=lambda **kwargs: message_log.append(kwargs))
    
    result = await template_agent.chat("test input")
    
    # Verify result
    assert result["status"] == "success"
    assert result["response"] == mock_llm_response
    
    # Verify logging calls
    assert len(message_log) == 2  # Should have logged query and response
    
    # Verify query log
    query_log = message_log[0]
    assert query_log["role"] == MessageRole.SYSTEM
    assert "Sending query to LLM" in query_log["content"]
    assert query_log["metadata"]["message_type"] == "llm_query"
    
    # Verify response log
    response_log = message_log[1]
    assert response_log["role"] == MessageRole.ASSISTANT
    assert response_log["content"] == mock_llm_response
    assert response_log["metadata"]["message_type"] == "llm_response"

@pytest.mark.asyncio
async def test_chat_with_history(template_agent, mock_llm_response):
    """Test chat history tracking."""
    # Mock LLM response
    template_agent.query_llm = Mock(return_value=mock_llm_response)
    
    # Enable history
    template_agent.conversation_history = []
    
    result = await template_agent.chat("test input")
    
    # Verify history was updated
    assert len(template_agent.conversation_history) == 1
    history_entry = template_agent.conversation_history[0]
    assert history_entry["user"] == "test input"
    assert history_entry["assistant"] == mock_llm_response
    assert "timestamp" in history_entry

@pytest.mark.asyncio
async def test_chat_error_handling(template_agent):
    """Test chat error handling."""
    # Mock LLM to raise an exception
    template_agent.query_llm = Mock(side_effect=Exception("Test error"))
    
    result = await template_agent.chat("test input")
    
    assert result["status"] == "error"
    assert "Test error" in result["response"]

@pytest.mark.asyncio
async def test_chat_with_logging_disabled(template_agent, mock_session_state, mock_llm_response):
    """Test chat functionality with logging disabled."""
    # Mock LLM response
    template_agent.query_llm = Mock(return_value=mock_llm_response)
    template_agent.graph_state = mock_session_state
    template_agent.config["enable_logging"] = False
    
    # Create a mock for add_message to verify it's not called
    template_agent.graph_state["conversation_state"]["add_message"] = Mock()
    
    result = await template_agent.chat("test input")
    
    assert result["status"] == "success"
    assert result["response"] == mock_llm_response
    template_agent.graph_state["conversation_state"]["add_message"].assert_not_called() 