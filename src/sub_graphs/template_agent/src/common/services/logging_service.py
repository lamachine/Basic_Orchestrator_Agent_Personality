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
from typing import Optional, Dict, Any

from ..models.service_models import LoggingServiceConfig

class LoggingService:
    """Service for logging operations."""
    
    def __init__(self, config: LoggingServiceConfig):
        """
        Initialize logging service.
        
        Args:
            config: Logging service configuration
        """
        self.config = config
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        # Get log format from config
        log_format = self.config.get_merged_config().get(
            "log_format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # Get log level from config
        log_level = self.config.get_merged_config().get("log_level", "INFO")
        level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Setup console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(console_handler)
        
        # Setup file handler if log file specified
        log_file = self.config.get_merged_config().get("log_file")
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)
            
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance with the specified name.
        
        Args:
            name: Name of the logger
            
        Returns:
            Logger instance
        """
        return logging.getLogger(name)
        
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
            "log_file": self.config.get_merged_config().get("log_file"),
            "log_format": self.config.get_merged_config().get("log_format")
        }

# Global instance for backward compatibility
_logging_service: Optional[LoggingService] = None

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    Always uses the global logging configuration.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger instance
    """
    global _logging_service
    if _logging_service is None:
        # Create default config if none exists
        config = LoggingServiceConfig()
        _logging_service = LoggingService(config)
    return _logging_service.get_logger(name) 