import os
import logging
import sqlite3
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import hashlib
import shutil

# Define folder structure
base_dir = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev"
db_file = os.path.join(base_dir, "betting_data.db")
logs_folder = os.path.join(base_dir, "logs")
backup_folder = os.path.join(base_dir, "backups")

# Create folders if they don't exist
os.makedirs(logs_folder, exist_ok=True)
os.makedirs(backup_folder, exist_ok=True)

# Set up logging
log_file = os.path.join(logs_folder, "scraping.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Function to connect to SQLite
def connect_db():
    conn = sqlite3.connect(db_file)
    return conn

# Function to create the table
def create_table():
    conn = connect_db()
    cursor = conn.cursor()
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

# Function to create a daily backup of the SQLite database
def create_daily_backup():
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%m%d%y")
        backup_file = os.path.join(backup_folder, f"betting_data_{yesterday}.db")
        if not os.path.exists(backup_file):
            shutil.copy(db_file, backup_file)
            logging.info(f"Database backup created: {backup_file}")
        else:
            logging.info(f"Backup already exists for {yesterday}: {backup_file}")
    except Exception as e:
        logging.error(f"Error creating database backup: {e}", exc_info=True)

# Function to clean up old backups
def cleanup_old_backups():
    """Delete backups older than 30 days."""
    try:
        cutoff_date = datetime.now() - timedelta(days=30)
        for filename in os.listdir(backup_folder):
            file_path = os.path.join(backup_folder, filename)
            if os.path.isfile(file_path):
                try:
                    # Extract the date from the filename (assuming 'betting_data_MMDDYY.db' format)
                    date_part = filename.split("_")[1].split(".")[0]
                    file_date = datetime.strptime(date_part, "%m%d%y")
                    if file_date < cutoff_date:
                        os.remove(file_path)
                        logging.info(f"Deleted old backup: {file_path}")
                except (IndexError, ValueError) as e:
                    logging.warning(f"Skipping non-standard backup file: {filename} - Error: {e}")
    except Exception as e:
        logging.error(f"Failed to clean up old backups: {e}", exc_info=True)

# Helper function to generate a bet ID
def generate_bet_id(event_time, event_teams, sport_league, bet_type, description):
    """Generate a hash-based bet ID."""
    unique_string = f"{event_time}|{event_teams}|{sport_league}|{bet_type}|{description}"
    return hashlib.md5(unique_string.encode()).hexdigest()

# Function to insert or update data
def upsert_data(data):
    conn = connect_db()
    cursor = conn.cursor()

    for row in data:
        cursor.execute("""
            INSERT INTO betting_data (
                bet_id, timestamp, ev_percent, event_time, event_teams,
                sport_league, bet_type, description, odds, sportsbook,
                bet_size, win_probability, result
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["bet_id"], row["timestamp"], row["EV Percent"], row["Event Time"],
            row["Event Teams"], row["Sport/League"], row["Bet Type"], row["Description"],
            row["Odds"], row["Sportsbook"], row["Bet Size"], row["Win Probability"], ""
        ))
    conn.commit()
    conn.close()

# Function to clean up log file
def cleanup_logs(log_file):
    """Keep only the log entries from the past 2 hours."""
    try:
        if os.path.exists(log_file):
            two_hours_ago = datetime.now() - timedelta(hours=2)
            with open(log_file, "r") as file:
                lines = file.readlines()

            # Filter out entries older than 2 hours
            recent_lines = []
            for line in lines:
                try:
                    log_time_str = line.split(" - ")[0]
                    log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S,%f")
                    if log_time >= two_hours_ago:
                        recent_lines.append(line)
                except Exception as e:
                    logging.warning(f"Malformed log line ignored: {line.strip()} - Error: {e}")
                    continue

            # Overwrite the log file with recent entries
            with open(log_file, "w") as file:
                file.writelines(recent_lines)
            logging.info("Log file cleaned up. Only recent entries retained.")
    except Exception as e:
        logging.error(f"Failed to clean up log file: {e}", exc_info=True)

# Main script logic
try:
    # Initialize database and clean up logs
    create_table()
    cleanup_logs(log_file)

    # Cleanup old backups
    cleanup_old_backups()

    # Create daily backup if it's the first run of the day
    if os.path.exists(db_file):
        create_daily_backup()

    # Set up Chrome options
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")
    options.add_argument(f"user-data-dir={os.path.expanduser('~/Library/Application Support/Google/Chrome/ScraperProfile')}")

    # Initialize WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Navigate to the target page
    url = "https://oddsjam.com/betting-tools/positive-ev"
    driver.get(url)
    logging.info("Navigated to OddsJam Positive EV page.")

    # Allow time for the page to load fully
    time.sleep(10)

    # Scrape the page source
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")

    # Parse and upsert data (parse_cleaned_data function to be implemented)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    odds_data = []  # Replace with the result of parse_cleaned_data(soup, timestamp)
    if odds_data:
        logging.info(f"Extracted {len(odds_data)} rows of data.")
        upsert_data(odds_data)
    else:
        logging.warning("No data was extracted from the page.")

except Exception as e:
    logging.error(f"An error occurred: {e}", exc_info=True)
finally:
    if 'driver' in locals():
        driver.quit()
    logging.info("Browser closed.")
