"""Tests for the LLMManager class."""

import pytest
from unittest.mock import Mock, patch
from src.managers.llm_manager import LLMManager
from src.services.llm_service import LLMService

@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    service = Mock(spec=LLMService)
    service.get_response.return_value = "Test response"
    service.get_embedding.return_value = [0.1, 0.2, 0.3]
    return service

@pytest.fixture
def llm_manager(mock_llm_service):
    """Create an LLMManager instance with a mock service."""
    return LLMManager(llm_service=mock_llm_service)

def test_get_response(llm_manager, mock_llm_service):
    """Test getting a response from the LLM."""
    messages = [{"role": "user", "content": "Hello"}]
    response = llm_manager.get_response(messages)
    
    assert response == "Test response"
    mock_llm_service.get_response.assert_called_once_with(messages)
    
    # Test caching
    llm_manager.get_response(messages)
    assert mock_llm_service.get_response.call_count == 1  # Should use cache

def test_get_embedding(llm_manager, mock_llm_service):
    """Test getting embeddings from the LLM."""
    text = "Test text"
    embedding = llm_manager.get_embedding(text)
    
    assert embedding == [0.1, 0.2, 0.3]
    mock_llm_service.get_embedding.assert_called_once_with(text)
    
    # Test caching
    llm_manager.get_embedding(text)
    assert mock_llm_service.get_embedding.call_count == 1  # Should use cache

def test_get_stats(llm_manager):
    """Test retrieving usage statistics."""
    messages = [{"role": "user", "content": "Hello"}]
    llm_manager.get_response(messages)
    
    stats = llm_manager.get_stats()
    assert isinstance(stats, dict)
    assert stats["total_requests"] == 1
    assert "average_latency" in stats

def test_clear_cache(llm_manager, mock_llm_service):
    """Test clearing the response and embedding caches."""
    messages = [{"role": "user", "content": "Hello"}]
    text = "Test text"
    
    # Populate caches
    llm_manager.get_response(messages)
    llm_manager.get_embedding(text)
    
    # Clear caches
    llm_manager.clear_cache()
    
    # Verify caches are cleared by checking if service is called again
    llm_manager.get_response(messages)
    llm_manager.get_embedding(text)
    assert mock_llm_service.get_response.call_count == 2
    assert mock_llm_service.get_embedding.call_count == 2

def test_error_handling(llm_manager, mock_llm_service):
    """Test error handling in the manager."""
    mock_llm_service.get_response.side_effect = Exception("Test error")
    
    messages = [{"role": "user", "content": "Hello"}]
    with pytest.raises(Exception) as exc_info:
        llm_manager.get_response(messages)
    
    assert str(exc_info.value) == "Test error"
    assert llm_manager.get_stats()["total_errors"] == 1 