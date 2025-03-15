"""
Configuration Module
==================

This module centralizes all configuration settings for the Positive EV application.
It handles environment variables, logging setup, and global constants.

Key Features:
    - Environment variable management
    - Logging configuration
    - Path management
    - Batch processing settings
    - Web scraping selectors

Configuration Categories:
    - Database Settings (Supabase)
    - File Paths and Directories
    - Logging Configuration
    - Batch Processing Parameters
    - Web Scraping Selectors

Dependencies:
    - python-dotenv: For environment variable management
    - logging: For application-wide logging

Environment Variables Required:
    - SUPABASE_URL: URL of the Supabase instance
    - SUPABASE_KEY: API key for Supabase authentication
    - SUPABASE_BATCH_SIZE: Number of records per batch (default: 100)
    - GRADE_BATCH_SIZE: Number of grades per batch (default: 25)

Usage:
    from src.config import (
        SUPABASE_URL,
        SUPABASE_KEY,
        setup_logging
    )

Author: highlyprofitable108
Created: March 2025
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import platform

# Load environment variables
load_dotenv()

# Project structure - use relative path approach
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Directory Configuration
LOGS_DIR = Path('/tmp/logs') if os.environ.get('VERCEL') else Path(PROJECT_ROOT) / "logs"
BACKUP_DIR = Path('/tmp/backups') if os.environ.get('VERCEL') else Path(PROJECT_ROOT) / "backups"
CSV_DIR = Path(PROJECT_ROOT) / "csv_backups"  # New directory for CSV backups

# Ensure all directories exist
for directory in [LOGS_DIR, BACKUP_DIR, CSV_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# File Paths
DB_FILE = os.path.join(PROJECT_ROOT, "betting_data.db")  # Legacy SQLite database file
SCRAPER_LOG_FILE = os.path.join(LOGS_DIR, "scraping.log")
CALCULATOR_LOG_FILE = os.path.join(LOGS_DIR, "grade_calculator.log")
SUPABASE_LOG_FILE = os.path.join(LOGS_DIR, "supabase.log")
CHROME_LOG_FILE = os.path.join(LOGS_DIR, "chrome.log")
CSV_FILE = os.path.join(CSV_DIR, "betting_data.csv")  # CSV backup file

# Cleanup Settings
BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '10'))
LOG_RETENTION_HOURS = int(os.environ.get('LOG_RETENTION_HOURS', '4'))

# Scraping Configuration
TARGET_URL = "https://oddsjam.com/betting-tools/positive-ev"
PAGE_LOAD_WAIT = int(os.environ.get('PAGE_LOAD_WAIT', '10'))

# Chrome Configuration
if platform.system() == 'Darwin':  # macOS
    CHROME_PROFILE = os.path.expanduser(os.environ.get('CHROME_PROFILE', '~/Library/Application Support/Google/Chrome/ScraperProfile'))
else:  # Linux (including Raspberry Pi)
    CHROME_PROFILE = os.path.expanduser(os.environ.get('CHROME_PROFILE', '~/.config/chromium/Default'))

CHROME_OPTIONS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--headless",
    "--disable-gpu",
    "--window-size=1920,1080"
]

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Batch Processing Configuration
SUPABASE_BATCH_SIZE = int(os.environ.get('SUPABASE_BATCH_SIZE', '100'))
GRADE_BATCH_SIZE = int(os.environ.get('GRADE_BATCH_SIZE', '25'))

# CSS Selectors for scraping
SELECTORS = {
    'bet_blocks': "div#betting-tool-table-row",
    'ev_percent': "p#percent-cell",
    'event_time': "div[data-testid='event-cell'] > p.text-xs",
    'event_teams': "p.text-sm.font-semibold",
    'sport_league': "p.text-sm:not(.font-semibold)",
    'bet_type': "p.text-sm.text-brand-purple",
    'description': "div.tour__bet_and_books p.flex-1",
    'odds': "p.text-sm.font-bold",
    'sportsbook': "img[alt]",
    'bet_size': "p.text-sm.__className_179fbf.self-center.font-semibold.text-white",
    'win_probability': "p.text-sm.text-white:last-child"
}

# Configure logging
def setup_logging(log_file, name, clean_logs=True):
    """Configure logging for a specific module"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Clear existing handlers
    logger.propagate = False  # Don't propagate to parent loggers
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(file_format)
    logger.addHandler(console_handler)
    
    # Clean old log entries if requested
    if clean_logs:
        try:
            # Try relative imports (when used as a module)
            from .common_utils import cleanup_logs
        except ImportError:
            # Fall back to absolute imports (when run directly)
            from src.common_utils import cleanup_logs
        cleanup_logs(log_file, LOG_RETENTION_HOURS)
    
    return logger
