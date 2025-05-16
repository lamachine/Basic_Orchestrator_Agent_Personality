"""
Text processing utilities for template agent.

This module provides utility functions for text processing and manipulation.
"""

import re
from typing import List, Dict, Any, Optional, Union
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing.
    
    Args:
        text: Text to clean
        
    Returns:
        str: Cleaned text
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    return text.strip()

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
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
    except Exception as e:
        logger.error(f"Error extracting JSON: {e}")
    return None

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
    if 'timestamp' not in metadata:
        metadata['timestamp'] = datetime.now().isoformat()
        
    # Format metadata
    meta_str = json.dumps(metadata, indent=2)
    return f"{content}\n\nMetadata:\n{meta_str}"

def split_text(text: str, max_length: int = 1000) -> List[str]:
    """
    Split text into chunks of maximum length.
    
    Args:
        text: Text to split
        max_length: Maximum chunk length
        
    Returns:
        List[str]: List of text chunks
    """
    if len(text) <= max_length:
        return [text]
        
    chunks = []
    current_chunk = ""
    
    # Split by sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def extract_code_blocks(text: str) -> List[str]:
    """
    Extract code blocks from text.
    
    Args:
        text: Text containing code blocks
        
    Returns:
        List[str]: List of code blocks
    """
    # Match code blocks with language specifier
    pattern = r'```(\w+)?\n(.*?)\n```'
    matches = re.finditer(pattern, text, re.DOTALL)
    
    blocks = []
    for match in matches:
        language = match.group(1)
        code = match.group(2)
        blocks.append({
            'language': language,
            'code': code.strip()
        })
        
    return blocks

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

def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text.
    
    Args:
        text: Text containing email addresses
        
    Returns:
        List[str]: List of email addresses
    """
    # Match email addresses
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, text)

def extract_phone_numbers(text: str) -> List[str]:
    """
    Extract phone numbers from text.
    
    Args:
        text: Text containing phone numbers
        
    Returns:
        List[str]: List of phone numbers
    """
    # Match phone numbers
    pattern = r'\+?1?\s*\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
    return re.findall(pattern, text)

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
        r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY
        r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
        r'\d{4}-\d{2}-\d{2}',        # YYYY-MM-DD
        r'\d{1,2}\s+[A-Za-z]+\s+\d{4}'  # DD Month YYYY
    ]
    
    dates = []
    for pattern in patterns:
        dates.extend(re.findall(pattern, text))
        
    return dates

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract various entities from text.
    
    Args:
        text: Text to process
        
    Returns:
        Dict[str, List[str]]: Dictionary of extracted entities
    """
    return {
        'links': extract_links(text),
        'emails': extract_emails(text),
        'phone_numbers': extract_phone_numbers(text),
        'dates': extract_dates(text),
        'code_blocks': extract_code_blocks(text)
    } 