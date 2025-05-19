"""
Tests for text processing utilities.
"""

import pytest

from src.common.utils.text_processing import (
    clean_text,
    extract_code_blocks,
    extract_emails,
    extract_entities,
    extract_json,
    extract_links,
    format_message,
    split_text,
)


def test_clean_text():
    """Test clean_text() removes extra whitespace."""
    text = "  Hello   World  \n  Test  "
    cleaned = clean_text(text)
    assert cleaned == "Hello World Test"


def test_clean_text_empty():
    """Test clean_text() with empty input."""
    assert clean_text("") == ""
    assert clean_text("   ") == ""


def test_extract_json():
    """Test extract_json() finds and parses JSON."""
    text = 'Some text {"key": "value"} more text'
    json_data = extract_json(text)
    assert json_data == {"key": "value"}


def test_extract_json_multiple():
    """Test extract_json() with multiple JSON objects."""
    text = 'Text {"key1": "value1"} more {"key2": "value2"}'
    json_data = extract_json(text)
    assert json_data == {"key1": "value1", "key2": "value2"}


def test_extract_json_invalid():
    """Test extract_json() with invalid JSON."""
    text = "Text {invalid json} more text"
    json_data = extract_json(text)
    assert json_data == {}


def test_format_message():
    """Test format_message() formats correctly."""
    message = {"role": "user", "content": "Hello"}
    formatted = format_message(message)
    assert formatted == "user: Hello"


def test_format_message_empty():
    """Test format_message() with empty content."""
    message = {"role": "user", "content": ""}
    formatted = format_message(message)
    assert formatted == "user: "


def test_split_text():
    """Test split_text() splits on newlines."""
    text = "Line 1\nLine 2\nLine 3"
    lines = split_text(text)
    assert lines == ["Line 1", "Line 2", "Line 3"]


def test_split_text_empty():
    """Test split_text() with empty input."""
    assert split_text("") == []
    assert split_text("\n\n") == []


def test_extract_code_blocks():
    """Test extract_code_blocks() finds code blocks."""
    text = "Text ```python\ncode\n``` more text"
    blocks = extract_code_blocks(text)
    assert blocks == ["python\ncode"]


def test_extract_code_blocks_multiple():
    """Test extract_code_blocks() with multiple blocks."""
    text = "Text ```python\ncode1\n``` more ```python\ncode2\n```"
    blocks = extract_code_blocks(text)
    assert blocks == ["python\ncode1", "python\ncode2"]


def test_extract_links():
    """Test extract_links() finds URLs."""
    text = "Visit https://example.com and http://test.com"
    links = extract_links(text)
    assert links == ["https://example.com", "http://test.com"]


def test_extract_emails():
    """Test extract_emails() finds email addresses."""
    text = "Contact test@example.com and user@test.com"
    emails = extract_emails(text)
    assert emails == ["test@example.com", "user@test.com"]


def test_extract_entities():
    """Test extract_entities() finds all entity types."""
    text = """
    Visit https://example.com
    Contact test@example.com
    Code: ```python\nprint('test')\n```
    """
    entities = extract_entities(text)
    assert "https://example.com" in entities["links"]
    assert "test@example.com" in entities["emails"]
    assert "python\nprint('test')\n" in entities["code_blocks"]
