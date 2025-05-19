"""
Utility package for template agent.

This package provides various utility functions and classes used throughout the template agent.
"""

from .datetime_utils import DateTimeUtils
from .db_verification import monitor_status, track_changes, verify_data_storage
from .embedding_utils import EmbeddingManager
from .github_adapter import (
    store_chunks_in_db,
    sync_download_repo,
    sync_get_file_content,
    sync_get_repo_structure,
    sync_process_and_store_document,
)
from .logging_utils import get_logger, setup_logging
from .text_processing import TextProcessor

__all__ = [
    # Core utilities
    "EmbeddingManager",
    "TextProcessor",
    "DateTimeUtils",
    "get_logger",
    "setup_logging",
    # GitHub utilities
    "sync_get_repo_structure",
    "sync_get_file_content",
    "sync_process_and_store_document",
    "sync_download_repo",
    "store_chunks_in_db",
    # Database verification utilities
    "verify_data_storage",
    "track_changes",
    "monitor_status",
]
