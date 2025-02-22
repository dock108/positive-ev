import os
import time
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import shutil
from config import (
    DB_FILE, LOGS_FOLDER, BACKUP_FOLDER, LOG_FILE,
    CHROME_PROFILE, TARGET_URL, PAGE_LOAD_WAIT,
    BACKUP_RETENTION_DAYS, CHROME_OPTIONS, 
    SELECTORS
)
from utils import (
    cleanup_logs, connect_db, fix_event_time,
    generate_bet_id, create_tables
)

# Create folders if they don't exist
os.makedirs(LOGS_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Function to create a daily backup of the SQLite database
def create_daily_backup():
    try:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%m%d%y")
        backup_file = os.path.join(BACKUP_FOLDER, f"betting_data_{yesterday}.db")
        if not os.path.exists(backup_file):
            shutil.copy(DB_FILE, backup_file)
            logging.info(f"Database backup created: {backup_file}")
        else:
            logging.info(f"Backup already exists for {yesterday}: {backup_file}")
    except Exception as e:
        logging.error(f"Error creating database backup: {e}", exc_info=True)

# Function to clean up old backups
def cleanup_old_backups():
    """Delete backups older than BACKUP_RETENTION_DAYS."""
    try:
        cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
        for filename in os.listdir(BACKUP_FOLDER):
            file_path = os.path.join(BACKUP_FOLDER, filename)
            if os.path.isfile(file_path):
                # Ensure the filename follows the expected pattern
                if filename.startswith("betting_data_") and filename.endswith(".db"):
                    try:
                        # Extract the date from the filename (assuming 'betting_data_MMDDYY.db' format)
                        date_part = filename.replace("betting_data_", "").replace(".db", "")
                        file_date = datetime.strptime(date_part, "%m%d%y")
                        if file_date < cutoff_date:
                            os.remove(file_path)
                            logging.info(f"Deleted old backup: {file_path}")
                    except ValueError as e:
                        logging.warning(f"Skipping invalid backup file: {filename} - Error: {e}")
    except Exception as e:
        logging.error(f"Failed to clean up old backups: {e}", exc_info=True)

# Parsing function
def parse_cleaned_data(soup, timestamp):
    """Parse data grouped by bet blocks."""
    try:
        bet_blocks = soup.select(SELECTORS['bet_blocks'])
        logging.info(f"Found {len(bet_blocks)} bet blocks.")

        data = []
        for index, block in enumerate(bet_blocks):
            logging.debug(f"Parsing Bet Block {index}")
            row = {"timestamp": timestamp}

            try:
                # Extract data using configured selectors
                ev_percent = block.select_one(SELECTORS['ev_percent'])
                row["EV Percent"] = ev_percent.text.strip('%') if ev_percent else "N/A"

                event_time = block.select_one(SELECTORS['event_time'])
                raw_event_time = event_time.text.strip() if event_time else "N/A"
                row["Event Time"] = fix_event_time(raw_event_time, timestamp)

                event_teams = block.select_one(SELECTORS['event_teams'])
                row["Event Teams"] = event_teams.text.strip() if event_teams else "N/A"

                sport_league = block.select_one(SELECTORS['sport_league'])
                row["Sport/League"] = sport_league.text.strip() if sport_league else "N/A"

                bet_type = block.select_one(SELECTORS['bet_type'])
                row["Bet Type"] = bet_type.text.strip() if bet_type else "N/A"

                description = block.select_one(SELECTORS['description'])
                row["Description"] = description.text.strip() if description else "N/A"

                odds = block.select_one(SELECTORS['odds'])
                row["Odds"] = odds.text.strip() if odds else "N/A"

                sportsbook_logo = block.select_one(SELECTORS['sportsbook'])
                row["Sportsbook"] = sportsbook_logo["alt"].strip() if sportsbook_logo else "N/A"

                bet_size = block.select_one(SELECTORS['bet_size'])
                logging.debug(f"Raw bet_size element: {bet_size}")
                if bet_size:
                    logging.debug(f"Raw bet_size text: '{bet_size.text}'")
                    stripped_text = bet_size.text.strip()
                    logging.debug(f"Stripped bet_size: '{stripped_text}'")
                    
                    if stripped_text != 'N/A':
                        # Remove currency symbol, commas, and whitespace, then convert to float
                        cleaned_value = stripped_text.replace('$', '').replace(',', '').strip()
                        logging.debug(f"Cleaned bet_size value: '{cleaned_value}'")
                        row["Bet Size"] = cleaned_value if cleaned_value else "N/A"
                    else:
                        logging.debug("Bet size is 'N/A'")
                        row["Bet Size"] = "N/A"
                else:
                    logging.debug("No bet_size element found")
                    row["Bet Size"] = "N/A"

                win_probability = block.select_one(SELECTORS['win_probability'])
                row["Win Probability"] = win_probability.text.strip('%') if win_probability else "N/A"

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

# Function to insert or update data
def upsert_data(data):
    conn = connect_db()
    cursor = conn.cursor()

    for row in data:
        cursor.execute("""
            INSERT INTO betting_data (
                bet_id, timestamp, ev_percent, event_time, event_teams,
                sport_league, bet_type, description, odds, sportsbook,
                bet_size, win_probability
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["bet_id"], row["timestamp"], row["EV Percent"], row["Event Time"],
            row["Event Teams"], row["Sport/League"], row["Bet Type"], row["Description"],
            row["Odds"], row["Sportsbook"], row["Bet Size"], row["Win Probability"]
        ))
    conn.commit()
    conn.close()

# Main script logic
def main():
    try:
        create_tables()  # Now using the utility function
        cleanup_logs(LOG_FILE)
        cleanup_old_backups()

        if os.path.exists(DB_FILE):
            create_daily_backup()

        driver = setup_chrome_driver()
        
        try:
            driver.get(TARGET_URL)
            logging.info("Navigated to OddsJam Positive EV page.")
            
            time.sleep(PAGE_LOAD_WAIT)
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            odds_data = parse_cleaned_data(soup, timestamp)
            
            if odds_data:
                logging.info(f"Extracted {len(odds_data)} rows of data.")
                upsert_data(odds_data)
            else:
                logging.warning("No data was extracted from the page.")
                
        finally:
            driver.quit()
            logging.info("Browser closed.")
            
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)

def setup_chrome_driver():
    """Initialize and configure Chrome WebDriver."""
    options = Options()
    for option in CHROME_OPTIONS:
        options.add_argument(option)
    options.add_argument(f"user-data-dir={CHROME_PROFILE}")
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

if __name__ == "__main__":
    main()
