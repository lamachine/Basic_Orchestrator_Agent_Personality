import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
from supabase import Client, create_client

from src.managers.db_manager import DBService
from src.services.logging_service import get_logger
from src.utils.datetime_utils import format_datetime, now, parse_datetime, timestamp

logger = get_logger(__name__)


class DatabaseAdvancedSearchService:
    """
    Service for advanced database search operations, such as semantic and graph search.
    Uses DBService for all database access.
    """

    def __init__(self, db_service: DBService):
        """
        Initialize the advanced search service.

        Args:
            db_service (DBService): The database service instance to use for DB operations.
        """
        self.db_service = db_service

    async def semantic_message_search(
        self,
        query_text: str,
        embedding: List[float],
        user_id: str = "developer",
        match_count: int = 5,
        match_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Search for messages semantically similar to the query.

        This combines vector search with filtering by user_id to find
        semantically relevant messages for a specific user.

        Args:
            query_text: Text query for fallback text search
            embedding: Query embedding vector
            user_id: User identifier to filter results
            match_count: Maximum number of matches to return
            match_threshold: Similarity threshold (0-1)

        Returns:
            List of matching messages with similarity scores
        """
        return await self.db_service.semantic_message_search(
            query_text=query_text,
            embedding=embedding,
            user_id=user_id,
            match_count=match_count,
            match_threshold=match_threshold,
        )

    async def graph_search(
        self,
        node_id: str,
        relationship_table: str,
        source_column: str = "source_id",
        target_column: str = "target_id",
        depth: int = 1,
        relationship_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Perform a graph search for related nodes.
        """
        return await self.db_service.graph_search(
            node_id=node_id,
            relationship_table=relationship_table,
            source_column=source_column,
            target_column=target_column,
            depth=depth,
            relationship_type=relationship_type,
            limit=limit,
        )
