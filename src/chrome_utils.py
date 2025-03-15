"""
Chrome Utilities Module
=====================

This module provides utility functions for managing Chrome/Chromium browser instances
and WebDriver configurations. It centralizes browser setup and management logic.

Key Features:
    - Chrome driver setup and configuration
    - Browser options management
    - Profile handling
    - Error recovery and retry logic
    - Logging and diagnostics
    - Cross-platform compatibility

Dependencies:
    - selenium: For web automation
    - webdriver_manager: For ChromeDriver management
    - python-dotenv: For environment variables

Environment Variables Used:
    - CHROME_PROFILE: Path to Chrome/Chromium profile directory
    - CHROME_OPTIONS: List of Chrome command-line options
    - CHROME_LOG_FILE: Path to Chrome log file

Usage:
    from src.chrome_utils import setup_chrome_driver

    # Get configured Chrome driver
    driver = setup_chrome_driver()
    
    # Use driver with automatic cleanup
    with setup_chrome_driver() as driver:
        driver.get("https://example.com")

Author: highlyprofitable108
Created: March 2025
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import from new consolidated modules
try:
    # Try relative imports (when used as a module)
    from .config import CHROME_PROFILE, CHROME_OPTIONS, CHROME_LOG_FILE, setup_logging
except ImportError:
    # Fall back to absolute imports (when run directly)
    from src.config import CHROME_PROFILE, CHROME_OPTIONS, CHROME_LOG_FILE, setup_logging

# Get logger for this module
logger = setup_logging(CHROME_LOG_FILE, "chrome")

def setup_chrome_driver():
    """Initialize and configure Chrome WebDriver."""
    try:
        options = Options()
        for option in CHROME_OPTIONS:
            options.add_argument(option)
            
        if CHROME_PROFILE:
            # Ensure profile directory exists
            os.makedirs(CHROME_PROFILE, exist_ok=True)
            options.add_argument(f"user-data-dir={CHROME_PROFILE}")
            logger.info(f"Using Chrome profile at: {CHROME_PROFILE}")
        
        # Create and return Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("Chrome WebDriver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        raise 