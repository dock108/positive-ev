import os
import sqlite3
import logging
from datetime import datetime

# Paths and Constants
LOG_FOLDER = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/logs"
LOG_FILE = os.path.join(LOG_FOLDER, "feature_engineering.log")
DB_PATH = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db"
BACKUP_FOLDER = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/backups"
SQL_FOLDER = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/sql"

# Stats Configuration
STAT_MAPPING = {
    "Points": 0,
    "Rebounds": 1,
    "Assists": 2,
    "Steals": 3,
    "Blocks": 4,
    "Turnovers": 5,
    "Made Threes": 6
}

# Update STAT_INDICES to use the same mapping
STAT_INDICES = {
    'points': 0,
    'rebounds': 1,
    'assists': 2,
    'steals': 3,
    'blocks': 4,
    'turnovers': 5,
    'made_threes': 6
}

TOTAL_POSSIBLE_GAMES = 82  # NBA season length

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def load_sql(filename):
    """Load SQL query from file."""
    with open(os.path.join(SQL_FOLDER, filename), 'r') as f:
        return f.read()

def cleanup_logs(log_file):
    """Keep only the last 5 runs in the log file."""
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as file:
                # Split logs into runs (each run starts with "Log setup completed")
                content = file.read()
                runs = content.split("Log setup completed")
                
                # Keep the last 5 non-empty runs
                valid_runs = [run for run in runs if run.strip()]
                kept_runs = valid_runs[-5:] if len(valid_runs) > 5 else valid_runs
                
                # Write back the kept runs
                with open(log_file, 'w') as outfile:
                    for i, run in enumerate(kept_runs):
                        if i > 0:  # Add the header back except for first run
                            outfile.write("Log setup completed")
                        outfile.write(run)
                        
            logging.info(f"Cleaned up log file. Keeping last {len(kept_runs)} runs.")
    except Exception as e:
        logging.error(f"Failed to clean up log file: {e}", exc_info=True)

def backup_work_table(conn):
    """Backup the current work table, keeping only the 3 most recent versions."""
    cursor = conn.cursor()
    backup_files = sorted(
        [f for f in os.listdir(BACKUP_FOLDER) if f.startswith("model_work_table_backup")],
        key=lambda f: os.path.getmtime(os.path.join(BACKUP_FOLDER, f))
    )

    while len(backup_files) >= 3:
        os.remove(os.path.join(BACKUP_FOLDER, backup_files.pop(0)))

    backup_file = os.path.join(BACKUP_FOLDER, f"model_work_table_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.sql")
    cursor.execute(f"VACUUM INTO '{backup_file}'")
    logging.info(f"Backed up model_work_table to {backup_file}")

def parse_event_time(event_time, timestamp):
    """Parse the event time (now in YYYY-MM-DD HH:MM format)."""
    try:
        return datetime.strptime(event_time, '%Y-%m-%d %H:%M')
    except ValueError as e:
        logging.error(f"Error parsing event_time: {event_time}: {e}")
        return None

def calculate_stat_metrics(stats_list, stat_index):
    """Calculate rolling averages and other metrics for a specific stat."""
    logging.debug(f"Calculating metrics for stat index {stat_index}")
    if not stats_list:
        logging.debug("No stats list provided")
        return None, None, None, None, None, None, None, None, None
    
    stat_values = [row[stat_index] for row in stats_list if row[stat_index] is not None]
    logging.debug(f"Found {len(stat_values)} valid stat values: {stat_values}")
    
    if not stat_values:
        logging.debug("No valid stat values found")
        return None, None, None, None, None, None, None, None, None

    def calc_window_stats(values, window):
        logging.debug(f"Calculating {window}-game window stats")
        # Use all available data if we don't have enough for the window
        actual_window = min(len(values), window)
        if actual_window == 0:
            return None, None
            
        window_vals = values[:actual_window]
        avg = sum(window_vals) / actual_window
        std = (sum((x - avg) ** 2 for x in window_vals) / actual_window) ** 0.5
        logging.debug(f"{actual_window}-game stats: avg={round(avg,2)}, std={round(std,2)}")
        return round(avg, 2), round(std, 2)

    # Calculate stats for different windows
    avg_5, std_5 = calc_window_stats(stat_values, 5)
    avg_10, std_10 = calc_window_stats(stat_values, 10)
    avg_20, std_20 = calc_window_stats(stat_values, 20)
    
    # Season average uses all available data
    season_avg = round(sum(stat_values) / len(stat_values), 2)
    logging.debug(f"Season average: {season_avg}")
    
    # Trend uses 5-game average or whatever we have
    trend = round(avg_5 - season_avg, 2) if avg_5 and season_avg else 0
    logging.debug(f"Trend: {trend}")
    
    # Consistency score uses 10-game or whatever we have
    consistency = round((1 - std_10 / avg_10) * 100, 2) if avg_10 and std_10 and avg_10 != 0 else 0
    logging.debug(f"Consistency score: {consistency}")
    
    return avg_5, std_5, avg_10, std_10, avg_20, std_20, season_avg, trend, consistency

def get_player_stats_features(cursor, player_name, event_time, event_teams):
    """Get player stats from boxscore data prior to event_time."""
    logging.info(f"Getting stats for player: {player_name}, event: {event_time}")
    
    # Get total games in season (including DNPs)
    season_query = load_sql('get_player_season_stats.sql')
    cursor.execute(season_query, (player_name, event_time, event_time))
    games_played, total_games = cursor.fetchone()
    
    health_score = round((games_played / total_games * 100), 2) if total_games > 0 else 0
    logging.debug(f"Games played: {games_played}/{total_games} (Health: {health_score}%)")
    
    # Get player's recent games before this event
    stats_query = load_sql('get_player_recent_stats.sql')
    cursor.execute(stats_query, (player_name, event_time))
    stats = cursor.fetchall()
    
    # Debug the actual stats values
    if stats:
        for i, stat in enumerate(stats[:3]):  # Show first 3 games
            logging.debug(
                f"Game {i+1}: Points={stat[0]}, Rebounds={stat[1]}, "
                f"Assists={stat[2]}, Date={stat[7]}"
            )
    
    if not stats:
        logging.warning(f"No prior game stats found for {player_name}")
        return {}
        
    # Calculate rolling stats for each stat type
    features = {
        'games_played_season': games_played,
        'health_score': health_score
    }
    
    for stat_name, stat_idx in STAT_INDICES.items():
        if stat_name != 'game_date':
            metrics = calculate_stat_metrics(stats, stat_idx)
            if metrics:
                avg_5, std_5, avg_10, std_10, avg_20, std_20, season_avg, trend, consistency = metrics
                features.update({
                    f'{stat_name}_last_5_avg': avg_5,
                    f'{stat_name}_last_5_std': std_5,
                    f'{stat_name}_last_10_avg': avg_10,
                    f'{stat_name}_last_10_std': std_10,
                    f'{stat_name}_last_20_avg': avg_20,
                    f'{stat_name}_last_20_std': std_20,
                    f'{stat_name}_season_avg': season_avg,
                    f'{stat_name}_trend': trend,
                    f'{stat_name}_consistency': consistency
                })
    
    return features

def extract_player_name(description):
    """Extract player name from bet description."""
    logging.debug(f"Extracting player name from description: {description}")
    try:
        parts = description.split()
        
        # Handle Double Double and Triple Double cases
        if "Double Double" in description:
            player_name = description.replace("Player Double Double", "").strip()
        elif "Triple Double" in description:
            player_name = description.replace("Player Triple Double", "").strip()
        else:
            # For regular prop bets, player name is everything before the last two parts
            # Example: "LeBron James Points Over 25.5" -> "LeBron James"
            player_name = " ".join(parts[:-2])
        
        logging.debug(f"Extracted player name: {player_name}")
        return player_name
    except Exception as e:
        logging.error(f"Error extracting player name from description: {description} - {e}")
        return None

def parse_bet_details(description, bet_type):
    """Parse bet description to extract player name, stat type, condition, and target value."""
    try:
        parts = description.split()
        
        # Handle Double Double and Triple Double cases
        if "Double Double" in description or "Triple Double" in description:
            return None, None, None, None
            
        # For regular props, format should be: "Player Name Stat Over/Under Value"
        # Example: "Anthony Edwards Points Over 35.5"
        if len(parts) < 3:
            return None, None, None, None
            
        # Last two parts should be condition and value
        target_value = float(parts[-1])
        condition = parts[-2]  # Over/Under
        
        # Player name is everything before the last two parts
        player_name = " ".join(parts[:-2])
        
        return player_name, condition, target_value
    except Exception as e:
        logging.error(f"Error parsing bet details: {description} - {e}")
        return None, None, None

def generate_features(conn):
    cursor = conn.cursor()
    
    # Get unique bets with optimal timing
    logging.info("Starting query execution...")
    unique_bets_sql = load_sql('get_unique_bets.sql')
    
    logging.info("Executing optimized query...")
    start_time = datetime.now()
    rows = cursor.execute(unique_bets_sql).fetchall()
    query_time = datetime.now() - start_time
    logging.info(f"Query completed in {query_time.total_seconds():.2f} seconds")
    logging.info(f"Found {len(rows)} optimally-timed bets to process")
    
    # Create the model work table
    cursor.execute("DROP TABLE IF EXISTS model_work_table")
    create_table_sql = load_sql('create_model_work_table.sql')
    cursor.execute(create_table_sql)
    
    # Pre-calculate player stats for all unique players
    player_stats_cache = {}
    player_bets = {}
    
    logging.info("Grouping bets by player...")
    for row in rows:
        if "Player" in row[6]:  # bet_type
            player_name = extract_player_name(row[7])  # description
            if player_name:
                if player_name not in player_bets:
                    player_bets[player_name] = []
                player_bets[player_name].append(row)
    
    logging.info(f"Found {len(player_bets)} unique players to process")
    
    # Calculate stats for each player once
    for player_name, player_rows in player_bets.items():
        # Use the earliest event_time for this player's bets
        earliest_event = min(row[3] for row in player_rows)  # event_time
        player_stats_cache[player_name] = get_player_stats_features(
            cursor, player_name, earliest_event, None
        )
    
    logging.info("Processing all bets with cached player stats...")
    processed = 0
    
    # Now process all bets using cached stats
    for row in rows:
        (bet_id, timestamp, ev_percent, event_time, event_teams, sport_league, 
         bet_type, description, odds, first_odds, sportsbook, bet_size, 
         win_probability, result, time_to_event, stat_categories, _) = row  # Added stat_categories, _ is for rn
        
        # Convert odds to float
        odds = float(odds) if isinstance(odds, (int, float, str)) else 0
        first_odds = float(first_odds) if isinstance(first_odds, (int, float, str)) else 0
        
        # Get player features from cache if it's a player prop
        player_features = {}
        if "Player" in bet_type:
            player_name = extract_player_name(description)
            if player_name in player_stats_cache:
                player_features = player_stats_cache[player_name]
        
        # Format basic features
        ev_percent = round(float(ev_percent.replace('%', '')), 2)
        bet_size = round(float(bet_size.replace('$', '')), 2)
        win_probability = round(float(win_probability.replace('%', '')), 2)
        
        # Calculate market metrics
        line_movement = odds - first_odds
        market_implied_prob = round(1 / (1 + abs(odds) / 100) * 100, 2) if odds != 0 else None
        clv_percent = round(((odds - first_odds) / abs(first_odds)) * 100, 2) if first_odds != 0 else None
        
        # Determine bet timing category
        hours_to_event = time_to_event / 60
        bet_time_category = "Early" if hours_to_event >= 24 else "Mid" if hours_to_event >= 6 else "Late"

        # Prepare all features for insertion
        features = {
            'bet_id': bet_id,
            'timestamp': timestamp,
            'ev_percent': ev_percent,
            'event_time': event_time,
            'event_teams': event_teams,
            'sport_league': sport_league,
            'bet_type': bet_type,
            'description': description,
            'first_odds': first_odds,
            'final_odds': odds,
            'line_movement': line_movement,
            'sportsbook': sportsbook,
            'bet_size': bet_size,
            'win_probability': win_probability,
            'result': result,
            'time_to_event': time_to_event,
            'market_implied_prob': market_implied_prob,
            'clv_percent': clv_percent,
            'bet_time_category': bet_time_category,
            **player_features
        }

        # Build and execute INSERT statement
        columns = ', '.join(features.keys())
        placeholders = ', '.join(['?' for _ in features])
        cursor.execute(f"""
            INSERT INTO model_work_table ({columns})
            VALUES ({placeholders})
        """, list(features.values()))
        
        processed += 1
        if processed % 100 == 0:
            logging.info(f"Processed {processed}/{len(rows)} bets")

    conn.commit()
    logging.info("Initial model work table population complete")

    # Clean up duplicate bets
    logging.info("Cleaning up duplicate bets...")
    cleanup_sql = load_sql('cleanup_model_work_table.sql')
    
    # Split and execute cleanup statements separately
    for statement in cleanup_sql.split(';'):
        if statement.strip():  # Skip empty statements
            try:
                cursor.execute(statement)
                conn.commit()  # Commit after each statement
            except Exception as e:
                logging.error(f"Error executing cleanup statement: {e}")
                raise
    
    # Get final count
    cursor.execute("SELECT COUNT(*) FROM model_work_table")
    final_count = cursor.fetchone()[0]
    logging.info(f"Final unique bet count after cleanup: {final_count}")
    
    conn.commit()
    logging.info("Successfully processed and cleaned up model work table")

def ensure_log_setup():
    """Ensure log folder and file exist."""
    try:
        # Create logs folder if it doesn't exist
        os.makedirs(LOG_FOLDER, exist_ok=True)
        
        # Create log file if it doesn't exist
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w') as f:
                f.write("")
            logging.info("Created new log file")
        
        logging.info("Log setup completed")
    except Exception as e:
        print(f"Error setting up logs: {e}")  # Use print since logging might not be set up yet

if __name__ == "__main__":
    ensure_log_setup()
    cleanup_logs(LOG_FILE)
    conn = sqlite3.connect(DB_PATH)
    try:
        generate_features(conn)
        backup_work_table(conn)
    except Exception as e:
        logging.error(f"Error in feature generation: {e}", exc_info=True)
    finally:
        conn.close()
