import os
import sys
import time
import json
import csv
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import from src modules
from src.config import (
    TARGET_URL, PAGE_LOAD_WAIT, BACKUP_RETENTION_DAYS,
    SELECTORS, SCRAPER_LOG_FILE, BACKUP_DIR, SUPABASE_BATCH_SIZE,
    CSV_FILE, setup_logging
)
from src.common_utils import (
    cleanup_logs, fix_event_time, generate_bet_id
)
from src.supabase_client import batch_upsert
from src.chrome_utils import setup_chrome_driver

# Initialize logger
logger = setup_logging(SCRAPER_LOG_FILE, "scraper")

# Create folders if they don't exist
os.makedirs(BACKUP_DIR, exist_ok=True)

# Function to clean up old backup files
def cleanup_old_backups():
    """Delete backup files older than BACKUP_RETENTION_DAYS."""
    try:
        now = datetime.now()
        cutoff_date = now - timedelta(days=BACKUP_RETENTION_DAYS)
        count = 0
        
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith("backup_") and filename.endswith(".json"):
                # Extract the date from the filename (assuming 'backup_YYYYMMDD.json' format)
                date_part = filename.replace("backup_", "").replace(".json", "")
                try:
                    file_date = datetime.strptime(date_part, "%Y%m%d")
                    if file_date < cutoff_date:
                        file_path = os.path.join(BACKUP_DIR, filename)
                        os.remove(file_path)
                        count += 1
                except ValueError:
                    # Skip files that don't match the expected date format
                    continue
        
        if count > 0:
            logger.info(f"Deleted {count} backup files older than {BACKUP_RETENTION_DAYS} days")
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}", exc_info=True)

# Function to scrape the webpage
def scrape_webpage():
    """Scrape the EV betting data from the target website."""
    driver = None
    try:
        # Get Chrome driver from chrome_utils
        driver = setup_chrome_driver()
        
        # Navigate to target URL
        logger.info(f"Navigating to {TARGET_URL}")
        driver.get(TARGET_URL)
        
        # Wait for the page to load
        logger.info(f"Waiting {PAGE_LOAD_WAIT} seconds for page to load...")
        time.sleep(PAGE_LOAD_WAIT)
        
        # Get the page source and parse with BeautifulSoup
        logger.info("Retrieving page source...")
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Parse the data
        logger.info("Parsing bet data...")
        timestamp = datetime.now().isoformat()
        data = parse_bet_data(soup, timestamp)
        
        return data
    except Exception as e:
        logger.error(f"Error scraping webpage: {e}", exc_info=True)
        return []
    finally:
        if driver:
            driver.quit()

# Function to parse the betting data from the HTML
def parse_bet_data(soup, timestamp):
    """Extract betting data from BeautifulSoup object."""
    try:
        # Find all bet blocks
        bet_blocks = soup.select(SELECTORS['bet_blocks'])
        logger.info(f"Found {len(bet_blocks)} bet blocks")
        
        data = []
        for index, block in enumerate(bet_blocks):
            try:
                logger.debug(f"Parsing Bet Block {index}")
                
                # Initialize a row dict with timestamp
                row = {"timestamp": timestamp}
                
                # Extract ev_percent
                ev_percent = block.select_one(SELECTORS['ev_percent'])
                row["EV Percent"] = ev_percent.text.strip('%') if ev_percent else "N/A"
                
                # Extract event_time and fix format
                event_time = block.select_one(SELECTORS['event_time'])
                raw_event_time = event_time.text.strip() if event_time else "N/A"
                row["Event Time"] = fix_event_time(raw_event_time, timestamp)
                
                # Extract event_teams
                event_teams = block.select_one(SELECTORS['event_teams'])
                row["Event Teams"] = event_teams.text.strip() if event_teams else "N/A"
                
                # Extract sport_league
                sport_league = block.select_one(SELECTORS['sport_league'])
                row["Sport/League"] = sport_league.text.strip() if sport_league else "N/A"
                
                # Extract bet_type
                bet_type = block.select_one(SELECTORS['bet_type'])
                row["Bet Type"] = bet_type.text.strip() if bet_type else "N/A"
                
                # Extract description
                description = block.select_one(SELECTORS['description']) 
                row["Description"] = description.text.strip() if description else "N/A"
                
                # Extract odds
                odds = block.select_one(SELECTORS['odds'])
                row["Odds"] = odds.text.strip() if odds else "N/A"
                
                # Extract sportsbook
                sportsbook_logo = block.select_one(SELECTORS['sportsbook'])
                row["Sportsbook"] = sportsbook_logo["alt"].strip() if sportsbook_logo and "alt" in sportsbook_logo.attrs else "N/A"
                
                # Extract bet_size
                bet_size = block.select_one(SELECTORS['bet_size'])
                if bet_size:
                    stripped_text = bet_size.text.strip()
                    if stripped_text != 'N/A':
                        # Remove currency symbol, commas, and whitespace
                        cleaned_value = stripped_text.replace('$', '').replace(',', '').strip()
                        row["Bet Size"] = cleaned_value
                    else:
                        row["Bet Size"] = "N/A"
                else:
                    row["Bet Size"] = "N/A"
                
                # Extract win_probability
                win_probability = block.select_one(SELECTORS['win_probability'])
                row["Win Probability"] = win_probability.text.strip('%') if win_probability else "N/A"
                
                # Generate unique bet_id
                row["bet_id"] = generate_bet_id(
                    row["Event Time"], 
                    row["Event Teams"],
                    row["Sport/League"], 
                    row["Bet Type"], 
                    row["Description"]
                )
                
                # Generate betid_timestamp for Supabase compatibility
                row["betid_timestamp"] = f"{row['bet_id']}:{timestamp}"
                
                logger.info(f"Extracted Row {index}: {row}")
                data.append(row)
                
            except Exception as e:
                logger.warning(f"Bet Block {index}: Failed to parse due to {e}")
                
        return data
    except Exception as e:
        logger.error(f"Error parsing data: {e}", exc_info=True)
        return []

# Function to insert or update data in Supabase
def upsert_data(data):
    # Convert batch to Supabase format
    supabase_records = []
    for row in data:
        # Create record dictionary with the Supabase schema
        record = {
            "bet_id": row["bet_id"],
            "timestamp": row["timestamp"],
            "betid_timestamp": row["betid_timestamp"],
            "ev_percent": row.get("EV Percent", ""),
            "event_time": row.get("Event Time", ""),
            "home_team": "",      # Will be parsed from Event Teams
            "away_team": "",      # Will be parsed from Event Teams
            "sport": "",          # Will be parsed from Sport/League
            "league": "",         # Will be parsed from Sport/League
            "bet_type": "",       # Will be parsed from Bet Type
            "participant": "",    # Will be parsed from Description
            "bet_line": "",      # Will be parsed from Description
            "bet_category": "",   # Will be determined based on Bet Type
            "odds": row.get("Odds", ""),
            "sportsbook": row.get("Sportsbook", ""),
            "bet_size": row.get("Bet Size", ""),
            "win_probability": row.get("Win Probability", ""),
            "result": ""
        }
        
        # Parse team names from Event Teams
        event_teams = row.get("Event Teams", "")
        if event_teams and event_teams != "N/A":
            parts = event_teams.split(" vs ")
            if len(parts) >= 2:
                record["home_team"] = parts[0].strip()
                record["away_team"] = parts[1].strip()
        
        # Parse sport and league from Sport/League
        sport_league = row.get("Sport/League", "")
        if sport_league and sport_league != "N/A":
            parts = sport_league.split("|")
            if len(parts) >= 2:
                record["sport"] = parts[0].strip()
                record["league"] = parts[1].strip()
        
        # Parse bet_type and bet_category from Bet Type
        bet_type = row.get("Bet Type", "")
        if bet_type:
            # Store original bet type
            record["bet_type"] = bet_type.strip()
            
            # Determine category
            if "Player" in bet_type:
                record["bet_category"] = "Player Props"
            elif "Moneyline" in bet_type:
                record["bet_category"] = "Moneyline"
            elif "Point Spread" in bet_type or "Spread" in bet_type:
                record["bet_category"] = "Spread"
            elif "Total" in bet_type:
                record["bet_category"] = "Total"
            else:
                record["bet_category"] = "Other"

        # Parse participant and bet_line from Description
        description = row.get("Description", "")
        if description and description != "N/A":
            # Split on Over/Under if present
            if "Over" in description:
                parts = description.split("Over")
                record["participant"] = parts[0].strip()
                record["bet_line"] = f"Over {parts[1].strip()}"
            elif "Under" in description:
                parts = description.split("Under")
                record["participant"] = parts[0].strip()
                record["bet_line"] = f"Under {parts[1].strip()}"
            else:
                # For moneyline bets or other types, use the whole description
                record["participant"] = description.strip()
                record["bet_line"] = ""  # No line for moneyline bets

        # Clean up numeric fields
        if record["ev_percent"]:
            record["ev_percent"] = record["ev_percent"].replace("%", "").strip()
        if record["win_probability"]:
            record["win_probability"] = record["win_probability"].replace("%", "").strip()
        if record["bet_size"]:
            record["bet_size"] = record["bet_size"].replace("$", "").replace(",", "").strip()
        
        supabase_records.append(record)
    
    # Use the batch_upsert function from supabase.py
    batch_upsert("betting_data", supabase_records, "betid_timestamp", SUPABASE_BATCH_SIZE)
    
    logger.info(f"Successfully processed {len(data)} records")

def update_csv_backup(data):
    """Update the CSV backup with new betting data."""
    try:
        # Define CSV headers based on Supabase schema
        headers = [
            "bet_id", "timestamp", "betid_timestamp", "ev_percent", "event_time",
            "home_team", "away_team", "sport", "league", "bet_type",
            "participant", "bet_line", "bet_category", "odds", "sportsbook",
            "bet_size", "win_probability", "result"
        ]

        # Check if file exists to determine if we need to write headers
        file_exists = os.path.exists(CSV_FILE)

        # Open in append mode
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            
            # Write headers if file is new
            if not file_exists:
                writer.writeheader()

            # Convert and write each record
            for row in data:
                # Create record with Supabase schema
                record = {
                    "bet_id": row["bet_id"],
                    "timestamp": row["timestamp"],
                    "betid_timestamp": row["betid_timestamp"],
                    "ev_percent": row.get("EV Percent", ""),
                    "event_time": row.get("Event Time", ""),
                    "home_team": "",    # Will be parsed from Event Teams
                    "away_team": "",    # Will be parsed from Event Teams
                    "sport": "",        # Will be parsed from Sport/League
                    "league": "",       # Will be parsed from Sport/League
                    "bet_type": row.get("Bet Type", ""),
                    "participant": "",  # Will be parsed from Description
                    "bet_line": "",    # Will be parsed from Description
                    "bet_category": "", # Will be determined based on Bet Type
                    "odds": row.get("Odds", ""),
                    "sportsbook": row.get("Sportsbook", ""),
                    "bet_size": row.get("Bet Size", ""),
                    "win_probability": row.get("Win Probability", ""),
                    "result": ""
                }

                # Parse team names from Event Teams
                event_teams = row.get("Event Teams", "")
                if event_teams and event_teams != "N/A":
                    parts = event_teams.split(" vs ")
                    if len(parts) >= 2:
                        record["home_team"] = parts[0].strip()
                        record["away_team"] = parts[1].strip()

                # Parse sport and league from Sport/League
                sport_league = row.get("Sport/League", "")
                if sport_league and sport_league != "N/A":
                    parts = sport_league.split("|")
                    if len(parts) >= 2:
                        record["sport"] = parts[0].strip()
                        record["league"] = parts[1].strip()

                # Parse participant and bet_line from Description
                description = row.get("Description", "")
                if description and description != "N/A":
                    # Split on Over/Under if present
                    if "Over" in description:
                        parts = description.split("Over")
                        record["participant"] = parts[0].strip()
                        record["bet_line"] = f"Over {parts[1].strip()}"
                    elif "Under" in description:
                        parts = description.split("Under")
                        record["participant"] = parts[0].strip()
                        record["bet_line"] = f"Under {parts[1].strip()}"
                    else:
                        # If no Over/Under, use the whole description as participant
                        record["participant"] = description.strip()

                # Determine bet_category based on Bet Type
                bet_type = row.get("Bet Type", "")
                if bet_type:
                    if "Player" in bet_type:
                        record["bet_category"] = "Player Props"
                    elif "Moneyline" in bet_type:
                        record["bet_category"] = "Moneyline"
                    elif "Point Spread" in bet_type or "Spread" in bet_type:
                        record["bet_category"] = "Spread"
                    elif "Total" in bet_type:
                        record["bet_category"] = "Total"
                    else:
                        record["bet_category"] = "Other"

                writer.writerow(record)

        logger.info(f"Successfully updated CSV backup with {len(data)} records")
    except Exception as e:
        logger.error(f"Error updating CSV backup: {e}", exc_info=True)

# Main script logic
def main():
    try:
        # Set up the environment
        cleanup_logs(SCRAPER_LOG_FILE)
        cleanup_old_backups()
        
        # Scrape the data
        betting_data = scrape_webpage()
        if betting_data:
            logger.info(f"Successfully scraped {len(betting_data)} bet entries")
            
            # Create a backup of the data
            backup_timestamp = datetime.now().strftime("%Y%m%d")
            backup_file = os.path.join(BACKUP_DIR, f"backup_{backup_timestamp}.json")
            
            # Save as JSON for backup
            with open(backup_file, 'w') as f:
                json.dump(betting_data, f, indent=2)
            logger.info(f"Saved backup to {backup_file}")
            
            # Update CSV backup
            update_csv_backup(betting_data)
            
            # Insert or update in Supabase
            upsert_data(betting_data)
        else:
            logger.warning("No betting data was scraped")
    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)

if __name__ == "__main__":
    main()
