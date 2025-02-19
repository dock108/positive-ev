import sqlite3
from contextlib import contextmanager
import logging
from flask import current_app, has_app_context

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DATABASE_PATH = 'app/betting_data.db'

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    if has_app_context():
        logger.debug("Creating database connection within Flask application context")
        db_path = current_app.config['DATABASE_PATH']
    else:
        logger.warning("Creating database connection outside Flask application context")
        db_path = 'app/betting_data.db'
    
    logger.debug(f"Connecting to database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        logger.debug("Successfully established database connection")
        conn.row_factory = sqlite3.Row
        yield conn
        logger.debug("Database connection yielded successfully")
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise
    finally:
        try:
            conn.close()
            logger.debug("Database connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")

def init_db():
    """Initialize the database with required tables."""
    logger.info("Starting database initialization")
    
    if has_app_context():
        logger.debug("Initializing database within Flask application context")
    else:
        logger.warning("Initializing database outside Flask application context")
    
    with get_db_connection() as conn:
        try:
            cursor = conn.cursor()
            
            # Log existing tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = cursor.fetchall()
            logger.debug(f"Existing tables before initialization: {[t[0] for t in existing_tables]}")
            
            # Create betting_data table
            logger.debug("Creating betting_data table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS betting_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bet_id TEXT UNIQUE,
                    timestamp TEXT,
                    ev_percent TEXT,
                    event_time TEXT,
                    event_teams TEXT,
                    sport_league TEXT,
                    bet_type TEXT,
                    description TEXT,
                    odds TEXT,
                    sportsbook TEXT,
                    bet_size TEXT,
                    win_probability TEXT,
                    result TEXT DEFAULT ''
                )
            ''')
            
            # Create bet_grades table
            logger.debug("Creating bet_grades table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bet_grades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bet_id TEXT NOT NULL,
                    grade TEXT NOT NULL,
                    calculated_at DATETIME NOT NULL,
                    ev_score FLOAT,
                    timing_score FLOAT,
                    historical_edge FLOAT,
                    composite_score FLOAT NOT NULL,
                    thirty_day_roi FLOAT,
                    similar_bets_count INTEGER,
                    FOREIGN KEY(bet_id) REFERENCES betting_data(bet_id)
                )
            ''')
            
            # Create bet_results table
            logger.debug("Creating bet_results table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bet_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bet_id TEXT NOT NULL,
                    settlement_time DATETIME NOT NULL,
                    result TEXT NOT NULL,
                    profit_loss FLOAT NOT NULL,
                    closing_line TEXT,
                    clv_percent FLOAT,
                    notes TEXT,
                    FOREIGN KEY(bet_id) REFERENCES betting_data(bet_id)
                )
            ''')
            
            conn.commit()
            logger.debug("Database tables committed successfully")
            
            # Log final table state
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            final_tables = cursor.fetchall()
            logger.info(f"Final tables after initialization: {[t[0] for t in final_tables]}")
            
        except Exception as e:
            logger.error(f"Error during database initialization: {str(e)}")
            raise
        
    logger.info("Database initialization completed successfully")

def dict_factory(cursor, row):
    """Convert database row to dictionary."""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)} 