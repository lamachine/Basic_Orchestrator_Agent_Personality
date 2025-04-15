import os
from typing import List, Dict, Any
from datetime import datetime
import logging
from dotenv import load_dotenv

from src.services.db_services.db_manager import DatabaseManager
from .text_processing import ProcessedChunk

# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables first
load_dotenv(override=True)

# For backwards compatibility - supabase variable can stay,
# but we'll use our own DatabaseManager for actual storage
supabase = None

# Initialize database manager
def get_db_manager():
    """Get a database manager instance."""
    return DatabaseManager()

def get_content_type() -> str:
    """
    Get the content type from environment variables or crawler task.
    
    Returns:
        String indicating content type (repo, docs, media)
    """
    # First try to get from environment
    content_type = os.getenv("CONTENT_TYPE", "").lower()
    
    # If not set explicitly, try to infer from other environment variables
    if not content_type:
        if os.getenv("CURRENT_SOURCE_BASE_URL", "").lower().find("github.com") > -1:
            content_type = "repo"
        elif os.getenv("CURRENT_SOURCE_NAME", "").lower().startswith("doc"):
            content_type = "docs"
        else:
            content_type = "unknown"
            
    logger.debug(f"Detected content type: {content_type}")
    return content_type

async def store_chunks(chunks: List[ProcessedChunk], content_type: str = None) -> bool:
    """
    Store processed chunks in the database. Returns True if successful.
    
    Args:
        chunks: List of processed chunks to store
        content_type: Optional content type override (repo, docs, media)
        
    Returns:
        Boolean indicating success
    """
    db_manager = get_db_manager()
    success = True
    count = 0
    stored_count = 0
    
    # If content_type not provided, try to determine it
    if not content_type:
        content_type = get_content_type()
    
    # Start counter at 20 for validation purposes
    initial_count = 20
    
    # Validate the first chunk before processing
    if chunks and len(chunks) > 0:
        first_chunk = chunks[0]
        if not first_chunk.content or len(first_chunk.content.strip()) < 10:
            logger.warning(f"First chunk validation failed: content too short or empty")
            if len(chunks) > 1:
                logger.debug("Skipping first chunk due to validation failure")
                chunks = chunks[1:]  # Skip the first chunk
            else:
                logger.error("No valid chunks to process after validation")
                return False
    
    for i, chunk in enumerate(chunks):
        try:
            # Extract essential data from the chunk
            content = chunk.content
            metadata = chunk.metadata.copy() if chunk.metadata else {}
            embedding = chunk.embedding
            
            # Skip empty or very small chunks
            if not content or len(content.strip()) < 10:
                logger.warning(f"Skipping chunk {i} due to insufficient content")
                continue
            
            # Create a unique session ID based on content type
            if content_type == "repo":
                repo_url = os.getenv("CURRENT_SOURCE_BASE_URL", "")
                file_path = metadata.get("file_path", "")
                session_id = f"repo_{repo_url.replace('https://', '').replace('/', '_')}_{file_path.replace('/', '_')}"
                
                # Add repo-specific metadata
                metadata.update({
                    "repo_url": repo_url,
                    "file_path": file_path,
                    "branch": os.getenv("CURRENT_SOURCE_BRANCH", "main"),
                    "owner": metadata.get("owner", os.getenv("CURRENT_SOURCE_OWNER", ""))
                })
                
            elif content_type == "docs":
                # For documentation pages
                doc_url = chunk.url or os.getenv("CURRENT_SOURCE_BASE_URL", "")
                page_title = chunk.title.replace(" ", "_") if chunk.title else "page"
                session_id = f"docs_{doc_url.replace('https://', '').replace('/', '_')}_{page_title}"
                
                # Add docs-specific metadata
                metadata.update({
                    "doc_url": doc_url,
                    "page_title": chunk.title,
                    "documentation_site": os.getenv("CURRENT_SOURCE_NAME", "")
                })
                
            elif content_type == "media":
                # For media content
                media_url = chunk.url or metadata.get("media_url", "unknown")
                media_type = metadata.get("media_type", "unknown")
                session_id = f"media_{media_type}_{media_url.replace('https://', '').replace('/', '_')}"
                
                # Add media-specific metadata
                metadata.update({
                    "media_url": media_url,
                    "media_type": media_type,
                    "description": metadata.get("description", ""),
                    "transcript": metadata.get("transcript", ""),
                    "duration": metadata.get("duration", None),
                    "publish_date": metadata.get("publish_date", None)
                })
                
            else:
                # Generic fallback
                source_name = os.getenv("CURRENT_SOURCE_NAME", "content").replace(" ", "_")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                session_id = f"content_{source_name}_{timestamp}_{chunk.chunk_number}"
            
            # Add timestamp to metadata if not present
            if "timestamp" not in metadata:
                metadata["timestamp"] = datetime.now().isoformat()
            
            # Store directly in repo_content table instead of using add_message
            result = db_manager.supabase.table('repo_content').insert({
                'content': content,
                'metadata': {
                    "title": chunk.title,
                    "summary": chunk.summary,
                    "url": chunk.url,
                    "chunk_number": chunk.chunk_number + initial_count,  # Start counting from 20
                    "document_creation_date": chunk.document_creation_date,
                    "document_crawl_date": chunk.document_crawl_date,
                    "content_type": content_type,
                    "source": metadata.get("source", os.getenv("CURRENT_SOURCE_NAME")),
                    **metadata  # Include all content-specific metadata
                },
                'embedding_nomic': embedding,  # Use embedding_nomic column instead of embedding
                'repo_url': metadata.get("repo_url") or os.getenv("CURRENT_SOURCE_BASE_URL", ""),
                'file_path': metadata.get("file_path", ""),
                'branch': metadata.get("branch") or os.getenv("CURRENT_SOURCE_BRANCH", "main"),
                'title': chunk.title or metadata.get("title", "Untitled"),
                'summary': chunk.summary or metadata.get("summary", f"Content from {metadata.get('file_path', 'unknown file')}"),
                'embedding_model': metadata.get("embedding_model", "nomic-embed-text"),
                'chunk_number': chunk.chunk_number + initial_count
            }).execute()
            
            count += 1
            stored_count += 1
            
            # Log progress periodically
            if count % 10 == 0 or count == len(chunks):
                logger.debug(f"Stored {stored_count}/{len(chunks)} chunks so far for content type {content_type}")
            
        except Exception as e:
            logger.error(f"Error storing chunk: {e}")
            success = False
            
    logger.debug(f"Completed storing {stored_count} chunks in repo_content table")
    return success 