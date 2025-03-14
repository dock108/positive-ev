#!/usr/bin/env python3
"""
Chrome Profile Export Utility

This script exports a Chrome profile from the user's local machine to the project root
for deployment to Vercel. It copies only the essential files needed for the scraper
to function properly, creating a clean profile suitable for deployment.

Usage:
    python export_chrome_profile.py

The script will:
1. Copy the Chrome profile from the default location to the project root
2. Create a .gitignore entry to prevent committing the profile to version control
3. Verify that all essential files are present
"""

import os
import sys
import shutil
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Define paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SOURCE_PROFILE = os.path.expanduser("~/Library/Application Support/Google/Chrome/ScraperProfile")
TARGET_PROFILE = os.path.join(PROJECT_ROOT, "chrome-profile")

# Essential files to copy
ESSENTIAL_FILES = [
    'Cookies',
    'Login Data',
    'Preferences',
    'Web Data',
    'Network',
    'Local Storage'
]

def export_chrome_profile(source_profile=None):
    """
    Export the Chrome profile from the source location to the project root.
    
    Args:
        source_profile (str, optional): Path to the source Chrome profile.
            Defaults to ~/Library/Application Support/Google/Chrome/ScraperProfile.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    # Use the provided source profile or the default
    source_profile = source_profile or DEFAULT_SOURCE_PROFILE
    
    try:
        # Check if source profile exists
        if not os.path.exists(source_profile):
            logging.error(f"Source Chrome profile does not exist: {source_profile}")
            return False
        
        logging.info(f"Source Chrome profile found: {source_profile}")
        
        # Create target directory if it doesn't exist
        if os.path.exists(TARGET_PROFILE):
            logging.info(f"Removing existing target profile: {TARGET_PROFILE}")
            shutil.rmtree(TARGET_PROFILE)
        
        os.makedirs(TARGET_PROFILE, exist_ok=True)
        logging.info(f"Created target profile directory: {TARGET_PROFILE}")
        
        # Copy essential files and directories
        missing_files = []
        for item in ESSENTIAL_FILES:
            source_item = os.path.join(source_profile, item)
            target_item = os.path.join(TARGET_PROFILE, item)
            
            if os.path.exists(source_item):
                if os.path.isdir(source_item):
                    shutil.copytree(source_item, target_item)
                    logging.info(f"Copied directory: {item}")
                else:
                    shutil.copy2(source_item, target_item)
                    logging.info(f"Copied file: {item}")
            else:
                missing_files.append(item)
        
        if missing_files:
            logging.warning(f"Missing files in source profile: {', '.join(missing_files)}")
        
        # Create a First Run file to skip the first run experience
        first_run_file = os.path.join(TARGET_PROFILE, "First Run")
        open(first_run_file, "w").close()
        logging.info("Created 'First Run' file to skip Chrome first-run experience")
        
        # Update .gitignore to exclude the Chrome profile
        gitignore_path = os.path.join(PROJECT_ROOT, ".gitignore")
        gitignore_entry = "chrome-profile/"
        
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as f:
                content = f.read()
            
            if gitignore_entry not in content:
                with open(gitignore_path, "a") as f:
                    if not content.endswith("\n"):
                        f.write("\n")
                    f.write(f"{gitignore_entry}\n")
                logging.info(f"Added {gitignore_entry} to .gitignore")
        else:
            with open(gitignore_path, "w") as f:
                f.write(f"{gitignore_entry}\n")
            logging.info(f"Created .gitignore with {gitignore_entry}")
        
        logging.info(f"Chrome profile successfully exported to: {TARGET_PROFILE}")
        return True
    
    except Exception as e:
        logging.error(f"Error exporting Chrome profile: {e}")
        return False

if __name__ == "__main__":
    logging.info("Starting Chrome profile export...")
    
    if len(sys.argv) > 1:
        custom_source = sys.argv[1]
        result = export_chrome_profile(custom_source)
    else:
        result = export_chrome_profile()
    
    if result:
        logging.info("Chrome profile export completed successfully!")
        print(f"\nProfile exported to: {TARGET_PROFILE}")
        print("You can now deploy this profile to Vercel.")
    else:
        logging.error("Chrome profile export failed!")
        sys.exit(1) 