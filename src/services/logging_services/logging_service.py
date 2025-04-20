import logging
import os
from typing import Dict, Optional, Any
from src.config import Configuration
from src.config.logging_config import setup_logging, get_log_config
from src.services.logging_services.http_logging import configure_http_client_logging

class LoggingService:
    """
    Central logging service that manages logging across the application.
    Uses configuration from logging_config.py but provides OO interface
    with additional functionality.
    """
    _instance = None  # Singleton instance
    
    @classmethod
    def get_instance(cls, config: Optional[Configuration] = None):
        """Get or create the singleton instance of LoggingService."""
        if cls._instance is None:
            cls._instance = LoggingService(config)
        return cls._instance
    
    def __init__(self, config: Optional[Configuration] = None):
        """
        Initialize the logging service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.log_config = get_log_config(config)
        self.handlers = None
        self.initialized = False
        self.loggers = {}  # Cache of configured loggers
        
        # Configure HTTP client logging
        self.http_loggers = configure_http_client_logging()
        
        # Initialize logging
        self.setup_logging()
        
    def setup_logging(self):
        """Set up logging using the configuration settings."""
        try:
            # Use the centralized setup_logging function
            self.handlers = setup_logging(self.config)
            self.initialized = True
            
            # Get a logger for this class
            self.logger = self.get_logger(__name__)
            self.logger.debug("Logging service initialized successfully")
        except Exception as e:
            print(f"Error setting up logging service: {e}")
            # Setup basic logging as fallback
            logging.basicConfig(level=logging.DEBUG)
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"Failed to initialize logging properly: {e}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a configured logger for the specified name.
        
        Args:
            name: Logger name (typically __name__ from the calling module)
            
        Returns:
            Configured Logger instance
        """
        if name in self.loggers:
            return self.loggers[name]
            
        logger = logging.getLogger(name)
        
        # Special logger configurations can be applied here
        # For example, setting specific levels for certain modules
        special_loggers = self.log_config.get('special_loggers', {})
        if name in special_loggers:
            logger.setLevel(special_loggers[name])
            
        self.loggers[name] = logger
        return logger
    
    def set_level(self, name: str, level: int):
        """
        Change the log level for a specific logger.
        
        Args:
            name: Logger name
            level: New log level (e.g., logging.DEBUG)
        """
        logger = self.get_logger(name)
        logger.setLevel(level)
        
        # Update cached config
        special_loggers = self.log_config.get('special_loggers', {})
        special_loggers[name] = level
        self.log_config['special_loggers'] = special_loggers
        
        # Log the change
        self.logger.debug(f"Changed log level for {name} to {level}")
        
    def get_all_loggers(self) -> Dict[str, int]:
        """
        Get all configured loggers and their levels.
        
        Returns:
            Dictionary of logger names to their log levels
        """
        result = {}
        for name, logger in self.loggers.items():
            result[name] = logger.level
        return result

# Helper function to get logger from any module
def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger from the central LoggingService.
    
    Args:
        name: Logger name (typically __name__ from the calling module)
        
    Returns:
        Configured Logger instance
    """
    service = LoggingService.get_instance()
    return service.get_logger(name) 