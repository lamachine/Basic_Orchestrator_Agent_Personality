"""
Unit tests for the LLM service.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from ...src.common.services.llm_service import LLMService
from ...src.common.models.state_models import Message, MessageType, MessageStatus
from ...src.common.models.service_models import LLMServiceConfig

@pytest.fixture
def config() -> LLMServiceConfig:
    """Create a test configuration."""
    return LLMServiceConfig(
        name="test_llm_service",
        enabled=True,
        config={
            "model_name": "test_model",
            "temperature": 0.7,
            "max_tokens": 100,
            "stop_sequences": ["\n", "Human:", "Assistant:"],
            "api_url": "http://localhost:11434/api"
        }
    )

@pytest.fixture
def llm_service(config: LLMServiceConfig) -> LLMService:
    """Create a test LLM service."""
    return LLMService(config)

def test_initialization(llm_service: LLMService):
    """Test service initialization."""
    assert llm_service.model == "test_model"
    assert llm_service.temperature == 0.7
    assert llm_service.max_tokens == 100
    assert llm_service.stop_sequences == ["\n", "Human:", "Assistant:"]
    assert llm_service.api_url == "http://localhost:11434/api"

@pytest.mark.asyncio
async def test_generate(llm_service: LLMService, mocker):
    """Test text generation."""
    # Mock HTTP client
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": "Test response",
        "model": "test_model",
        "created_at": datetime.now().isoformat(),
        "done": True
    }
    
    mock_client = mocker.Mock()
    mock_client.post = mocker.AsyncMock(return_value=mock_response)
    llm_service.client = mock_client
    
    # Generate text
    response = await llm_service.generate("Test prompt")
    assert response == "Test response"
    
    # Check client call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args[1]
    assert call_args["json"]["model"] == "test_model"
    assert call_args["json"]["prompt"] == "Test prompt"
    assert call_args["json"]["temperature"] == 0.7
    assert call_args["json"]["max_tokens"] == 100
    assert call_args["json"]["stop"] == ["\n", "Human:", "Assistant:"]

@pytest.mark.asyncio
async def test_get_response(llm_service: LLMService, mocker):
    """Test getting response with conversation history."""
    # Mock generate method
    mocker.patch.object(llm_service, "generate", return_value="Test response")
    
    # Create test messages
    messages = [
        Message(
            request_id="test_request",
            type=MessageType.REQUEST,
            status=MessageStatus.COMPLETED,
            timestamp=datetime.now(),
            content="Test message"
        )
    ]
    
    # Get response
    response = await llm_service.get_response(
        system_prompt="Test system prompt",
        conversation_history=messages
    )
    
    assert response == "Test response"
    
    # Check format_messages call
    formatted_prompt = await llm_service.format_messages(messages, "Test system prompt")
    assert "System: Test system prompt" in formatted_prompt
    assert "User: Test message" in formatted_prompt

@pytest.mark.asyncio
async def test_get_embedding(llm_service: LLMService, mocker):
    """Test getting embeddings."""
    # Mock HTTP client
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "embedding": [0.1, 0.2, 0.3]
    }
    
    mock_client = mocker.Mock()
    mock_client.post = mocker.AsyncMock(return_value=mock_response)
    llm_service.client = mock_client
    
    # Get embedding
    embedding = await llm_service.get_embedding("Test text")
    assert embedding == [0.1, 0.2, 0.3]
    
    # Check client call
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args[1]
    assert call_args["json"]["model"] == "test_model"
    assert call_args["json"]["prompt"] == "Test text"

@pytest.mark.asyncio
async def test_format_messages(llm_service: LLMService):
    """Test formatting messages."""
    # Create test messages
    messages = [
        Message(
            request_id="test_request",
            type=MessageType.REQUEST,
            status=MessageStatus.COMPLETED,
            timestamp=datetime.now(),
            content="Test user message"
        ),
        Message(
            request_id="test_response",
            type=MessageType.RESPONSE,
            status=MessageStatus.COMPLETED,
            timestamp=datetime.now(),
            content="Test assistant message"
        )
    ]
    
    # Format messages
    formatted = await llm_service.format_messages(messages, "Test system prompt")
    
    assert "System: Test system prompt" in formatted
    assert "User: Test user message" in formatted
    assert "Assistant: Test assistant message" in formatted

def test_get_stats(llm_service: LLMService):
    """Test getting service statistics."""
    stats = llm_service.get_stats()
    assert isinstance(stats, dict)
    assert stats["model"] == "test_model"
    assert stats["temperature"] == 0.7
    assert stats["max_tokens"] == 100
    assert stats["stop_sequences"] == ["\n", "Human:", "Assistant:"]
    assert stats["api_url"] == "http://localhost:11434/api" 