"""Logging configuration for the application."""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Default logging configuration
DEFAULT_CONFIG = {
    # Log levels
    'file_log_level': logging.DEBUG,
    'console_log_level': logging.INFO,
    
    # File configuration
    'log_dir': os.path.join(os.getcwd(), 'logs'),
    'max_log_size_mb': 10,
    'backup_count': 5,
    
    # Formatting
    'file_format': '%(asctime)s - %(levelname)s - [%(name)s] - %(module)s - %(message)s',
    'console_format': '%(levelname)s: %(message)s',
    
    # Special loggers that might need different levels
    'special_loggers': {
        'src.agents.ai_agent': logging.INFO,
        'src.agents.orchestrator_tools': logging.INFO,
        'src.services.llm_services': logging.INFO
    }
}

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
                log_config['file_log_level'] = level
                
            if 'console_level' in user_log_config:
                level = user_log_config['console_level']
                if isinstance(level, str):
                    level = getattr(logging, level.upper(), logging.INFO)
                log_config['console_log_level'] = level
                
            if 'log_dir' in user_log_config:
                log_config['log_dir'] = user_log_config['log_dir']
                
            if 'max_log_size_mb' in user_log_config:
                log_config['max_log_size_mb'] = user_log_config['max_log_size_mb']
                
            if 'backup_count' in user_log_config:
                log_config['backup_count'] = user_log_config['backup_count']
        
        # Check for direct attributes on config object as fallback
        if hasattr(config, 'file_level'):
            level = config.file_level
            if isinstance(level, str):
                level = getattr(logging, level.upper(), logging.DEBUG)
            log_config['file_log_level'] = level
            
        if hasattr(config, 'console_level'):
            level = config.console_level
            if isinstance(level, str):
                level = getattr(logging, level.upper(), logging.INFO)
            log_config['console_log_level'] = level
            
        if hasattr(config, 'log_dir'):
            log_config['log_dir'] = getattr(config, 'log_dir')
    
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
    log_dir = log_config['log_dir']
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'agent_debug_{timestamp}.log')
    
    # Create formatters
    file_formatter = logging.Formatter(log_config['file_format'])
    console_formatter = logging.Formatter(log_config['console_format'])
    
    # Create and configure file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_config['max_log_size_mb']*1024*1024,
        backupCount=log_config['backup_count']
    )
    file_handler.setLevel(log_config['file_log_level'])
    file_handler.setFormatter(file_formatter)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_config['console_log_level'])
    console_handler.setFormatter(console_formatter)
    
    # Remove any existing handlers from the root logger
    logging.getLogger().handlers.clear()
    
    # Configure root logger
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().addHandler(console_handler)
    
    # Configure special loggers with specific levels if needed
    for logger_name, level in log_config['special_loggers'].items():
        logging.getLogger(logger_name).setLevel(level)
    
    # Tool loggers - these still get the file handler but we allow propagation
    # so that INFO and above messages appear in the console
    tool_loggers = [
        "src.tools",
        "src.tools.librarian",
        "src.tools.personal_assistant",
        "src.tools.valet",
        "src.tools.scrape_web_tool",
        "src.tools.scrape_repo_tool",
        "src.tools.mcp_tools",
        "src.tools.crawler",
        "src.agents.orchestrator_tools",
        "src.services.db_services",
        "httpx",
        "urllib3",
        "requests",
        "http.client",
        "aiohttp"
    ]
    
    for logger_name in tool_loggers:
        tool_logger = logging.getLogger(logger_name)
        # Allow propagation so INFO and above messages appear in console
        # tool_logger.propagate = False  # Removed this line
        
        # Ensure the tool logger has the file handler for capturing detailed logs
        if not any(isinstance(h, logging.FileHandler) for h in tool_logger.handlers):
            tool_logger.addHandler(file_handler)
    
    return file_handler, console_handler