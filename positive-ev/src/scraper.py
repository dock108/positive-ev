import os
import logging
import csv
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Define folder structure
base_dir = "/Users/michaelfuscoletti/Desktop/mega_plan/mega-plan/positive-ev"
output_folder = os.path.join(base_dir, "output")
logs_folder = os.path.join(base_dir, "logs")

# Create folders if they don't exist
os.makedirs(output_folder, exist_ok=True)
os.makedirs(logs_folder, exist_ok=True)

# Set up logging
log_file = os.path.join(logs_folder, "scraping.log")
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# CSV file setup
output_file = os.path.join(output_folder, "betting_data.csv")
fieldnames = [
    "Timestamp", "EV Percent", "Event Time", "Event Teams",
    "Sport/League", "Bet Type", "Description",
    "Odds", "Sportsbook", "Bet Size", "Win Probability"
]

# If file doesn't exist, write the header
if not os.path.exists(output_file):
    with open(output_file, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

# Helper function to fix Event Time
def fix_event_time(event_time):
    """Fix relative Event Time terms to a consistent format."""
    try:
        now = datetime.now()
        if "Today at" in event_time:
            event_time = event_time.replace("Today", now.strftime("%a, %b %-d"))
        elif "Tomorrow at" in event_time:
            tomorrow = now + timedelta(days=1)
            event_time = event_time.replace("Tomorrow", tomorrow.strftime("%a, %b %-d"))
        elif " at " in event_time:
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
        return event_time
    except Exception as e:
        logging.warning(f"Failed to fix Event Time: {event_time} due to {e}")
        return event_time

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
                    print(e)
                    continue  # Ignore malformed lines

            # Overwrite the log file with recent entries
            with open(log_file, "w") as file:
                file.writelines(recent_lines)
            logging.info("Log file cleaned up. Only recent entries retained.")
    except Exception as e:
        logging.error(f"Failed to clean up log file: {e}")

# Parsing function
def parse_cleaned_data(soup, timestamp):
    """Parse data grouped by bet blocks and add timestamp."""
    try:
        bet_blocks = soup.select("div#betting-tool-table-row")
        logging.info(f"Selector 'div#betting-tool-table-row' found {len(bet_blocks)} bet blocks.")

        data = []
        for index, block in enumerate(bet_blocks):
            logging.debug(f"Parsing Bet Block {index}")
            block_content = {"Timestamp": timestamp}  # Add the timestamp to each row

            try:
                ev_percent = block.select_one("p#percent-cell")
                block_content["EV Percent"] = ev_percent.text.strip() if ev_percent else "N/A"

                event_time = block.select_one("div[data-testid='event-cell'] > p.text-xs")
                raw_event_time = event_time.text.strip() if event_time else "N/A"
                block_content["Event Time"] = fix_event_time(raw_event_time)

                event_teams = block.select_one("p.text-sm.font-semibold")
                block_content["Event Teams"] = event_teams.text.strip() if event_teams else "N/A"

                sport_league = block.select_one("p.text-sm:not(.font-semibold)")
                block_content["Sport/League"] = sport_league.text.strip() if sport_league else "N/A"

                bet_type = block.select_one("p.text-sm.text-brand-purple")
                block_content["Bet Type"] = bet_type.text.strip() if bet_type else "N/A"

                description = block.select_one("div.tour__bet_and_books p.flex-1")
                block_content["Description"] = description.text.strip() if description else "N/A"

                odds = block.select_one("p.text-sm.font-bold")
                block_content["Odds"] = odds.text.strip() if odds else "N/A"

                sportsbook_logo = block.select_one("img[alt]")
                block_content["Sportsbook"] = sportsbook_logo["alt"].strip() if sportsbook_logo else "N/A"

                bet_size = block.select_one("p.text-sm.font-semibold.text-white")
                block_content["Bet Size"] = bet_size.text.strip() if bet_size else "N/A"

                win_probability = block.select_one("p.text-sm.text-white")
                block_content["Win Probability"] = win_probability.text.strip() if win_probability else "N/A"

                logging.debug(f"Extracted Row {index}: {block_content}")
                data.append(block_content)
            except Exception as e:
                logging.warning(f"Bet Block {index}: Failed to parse due to {e}")

        return data
    except Exception as e:
        logging.error(f"Error parsing data: {e}", exc_info=True)
        return []

try:
    # Clean up old log entries
    cleanup_logs(log_file)

    # Set up Chrome options
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
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

    # Add the current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Parse data
    odds_data = parse_cleaned_data(soup, timestamp)

    # Save data to CSV
    if odds_data:
        logging.info(f"Extracted {len(odds_data)} rows of data.")
        with open(output_file, mode="a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writerows(odds_data)
    else:
        logging.warning("No data was extracted from the page.")

except Exception as e:
    logging.error(f"An error occurred: {e}", exc_info=True)
finally:
    if 'driver' in locals():
        driver.quit()
    logging.info("Browser closed.")
