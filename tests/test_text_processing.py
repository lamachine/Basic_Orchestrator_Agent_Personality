"""
Unit tests for text processing utilities module.

This module contains tests for the text processing utilities provided
by the template agent.
"""

import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.sub_graphs.template_agent.src.common.utils.text_processing import (
    clean_text,
    extract_code_blocks,
    extract_dates,
    extract_emails,
    extract_entities,
    extract_json,
    extract_links,
    extract_phone_numbers,
    format_message,
    split_text,
)


class TestTextProcessing(unittest.TestCase):
    """Test cases for the text processing utilities."""

    # Normal operation tests
    def test_clean_text(self):
        """Test that clean_text() properly cleans text."""
        # Arrange
        dirty_text = '  This   text  has \n extra   spaces  and "smart" quotes  '
        expected = 'This text has extra spaces and "smart" quotes'

        # Act
        result = clean_text(dirty_text)

        # Assert
        self.assertEqual(result, expected)

    def test_extract_json(self):
        """Test that extract_json() extracts JSON from text."""
        # Arrange
        json_text = 'Here is some JSON: {"name": "test", "value": 123}'
        expected = {"name": "test", "value": 123}

        # Act
        result = extract_json(json_text)

        # Assert
        self.assertEqual(result, expected)

    def test_format_message(self):
        """Test that format_message() formats message with metadata."""
        # Arrange
        content = "Test message"
        metadata = {"user": "test_user", "type": "test"}

        # Act
        result = format_message(content, metadata)

        # Assert
        self.assertIn(content, result)
        self.assertIn("Metadata:", result)
        self.assertIn('"user": "test_user"', result)
        self.assertIn('"type": "test"', result)
        self.assertIn('"timestamp":', result)  # Should add timestamp

    def test_split_text_under_limit(self):
        """Test that split_text() returns single chunk when under limit."""
        # Arrange
        text = "This is a short text"
        max_length = 100

        # Act
        result = split_text(text, max_length)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], text)

    def test_split_text_over_limit(self):
        """Test that split_text() splits text properly."""
        # Arrange
        text = (
            "This is the first sentence. This is the second sentence. This is the third sentence."
        )
        max_length = 30

        # Act
        result = split_text(text, max_length)

        # Assert
        self.assertGreater(len(result), 1)
        # Each chunk should be <= max_length
        for chunk in result:
            self.assertLessEqual(len(chunk), max_length)
        # Combined chunks should contain all text (accounting for added spaces)
        self.assertEqual(" ".join(result).replace("  ", " "), text)

    def test_extract_code_blocks(self):
        """Test that extract_code_blocks() extracts code blocks."""
        # Arrange
        text = "Here is some code:\n```python\ndef hello():\n    print('Hello')\n```\nAnd here is more:\n```javascript\nconsole.log('Hello');\n```"

        # Act
        result = extract_code_blocks(text)

        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["language"], "python")
        self.assertEqual(result[0]["code"], "def hello():\n    print('Hello')")
        self.assertEqual(result[1]["language"], "javascript")
        self.assertEqual(result[1]["code"], "console.log('Hello');")

    def test_extract_links(self):
        """Test that extract_links() extracts URLs."""
        # Arrange
        text = "Visit https://example.com and http://test.org or www.example.org for more info."

        # Act
        result = extract_links(text)

        # Assert
        self.assertEqual(len(result), 3)
        self.assertIn("https://example.com", result)
        self.assertIn("http://test.org", result)
        self.assertIn("www.example.org", result)

    def test_extract_emails(self):
        """Test that extract_emails() extracts email addresses."""
        # Arrange
        text = "Contact user@example.com or admin.test@test.org for support."

        # Act
        result = extract_emails(text)

        # Assert
        self.assertEqual(len(result), 2)
        self.assertIn("user@example.com", result)
        self.assertIn("admin.test@test.org", result)

    def test_extract_phone_numbers(self):
        """Test that extract_phone_numbers() extracts phone numbers."""
        # Arrange
        text = "Call (123) 456-7890 or +1-123-456-7890 for more information."

        # Act
        result = extract_phone_numbers(text)

        # Assert
        self.assertEqual(len(result), 2)
        self.assertIn("(123) 456-7890", result)
        self.assertIn("+1-123-456-7890", result)

    def test_extract_dates(self):
        """Test that extract_dates() extracts dates."""
        # Arrange
        text = "Meeting on 01/15/2023 or 2023-01-15 or 15 January 2023."

        # Act
        result = extract_dates(text)

        # Assert
        self.assertEqual(len(result), 3)
        self.assertIn("01/15/2023", result)
        self.assertIn("2023-01-15", result)
        self.assertIn("15 January 2023", result)

    def test_extract_entities(self):
        """Test that extract_entities() extracts all entity types."""
        # Arrange
        text = "Contact user@example.com or call (123) 456-7890 on 01/15/2023. Visit https://example.com for code:\n```python\nprint('Hello')\n```"

        # Act
        result = extract_entities(text)

        # Assert
        self.assertIn("links", result)
        self.assertIn("emails", result)
        self.assertIn("phone_numbers", result)
        self.assertIn("dates", result)
        self.assertIn("code_blocks", result)
        self.assertEqual(len(result["emails"]), 1)
        self.assertEqual(len(result["phone_numbers"]), 1)
        self.assertEqual(len(result["links"]), 1)
        self.assertEqual(len(result["dates"]), 1)
        self.assertEqual(len(result["code_blocks"]), 1)

    # Error condition tests
    def test_extract_json_invalid(self):
        """Test that extract_json() returns None for invalid JSON."""
        # Arrange
        invalid_json = 'This contains invalid JSON: {"name": "test", unclosed'

        # Act
        result = extract_json(invalid_json)

        # Assert
        self.assertIsNone(result)

    def test_extract_json_no_json(self):
        """Test that extract_json() returns None when no JSON is found."""
        # Arrange
        no_json = "This text has no JSON content"

        # Act
        result = extract_json(no_json)

        # Assert
        self.assertIsNone(result)

    def test_format_message_no_metadata(self):
        """Test that format_message() works without metadata."""
        # Arrange
        content = "Test message"

        # Act
        result = format_message(content)

        # Assert
        self.assertEqual(result, content)  # Should return content unchanged

    @patch("json.dumps")
    def test_format_message_error(self, mock_dumps):
        """Test that format_message() handles JSON errors."""
        # Arrange
        content = "Test message"
        metadata = {"user": "test_user"}
        mock_dumps.side_effect = Exception("JSON error")

        # Act & Assert
        with self.assertRaises(Exception):
            format_message(content, metadata)

    def test_extract_code_blocks_malformed(self):
        """Test that extract_code_blocks() handles malformed code blocks."""
        # Arrange
        malformed = "```python\ndef incomplete():\n```missing closing"

        # Act
        result = extract_code_blocks(malformed)

        # Assert
        self.assertEqual(len(result), 0)  # Should not extract malformed blocks

    # Edge case tests
    def test_clean_text_empty(self):
        """Test that clean_text() handles empty text."""
        # Arrange
        empty = ""

        # Act
        result = clean_text(empty)

        # Assert
        self.assertEqual(result, "")

    def test_extract_json_nested(self):
        """Test that extract_json() handles nested JSON."""
        # Arrange
        nested_json = 'Complex: {"user": {"name": "test", "data": {"active": true}}}'
        expected = {"user": {"name": "test", "data": {"active": True}}}

        # Act
        result = extract_json(nested_json)

        # Assert
        self.assertEqual(result, expected)

    def test_split_text_exact_limit(self):
        """Test that split_text() handles text exactly at the limit."""
        # Arrange
        text = "This is exactly the limit."
        max_length = len(text)

        # Act
        result = split_text(text, max_length)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], text)

    def test_extract_code_blocks_no_language(self):
        """Test that extract_code_blocks() handles blocks with no language."""
        # Arrange
        no_lang = "Here is code:\n```\ndef test():\n    pass\n```"

        # Act
        result = extract_code_blocks(no_lang)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["language"])
        self.assertEqual(result[0]["code"], "def test():\n    pass")

    def test_extract_entities_empty(self):
        """Test that extract_entities() handles empty text."""
        # Arrange
        empty = ""

        # Act
        result = extract_entities(empty)

        # Assert
        self.assertEqual(len(result["links"]), 0)
        self.assertEqual(len(result["emails"]), 0)
        self.assertEqual(len(result["phone_numbers"]), 0)
        self.assertEqual(len(result["dates"]), 0)
        self.assertEqual(len(result["code_blocks"]), 0)

    def test_extract_emails_complex(self):
        """Test that extract_emails() handles complex email addresses."""
        # Arrange
        complex_emails = "Contact first.last+tag@sub.example.com or user-name@example.co.uk"

        # Act
        result = extract_emails(complex_emails)

        # Assert
        self.assertEqual(len(result), 2)
        self.assertIn("first.last+tag@sub.example.com", result)
        self.assertIn("user-name@example.co.uk", result)
