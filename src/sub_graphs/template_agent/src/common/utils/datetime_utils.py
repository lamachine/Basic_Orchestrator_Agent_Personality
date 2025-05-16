"""
Date and time utilities for template agent.

This module provides utility functions for date and time handling.
"""

from datetime import datetime, timezone
import pytz
from typing import Optional, Union, Any
import json
import logging

logger = logging.getLogger(__name__)

def now() -> datetime:
    """
    Get current UTC datetime.
    
    Returns:
        datetime: Current UTC datetime
    """
    try:
        return datetime.now(timezone.utc)
    except Exception as e:
        logger.error(f"Error getting current time: {e}")
        raise

def get_local_datetime_str() -> str:
    """
    Get current local datetime as string.
    
    Returns:
        str: Current local datetime string
    """
    try:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.error(f"Error formatting local datetime: {e}")
        raise

def format_datetime(dt: datetime) -> str:
    """
    Format datetime as ISO string.
    
    Args:
        dt: Datetime to format
        
    Returns:
        str: ISO formatted datetime string
    """
    try:
        return dt.isoformat()
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        raise

def parse_datetime(dt_str: str) -> datetime:
    """
    Parse ISO datetime string.
    
    Args:
        dt_str: ISO datetime string
        
    Returns:
        datetime: Parsed datetime
        
    Raises:
        ValueError: If datetime string is invalid
    """
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError as e:
        logger.error(f"Invalid datetime string: {dt_str}")
        raise
    except Exception as e:
        logger.error(f"Error parsing datetime: {e}")
        raise

def timestamp(dt: Optional[datetime] = None) -> float:
    """
    Get timestamp for datetime.
    
    Args:
        dt: Optional datetime (defaults to now)
        
    Returns:
        float: Unix timestamp
    """
    try:
        if dt is None:
            dt = now()
        return dt.timestamp()
    except Exception as e:
        logger.error(f"Error getting timestamp: {e}")
        raise

class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    
    def default(self, obj: Any) -> Any:
        """
        Convert datetime to ISO string.
        
        Args:
            obj: Object to encode
            
        Returns:
            Any: Encoded object
            
        Raises:
            TypeError: If object cannot be encoded
        """
        try:
            if isinstance(obj, datetime):
                return format_datetime(obj)
            return super().default(obj)
        except Exception as e:
            logger.error(f"Error encoding datetime: {e}")
            raise 