"""
Unit tests for datetime utilities module.

This module contains tests for the datetime utilities provided
by the template agent.
"""

import unittest
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import json

from src.sub_graphs.template_agent.src.common.utils.datetime_utils import (
    now,
    get_local_datetime_str,
    format_datetime,
    parse_datetime,
    timestamp,
    DateTimeEncoder
)

class TestDatetimeUtils(unittest.TestCase):
    """Test cases for the datetime utilities."""
    
    # Normal operation tests
    def test_now(self):
        """Test that now() returns a UTC datetime."""
        # Act
        result = now()
        
        # Assert
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.tzinfo, timezone.utc)
    
    def test_get_local_datetime_str(self):
        """Test that get_local_datetime_str() returns a properly formatted string."""
        # Act
        result = get_local_datetime_str()
        
        # Assert
        self.assertIsInstance(result, str)
        self.assertRegex(result, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
    
    def test_format_datetime(self):
        """Test that format_datetime() formats a datetime correctly."""
        # Arrange
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Act
        result = format_datetime(dt)
        
        # Assert
        self.assertEqual(result, "2023-01-01T12:00:00+00:00")
    
    def test_parse_datetime(self):
        """Test that parse_datetime() parses a datetime string correctly."""
        # Arrange
        dt_str = "2023-01-01T12:00:00+00:00"
        
        # Act
        result = parse_datetime(dt_str)
        
        # Assert
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2023)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.hour, 12)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.second, 0)
        self.assertEqual(result.tzinfo, timezone.utc)
    
    def test_timestamp(self):
        """Test that timestamp() returns the correct timestamp value."""
        # Arrange
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        expected = 1672574400.0  # Known timestamp for 2023-01-01T12:00:00+00:00
        
        # Act
        result = timestamp(dt)
        
        # Assert
        self.assertEqual(result, expected)
    
    def test_timestamp_default(self):
        """Test that timestamp() with no argument uses current time."""
        # Act
        result = timestamp()
        
        # Assert
        self.assertIsInstance(result, float)
        # Should be a recent timestamp (within last day)
        self.assertGreater(result, datetime.now().timestamp() - 86400)
    
    def test_datetime_encoder_datetime(self):
        """Test that DateTimeEncoder correctly encodes datetime objects."""
        # Arrange
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        encoder = DateTimeEncoder()
        
        # Act
        result = encoder.default(dt)
        
        # Assert
        self.assertEqual(result, "2023-01-01T12:00:00+00:00")
    
    def test_datetime_json_serialization(self):
        """Test that datetime objects are correctly serialized in JSON."""
        # Arrange
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        data = {"date": dt}
        
        # Act
        result = json.dumps(data, cls=DateTimeEncoder)
        
        # Assert
        self.assertEqual(result, '{"date": "2023-01-01T12:00:00+00:00"}')
    
    # Error condition tests
    def test_format_datetime_error(self):
        """Test that format_datetime() raises on invalid input."""
        # Arrange
        invalid_dt = "not a datetime"
        
        # Act & Assert
        with self.assertRaises(Exception):
            format_datetime(invalid_dt)
    
    def test_parse_datetime_invalid_format(self):
        """Test that parse_datetime() raises on invalid format."""
        # Arrange
        invalid_format = "01/01/2023"  # Not ISO format
        
        # Act & Assert
        with self.assertRaises(ValueError):
            parse_datetime(invalid_format)
    
    def test_parse_datetime_empty_string(self):
        """Test that parse_datetime() raises on empty string."""
        # Arrange
        empty_string = ""
        
        # Act & Assert
        with self.assertRaises(ValueError):
            parse_datetime(empty_string)
    
    @patch('src.sub_graphs.template_agent.src.common.utils.datetime_utils.datetime')
    def test_now_error(self, mock_datetime):
        """Test that now() propagates errors."""
        # Arrange
        mock_datetime.now.side_effect = Exception("Test error")
        
        # Act & Assert
        with self.assertRaises(Exception):
            now()
    
    def test_datetime_encoder_non_serializable(self):
        """Test that DateTimeEncoder raises on non-serializable objects."""
        # Arrange
        encoder = DateTimeEncoder()
        non_serializable = object()  # An object that can't be serialized to JSON
        
        # Act & Assert
        with self.assertRaises(TypeError):
            encoder.default(non_serializable)
    
    # Edge case tests
    def test_parse_datetime_microseconds(self):
        """Test that parse_datetime() handles microseconds correctly."""
        # Arrange
        dt_str = "2023-01-01T12:00:00.123456+00:00"
        
        # Act
        result = parse_datetime(dt_str)
        
        # Assert
        self.assertEqual(result.microsecond, 123456)
    
    def test_format_datetime_naive(self):
        """Test that format_datetime() handles naive datetimes."""
        # Arrange
        naive_dt = datetime(2023, 1, 1, 12, 0, 0)  # No timezone
        
        # Act
        result = format_datetime(naive_dt)
        
        # Assert
        self.assertEqual(result, "2023-01-01T12:00:00")
    
    def test_datetime_encoder_nested(self):
        """Test that DateTimeEncoder handles nested datetime objects."""
        # Arrange
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        nested_data = {
            "outer": {
                "inner": {
                    "date": dt
                }
            }
        }
        
        # Act
        result = json.dumps(nested_data, cls=DateTimeEncoder)
        
        # Assert
        expected = '{"outer": {"inner": {"date": "2023-01-01T12:00:00+00:00"}}}'
        self.assertEqual(result, expected)
    
    def test_timestamp_min_datetime(self):
        """Test that timestamp() handles minimum datetime values."""
        # Arrange - use a very old date, but not too old to cause platform-specific issues
        old_dt = datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
        
        # Act
        result = timestamp(old_dt)
        
        # Assert
        self.assertEqual(result, 1.0)  # 1 second after epoch 