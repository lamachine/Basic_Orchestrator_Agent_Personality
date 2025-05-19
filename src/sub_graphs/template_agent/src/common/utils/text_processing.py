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

from ..utils.logging_utils import get_logger

logger = get_logger(__name__)


class TextProcessor:
    """Utility class for text processing operations."""

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def chunk_text_by_tokens(
        text: str, chunk_size: int = 1000, chunk_overlap: int = 200
    ) -> List[str]:
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
            para_tokens = TextProcessor.estimate_token_count(paragraph)

            # If adding this paragraph would exceed the chunk size,
            # save the current chunk and start a new one
            if current_size + para_tokens > chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))

                # Keep some paragraphs for overlap
                overlap_size = 0
                overlap_paragraphs = []

                # Work backwards through current_chunk to create overlap
                for p in reversed(current_chunk):
                    p_tokens = TextProcessor.estimate_token_count(p)
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

    @staticmethod
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

    @staticmethod
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
        token_count = TextProcessor.estimate_token_count(text)
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
            "title": TextProcessor.generate_chunk_title(text),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        # Add any additional metadata
        if additional_metadata:
            metadata.update(additional_metadata)

        return metadata

    @staticmethod
    def split_by_section(
        text: str, section_markers: List[str] = ["##", "###", "####"]
    ) -> List[Tuple[str, str]]:
        """
        Split text into sections based on markdown-style headers.

        Args:
            text: Input text to split
            section_markers: List of header markers to look for

        Returns:
            List of (title, content) tuples for each section
        """
        if not text:
            return []

        # Create regex pattern for section headers
        pattern = "|".join(f"^{marker}\\s+(.+)$" for marker in section_markers)
        pattern = re.compile(pattern, re.MULTILINE)

        # Find all section headers
        matches = list(pattern.finditer(text))

        if not matches:
            return [("", text)]

        sections = []
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            sections.append((title, content))

        return sections

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from text.

        Args:
            text: Text containing JSON

        Returns:
            Optional[Dict[str, Any]]: Extracted JSON or None if not found
        """
        try:
            # Find JSON-like structure
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}")
        return None

    @staticmethod
    def format_message(content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Format message with metadata.

        Args:
            content: Message content
            metadata: Optional metadata

        Returns:
            str: Formatted message
        """
        if not metadata:
            return content

        # Add timestamp if not present
        if "timestamp" not in metadata:
            metadata["timestamp"] = datetime.now().isoformat()

        # Format metadata
        meta_str = json.dumps(metadata, indent=2)
        return f"{content}\n\nMetadata:\n{meta_str}"

    @staticmethod
    def extract_code_blocks(text: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from text.

        Args:
            text: Text containing code blocks

        Returns:
            List[Dict[str, str]]: List of code blocks with language
        """
        # Match code blocks with language specifier
        pattern = r"```(\w+)?\n(.*?)\n```"
        matches = re.finditer(pattern, text, re.DOTALL)

        blocks = []
        for match in matches:
            language = match.group(1)
            code = match.group(2)
            blocks.append({"language": language, "code": code.strip()})

        return blocks

    @staticmethod
    def extract_links(text: str) -> List[str]:
        """
        Extract URLs from text.

        Args:
            text: Text containing URLs

        Returns:
            List[str]: List of URLs
        """
        # Match URLs
        pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        return re.findall(pattern, text)

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """
        Extract email addresses from text.

        Args:
            text: Text containing email addresses

        Returns:
            List[str]: List of email addresses
        """
        # Match email addresses
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        return re.findall(pattern, text)

    @staticmethod
    def extract_phone_numbers(text: str) -> List[str]:
        """
        Extract phone numbers from text.

        Args:
            text: Text containing phone numbers

        Returns:
            List[str]: List of phone numbers
        """
        # Match phone numbers
        pattern = r"\+?1?\s*\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}"
        return re.findall(pattern, text)

    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """
        Extract dates from text.

        Args:
            text: Text containing dates

        Returns:
            List[str]: List of dates
        """
        # Match dates in various formats
        patterns = [
            r"\d{1,2}/\d{1,2}/\d{2,4}",  # MM/DD/YYYY
            r"\d{1,2}-\d{1,2}-\d{2,4}",  # MM-DD-YYYY
            r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
            r"\d{1,2}\s+[A-Za-z]+\s+\d{4}",  # DD Month YYYY
        ]

        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, text))

        return dates

    @staticmethod
    def extract_entities(text: str) -> Dict[str, List[str]]:
        """
        Extract various entities from text.

        Args:
            text: Text to process

        Returns:
            Dict[str, List[str]]: Dictionary of extracted entities
        """
        return {
            "links": TextProcessor.extract_links(text),
            "emails": TextProcessor.extract_emails(text),
            "phone_numbers": TextProcessor.extract_phone_numbers(text),
            "dates": TextProcessor.extract_dates(text),
        }
