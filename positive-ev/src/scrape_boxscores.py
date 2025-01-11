import os
import hashlib
import sqlite3
import logging
from datetime import datetime
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
    level=logging.DEBUG,  # Set to DEBUG for detailed logging
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def connect_db():
    logging.debug("Connecting to SQLite database...")
    conn = sqlite3.connect(db_file)
    logging.debug("Connected to SQLite database.")
    return conn

def create_tables():
    logging.debug("Creating database tables if they don't exist...")
    conn = connect_db()
    cursor = conn.cursor()

    # Update schema for game_boxscores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_boxscores (
            game_id TEXT PRIMARY KEY,
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
            plus_minus REAL  -- Updated for float values
        )
    """)

    # Update schema for player_boxscores
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
            plus_minus REAL,  -- Updated for float values
            FOREIGN KEY (game_id) REFERENCES game_boxscores (game_id)
        )
    """)

    conn.commit()
    conn.close()
    logging.debug("Database tables created.")

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
    game_ids = [game[2] for game in data["resultSets"][0]["rowSet"]]
    logging.info(f"Found {len(game_ids)} games for {game_date}")
    return game_ids

def fetch_boxscore(game_id):
    url = "https://stats.nba.com/stats/boxscoretraditionalv2"
    params = {
        "GameID": game_id,
        "StartPeriod": 0,
        "EndPeriod": 0
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    data = response.json()
    return data

def generate_game_id(date, team, opponent):
    """Generate a unique game ID based on the date, team, and opponent."""
    unique_string = f"{date}|{team}|{opponent}"
    return hashlib.md5(unique_string.encode()).hexdigest()

def parse_and_save_boxscore(data):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        game_data = data["resultSets"][1]["rowSet"]  # Team stats
        player_data = data["resultSets"][0]["rowSet"]  # Player stats

        logging.debug("Raw Team Data from API:")
        for team in game_data:
            logging.debug(team)

        logging.debug("Raw Player Data from API:")
        for player in player_data:
            logging.debug(player)

        # Parse team stats
        for team in game_data:
            try:
                team_name = team[4]  # Full team name
                date = datetime.now().strftime("%Y-%m-%d")
                quarters = [int(team[8] or 0), int(team[9] or 0), int(team[10] or 0), int(team[11] or 0)]
                first_half = sum(quarters[:2])
                second_half = sum(quarters[2:])
                total_score = sum(quarters)

                # Find opponent
                opponent_row = next(
                    (t for t in game_data if t[4] != team_name), None
                )
                opponent_name = opponent_row[4] if opponent_row else "Unknown"

                # Generate game ID
                game_id = generate_game_id(date, team_name, opponent_name)

                logging.debug(f"Extracted Team Data: Game ID: {game_id}, Team: {team_name}, "
                              f"Opponent: {opponent_name}, Quarters: {quarters}, "
                              f"First Half: {first_half}, Second Half: {second_half}, Total Score: {total_score}")

                # Insert or update team data
                cursor.execute("""
                    INSERT OR REPLACE INTO game_boxscores (
                        game_id, game_date, team, opponent, quarter_1, quarter_2, quarter_3, quarter_4,
                        first_half, second_half, total_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game_id, date, team_name, opponent_name,
                    quarters[0], quarters[1], quarters[2], quarters[3],
                    first_half, second_half, total_score
                ))

            except Exception as e:
                logging.error(f"Error processing team data: {team} - {e}")

        # Parse player stats
        for player in player_data:
            try:
                team_abbr = player[2]  # Team abbreviation
                team_name = next((t[4] for t in game_data if t[3] == team_abbr), None)
                if not team_name:
                    logging.error(f"Could not match team abbreviation {team_abbr} to team name. Skipping player.")
                    continue

                opponent_name = next(
                    (t[4] for t in game_data if t[4] != team_name), None
                )

                game_id = generate_game_id(date, team_name, opponent_name)

                player_name = player[5]
                points = int(player[26] or 0)
                rebounds = int(player[20] or 0)
                assists = int(player[21] or 0)
                steals = int(player[22] or 0)
                blocks = int(player[23] or 0)
                turnovers = int(player[24] or 0)
                made_threes = int(player[11] or 0)

                logging.debug(f"Extracted Player Data: Game ID: {game_id}, Player: {player_name}, "
                              f"Points: {points}, Rebounds: {rebounds}, Assists: {assists}, "
                              f"Steals: {steals}, Blocks: {blocks}, Turnovers: {turnovers}, "
                              f"Made Threes: {made_threes}")

                # Insert or update player data
                cursor.execute("""
                    INSERT OR REPLACE INTO player_boxscores (
                        game_id, player_name, points, rebounds, assists, steals, blocks, turnovers,
                        made_threes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game_id, player_name, points, rebounds, assists, steals, blocks, turnovers,
                    made_threes
                ))

            except Exception as e:
                logging.error(f"Error processing player data: {player} - {e}")

        conn.commit()
        logging.info("Data successfully saved to database.")

    except Exception as e:
        logging.error(f"Error saving data: {e}", exc_info=True)

    finally:
        conn.close()

def main(game_date):
    create_tables()
    try:
        game_ids = fetch_game_ids(game_date)
        if not game_ids:
            logging.warning("No games found for the specified date.")
            return

        for game_id in game_ids:
            logging.info(f"Fetching boxscore for Game ID: {game_id}")
            data = fetch_boxscore(game_id)
            parse_and_save_boxscore(data)
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    game_date = "2024-12-31"
    main(game_date)
