"""
Standardized datetime utilities for consistent handling of date and time operations.

This module provides functions for working with datetime objects in a consistent way,
particularly focusing on ISO format compatibility with both Python and JSON.
"""

import time
from datetime import datetime, timezone
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

def format_datetime(dt: Optional[datetime] = None) -> str:
    """
    Format a datetime as ISO 8601 string.
    
    Args:
        dt: Datetime to format, or current time if None
        
    Returns:
        ISO 8601 formatted string
    """
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()

def parse_datetime(dt_str: Optional[Union[str, datetime]]) -> datetime:
    """
    Parse an ISO 8601 datetime string to a datetime object.
    
    Args:
        dt_str: ISO 8601 string, datetime object, or None
        
    Returns:
        Datetime object (current time if None or parsing fails)
    """
    if not dt_str:
        return datetime.now()
    
    try:
        # Already a datetime object
        if isinstance(dt_str, datetime):
            # Ensure it's timezone-naive
            return dt_str.replace(tzinfo=None) if dt_str.tzinfo else dt_str
        
        # Convert to string if not already
        if not isinstance(dt_str, str):
            dt_str = str(dt_str)
            
        # Handle Z-suffix (UTC indicator)
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1]  # Remove the Z
            
        # Try different parsing approaches
        try:
            # Standard format with fromisoformat
            return datetime.fromisoformat(dt_str)
        except ValueError:
            # Try with specific format patterns
            try:
                # Format with microseconds and timezone: 2025-04-12T09:37:17.81878+00:00
                if '+' in dt_str and '.' in dt_str:
                    # Remove timezone for now
                    dt_part = dt_str.split('+')[0]
                    # Parse with explicit format
                    return datetime.strptime(dt_part, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                pass
                
            # Try without microseconds
            try:
                if 'T' in dt_str:
                    return datetime.strptime(dt_str.split('+')[0], '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                pass
                
            # Final fallback: simple date format
            try:
                return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # If all parsing attempts fail, return current time
                logger.warning(f"All parsing attempts failed for: {dt_str}")
                return datetime.now()
                
    except Exception as e:
        logger.warning(f"Error parsing datetime '{dt_str}': {e}")
        return datetime.now()

def now() -> datetime:
    """
    Get the current datetime in UTC as a timezone-naive datetime object.
    
    Returns:
        A naive datetime object representing the current time in UTC.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

def timestamp() -> str:
    """
    Get the current timestamp as a string in ISO 8601 format.
    
    Returns:
        String timestamp in ISO format (YYYY-MM-DDTHH:MM:SS.mmmZ)
    """
    return now().isoformat() + "Z"

def parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a timestamp string into a datetime object.
    
    Args:
        timestamp_str: A string timestamp, ideally in ISO format.
            Can be None, which will return None.
            
    Returns:
        A datetime object or None if the input was None or invalid.
    """
    if not timestamp_str:
        return None
        
    try:
        # Handle ISO format with Z suffix
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1]
            dt = datetime.fromisoformat(timestamp_str)
            # Convert to naive datetime
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)
            return dt
        # Try ISO format
        elif "T" in timestamp_str:
            return datetime.fromisoformat(timestamp_str)
        # Try simple date format
        else:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        # Fallback for Unix timestamp format
        try:
            return datetime.fromtimestamp(float(timestamp_str))
        except (ValueError, TypeError):
            return None

def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """
    Format a datetime object into an ISO 8601 string.
    
    Args:
        dt: A datetime object or None
        
    Returns:
        An ISO format string or None if input was None
    """
    if not dt:
        return None
    
    # Ensure naive datetime
    if dt.tzinfo:
        dt = dt.replace(tzinfo=None)
        
    return dt.isoformat() + "Z"

def to_unix_timestamp(dt: Optional[datetime]) -> Optional[float]:
    """
    Convert a datetime object to a Unix timestamp.
    
    Args:
        dt: A datetime object or None
        
    Returns:
        Unix timestamp as float or None if input was None
    """
    if not dt:
        return None
    
    return dt.timestamp()

def from_unix_timestamp(timestamp: Optional[Union[float, int, str]]) -> Optional[datetime]:
    """
    Convert a Unix timestamp to a datetime object.
    
    Args:
        timestamp: Unix timestamp as float, int, or string, or None
        
    Returns:
        A datetime object or None if input was None or invalid
    """
    if timestamp is None:
        return None
        
    try:
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        return datetime.fromtimestamp(timestamp)
    except (ValueError, TypeError):
        return None

def is_valid_iso_format(dt_str: str) -> bool:
    """
    Check if a string is a valid ISO 8601 datetime.
    
    Args:
        dt_str: String to check
        
    Returns:
        True if valid ISO 8601 format, False otherwise
    """
    try:
        parse_datetime(dt_str)
        return True
    except Exception:
        return False 