"""Tests for the logging configuration module."""

import os
import logging
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from src.config import Configuration
from src.config.logging_config import setup_logging

class TestConfig:
    """Mock configuration class for testing."""
    file_level = 'INFO'
    console_level = 'DEBUG'

@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    return TestConfig()

@pytest.fixture
def mock_filesystem():
    """Mock filesystem operations."""
    with patch('pathlib.Path.mkdir') as mock_mkdir:
        yield mock_mkdir

def test_setup_logging_creates_handlers(mock_config, mock_filesystem):
    """Test that setup_logging creates file and console handlers."""
    with patch('logging.FileHandler') as mock_file_handler, \
         patch('logging.StreamHandler') as mock_stream_handler:
        
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        # Call function
        file_handler, console_handler = setup_logging(mock_config)
        
        # Check log directory was created
        mock_filesystem.assert_called_once_with(exist_ok=True)
        
        # Check handlers were created
        mock_file_handler.assert_called_once()
        mock_stream_handler.assert_called_once()
        
        # Check log levels were set
        file_handler.setLevel.assert_called_once_with(logging.INFO)
        console_handler.setLevel.assert_called_once_with(logging.DEBUG)

def test_setup_logging_with_different_levels():
    """Test that setup_logging respects different log levels."""
    config = Configuration(file_level='ERROR', console_level='WARNING')
    
    with patch('logging.FileHandler') as mock_file_handler, \
         patch('logging.StreamHandler') as mock_stream_handler, \
         patch('pathlib.Path.mkdir'):
        
        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()
        
        # Call function
        file_handler, console_handler = setup_logging(config)
        
        # Check log levels were set
        file_handler.setLevel.assert_called_once_with(logging.ERROR)
        console_handler.setLevel.assert_called_once_with(logging.WARNING)

def test_setup_logging_handles_errors():
    """Test that setup_logging gracefully handles errors."""
    config = TestConfig()
    
    # Simulate an error creating the file handler
    with patch('logging.FileHandler', side_effect=PermissionError("Permission denied")), \
         patch('logging.StreamHandler') as mock_stream_handler, \
         patch('logging.error') as mock_logging_error, \
         patch('pathlib.Path.mkdir'):
        
        # Setup mocks
        mock_stream_handler.return_value = MagicMock()
        
        # Call function - should not raise an exception
        fallback_file, fallback_console = setup_logging(config)
        
        # Check fallback logger was setup
        assert fallback_file is not None
        assert fallback_console is not None
        
        # Check error was logged
        mock_logging_error.assert_called_once()
        assert "Logging setup failed" in mock_logging_error.call_args[0][0] 