#!/usr/bin/env python3
"""
Chrome profile setup utility script.
This script sets up a Chrome profile for the scraper to use.
It assumes the Chrome profile directory already exists and has been
manually copied to the server during deployment.
"""

import os
import sys
import logging

# Set up basic logging for this standalone script
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import from new consolidated modules
try:
    from src.config import CHROME_PROFILE, CHROME_OPTIONS
    
    logging.info(f"Using Chrome profile path: {CHROME_PROFILE}")
    logging.info(f"Chrome options: {CHROME_OPTIONS}")
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def setup_chrome_profile():
    """
    Set up the Chrome profile directory on the server.
    This function assumes the Chrome profile directory already exists
    and has been manually copied to the server during deployment.
    """
    try:
        # Check if profile directory exists
        if not os.path.exists(CHROME_PROFILE):
            logging.error(f"Chrome profile directory does not exist: {CHROME_PROFILE}")
            logging.error("The Chrome profile must be manually copied during deployment")
            return False
            
        logging.info(f"Chrome profile directory exists: {CHROME_PROFILE}")
        
        # Check for essential files
        essential_files = ['Cookies', 'Preferences', 'Web Data']
        missing_files = []
        
        for filename in essential_files:
            file_path = os.path.join(CHROME_PROFILE, filename)
            if not os.path.exists(file_path):
                missing_files.append(filename)
        
        if missing_files:
            logging.warning(f"Missing essential files in Chrome profile: {', '.join(missing_files)}")
            logging.warning("The Chrome profile may not work correctly")
        else:
            logging.info("All essential Chrome profile files are present")
        
        # Create a First Run file to skip the first run experience if it doesn't exist
        first_run_file = os.path.join(CHROME_PROFILE, "First Run")
        if not os.path.exists(first_run_file):
            # Create an empty file
            open(first_run_file, "w").close()
            logging.info(f"Created First Run file: {first_run_file}")
        
        return True
    except Exception as e:
        logging.error(f"Error setting up Chrome profile: {e}")
        return False

if __name__ == "__main__":
    logging.info("Starting Chrome profile setup...")
    
    if setup_chrome_profile():
        logging.info("Successfully set up Chrome profile")
    else:
        logging.error("Failed to set up Chrome profile")
        sys.exit(1)
    
    logging.info("Chrome profile setup complete!") 