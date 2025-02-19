import os
import sqlite3
import logging
import argparse
from datetime import datetime, timedelta
import requests
from config import (
    DB_FILE, LOGS_FOLDER, NBA_STATS_LOG_FILE,
    NBA_HEADERS, NBA_STATS_URLS, LOG_RETENTION_HOURS
)
from utils import (
    cleanup_logs, connect_db, create_tables,
    get_latest_date_from_db
)

# Create folders if they don't exist
os.makedirs(LOGS_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(
    filename=NBA_STATS_LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def fetch_game_ids(game_date):
    url = NBA_STATS_URLS["scoreboard"]
    params = {
        "GameDate": game_date,
        "LeagueID": "00",
        "DayOffset": 0
    }
    response = requests.get(url, headers=NBA_HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    return [game[2] for game in data["resultSets"][0]["rowSet"]]

def fetch_boxscore_with_quarters(game_id):
    summary_url = NBA_STATS_URLS["summary"]
    boxscore_url = NBA_STATS_URLS["boxscore"]

    summary_response = requests.get(summary_url, headers=NBA_HEADERS, params={"GameID": game_id})
    summary_response.raise_for_status()
    summary_data = summary_response.json()

    boxscore_response = requests.get(boxscore_url, headers=NBA_HEADERS, params={"GameID": game_id, "StartPeriod": 0, "EndPeriod": 0})
    boxscore_response.raise_for_status()
    boxscore_data = boxscore_response.json()

    return boxscore_data, summary_data

def parse_and_save_boxscore(boxscore_data, summary_data):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Extract game date
        game_date = summary_data["resultSets"][0]["rowSet"][0][
            summary_data["resultSets"][0]["headers"].index("GAME_DATE_EST")
        ]

        # Extract home and away team IDs
        game_summary = next(
            (result for result in summary_data["resultSets"] if result["name"] == "GameSummary"), None
        )
        if not game_summary:
            logging.error("GameSummary data not found in summary.")
            return

        game_summary_data = game_summary["rowSet"][0]
        game_summary_headers = game_summary["headers"]

        home_team_id = game_summary_data[game_summary_headers.index("HOME_TEAM_ID")]
        visitor_team_id = game_summary_data[game_summary_headers.index("VISITOR_TEAM_ID")]

        # Extract LineScore data
        line_score = next(
            (result for result in summary_data["resultSets"] if result["name"] == "LineScore"), None
        )
        if not line_score:
            logging.warning("No LineScore data found in summary.")
            return

        quarter_headers = line_score["headers"]
        quarter_data = line_score["rowSet"]

        logging.debug(f"Quarter Headers: {quarter_headers}")
        logging.debug(f"Quarter Data: {quarter_data}")

        # Save line score (team data)
        for row in quarter_data:
            game_id = row[quarter_headers.index("GAME_ID")]
            team_id = row[quarter_headers.index("TEAM_ID")]
            is_home = team_id == home_team_id
            home_away = "H" if is_home else "A"

            opponent_row = next(
                (r for r in quarter_data if r[quarter_headers.index("GAME_ID")] == game_id and r != row), None
            )
            opponent = opponent_row[quarter_headers.index("TEAM_CITY_NAME")] if opponent_row else "Unknown"

            quarter_scores = [
                row[quarter_headers.index(f"PTS_QTR{i}")] for i in range(1, 5)
            ]

            # Check if game is still live
            if any(score is None for score in quarter_scores) or any(score < 5 for score in quarter_scores):
                logging.warning(f"Skipping game {game_id} as it is still in progress.")
                logging.debug(f"Game Details: game_id={game_id}, quarter_scores={quarter_scores}, home_team_id={home_team_id}, visitor_team_id={visitor_team_id}, game_date={game_date}")
                continue

            first_half = sum(quarter_scores[:2])
            second_half = sum(quarter_scores[2:])
            total_score = row[quarter_headers.index("PTS")]

            # Insert or update the game boxscore
            cursor.execute("""
                INSERT OR REPLACE INTO game_boxscores (
                    game_id, home_away, game_date, team, opponent, quarter_1, quarter_2,
                    quarter_3, quarter_4, first_half, second_half, total_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_id, home_away, game_date[:10],  # Only take the date part
                row[quarter_headers.index("TEAM_CITY_NAME")], opponent,
                quarter_scores[0], quarter_scores[1], quarter_scores[2], quarter_scores[3],
                first_half, second_half, total_score
            ))

        # Save player data
        player_headers = boxscore_data["resultSets"][0]["headers"]
        player_data = boxscore_data["resultSets"][0]["rowSet"]

        for player in player_data:
            game_id = player[player_headers.index("GAME_ID")]
            player_name = player[player_headers.index("PLAYER_NAME")]
            points = player[player_headers.index("PTS")]
            rebounds = player[player_headers.index("REB")]
            assists = player[player_headers.index("AST")]
            steals = player[player_headers.index("STL")]
            blocks = player[player_headers.index("BLK")]
            turnovers = player[player_headers.index("TO")]
            made_threes = player[player_headers.index("FG3M")]

            cursor.execute("""
                INSERT OR REPLACE INTO player_boxscores (
                    game_id, player_name, points, rebounds, assists, steals, blocks, turnovers, made_threes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_id, player_name, points, rebounds, assists, steals, blocks, turnovers, made_threes
            ))

        conn.commit()

    except Exception as e:
        logging.error(f"Error parsing and saving boxscore: {e}", exc_info=True)

    finally:
        conn.close()

def main(game_date, force_reload=False):
    """
    Main function to scrape and save NBA boxscores.
    
    Args:
        game_date (str): Date to scrape in YYYY-MM-DD format
        force_reload (bool): If True, ignore latest date and start from season beginning
    """
    create_tables()
    try:
        game_ids = fetch_game_ids(game_date)
        for game_id in game_ids:
            boxscore_data, summary_data = fetch_boxscore_with_quarters(game_id)
            parse_and_save_boxscore(boxscore_data, summary_data)
        logging.info(f"Scraping completed for {game_date}")
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Scrape NBA boxscores')
    parser.add_argument('--reload', action='store_true', 
                       help='Reload all data from the start of the season')
    args = parser.parse_args()
    
    cleanup_logs(NBA_STATS_LOG_FILE)
    
    if args.reload:
        # Start from beginning of season if reload flag is set
        start_date = datetime(2024, 10, 1)
        logging.info("Reload flag set - Starting from beginning of season")
    else:
        # Get the latest date with a result from the database
        latest_date = get_latest_date_from_db("game_boxscores", "game_date")
        # Set the start date to one day before the latest date in the database
        start_date = latest_date - timedelta(days=1)
    
    # Set the end date to today (not including today)
    end_date = datetime.now() - timedelta(days=1)
    
    # Log the date range
    logging.info(f"Updating results from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.")
    
    current_date = start_date
    while current_date <= end_date:
        main(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
