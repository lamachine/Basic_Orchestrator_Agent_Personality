"""
Database Query Service

This module provides a simple interface for executing read-only SQL queries
against the database for use with the MCP adapter.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional, Union

# Add project path for imports
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from src.services.db_services.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def execute_query(sql: str) -> Dict[str, Any]:
    """
    Execute a read-only SQL query against the database.
    
    This function ensures that only SELECT queries are executed
    to prevent modification of the database.
    
    Args:
        sql: The SQL query to execute (must be a SELECT query)
        
    Returns:
        Dictionary containing the query results or error information
    """
    try:
        # Validate that this is a read-only query
        sql = sql.strip()
        if not sql.lower().startswith('select'):
            return {
                "status": "error",
                "error": "Only SELECT queries are allowed for security reasons"
            }
        
        # Initialize the database manager
        db_manager = DatabaseManager()
        
        # Execute the query
        logger.debug(f"Executing SQL query: {sql[:100]}...")
        result = db_manager.execute_raw_query(sql)
        
        # Process the result
        if isinstance(result, list):
            # Convert any non-JSON serializable values to strings
            processed_rows = []
            for row in result:
                processed_row = {}
                for key, value in row.items():
                    if isinstance(value, (str, int, float, bool, type(None))):
                        processed_row[key] = value
                    else:
                        processed_row[key] = str(value)
                processed_rows.append(processed_row)
            
            return {
                "status": "success",
                "query": sql,
                "row_count": len(processed_rows),
                "columns": list(processed_rows[0].keys()) if processed_rows else [],
                "rows": processed_rows
            }
        else:
            return {
                "status": "success",
                "query": sql,
                "result": str(result)
            }
    
    except Exception as e:
        error_msg = f"Error executing query: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "query": sql,
            "error": error_msg
        } 