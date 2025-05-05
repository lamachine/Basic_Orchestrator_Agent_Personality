"""Logging configuration for the application."""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, Any, Optional

# Default logging configuration
DEFAULT_CONFIG = {
    "log_levels": {
        # Standard logging levels (from most to least verbose):
        # DEBUG (10): Detailed information for diagnosing problems
        # INFO (20): General operational events
        # WARNING (30): Unexpected but handled issues
        # ERROR (40): Serious problems
        # CRITICAL (50): Program may not be able to continue
        "file": "DEBUG",     # Log everything to file
        "console": "INFO",   # Only INFO and above to console
        "root": "DEBUG"      # Allow all logs to propagate
    },
    "file_config": {
        "log_dir": "logs",
        "max_size_mb": 10,
        "backup_count": 5
    },
    "formatters": {
        "file": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "console": {
            "format": "%(levelname)s: %(message)s"
        }
    }
}

# Loggers to reduce noise from (only log WARNING and above)
NOISY_LOGGERS = [
    "httpcore.http11",
    "httpx",
    "urllib3",
    "requests",
    "chardet.charsetprober",
    "asyncio",
    "charset_normalizer"
]

def get_log_config(config=None):
    """
    Get logging configuration, optionally overriding defaults with provided config.
    
    Args:
        config: Optional configuration object with logging settings
        
    Returns:
        Dictionary with merged logging configuration
    """
    log_config = DEFAULT_CONFIG.copy()
    
    # If config is provided, override defaults with any provided values
    if config:
        # Try to get settings from user config first
        if hasattr(config, 'user_config') and config.user_config:
            user_log_config = config.user_config.get_logging_config()
            # Convert string log levels to int constants if needed
            if 'file_level' in user_log_config:
                level = user_log_config['file_level']
                if isinstance(level, str):
                    level = getattr(logging, level.upper(), logging.DEBUG)
                log_config['log_levels']['file'] = level
                
            if 'console_level' in user_log_config:
                level = user_log_config['console_level']
                if isinstance(level, str):
                    level = getattr(logging, level.upper(), logging.INFO)
                log_config['log_levels']['console'] = level
                
            if 'log_dir' in user_log_config:
                log_config['file_config']['log_dir'] = user_log_config['log_dir']
                
            if 'max_log_size_mb' in user_log_config:
                log_config['file_config']['max_size_mb'] = user_log_config['max_log_size_mb']
                
            if 'backup_count' in user_log_config:
                log_config['file_config']['backup_count'] = user_log_config['backup_count']
    
    return log_config

def setup_logging(config=None):
    """
    Setup logging configuration with separate file and console handlers.
    
    The root logger allows all messages (DEBUG+) to propagate, but:
    - File handler logs everything (DEBUG+) to dated log file
    - Console handler only shows important messages (INFO+)
    
    Args:
        config: Optional configuration object
        
    Returns:
        Tuple of (file_handler, console_handler)
    """
    # Get merged configuration
    log_config = get_log_config(config)
    
    # Create logs directory if it doesn't exist
    log_dir = log_config['file_config']['log_dir']
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'agent_debug_{timestamp}.log')
    
    # Create formatters
    file_formatter = logging.Formatter(log_config['formatters']['file']['format'])
    console_formatter = logging.Formatter(log_config['formatters']['console']['format'])
    
    # Create and configure file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_config['file_config']['max_size_mb']*1024*1024,
        backupCount=log_config['file_config']['backup_count']
    )
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_config['log_levels']['root'])  # DEBUG by default
    
    # File handler gets everything
    file_handler.setLevel(log_config['log_levels']['file'])  # DEBUG by default
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler gets reduced output
    console_handler.setLevel(log_config['log_levels']['console'])  # INFO by default
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from HTTP libraries (WARNING+ only)
    for logger_name in NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    return file_handler, console_handler