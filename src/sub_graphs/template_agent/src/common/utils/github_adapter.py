"""
GitHub Adapter Module

This module provides functionality for interacting with GitHub repositories.
It includes:
1. Repository cloning and management
2. File operations
3. Branch management
4. Commit handling
5. Pull request operations
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..services.db_service import DBService
from ..utils.logging_utils import get_logger

logger = get_logger(__name__)


def run_async(async_func, *args, **kwargs):
    """Run an async function synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(async_func(*args, **kwargs))
    finally:
        loop.close()


def sync_get_repo_structure(repo_url: str) -> List[str]:
    """Get repository structure (sync wrapper)."""
    from ...tools.crawler.repos.github_crawler import get_repo_structure

    try:
        return run_async(get_repo_structure, repo_url)
    except Exception as e:
        logger.error(f"Error getting repo structure: {e}")
        return []


def sync_get_file_content(repo_url: str, file_path: str) -> str:
    """Get file content (sync wrapper)."""
    from ...tools.crawler.repos.github_crawler import get_file_content

    try:
        return run_async(get_file_content, repo_url, file_path)
    except Exception as e:
        logger.error(f"Error getting file content: {e}")
        return ""


def sync_process_and_store_document(
    content: str,
    file_path: str,
    repo_url: str,
    db_service: DBService,
    embedding_service: EmbeddingService,
) -> Dict[str, Any]:
    """Process and store document (sync wrapper)."""
    from ...tools.crawler.repos.github_crawler import process_and_store_document

    try:
        return run_async(
            process_and_store_document,
            content,
            file_path,
            repo_url,
            db_service,
            embedding_service,
        )
    except Exception as e:
        logger.error(f"Error processing and storing document: {e}")
        return {"status": "error", "error": str(e)}


def sync_download_repo(
    repo_url: str, db_service: DBService, embedding_service: EmbeddingService
) -> Dict[str, Any]:
    """Download repository (sync wrapper)."""
    from ...tools.crawler.repos.github_crawler import download_repo

    try:
        parts = repo_url.rstrip("/").split("/")
        owner = parts[-2]
        repo = parts[-1]
        source_name = f"repo_{repo}"
        logger.debug(f"Starting repository download for {source_name} from {repo_url}")
        result = run_async(download_repo, repo_url, db_service, embedding_service)
        storage_info = {
            "source_name": source_name,
            "processed_files": (
                result.get("processed_files", 0) if isinstance(result, dict) else 0
            ),
            "chunks_stored": (result.get("chunks_stored", 0) if isinstance(result, dict) else 0),
            "storage_locations": (
                result.get("storage_locations", []) if isinstance(result, dict) else []
            ),
        }
        logger.debug(f"Repository {source_name} download complete: {storage_info}")
        return {
            "repository": {
                "name": repo,
                "owner": owner,
                "url": repo_url,
                "source_name": source_name,
            },
            "status": "completed",
            "message": f"Repository {owner}/{repo} successfully downloaded and processed",
            "storage_info": storage_info,
        }
    except Exception as e:
        logger.error(f"Error downloading repo: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to download repository: {str(e)}",
        }


def store_chunks_in_db(
    processed_chunks: List[Dict[str, Any]],
    db_service: DBService,
    repo_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Store processed chunks in database."""
    try:
        stored_count = 0
        source_name = None
        if processed_chunks and len(processed_chunks) > 0:
            first_chunk = processed_chunks[0]
            if not first_chunk.get("content") or len(first_chunk.get("content", "").strip()) < 10:
                logger.warning("First chunk validation failed: content too short or empty")
                if len(processed_chunks) > 1:
                    processed_chunks = processed_chunks[1:]
                else:
                    logger.error("No valid chunks to process after validation")
                    return {
                        "status": "error",
                        "message": "No valid chunks to process after validation",
                        "chunks_stored": 0,
                    }
        initial_count = 20
        for i, chunk in enumerate(processed_chunks):
            try:
                content = chunk.get("content", "")
                metadata = chunk.get("metadata", {})
                embedding = chunk.get("embedding", [])
                if not content or len(content.strip()) < 10:
                    logger.warning(f"Skipping chunk {i} due to insufficient content")
                    continue
                if "source" in metadata and not source_name:
                    source_name = metadata["source"]
                if source_name and not source_name.startswith("repo_"):
                    source_name = f"repo_{source_name}"
                    metadata["source"] = source_name
                if "timestamp" not in metadata:
                    metadata["timestamp"] = datetime.now().isoformat()
                if "chunk_number" not in metadata:
                    metadata["chunk_number"] = i + initial_count
                db_service.insert_record(
                    table_name="repo_content",
                    data={
                        "content": content,
                        "metadata": metadata,
                        "embedding": embedding,
                        "repo_url": repo_url or metadata.get("repo_url", ""),
                        "file_path": metadata.get("file_path", ""),
                        "branch": metadata.get("branch")
                        or os.getenv("CURRENT_SOURCE_BRANCH", "main"),
                        "title": metadata.get(
                            "title",
                            metadata.get("file_path", "unknown file").split("/")[-1],
                        ),
                        "summary": metadata.get(
                            "summary",
                            f"Content from {metadata.get('file_path', 'unknown file')}",
                        ),
                        "embedding_model": metadata.get("embedding_model", "nomic-embed-text"),
                        "chunk_number": metadata.get("chunk_number", i + initial_count),
                    },
                )
                stored_count += 1
            except Exception as chunk_error:
                logger.error(f"Error storing chunk {i+1}: {chunk_error}")
        storage_locations = ["repo_content"]
        logger.debug(f"Stored {stored_count} chunks with source: {source_name or 'unknown'}")
        return {
            "status": "success",
            "chunks_stored": stored_count,
            "processed_files": len(processed_chunks),
            "source_name": source_name,
            "storage_locations": storage_locations,
            "message": f"Successfully stored {stored_count} chunks in repo_content table",
        }
    except Exception as e:
        logger.error(f"Error storing chunks in database: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to store chunks in database: {str(e)}",
        }
