import os
import time
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

# Helper function to generate a bet ID
def generate_bet_id(event_time, event_teams, sport_league, bet_type, description):
    """Generate a hash-based bet ID."""
    unique_string = f"{event_time}|{event_teams}|{sport_league}|{bet_type}|{description}"
    return hashlib.md5(unique_string.encode()).hexdigest()

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

def fix_event_time(event_time):
    """Fix relative Event Time terms like 'Today at' and 'Tomorrow at' to absolute dates."""
    try:
        now = datetime.now()
        if "Today at" in event_time:
            # Replace "Today" with the current date
            event_time = event_time.replace("Today", now.strftime("%a, %b %-d"))
        elif "Tomorrow at" in event_time:
            # Replace "Tomorrow" with the next day's date
            tomorrow = now + timedelta(days=1)
            event_time = event_time.replace("Tomorrow", tomorrow.strftime("%a, %b %-d"))
        elif " at " in event_time:
            # Handle weekday-based references like "Sunday at"
            day_name = event_time.split(" at")[0]
            target_date = None
            for i in range(7):
                candidate_date = now + timedelta(days=i)
                if candidate_date.strftime("%a") == day_name:
                    target_date = candidate_date
                    break
            if target_date:
                event_time = event_time.replace(
                    f"{day_name} at", target_date.strftime("%a, %b %-d at")
                )
        # Return the fixed event time
        return event_time
    except Exception as e:
        logging.warning(f"Failed to fix Event Time: {event_time} due to {e}")
        return event_time

# Parsing function
def parse_cleaned_data(soup, timestamp):
    """Parse data grouped by bet blocks."""
    try:
        # Select all bet blocks from the page
        bet_blocks = soup.select("div#betting-tool-table-row")
        logging.info(f"Selector 'div#betting-tool-table-row' found {len(bet_blocks)} bet blocks.")

        data = []
        for index, block in enumerate(bet_blocks):
            logging.debug(f"Parsing Bet Block {index}")
            row = {"timestamp": timestamp}

            try:
                # Extract data points
                ev_percent = block.select_one("p#percent-cell")
                row["EV Percent"] = ev_percent.text.strip('%') if ev_percent else "N/A"

                event_time = block.select_one("div[data-testid='event-cell'] > p.text-xs")
                raw_event_time = event_time.text.strip() if event_time else "N/A"
                row["Event Time"] = fix_event_time(raw_event_time)

                event_teams = block.select_one("p.text-sm.font-semibold")
                row["Event Teams"] = event_teams.text.strip() if event_teams else "N/A"

                sport_league = block.select_one("p.text-sm:not(.font-semibold)")
                row["Sport/League"] = sport_league.text.strip() if sport_league else "N/A"

                bet_type = block.select_one("p.text-sm.text-brand-purple")
                row["Bet Type"] = bet_type.text.strip() if bet_type else "N/A"

                description = block.select_one("div.tour__bet_and_books p.flex-1")
                row["Description"] = description.text.strip() if description else "N/A"

                odds = block.select_one("p.text-sm.font-bold")
                row["Odds"] = odds.text.strip() if odds else "N/A"

                sportsbook_logo = block.select_one("img[alt]")
                row["Sportsbook"] = sportsbook_logo["alt"].strip() if sportsbook_logo else "N/A"

                bet_size = block.select_one("p.text-sm.font-semibold.text-white")
                row["Bet Size"] = bet_size.text.strip('$') if bet_size else "N/A"

                win_probability = block.select_one("p.text-sm.text-white")
                row["Win Probability"] = win_probability.text.strip('%') if win_probability else "N/A"

                row["Result"] = ""  # Default value

                # Generate bet ID
                row["bet_id"] = generate_bet_id(
                    row["Event Time"], row["Event Teams"],
                    row["Sport/League"], row["Bet Type"], row["Description"]
                )

                logging.info(f"Extracted Row {index}: {row}")
                data.append(row)
            except Exception as e:
                logging.warning(f"Bet Block {index}: Failed to parse due to {e}")

        return data
    except Exception as e:
        logging.error(f"Error parsing data: {e}", exc_info=True)
        return []

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

    # Parse data and save to SQLite
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    odds_data = parse_cleaned_data(soup, timestamp)
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
