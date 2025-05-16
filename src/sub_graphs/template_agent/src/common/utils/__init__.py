"""
Utility modules for template agent.
"""

from .datetime_utils import now, parse_datetime, format_datetime, timestamp
from .text_processing import (
    clean_text,
    extract_json,
    format_message,
    split_text,
    extract_code_blocks,
    extract_links,
    extract_emails,
    extract_phone_numbers,
    extract_dates,
    extract_entities
)
from .embedding_utils import EmbeddingManager

__all__ = [
    'now',
    'parse_datetime',
    'format_datetime',
    'timestamp',
    'clean_text',
    'extract_json',
    'format_message',
    'split_text',
    'extract_code_blocks',
    'extract_links',
    'extract_emails',
    'extract_phone_numbers',
    'extract_dates',
    'extract_entities',
    'EmbeddingManager'
] 