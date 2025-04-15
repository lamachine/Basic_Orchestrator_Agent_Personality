"""Tool for scraping web pages and websites for knowledge capture."""

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
from urllib.parse import urlparse

# Import the web crawler adapter for synchronous operations
from src.tools.crawler.other_unmapped.generic_crawler import GenericCrawler

# Setup logging
logger = logging.getLogger(__name__)

# Ensure only important messages go to the console
# Debug messages will still be written to log files based on file_level
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
        handler.setLevel(logging.INFO)

# Track pending web scrape requests - simulate asynchronous operation
PENDING_WEB_SCRAPE_REQUESTS = {}

# Update the table name constant
DEFAULT_TABLE = "full_site_pages"

def _process_web_scrape(start_url: str, request_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Process the web scraping asynchronously.
    
    Args:
        start_url: The starting URL to scrape
        request_id: Optional request ID for tracking
        
    Returns:
        Dict with the scraping response
    """
    try:
        logger.debug(f"Starting web scrape for {start_url} (request_id: {request_id})")
        
        # Extract domain and create source name
        parsed_url = urlparse(start_url)
        domain = parsed_url.netloc
        source_name = f"web_{domain.replace('.', '_')}"
        
        # Log scraping progress
        logger.debug(f"Initializing crawler for: {start_url}")
        logger.debug(f"Domain: {domain}")
        logger.debug(f"Source name: {source_name}")
        
        # Set required environment variables for the crawler
        os.environ["CURRENT_SOURCE"] = start_url
        os.environ["CURRENT_SOURCE_NAME"] = source_name
        os.environ["CURRENT_SOURCE_OWNER"] = domain
        os.environ["CONTENT_TYPE"] = "webpage"
        os.environ["CURRENT_SOURCE_TABLE"] = DEFAULT_TABLE  # Use the correct table name
        
        # Import verification utilities
        from src.utils.db_verification import verify_storage, reset_verification_tracker
        
        # Reset any existing tracking data for this source
        reset_verification_tracker(source_name)
        
        # Configure the crawler to verify after processing batches of entries
        os.environ["VERIFY_AFTER_COUNT"] = "10"  # Verify after every 10 entries
        
        # Initialize and run the crawler
        logger.debug(f"Starting crawl and processing of {start_url} with batch verification")
        
        # Create and configure crawler instance
        crawler = GenericCrawler(
            start_url=start_url,
            max_pages=int(os.getenv("MAX_PAGES", "50")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "5000")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            delay_between_requests=float(os.getenv("DELAY_BETWEEN_REQUESTS", "0.5"))
        )
        
        # Run the crawler synchronously (it handles its own async operations internally)
        import asyncio
        result = asyncio.run(crawler.crawl())
        logger.debug(f"Completed crawl and processing of {start_url}")
        
        # After processing is complete, do a final verification check
        logger.debug(f"Performing final verification of database storage for {source_name}")
        verification = verify_storage(
            source_name=source_name,
            table_name=DEFAULT_TABLE,
            metadata_field='source',
            required_count=5  # Require at least 5 entries to be considered successful
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
                
                # Delete records from the correct table with this source name
                response = db_manager.supabase.table(DEFAULT_TABLE) \
                    .delete() \
                    .filter('metadata->>source', 'eq', source_name) \
                    .execute()
                
                deleted_count = len(response.data) if hasattr(response, 'data') else 0
                logger.debug(f"Cleaned up {deleted_count} records for {source_name} due to verification failure")
                
                # Return failure result
                return {
                    "status": "error",
                    "request_id": request_id,
                    "message": f"Website {domain} scrape failed: Final verification failed",
                    "error": "Verification failed after processing",
                    "reason": reason,
                    "cleanup": f"Removed {deleted_count} unverified records"
                }
                
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup after verification failure: {cleanup_error}")
                return {
                    "status": "error",
                    "request_id": request_id,
                    "message": f"Website {domain} scrape failed: Final verification failed and cleanup failed",
                    "error": str(cleanup_error),
                    "reason": reason
                }
        else:
            logger.debug(f"FINAL STORAGE VERIFICATION PASSED: Website data successfully stored in database")
            verification_count = verification.get("total_items", 0)
            result["storage_verification"] = "success"
            result["verified_count"] = verification_count
        
        logger.debug(f"Web scrape completed for {start_url}")
        return {
            "status": "success",
            "request_id": request_id,
            "message": f"Website {domain} successfully scraped and analyzed",
            "data": result,
            "storage_status": "verified" if storage_ok else "not_verified"
        }
    except Exception as e:
        logger.error(f"Error processing web scrape: {e}")
        return {
            "status": "error",
            "request_id": request_id,
            "message": f"Failed to scrape website: {str(e)}"
        }

def scrape_web_tool(task: Optional[str] = None, request_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Scrape a website or web page for analysis.
    
    Args:
        task: Description of the scraping task, typically containing the website URL
        request_id: Optional request ID for tracking
        
    Returns:
        Dict with status and response message
    """
    logger.debug(f"Received web scrape task: {task}")
    
    if not task:
        return {
            "status": "error",
            "request_id": request_id,
            "message": "No website URL provided. Please specify a website to scrape."
        }
    
    # Extract website URL from task description
    url = None
    
    # Look for URLs in the task description
    words = task.split()
    for word in words:
        if word.startswith(("http://", "https://")):
            url = word.strip(",.;:")
            break
    
    # Fall back to assuming the task itself might be just the URL
    if not url and ("http://" in task or "https://" in task):
        url = task.strip()
    
    if not url:
        return {
            "status": "error",
            "request_id": request_id,
            "message": "Could not identify a valid website URL in your request. Please provide a URL starting with http:// or https://"
        }
    
    # Create a thread to process the request asynchronously
    def process_thread():
        try:
            result = _process_web_scrape(url, request_id)
            PENDING_WEB_SCRAPE_REQUESTS[request_id] = result
        except Exception as e:
            logger.error(f"Error in web scrape thread: {e}")
            PENDING_WEB_SCRAPE_REQUESTS[request_id] = {
                "status": "error",
                "request_id": request_id,
                "message": f"Error scraping website: {str(e)}"
            }
    
    # Start the processing thread
    thread = threading.Thread(target=process_thread)
    thread.daemon = True
    thread.start()
    
    # Return initial pending response
    return {
        "status": "pending",
        "request_id": request_id,
        "message": f"Web scrape initiated for {url}. This will take approximately 1-3 minutes to complete depending on website size."
    } 