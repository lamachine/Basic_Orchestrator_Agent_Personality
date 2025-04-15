"""
Database service provider module.
"""
from typing import Optional, Dict, Any
import os
from supabase import create_client, Client

class DBService:
    """Service for interacting with the database."""
    
    def __init__(self):
        """Initialize the database service."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Using service role key for backend operations
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
            
        self.client = create_client(url, key)
        
    async def query(self, table: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a query on the database.
        
        Args:
            table: The table to query
            query_params: Query parameters
            
        Returns:
            Query results
        """
        try:
            result = self.client.table(table).select("*")
            for key, value in query_params.items():
                result = result.eq(key, value)
            return result.execute()
        except Exception as e:
            print(f"Error in database query: {e}")
            return {"data": [], "error": str(e)}

_db_service: Optional[DBService] = None

def get_db_service() -> DBService:
    """
    Get or create the database service instance.
    
    Returns:
        DBService instance
    """
    global _db_service
    if _db_service is None:
        _db_service = DBService()
    return _db_service 