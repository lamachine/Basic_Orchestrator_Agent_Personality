"""
GitHub Adapter

This module provides synchronous wrapper functions around the async GitHub crawler
functionality, adapted to use the orchestrator's database and LLM interfaces.
"""

import os
import sys
import asyncio
import threading
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Import orchestrator's database manager
from src.services.db_services.db_manager import DatabaseManager

# Import LLMService directly
from src.services.llm_services.llm_service import LLMService

# Global LLM service and agent for embedding generation
llm_service = None
llm_agent = None

def set_llm_agent(agent):
    """Set the LLM agent for embedding generation."""
    global llm_agent, llm_service
    llm_agent = agent
    
    # Initialize LLM service if not already available
    if llm_service is None:
        ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        llm_service = LLMService(ollama_url, embedding_model)
    
    logger.debug("LLM agent and service set for GitHub adapter")

def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector for text using LLMService.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector as a list of floats
    """
    global llm_service
    
    # Initialize LLM service if not already available
    if llm_service is None:
        ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        llm_service = LLMService(ollama_url, embedding_model)
        
    try:
        # Use LLMService to get embeddings directly
        embedding = llm_service.get_embedding(text)
        return embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return [0.0] * 768  # Return dummy embedding on error

def run_async(async_func, *args, **kwargs):
    """
    Run an async function synchronously.
    
    Args:
        async_func: Async function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the async function
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(async_func(*args, **kwargs))
    finally:
        loop.close()

def sync_get_repo_structure(repo_url: str) -> List[str]:
    """
    Synchronous wrapper for getting repository structure.
    
    Args:
        repo_url: URL of the repository
        
    Returns:
        List of file paths in the repository
    """
    # Import from the correct path
    from src.tools.crawler.repos.github_crawler import get_repo_structure
    try:
        return run_async(get_repo_structure, repo_url)
    except Exception as e:
        logger.error(f"Error getting repo structure: {e}")
        return []

def sync_get_file_content(repo_url: str, file_path: str) -> str:
    """
    Synchronous wrapper for getting file content.
    
    Args:
        repo_url: URL of the repository
        file_path: Path to the file in the repository
        
    Returns:
        Content of the file
    """
    # Import from the correct path
    from src.tools.crawler.repos.github_crawler import get_file_content
    try:
        return run_async(get_file_content, repo_url, file_path)
    except Exception as e:
        logger.error(f"Error getting file content: {e}")
        return ""

def sync_process_and_store_document(content: str, file_path: str, repo_url: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for processing and storing document.
    
    Args:
        content: Content of the file
        file_path: Path to the file in the repository
        repo_url: URL of the repository
        
    Returns:
        Processing result
    """
    # Import from the correct path
    from src.tools.crawler.repos.github_crawler import process_and_store_document
    try:
        return run_async(process_and_store_document, content, file_path, repo_url)
    except Exception as e:
        logger.error(f"Error processing and storing document: {e}")
        return {"status": "error", "error": str(e)}

def sync_download_repo(repo_url: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for downloading repository.
    
    Args:
        repo_url: URL of the repository
        
    Returns:
        Download result
    """
    # Import from the correct path
    from src.tools.crawler.repos.github_crawler import download_repo
    try:
        # Extract repo name from URL
        parts = repo_url.rstrip("/").split("/")
        owner = parts[-2]
        repo = parts[-1]
        
        # Get source name for easy tracking
        source_name = f"repo_{repo}"
        logger.debug(f"Starting repository download for {source_name} from {repo_url}")
        
        # Process the repository
        result = run_async(download_repo, repo_url)
        
        # Verify storage info
        logger.debug(f"Download completed for {source_name}, checking for storage details")
        storage_info = {
            "source_name": source_name,
            "processed_files": 0,
            "chunks_stored": 0,
            "storage_locations": []
        }
        
        # Try to extract storage details from the result if available
        if isinstance(result, dict):
            storage_info["processed_files"] = result.get("processed_files", 0)
            storage_info["chunks_stored"] = result.get("chunks_stored", 0)
            storage_info["storage_locations"] = result.get("storage_locations", [])
            
        # Log detailed storage information
        logger.debug(f"Repository {source_name} download statistics:")
        logger.debug(f"- Processed files: {storage_info['processed_files']}")
        logger.debug(f"- Chunks stored: {storage_info['chunks_stored']}")
        
        # Format the response with detailed storage info
        return {
            "repository": {
                "name": repo,
                "owner": owner,
                "url": repo_url,
                "source_name": source_name
            },
            "status": "completed",
            "message": f"Repository {owner}/{repo} successfully downloaded and processed",
            "storage_info": storage_info
        }
    except Exception as e:
        logger.error(f"Error downloading repo: {e}")
        return {
            "status": "error", 
            "error": str(e),
            "message": f"Failed to download repository: {str(e)}"
        }

def store_chunks_in_orchestrator_db(processed_chunks: List[Dict[str, Any]], repo_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Store processed chunks in orchestrator's database.
    
    Args:
        processed_chunks: List of processed chunks
        repo_url: URL of the repository being processed
        
    Returns:
        Storage result
    """
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        stored_count = 0
        source_name = None
        
        logger.debug(f"Storing {len(processed_chunks)} chunks in repo_content table")
        
        # Initial validation - skip empty first chunk if invalid
        if processed_chunks and len(processed_chunks) > 0:
            first_chunk = processed_chunks[0]
            if not first_chunk.get("content") or len(first_chunk.get("content", "").strip()) < 10:
                logger.warning("First chunk validation failed: content too short or empty")
                if len(processed_chunks) > 1:
                    logger.debug("Skipping first chunk due to validation failure")
                    processed_chunks = processed_chunks[1:]  # Skip the first chunk
                else:
                    logger.error("No valid chunks to process after validation")
                    return {
                        "status": "error",
                        "message": "No valid chunks to process after validation",
                        "chunks_stored": 0
                    }
        
        # Start counter at 20 for validation purposes
        initial_count = 20
        
        # Store each chunk
        for i, chunk in enumerate(processed_chunks):
            try:
                # Extract data from chunk
                content = chunk.get("content", "")
                metadata = chunk.get("metadata", {})
                embedding = chunk.get("embedding", [])
                
                # Skip empty or very small chunks
                if not content or len(content.strip()) < 10:
                    logger.warning(f"Skipping chunk {i} due to insufficient content")
                    continue
                
                # Keep track of source name for reporting
                if "source" in metadata and not source_name:
                    source_name = metadata["source"]
                    logger.debug(f"Found source name in metadata: {source_name}")
                
                # Make sure we're using a 'repo_' prefixed source name for easy querying
                if source_name and not source_name.startswith("repo_"):
                    source_name = f"repo_{source_name}"
                    metadata["source"] = source_name
                
                # Directly insert into repo_content table
                logger.debug(f"Storing chunk {i+1}/{len(processed_chunks)} with content length: {len(content)}")
                
                # Add timestamp to metadata if not present
                if "timestamp" not in metadata:
                    metadata["timestamp"] = datetime.now().isoformat() 
                
                # Add chunk number starting from initial_count (20)
                if "chunk_number" not in metadata:
                    metadata["chunk_number"] = i + initial_count
                
                # Insert directly into repo_content table
                # Use embedding_nomic column instead of embedding
                result = db_manager.supabase.table('repo_content').insert({
                    'content': content,
                    'metadata': metadata,
                    'embedding_nomic': embedding,
                    'repo_url': repo_url or metadata.get("repo_url", ""),
                    'file_path': metadata.get("file_path", ""),
                    'branch': metadata.get("branch") or os.getenv("CURRENT_SOURCE_BRANCH", "main"),
                    'title': metadata.get("title", metadata.get("file_path", "unknown file").split("/")[-1]),
                    'summary': metadata.get("summary", f"Content from {metadata.get('file_path', 'unknown file')}"),
                    'embedding_model': metadata.get("embedding_model", "nomic-embed-text"),
                    'chunk_number': metadata.get("chunk_number", i + initial_count)
                }).execute()
                
                logger.debug(f"Insert result status: {result.status_code if hasattr(result, 'status_code') else 'unknown'}")
                
                stored_count += 1
                
                # Log progress periodically
                if i % 10 == 0 or i == len(processed_chunks) - 1:
                    logger.debug(f"Stored {stored_count}/{len(processed_chunks)} chunks so far")
                
            except Exception as chunk_error:
                logger.error(f"Error storing chunk {i+1}: {chunk_error}")
        
        # Report what we stored 
        storage_locations = ["repo_content"]
        logger.debug(f"Stored {stored_count} chunks with source: {source_name or 'unknown'}")
        logger.debug(f"Data stored in: {storage_locations}")
        
        return {
            "status": "success",
            "chunks_stored": stored_count,
            "processed_files": len(processed_chunks),
            "source_name": source_name,
            "storage_locations": storage_locations,
            "message": f"Successfully stored {stored_count} chunks in repo_content table"
        }
    except Exception as e:
        logger.error(f"Error storing chunks in database: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to store chunks in database: {str(e)}"
        } 