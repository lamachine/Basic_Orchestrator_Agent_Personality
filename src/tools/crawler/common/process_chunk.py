import os
from typing import Dict, List, Any
from datetime import datetime, timezone
from urllib.parse import urlparse

from .llm_provider import LLMProvider
from .text_processing import ProcessedChunk

async def get_title_and_summary(chunk: str, url: str, source_name: str, llm_provider: LLMProvider) -> Dict[str, str]:
    """Extract title and summary using the configured LLM provider."""
    try:
        # Use the LLMProvider's built-in method
        return await llm_provider.get_title_and_summary(chunk, url)
            
    except Exception as e:
        print(f"Error getting title and summary: {e}")
        return {"title": "Error processing title", "summary": "Error processing summary"}

async def process_chunk(chunk: str, chunk_number: int, url: str, llm_provider: LLMProvider, metadata: Dict[str, Any] = None) -> ProcessedChunk:
    """Process a single chunk of text."""
    # Get title and summary using the local function
    source_name = os.getenv("CURRENT_SOURCE_NAME", "unknown")
    extracted = await get_title_and_summary(chunk, url, source_name, llm_provider)
    
    # Get embedding and model name
    embedding = await llm_provider.get_embedding(chunk)
    embedding_model = llm_provider.embedding_provider
    
    # Get provider metadata
    provider_metadata = llm_provider.get_metadata()
    
    # Create base metadata
    base_metadata = {
        "source": os.getenv("CURRENT_SOURCE_NAME", "unknown"),
        "chunk_size": len(chunk),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path": urlparse(url).path,
        "base_url": os.getenv("CURRENT_SOURCE_BASE_URL"),
        "owner": os.getenv("CURRENT_SOURCE_OWNER", "unknown"),
        **provider_metadata  # Include provider and model information
    }
    
    # Merge with provided metadata if any
    if metadata:
        base_metadata.update(metadata)
    
    return ProcessedChunk(
        url=url,
        chunk_number=chunk_number,
        title=extracted['title'],
        summary=extracted['summary'],
        content=chunk,
        document_creation_date=None,  # Could be added if available
        document_crawl_date=datetime.now(timezone.utc).isoformat(),
        metadata=base_metadata,
        embedding=embedding,
        embedding_model=embedding_model
    ) 

async def get_embeddings(text: str) -> Dict[str, List[float]]:
    """
    Get embeddings using Nomic model.
    
    Args:
        text: Text to get embeddings for
        
    Returns:
        Dict with 'nomic' embeddings
    """
    try:
        llm_provider = LLMProvider()
        embedding = await llm_provider.get_embedding(text)
        await llm_provider.close()
        return {
            "nomic": embedding
        }
    except Exception as e:
        print(f"Error getting embeddings: {e}")
        # Return zero vector on error
        return {
            "nomic": [0] * 768
        } 