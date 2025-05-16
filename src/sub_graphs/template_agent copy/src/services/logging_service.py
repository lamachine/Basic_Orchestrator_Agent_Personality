"""
Template Agent Logging Service.

This service provides logging functionality for the template agent,
using the same format as the orchestrator but writing to a template-specific
log directory. It maintains compatibility with the parent graph's logging
system while providing isolated logs for the template agent.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

# Configure template-specific log directory
TEMPLATE_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
TEMPLATE_LOG_DIR.mkdir(exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger configured for the template agent.
    
    Args:
        name: The name of the logger
        
    Returns:
        logging.Logger: A configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create file handler for debug logs
        debug_file = TEMPLATE_LOG_DIR / f"template_debug_{datetime.now().strftime('%Y%m%d')}.log"
        debug_handler = logging.FileHandler(debug_file)
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        logger.addHandler(debug_handler)
        
        # Create file handler for error logs
        error_file = TEMPLATE_LOG_DIR / f"template_error_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger 