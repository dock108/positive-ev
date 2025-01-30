import os
import sqlite3
import logging
from datetime import datetime, timedelta
import math

# Update with the correct path to the logs folder
LOG_FOLDER = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/logs"
LOG_FILE = os.path.join(LOG_FOLDER, "feature_engineering.log")
DB_PATH = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db"
BACKUP_FOLDER = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/backups"

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Increased logging level for detailed debug output
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def cleanup_logs(log_folder):
    """Remove log files older than 48 hours."""
    cutoff_time = datetime.now() - timedelta(hours=48)
    for log_file in os.listdir(log_folder):
        log_path = os.path.join(log_folder, log_file)
        if os.path.isfile(log_path):
            file_time = datetime.fromtimestamp(os.path.getmtime(log_path))
            if file_time < cutoff_time:
                os.remove(log_path)
                logging.info(f"Deleted old log file: {log_file}")

def backup_work_table(conn):
    """Backup the current work table, keeping only the 3 most recent versions."""
    cursor = conn.cursor()
    backup_files = sorted(
        [f for f in os.listdir(BACKUP_FOLDER) if f.startswith("model_work_table_backup")],
        key=lambda f: os.path.getmtime(os.path.join(BACKUP_FOLDER, f))
    )

    # Remove old backups if there are more than 3
    while len(backup_files) >= 3:
        os.remove(os.path.join(BACKUP_FOLDER, backup_files.pop(0)))

    # Create a new backup
    backup_file = os.path.join(BACKUP_FOLDER, f"model_work_table_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.sql")
    cursor.execute(f"VACUUM INTO '{backup_file}'")
    logging.info(f"Backed up model_work_table to {backup_file}")

def parse_event_time(event_time, timestamp):
    """Parse the event time."""
    try:
        event_dt = datetime.strptime(event_time, '%a, %b %d at %I:%M %p')
        timestamp_year = timestamp.year
        event_dt = event_dt.replace(year=timestamp_year)

        if event_dt < timestamp and timestamp.month == 12 and event_dt.month == 1:
            event_dt = event_dt.replace(year=timestamp_year + 1)
        return event_dt
    except ValueError as e:
        logging.error(f"Error parsing event_time: {event_time} with timestamp {timestamp}: {e}")
        return None

def calculate_time_window_score(time_to_event, optimal_time=30, steepness=0.1):
    """
    Score time_to_event using a sigmoid function for smoother transitions.
    
    Args:
        time_to_event (float): The time to event in minutes.
        optimal_time (float): The ideal time to event for maximum score.
        steepness (float): Controls the steepness of the curve.
        
    Returns:
        float: A score between 0 and 1.
    """
    return round(1 / (1 + math.exp(-steepness * (time_to_event - optimal_time))), 2)

def calculate_odds_score(odds):
    """Score odds."""
    return round(max(0, 1 - abs(odds - 100) / 500), 2)

def calculate_opportunity_value(bet_size, win_probability, ev_percent, time_window_score, odds_score, weights=None):
    """
    Calculate opportunity value with reduced impact from time_window_score.
    
    Args:
        bet_size (float): The bet size in dollars.
        win_probability (float): The probability of winning.
        ev_percent (float): Expected value as a decimal.
        time_window_score (float): A score between 0 and 1 based on time to event.
        odds_score (float): A score between 0 and 1 based on odds.
        weights (dict): Optional weights for each component (default is equal weighting).
    
    Returns:
        float: Opportunity value.
    """
    # Default weights for components
    if weights is None:
        weights = {
            "bet_size": 0.4,
            "win_probability": 0.3,
            "ev_percent": 0.2,
            "time_window_score": 0.05,
            "odds_score": 0.05
        }
    
    # Weighted sum approach
    opportunity_value = (
        weights["bet_size"] * bet_size +
        weights["win_probability"] * win_probability * bet_size +
        weights["ev_percent"] * ev_percent * bet_size +
        weights["time_window_score"] * time_window_score * bet_size +
        weights["odds_score"] * odds_score * bet_size
    )
    
    return round(opportunity_value, 2)

def generate_features(conn):
    """Generate features and save to model_work_table."""
    cursor = conn.cursor()

    logging.info("Dropping and recreating model_work_table...")
    cursor.execute("DROP TABLE IF EXISTS model_work_table")
    cursor.execute("""
        CREATE TABLE model_work_table (
            bet_id TEXT,
            timestamp TEXT,
            ev_percent REAL,
            event_time TEXT,
            event_teams TEXT,
            sport_league TEXT,
            bet_type TEXT,
            description TEXT,
            first_odds INTEGER,
            final_odds INTEGER,
            line_movement INTEGER,
            sportsbook TEXT,
            bet_size REAL,
            win_probability REAL,
            result TEXT,
            time_to_event REAL,
            UNIQUE (bet_id, timestamp) ON CONFLICT REPLACE
        )
    """)

    logging.info("Querying betting_data for results 'W' or 'L'...")
    rows = cursor.execute("""
        SELECT bet_id, timestamp, ev_percent, event_time, event_teams, sport_league, bet_type,
               description, odds, sportsbook, bet_size, win_probability, result
        FROM betting_data
        WHERE result IN ('W', 'L')
        ORDER BY bet_id, timestamp
    """).fetchall()

    # Group bets by bet_id
    bet_id_groups = {}
    for row in rows:
        bet_id = row[0]
        if bet_id not in bet_id_groups:
            bet_id_groups[bet_id] = []
        bet_id_groups[bet_id].append(row)

    processed_rows = []

    for bet_id, group in bet_id_groups.items():
        valid_entries = []

        for row in group:
            bet_id, timestamp, ev_percent, event_time, event_teams, sport_league, bet_type, description, odds, sportsbook, bet_size, win_probability, result = row
            
            # Parse timestamp and event time
            timestamp_dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            event_dt = parse_event_time(event_time, timestamp_dt)

            if not event_dt or not timestamp_dt:
                logging.warning(f"Skipping invalid event_time or timestamp for bet_id {bet_id}.")
                continue

            # Calculate time_to_event
            time_to_event = round((event_dt - timestamp_dt).total_seconds() / 60, 2)

            # Keep only entries where time_to_event >= 20
            if time_to_event >= 20:
                valid_entries.append((row, time_to_event))

        # If no valid entries remain, log and skip this bet
        if not valid_entries:
            logging.warning(f"Skipping bet_id {bet_id} because all entries were within 20 minutes.")
            continue

        # Sort valid entries by timestamp
        valid_entries.sort(key=lambda x: x[0][1])

        # First and final odds
        first_odds = int(valid_entries[0][0][8])  # First seen valid odds
        final_odds = int(valid_entries[-1][0][8])  # Last recorded valid odds

        # Compute line movement
        line_movement = final_odds - first_odds

        # Get last valid row data
        latest_entry, time_to_event = valid_entries[-1]
        (bet_id, timestamp, ev_percent, event_time, event_teams, sport_league, bet_type, description,
         odds, sportsbook, bet_size, win_probability, result) = latest_entry

        # Format numbers
        ev_percent = round(float(ev_percent.replace('%', '')), 2)
        bet_size = round(float(bet_size.replace('$', '')), 2)
        win_probability = round(float(win_probability.replace('%', '')), 2)

        # Insert into model_work_table
        cursor.execute("""
            INSERT INTO model_work_table (
                bet_id, timestamp, ev_percent, event_time, event_teams, sport_league, bet_type,
                description, first_odds, final_odds, line_movement, sportsbook,
                bet_size, win_probability, result,
                time_to_event
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bet_id, timestamp, ev_percent, event_time, event_teams, sport_league, bet_type, description,
            first_odds, final_odds, line_movement, sportsbook,
            bet_size, win_probability, result,
            time_to_event
        ))

        processed_rows.append(bet_id)

    conn.commit()
    logging.info(f"Processed {len(processed_rows)} rows into model_work_table.")

if __name__ == "__main__":
    cleanup_logs(LOG_FOLDER)
    conn = sqlite3.connect(DB_PATH)
    try:
        generate_features(conn)
    except Exception as e:
        logging.error(f"Error in feature generation: {e}", exc_info=True)
    finally:
        conn.close()
