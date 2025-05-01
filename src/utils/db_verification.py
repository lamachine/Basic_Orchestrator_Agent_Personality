"""
Database Verification Utilities

Functions to verify data storage in the database across tools and data types.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
from src.managers.db_manager import DatabaseManager

_verification_trackers = {}

def verify_storage(
    source_name: str, 
    table_name: str = 'repo_content', 
    metadata_field: str = 'source',
    required_count: int = 1
) -> Dict[str, Any]:
    """Verify that data is properly stored in the database."""
    if source_name not in _verification_trackers:
        _verification_trackers[source_name] = {
            "last_count": 0,
            "verified_ids": []
        }
    tracker = _verification_trackers[source_name]
    try:
        db_manager = DatabaseManager()
        try:
            response = db_manager.supabase.table(table_name) \
                .select('id, metadata') \
                .filter(f'metadata->>{metadata_field}', 'eq', source_name) \
                .execute()
            results = response.data if hasattr(response, 'data') else []
            current_count = len(results)
            current_ids = [item['id'] for item in results]
            new_items = [id for id in current_ids if id not in tracker["verified_ids"]]
            tracker["verified_ids"] = current_ids
            new_count = current_count - tracker["last_count"]
            tracker["last_count"] = current_count
            verification_success = current_count >= required_count
            logger.debug(f"Verification for {source_name} in {table_name}: {current_count} items, new: {new_count}")
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
    """Reset the verification tracker for a specific source or all sources."""
    global _verification_trackers
    if source_name is None:
        _verification_trackers = {}
        logger.debug("Reset all verification trackers")
    elif source_name in _verification_trackers:
        del _verification_trackers[source_name]
        logger.debug(f"Reset verification tracker for {source_name}")

def get_verification_status(source_name: str) -> Dict[str, Any]:
    """Get the current verification status for a source."""
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