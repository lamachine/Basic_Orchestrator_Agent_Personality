from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import re
from .llm_provider import LLMProvider

@dataclass
class RawContent:
    content: str           # Raw text/markdown content
    url: str              # Source URL/identifier
    metadata: Dict        # Source-specific metadata
    content_type: str     # doc|repo|media

@dataclass
class ProcessedChunk:
    content: str          # Chunk content
    title: str           # Generated title
    summary: str         # Generated summary
    embedding: List[float] # Vector embedding
    metadata: Dict       # Enhanced metadata
    url: str
    chunk_number: int
    embedding_model: str
    document_creation_date: Optional[str] = None  # ISO format date string
    document_crawl_date: Optional[str] = None     # ISO format date string

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    """Split text into chunks, respecting code blocks and paragraphs."""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = start + chunk_size

        # If we're at the end of the text, just take what's left
        if end >= text_length:
            chunks.append(text[start:].strip())
            break

        # Try to find a code block boundary first (```)
        chunk = text[start:end]
        code_block = chunk.rfind('```')
        if code_block != -1 and code_block > chunk_size * 0.3:
            end = start + code_block

        # If no code block, try to break at a paragraph
        elif '\n\n' in chunk:
            last_break = chunk.rfind('\n\n')
            if last_break > chunk_size * 0.3:
                end = start + last_break

        # If no paragraph break, try to break at a sentence
        elif '. ' in chunk:
            last_period = chunk.rfind('. ')
            if last_period > chunk_size * 0.3:
                end = start + last_period + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = max(start + 1, end)

    return chunks 

async def summarize_text(text: str) -> str:
    """
    Generate a summary of the given text using the LLM provider.
    
    Args:
        text: The text to summarize
        
    Returns:
        A brief summary of the text
    """
    try:
        llm_provider = LLMProvider()
        result = await llm_provider.get_title_and_summary(text, "")
        await llm_provider.close()
        return result["summary"]
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return "Error generating summary" 