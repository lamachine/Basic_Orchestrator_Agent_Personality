"""
Unit tests for the logging service.
"""

import pytest
import logging
from datetime import datetime
from typing import Dict, Any, List

from ...src.common.services.logging_service import LoggingService
from ...src.common.models.service_models import LoggingServiceConfig

@pytest.fixture
def config() -> LoggingServiceConfig:
    """Create a test configuration."""
    return LoggingServiceConfig(
        name="test_logging_service",
        enabled=True,
        config={
            "log_level": "DEBUG",
            "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_file": "test.log"
        }
    )

@pytest.fixture
def logging_service(config: LoggingServiceConfig):
    """Create a test logging service."""
    return LoggingService(config)

def test_initialization(logging_service: LoggingService):
    """Test service initialization."""
    assert logging_service.is_connected
    assert logging_service.log_count == 0
    assert logging_service.error_count == 0

def test_get_logger(logging_service: LoggingService):
    """Test getting a logger instance."""
    logger = logging_service.get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    assert logger.level == logging.DEBUG

def test_log_exception(logging_service: LoggingService, caplog):
    """Test logging an exception."""
    try:
        raise ValueError("Test error")
    except ValueError as e:
        logging_service.log_exception(e)
    
    assert "Test error" in caplog.text
    assert logging_service.error_count == 1

def test_log_message(logging_service: LoggingService, caplog):
    """Test logging a message."""
    logger = logging_service.get_logger("test_logger")
    logger.info("Test message")
    
    assert "Test message" in caplog.text
    assert logging_service.log_count == 1

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
    assert logging_service.log_count == 5
    assert logging_service.error_count == 2  # Error and Critical

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
    # Log some messages
    logger = logging_service.get_logger("test_logger")
    logger.info("Test message")
    logger.error("Test error")
    
    stats = logging_service.get_stats()
    assert isinstance(stats, dict)
    assert stats["log_count"] == 2
    assert stats["error_count"] == 1
    assert "log_level" in stats
    assert "log_format" in stats
    assert "log_file" in stats

def test_global_logger():
    """Test the global logger instance."""
    from ...src.common.services.logging_service import get_logger
    
    logger = get_logger("test_global_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_global_logger" 