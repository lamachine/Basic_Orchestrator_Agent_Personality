import os
from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client

from src.services.logging_service import get_logger

# Initialize logger
logger = get_logger(__name__)


# Initialize database service
class DBService:
    """Service for interacting with the database."""

    def __init__(self):
        """Initialize the database service."""
        url = os.getenv("SUPABASE_URL")  # Preferred: url
        anon_key = os.getenv("SUPABASE_ANON_KEY")  # Preferred: anon_key
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Preferred: service_role_key
        if not (url and service_role_key):
            raise ValueError("url and service_role_key must be set")

        self.client: Client = create_client(url, service_role_key)
        self.message_manager = None  # Will be set in main.py

    async def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a record into a table.
        Args:
            table_name: Name of the table
            data: Record data
        Returns:
            Inserted record data
        Raises:
            RuntimeError: If insert fails
        """
        try:
            response = self.client.table(table_name).insert(data).execute()
            if not response.data:
                raise RuntimeError(f"Insert operation returned no data")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error inserting record into {table_name}: {e}")
            raise RuntimeError(f"Error inserting record into {table_name}: {e}")

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
        Select records from a table with optional filtering.
        Args:
            table_name: Name of the table
            columns: Columns to select
            filters: Optional dictionary of filter conditions
            order_by: Optional column to order by
            order_desc: Whether to order in descending order
            limit: Maximum number of records to return
        Returns:
            List of records
        Raises:
            RuntimeError: If select fails
        """
        try:
            query = self.client.table(table_name).select(columns)
            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)
            if order_by:
                query = query.order(order_by, desc=order_desc)
            if limit:
                query = query.limit(limit)
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error selecting records from {table_name}: {e}")
            raise RuntimeError(f"Error selecting records from {table_name}: {e}")

    async def update(
        self,
        table_name: str,
        record_id: Union[int, str],
        data: Dict[str, Any],
        id_column: str = "id",
    ) -> Dict[str, Any]:
        """
        Update a record in a table.
        Args:
            table_name: Name of the table
            record_id: ID of the record to update
            data: Updated data
            id_column: Name of the ID column
        Returns:
            Updated record data
        Raises:
            RuntimeError: If update fails
        """
        try:
            response = self.client.table(table_name).update(data).eq(id_column, record_id).execute()
            if not response.data:
                raise RuntimeError(f"Update operation returned no data")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error updating record {record_id} in {table_name}: {e}")
            raise RuntimeError(f"Error updating record {record_id} in {table_name}: {e}")

    async def delete(self, table_name: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Delete records from a table.
        Args:
            table_name: Name of the table
            filters: Filter conditions (column/value pairs)
        Returns:
            List of deleted records
        Raises:
            RuntimeError: If delete fails
        """
        try:
            query = self.client.table(table_name).delete()
            for column, value in filters.items():
                query = query.eq(column, value)
            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error deleting records from {table_name}: {e}")
            raise RuntimeError(f"Error deleting records from {table_name}: {e}")
