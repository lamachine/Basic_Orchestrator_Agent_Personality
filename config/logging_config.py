"""
Logging configuration for the application.
"""
import os
from datetime import datetime
import logging.config

# Create logs directory if it doesn't exist
os.makedirs("logs/debug", exist_ok=True)

# Generate timestamp for log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
debug_log_file = f"logs/debug/debug_{timestamp}.log"
app_log_file = f"logs/orchestrator_{timestamp}.log"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)8s] [%(name)s] %(message)s (%(filename)s:%(lineno)s)",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "debug_file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": debug_log_file,
            "mode": "a",
        },
        "app_file": {
            "class": "logging.FileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": app_log_file,
            "mode": "a",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "app_file"],
            "level": "INFO",
            "propagate": True,
        },
        "debug": {  # Debug logger
            "handlers": ["debug_file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

def setup_logging():
    """
    Initialize logging configuration for the application.
    """
    logging.config.dictConfig(LOGGING_CONFIG)
    
    # Create logger instances
    logger = logging.getLogger(__name__)
    debug_logger = logging.getLogger("debug")
    
    logger.debug("Logging system initialized")
    debug_logger.debug("Debug logging system initialized")
    
    return logger, debug_logger 