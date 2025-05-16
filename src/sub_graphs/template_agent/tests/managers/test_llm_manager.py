"""
Tests for llm_manager.py

This module tests the LLM Manager functionality, including:
1. Initialization and configuration
2. Provider selection
3. Response generation
4. Stats tracking
5. Error handling
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from typing import Dict, Any, Optional, List

from ...src.common.managers.llm_manager import LLMManager, LLMUsageStats, LLMState
from ...src.common.services.llm_service import LLMService
from ...src.common.managers.state_models import Message, MessageType, MessageStatus
from ...src.common.managers.service_models import LLMServiceConfig


@pytest.fixture
def llm_config():
    """Create a test LLM configuration."""
    return LLMServiceConfig(
        api_url="http://localhost:11434",
        model_name="llama2",
        temperature=0.7,
        max_tokens=1000,
        stop_sequences=["User:", "Assistant:"]
    )


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    mock = AsyncMock(spec=LLMService)
    mock.generate = AsyncMock(return_value="This is a mock LLM response")
    mock.stream = AsyncMock(return_value=["This ", "is ", "a ", "mock ", "LLM ", "response"])
    return mock


@pytest.fixture
def llm_manager(llm_config):
    """Create an LLM manager with mocked service."""
    with patch('src.common.managers.llm_manager.LLMService') as mock_service_class:
        mock_service = AsyncMock(spec=LLMService)
        mock_service.generate = AsyncMock(return_value="This is a mock LLM response")
        mock_service_class.return_value = mock_service
        
        manager = LLMManager(llm_config)
        manager.service = mock_service  # Ensure we use our mocked service
        return manager


def test_initialization(llm_config):
    """Test LLM manager initialization."""
    # Test case: Normal operation - should pass
    with patch('src.common.managers.llm_manager.LLMService'):
        manager = LLMManager(llm_config)
        
        # Verify basic properties
        assert manager.model_name == "llama2"
        assert manager.temperature == 0.7
        assert manager.max_tokens == 1000
        assert manager.stop_sequences == ["User:", "Assistant:"]
        
        # Verify state
        assert manager.state.current_provider == "http://localhost:11434"
        assert manager.state.current_model == "llama2"
        assert isinstance(manager.state.stats, LLMUsageStats)


def test_llm_usage_stats_validation():
    """Test LLMUsageStats validation."""
    # Test case: Normal operation - should pass
    stats = LLMUsageStats()
    assert stats.total_requests == 0
    assert stats.total_tokens == 0
    assert stats.total_errors == 0
    assert stats.average_latency == 0.0
    assert stats.request_history == []
    
    # Initialize with custom values
    stats = LLMUsageStats(
        total_requests=10,
        total_tokens=1000,
        total_errors=2,
        average_latency=0.5,
        last_request=datetime.now()
    )
    assert stats.total_requests == 10
    assert stats.total_tokens == 1000
    assert stats.total_errors == 2
    assert stats.average_latency == 0.5
    assert stats.last_request is not None


def test_llm_state_validation():
    """Test LLMState validation."""
    # Test case: Normal operation - should pass
    state = LLMState()
    assert isinstance(state.stats, LLMUsageStats)
    assert state.cache == {}
    assert state.current_provider is None
    assert state.current_model is None
    
    # Initialize with custom values
    stats = LLMUsageStats(total_requests=5)
    state = LLMState(
        stats=stats,
        cache={"test_prompt": ("test_response", datetime.now())},
        current_provider="ollama",
        current_model="llama2"
    )
    assert state.stats.total_requests == 5
    assert "test_prompt" in state.cache
    assert state.current_provider == "ollama"
    assert state.current_model == "llama2"


@pytest.mark.asyncio
async def test_choose_provider(llm_manager):
    """Test provider selection based on query type and token balances."""
    # Test case: Normal operation - should pass
    with patch('src.common.managers.llm_manager.get_provider_config') as mock_get_config:
        mock_get_config.return_value = {"api_url": "http://test.provider", "default_model": "test_model"}
        
        # Code query should use ollama
        provider = await llm_manager.choose_provider("code", {"anthropic": 2000})
        mock_get_config.assert_called_with("ollama")
        
        # Chat query with low anthropic balance should use openai
        provider = await llm_manager.choose_provider("chat", {"anthropic": 500})
        mock_get_config.assert_called_with("openai")
        
        # Chat query with high anthropic balance should use anthropic
        provider = await llm_manager.choose_provider("chat", {"anthropic": 2000})
        mock_get_config.assert_called_with("anthropic")


@pytest.mark.asyncio
async def test_choose_provider_error(llm_manager):
    """Test error handling in provider selection."""
    # Test case: Error condition - should fail but handle gracefully
    with patch('src.common.managers.llm_manager.get_provider_config', side_effect=Exception("Provider not found")):
        with pytest.raises(RuntimeError) as excinfo:
            await llm_manager.choose_provider("chat", {})
        
        assert "Failed to choose provider" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_service_for_query(llm_manager):
    """Test getting a service for a specific query."""
    # Test case: Normal operation - should pass
    with patch('src.common.managers.llm_manager.LLMService') as mock_service_class:
        mock_service = MagicMock(spec=LLMService)
        mock_service_class.return_value = mock_service
        
        with patch.object(llm_manager, 'choose_provider') as mock_choose_provider:
            mock_choose_provider.return_value = {
                "api_url": "http://test.provider",
                "default_model": "test_model"
            }
            
            service = await llm_manager.get_service_for_query("chat", {}, "user-1")
            
            # Verify provider was chosen correctly
            mock_choose_provider.assert_called_with("chat", {}, "user-1")
            
            # Verify service was created with correct parameters
            mock_service_class.assert_called_with(
                api_url="http://test.provider",
                model="test_model"
            )


@pytest.mark.asyncio
async def test_update_stats(llm_manager):
    """Test updating LLM usage statistics."""
    # Test case: Normal operation - should pass
    
    # Initial state
    assert llm_manager.state.stats.total_requests == 0
    assert llm_manager.state.stats.total_tokens == 0
    
    # Update stats
    await llm_manager.update_stats(tokens=100, latency=0.5)
    
    # Verify stats were updated
    assert llm_manager.state.stats.total_requests == 1
    assert llm_manager.state.stats.total_tokens == 100
    assert llm_manager.state.stats.average_latency == 0.5
    assert llm_manager.state.stats.last_request is not None
    assert len(llm_manager.state.stats.request_history) == 1
    
    # Update stats again
    await llm_manager.update_stats(tokens=200, latency=1.0)
    
    # Verify stats were updated
    assert llm_manager.state.stats.total_requests == 2
    assert llm_manager.state.stats.total_tokens == 300
    # Average latency should be (0.5 + 1.0) / 2 = 0.75
    assert llm_manager.state.stats.average_latency == 0.75
    assert len(llm_manager.state.stats.request_history) == 2


@pytest.mark.asyncio
async def test_update_stats_error(llm_manager):
    """Test updating stats with an error."""
    # Test case: Error condition - should handle properly
    
    # Update stats with error
    await llm_manager.update_stats(tokens=0, latency=0.0, error=True)
    
    # Verify error count was incremented
    assert llm_manager.state.stats.total_errors == 1
    assert llm_manager.state.stats.request_history[0]["error"] is True


@pytest.mark.asyncio
async def test_update_stats_history_limit(llm_manager):
    """Test that request history is limited to most recent 100 requests."""
    # Test case: Edge case - history size limit
    
    # Add 101 requests
    for i in range(101):
        await llm_manager.update_stats(tokens=i, latency=0.1 * i)
    
    # Verify history is limited to 100 entries
    assert len(llm_manager.state.stats.request_history) == 100
    # Verify oldest requests were removed (should start from i=1)
    assert llm_manager.state.stats.request_history[0]["tokens"] == 1


@pytest.mark.asyncio
async def test_generate_response_success(llm_manager):
    """Test successful response generation."""
    # Test case: Normal operation - should pass
    
    # Mock service.generate to return a response
    llm_manager.service.generate.reset_mock()
    llm_manager.service.generate.return_value = "This is a test response"
    
    # Generate response
    response = await llm_manager.generate_response("Test prompt", {"user_id": "user-1"})
    
    # Verify response
    assert response.content == "This is a test response"
    assert response.type == MessageType.RESPONSE
    assert response.status == MessageStatus.SUCCESS
    
    # Verify service was called correctly
    llm_manager.service.generate.assert_called_once_with(
        prompt="Test prompt",
        temperature=0.7,
        max_tokens=1000,
        stop=["User:", "Assistant:"]
    )
    
    # Verify stats were updated
    assert llm_manager.state.stats.total_requests == 1
    assert llm_manager.state.stats.total_tokens > 0


@pytest.mark.asyncio
async def test_generate_response_error(llm_manager):
    """Test error handling in response generation."""
    # Test case: Error condition - should fail but return error message
    
    # Mock service.generate to raise an exception
    llm_manager.service.generate.reset_mock()
    llm_manager.service.generate.side_effect = Exception("LLM service failed")
    
    # Generate response
    response = await llm_manager.generate_response("Test prompt")
    
    # Verify response is an error message
    assert "Error generating LLM response" in response.content
    assert response.type == MessageType.ERROR
    assert response.status == MessageStatus.ERROR
    assert "error" in response.data
    assert "LLM service failed" in response.data["error"]
    
    # Verify stats were updated
    assert llm_manager.state.stats.total_errors == 1


@pytest.mark.asyncio
async def test_stream_response(llm_manager):
    """Test streaming a response."""
    # Mock stream method to return chunks
    llm_manager.service.stream = AsyncMock(return_value=[
        "This ", "is ", "a ", "test ", "response."
    ])
    
    # Stream response
    async for chunk in llm_manager.stream_response("Test prompt"):
        # Verify chunk is a Message
        assert isinstance(chunk, Message)
        assert chunk.type == MessageType.STREAM
        assert chunk.content in ["This ", "is ", "a ", "test ", "response."]
    
    # Verify service was called correctly
    llm_manager.service.stream.assert_called_once_with(
        prompt="Test prompt",
        temperature=0.7,
        max_tokens=1000,
        stop=["User:", "Assistant:"]
    )


@pytest.mark.asyncio
async def test_stream_response_error(llm_manager):
    """Test error handling in response streaming."""
    # Mock stream method to raise an exception
    llm_manager.service.stream = AsyncMock(side_effect=Exception("Streaming failed"))
    
    # Stream response and collect chunks
    chunks = []
    async for chunk in llm_manager.stream_response("Test prompt"):
        chunks.append(chunk)
    
    # Should get a single error message
    assert len(chunks) == 1
    assert chunks[0].type == MessageType.ERROR
    assert chunks[0].status == MessageStatus.ERROR
    assert "Error streaming LLM response" in chunks[0].content
    
    # Verify stats were updated
    assert llm_manager.state.stats.total_errors == 1 