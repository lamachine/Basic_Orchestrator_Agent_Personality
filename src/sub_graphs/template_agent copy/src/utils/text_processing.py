"""
Template Agent Text Processing Utilities.

This module provides text processing utilities for the template agent,
inheriting core functionality from the orchestrator's text processing utilities
but adding template-specific text handling.
"""

import logging
import re
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from src.utils.text_processing import (
    clean_text as base_clean_text,
    estimate_token_count as base_estimate_token_count,
    chunk_text_by_tokens as base_chunk_text_by_tokens,
    generate_chunk_title as base_generate_chunk_title,
    generate_chunk_metadata as base_generate_chunk_metadata,
    get_timestamp as base_get_timestamp,
    split_by_section as base_split_by_section
)

from ..services.logging_service import get_logger

logger = get_logger(__name__)

def clean_text(text: str) -> str:
    """
    Clean text content with template-specific handling.
    
    Args:
        text: The input text to clean
        
    Returns:
        Cleaned text
    """
    cleaned = base_clean_text(text)
    logger.debug(f"Cleaned template text: {cleaned[:100]}...")
    return cleaned

def estimate_token_count(text: str) -> int:
    """
    Estimate the number of tokens in a text string with template validation.
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    count = base_estimate_token_count(text)
    logger.debug(f"Estimated template token count: {count}")
    return count

def chunk_text_by_tokens(
    text: str, 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[str]:
    """
    Split text into chunks with template-specific handling.
    
    Args:
        text: Input text to chunk
        chunk_size: Target size of each chunk in tokens
        chunk_overlap: Number of tokens to overlap between chunks
        
    Returns:
        List of text chunks
    """
    chunks = base_chunk_text_by_tokens(text, chunk_size, chunk_overlap)
    logger.debug(f"Created {len(chunks)} template text chunks")
    return chunks

def generate_chunk_title(chunk: str, max_length: int = 60) -> str:
    """
    Generate a title for a text chunk with template context.
    
    Args:
        chunk: The text chunk
        max_length: Maximum length of the title
        
    Returns:
        A title for the chunk
    """
    title = base_generate_chunk_title(chunk, max_length)
    logger.debug(f"Generated template chunk title: {title}")
    return title

def generate_chunk_metadata(
    text: str,
    chunk_id: str,
    document_id: str,
    document_name: str = "",
    chunk_index: int = 0,
    total_chunks: int = 1,
    additional_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate metadata for a text chunk with template context.
    
    Args:
        text: The chunk text
        chunk_id: Unique identifier for this chunk
        document_id: ID of the parent document
        document_name: Name of the parent document
        chunk_index: Index of this chunk in sequence
        total_chunks: Total number of chunks in the document
        additional_metadata: Any additional metadata to include
        
    Returns:
        Dictionary with metadata for the chunk
    """
    # Add template-specific metadata
    if additional_metadata is None:
        additional_metadata = {}
    
    additional_metadata["source"] = "template"
    additional_metadata["processed_at"] = datetime.now().isoformat()
    
    metadata = base_generate_chunk_metadata(
        text,
        chunk_id,
        document_id,
        document_name,
        chunk_index,
        total_chunks,
        additional_metadata
    )
    
    logger.debug(f"Generated template chunk metadata for chunk {chunk_id}")
    return metadata

def get_timestamp() -> str:
    """Get a timestamp string with template context."""
    ts = base_get_timestamp()
    logger.debug(f"Generated template timestamp: {ts}")
    return ts

def split_by_section(
    text: str, 
    section_markers: List[str] = ["##", "###", "####"]
) -> List[Tuple[str, str]]:
    """
    Split text into sections with template-specific handling.
    
    Args:
        text: Input text to split
        section_markers: List of section marker strings
        
    Returns:
        List of (title, content) tuples
    """
    sections = base_split_by_section(text, section_markers)
    logger.debug(f"Split template text into {len(sections)} sections")
    return sections 