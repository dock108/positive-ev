import logging
import os
import shutil
from datetime import datetime

# Import path setup first
from path_setup import project_root  # noqa

from app.db_utils import get_db_connection

def backup_database():
    """Create a backup of the database before making schema changes."""
    try:
        db_path = 'app/betting_data.db'
        backup_folder = 'app/backups'
        os.makedirs(backup_folder, exist_ok=True)
        
        # Create timestamped backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_folder, f'betting_data_pre_schema_change_{timestamp}.db')
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_file)
            logging.info(f"Created database backup at: {backup_file}")
            return True
        else:
            logging.warning(f"Database file not found at: {db_path}")
            return False
    except Exception as e:
        logging.error(f"Error creating database backup: {e}")
        return False

def create_outcome_evaluation_table():
    """Create the bet_outcome_evaluation table for storing AI-evaluated bet outcomes."""
    # First, create a backup
    if not backup_database():
        raise Exception("Failed to create database backup. Aborting schema changes.")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if sport column exists
        cursor.execute("PRAGMA table_info(betting_data)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add sport and league columns if they don't exist
        if 'sport' not in columns:
            cursor.execute("""
                ALTER TABLE betting_data 
                ADD COLUMN sport VARCHAR(50) DEFAULT 'nba'
            """)
        
        if 'league' not in columns:
            cursor.execute("""
                ALTER TABLE betting_data 
                ADD COLUMN league VARCHAR(50) DEFAULT 'NBA'
            """)
        
        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_betting_data_sport_league 
            ON betting_data(sport, league)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_betting_data_event_time 
            ON betting_data(event_time)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_betting_data_composite 
            ON betting_data(sport, league, event_time)
        """)
        
        # Create bet_outcome_evaluation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bet_outcome_evaluation (
                evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bet_id TEXT NOT NULL,
                outcome VARCHAR(10) NOT NULL CHECK (outcome IN ('WIN', 'LOSS', 'TIE', 'UNCERTAIN')),
                confidence_score DECIMAL(5,2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 100),
                evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reasoning TEXT,
                FOREIGN KEY (bet_id) REFERENCES betting_data(bet_id)
            )
        """)
        
        # Create indexes for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bet_outcome_eval_bet_id 
            ON bet_outcome_evaluation(bet_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bet_outcome_eval_outcome 
            ON bet_outcome_evaluation(outcome)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bet_outcome_eval_confidence 
            ON bet_outcome_evaluation(confidence_score)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bet_outcome_eval_date 
            ON bet_outcome_evaluation(evaluated_at)
        """)
        
        conn.commit()
        logging.info("Successfully created bet_outcome_evaluation table and updated betting_data schema with indexes")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bet_evaluation.log'),
            logging.StreamHandler()
        ]
    )
    create_outcome_evaluation_table() 