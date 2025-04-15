"""Tool for scraping Git repositories for codebase analysis and knowledge capture."""

import logging
import time
import os
from typing import Dict, Any, Optional
from datetime import datetime
import threading
import random
import re
import json
import uuid

# Import the github adapter for synchronous operations
from src.utils.github_adapter import sync_download_repo

# Setup logging
logger = logging.getLogger(__name__)

# Ensure only important messages go to the console
# Debug messages will still be written to log files based on file_level
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
        handler.setLevel(logging.INFO)

# Track pending scrape repository requests - simulate asynchronous operation
PENDING_SCRAPE_REPO_REQUESTS = {}

def _process_repo_scrape(repo_url: str, request_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Process the repository scraping asynchronously.
    
    Args:
        repo_url: The URL of the repository to scrape
        request_id: Optional request ID for tracking
        
    Returns:
        Dict with the scraping response
    """
    try:
        logger.debug(f"Starting repository scrape for {repo_url} (request_id: {request_id})")
        
        # Extract repo name and owner from URL
        parts = repo_url.strip("/").split("/")
        repo_name = parts[-1]
        repo_owner = parts[-2] if len(parts) > 2 else "unknown"
        
        # Log scraping progress
        logger.debug(f"Cloning repository: {repo_url}")
        logger.debug(f"Analyzing code structure...")
        logger.debug(f"Extracting file statistics...")
        logger.debug(f"Building repository knowledge graph...")
        
        # Set required environment variables for the crawler
        os.environ["CURRENT_SOURCE_NAME"] = f"repo_{repo_name}"
        os.environ["CURRENT_SOURCE_OWNER"] = repo_owner
        os.environ["CURRENT_SOURCE_BASE_URL"] = repo_url
        os.environ["CONTENT_TYPE"] = "repo"
        os.environ["CURRENT_SOURCE_BRANCH"] = "main"  # Default to main branch
        os.environ["CURRENT_SOURCE_TABLE"] = "repo_content"  # Explicitly set table name
        
        # Import verification utilities
        from src.utils.db_verification import verify_storage, reset_verification_tracker
        
        # Reset any existing tracking data for this repo
        source_name = f"repo_{repo_name}"
        reset_verification_tracker(source_name)
        
        # Configure the crawler to verify after processing batches of entries
        # This eliminates the need for sleep delays after processing
        os.environ["VERIFY_AFTER_COUNT"] = "20"  # Verify after every 20 entries
        
        # Call the adapted crawler through the sync adapter
        logger.debug(f"Starting download and processing of {repo_url} with batch verification")
        result = sync_download_repo(repo_url)
        logger.debug(f"Completed download and processing of {repo_url}")
        
        # After processing is complete, do a final verification check
        logger.debug(f"Performing final verification of database storage for {source_name}")
        verification = verify_storage(
            source_name=source_name, 
            table_name='repo_content', 
            metadata_field='source',
            required_count=20  # Require at least 20 entries to be considered successful
        )
        
        storage_ok = verification["verification_result"]
        
        # Check verification results
        if not storage_ok:
            reason = verification.get("reason", "No data found")
            logger.warning(f"FINAL STORAGE VERIFICATION FAILED: {reason}")
            
            # Clean up any stored but unverified data
            logger.warning(f"Attempting to clean up any partially stored data for {source_name}")
            try:
                # Initialize database manager
                from src.services.db_services.db_manager import DatabaseManager
                db_manager = DatabaseManager()
                
                # Delete records from repo_content table with this source name
                response = db_manager.supabase.table('repo_content') \
                    .delete() \
                    .filter('metadata->>source', 'eq', source_name) \
                    .execute()
                
                deleted_count = len(response.data) if hasattr(response, 'data') else 0
                logger.debug(f"Cleaned up {deleted_count} records for {source_name} due to verification failure")
                
                # Return failure result
                return {
                    "status": "error",
                    "request_id": request_id,
                    "message": f"Repository {repo_name} scrape failed: Final verification failed",
                    "error": "Verification failed after processing",
                    "reason": reason,
                    "cleanup": f"Removed {deleted_count} unverified records"
                }
                
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup after verification failure: {cleanup_error}")
                return {
                    "status": "error",
                    "request_id": request_id,
                    "message": f"Repository {repo_name} scrape failed: Final verification failed and cleanup failed",
                    "error": str(cleanup_error),
                    "reason": reason
                }
        else:
            logger.debug(f"FINAL STORAGE VERIFICATION PASSED: Repository data successfully stored in database")
            verification_count = verification.get("total_items", 0)
            result["storage_verification"] = "success"
            result["verified_count"] = verification_count
        
        logger.debug(f"Repository scrape completed for {repo_url}")
        return {
            "status": "success",
            "request_id": request_id,
            "message": f"Repository {repo_name} successfully scraped and analyzed",
            "data": result,
            "storage_status": "verified" if storage_ok else "not_verified"
        }
    except Exception as e:
        logger.error(f"Error processing repository scrape: {e}")
        return {
            "status": "error",
            "request_id": request_id,
            "message": f"Failed to scrape repository: {str(e)}"
        }

def scrape_repo_tool(task: Optional[str] = None, request_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Scrape a Git repository for analysis.
    
    Args:
        task: Description of the scraping task, typically containing the repository URL
        request_id: Optional request ID for tracking
        
    Returns:
        Dict with status and response message
    """
    logger.debug(f"Received repository scrape task: {task}")
    
    if not task:
        return {
            "status": "error",
            "request_id": request_id,
            "message": "No repository URL provided. Please specify a repository to scrape."
        }
    
    # Extract repository URL from task description
    # This is a simple extraction - could be improved with regex or NLP
    repo_url = None
    
    # Look for common git repo URL patterns in the task
    if "github.com" in task:
        parts = task.split("github.com/")
        if len(parts) > 1:
            potential_url = "github.com/" + parts[1].split(" ")[0]
            repo_url = "https://" + potential_url
    elif "gitlab.com" in task:
        parts = task.split("gitlab.com/")
        if len(parts) > 1:
            potential_url = "gitlab.com/" + parts[1].split(" ")[0]
            repo_url = "https://" + potential_url
    
    # If URL wasn't found, try simpler extraction
    if not repo_url:
        words = task.split()
        for word in words:
            if word.startswith(("http://", "https://", "git@")):
                repo_url = word.strip(",.;:")
                break
    
    # Fall back to assuming the task itself might be just the URL
    if not repo_url and ("http://" in task or "https://" in task):
        repo_url = task.strip()
    
    if not repo_url:
        return {
            "status": "error",
            "request_id": request_id,
            "message": "Could not identify a valid repository URL in your request. Please provide a GitHub or GitLab URL."
        }
    
    # Create a thread to process the request asynchronously
    def process_thread():
        try:
            result = _process_repo_scrape(repo_url, request_id)
            PENDING_SCRAPE_REPO_REQUESTS[request_id] = result
        except Exception as e:
            logger.error(f"Error in repository scrape thread: {e}")
            PENDING_SCRAPE_REPO_REQUESTS[request_id] = {
                "status": "error",
                "request_id": request_id,
                "message": f"Error scraping repository: {str(e)}"
            }
    
    # Start the processing thread
    thread = threading.Thread(target=process_thread)
    thread.daemon = True
    thread.start()
    
    # Return initial pending response
    return {
        "status": "pending",
        "request_id": request_id,
        "message": f"Repository scrape initiated for {repo_url}. This will take approximately 1-3 minutes to complete depending on repository size."
    } 