"""
HTTP Client Logging Configuration

This module centralizes the configuration for various HTTP client libraries to ensure
proper logging behavior across the application. It prevents these libraries from
logging to the console by default, which can be noisy in production environments.
"""

import logging
from typing import Dict

def configure_http_client_logging() -> Dict[str, logging.Logger]:
    """
    Configure HTTP client libraries to not send logs to the console.
    
    Returns:
        Dict of logger name to logger instance
    """
    # List of HTTP client libraries to configure
    http_libraries = [
        "httpx",
        "urllib3",
        "requests",
        "http.client",
        "aiohttp"
    ]
    
    # Configure each library's logger
    loggers = {}
    for lib in http_libraries:
        logger = logging.getLogger(lib)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # Prevent propagation to root logger/console
        loggers[lib] = logger
        
    return loggers

# Optional helper function to enable file logging for HTTP clients
def enable_http_client_file_logging(file_path: str, level: int = logging.INFO):
    """
    Enable logging to a file for HTTP client libraries.
    
    Args:
        file_path: Path to the log file
        level: Log level to use
    """
    # Get all HTTP client loggers
    loggers = configure_http_client_logging()
    
    # Create a file handler
    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(level)
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add the handler to each logger
    for logger in loggers.values():
        logger.addHandler(file_handler)
        
    return loggers 