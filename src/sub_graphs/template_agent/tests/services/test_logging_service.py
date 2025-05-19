"""
Unit tests for the logging service.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest

from ...src.common.config import LoggingServiceConfig
from ...src.common.services.logging_service import LoggingService


@pytest.fixture
def config() -> LoggingServiceConfig:
    """Create a test configuration."""
    return LoggingServiceConfig(
        name="test_logging_service",
        enabled=True,
        config={
            "log_level": "DEBUG",
            "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_dir": "./test_logs",
            "file_level": "DEBUG",
            "console_level": "INFO",
            "max_log_size_mb": 1,
            "backup_count": 3,
            "noisy_loggers": ["test_noisy"],
        },
    )


@pytest.fixture
def logging_service(config: LoggingServiceConfig):
    """Create a test logging service."""
    service = LoggingService(config)
    yield service
    # Cleanup after tests
    if os.path.exists("./test_logs"):
        for file in Path("./test_logs").glob("*.log"):
            file.unlink()
        Path("./test_logs").rmdir()


def test_initialization(logging_service: LoggingService):
    """Test service initialization."""
    assert logging_service.config is not None
    assert logging_service.config.name == "test_logging_service"


def test_get_logger(logging_service: LoggingService):
    """Test getting a logger instance."""
    logger = logging_service.get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"


def test_log_exception(logging_service: LoggingService, caplog):
    """Test logging an exception."""
    logger = logging_service.get_logger("test_logger")
    try:
        raise ValueError("Test error")
    except ValueError as e:
        logging_service.log_exception(logger, e, "Test exception")

    assert "Test error" in caplog.text
    assert "Test exception" in caplog.text


def test_log_levels(logging_service: LoggingService, caplog):
    """Test different log levels."""
    logger = logging_service.get_logger("test_logger")

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    assert "Debug message" in caplog.text
    assert "Info message" in caplog.text
    assert "Warning message" in caplog.text
    assert "Error message" in caplog.text
    assert "Critical message" in caplog.text


def test_log_format(logging_service: LoggingService, caplog):
    """Test log format."""
    logger = logging_service.get_logger("test_logger")
    logger.info("Test message")

    log_entry = caplog.records[0]
    assert hasattr(log_entry, "asctime")
    assert hasattr(log_entry, "name")
    assert hasattr(log_entry, "levelname")
    assert hasattr(log_entry, "message")


def test_get_stats(logging_service: LoggingService):
    """Test getting service statistics."""
    stats = logging_service.get_stats()
    assert isinstance(stats, dict)
    assert "log_level" in stats
    assert "log_file" in stats
    assert "log_format" in stats


def test_noisy_logger_handling(logging_service: LoggingService):
    """Test that noisy loggers are set to WARNING level."""
    noisy_logger = logging.getLogger("test_noisy")
    assert noisy_logger.level == logging.WARNING


def test_global_logger():
    """Test the global logger instance."""
    from ...src.common.services.logging_service import get_logger

    logger = get_logger("test_global_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_global_logger"
