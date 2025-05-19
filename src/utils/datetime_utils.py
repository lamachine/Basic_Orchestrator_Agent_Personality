"""
Standardized datetime utilities for consistent handling of date and time operations.
"""

import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Union

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
    logging.warning("zoneinfo not available; local time will default to UTC.")

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects and enums."""

    def default(self, obj):
        if isinstance(obj, datetime):
            if obj.tzinfo:
                obj = obj.replace(tzinfo=None)
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format a datetime as ISO 8601 string."""
    if dt is None:
        dt = datetime.now()
    if dt.tzinfo:
        dt = dt.replace(tzinfo=None)
    return dt.isoformat()


def parse_datetime(dt_str: Optional[Union[str, datetime]]) -> datetime:
    """Parse an ISO 8601 datetime string to a datetime object."""
    if not dt_str:
        return datetime.now()
    try:
        if isinstance(dt_str, datetime):
            return dt_str.replace(tzinfo=None) if dt_str.tzinfo else dt_str
        if not isinstance(dt_str, str):
            dt_str = str(dt_str)
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1]
        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            try:
                if "+" in dt_str and "." in dt_str:
                    dt_part = dt_str.split("+")[0]
                    return datetime.strptime(dt_part, "%Y-%m-%dT%H:%M:%S.%f")
            except ValueError:
                pass
            try:
                if "T" in dt_str:
                    return datetime.strptime(dt_str.split("+")[0], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass
            try:
                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.warning(f"All parsing attempts failed for: {dt_str}")
                return datetime.now()
    except Exception as e:
        logger.warning(f"Error parsing datetime '{dt_str}': {e}")
        return datetime.now()


def now() -> datetime:
    """Get the current datetime in UTC as a timezone-naive datetime object."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def timestamp() -> str:
    """Get the current timestamp as a string in ISO 8601 format."""
    return now().isoformat() + "Z"


def parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """Parse a timestamp string into a datetime object."""
    if not timestamp_str:
        return None
    try:
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1]
            dt = datetime.fromisoformat(timestamp_str)
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)
            return dt
        elif "T" in timestamp_str:
            return datetime.fromisoformat(timestamp_str)
        else:
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        try:
            return datetime.fromtimestamp(float(timestamp_str))
        except (ValueError, TypeError):
            return None


def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """Format a datetime object into an ISO 8601 string."""
    if not dt:
        return None
    if dt.tzinfo:
        dt = dt.replace(tzinfo=None)
    return dt.isoformat() + "Z"


def to_unix_timestamp(dt: Optional[datetime]) -> Optional[float]:
    """Convert a datetime object to a Unix timestamp."""
    if not dt:
        return None
    return dt.timestamp()


def from_unix_timestamp(timestamp: Optional[Union[float, int, str]]) -> Optional[datetime]:
    """Convert a Unix timestamp to a datetime object."""
    if timestamp is None:
        return None
    try:
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        return datetime.fromtimestamp(timestamp)
    except (ValueError, TypeError):
        return None


def is_valid_iso_format(dt_str: str) -> bool:
    """Check if a string is a valid ISO 8601 datetime."""
    try:
        parse_datetime(dt_str)
        return True
    except Exception:
        return False


def get_local_datetime(timezone_str: str) -> datetime:
    """
    Get the current local datetime for the given IANA timezone string.
    Falls back to UTC if zoneinfo is unavailable or timezone is invalid.
    Args:
        timezone_str (str): IANA timezone string (e.g., 'America/Los_Angeles')
    Returns:
        datetime: Local datetime (timezone-naive)
    """
    if ZoneInfo is not None:
        try:
            dt = datetime.now(ZoneInfo(timezone_str))
            return dt.replace(tzinfo=None)
        except Exception as e:
            logger.warning(f"Invalid timezone '{timezone_str}': {e}. Falling back to UTC.")
    return datetime.utcnow()


def get_local_datetime_str(timezone_str: str) -> str:
    """
    Get the current local datetime as a formatted string for the given timezone.
    Args:
        timezone_str (str): IANA timezone string
    Returns:
        str: ISO 8601 formatted local datetime string
    """
    return get_local_datetime(timezone_str).isoformat()
