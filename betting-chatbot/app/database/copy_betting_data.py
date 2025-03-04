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
        logging.FileHandler("copy_betting_data.log"),
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

def main():
    """Copy the betting_data.db database from source to target."""
    try:
        # First, make a direct copy of the database file
        logger.info(f"Copying database from {SOURCE_DB_PATH} to {TARGET_DB_PATH}")
        shutil.copy2(SOURCE_DB_PATH, TARGET_DB_PATH)
        logger.info(f"Database copied successfully")
        
        # Connect to the copied database
        conn = sqlite3.connect(TARGET_DB_PATH)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Find boxscore tables
        boxscore_tables = [t for t in tables if 'boxscore' in t.lower()]
        
        # Drop boxscore tables
        for table in boxscore_tables:
            logger.info(f"Dropping boxscore table: {table}")
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        # Commit changes
        conn.commit()
        
        # Get remaining tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        remaining_tables = [row[0] for row in cursor.fetchall()]
        
        # Log table counts
        for table in remaining_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"Table {table}: {count} rows")
        
        # Close connection
        conn.close()
        
        logger.info(f"Successfully copied database with {len(remaining_tables)} tables")
        logger.info(f"Removed {len(boxscore_tables)} boxscore tables")
        
        return True
    
    except Exception as e:
        logger.error(f"Error copying database: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 