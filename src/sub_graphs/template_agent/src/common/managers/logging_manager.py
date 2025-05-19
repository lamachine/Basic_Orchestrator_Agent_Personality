"""
Logging Manager Module

This module implements the manager layer for logging operations.
It handles logging state, coordination, and lifecycle management.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..config.base_config import LoggingConfig
from ..services.logging_service import LoggingService
from .base_manager import BaseManager, ManagerState


class LoggingStats(BaseModel):
    """Track logging statistics."""

    total_logs: int = 0
    error_count: int = 0
    warning_count: int = 0
    last_log: Optional[datetime] = None
    log_history: List[Dict[str, Any]] = Field(default_factory=list)


class LoggingState(ManagerState):
    """State model for logging management."""

    active_handlers: Dict[str, List[str]] = Field(default_factory=dict)
    log_files: List[str] = Field(default_factory=list)
    stats: LoggingStats = Field(default_factory=LoggingStats)


class LoggingManager(BaseManager[LoggingConfig, LoggingState]):
    """Manager for logging operations and state."""

    def __init__(self, config: LoggingConfig):
        """Initialize the logging manager.

        Args:
            config: Logging configuration
        """
        super().__init__(config)
        self.service = LoggingService(config)

    async def initialize(self) -> None:
        """Initialize the logging manager."""
        await super().initialize()
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        # Initialize service
        self.service._setup_logging()

        # Track active handlers
        for logger_name in self.config.noisy_loggers:
            handlers = self.service.get_handlers(logger_name)
            self._state.active_handlers[logger_name] = [h.__class__.__name__ for h in handlers]

        # Track log files
        if self.config.log_to_file and self.config.log_file:
            log_path = Path(self.config.log_dir) / self.config.log_file
            self._state.log_files.append(str(log_path))

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance.

        Args:
            name: Logger name

        Returns:
            Configured logger instance
        """
        return self.service.get_logger(name)

    def log_error(
        self, logger: logging.Logger, message: str, exc_info: Optional[Exception] = None
    ) -> None:
        """Log an error message.

        Args:
            logger: Logger instance
            message: Error message
            exc_info: Optional exception info
        """
        logger.error(message, exc_info=exc_info)
        self._update_stats("ERROR", message)

    def log_warning(self, logger: logging.Logger, message: str) -> None:
        """Log a warning message.

        Args:
            logger: Logger instance
            message: Warning message
        """
        logger.warning(message)
        self._update_stats("WARNING", message)

    def log_info(self, logger: logging.Logger, message: str) -> None:
        """Log an info message.

        Args:
            logger: Logger instance
            message: Info message
        """
        logger.info(message)
        self._update_stats("INFO", message)

    def log_debug(self, logger: logging.Logger, message: str) -> None:
        """Log a debug message.

        Args:
            logger: Logger instance
            message: Debug message
        """
        logger.debug(message)
        self._update_stats("DEBUG", message)

    def _update_stats(self, level: str, message: str) -> None:
        """Update logging statistics.

        Args:
            level: Log level
            message: Log message
        """
        self._state.stats.total_logs += 1
        self._state.stats.last_log = datetime.now()

        if level == "ERROR":
            self._state.stats.error_count += 1
        elif level == "WARNING":
            self._state.stats.warning_count += 1

        self._state.stats.log_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
            }
        )

        # Keep history at reasonable size
        if len(self._state.stats.log_history) > 1000:
            self._state.stats.log_history = self._state.stats.log_history[-1000:]

    async def rotate_logs(self) -> None:
        """Rotate log files."""
        for log_file in self._state.log_files:
            path = Path(log_file)
            if path.exists():
                # Let the service handle rotation
                self.service.rotate_log(path)

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Close all handlers
        for logger_name in self._state.active_handlers:
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

        await super().cleanup()
