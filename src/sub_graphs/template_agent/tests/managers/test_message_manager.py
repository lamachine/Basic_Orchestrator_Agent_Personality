"""
Tests for message_manager.py

This module tests the message management functionality, including:
1. Adding swarm messages to memory
2. Searching swarm messages from memory
3. Error handling
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

from ...src.common.managers.message_manager import add_swarm_message, search_swarm_messages
from ...src.common.managers.memory_manager import Mem0Memory, SwarmMessage


@pytest.fixture
def mock_mem0():
    """Create a mock Mem0Memory instance."""
    mock = MagicMock(spec=Mem0Memory)
    mock.add_memory = MagicMock(return_value={"status": "success", "id": "test-id-1234"})
    mock.search_memory = MagicMock(return_value={
        "results": [
            {
                "id": "mem-1",
                "content": "Test memory 1",
                "metadata": {"user_id": "user-1", "tag": "test"},
                "similarity": 0.95
            },
            {
                "id": "mem-2",
                "content": "Test memory 2",
                "metadata": {"user_id": "user-2", "tag": "test"},
                "similarity": 0.85
            },
            {
                "id": "mem-3",
                "content": "Test memory 3",
                "metadata": {"user_id": "user-1", "tag": "other"},
                "similarity": 0.75
            }
        ]
    })
    return mock


@pytest.mark.asyncio
async def test_add_swarm_message_success(mock_mem0):
    """Test successful addition of a swarm message."""
    # Mock Mem0Memory
    with patch('common.managers.message_manager.mem0', mock_mem0):
        # Add message
        result = await add_swarm_message("Test content", "user-1", {"tag": "test"})
        
        # Verify result
        assert result["status"] == "success"
        assert result["id"] == "test-id-1234"
        
        # Verify Mem0Memory.add_memory was called correctly
        mock_mem0.add_memory.assert_called_once()
        call_args = mock_mem0.add_memory.call_args[0][0]
        assert isinstance(call_args, SwarmMessage)
        assert call_args.content == "Test content"
        assert call_args.user_id == "user-1"
        assert call_args.metadata == {"tag": "test"}


@pytest.mark.asyncio
async def test_add_swarm_message_no_metadata(mock_mem0):
    """Test adding a swarm message without metadata."""
    # Mock Mem0Memory
    with patch('common.managers.message_manager.mem0', mock_mem0):
        # Add message without metadata
        result = await add_swarm_message("Test content", "user-1")
        
        # Verify result
        assert result["status"] == "success"
        assert result["id"] == "test-id-1234"
        
        # Verify Mem0Memory.add_memory was called correctly
        mock_mem0.add_memory.assert_called_once()
        call_args = mock_mem0.add_memory.call_args[0][0]
        assert call_args.metadata == {}


@pytest.mark.asyncio
async def test_add_swarm_message_error():
    """Test error handling when adding a swarm message."""
    # Mock Mem0Memory to raise an exception
    mock_error_mem0 = MagicMock(spec=Mem0Memory)
    mock_error_mem0.add_memory = MagicMock(side_effect=RuntimeError("Failed to add memory"))
    
    with patch('common.managers.message_manager.mem0', mock_error_mem0):
        # Verify error is raised
        with pytest.raises(RuntimeError) as excinfo:
            await add_swarm_message("Test content", "user-1")
        
        assert "Failed to add memory" in str(excinfo.value)
        
        # Verify Mem0Memory.add_memory was called
        mock_error_mem0.add_memory.assert_called_once()


@pytest.mark.asyncio
async def test_search_swarm_messages_success(mock_mem0):
    """Test successful search of swarm messages."""
    # Mock Mem0Memory
    with patch('common.managers.message_manager.mem0', mock_mem0):
        # Search messages
        result = await search_swarm_messages("test query", "user-1", top_k=3)
        
        # Verify result
        assert "results" in result
        assert len(result["results"]) == 2  # Only user-1's messages should be returned
        assert result["results"][0]["id"] == "mem-1"
        assert result["results"][1]["id"] == "mem-3"
        
        # Verify Mem0Memory.search_memory was called correctly
        mock_mem0.search_memory.assert_called_once_with("test query", top_k=3)


@pytest.mark.asyncio
async def test_search_swarm_messages_empty_results(mock_mem0):
    """Test searching swarm messages with empty results."""
    # Mock Mem0Memory with empty results
    mock_empty_mem0 = MagicMock(spec=Mem0Memory)
    mock_empty_mem0.search_memory = MagicMock(return_value={"results": []})
    
    with patch('common.managers.message_manager.mem0', mock_empty_mem0):
        # Search messages
        result = await search_swarm_messages("nonexistent query", "user-1")
        
        # Verify result
        assert "results" in result
        assert len(result["results"]) == 0
        
        # Verify Mem0Memory.search_memory was called
        mock_empty_mem0.search_memory.assert_called_once()


@pytest.mark.asyncio
async def test_search_swarm_messages_error():
    """Test error handling when searching swarm messages."""
    # Mock Mem0Memory to raise an exception
    mock_error_mem0 = MagicMock(spec=Mem0Memory)
    mock_error_mem0.search_memory = MagicMock(side_effect=RuntimeError("Search failed"))
    
    with patch('common.managers.message_manager.mem0', mock_error_mem0):
        # Verify error is raised
        with pytest.raises(RuntimeError) as excinfo:
            await search_swarm_messages("test query", "user-1")
        
        assert "Search failed" in str(excinfo.value)
        
        # Verify Mem0Memory.search_memory was called
        mock_error_mem0.search_memory.assert_called_once()


@pytest.mark.asyncio
async def test_search_swarm_messages_no_results_key(mock_mem0):
    """Test handling of malformed response from memory search."""
    # Mock Mem0Memory with malformed response
    mock_malformed_mem0 = MagicMock(spec=Mem0Memory)
    mock_malformed_mem0.search_memory = MagicMock(return_value={"status": "success"})  # No "results" key
    
    with patch('common.managers.message_manager.mem0', mock_malformed_mem0):
        # Search messages
        result = await search_swarm_messages("test query", "user-1")
        
        # Verify result
        assert "results" in result
        assert len(result["results"]) == 0
        
        # Verify Mem0Memory.search_memory was called
        mock_malformed_mem0.search_memory.assert_called_once()


@pytest.mark.asyncio
async def test_search_swarm_messages_user_filter_edge_case():
    """Test edge case where user filter results in no matches."""
    # Create mock with results for different user
    mock_other_user_mem0 = MagicMock(spec=Mem0Memory)
    mock_other_user_mem0.search_memory = MagicMock(return_value={
        "results": [
            {
                "id": "mem-1",
                "content": "Test memory 1",
                "metadata": {"user_id": "user-2", "tag": "test"},
                "similarity": 0.95
            },
            {
                "id": "mem-2",
                "content": "Test memory 2",
                "metadata": {"user_id": "user-3", "tag": "test"},
                "similarity": 0.85
            }
        ]
    })
    
    with patch('common.managers.message_manager.mem0', mock_other_user_mem0):
        # Search messages for user-1
        result = await search_swarm_messages("test query", "user-1")
        
        # Verify result has no matches for user-1
        assert "results" in result
        assert len(result["results"]) == 0 