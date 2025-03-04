import os
import sqlite3
import sys
import logging
from pathlib import Path
from flask import Flask

# Add the parent directory to sys.path
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database.db import migrate_from_positive_ev

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """
    Initialize the chatbot database and migrate data from Positive EV.
    """
    try:
        # Define paths
        chatbot_db_dir = Path(__file__).resolve().parent.parent.parent / 'database'
        chatbot_db_path = chatbot_db_dir / 'chatbot.db'
        positive_ev_db_path = Path('/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db')
        
        # Create database directory if it doesn't exist
        os.makedirs(chatbot_db_dir, exist_ok=True)
        
        # Check if Positive EV database exists
        if not positive_ev_db_path.exists():
            logger.error(f"Positive EV database not found at {positive_ev_db_path}")
            return False
        
        # Initialize database with schema
        logger.info("Initializing chatbot database...")
        
        # Create a temporary connection to run the schema
        conn = sqlite3.connect(chatbot_db_path)
        with open(Path(__file__).resolve().parent / 'schema.sql', 'r') as f:
            conn.executescript(f.read())
        conn.close()
        
        # Create a minimal Flask app for context
        app = Flask(__name__)
        with app.app_context():
            # Migrate data from Positive EV
            logger.info("Migrating data from Positive EV...")
            migrate_from_positive_ev(str(positive_ev_db_path))
        
        logger.info("Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
