"""Logging configuration for the application."""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, Any, Optional

# Default logging configuration
DEFAULT_CONFIG = {
    "log_levels": {
        "file": "DEBUG",
        "console": "INFO"
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

# Special loggers that need custom handling
SPECIAL_LOGGERS = [
    # "src.sub_graph_personal_assistant.agents.personal_assistant_agent",  # (disabled for minimal orchestrator)
    "src.tools.valet",
    "src.tools.librarian"
]

# Tool loggers that need custom handling
TOOL_LOGGERS = [
    "src.tools.valet",
    "src.tools.librarian",
    "src.tools.tool_utils"
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
        
        # Check for direct attributes on config object as fallback
        if hasattr(config, 'file_level'):
            level = config.file_level
            if isinstance(level, str):
                level = getattr(logging, level.upper(), logging.DEBUG)
            log_config['log_levels']['file'] = level
            
        if hasattr(config, 'console_level'):
            level = config.console_level
            if isinstance(level, str):
                level = getattr(logging, level.upper(), logging.INFO)
            log_config['log_levels']['console'] = level
            
        if hasattr(config, 'log_dir'):
            log_config['file_config']['log_dir'] = getattr(config, 'log_dir')
    
    return log_config

def setup_logging(config=None):
    """
    Setup logging configuration.
    
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
    file_handler.setLevel(log_config['log_levels']['file'])
    file_handler.setFormatter(file_formatter)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_config['log_levels']['console'])
    console_handler.setFormatter(console_formatter)
    
    # Remove any existing handlers from the root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure special loggers with specific levels if needed
    for logger_name in SPECIAL_LOGGERS:
        special_logger = logging.getLogger(logger_name)
        special_logger.setLevel(log_config['log_levels']['console'])
        # Ensure it doesn't have its own handlers (use root handlers only)
        special_logger.handlers = []
        # Allow propagation to root
        special_logger.propagate = True
    
    # Tool loggers - ensure they don't have duplicate handlers
    for logger_name in TOOL_LOGGERS:
        tool_logger = logging.getLogger(logger_name)
        # Remove any existing handlers
        tool_logger.handlers = []
        # Let propagation work to root logger
        tool_logger.propagate = True
    
    # Reduce logging noise from HTTP libraries
    noisy_loggers = [
        "httpcore.http11",
        "httpx",
        "urllib3",
        "requests",
        "chardet.charsetprober",
        "asyncio",
        "charset_normalizer"
    ]
    
    for logger_name in noisy_loggers:
        noisy_logger = logging.getLogger(logger_name)
        noisy_logger.setLevel(logging.WARNING)  # Only log WARNING and above
        # Ensure it doesn't have handlers
        noisy_logger.handlers = []
        noisy_logger.propagate = True
    
    return file_handler, console_handler