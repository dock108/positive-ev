"""
Selenium Setup Module
===================

This module handles the setup and configuration of Selenium WebDriver for web automation.
It provides a unified interface for creating and managing Chrome/Chromium browser instances.

Key Features:
    - WebDriver initialization and configuration
    - Chrome profile management
    - Proxy support (if configured)
    - Error handling and recovery
    - Cross-platform compatibility (macOS, Linux)

Dependencies:
    - selenium: For web automation
    - webdriver_manager: For ChromeDriver management
    - python-dotenv: For environment variables

Environment Variables Used:
    - CHROME_PROFILE: Path to Chrome/Chromium profile directory
    - PROXY_SERVER: Optional proxy server configuration
    - HEADLESS: Whether to run in headless mode (default: true)

Usage:
    from src.selenium_setup import setup_webdriver

    # Get configured WebDriver instance
    driver = setup_webdriver()
    driver.get("https://example.com")

Author: highlyprofitable108
Created: March 2025
"""

import os
import sys
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Import configuration
from config import CHROME_PROFILE, CHROME_OPTIONS

# Get project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Ensure logs directory exists at project root
logs_dir = os.path.join(project_root, "logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Set up logging
logging.basicConfig(
    filename=os.path.join(logs_dir, "debug.log"),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def setup_driver():
    """Initialize ChromeDriver with debugging options."""
    try:
        options = Options()
        
        # Add standard Chrome options from config
        for option in CHROME_OPTIONS:
            options.add_argument(option)
            
        # Add additional debugging options
        options.add_argument("--start-maximized")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--remote-debugging-port=9222")

        # Use the saved profile from config
        options.add_argument(f"user-data-dir={CHROME_PROFILE}")

        # Set ChromeDriver logging
        service = Service(ChromeDriverManager().install())
        service.log_path = os.path.join(logs_dir, "chromedriver.log")
        service.start()

        driver = webdriver.Chrome(service=service, options=options)
        logging.info("ChromeDriver initialized successfully.")
        return driver

    except Exception as e:
        logging.error(f"Failed to initialize ChromeDriver: {e}", exc_info=True)
        raise

def check_driver_crash(driver):
    """Check if ChromeDriver process is running."""
    try:
        driver.execute_script("return navigator.userAgent;")
        logging.info("ChromeDriver is running fine.")
    except Exception:
        logging.critical("ChromeDriver seems to have crashed!", exc_info=True)
        driver.save_screenshot(os.path.join(logs_dir, "chrome_crash.png"))
        raise

def login_to_oddsjam(driver):
    """Automate login to OddsJam with debugging."""
    try:
        login_url = "https://oddsjam.com/login"
        driver.get(login_url)
        logging.info(f"Navigated to {login_url}")

        # Check if login page loaded
        time.sleep(2)
        check_driver_crash(driver)

        # Take a screenshot before attempting login
        driver.save_screenshot(os.path.join(logs_dir, "login_page.png"))

        # Enter email
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        )
        email_input.send_keys("mike.fuscoletti@gmail.com")
        email_input.send_keys(Keys.RETURN)
        logging.info("Entered email and submitted.")

        # Check if the page transitioned to the verification step
        time.sleep(2)
        check_driver_crash(driver)

        # Prompt user to manually enter verification code
        print("Enter the verification code manually in the browser and complete the login process.")
        input("Once you're logged in, type 'y' and hit Enter to continue: ")

        # Final verification
        driver.save_screenshot(os.path.join(logs_dir, "login_success.png"))
        logging.info("Login successful. Profile saved.")

    except Exception as e:
        logging.error(f"Login failed: {e}", exc_info=True)
        driver.save_screenshot(os.path.join(logs_dir, "login_error.png"))
        raise

if __name__ == "__main__":
    driver = None
    try:
        driver = setup_driver()
        login_to_oddsjam(driver)

    except Exception as e:
        logging.critical(f"Fatal script error: {e}", exc_info=True)

    finally:
        if driver:
            driver.quit()
            logging.info("ChromeDriver closed.")
