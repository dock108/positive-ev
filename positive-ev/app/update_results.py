import os
import logging
from datetime import datetime
from config import (
    LOGS_FOLDER, RESULTS_UPDATE_LOG_FILE,
    TEAM_NORMALIZATION_MAP, STATS_MAPPING
)
from utils import (
    cleanup_logs, connect_db, create_tables,
    get_latest_date_from_db
)

# Create folders if they don't exist
os.makedirs(LOGS_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(
    filename=RESULTS_UPDATE_LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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
    """Normalize team names using the team normalization map."""
    return TEAM_NORMALIZATION_MAP.get(team_name.strip(), team_name.strip())

def extract_and_normalize_teams(event_teams):
    """Extract and normalize team names from the event_teams string."""
    teams = [normalize_team_name(team.strip()) for team in event_teams.split("vs")]
    logging.debug(f"Extracted and normalized teams: {teams}")
    return teams if len(teams) == 2 else None

def find_game_id(cursor, event_teams, event_time):
    """Find the game ID in the database matching the event teams and event time."""
    try:
        teams = extract_and_normalize_teams(event_teams)
        if not teams:
            logging.warning(f"Invalid event_teams format: {event_teams}")
            return None

        try:
            parsed_date = datetime.strptime(event_time.split(" at")[0].strip(), "%a, %b %d")
            current_year = datetime.now().year
            event_datetime = parsed_date.replace(year=current_year)
            event_date = event_datetime.strftime("%Y-%m-%d")
        except ValueError as e:
            logging.error(f"Error parsing event_time: {event_time} - {e}")
            return None

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
            logging.debug(f"No game found for teams: {teams} on date: {event_date}")
            return None

    except Exception as e:
        logging.error(f"Error in find_game_id: {e}", exc_info=True)
        return None

def determine_result(player_stats, stat_types, condition, target_value):
    """Determine the result (W, L, or R) based on player stats."""
    try:
        logging.debug(f"Player stats: {player_stats}, Stat types: {stat_types}, Condition: {condition}, Target: {target_value}")

        if "Double Double" in stat_types or "Triple Double" in stat_types:
            double_stats = sum(1 for i, stat in enumerate(player_stats) if stat >= 10 and i < 6)
            logging.debug(f"Double/Triple Double count: {double_stats}")
            
            if "Triple Double" in stat_types:
                return "W" if double_stats >= 3 else "L"
            elif "Double Double" in stat_types:
                return "W" if double_stats >= 2 else "L"

        if any(player_stats[STATS_MAPPING[stat]] is None for stat in stat_types):
            logging.debug("Player stats contain None values. Player likely did not play. Result: R")
            return "R"
        
        actual_value = sum(player_stats[STATS_MAPPING[stat]] for stat in stat_types)
        logging.debug(f"Calculated actual value for {stat_types}: {actual_value}")

        # Check for exact match first (should be a push/refund)
        if actual_value == target_value:
            logging.debug("Actual value matches target value. Result: R")
            return "R"
        
        # Then check over/under conditions
        if condition == "Over":
            return "W" if actual_value > target_value else "L"
        elif condition == "Under":
            return "W" if actual_value < target_value else "L"
        else:
            logging.debug("No matching condition found. Falling back to Result: L")
            return "L"
    except Exception as e:
        logging.error(f"Error calculating result: {e}", exc_info=True)
        return None

def parse_bet_details(description, bet_type):
    """Parse bet details from description and bet type."""
    try:
        parts = description.split()
        is_double_or_triple = "Double Double" in bet_type or "Triple Double" in bet_type
        
        condition = parts[-2] if not is_double_or_triple else None
        target_value = float(parts[-1]) if condition else None

        if is_double_or_triple:
            player_name = description.replace("Player Double Double", "").replace("Player Triple Double", "").strip()
        else:
            player_name = " ".join(parts[:-2])

        stat_types = []
        for stat in ["Points", "Rebounds", "Assists", "Steals", "Blocks", "Turnovers"]:
            if stat in bet_type:
                stat_types.append(stat)
        if "Made Threes" in bet_type or "Three Pointers Made" in bet_type:
            stat_types.append("Made Threes")
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
    """Update results for all unresolved NBA player bets."""
    conn = connect_db()
    cursor = conn.cursor()

    today = datetime.now()
    today_formatted = today.strftime("%a, %b %d")

    query = f"""
        SELECT id, bet_id, event_teams, event_time, bet_type, description
        FROM betting_data
        WHERE result NOT IN ('W', 'L', 'R')
        AND sport_league LIKE '%NBA%'
        AND bet_type LIKE 'Player%'
        AND DATE(event_time, 'unixepoch') < DATE('{today_formatted}')
    """
    cursor.execute(query)
    bets = cursor.fetchall()

    for bet in bets:
        bet_id, event_teams, event_time, bet_type, description = bet[1:6]
        logging.debug(f"Processing bet: {bet_id}, Type: {bet_type}, Desc: {description}")

        player_name, stat_types, condition, target_value = parse_bet_details(description, bet_type)
        if not player_name or not stat_types:
            continue

        game_id = find_game_id(cursor, event_teams, event_time)
        if not game_id:
            continue

        player_stats = fetch_player_stats(cursor, game_id, player_name)
        if player_stats is None:
            cursor.execute("UPDATE betting_data SET result = ? WHERE bet_id = ?", ("R", bet_id))
            conn.commit()
            logging.info(f"Updated result for bet: {bet_id} to R")
            continue

        try:
            result = determine_result(player_stats, stat_types, condition, target_value)
            if result:
                cursor.execute("UPDATE betting_data SET result = ? WHERE bet_id = ?", (result, bet_id))
                conn.commit()
                logging.info(f"Updated result for bet: {bet_id} to {result}")
        except Exception as e:
            logging.error(f"Error determining result for bet: {bet_id} - {e}", exc_info=True)

    conn.close()
    logging.info("Bet results update completed.")

if __name__ == "__main__":
    create_tables()  # Ensure all tables exist
    cleanup_logs(RESULTS_UPDATE_LOG_FILE)
    update_bet_results()
