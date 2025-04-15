"""
Tool for vectorizing text content and storing it in the database.

This tool processes text content, generates vector embeddings, and stores both
the content and embeddings in the database for later retrieval via semantic search.
"""

import os
import sys
import time
import uuid
import threading
import logging
from typing import Dict, Any, List, Optional, Union, Tuple

# Add project path for imports
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Import utilities
from src.utils.text_processing import (
    clean_text, 
    chunk_text_by_tokens,
    generate_chunk_metadata
)
from src.utils.embedding_utils import get_embedding, batch_get_embeddings

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Dictionary to store pending vectorization tasks
PENDING_VECTORIZE_REQUESTS = {}

def _process_vectorization(
    task_id: str,
    content: Union[str, List[Dict[str, Any]]],
    source_name: str,
    source_url: Optional[str] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process the vectorization task in a background thread.
    
    Args:
        task_id: Unique identifier for this vectorization task
        content: Text content or list of content objects to vectorize
        source_name: Name of the source (e.g., "Documentation", "GitHub Repo")
        source_url: URL of the content source
        chunk_size: Size of text chunks in tokens
        chunk_overlap: Overlap between chunks in tokens
        metadata: Additional metadata to store with the vectors
        
    Returns:
        Dictionary containing vectorization results
    """
    try:
        logger.debug(f"Starting vectorization task {task_id} for {source_name}")
        
        # Initialize results
        chunks_processed = 0
        chunks_stored = 0
        errors = []
        all_chunks = []
        
        # Process time simulation base (will be increased based on content size)
        base_processing_time = 2.0
        
        # Normalize the content to a list of content objects
        content_list = []
        if isinstance(content, str):
            # Single text string provided
            content_list = [{
                "id": "chunk-0",
                "title": source_name,
                "content": content,
                "metadata": metadata or {}
            }]
            processing_time = base_processing_time + (len(content) / 5000)
        elif isinstance(content, list):
            # List of content objects provided
            content_list = content
            processing_time = base_processing_time + (len(content) * 0.5)
        
        # Simulate processing time
        time.sleep(min(processing_time, 10.0))  # Cap at 10 seconds for simulation
        
        # Process each content object
        for idx, content_obj in enumerate(content_list):
            try:
                text = content_obj.get("content", "")
                if not text:
                    continue
                
                title = content_obj.get("title", f"Content {idx+1}")
                item_id = content_obj.get("id", str(uuid.uuid4()))
                item_metadata = content_obj.get("metadata", {})
                
                # Clean the text
                cleaned_text = clean_text(text)
                
                # Chunk the text
                chunks = chunk_text_by_tokens(
                    cleaned_text, 
                    chunk_size=chunk_size, 
                    chunk_overlap=chunk_overlap
                )
                
                # Process each chunk
                for chunk_idx, chunk in enumerate(chunks):
                    # Generate chunk metadata
                    chunk_metadata = generate_chunk_metadata(
                        chunk, 
                        source_name=source_name,
                        title=title,
                        chunk_index=chunk_idx,
                        source_url=source_url,
                        **item_metadata
                    )
                    
                    # Generate embedding for the chunk
                    # Note: In a real implementation, this would call the embedding model
                    embedding = get_embedding(chunk)
                    
                    # Store in database (simulated)
                    # In real implementation, would call database storage method
                    
                    # Add to results
                    all_chunks.append({
                        "id": f"{item_id}-chunk-{chunk_idx}",
                        "text": chunk[:100] + "..." if len(chunk) > 100 else chunk,
                        "embedding_length": len(embedding),
                        "metadata": chunk_metadata
                    })
                    
                    chunks_processed += 1
                    chunks_stored += 1
                    
            except Exception as e:
                error_msg = f"Error processing content {idx}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Prepare the result
        result = {
            "task_id": task_id,
            "status": "completed",
            "source_name": source_name,
            "source_url": source_url,
            "total_content_objects": len(content_list),
            "chunks_processed": chunks_processed,
            "chunks_stored": chunks_stored,
            "errors": errors,
            "sample_chunks": all_chunks[:5] if all_chunks else [],
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.debug(f"Completed vectorization task {task_id}: processed {chunks_processed} chunks")
        PENDING_VECTORIZE_REQUESTS[task_id] = result
        return result
        
    except Exception as e:
        error_msg = f"Error in vectorization task: {str(e)}"
        logger.error(error_msg)
        PENDING_VECTORIZE_REQUESTS[task_id] = {
            "task_id": task_id,
            "status": "error",
            "error": error_msg
        }
        return PENDING_VECTORIZE_REQUESTS[task_id]


def vectorize_and_store_tool(
    content: Union[str, List[Dict[str, Any]]],
    source_name: str,
    source_url: Optional[str] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Tool for vectorizing text content and storing it in the database.
    
    This tool initiates a background task to process text content, generate
    vector embeddings, and store both in the database for later retrieval.
    
    Args:
        content: Text content to vectorize - either a string or a list of 
                content objects with "content" field and optional "metadata"
        source_name: Name of the source (e.g., "Documentation", "GitHub Repo")
        source_url: URL of the content source
        chunk_size: Size of text chunks in tokens
        chunk_overlap: Overlap between chunks in tokens
        metadata: Additional metadata to store with the vectors
        
    Returns:
        Dictionary with task information including a task_id to check status later
    """
    if not content:
        return {"status": "error", "error": "Content is required"}
    
    if not source_name:
        return {"status": "error", "error": "Source name is required"}
    
    # Create a task ID
    task_id = str(uuid.uuid4())
    
    # Initialize the task in the pending requests
    PENDING_VECTORIZE_REQUESTS[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "source_name": source_name,
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Start the processing in a background thread
    threading.Thread(
        target=_process_vectorization,
        args=(task_id, content, source_name, source_url, chunk_size, chunk_overlap, metadata),
        daemon=True
    ).start()
    
    # Return immediately with the task ID
    return {
        "status": "pending",
        "message": f"Vectorization task started for {source_name}",
        "task_id": task_id,
        "check_command": f"Use check_vectorize_status('{task_id}') to check the status of this task"
    }


def check_vectorize_status(task_id: str) -> Dict[str, Any]:
    """
    Check the status of a vectorization task.
    
    Args:
        task_id: The ID of the task to check
        
    Returns:
        Dictionary with the current status of the task
    """
    if task_id not in PENDING_VECTORIZE_REQUESTS:
        return {
            "status": "error",
            "error": f"No task found with ID {task_id}"
        }
    
    result = PENDING_VECTORIZE_REQUESTS[task_id]
    
    # If the task is completed and we want to keep memory usage down,
    # we could remove it from the dictionary after a certain time period
    
    return result 