"""
Logging Service Module

This module implements logging functionality as a service layer. As a service (not a manager), it:

1. Provides stateless utility functions for logging
2. Focuses on a single responsibility (logging)
3. Does not make decisions about application flow
4. Offers tools and functions for logging

The key distinction of this being a service (vs a manager) is that it:
- Is stateless
- Provides utility functions
- Has a single responsibility
- Does not make decisions about system state

This is different from a manager which would:
- Maintain state
- Make decisions about flow
- Coordinate between components
- Handle lifecycle management
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    Always uses the global logging configuration.
    """
    return logging.getLogger(name)


def setup_file_logging(log_file: str, level: Optional[int] = None) -> None:
    """
    Setup file-based logging.

    Args:
        log_file: Path to log file
        level: Optional logging level
    """
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create file handler
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    if level:
        root_logger.setLevel(level)


def log_exception(logger: logging.Logger, e: Exception, message: str) -> None:
    """
    Log an exception with traceback.

    Args:
        logger: Logger instance
        e: Exception to log
        message: Error message
    """
    logger.error(f"{message}: {str(e)}", exc_info=True)
