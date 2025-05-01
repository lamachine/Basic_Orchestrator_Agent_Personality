"""
Database Migration Utilities

This module provides utilities for managing database migrations.
It includes functions for creating migration files, running migrations,
and tracking migration status.
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from src.managers.db_manager import DatabaseManager
from src.services.logging_service import get_logger

# Initialize logger
logger = get_logger(__name__)

# Constants
MIGRATIONS_DIR = "migrations"
MIGRATION_HISTORY_TABLE = "migration_history"

def ensure_migrations_dir() -> str:
    """
    Ensure the migrations directory exists.
    
    Returns:
        str: Path to the migrations directory
    """
    # Get the project root directory
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    migrations_dir = os.path.join(root_dir, MIGRATIONS_DIR)
    
    # Create the directory if it doesn't exist
    if not os.path.exists(migrations_dir):
        os.makedirs(migrations_dir)
        logger.debug(f"Created migrations directory: {migrations_dir}")
    
    return migrations_dir

def create_migration_file(name: str, description: str = "") -> str:
    """
    Create a new migration file.
    
    Args:
        name: Migration name (will be used in filename)
        description: Optional description of the migration
        
    Returns:
        str: Path to the created migration file
    """
    # Ensure migrations directory exists
    migrations_dir = ensure_migrations_dir()
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Create filename: timestamp_name.sql
    safe_name = name.lower().replace(" ", "_").replace("-", "_")
    filename = f"{timestamp}_{safe_name}.sql"
    filepath = os.path.join(migrations_dir, filename)
    
    # Create the migration file with a template
    with open(filepath, "w") as f:
        f.write(f"-- Migration: {name}\n")
        f.write(f"-- Created: {datetime.now().isoformat()}\n")
        f.write(f"-- Description: {description}\n\n")
        f.write("-- Write your SQL statements here\n\n")
        f.write("-- Example:\n")
        f.write("-- CREATE TABLE IF NOT EXISTS example_table (\n")
        f.write("--     id SERIAL PRIMARY KEY,\n")
        f.write("--     name TEXT NOT NULL,\n")
        f.write("--     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()\n")
        f.write("-- );\n")
    
    logger.debug(f"Created migration file: {filepath}")
    return filepath

async def ensure_migration_table(db_manager: DatabaseManager) -> None:
    """
    Ensure the migration history table exists.
    
    Args:
        db_manager: DatabaseManager instance
    """
    # SQL to create the migration history table if it doesn't exist
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {MIGRATION_HISTORY_TABLE} (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        filename TEXT NOT NULL,
        applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        status TEXT NOT NULL,
        error_message TEXT
    );
    """
    
    # Execute the SQL
    try:
        await db_manager.db_service.supabase.rpc('execute_sql', {'sql': create_table_sql}).execute()
        logger.debug(f"Ensured migration history table exists")
    except Exception as e:
        logger.error(f"Error ensuring migration history table: {e}")
        raise

async def get_applied_migrations(db_manager: DatabaseManager) -> List[Dict[str, Any]]:
    """
    Get the list of applied migrations.
    
    Args:
        db_manager: DatabaseManager instance
        
    Returns:
        List of applied migrations
    """
    try:
        # Ensure the migration table exists
        await ensure_migration_table(db_manager)
        
        # Get all applied migrations
        result = await db_manager.db_service.select_records(
            table_name=MIGRATION_HISTORY_TABLE,
            order_by="applied_at"
        )
        
        return result
    except Exception as e:
        logger.error(f"Error getting applied migrations: {e}")
        return []

async def run_migration(db_manager: DatabaseManager, migration_file: str) -> bool:
    """
    Run a single migration file.
    
    Args:
        db_manager: DatabaseManager instance
        migration_file: Path to the migration file
        
    Returns:
        bool: Success status
    """
    # Extract filename and name from the path
    filename = os.path.basename(migration_file)
    name = filename.split("_", 1)[1].replace(".sql", "").replace("_", " ").title()
    
    # Record in the migration history table
    migration_record = {
        "name": name,
        "filename": filename,
        "status": "running"
    }
    
    try:
        # Ensure the migration table exists
        await ensure_migration_table(db_manager)
        
        # Insert the migration record
        await db_manager.db_service.insert(
            table_name=MIGRATION_HISTORY_TABLE,
            data=migration_record
        )
        
        # Run the migration
        success = await db_manager.execute_migration(migration_file)
        
        # Update the migration record
        if success:
            await db_manager.db_service.update_record(
                table_name=MIGRATION_HISTORY_TABLE,
                record_id=migration_record["id"],
                data={"status": "completed"}
            )
            logger.debug(f"Successfully applied migration: {filename}")
        else:
            await db_manager.db_service.update_record(
                table_name=MIGRATION_HISTORY_TABLE,
                record_id=migration_record["id"],
                data={"status": "failed", "error_message": "Migration returned false"}
            )
            logger.error(f"Failed to apply migration: {filename}")
        
        return success
    except Exception as e:
        # Update the migration record with the error
        try:
            await db_manager.db_service.update_record(
                table_name=MIGRATION_HISTORY_TABLE,
                record_id=migration_record["id"],
                data={"status": "failed", "error_message": str(e)}
            )
        except Exception:
            # If we can't update the record, just log the error
            pass
        
        logger.error(f"Error running migration {filename}: {e}")
        return False

async def run_pending_migrations(db_manager: DatabaseManager) -> Dict[str, Any]:
    """
    Run all pending migrations.
    
    Args:
        db_manager: DatabaseManager instance
        
    Returns:
        Dict with migration results
    """
    # Ensure migrations directory exists
    migrations_dir = ensure_migrations_dir()
    
    # Get all migration files
    all_files = [f for f in os.listdir(migrations_dir) if f.endswith(".sql")]
    all_files.sort()  # Sort by timestamp (filename starts with timestamp)
    
    # Get applied migrations
    applied = await get_applied_migrations(db_manager)
    applied_filenames = [m["filename"] for m in applied]
    
    # Find pending migrations
    pending_files = [f for f in all_files if f not in applied_filenames]
    
    # Run each pending migration
    results = {
        "total": len(pending_files),
        "success": 0,
        "failed": 0,
        "details": []
    }
    
    for filename in pending_files:
        migration_file = os.path.join(migrations_dir, filename)
        success = await run_migration(db_manager, migration_file)
        
        # Update results
        if success:
            results["success"] += 1
        else:
            results["failed"] += 1
            
        results["details"].append({
            "filename": filename,
            "success": success
        })
    
    return results

def create_table_migration(table_name: str, columns: List[Dict[str, Any]]) -> str:
    """
    Create a migration file for a new table.
    
    Args:
        table_name: Name of the table to create
        columns: List of column definitions with name, type, and constraints
        
    Returns:
        str: Path to the created migration file
    """
    # Create migration file
    filepath = create_migration_file(
        f"create_{table_name}_table", 
        f"Create {table_name} table"
    )
    
    # Build the SQL for the table creation
    with open(filepath, "w") as f:
        f.write(f"-- Migration: Create {table_name} table\n")
        f.write(f"-- Created: {datetime.now().isoformat()}\n\n")
        
        f.write(f"CREATE TABLE IF NOT EXISTS {table_name} (\n")
        
        # Add columns
        for i, column in enumerate(columns):
            # Generate constraints string
            constraints = column.get("constraints", "")
            if constraints and not constraints.strip().startswith("CONSTRAINT"):
                constraints = " " + constraints
                
            # Write the column definition
            line = f"    {column['name']} {column['type']}{constraints}"
            
            # Add comma if not the last column
            if i < len(columns) - 1:
                line += ","
                
            f.write(line + "\n")
            
        # Close the table definition
        f.write(");\n")
        
        # Add indexes if specified
        indexes = column.get("indexes", [])
        for index in indexes:
            index_name = index.get("name", f"idx_{table_name}_{index['columns'].replace(',', '_')}")
            index_type = index.get("type", "")
            if index_type:
                index_type = f"USING {index_type}"
                
            f.write(f"\nCREATE INDEX {index_name} ON {table_name} {index_type}({index['columns']});\n")
    
    logger.debug(f"Created table migration file: {filepath}")
    return filepath

async def create_migration_from_diff(
    db_manager: DatabaseManager,
    source_table: str,
    target_table: str,
    name: Optional[str] = None
) -> str:
    """
    Create a migration file based on the diff between two tables.
    
    Args:
        db_manager: DatabaseManager instance
        source_table: Source table name
        target_table: Target table name
        name: Optional name for the migration
        
    Returns:
        str: Path to the created migration file
    """
    # Get schema for both tables
    source_schema = await db_manager.get_table_schema(source_table)
    target_schema = await db_manager.get_table_schema(target_table)
    
    # Create name if not provided
    if not name:
        name = f"migrate_{source_table}_to_{target_table}"
    
    # Create migration file
    filepath = create_migration_file(
        name, 
        f"Migration from {source_table} to {target_table}"
    )
    
    # Build the SQL for the migration
    with open(filepath, "w") as f:
        f.write(f"-- Migration: {name}\n")
        f.write(f"-- Created: {datetime.now().isoformat()}\n")
        f.write(f"-- Source: {source_table}\n")
        f.write(f"-- Target: {target_table}\n\n")
        
        # Find columns to add (in target but not in source)
        source_cols = {col["column_name"]: col for col in source_schema}
        target_cols = {col["column_name"]: col for col in target_schema}
        
        # Columns to add
        for col_name, col in target_cols.items():
            if col_name not in source_cols:
                f.write(f"-- Add column {col_name}\n")
                f.write(f"ALTER TABLE {source_table} ADD COLUMN {col_name} {col['data_type']}")
                
                # Add default value if specified
                default = col.get("column_default")
                if default:
                    f.write(f" DEFAULT {default}")
                    
                # Add NULL constraint if specified
                if col.get("is_nullable", "YES").upper() == "NO":
                    f.write(" NOT NULL")
                    
                f.write(";\n\n")
        
        # Columns to modify (data type changes)
        for col_name, source_col in source_cols.items():
            if col_name in target_cols:
                target_col = target_cols[col_name]
                
                # Check if data type is different
                if source_col["data_type"] != target_col["data_type"]:
                    f.write(f"-- Change data type of {col_name}\n")
                    f.write(f"ALTER TABLE {source_table} ALTER COLUMN {col_name} TYPE {target_col['data_type']};\n\n")
                
                # Check if NULL constraint is different
                if source_col.get("is_nullable") != target_col.get("is_nullable"):
                    if target_col.get("is_nullable", "YES").upper() == "NO":
                        f.write(f"-- Add NOT NULL constraint to {col_name}\n")
                        f.write(f"ALTER TABLE {source_table} ALTER COLUMN {col_name} SET NOT NULL;\n\n")
                    else:
                        f.write(f"-- Remove NOT NULL constraint from {col_name}\n")
                        f.write(f"ALTER TABLE {source_table} ALTER COLUMN {col_name} DROP NOT NULL;\n\n")
        
        # Columns to drop (in source but not in target)
        for col_name in source_cols:
            if col_name not in target_cols:
                f.write(f"-- Drop column {col_name}\n")
                f.write(f"ALTER TABLE {source_table} DROP COLUMN {col_name};\n\n")
    
    logger.debug(f"Created diff migration file: {filepath}")
    return filepath 