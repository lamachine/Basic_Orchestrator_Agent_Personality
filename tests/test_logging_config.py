"""Tests for the logging configuration module."""

import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

from src.config import Configuration
from src.config.logging_config import setup_logging


class TestConfig:
    """Mock configuration class for testing."""

    file_level = "INFO"
    console_level = "DEBUG"


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    return TestConfig()


@pytest.fixture
def mock_filesystem():
    """Mock filesystem operations."""
    with (
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("pathlib.Path.exists", return_value=False),
    ):
        yield mock_mkdir


def test_setup_logging_creates_handlers(mock_config, mock_filesystem):
    """Test that setup_logging creates file and console handlers."""
    with (
        patch("logging.FileHandler") as mock_file_handler,
        patch("logging.StreamHandler") as mock_stream_handler,
        patch("logging.getLogger", return_value=MagicMock()) as mock_get_logger,
    ):

        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()

        # Call function
        file_handler, console_handler = setup_logging(mock_config)

        # Check log directory was created
        mock_filesystem.assert_called_once()

        # Check handlers were created
        mock_file_handler.assert_called_once()
        mock_stream_handler.assert_called_once()

        # Check log levels were set
        assert file_handler.setLevel.call_args[0][0] == logging.INFO
        assert console_handler.setLevel.call_args[0][0] == logging.DEBUG


def test_setup_logging_with_different_levels():
    """Test that setup_logging respects different log levels."""
    config = Configuration(file_level="ERROR", console_level="WARNING")

    with (
        patch("logging.FileHandler", return_value=MagicMock()) as mock_file_handler,
        patch("logging.StreamHandler", return_value=MagicMock()) as mock_stream_handler,
        patch("logging.getLogger", return_value=MagicMock()),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.exists", return_value=False),
    ):

        # Setup mocks
        mock_file_handler.return_value = MagicMock()
        mock_stream_handler.return_value = MagicMock()

        # Call function
        file_handler, console_handler = setup_logging(config)

        # Check log levels were set
        assert file_handler.setLevel.call_args[0][0] == logging.ERROR
        assert console_handler.setLevel.call_args[0][0] == logging.WARNING


def test_setup_logging_handles_errors():
    """Test that setup_logging gracefully handles errors."""
    config = TestConfig()

    # Create a FileHandler mock that raises an exception only on first call
    file_handler_mock = MagicMock()
    call_count = 0

    def mock_file_handler(*args, **kwargs):
        nonlocal call_count
        if call_count == 0:
            call_count += 1
            raise PermissionError("Permission denied")
        return MagicMock()

    # Simulate an error creating the file handler
    with (
        patch("logging.FileHandler", side_effect=mock_file_handler),
        patch("logging.StreamHandler", return_value=MagicMock()) as mock_stream_handler,
        patch("logging.error") as mock_logging_error,
        patch("pathlib.Path.mkdir"),
    ):

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
