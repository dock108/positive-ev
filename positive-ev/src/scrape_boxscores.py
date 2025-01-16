import os
import sqlite3
import logging
from datetime import datetime, timedelta
import requests

# Database file path
db_file = "betting_data.db"

# NBA Stats API Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nba.com"
}

# Logs folder and log file
logs_folder = "logs"
log_file = os.path.join(logs_folder, "nba_stats_scraping.log")

# Create folders if they don't exist
os.makedirs(logs_folder, exist_ok=True)

# Set up logging
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def connect_db():
    conn = sqlite3.connect(db_file)
    return conn

def get_latest_date_from_db():
    """Fetch the latest game_date from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT MAX(game_date) FROM game_boxscores")
        result = cursor.fetchone()
        if result and result[0]:
            latest_date = datetime.strptime(result[0], "%Y-%m-%d")
            logging.info(f"Latest date in database: {latest_date.strftime('%Y-%m-%d')}")
            return latest_date
        else:
            logging.info("No dates found in database. Defaulting to start date.")
            return datetime(2025, 1, 1)  # Default start date
    except Exception as e:
        logging.error(f"Error fetching latest date from database: {e}", exc_info=True)
        return datetime(2025, 1, 1)  # Default start date
    finally:
        conn.close()

def create_tables():
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

    conn.commit()
    conn.close()

def fetch_game_ids(game_date):
    url = "https://stats.nba.com/stats/scoreboardv2"
    params = {
        "GameDate": game_date,
        "LeagueID": "00",
        "DayOffset": 0
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    return [game[2] for game in data["resultSets"][0]["rowSet"]]

def fetch_boxscore_with_quarters(game_id):
    summary_url = "https://stats.nba.com/stats/boxscoresummaryv2"
    boxscore_url = "https://stats.nba.com/stats/boxscoretraditionalv2"

    summary_response = requests.get(summary_url, headers=HEADERS, params={"GameID": game_id})
    summary_response.raise_for_status()
    summary_data = summary_response.json()

    boxscore_response = requests.get(boxscore_url, headers=HEADERS, params={"GameID": game_id, "StartPeriod": 0, "EndPeriod": 0})
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

def main(game_date):
    create_tables()
    try:
        game_ids = fetch_game_ids(game_date)
        for game_id in game_ids:
            boxscore_data, summary_data = fetch_boxscore_with_quarters(game_id)
            parse_and_save_boxscore(boxscore_data, summary_data)
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    latest_date = get_latest_date_from_db()
    start_date = latest_date + timedelta(days=1)
    end_date = datetime.now()

    current_date = start_date
    while current_date <= end_date:
        main(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
