"""
Tests for memory_manager.py

This module tests the mem0 memory integration, including:
1. Adding memories
2. Searching memories
3. Error handling
"""

import json
import subprocess
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from ...src.common.managers.memory_manager import Mem0Memory, SwarmMessage


@pytest.fixture
def mock_subprocess_success():
    """Create a mock for subprocess.run that returns success."""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = json.dumps({"status": "success", "id": "test-id-1234"})
    return mock_process


@pytest.fixture
def mock_subprocess_error():
    """Create a mock for subprocess.run that returns an error."""
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stderr = "Memory operation failed"
    return mock_process


@pytest.fixture
def mock_search_results():
    """Create mock search results."""
    return json.dumps(
        {
            "results": [
                {
                    "id": "mem-1",
                    "content": "This is a test memory",
                    "metadata": {"user_id": "user-1", "tag": "test"},
                    "similarity": 0.95,
                },
                {
                    "id": "mem-2",
                    "content": "Another test memory",
                    "metadata": {"user_id": "user-1", "tag": "example"},
                    "similarity": 0.85,
                },
            ]
        }
    )


def test_swarm_message_validation():
    """Test SwarmMessage validation."""
    # Test case: Normal operation - should pass
    message = SwarmMessage(content="Test content", user_id="user-1")
    assert message.content == "Test content"
    assert message.user_id == "user-1"
    assert message.metadata == {}

    # Test with metadata
    message = SwarmMessage(
        content="Test content",
        user_id="user-1",
        metadata={"tag": "test", "importance": "high"},
    )
    assert message.metadata["tag"] == "test"
    assert message.metadata["importance"] == "high"

    # Test case: Missing required fields - should fail
    with pytest.raises(ValueError):
        SwarmMessage(content="Missing user_id")

    # Test case: Empty content - edge case
    message = SwarmMessage(content="", user_id="user-1")
    assert message.content == ""


def test_memory_initialization():
    """Test Mem0Memory initialization."""
    # Default config path
    memory = Mem0Memory()
    assert memory.config_path == "mem0.config.json"

    # Custom config path
    memory = Mem0Memory(config_path="custom/path/config.json")
    assert memory.config_path == "custom/path/config.json"


def test_add_memory_success(mock_subprocess_success):
    """Test successful memory addition."""
    # Create test message
    message = SwarmMessage(content="Test memory", user_id="user-1", metadata={"tag": "test"})

    # Mock subprocess call
    with patch("subprocess.run", return_value=mock_subprocess_success) as mock_run:
        memory = Mem0Memory()
        result = memory.add_memory(message)

        # Verify result
        assert result["status"] == "success"
        assert result["id"] == "test-id-1234"

        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "npx" in args
        assert "mem0" in args
        assert "add" in args
        assert "--content" in args
        assert "Test memory" in args
        assert "--metadata" in args
        assert json.dumps({"tag": "test"}) in args


def test_add_memory_error(mock_subprocess_error):
    """Test memory addition with error."""
    # Create test message
    message = SwarmMessage(content="Test memory", user_id="user-1")

    # Mock subprocess call
    with patch("subprocess.run", return_value=mock_subprocess_error) as mock_run:
        memory = Mem0Memory()

        # Verify error is raised
        with pytest.raises(RuntimeError) as excinfo:
            memory.add_memory(message)

        assert "mem0 add failed" in str(excinfo.value)

        # Verify subprocess was called
        mock_run.assert_called_once()


def test_search_memory_success(mock_search_results):
    """Test successful memory search."""
    # Mock subprocess call
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = mock_search_results

    with patch("subprocess.run", return_value=mock_process) as mock_run:
        memory = Mem0Memory()
        result = memory.search_memory("test query", top_k=2)

        # Verify result
        assert "results" in result
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == "mem-1"
        assert result["results"][1]["id"] == "mem-2"

        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "npx" in args
        assert "mem0" in args
        assert "search" in args
        assert "--query" in args
        assert "test query" in args
        assert "--top_k" in args
        assert "2" in args


def test_search_memory_error(mock_subprocess_error):
    """Test memory search with error."""
    # Mock subprocess call
    with patch("subprocess.run", return_value=mock_subprocess_error) as mock_run:
        memory = Mem0Memory()

        # Verify error is raised
        with pytest.raises(RuntimeError) as excinfo:
            memory.search_memory("test query")

        assert "mem0 search failed" in str(excinfo.value)

        # Verify subprocess was called
        mock_run.assert_called_once()


def test_search_memory_empty_results():
    """Test memory search with empty results (edge case)."""
    # Mock subprocess call
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = json.dumps({"results": []})

    with patch("subprocess.run", return_value=mock_process) as mock_run:
        memory = Mem0Memory()
        result = memory.search_memory("nonexistent query")

        # Verify result
        assert "results" in result
        assert len(result["results"]) == 0

        # Verify subprocess was called
        mock_run.assert_called_once()


def test_subprocess_exception_handling():
    """Test handling of subprocess exceptions."""
    # Mock subprocess call that raises an exception
    with patch("subprocess.run", side_effect=Exception("Command not found")) as mock_run:
        memory = Mem0Memory()

        # Verify error is raised
        with pytest.raises(Exception) as excinfo:
            memory.add_memory(SwarmMessage(content="Test", user_id="user-1"))

        assert "Command not found" in str(excinfo.value)

        # Verify subprocess was called
        mock_run.assert_called_once()
