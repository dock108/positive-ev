import os
import sqlite3
import logging
from datetime import datetime, timedelta

# Normalization dictionary for team names
team_normalization_map = {
    "Memphis Grizzlies": "Memphis",
    "Golden State Warriors": "Golden State",
    "Denver Nuggets": "Denver",
    "San Antonio Spurs": "San Antonio",
    "Utah Jazz": "Utah",
    "Miami Heat": "Miami",
    "New York Knicks": "New York",
    "Chicago Bulls": "Chicago",
    "Portland Trail Blazers": "Portland",
    "Milwaukee Bucks": "Milwaukee",
    "Minnesota Timberwolves": "Minnesota",
    "Detroit Pistons": "Detroit",
    "Phoenix Suns": "Phoenix",
    "Indiana Pacers": "Indiana",
    "Atlanta Hawks": "Atlanta",
    "Los Angeles Clippers": "LA",
    "Los Angeles Lakers": "Los Angeles",
    "Sacramento Kings": "Sacramento",
    "Houston Rockets": "Houston",
    "Orlando Magic": "Orlando",
    "New Orleans Pelicans": "New Orleans",
    "Washington Wizards": "Washington",
    "Boston Celtics": "Boston",
    "Oklahoma City Thunder": "Oklahoma City",
    "Charlotte Hornets": "Charlotte",
    "Cleveland Cavaliers": "Cleveland",
    "Philadelphia 76ers": "Philadelphia",
    "Brooklyn Nets": "Brooklyn",
    "Toronto Raptors": "Toronto",
    "Dallas Mavericks": "Dallas"
}

# Define folder structure
base_dir = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app"
db_file = os.path.join(base_dir, "betting_data.db")
logs_folder = os.path.join(base_dir, "logs")
log_file = f"{logs_folder}/results_update.log"

# Create logs folder if it doesn't exist
os.makedirs(logs_folder, exist_ok=True)

# Set up logging
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Mapping of stat types to database column names
stat_mapping = {
    "Points": "points",
    "Rebounds": "rebounds",
    "Assists": "assists",
    "Steals": "steals",
    "Blocks": "blocks",
    "Turnovers": "turnovers",
    "Made Threes": "made_threes"
}

def cleanup_logs(log_file, retention_hours=2):
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
    logging.debug("Connecting to SQLite database...")
    conn = sqlite3.connect(db_file)
    logging.debug("Connected to SQLite database.")
    return conn

def fetch_player_stats(cursor, game_id, player_name):
    """Fetch player stats for a given game and player."""
    query = """
        SELECT points, rebounds, assists, steals, blocks, turnovers, made_threes
        FROM player_boxscores
        WHERE game_id = ? AND player_name = ?
    """
    cursor.execute(query, (game_id, player_name))
    return cursor.fetchone()

def normalize_team_name(team_name):
    """
    Normalize team names using the team normalization map.
    """
    return team_normalization_map.get(team_name.strip(), team_name.strip())

def extract_and_normalize_teams(event_teams):
    """
    Extract and normalize team names from the event_teams string.
    """
    teams = [normalize_team_name(team.strip()) for team in event_teams.split("vs")]
    logging.debug(f"Extracted and normalized teams: {teams}")
    return teams if len(teams) == 2 else None

def find_game_id(cursor, event_teams, event_time):
    """
    Find the game ID in the database matching the event teams and event time using normalized team names.
    """
    try:
        # Normalize team names
        teams = extract_and_normalize_teams(event_teams)
        if not teams:
            logging.warning(f"Invalid event_teams format: {event_teams}")
            return None

        # Parse and reformat event_time to extract the date
        try:
            parsed_date = datetime.strptime(event_time.split(" at")[0].strip(), "%a, %b %d")
            current_year = datetime.now().year  # Default to the current year if not provided
            event_datetime = parsed_date.replace(year=current_year)  # Add the year to the parsed date
            event_date = event_datetime.strftime("%Y-%m-%d")  # Format as YYYY-MM-DD
        except ValueError as e:
            logging.error(f"Error parsing event_time: {event_time} - {e}")
            return None

        # Query for matching game in the database
        query = """
            SELECT game_id
            FROM game_boxscores
            WHERE game_date = ?
            AND ((team = ? AND opponent = ?) OR (team = ? AND opponent = ?))
        """
        cursor.execute(query, (event_date, teams[0], teams[1], teams[1], teams[0]))
        result = cursor.fetchone()

        if result:
            logging.debug(f"Found game: Game ID {result[0]} for teams: {teams} on date: {event_date}")
            return result[0]
        else:
            logging.warning(f"No game found for teams: {teams} on date: {event_date}")
            return None

    except Exception as e:
        logging.error(f"Error in find_game_id: {e}", exc_info=True)
        return None

def determine_result(player_stats, stat_types, condition, target_value):
    """
    Determine the result (W, L, or R) based on player stats, target value, and condition.

    Args:
        player_stats (tuple): Player's stats as a tuple.
        stat_types (list): List of stats to consider.
        condition (str): "Over" or "Under".
        target_value (float): The target value to compare against.

    Returns:
        str: Result of the bet ("W", "L", or "R").
    """
    stat_mapping = {
        "Points": 0,
        "Rebounds": 1,
        "Assists": 2,
        "Steals": 3,
        "Blocks": 4,
        "Turnovers": 5,
        "Made Threes": 6
    }

    try:
        # Log inputs for transparency
        logging.debug(f"Player stats: {player_stats}, Stat types: {stat_types}, Condition: {condition}, Target: {target_value}")

        # Handle Player Double Double and Triple Double
        if "Double Double" in stat_types or "Triple Double" in stat_types:
            double_stats = sum(1 for i, stat in enumerate(player_stats) if stat >= 10 and i < 6)  # First six columns are core stats
            logging.debug(f"Double/Triple Double count: {double_stats}")
            
            if "Triple Double" in stat_types:
                return "W" if double_stats >= 3 else "L"
            elif "Double Double" in stat_types:
                return "W" if double_stats >= 2 else "L"

        # Calculate the combined stat value
        actual_value = sum(player_stats[stat_mapping[stat]] for stat in stat_types)
        logging.debug(f"Calculated actual value for {stat_types}: {actual_value}")

        # Compare actual_value with target_value based on condition
        if condition == "Over":
            if actual_value > target_value:
                logging.debug(f"Condition 'Over' met. Actual: {actual_value} > Target: {target_value}. Result: W")
                return "W"
            else:
                logging.debug(f"Condition 'Over' not met. Actual: {actual_value} <= Target: {target_value}. Result: L")
                return "L"
        elif condition == "Under":
            if actual_value < target_value:
                logging.debug(f"Condition 'Under' met. Actual: {actual_value} < Target: {target_value}. Result: W")
                return "W"
            else:
                logging.debug(f"Condition 'Under' not met. Actual: {actual_value} >= Target: {target_value}. Result: L")
                return "L"
        elif actual_value == target_value:
            logging.debug("Actual value matches target value. Result: R")
            return "R"  # Refund/Tie/Push
        else:
            # This fallback should rarely be triggered
            logging.debug("No matching condition found. Falling back to Result: L")
            return "L"
    except KeyError as e:
        logging.error(f"Stat type not found in player stats: {e}")
        return None
    except Exception as e:
        logging.error(f"Error calculating result: {e}", exc_info=True)
        return None

def parse_bet_details(description, bet_type):
    try:
        # Split description into parts
        parts = description.split()

        # Determine if the bet is for Double Double or Triple Double
        is_double_or_triple = "Double Double" in bet_type or "Triple Double" in bet_type
        
        # The last two parts are the condition (Over/Under) and the target value, if not Double/Triple Double
        condition = parts[-2] if not is_double_or_triple else None
        target_value = float(parts[-1]) if condition else None

        # The remaining parts form the player's name
        if is_double_or_triple:
            # Remove the stat type (e.g., "Player Double Double" or "Player Triple Double") from the description
            player_name = description.replace("Player Double Double", "").replace("Player Triple Double", "").strip()
        else:
            player_name = " ".join(parts[:-2])  # Everything before the last two parts

        # Determine the stat type(s)
        stat_types = []
        if "Points" in bet_type:
            stat_types.append("Points")
        if "Rebounds" in bet_type:
            stat_types.append("Rebounds")
        if "Assists" in bet_type:
            stat_types.append("Assists")
        if "Steals" in bet_type:
            stat_types.append("Steals")
        if "Blocks" in bet_type:
            stat_types.append("Blocks")
        if "Turnovers" in bet_type:
            stat_types.append("Turnovers")
        if "Made Threes" in bet_type or "Three Pointers Made" in bet_type:
            stat_types.append("Made Threes")
        
        # Special case for Double Double and Triple Double
        if "Double Double" in bet_type:
            stat_types.append("Double Double")
        if "Triple Double" in bet_type:
            stat_types.append("Triple Double")

        if not stat_types:
            raise ValueError(f"Invalid or unrecognized stat type in bet_type: {bet_type}")

        logging.debug(f"Parsed bet details - Player: {player_name}, Stats: {stat_types}, Condition: {condition}, Target: {target_value}")
        return player_name, stat_types, condition, target_value

    except Exception as e:
        logging.error(f"Error parsing bet details - Description: {description}, Bet Type: {bet_type} - {e}", exc_info=True)
        return None, None, None, None

def update_bet_results():
    cleanup_logs(log_file)

    conn = connect_db()
    cursor = conn.cursor()

    query = """
        SELECT id, bet_id, event_teams, event_time, bet_type, description
        FROM betting_data
        WHERE result NOT IN ('W', 'L', 'R')
        AND sport_league LIKE '%NBA%'
        AND bet_type LIKE 'Player%'
    """
    cursor.execute(query)
    bets = cursor.fetchall()

    for bet in bets:
        bet_id, event_teams, event_time, bet_type, description = bet[1:6]
        logging.debug(f"Processing bet: {bet_id}, Type: {bet_type}, Desc: {description}")

        # Parse bet details
        player_name, stat_types, condition, target_value = parse_bet_details(description, bet_type)
        if not player_name or not stat_types:
            logging.warning(f"Failed to parse bet details for bet: {bet_id}, Desc: {description}")
            continue

        # Find game
        game_id = find_game_id(cursor, event_teams, event_time)
        if not game_id:
            logging.warning(f"Game not found for bet: {bet_id}, Teams: {event_teams}, Time: {event_time}")
            continue

        # Fetch player stats
        player_stats = fetch_player_stats(cursor, game_id, player_name)
        if player_stats is None:
            # Player stats not found; refund the bet
            logging.debug(f"Stats not found for player: {player_name} in game: {game_id}")
            cursor.execute("UPDATE betting_data SET result = ? WHERE bet_id = ?", ("R", bet_id))
            conn.commit()
            logging.info(f"Updated result for bet: {bet_id} to R (Refunded)")
            continue

        logging.debug(f"Fetched player stats for {player_name} in game {game_id}: {player_stats}")

        # Determine result
        try:
            result = determine_result(player_stats, stat_types, condition, target_value)
            logging.debug(f"Determined result for bet: {bet_id}, Result: {result}")
        except Exception as e:
            logging.error(f"Error determining result for bet: {bet_id} - {e}", exc_info=True)
            continue

        # Update result in database
        cursor.execute("UPDATE betting_data SET result = ? WHERE bet_id = ?", (result, bet_id))
        conn.commit()
        logging.info(f"Updated result for bet: {bet_id} to {result}")

    conn.close()
    logging.info("Bet results update completed.")

if __name__ == "__main__":
    update_bet_results()
