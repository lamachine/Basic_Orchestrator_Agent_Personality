"""
Logging Utilities Module

This module provides utility functions for logging setup and configuration.
Implements a singleton pattern to ensure logging is configured once at startup.
Handles sub-graph logging hierarchy with complete isolation by default.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Global flag to track if logging has been initialized
_logging_initialized = False

# Base logger name for this sub-graph
LOGGER_BASE = "template_agent"


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (will be prefixed with template_agent)

    Returns:
        Configured logger instance
    """
    if not _logging_initialized:
        # Default setup if not initialized
        setup_logging()

    # Ensure logger name is properly namespaced
    if not name.startswith(LOGGER_BASE):
        name = f"{LOGGER_BASE}.{name}"

    logger = logging.getLogger(name)
    # Ensure isolation by default
    logger.propagate = False
    return logger


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    log_to_console: bool = True,
    log_to_file: bool = False,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    propagate: bool = False,  # Changed default to False for isolation
) -> None:
    """Setup basic logging configuration.

    This function should be called once at program startup.
    Subsequent calls will be ignored unless force=True.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log message format
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        log_file: Log file name
        log_dir: Log directory path
        propagate: Whether to propagate logs to parent loggers (default: False for isolation)
    """
    global _logging_initialized

    # Skip if already initialized
    if _logging_initialized:
        return

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to ensure clean setup
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Setup console handler if enabled
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Setup file handler if enabled
    if log_to_file and log_file:
        # Ensure log directory exists
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / log_file
        else:
            log_path = Path(log_file)

        # Create file handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure our base logger with isolation
    base_logger = logging.getLogger(LOGGER_BASE)
    base_logger.propagate = propagate  # Default to False for isolation
    base_logger.setLevel(log_level)

    # Add handlers to base logger to ensure all child loggers get them
    if log_to_console:
        base_logger.addHandler(console_handler)
    if log_to_file and log_file:
        base_logger.addHandler(file_handler)

    # Mark as initialized
    _logging_initialized = True

    # Log initialization
    logger = get_logger(__name__)
    logger.info("Logging system initialized with complete isolation")
    logger.debug(f"Log level: {log_level}")
    logger.debug(f"Console logging: {log_to_console}")
    logger.debug(f"File logging: {log_to_file}")
    logger.debug(f"Log propagation: {propagate}")
    if log_to_file:
        logger.debug(f"Log file: {log_path}")


def get_base_logger() -> logging.Logger:
    """Get the base logger for this sub-graph.

    Returns:
        Base logger instance (configured for isolation)
    """
    logger = logging.getLogger(LOGGER_BASE)
    logger.propagate = False  # Ensure isolation
    return logger
