"""
Text processing utilities for document chunking and metadata generation.

This module provides functions for:
- Cleaning text content for better processing
- Chunking text into smaller segments for embedding
- Generating metadata for text chunks
- Creating useful titles for chunks
"""

import logging
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Setup logging
logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    Clean text content by removing extra whitespace and normalizing.

    Args:
        text: The input text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Replace multiple newlines with a single newline
    text = re.sub(r"\n+", "\n", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    # Trim leading/trailing whitespace
    text = text.strip()

    return text


def estimate_token_count(text: str) -> int:
    """
    Estimate the number of tokens in a text string.
    This is a simple approximation (avg 4 chars per token).

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    # A very basic estimation - in practice, you might want
    # to use a tokenizer from your LLM library
    return len(text) // 4


def chunk_text_by_tokens(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into chunks based on estimated token count.

    Args:
        text: Input text to chunk
        chunk_size: Target size of each chunk in tokens
        chunk_overlap: Number of tokens to overlap between chunks

    Returns:
        List of text chunks
    """
    if not text:
        return []

    # For demonstration, we'll use a simple paragraph-based chunking
    # In a real implementation, you might want more sophisticated chunking

    paragraphs = text.split("\n")
    chunks = []
    current_chunk = []
    current_size = 0

    for paragraph in paragraphs:
        # Skip empty paragraphs
        if not paragraph.strip():
            continue

        # Estimate tokens in this paragraph
        para_tokens = estimate_token_count(paragraph)

        # If adding this paragraph would exceed the chunk size,
        # save the current chunk and start a new one
        if current_size + para_tokens > chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))

            # Keep some paragraphs for overlap
            overlap_size = 0
            overlap_paragraphs = []

            # Work backwards through current_chunk to create overlap
            for p in reversed(current_chunk):
                p_tokens = estimate_token_count(p)
                if overlap_size + p_tokens <= chunk_overlap:
                    overlap_paragraphs.insert(0, p)
                    overlap_size += p_tokens
                else:
                    break

            current_chunk = overlap_paragraphs
            current_size = overlap_size

        # Add the paragraph to the current chunk
        current_chunk.append(paragraph)
        current_size += para_tokens

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    # If we end up with no chunks (e.g., all empty text),
    # return the original text as a single chunk
    if not chunks and text.strip():
        chunks = [text]

    return chunks


def generate_chunk_title(chunk: str, max_length: int = 60) -> str:
    """
    Generate a title for a text chunk based on its content.

    Args:
        chunk: The text chunk
        max_length: Maximum length of the title

    Returns:
        A title for the chunk
    """
    # Get first line
    lines = chunk.split("\n")
    first_line = lines[0].strip() if lines else ""

    # If first line is a good length, use it
    if first_line and len(first_line) <= max_length and len(first_line) > 10:
        return first_line

    # Otherwise, try to extract a meaningful phrase
    if len(chunk) <= max_length:
        return chunk

    # Take the beginning of the text
    title = chunk[:max_length].strip()

    # Try to cut at a space rather than mid-word
    last_space = title.rfind(" ")
    if last_space > max_length // 2:
        title = title[:last_space]

    # Add ellipsis if we truncated
    if len(title) < len(chunk):
        title += "..."

    return title


def generate_chunk_metadata(
    text: str,
    chunk_id: str,
    document_id: str,
    document_name: str = "",
    chunk_index: int = 0,
    total_chunks: int = 1,
    additional_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate metadata for a text chunk.

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
    # Calculate basic statistics
    token_count = estimate_token_count(text)
    char_count = len(text)

    # Create metadata dictionary
    metadata = {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "document_name": document_name,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "token_count": token_count,
        "char_count": char_count,
        "created_at": get_timestamp(),
    }

    # Add additional metadata if provided
    if additional_metadata:
        metadata.update(additional_metadata)

    return metadata


def get_timestamp() -> str:
    """
    Get current timestamp as string.

    Returns:
        Current timestamp in ISO format
    """
    return time.strftime("%Y-%m-%d %H:%M:%S")


def split_by_section(
    text: str, section_markers: List[str] = ["##", "###", "####"]
) -> List[Tuple[str, str]]:
    """
    Split text by section markers (like markdown headings).

    Args:
        text: Text to split
        section_markers: List of section markers to split on

    Returns:
        List of (section_title, section_content) tuples
    """
    if not text:
        return []

    # Create a regex pattern to match any of the section markers
    pattern = "|".join([re.escape(marker) for marker in section_markers])
    pattern = f"({pattern})\\s+(.+?)\\s*(?:\\n|$)"

    # Find all section headings
    headings = list(re.finditer(pattern, text))

    if not headings:
        # No section headings found, return the entire text as one section
        return [("", text)]

    sections = []

    # Handle text before the first heading
    if headings[0].start() > 0:
        sections.append(("", text[: headings[0].start()].strip()))

    # Process each heading and its content
    for i, match in enumerate(headings):
        title = match.group(2)  # The heading text
        start = match.end()

        # Find the end of this section (start of next section or end of text)
        if i < len(headings) - 1:
            end = headings[i + 1].start()
        else:
            end = len(text)

        # Extract the section content
        content = text[start:end].strip()

        # Add the section
        sections.append((title, content))

    return sections
