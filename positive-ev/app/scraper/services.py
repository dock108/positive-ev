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
from app.db_utils import get_db_connection
from flask import current_app

class ScraperService:
    """Service class to handle all scraping operations."""
    
    def __init__(self):
        """Initialize the scraper service."""
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for the scraper service."""
        log_file = os.path.join(current_app.config['LOGS_FOLDER'], 'scraping.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def setup_chrome_driver(self):
        """Initialize and configure Chrome WebDriver."""
        options = Options()
        for option in current_app.config['CHROME_OPTIONS']:
            options.add_argument(option)
        options.add_argument(f"user-data-dir={current_app.config['CHROME_PROFILE']}")
        
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
    
    def scrape_odds(self):
        """Scrape betting odds from the target website."""
        try:
            driver = self.setup_chrome_driver()
            new_bets = []
            
            try:
                driver.get(current_app.config['TARGET_URL'])
                logging.info('Navigated to OddsJam Positive EV page.')
                
                time.sleep(current_app.config['PAGE_LOAD_WAIT'])
                
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                timestamp = datetime.utcnow()
                odds_data = self.parse_cleaned_data(soup, timestamp)
                
                if odds_data:
                    new_bets = self.save_betting_data(odds_data)
                    logging.info(f'Extracted and saved {len(new_bets)} rows of data.')
                else:
                    logging.warning('No data was extracted from the page.')
                    
            finally:
                driver.quit()
                logging.info('Browser closed.')
                
            return new_bets
            
        except Exception as e:
            logging.error(f'An error occurred during scraping: {e}', exc_info=True)
            raise
    
    def parse_cleaned_data(self, soup, timestamp):
        """Parse data grouped by bet blocks."""
        try:
            bet_blocks = soup.select(current_app.config['SELECTORS']['bet_blocks'])
            logging.info(f'Found {len(bet_blocks)} bet blocks.')
            
            data = []
            for index, block in enumerate(bet_blocks):
                try:
                    row = self.parse_bet_block(block, timestamp, index)
                    if row:
                        data.append(row)
                except Exception as e:
                    logging.warning(f'Failed to parse bet block {index}: {e}')
            
            return data
            
        except Exception as e:
            logging.error(f'Error parsing data: {e}', exc_info=True)
            return []
 
    def parse_bet_block(self, block, timestamp, index):
        """Parse individual bet block."""
        selectors = current_app.config['SELECTORS']
        row = {'timestamp': timestamp}
        
        try:
            # Extract data using configured selectors
            field_mapping = {
                'EV Percent': 'ev_percent',
                'Event Time': 'event_time',
                'Event Teams': 'event_teams',
                'Sport/League': 'sport_league',
                'Bet Type': 'bet_type',
                'Description': 'description',
                'Odds': 'odds',
                'Sportsbook': 'sportsbook',
                'Bet Size': 'bet_size',
                'Win Probability': 'win_probability'
            }
            
            for scraper_field, selector in selectors.items():
                if scraper_field == 'bet_blocks':
                    continue
                    
                element = block.select_one(selector)
                value = element.text.strip() if element else None
                
                # Map the field name to database model field
                db_field = field_mapping.get(scraper_field, scraper_field)
                
                # Process values based on field type
                if db_field == 'ev_percent':
                    value = float(value.strip('%')) if value else None
                elif db_field == 'odds':
                    value = value.strip() if value else None
                elif db_field == 'bet_size':
                    if value and value.strip() != 'N/A':
                        # Remove currency symbol and any whitespace, then convert to float
                        cleaned_value = value.strip().replace('$', '').replace(',', '').strip()
                        value = float(cleaned_value) if cleaned_value else None
                    else:
                        value = None
                elif db_field == 'win_probability':
                    value = float(value.strip('%')) if value else None
                elif db_field == 'sportsbook':
                    value = element['alt'].strip() if element else None
                
                row[db_field] = value
            
            # Generate bet ID
            row['bet_id'] = self.generate_bet_id(row)
            
            logging.info(f'Extracted Row {index}: {row}')
            return row
            
        except Exception as e:
            logging.warning(f'Error parsing bet block {index}: {e}')
            return None
    
    def save_betting_data(self, data):
        """Save parsed betting data to database."""
        new_bets = []
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for row in data:
                try:
                    # Check if bet exists
                    cursor.execute("SELECT bet_id FROM betting_data WHERE bet_id = ?", (row['bet_id'],))
                    existing_bet = cursor.fetchone()
                    
                    if not existing_bet:
                        cursor.execute("""
                            INSERT INTO betting_data (
                                bet_id, timestamp, ev_percent, event_time, event_teams,
                                sport_league, bet_type, description, odds, sportsbook,
                                bet_size, win_probability
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            row['bet_id'],
                            row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                            row['ev_percent'],
                            self.parse_event_time(row['event_time']),
                            row['event_teams'],
                            row['sport_league'],
                            row['bet_type'],
                            row['description'],
                            row['odds'],
                            row['sportsbook'],
                            row['bet_size'],
                            row['win_probability']
                        ))
                        new_bets.append(row)
                    
                except Exception as e:
                    logging.error(f'Error saving bet {row["bet_id"]}: {e}')
                    continue
            
            try:
                conn.commit()
            except Exception as e:
                conn.rollback()
                logging.error(f'Error committing betting data: {e}')
                raise
        
        return new_bets
    
    def update_bet_results(self):
        """Update results for resolved bets."""
        # Implementation for updating bet results
        pass
    
    def cleanup_old_data(self):
        """Clean up old data and create backups."""
        try:
            # Create backup
            self.create_daily_backup()
            
            # Clean up old backups
            self.cleanup_old_backups()
            
            # Archive old resolved bets
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.*, boe.outcome as result
                    FROM betting_data b
                    LEFT JOIN bet_outcome_evaluation boe ON b.bet_id = boe.bet_id
                    WHERE b.timestamp < ? AND boe.outcome IN ('WIN', 'LOSS', 'TIE')
                """, (cutoff_date.strftime('%Y-%m-%d %H:%M:%S'),))
                old_bets = cursor.fetchall()
                
                # Archive logic here if needed
                
                return len(old_bets)
            
        except Exception as e:
            logging.error(f'Error during cleanup: {e}', exc_info=True)
            raise
    
    def create_daily_backup(self):
        """Create a daily backup of the database."""
        try:
            backup_folder = current_app.config['BACKUP_FOLDER']
            db_file = current_app.config['DATABASE_PATH']
            
            if not os.path.exists(backup_folder):
                os.makedirs(backup_folder)
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%m%d%y')
            backup_file = os.path.join(backup_folder, f'betting_data_{yesterday}.db')
            
            if not os.path.exists(backup_file):
                shutil.copy(db_file, backup_file)
                logging.info(f'Database backup created: {backup_file}')
            else:
                logging.info(f'Backup already exists for {yesterday}: {backup_file}')
                
        except Exception as e:
            logging.error(f'Error creating database backup: {e}', exc_info=True)
            raise
    
    def cleanup_old_backups(self):
        """Delete backups older than retention period."""
        try:
            backup_folder = current_app.config['BACKUP_FOLDER']
            retention_days = current_app.config['BACKUP_RETENTION_DAYS']
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for filename in os.listdir(backup_folder):
                if filename.startswith('betting_data_') and filename.endswith('.db'):
                    file_path = os.path.join(backup_folder, filename)
                    try:
                        date_part = filename.replace('betting_data_', '').replace('.db', '')
                        file_date = datetime.strptime(date_part, '%m%d%y')
                        if file_date < cutoff_date:
                            os.remove(file_path)
                            logging.info(f'Deleted old backup: {file_path}')
                    except ValueError as e:
                        logging.warning(f'Skipping invalid backup file: {filename} - Error: {e}')
                        
        except Exception as e:
            logging.error(f'Failed to clean up old backups: {e}', exc_info=True)
            raise
    
    @staticmethod
    def generate_bet_id(row):
        """Generate a unique identifier for a bet."""
        components = [
            str(row['event_time']),
            row['event_teams'],
            row['sport_league'],
            row['bet_type'],
            row['description']
        ]
        return '_'.join(filter(None, components))
    
    @staticmethod
    def parse_event_time(time_str):
        """Parse event time string into datetime object."""
        # Implementation for parsing event time
        pass 