"""
Database Verification Utilities

This module provides functions to verify data storage in the database
across different tools and data types.
"""

import logging
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Import database manager
from src.services.db_services.db_manager import DatabaseManager

# Storage verification tracking
_verification_trackers = {}

def verify_storage(
    source_name: str, 
    table_name: str = 'repo_content', 
    metadata_field: str = 'source',
    required_count: int = 1
) -> Dict[str, Any]:
    """
    Verify that data is properly stored in the database.
    
    Args:
        source_name: Identifier for the data source (e.g., "repo_fastapi")
        table_name: Name of the table to check (default: repo_content)
        metadata_field: Field in metadata to match against source_name
        required_count: Minimum number of entries required for verification to succeed
        
    Returns:
        Dictionary with verification results
    """
    # Initialize tracker for this source if not exists
    if source_name not in _verification_trackers:
        _verification_trackers[source_name] = {
            "last_count": 0,
            "verified_ids": []
        }
    
    tracker = _verification_trackers[source_name]
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Query the table for entries with this source name
        try:
            # Direct Supabase query to find entries for this source
            logger.debug(f"Checking {table_name} table for source: {source_name}")
            response = db_manager.supabase.table(table_name) \
                .select('id, metadata') \
                .filter(f'metadata->>{metadata_field}', 'eq', source_name) \
                .execute()
            results = response.data if hasattr(response, 'data') else []
            
            # Extract count information
            current_count = len(results)
            
            # Get IDs for tracking
            current_ids = [item['id'] for item in results]
            new_items = [id for id in current_ids if id not in tracker["verified_ids"]]
            tracker["verified_ids"] = current_ids  # Update our tracking list
            
            # Log detailed information about what we found
            logger.debug(f"Database check found {current_count} items for {source_name} in {table_name}")
            if current_count > 0 and len(results) > 0:
                logger.debug(f"Sample item - ID: {results[0].get('id')}")
                logger.debug(f"Metadata sample: {str(results[0].get('metadata', {}))[:200]}...")
            
            # Check if count has increased since last check
            new_count = current_count - tracker["last_count"]
            tracker["last_count"] = current_count
            
            logger.debug(f"Database verification: Found {current_count} total items for {source_name} in {table_name}")
            logger.debug(f"New items since last check: {new_count}")
            
            # Verification is successful if we have at least the required number of items
            verification_success = current_count >= required_count
            
            return {
                "status": "success",
                "source": source_name,
                "table": table_name,
                "total_items": current_count,
                "new_items": new_count,
                "verification_result": verification_success,
                "reason": None if verification_success else f"Expected at least {required_count} items, found {current_count}"
            }
        except Exception as e:
            logger.error(f"Database query error for {source_name}: {e}")
            return {
                "status": "error",
                "source": source_name,
                "table": table_name,
                "error": str(e),
                "verification_result": False,
                "reason": f"Query failed: {str(e)}"
            }
    except Exception as e:
        logger.error(f"Database verification error: {e}")
        return {
            "status": "error",
            "source": source_name,
            "error": str(e),
            "verification_result": False,
            "reason": f"Database error: {str(e)}"
        }

def reset_verification_tracker(source_name: Optional[str] = None) -> None:
    """
    Reset the verification tracker for a specific source or all sources.
    
    Args:
        source_name: Name of the source to reset, or None to reset all
    """
    global _verification_trackers
    
    if source_name is None:
        _verification_trackers = {}
        logger.debug("Reset all verification trackers")
    elif source_name in _verification_trackers:
        del _verification_trackers[source_name]
        logger.debug(f"Reset verification tracker for {source_name}")
    else:
        logger.debug(f"No verification tracker found for {source_name}")

def get_verification_status(source_name: str) -> Dict[str, Any]:
    """
    Get the current verification status for a source.
    
    Args:
        source_name: Name of the source to check
        
    Returns:
        Dictionary with current tracking status
    """
    if source_name not in _verification_trackers:
        return {
            "source": source_name,
            "last_count": 0,
            "tracked_ids": 0,
            "initialized": False
        }
        
    tracker = _verification_trackers[source_name]
    return {
        "source": source_name,
        "last_count": tracker["last_count"],
        "tracked_ids": len(tracker["verified_ids"]),
        "initialized": True
    } 