"""
Database Verification Utilities

This module provides utilities for verifying database operations and state.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..services.db_service import DBService
from ..utils.logging_utils import get_logger

logger = get_logger(__name__)

_verification_trackers = {}


def verify_storage(
    db_service: DBService,
    source_name: str,
    table_name: str = "repo_content",
    metadata_field: str = "source",
    required_count: int = 1,
) -> Dict[str, Any]:
    """
    Verify that data is properly stored in the database.

    Args:
        db_service: DBService instance
        source_name: Name of the source to verify
        table_name: Name of the table to check
        metadata_field: Field in metadata to match against
        required_count: Minimum number of records required

    Returns:
        Dict with verification results
    """
    if source_name not in _verification_trackers:
        _verification_trackers[source_name] = {"last_count": 0, "verified_ids": []}
    tracker = _verification_trackers[source_name]
    try:
        try:
            response = db_service.select_records(
                table_name=table_name,
                filters={f"metadata->{metadata_field}": source_name},
            )
            results = response if isinstance(response, list) else []
            current_count = len(results)
            current_ids = [item["id"] for item in results]
            new_items = [id for id in current_ids if id not in tracker["verified_ids"]]
            tracker["verified_ids"] = current_ids
            new_count = current_count - tracker["last_count"]
            tracker["last_count"] = current_count
            verification_success = current_count >= required_count
            logger.debug(
                f"Verification for {source_name} in {table_name}: {current_count} items, new: {new_count}"
            )
            return {
                "status": "success",
                "source": source_name,
                "table": table_name,
                "total_items": current_count,
                "new_items": new_count,
                "verification_result": verification_success,
                "reason": (
                    None
                    if verification_success
                    else f"Expected at least {required_count} items, found {current_count}"
                ),
            }
        except Exception as e:
            logger.error(f"Database query error for {source_name}: {e}")
            return {
                "status": "error",
                "source": source_name,
                "table": table_name,
                "error": str(e),
                "verification_result": False,
                "reason": f"Query failed: {str(e)}",
            }
    except Exception as e:
        logger.error(f"Database verification error: {e}")
        return {
            "status": "error",
            "source": source_name,
            "error": str(e),
            "verification_result": False,
            "reason": f"Database error: {str(e)}",
        }


def reset_verification_tracker(source_name: Optional[str] = None) -> None:
    """
    Reset the verification tracker for a specific source or all sources.

    Args:
        source_name: Optional source name to reset. If None, resets all trackers.
    """
    global _verification_trackers
    if source_name is None:
        _verification_trackers = {}
        logger.debug("Reset all verification trackers")
    elif source_name in _verification_trackers:
        del _verification_trackers[source_name]
        logger.debug(f"Reset verification tracker for {source_name}")


def get_verification_status(source_name: str) -> Dict[str, Any]:
    """
    Get the current verification status for a source.

    Args:
        source_name: Name of the source to check

    Returns:
        Dict with verification status
    """
    if source_name not in _verification_trackers:
        return {
            "source": source_name,
            "last_count": 0,
            "tracked_ids": 0,
            "initialized": False,
        }
    tracker = _verification_trackers[source_name]
    return {
        "source": source_name,
        "last_count": tracker["last_count"],
        "tracked_ids": len(tracker["verified_ids"]),
        "initialized": True,
    }


async def verify_db_connection(db_service: DBService, timeout: int = 30) -> Dict[str, Any]:
    """
    Verify database connection and basic operations.

    Args:
        db_service: DBService instance
        timeout: Connection timeout in seconds

    Returns:
        Dict containing verification results
    """
