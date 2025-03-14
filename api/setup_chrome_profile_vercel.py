"""
Chrome Profile Setup for Vercel

This script downloads and sets up a Chrome profile during Vercel function initialization.
It can download a Chrome profile from a URL (e.g., S3, GitHub, etc.) and extract it
to the appropriate location for use by the scraper.

This approach allows you to store the Chrome profile externally and download it
during deployment, rather than including it in the Git repository.
"""

import os
import sys
import logging
import requests
import zipfile
import io

# Set up logging
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

# Import configuration
try:
    from src.config import CHROME_PROFILE
except ImportError:
    # Fallback if config can't be imported
    CHROME_PROFILE = os.path.join(project_root, "chrome-profile")

def download_and_setup_chrome_profile():
    """
    Download and set up Chrome profile from a URL specified in environment variables.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    # Get Chrome profile URL from environment variable
    chrome_profile_url = os.environ.get("CHROME_PROFILE_URL")
    
    if not chrome_profile_url:
        logging.warning("CHROME_PROFILE_URL environment variable not set.")
        logging.info("Checking if local Chrome profile exists...")
        
        # Check if a local profile exists (included in deployment)
        if os.path.exists(CHROME_PROFILE) and os.path.isdir(CHROME_PROFILE):
            logging.info(f"Local Chrome profile found at {CHROME_PROFILE}")
            return True
        else:
            logging.error("No Chrome profile URL provided and no local profile found.")
            return False
    
    try:
        logging.info(f"Downloading Chrome profile from {chrome_profile_url}")
        
        # Download the Chrome profile ZIP file
        response = requests.get(chrome_profile_url, stream=True)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Create a BytesIO object from the response content
        zip_data = io.BytesIO(response.content)
        
        # Create the Chrome profile directory if it doesn't exist
        os.makedirs(CHROME_PROFILE, exist_ok=True)
        
        # Extract the ZIP file to the Chrome profile directory
        with zipfile.ZipFile(zip_data) as zip_ref:
            zip_ref.extractall(CHROME_PROFILE)
        
        logging.info(f"Chrome profile extracted to {CHROME_PROFILE}")
        
        # Create a First Run file to skip the first run experience
        first_run_file = os.path.join(CHROME_PROFILE, "First Run")
        open(first_run_file, "w").close()
        logging.info("Created 'First Run' file to skip Chrome first-run experience")
        
        # List the contents of the Chrome profile directory
        profile_contents = os.listdir(CHROME_PROFILE)
        logging.info(f"Chrome profile contents: {profile_contents}")
        
        return True
    
    except Exception as e:
        logging.error(f"Error setting up Chrome profile: {e}")
        return False

if __name__ == "__main__":
    logging.info("Starting Chrome profile setup for Vercel...")
    
    if download_and_setup_chrome_profile():
        logging.info("Chrome profile setup completed successfully!")
    else:
        logging.error("Chrome profile setup failed!")
        sys.exit(1) 