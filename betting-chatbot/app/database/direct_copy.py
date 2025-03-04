import sqlite3
import os
import sys
from pathlib import Path
import logging
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("direct_copy.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define paths
SOURCE_DB_PATH = '/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db'
TARGET_DB_DIR = Path('/Users/michaelfuscoletti/Desktop/mega-plan/betting-chatbot/web/backend/database')
TARGET_DB_PATH = TARGET_DB_DIR / 'betting_data.db'

# Ensure target directory exists
os.makedirs(TARGET_DB_DIR, exist_ok=True)

def get_table_schema(conn, table_name):
    """Get the CREATE TABLE statement for a table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone()[0]

def get_all_tables(conn):
    """Get a list of all tables in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row[0] for row in cursor.fetchall()]

def copy_table(source_conn, target_conn, table_name):
    """Copy a table from source to target database."""
    logger.info(f"Copying table: {table_name}")
    
    # Get table schema
    schema = get_table_schema(source_conn, table_name)
    
    # Create table in target database
    target_conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    target_conn.execute(schema)
    
    # Get column names
    cursor = source_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    columns_str = ', '.join(columns)
    placeholders = ', '.join(['?' for _ in columns])
    
    # Copy data
    cursor.execute(f"SELECT {columns_str} FROM {table_name}")
    rows = cursor.fetchall()
    
    if rows:
        target_cursor = target_conn.cursor()
        target_cursor.executemany(
            f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})",
            rows
        )
    
    logger.info(f"Copied {len(rows)} rows for table {table_name}")
    return len(rows)

def main():
    """Copy all tables from source to target database."""
    try:
        # Option 1: Direct file copy (faster but less flexible)
        logger.info(f"Copying database file from {SOURCE_DB_PATH} to {TARGET_DB_PATH}")
        shutil.copy2(SOURCE_DB_PATH, TARGET_DB_PATH)
        logger.info("Database file copied successfully")
        
        # Connect to the copied database to remove boxscore tables
        conn = sqlite3.connect(TARGET_DB_PATH)
        cursor = conn.cursor()
        
        # Get all tables
        tables = get_all_tables(conn)
        
        # Find boxscore tables
        boxscore_tables = [t for t in tables if 'boxscore' in t.lower()]
        
        # Drop boxscore tables
        for table in boxscore_tables:
            logger.info(f"Dropping boxscore table: {table}")
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        # Commit changes
        conn.commit()
        
        # Get remaining tables and log row counts
        remaining_tables = get_all_tables(conn)
        for table in remaining_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"Table {table}: {count} rows")
        
        # Close connection
        conn.close()
        
        logger.info(f"Successfully copied database with {len(remaining_tables)} tables")
        logger.info(f"Removed {len(boxscore_tables)} boxscore tables")
        
        return True
        
        # Option 2: Table-by-table copy (commented out, use if needed)
        """
        # Connect to databases
        source_conn = sqlite3.connect(SOURCE_DB_PATH)
        target_conn = sqlite3.connect(TARGET_DB_PATH)
        
        # Get all tables
        tables = get_all_tables(source_conn)
        
        # Skip boxscore tables
        tables_to_copy = [t for t in tables if 'boxscore' not in t.lower()]
        
        logger.info(f"Found {len(tables_to_copy)} tables to copy")
        
        # Copy each table
        total_rows = 0
        for table in tables_to_copy:
            rows = copy_table(source_conn, target_conn, table)
            total_rows += rows
        
        # Commit changes
        target_conn.commit()
        
        logger.info(f"Successfully copied {len(tables_to_copy)} tables with {total_rows} total rows")
        
        # Close connections
        source_conn.close()
        target_conn.close()
        
        return True
        """
    
    except Exception as e:
        logger.error(f"Error copying database: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 