"""Logging configuration for the application."""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(config):
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(log_dir, f'agent_debug_{timestamp}.log')
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(module)s - %(message)s')
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Create and configure file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Remove any existing handlers from the root logger
    logging.getLogger().handlers.clear()
    
    # Configure root logger
    logging.getLogger().setLevel(logging.DEBUG)
    
    return file_handler, console_handler