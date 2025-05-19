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
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from ..config.base_config import LoggingConfig


class LoggingService:
    """Service for logging operations."""

    def __init__(self, config: LoggingConfig):
        """Initialize logging service.

        Args:
            config: Logging configuration
        """
        self.config = config
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.config.log_level)

        # Create formatters
        formatters = {
            "default": logging.Formatter(self.config.log_format),
            **{name: logging.Formatter(fmt) for name, fmt in self.config.formatters.items()},
        }

        # Setup console handler if enabled
        if self.config.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.config.console_level)
            console_handler.setFormatter(formatters["default"])
            root_logger.addHandler(console_handler)

        # Setup file handler if enabled
        if self.config.log_to_file and self.config.log_file:
            # Ensure log directory exists
            log_dir = Path(self.config.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)

            # Create file handler
            file_handler = RotatingFileHandler(
                filename=log_dir / self.config.log_file,
                maxBytes=self.config.max_log_size_mb * 1024 * 1024,
                backupCount=self.config.backup_count,
            )
            file_handler.setLevel(self.config.file_level)
            file_handler.setFormatter(formatters["default"])
            root_logger.addHandler(file_handler)

        # Configure noisy loggers
        for logger_name in self.config.noisy_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance.

        Args:
            name: Logger name

        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)

    def set_level(self, name: str, level: str) -> None:
        """Set logging level for a specific logger.

        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

    def add_handler(self, name: str, handler: logging.Handler) -> None:
        """Add a handler to a specific logger.

        Args:
            name: Logger name
            handler: Logging handler to add
        """
        logger = logging.getLogger(name)
        logger.addHandler(handler)

    def remove_handler(self, name: str, handler: logging.Handler) -> None:
        """Remove a handler from a specific logger.

        Args:
            name: Logger name
            handler: Logging handler to remove
        """
        logger = logging.getLogger(name)
        logger.removeHandler(handler)

    def get_handlers(self, name: str) -> list[logging.Handler]:
        """Get all handlers for a specific logger.

        Args:
            name: Logger name

        Returns:
            List of handlers
        """
        logger = logging.getLogger(name)
        return logger.handlers

    def log_exception(self, logger: logging.Logger, e: Exception, message: str) -> None:
        """
        Log an exception with traceback.

        Args:
            logger: Logger instance
            e: Exception to log
            message: Error message
        """
        logger.error(f"{message}: {str(e)}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "log_level": logging.getLevelName(logging.getLogger().level),
            "log_file": self.config.log_file,
            "log_format": self.config.log_format,
        }
