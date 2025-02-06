import os
import logging
from datetime import datetime, timedelta
import sqlite3
from config import DB_FILE, LOG_RETENTION_HOURS

def cleanup_logs(log_file, retention_hours=LOG_RETENTION_HOURS):
    """Keep only the log entries from the past specified hours."""
    try:
        if os.path.exists(log_file):
            cutoff_time = datetime.now() - timedelta(hours=retention_hours)
            with open(log_file, "r") as file:
                lines = file.readlines()

            recent_lines = []
            for line in lines:
                try:
                    log_time_str = line.split(" - ")[0]
                    log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S,%f")
                    if log_time >= cutoff_time:
                        recent_lines.append(line)
                except Exception as e:
                    logging.warning(f"Malformed log line ignored: {line.strip()} - Error: {e}")

            with open(log_file, "w") as file:
                file.writelines(recent_lines)
            logging.info("Log file cleaned up. Only recent entries retained.")
    except Exception as e:
        logging.error(f"Failed to clean up log file: {e}", exc_info=True)

def connect_db():
    """Connect to SQLite database."""
    logging.debug("Connecting to SQLite database...")
    conn = sqlite3.connect(DB_FILE)
    logging.debug("Connected to SQLite database.")
    return conn

def fix_event_time(event_time, timestamp):
    """
    Convert event time from format like 'Wed, Feb 5 at 2:30 PM' to '2025-02-05 14:30'
    
    Args:
        event_time (str): Event time string from scraping
        timestamp (str): Current timestamp in format 'YYYY-MM-DD HH:MM:SS'
    
    Returns:
        str: Formatted datetime string 'YYYY-MM-DD HH:MM'
    """
    try:
        now = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        
        # First convert relative dates to absolute
        if "Today at" in event_time:
            event_time = event_time.replace("Today", now.strftime("%a, %b %d"))
        elif "Tomorrow at" in event_time:
            tomorrow = now + timedelta(days=1)
            event_time = event_time.replace("Tomorrow", tomorrow.strftime("%a, %b %d"))

        # Extract components
        date_part = event_time.split(" at ")[0].strip()
        time_part = event_time.split(" at ")[1].strip()
        
        # Parse time
        time_obj = datetime.strptime(time_part, "%I:%M %p")
        time_str = time_obj.strftime("%H:%M")
        
        # Parse date
        date_obj = datetime.strptime(f"{date_part}, {now.year}", "%a, %b %d, %Y")
        
        # Handle year rollover
        if date_obj.month < now.month:
            date_obj = date_obj.replace(year=now.year + 1)
            
        return f"{date_obj.strftime('%Y-%m-%d')} {time_str}"
        
    except Exception as e:
        logging.error(f"Failed to fix Event Time: {event_time} due to {e}")
        return event_time

def generate_bet_id(event_time, event_teams, sport_league, bet_type, description):
    """Generate a hash-based bet ID."""
    import hashlib
    unique_string = f"{event_time}|{event_teams}|{sport_league}|{bet_type}|{description}"
    return hashlib.md5(unique_string.encode()).hexdigest()

def create_tables():
    """Create necessary database tables if they don't exist."""
    conn = connect_db()
    cursor = conn.cursor()

    # Table for game boxscores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_boxscores (
            game_id TEXT,
            home_away TEXT,
            game_date TEXT,
            team TEXT,
            opponent TEXT,
            quarter_1 INTEGER,
            quarter_2 INTEGER,
            quarter_3 INTEGER,
            quarter_4 INTEGER,
            first_half INTEGER,
            second_half INTEGER,
            total_score INTEGER,
            PRIMARY KEY (game_id, home_away)
        )
    """)

    # Table for player boxscores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_boxscores (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            player_name TEXT,
            points INTEGER,
            rebounds INTEGER,
            assists INTEGER,
            steals INTEGER,
            blocks INTEGER,
            turnovers INTEGER,
            made_threes INTEGER,
            FOREIGN KEY (game_id) REFERENCES game_boxscores (game_id)
        )
    """)

    # Table for betting data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS betting_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bet_id TEXT,
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
    """)

    conn.commit()
    conn.close()

def get_latest_date_from_db(table_name, date_column):
    """
    Fetch the latest date from a specified table and column.
    
    Args:
        table_name (str): Name of the table to query
        date_column (str): Name of the date column
        
    Returns:
        datetime: Latest date from the database or default date if none found
    """
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT MAX({date_column}) FROM {table_name}")
        result = cursor.fetchone()
        if result and result[0]:
            latest_date = datetime.strptime(result[0], "%Y-%m-%d")
            logging.info(f"Latest date in {table_name}: {latest_date.strftime('%Y-%m-%d')}")
            return latest_date
        else:
            logging.info(f"No dates found in {table_name}. Defaulting to start date.")
            return datetime(2025, 1, 1)  # Default start date
    except Exception as e:
        logging.error(f"Error fetching latest date from {table_name}: {e}", exc_info=True)
        return datetime(2025, 1, 1)  # Default start date
    finally:
        conn.close() 