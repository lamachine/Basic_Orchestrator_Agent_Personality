"""
Template Agent Datetime Utilities.

This module provides datetime utilities for the template agent,
inheriting core functionality from the orchestrator's datetime utilities
but adding template-specific datetime handling.
"""

import time
import json
from datetime import datetime, timezone
from typing import Optional, Union
import logging
from enum import Enum

from src.utils.datetime_utils import (
    DateTimeEncoder as BaseDateTimeEncoder,
    format_datetime as base_format_datetime,
    parse_datetime as base_parse_datetime,
    now as base_now,
    timestamp as base_timestamp,
    parse_timestamp as base_parse_timestamp,
    format_timestamp as base_format_timestamp,
    to_unix_timestamp as base_to_unix_timestamp,
    from_unix_timestamp as base_from_unix_timestamp,
    is_valid_iso_format as base_is_valid_iso_format
)

from ..services.logging_service import get_logger

logger = get_logger(__name__)

class DateTimeEncoder(BaseDateTimeEncoder):
    """Template agent JSON encoder that handles datetime objects and enums."""
    def default(self, obj):
        if isinstance(obj, datetime):
            if obj.tzinfo:
                obj = obj.replace(tzinfo=None)
            return obj.isoformat()
        elif isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format a datetime as ISO 8601 string with template context."""
    dt_str = base_format_datetime(dt)
    logger.debug(f"Formatted template datetime: {dt_str}")
    return dt_str

def parse_datetime(dt_str: Optional[Union[str, datetime]]) -> datetime:
    """Parse an ISO 8601 datetime string to a datetime object with template validation."""
    dt = base_parse_datetime(dt_str)
    logger.debug(f"Parsed template datetime: {dt}")
    return dt

def now() -> datetime:
    """Get the current datetime in UTC as a timezone-naive datetime object."""
    return base_now()

def timestamp() -> str:
    """Get the current timestamp as a string in ISO 8601 format."""
    return base_timestamp()

def parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """Parse a timestamp string into a datetime object."""
    return base_parse_timestamp(timestamp_str)

def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """Format a datetime object into an ISO 8601 string."""
    return base_format_timestamp(dt)

def to_unix_timestamp(dt: Optional[datetime]) -> Optional[float]:
    """Convert a datetime object to a Unix timestamp."""
    return base_to_unix_timestamp(dt)

def from_unix_timestamp(timestamp: Optional[Union[float, int, str]]) -> Optional[datetime]:
    """Convert a Unix timestamp to a datetime object."""
    return base_from_unix_timestamp(timestamp)

def is_valid_iso_format(dt_str: str) -> bool:
    """Check if a string is a valid ISO 8601 datetime."""
    return base_is_valid_iso_format(dt_str) 