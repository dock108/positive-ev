import sqlite3
import os
import sys
import logging
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("merge_databases.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define paths
CHATBOT_DB_PATH = '/Users/michaelfuscoletti/Desktop/mega-plan/betting-chatbot/web/backend/database/chatbot.db'
BETTING_DB_PATH = '/Users/michaelfuscoletti/Desktop/mega-plan/betting-chatbot/web/backend/database/betting_data.db'
MERGED_DB_PATH = '/Users/michaelfuscoletti/Desktop/mega-plan/betting-chatbot/web/backend/database/chatbot_merged.db'

def get_table_schema(conn, table_name):
    """Get the CREATE TABLE statement for a table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    result = cursor.fetchone()
    return result[0] if result else None

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
    if not schema:
        logger.warning(f"Table {table_name} not found in source database")
        return 0
    
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
    """Merge chatbot.db and betting_data.db into a single database."""
    try:
        # Make a copy of chatbot.db as our starting point
        logger.info("Creating merged database from chatbot.db")
        shutil.copy2(CHATBOT_DB_PATH, MERGED_DB_PATH)
        
        # Connect to databases
        chatbot_conn = sqlite3.connect(CHATBOT_DB_PATH)
        betting_conn = sqlite3.connect(BETTING_DB_PATH)
        merged_conn = sqlite3.connect(MERGED_DB_PATH)
        
        # Get tables from each database
        chatbot_tables = get_all_tables(chatbot_conn)
        betting_tables = get_all_tables(betting_conn)
        
        logger.info(f"Chatbot tables: {', '.join(chatbot_tables)}")
        logger.info(f"Betting tables: {', '.join(betting_tables)}")
        
        # Drop positive_ev_bets table from merged database if it exists
        if 'positive_ev_bets' in chatbot_tables:
            logger.info("Dropping positive_ev_bets table from merged database")
            merged_conn.execute("DROP TABLE IF EXISTS positive_ev_bets")
        
        # Copy all tables from betting_data.db to merged database
        total_rows = 0
        for table in betting_tables:
            rows = copy_table(betting_conn, merged_conn, table)
            total_rows += rows
        
        # Commit changes
        merged_conn.commit()
        
        # Get final list of tables in merged database
        merged_tables = get_all_tables(merged_conn)
        logger.info(f"Merged database tables: {', '.join(merged_tables)}")
        
        # Log row counts for each table
        for table in merged_tables:
            cursor = merged_conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"Table {table}: {count} rows")
        
        # Close connections
        chatbot_conn.close()
        betting_conn.close()
        merged_conn.close()
        
        # Replace chatbot.db with merged database
        logger.info("Replacing chatbot.db with merged database")
        shutil.copy2(MERGED_DB_PATH, CHATBOT_DB_PATH)
        
        # Remove temporary merged database
        os.remove(MERGED_DB_PATH)
        logger.info("Merge completed successfully")
        
        return True
    
    except Exception as e:
        logger.error(f"Error merging databases: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 