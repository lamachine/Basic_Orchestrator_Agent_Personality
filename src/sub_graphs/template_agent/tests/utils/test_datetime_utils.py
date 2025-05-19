"""
Tests for datetime utilities.
"""

import json
from datetime import datetime, timezone

import pytest

from src.common.utils.datetime_utils import (
    DateTimeEncoder,
    format_datetime,
    get_local_datetime_str,
    now,
    parse_datetime,
    timestamp,
)


def test_now():
    """Test now() returns UTC datetime."""
    current = now()
    assert isinstance(current, datetime)
    assert current.tzinfo == timezone.utc


def test_get_local_datetime_str():
    """Test get_local_datetime_str() returns formatted string."""
    dt_str = get_local_datetime_str()
    assert isinstance(dt_str, str)
    assert len(dt_str) == 19  # YYYY-MM-DD HH:MM:SS
    assert dt_str[4] == "-"  # Check format
    assert dt_str[7] == "-"
    assert dt_str[10] == " "
    assert dt_str[13] == ":"
    assert dt_str[16] == ":"


def test_format_datetime():
    """Test format_datetime() formats correctly."""
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    formatted = format_datetime(dt)
    assert isinstance(formatted, str)
    assert formatted == "2024-01-01T12:00:00+00:00"


def test_parse_datetime():
    """Test parse_datetime() parses correctly."""
    dt_str = "2024-01-01T12:00:00+00:00"
    dt = parse_datetime(dt_str)
    assert isinstance(dt, datetime)
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.tzinfo == timezone.utc


def test_parse_datetime_invalid():
    """Test parse_datetime() with invalid input."""
    with pytest.raises(ValueError):
        parse_datetime("invalid")


def test_timestamp():
    """Test timestamp() returns correct value."""
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts = timestamp(dt)
    assert isinstance(ts, float)
    assert ts == dt.timestamp()


def test_timestamp_default():
    """Test timestamp() with default value."""
    ts = timestamp()
    assert isinstance(ts, float)
    assert ts > 0


def test_datetime_encoder():
    """Test DateTimeEncoder handles datetime objects."""
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    encoder = DateTimeEncoder()
    encoded = encoder.default(dt)
    assert isinstance(encoded, str)
    assert encoded == "2024-01-01T12:00:00+00:00"


def test_datetime_encoder_other():
    """Test DateTimeEncoder with non-datetime objects."""
    encoder = DateTimeEncoder()
    assert encoder.default("test") == "test"
    assert encoder.default(123) == 123


def test_datetime_json_serialization():
    """Test datetime serialization in JSON."""
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    data = {"timestamp": dt}
    json_str = json.dumps(data, cls=DateTimeEncoder)
    assert '"timestamp": "2024-01-01T12:00:00+00:00"' in json_str
