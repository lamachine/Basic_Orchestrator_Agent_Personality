import os
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client, Client

from src.services.logging_service import get_logger
from src.utils.datetime_utils import format_datetime, parse_datetime, now, timestamp
from src.managers.db_manager import DBService
logger = get_logger(__name__)

class DatabaseRecordService:

    
    def __init__(self, db_service: DBService):
        """
        Initialize database service.
        
        Args:
            url: Optional Supabase URL
            key: Optional Supabase key
            
        Raises:
            ValueError: If Supabase credentials are missing
        """
        self.db_service = db_service
        

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
            response = self.supabase.from_(table_name).select(column_name).execute()
            
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
            
            return max_val + 1
            
        except Exception as e:
            error_msg = f"Error getting next ID for {table_name}.{column_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
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
            response = self.supabase.table(table_name).insert(data).execute()
            
            if not response.data:
                raise RuntimeError(f"Insert operation returned no data")
                
            return response.data[0]
            
        except Exception as e:
            error_msg = f"Error inserting record into {table_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
    async def select_records(self, 
                           table_name: str, 
                           columns: str = "*", 
                           filters: Optional[Dict[str, Any]] = None,
                           order_by: Optional[str] = None,
                           order_desc: bool = False,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
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
            query = self.supabase.table(table_name).select(columns)
            
            # Apply filters
            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)
            
            # Apply order
            if order_by:
                query = query.order(order_by, desc=order_desc)
                
            # Apply limit
            if limit:
                query = query.limit(limit)
                
            # Execute query
            response = query.execute()
            return response.data or []
            
        except Exception as e:
            error_msg = f"Error selecting records from {table_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
    async def update_record(self, 
                          table_name: str, 
                          record_id: Union[int, str], 
                          data: Dict[str, Any],
                          id_column: str = "id") -> Dict[str, Any]:
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
            response = self.supabase.table(table_name)\
                .update(data)\
                .eq(id_column, record_id)\
                .execute()
                
            if not response.data:
                raise RuntimeError(f"Update operation returned no data")
                
            return response.data[0]
            
        except Exception as e:
            error_msg = f"Error updating record {record_id} in {table_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
    async def delete_records(self, 
                           table_name: str, 
                           filters: Dict[str, Any]) -> List[Dict[str, Any]]:
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
            query = self.supabase.table(table_name).delete()
            
            # Apply filters
            for column, value in filters.items():
                query = query.eq(column, value)
                
            # Execute query
            response = query.execute()
            return response.data or []
            
        except Exception as e:
            error_msg = f"Error deleting records from {table_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
    async def search_records(self, 
                           table_name: str, 
                           search_column: str, 
                           search_query: str,
                           columns: str = "*",
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for records using ILIKE (case-insensitive pattern matching).
        
        Args:
            table_name: Name of the table
            search_column: Column to search in
            search_query: Search query
            columns: Columns to select
            limit: Maximum number of records to return
            
        Returns:
            List of matching records
            
        Raises:
            RuntimeError: If search fails
        """
        try:
            query = self.supabase.table(table_name)\
                .select(columns)\
                .ilike(search_column, f"%{search_query}%")
                
            if limit:
                query = query.limit(limit)
                
            response = query.execute()
            return response.data or []
            
        except Exception as e:
            error_msg = f"Error searching records in {table_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
    async def vector_search(self, 
                          table_name: str, 
                          embedding: List[float],
                          embedding_column: str = "embedding_nomic",
                          match_threshold: float = 0.7,
                          match_count: int = 5,
                          filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector embeddings.
        
        Args:
            table_name: Name of the table containing embeddings
            embedding: Query embedding vector
            embedding_column: Name of the column containing embeddings
            match_threshold: Similarity threshold (0-1)
            match_count: Maximum number of matches to return
            filters: Optional dictionary of filter conditions
            
        Returns:
            List of matching records with similarity scores
            
        Raises:
            RuntimeError: If vector search fails
        """
        try:
            # Build the RPC function parameters
            params = {
                'query_embedding': embedding,
                'match_threshold': match_threshold,
                'match_count': match_count,
                'table_name': table_name,
                'embedding_column': embedding_column
            }
            
            # Add filters if provided
            if filters:
                params['filter_object'] = filters
            
            # Call the vector similarity search RPC function
            response = self.supabase.rpc('match_documents', params).execute()
            
            if response.error:
                raise RuntimeError(f"Vector search RPC error: {response.error}")
                
            return response.data or []
            
        except Exception as e:
            error_msg = f"Error performing vector search on {table_name}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
                
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the database connection.
        
        Returns:
            Dict with status information
            
        Raises:
            RuntimeError: If operation fails
        """
        try:
            # Try to execute a simple query
            start_time = datetime.now()
            await self.select_records('swarm_messages', limit=1)
            end_time = datetime.now()
            
            return {
                'status': 'ok',
                'latency_ms': (end_time - start_time).total_seconds() * 1000,
                'timestamp': timestamp()
            }
            
        except Exception as e:
            error_msg = f"Database health check failed: {e}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': timestamp()
            } 