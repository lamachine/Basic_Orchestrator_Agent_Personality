"""
Database Service Module

This module implements database operations as a service layer. It provides:
1. Basic CRUD operations
2. Message-specific operations
3. Search functionality
4. Connection management
5. State tracking
6. Vector search support
7. Health monitoring
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client

from ..config.service_config import DBServiceConfig
from ..state.state_models import Message, MessageStatus, MessageType
from ..utils.logging_utils import get_logger

logger = get_logger(__name__)


class DBService:
    """
    Service for database operations.

    This class provides methods for:
    1. Basic CRUD operations (insert, select, update, delete)
    2. Message-specific operations
    3. Search functionality
    4. Connection management
    5. State tracking
    6. Vector search support
    7. Health monitoring
    """

    def __init__(self, config: DBServiceConfig, client: Optional[Client] = None):
        """
        Initialize the database service.

        Args:
            config: Database service configuration
            client: Optional Supabase client (for testing)
        """
        try:
            self.config = config

            # Get Supabase credentials from config
            supabase_url = config.get_merged_config().get("supabase_url")
            supabase_key = config.get_merged_config().get("supabase_key")

            if not supabase_url or not supabase_key:
                raise ValueError("Missing Supabase credentials in config")

            # Initialize Supabase client
            self.client: Client = client or create_client(supabase_url, supabase_key)

            # Initialize state tracking
            self._connected = True
            self._last_query = datetime.now()
            self._query_count = 0
            self._error_count = 0

            logger.debug("Database service initialized successfully")

        except Exception as e:
            self._connected = False
            self._error_count += 1
            logger.error(f"Error initializing database service: {e}")
            raise

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected

    @property
    def last_query_time(self) -> datetime:
        """Get time of last query."""
        return self._last_query

    @property
    def query_count(self) -> int:
        """Get total number of queries executed."""
        return self._query_count

    @property
    def error_count(self) -> int:
        """Get total number of errors encountered."""
        return self._error_count

    async def get_next_id(self, column_name: str, table_name: str) -> int:
        """
        Get next available ID for a column.

        Args:
            column_name: Name of the ID column
            table_name: Name of the table

        Returns:
            Next available ID (max + 1)

        Raises:
            RuntimeError: If operation fails
        """
        try:
            response = self.client.from_(table_name).select(column_name).execute()

            max_val = 0
            if response.data:
                for item in response.data:
                    val = item.get(column_name, 0)
                    if val is None:
                        continue
                    if isinstance(val, str) and val.isdigit():
                        val = int(val)
                    if isinstance(val, int) and val > max_val:
                        max_val = val

            self._query_count += 1
            self._last_query = datetime.now()
            return max_val + 1

        except Exception as e:
            self._error_count += 1
            error_msg = f"Error getting next ID for {table_name}.{column_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a record into a table.

        Args:
            table_name: Name of the table
            data: Record data to insert

        Returns:
            The inserted record
        """
        try:
            response = self.client.table(table_name).insert(data).execute()
            self._query_count += 1
            self._last_query = datetime.now()
            return response.data[0] if response.data else {}
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error inserting into {table_name}: {e}")
            raise

    async def select(
        self,
        table_name: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Select records from a table.

        Args:
            table_name: Name of the table
            columns: Columns to select (default: all)
            filters: Optional filters to apply
            order_by: Optional column to order by
            order_desc: Whether to order descending
            limit: Optional limit on number of records

        Returns:
            List of matching records
        """
        try:
            query = self.client.table(table_name).select(columns)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            # Apply ordering
            if order_by:
                query = query.order(order_by, desc=order_desc)

            # Apply limit
            if limit:
                query = query.limit(limit)

            response = query.execute()
            self._query_count += 1
            self._last_query = datetime.now()
            return response.data

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error selecting from {table_name}: {e}")
            raise

    async def update(
        self, table_name: str, data: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Update records in a table.

        Args:
            table_name: Name of the table
            data: Data to update
            filters: Filters to select records to update

        Returns:
            List of updated records
        """
        try:
            query = self.client.table(table_name)

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.update(data).execute()
            self._query_count += 1
            self._last_query = datetime.now()
            return response.data

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error updating {table_name}: {e}")
            raise

    async def delete_records(
        self, table_name: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Delete records from a table.

        Args:
            table_name: Name of the table
            filters: Filters to select records to delete

        Returns:
            List of deleted records
        """
        try:
            query = self.client.table(table_name)

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.delete().execute()
            self._query_count += 1
            self._last_query = datetime.now()
            return response.data

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error deleting from {table_name}: {e}")
            raise

    async def get_messages(
        self, session_id: Union[str, int], user_id: str = "developer"
    ) -> List[Message]:
        """
        Get messages for a session.

        Args:
            session_id: Session ID
            user_id: User ID (default: developer)

        Returns:
            List of messages
        """
        try:
            response = await self.select(
                "messages",
                filters={"session_id": session_id, "user_id": user_id},
                order_by="created_at",
            )

            # Convert to Message objects
            messages = []
            for msg in response:
                messages.append(
                    Message(
                        id=msg["id"],
                        type=MessageType(msg["type"]),
                        content=msg["content"],
                        status=MessageStatus(msg["status"]),
                        metadata=msg.get("metadata", {}),
                        created_at=msg["created_at"],
                        updated_at=msg["updated_at"],
                    )
                )

            return messages

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error getting messages: {e}")
            raise

    async def search_messages(
        self,
        query: str,
        session_id: Optional[Union[str, int]] = None,
        user_id: str = "developer",
    ) -> List[Message]:
        """
        Search messages by content.

        Args:
            query: Search query
            session_id: Optional session ID
            user_id: User ID (default: developer)

        Returns:
            List of matching messages
        """
        try:
            # Build query
            filters = {"user_id": user_id}
            if session_id:
                filters["session_id"] = session_id

            response = await self.select("messages", filters=filters, order_by="created_at")

            # Filter by content
            matches = []
            for msg in response:
                if query.lower() in msg["content"].lower():
                    matches.append(
                        Message(
                            id=msg["id"],
                            type=MessageType(msg["type"]),
                            content=msg["content"],
                            status=MessageStatus(msg["status"]),
                            metadata=msg.get("metadata", {}),
                            created_at=msg["created_at"],
                            updated_at=msg["updated_at"],
                        )
                    )

            return matches

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error searching messages: {e}")
            raise

    async def semantic_message_search(
        self, query: str, embedding: List[float], limit: int = 5
    ) -> List[Message]:
        """
        Search messages using semantic similarity.

        Args:
            query: Search query
            embedding: Query embedding
            limit: Maximum number of results

        Returns:
            List of similar messages
        """
        try:
            # Use vector search
            response = await self.vector_search("messages", embedding, "embedding", limit)

            # Convert to Message objects
            messages = []
            for msg in response:
                messages.append(
                    Message(
                        id=msg["id"],
                        type=MessageType(msg["type"]),
                        content=msg["content"],
                        status=MessageStatus(msg["status"]),
                        metadata=msg.get("metadata", {}),
                        created_at=msg["created_at"],
                        updated_at=msg["updated_at"],
                    )
                )

            return messages

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error in semantic message search: {e}")
            raise

    async def vector_search(
        self,
        table_name: str,
        embedding: List[float],
        embedding_column: str = "embedding_nomic",
        match_count: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search using vector similarity.

        Args:
            table_name: Name of the table
            embedding: Query embedding
            embedding_column: Name of embedding column
            match_count: Number of matches to return
            filters: Optional filters to apply

        Returns:
            List of similar records
        """
        try:
            # Build query
            query = self.client.rpc(
                "match_documents",
                {
                    "query_embedding": embedding,
                    "match_count": match_count,
                    "filter": filters,
                },
            )

            response = query.execute()
            self._query_count += 1
            self._last_query = datetime.now()
            return response.data

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error in vector search: {e}")
            raise

    async def graph_search(
        self, node_id: str, relationship_type: Optional[str] = None, depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Search graph relationships.

        Args:
            node_id: ID of starting node
            relationship_type: Optional relationship type
            depth: Search depth

        Returns:
            List of related nodes
        """
        try:
            # Build query
            query = self.client.rpc(
                "graph_search",
                {"start_id": node_id, "rel_type": relationship_type, "depth": depth},
            )

            response = query.execute()
            self._query_count += 1
            self._last_query = datetime.now()
            return response.data

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error in graph search: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Check database health.

        Returns:
            Health status information
        """
        try:
            # Check connection
            response = self.client.from_("health_check").select("1").limit(1).execute()

            return {
                "connected": self._connected,
                "last_query": self._last_query.isoformat(),
                "query_count": self._query_count,
                "error_count": self._error_count,
                "status": "healthy" if response.data else "unhealthy",
            }

        except Exception as e:
            self._error_count += 1
            logger.error(f"Error in health check: {e}")
            return {
                "connected": self._connected,
                "last_query": self._last_query.isoformat(),
                "query_count": self._query_count,
                "error_count": self._error_count,
                "status": "unhealthy",
                "error": str(e),
            }
