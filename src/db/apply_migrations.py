"""
Script to apply database migrations to Supabase.
"""

import os
import sys
from pathlib import Path
from supabase import create_client, Client
from src.services.logging_service import get_logger

logger = get_logger(__name__)

def apply_migration(client: Client, migration_file: Path) -> bool:
    """
    Apply a single migration file to the database.
    
    Args:
        client: Supabase client
        migration_file: Path to the migration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(migration_file, 'r') as f:
            sql = f.read()
            
        # Split into individual statements
        statements = sql.split(';')
        
        for statement in statements:
            if statement.strip():
                try:
                    # Execute each statement
                    client.query(statement).execute()
                except Exception as e:
                    logger.error(f"Error executing statement: {e}")
                    logger.error(f"Statement: {statement}")
                    return False
                    
        logger.debug(f"Successfully applied migration: {migration_file.name}")
        return True
        
    except Exception as e:
        logger.error(f"Error applying migration {migration_file}: {e}")
        return False

def main():
    """Apply all migrations in the migrations directory."""
    try:
        # Get Supabase credentials
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            logger.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
            return 1
            
        # Initialize Supabase client
        client = create_client(url, key)
        
        # Get migrations directory
        migrations_dir = Path(__file__).parent / "migrations"
        if not migrations_dir.exists():
            logger.error(f"Migrations directory not found: {migrations_dir}")
            return 1
            
        # Apply each migration in order
        success = True
        for migration_file in sorted(migrations_dir.glob("*.sql")):
            logger.debug(f"Applying migration: {migration_file.name}")
            if not apply_migration(client, migration_file):
                success = False
                break
                
        if success:
            logger.debug("All migrations applied successfully")
            return 0
        else:
            logger.error("Migration failed")
            return 1
            
    except Exception as e:
        logger.error(f"Error applying migrations: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 